import os
import urllib.parse
import logging
from typing import List
from models.schemas import JobItem
from services.scrapers.mock_data import generate_mock_jobs
from utils.browser import BrowserManager
from utils.ddg_search import discover_job_urls

logger = logging.getLogger("services.scrapers.indeed")

async def scrape_indeed(job_title: str, industry: str, location: str, radius: int) -> List[JobItem]:
    """
    Scrapes Indeed UK or generates mock jobs if DEMO_MODE=true.
    First attempts URL discovery via DuckDuckGo, falling back to direct search page crawling.
    """
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    if demo_mode:
        logger.info("DEMO_MODE active: returning mock Indeed UK data")
        return generate_mock_jobs(job_title, industry, location, "Indeed")

    logger.info(f"Scraping Indeed UK for {job_title} in {location} (radius {radius})")
    
    # 1. Try DuckDuckGo URL discovery
    urls = discover_job_urls("uk.indeed.com/viewjob", job_title, location, max_results=8)
    
    if urls:
        logger.info(f"Discovered {len(urls)} Indeed UK URLs. Scraping pages...")
        jobs = []
        page = None
        try:
            page = await BrowserManager.new_page()
            for url in urls:
                try:
                    logger.info(f"Scraping Indeed individual job page: {url}")
                    # Use a short timeout per page to avoid getting stuck
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    
                    title_el = await page.query_selector("h1")
                    company_el = await page.query_selector("div.jobsearch-CompanyReview--heading, [data-testid='inline-header-companyname'], div.jobsearch-InlineCompanyRating a")
                    location_el = await page.query_selector("div[data-testid='job-location'], div.jobsearch-JobInfoHeader-subtitle div:last-child")
                    time_el = await page.query_selector("[data-testid='jobsearch-JobMetadataFooter'], .jobsearch-JobMetadataFooter")
                    
                    title = (await title_el.inner_text()).strip() if title_el else ""
                    company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                    loc = (await location_el.inner_text()).strip() if location_el else location
                    
                    # Clean title if it contains company rating suffix
                    if "\n" in title:
                        title = title.split("\n")[0]
                    if "\n" in company:
                        company = company.split("\n")[0]
                        
                    posted = "Recent"
                    if time_el:
                        t_text = (await time_el.inner_text()).strip()
                        if " ago" in t_text.lower() or "posted" in t_text.lower():
                            # Usually Indeed says "Posted 5 days ago" or similar
                            posted = t_text.split("\n")[0]

                    if title:
                        logger.info(f"Extracted Indeed Job: '{title}' at '{company}' (Date: {posted})")
                        jobs.append(JobItem(
                            job_title=title,
                            company_name=company,
                            job_website="Indeed",
                            location=loc,
                            date_posted=posted,
                            industry_match=True,
                            job_type="Permanent",
                            job_url=url,
                            match_reason=f"Title '{title}' is a strong match for the requested '{job_title}' role within {industry}."
                        ))
                except Exception as e:
                    logger.error(f"Error scraping individual Indeed page {url}: {e}")
                    continue
            
            if jobs:
                return jobs
        except Exception as e:
            logger.error(f"Failed scraping Indeed individual URLs: {e}")
        finally:
            if page:
                await page.close()

    # 2. Fallback to direct search page crawling
    logger.info("Falling back to direct search page crawling for Indeed UK...")
    jobs = []
    page = None
    try:
        page = await BrowserManager.new_page()
        query = urllib.parse.quote(job_title)
        loc_query = urllib.parse.quote(location)
        url = f"https://uk.indeed.com/jobs?q={query}&l={loc_query}&radius={radius}&fromage=90"
        
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        try:
            await page.wait_for_selector(".job_seen_beacon", timeout=10000)
        except Exception:
            logger.warning("Indeed card selector (.job_seen_beacon) not found in fallback search page crawl.")
            return []

        job_cards = await page.query_selector_all(".job_seen_beacon")
        
        for card in job_cards[:10]:
            try:
                title_el = await card.query_selector("h2.jobTitle span")
                company_el = await card.query_selector("[data-testid='company-name']")
                location_el = await card.query_selector("[data-testid='text-location']")
                link_el = await card.query_selector("h2.jobTitle a")
                time_el = await card.query_selector("[data-testid='myJobsStateDate']")
                
                title = (await title_el.inner_text()).strip() if title_el else ""
                company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                loc = (await location_el.inner_text()).strip() if location_el else location
                posted = (await time_el.inner_text()).strip() if time_el else "Recent"
                
                link = ""
                if link_el:
                    href = await link_el.get_attribute("href")
                    if href:
                        link = f"https://uk.indeed.com{href}" if href.startswith("/") else href

                if title and link:
                    jobs.append(JobItem(
                        job_title=title,
                        company_name=company,
                        job_website="Indeed",
                        location=loc,
                        date_posted=posted,
                        industry_match=True,
                        job_type="Permanent",
                        job_url=link,
                        match_reason=f"Title '{title}' is a strong match for the requested '{job_title}' role within {industry}."
                    ))
            except Exception as e:
                logger.error(f"Error parsing Indeed card in fallback search: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Indeed UK fallback search failed: {str(e)}")
        raise e
    finally:
        if page:
            await page.close()
            
    return jobs
