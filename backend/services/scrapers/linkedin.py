import os
import urllib.parse
import logging
from typing import List
from models.schemas import JobItem
from services.scrapers.mock_data import generate_mock_jobs
from utils.browser import BrowserManager
from utils.ddg_search import discover_job_urls

logger = logging.getLogger("services.scrapers.linkedin")

async def scrape_linkedin(job_title: str, industry: str, location: str, radius: int) -> List[JobItem]:
    """
    Scrapes LinkedIn Jobs UK or generates mock jobs if DEMO_MODE=true.
    First attempts URL discovery via DuckDuckGo, falling back to direct search page crawling.
    """
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    if demo_mode:
        logger.info("DEMO_MODE active: returning mock LinkedIn data")
        return generate_mock_jobs(job_title, industry, location, "LinkedIn")

    logger.info(f"Scraping LinkedIn for {job_title} in {location} (radius {radius})")
    
    # 1. Try DuckDuckGo URL discovery
    urls = discover_job_urls("uk.linkedin.com/jobs/view", job_title, location, max_results=20)
    
    if urls:
        logger.info(f"Discovered {len(urls)} LinkedIn URLs. Scraping pages...")
        jobs = []
        page = None
        try:
            page = await BrowserManager.new_page()
            for url in urls:
                try:
                    logger.info(f"Scraping LinkedIn individual job page: {url}")
                    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    
                    # Wait for either the job title or an authwall redirect
                    try:
                        await page.wait_for_selector("h1, .topcard__title, .top-card-layout__title", timeout=5000)
                    except Exception:
                        logger.warning(f"LinkedIn page redirected to authwall or blocked: {url}")
                        continue
                        
                    title_el = await page.query_selector("h1, .topcard__title, .top-card-layout__title")
                    company_el = await page.query_selector(".topcard__org-name-link, .top-card-layout__subcard a, .top-card-layout__org-name-link")
                    location_el = await page.query_selector(".topcard__flavor--bullet, .topcard__flavor--metadata, .top-card-layout__first-subcard-item")
                    time_el = await page.query_selector(".posted-time-ago__text, .topcard__flavor--metadata")
                    desc_el = await page.query_selector(".show-more-less-html__markup, .description__text, #job-details, .jobs-description")
                    
                    title = (await title_el.inner_text()).strip() if title_el else ""
                    company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                    loc = (await location_el.inner_text()).strip() if location_el else location
                    posted = (await time_el.inner_text()).strip() if time_el else "Recent"
                    description = (await desc_el.inner_text()).strip() if desc_el else ""
                    
                    # Filter out redirected authwall or generic search landing pages
                    title_lower = title.lower()
                    if not title or "join linkedin" in title_lower or "jobs in " in title_lower:
                        logger.warning(f"Discarding LinkedIn redirected authwall/landing page: {url} (Title: {title}, Company: {company})")
                        continue
                        
                    if title:
                        logger.info(f"Extracted LinkedIn Job: '{title}' at '{company}' (Date: {posted})")
                        jobs.append(JobItem(
                            job_title=title,
                            company_name=company,
                            job_website="LinkedIn",
                            location=loc,
                            date_posted=posted,
                            industry_match=True,
                            job_type="Permanent",
                            job_url=url,
                            match_reason=f"Title '{title}' is a strong match for the requested '{job_title}' role within {industry}.",
                            job_description=description
                        ))
                except Exception as e:
                    if "Execution context was destroyed" in str(e):
                        logger.warning(f"LinkedIn authwall redirect prevented scraping: {url}")
                    else:
                        logger.error(f"Error scraping individual LinkedIn page {url}: {e}")
                    continue
            
            if jobs:
                return jobs
        except Exception as e:
            logger.error(f"Failed scraping LinkedIn individual URLs: {e}")
        finally:
            if page:
                await page.close()

    # 2. Fallback to direct search page crawling
    logger.info("Falling back to direct search page crawling for LinkedIn...")
    jobs = []
    page = None
    try:
        page = await BrowserManager.new_page()
        
        query = urllib.parse.quote(job_title)
        loc_query = urllib.parse.quote(f"{location}, United Kingdom")
        
        dist = 25
        if radius <= 5: dist = 5
        elif radius <= 10: dist = 10
        elif radius <= 25: dist = 25
        elif radius <= 50: dist = 50
        else: dist = 100

        url = f"https://uk.linkedin.com/jobs/search?keywords={query}&location={loc_query}&distance={dist}&f_TPR=r7776000"
        
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        try:
            await page.wait_for_selector(".jobs-search__results-list li", timeout=10000)
        except Exception:
            logger.warning("LinkedIn job list elements selector not found in fallback search page crawl.")
            return []

        job_cards = await page.query_selector_all(".jobs-search__results-list li")
        
        cards_data = []
        for card in job_cards[:8]:
            try:
                title_el = await card.query_selector(".base-search-card__title")
                company_el = await card.query_selector(".base-search-card__subtitle")
                location_el = await card.query_selector(".base-search-card__metadata-location")
                link_el = await card.query_selector(".base-card__full-link")
                time_el = await card.query_selector(".job-search-card__listdate, .job-search-card__listdate--new")
                
                title = (await title_el.inner_text()).strip() if title_el else ""
                company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                loc = (await location_el.inner_text()).strip() if location_el else location
                link = await link_el.get_attribute("href") if link_el else ""
                posted = (await time_el.inner_text()).strip() if time_el else "Recent"
                
                if title and link:
                    cards_data.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "link": link,
                        "posted": posted
                    })
            except Exception as e:
                logger.error(f"Error parsing LinkedIn card metadata in fallback search: {e}")
                continue
                
        # Now visit each link to scrape description
        for data in cards_data:
            try:
                logger.info(f"Navigating to fallback LinkedIn page: {data['link']}")
                await page.goto(data["link"], wait_until="domcontentloaded", timeout=15000)
                
                title_el = await page.query_selector("h1, .topcard__title, .top-card-layout__title")
                title = (await title_el.inner_text()).strip() if title_el else data["title"]
                
                title_lower = title.lower()
                if "join linkedin" in title_lower or "jobs in " in title_lower:
                    logger.warning(f"Discarding fallback LinkedIn redirected authwall/landing page: {data['link']} (Title: {title})")
                    continue
                
                desc_el = await page.query_selector(".show-more-less-html__markup, .description__text, #job-details, .jobs-description")
                description = (await desc_el.inner_text()).strip() if desc_el else ""
                
                jobs.append(JobItem(
                    job_title=title,
                    company_name=data["company"],
                    job_website="LinkedIn",
                    location=data["location"],
                    date_posted=data["posted"],
                    industry_match=True,
                    job_type="Permanent",
                    job_url=data["link"],
                    match_reason=f"Title '{title}' is a strong match for the requested '{job_title}' role within {industry}.",
                    job_description=description
                ))
            except Exception as e:
                logger.error(f"Error scraping description for fallback LinkedIn job {data['link']}: {e}")
                # Append even without description as fallback if title is not an authwall
                jobs.append(JobItem(
                    job_title=data["title"],
                    company_name=data["company"],
                    job_website="LinkedIn",
                    location=data["location"],
                    date_posted=data["posted"],
                    industry_match=True,
                    job_type="Permanent",
                    job_url=data["link"],
                    match_reason=f"Title '{data['title']}' is a strong match for the requested '{job_title}' role within {industry}.",
                    job_description=""
                ))
                
    except Exception as e:
        logger.error(f"LinkedIn fallback search failed: {str(e)}")
        raise e
    finally:
        if page:
            await page.close()
            
    return jobs
