import logging
from typing import List
from ddgs import DDGS

logger = logging.getLogger(__name__)

def discover_job_urls(site_domain: str, job_title: str, location: str, max_results: int = 15) -> List[str]:
    """
    Discovers job posting URLs for a specific site domain via DuckDuckGo.
    e.g. site_domain = 'linkedin.com/jobs/view', 'uk.indeed.com/viewjob', 'cv-library.co.uk/job'
    """
    import re
    if " or " in job_title.lower():
        parts = re.split(r'\s+or\s+', job_title, flags=re.IGNORECASE)
        # Limit to first 4 terms to keep query short and robust against bot firewalls
        simplified_terms = [p.strip() for p in parts if p.strip()][:4]
        simplified_title = " OR ".join(simplified_terms)
        query = f'site:{site_domain} ({simplified_title}) "{location}"'
    else:
        query = f'site:{site_domain} "{job_title}" "{location}"'
    logger.info(f"Querying DuckDuckGo for: {query} [timelimit='m' applied]")
    urls = []
    try:
        with DDGS() as ddgs:
            # We fetch up to max_results text items, restricting to the last month ('m')
            results = ddgs.text(query, timelimit='m', max_results=max_results)
            for r in results:
                url = r.get("href")
                if url:
                    # Clean/normalize URL
                    if site_domain in url:
                        urls.append(url)
        logger.info(f"DuckDuckGo discovered {len(urls)} URLs for {site_domain}")
    except Exception as e:
        logger.error(f"DuckDuckGo search failed for query '{query}': {e}")
        
    return urls
