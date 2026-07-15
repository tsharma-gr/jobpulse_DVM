import os
import urllib.parse
import logging
from typing import List
from models.schemas import JobItem
from services.scrapers.mock_data import generate_mock_jobs
from utils.browser import BrowserManager
from utils.ddg_search import discover_job_urls

logger = logging.getLogger("services.scrapers.cvlibrary")

async def scrape_cvlibrary(job_title: str, industry: str, location: str, radius: int) -> List[JobItem]:
    """
    Scrapes CV-Library UK or generates mock jobs if DEMO_MODE=true.
    First attempts URL discovery via DuckDuckGo, falling back to direct search page crawling.
    """
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    if demo_mode:
        logger.info("DEMO_MODE active: returning mock CV-Library UK data")
        return generate_mock_jobs(job_title, industry, location, "CV-Library")

    logger.info(f"Scraping CV-Library for {job_title} in {location} (radius {radius})")
    
    # 1. Try DuckDuckGo URL discovery
    urls = discover_job_urls("cv-library.co.uk/job", job_title, location, max_results=8)
    
    if urls:
        logger.info(f"Discovered {len(urls)} CV-Library URLs. Scraping pages...")
        jobs = []
        page = None
        try:
            page = await BrowserManager.new_page()
            for url in urls:
                try:
                    logger.info(f"Scraping CV-Library individual job page: {url}")
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    
                    # Dismiss cookie popup if visible
                    try:
                        cookie = await page.query_selector("#cmp-bnty-ok, button:has-text('Accept')")
                        if cookie:
                            await cookie.click()
                    except Exception:
                        pass
                    
                    title_el = await page.query_selector("h1")
                    company_el = await page.query_selector("[itemprop='name'], .job__company, .job__meta-company")
                    location_el = await page.query_selector(".job__location, .job__meta-location")
                    time_el = await page.query_selector(".job__posted, .job__meta-posted")
                    type_el = await page.query_selector(".job__type, .job__meta-type")
                    desc_el = await page.query_selector("[itemprop='description'], .job__description, .job-description")
                    
                    title = (await title_el.inner_text()).strip() if title_el else ""
                    company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                    loc = (await location_el.inner_text()).strip() if location_el else location
                    posted = (await time_el.inner_text()).strip() if time_el else "Recent"
                    job_type = (await type_el.inner_text()).strip() if type_el else "Permanent"
                    description = (await desc_el.inner_text()).strip() if desc_el else ""
                    
                    # Filter out blocked pages or generic landing pages
                    title_lower = title.lower()
                    if not title or title_lower == "blocked":
                        logger.warning(f"Discarding CV-Library blocked/invalid page: {url} (Title: {title}, Company: {company})")
                        continue
                        
                    if title:
                        logger.info(f"Extracted CV-Library Job: '{title}' at '{company}' (Date: {posted})")
                        jobs.append(JobItem(
                            job_title=title,
                            company_name=company,
                            job_website="CV-Library",
                            location=loc,
                            date_posted=posted,
                            industry_match=True,
                            job_type=job_type,
                            job_url=url,
                            match_reason=f"Title '{title}' is a strong match for the requested '{job_title}' role within {industry}.",
                            job_description=description
                        ))
                except Exception as e:
                    logger.error(f"Error scraping individual CV-Library page {url}: {e}")
                    continue
            
            if jobs:
                return jobs
        except Exception as e:
            logger.error(f"Failed scraping CV-Library individual URLs: {e}")
        finally:
            if page:
                await page.close()

    # 2. Fallback to direct search page crawling
    logger.info("Falling back to direct search page crawling for CV-Library...")
    jobs = []
    page = None
    try:
        page = await BrowserManager.new_page()
        import re
        if " or " in job_title.lower():
            parts = re.split(r'\s+or\s+', job_title, flags=re.IGNORECASE)
            simplified = " OR ".join([p.strip() for p in parts if p.strip()][:4])
        else:
            simplified = job_title
        query = urllib.parse.quote(simplified)
        loc_query = urllib.parse.quote(location)
        url = f"https://www.cv-library.co.uk/search-jobs?q={query}&l={loc_query}&r={radius}&posted=90"
        
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        try:
            cookie = await page.query_selector("#cmp-bnty-ok, button:has-text('Accept')")
            if cookie:
                await cookie.click()
        except Exception:
            pass

        job_selector = None
        for sel in [".job__card", "article.job", ".job", ".search-results-list li"]:
            try:
                await page.wait_for_selector(sel, timeout=5000)
                job_selector = sel
                break
            except Exception:
                continue

        if not job_selector:
            logger.warning("CV-Library job cards not found. Fallback search page crawl yielded 0 results.")
            return []

        job_cards = await page.query_selector_all(job_selector)
        
        cards_data = []
        for card in job_cards[:8]:
            try:
                title_el = await card.query_selector(".job__title a, h2 a, h3 a")
                company_el = await card.query_selector(".job__company, .job__company-link")
                location_el = await card.query_selector(".job__location")
                time_el = await card.query_selector(".job__posted")
                type_el = await card.query_selector(".job__type")
                
                title = (await title_el.inner_text()).strip() if title_el else ""
                company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                loc = (await location_el.inner_text()).strip() if location_el else location
                posted = (await time_el.inner_text()).strip() if time_el else "Recent"
                job_type = (await type_el.inner_text()).strip() if type_el else "Permanent"
                
                link = ""
                if title_el:
                    href = await title_el.get_attribute("href")
                    if href:
                        link = f"https://www.cv-library.co.uk{href}" if href.startswith("/") else href

                if title and link:
                    cards_data.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "posted": posted,
                        "job_type": job_type,
                        "link": link
                    })
            except Exception as e:
                logger.error(f"Error parsing CV-Library card metadata in fallback search: {e}")
                continue
                
        # Now visit each link to scrape description
        for data in cards_data:
            try:
                logger.info(f"Navigating to fallback CV-Library page: {data['link']}")
                await page.goto(data["link"], wait_until="domcontentloaded", timeout=15000)
                
                title_el = await page.query_selector("h1")
                title = (await title_el.inner_text()).strip() if title_el else data["title"]
                
                title_lower = title.lower()
                if title_lower == "blocked":
                    logger.warning(f"Discarding fallback CV-Library blocked/invalid page: {data['link']} (Title: {title})")
                    continue
                
                desc_el = await page.query_selector("[itemprop='description'], .job__description, .job-description")
                description = (await desc_el.inner_text()).strip() if desc_el else ""
                
                jobs.append(JobItem(
                    job_title=title,
                    company_name=data["company"],
                    job_website="CV-Library",
                    location=data["location"],
                    date_posted=data["posted"],
                    industry_match=True,
                    job_type=data["job_type"],
                    job_url=data["link"],
                    match_reason=f"Title '{title}' is a strong match for the requested '{job_title}' role within {industry}.",
                    job_description=description
                ))
            except Exception as e:
                logger.error(f"Error scraping description for fallback CV-Library job {data['link']}: {e}")
                # Append even without description as fallback if not blocked
                jobs.append(JobItem(
                    job_title=data["title"],
                    company_name=data["company"],
                    job_website="CV-Library",
                    location=data["location"],
                    date_posted=data["posted"],
                    industry_match=True,
                    job_type=data["job_type"],
                    job_url=data["link"],
                    match_reason=f"Title '{data['title']}' is a strong match for the requested '{job_title}' role within {industry}.",
                    job_description=""
                ))
                
    except Exception as e:
        logger.error(f"CV-Library fallback search failed: {str(e)}")
        raise e
    finally:
        if page:
            await page.close()
            
    return jobs
