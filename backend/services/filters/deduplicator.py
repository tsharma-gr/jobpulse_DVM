import re
from typing import List
from models.schemas import JobItem

def _normalize(text: str) -> str:
    if not text:
        return ""
    # Lowercase, remove special characters and extra spaces
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return " ".join(text.split())

def deduplicate_jobs(jobs: List[JobItem]) -> List[JobItem]:
    """
    Deduplicates a list of job postings.
    Keeps the first occurrence.
    Matches duplicates based on:
    - Exact URL match
    - Similarity of Normalized Title + Normalized Company + Normalized Location
    """
    seen_urls = set()
    seen_keys = set()
    unique_jobs = []

    for job in jobs:
        # Check URL
        url_normalized = job.job_url.split("?")[0].strip().lower()  # strip query parameters
        if url_normalized in seen_urls:
            continue
            
        # Check key components
        norm_title = _normalize(job.job_title)
        norm_company = _normalize(job.company_name)
        norm_loc = _normalize(job.location)
        
        # Simple compound key
        key = (norm_title, norm_company, norm_loc)
        
        # We can also check if a similar key exists (e.g. subset of location/title)
        # For simplicity and reliability, matching exact normalized key is highly effective
        if key in seen_keys:
            continue
            
        seen_urls.add(url_normalized)
        seen_keys.add(key)
        unique_jobs.append(job)

    return unique_jobs
