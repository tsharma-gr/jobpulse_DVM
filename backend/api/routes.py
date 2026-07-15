import io
import os
import json
import asyncio
import logging
import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, Response
from models.schemas import SearchRequest, JobItem
from services.filters.title_generator import generate_related_titles
from services.filters.employer_validator import EmployerValidator
from services.filters.deduplicator import deduplicate_jobs
from services.scrapers.linkedin import scrape_linkedin
from services.scrapers.indeed import scrape_indeed
from services.scrapers.cvlibrary import scrape_cvlibrary
from utils.llm import generate_batch_match_reasons

router = APIRouter()
logger = logging.getLogger(__name__)
employer_validator = EmployerValidator()

async def run_search_pipeline(job_title: str, industry: str, location: str, radius: int, expanded_titles: list = None):
    """
    Orchestrates the search pipeline:
    1. Title expansion
    2. Concurrent Scraping (LinkedIn, Indeed, CV-Library)
    3. Filtering (recruitment agencies, duplicate removal)
    4. Sorting by newest
    """
    # 1. Expand Job Titles
    if not expanded_titles:
        expanded_titles = generate_related_titles(job_title, industry)
    lower_expanded_titles = [t.lower() for t in expanded_titles]
    
    # 2. Concurrently scrape LinkedIn, Indeed UK, and CV-Library
    warnings = []
    
    tasks = [
        scrape_linkedin(job_title, industry, location, radius),
        scrape_indeed(job_title, industry, location, radius),
        scrape_cvlibrary(job_title, industry, location, radius)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    linkedin_jobs = []
    indeed_jobs = []
    cvlibrary_jobs = []
    
    # Check LinkedIn result
    if isinstance(results[0], Exception):
        warnings.append("LinkedIn search is temporarily unavailable.")
        logger.error(f"LinkedIn scraper error: {results[0]}")
    else:
        linkedin_jobs = results[0]
        
    # Check Indeed result
    if isinstance(results[1], Exception):
        warnings.append("Indeed UK search is temporarily unavailable.")
        logger.error(f"Indeed scraper error: {results[1]}")
    else:
        indeed_jobs = results[1]
        
    # Check CV-Library result
    if isinstance(results[2], Exception):
        warnings.append("CV-Library search is temporarily unavailable.")
        logger.error(f"CV-Library scraper error: {results[2]}")
    else:
        cvlibrary_jobs = results[2]

    # Calculate detailed platform statistics before merging
    platform_stats = {}
    for platform, platform_jobs, result in [
        ("linkedin", linkedin_jobs, results[0]),
        ("indeed", indeed_jobs, results[1]),
        ("cvlibrary", cvlibrary_jobs, results[2])
    ]:
        if isinstance(result, Exception):
            err_msg = str(result)
            status_msg = "Blocked or unavailable"
            if "Timeout" in err_msg:
                status_msg = "Timeout exceeded"
            elif "Executable doesn't exist" in err_msg:
                status_msg = "Browser initialization error"
            
            platform_stats[platform] = {
                "found": 0,
                "valid": 0,
                "removed": 0,
                "status": "failed",
                "message": status_msg
            }
        else:
            # Filter matches by title expansion
            title_ok = []
            for j in platform_jobs:
                job_title_lower = j.job_title.lower()
                matched = False
                for exp in lower_expanded_titles:
                    if exp in job_title_lower or job_title_lower in exp:
                        matched = True
                        break
                if matched:
                    title_ok.append(j)

            # Filter recruitment agencies
            agency_ok = []
            agency_removed = 0
            for j in title_ok:
                if not employer_validator.is_recruitment_agency(j.company_name):
                    agency_ok.append(j)
                else:
                    agency_removed += 1
            
            removed_count = (len(platform_jobs) - len(title_ok)) + agency_removed
            
            platform_stats[platform] = {
                "found": len(platform_jobs),
                "valid": len(agency_ok),
                "removed": removed_count,
                "status": "success" if len(platform_jobs) > 0 else "no_results",
                "message": "Scraped successfully." if len(platform_jobs) > 0 else "No matching jobs found."
            }

    raw_jobs = linkedin_jobs + indeed_jobs + cvlibrary_jobs
    
    # 3. Apply Filters
    # Filter by Title Expansion
    title_matched_jobs = []
    for job in raw_jobs:
        job_title_lower = job.job_title.lower()
        matched = False
        for exp in lower_expanded_titles:
            if exp in job_title_lower or job_title_lower in exp:
                matched = True
                break
        if matched:
            title_matched_jobs.append(job)

    # Filter out Recruitment Agencies, Non-Permanent Roles, and Old Jobs
    direct_jobs = []
    non_permanent_keywords = ["contract", "temporary", "temp", "interim", "freelance", "fixed term"]
    
    import re
    def is_older_than_3_months(date_str: str) -> bool:
        ds = date_str.lower()
        if "year" in ds or "yr" in ds:
            return True
            
        # Catch months > 3
        match_months = re.search(r'(\d+)\s*month', ds)
        if match_months and int(match_months.group(1)) > 3:
            return True
            
        # Catch weeks > 12
        match_weeks = re.search(r'(\d+)\s*week', ds)
        if match_weeks and int(match_weeks.group(1)) > 12:
            return True
            
        # Catch days > 90
        match_days = re.search(r'(\d+)\s*day', ds)
        if match_days and int(match_days.group(1)) > 90:
            return True
            
        return False
        
    for job in title_matched_jobs:
        # Check if it's an agency
        if employer_validator.is_recruitment_agency(job.company_name):
            logger.info(f"Filtered out recruitment agency: {job.company_name} for job {job.job_title}")
            continue
            
        # Check if it's explicitly non-permanent in title or job_type
        title_lower = job.job_title.lower()
        type_lower = job.job_type.lower() if job.job_type else ""
        
        # Check if the page was actually blocked by Cloudflare or a Login wall
        blocked_keywords = ["blocked", "additional verification required", "join linkedin", "security measure", "captcha"]
        if any(b in title_lower for b in blocked_keywords):
            logger.info(f"Filtered out blocked/failed scrape job: {job.job_title}")
            continue
            
        is_contract = any(kw in title_lower or kw in type_lower for kw in non_permanent_keywords)
        if is_contract:
            logger.info(f"Filtered out non-permanent job: {job.job_title} ({job.job_type})")
            continue
            
        # Check if it's strictly older than 3 months
        if is_older_than_3_months(job.date_posted):
            logger.info(f"Filtered out old job: {job.job_title} ({job.date_posted})")
            continue
            
        # If it passes, force standardize it to Permanent
        job.job_type = "Permanent"
        direct_jobs.append(job)
            
    # Deduplicate
    deduplicated = deduplicate_jobs(direct_jobs)
    
    # Sort by date (newest first)
    sorted_jobs = sorted(
        deduplicated,
        key=lambda x: x.date_posted,
        reverse=True
    )
    
    # Send all valid jobs to LLM to generate intelligent match reasons
    sorted_jobs = generate_batch_match_reasons(job_title, industry, location, sorted_jobs)
    
    # Pack platform statistics in counts
    counts = {
        "linkedin": platform_stats["linkedin"],
        "indeed": platform_stats["indeed"],
        "cvlibrary": platform_stats["cvlibrary"],
        "total_before_filters": len(raw_jobs),
        "total_after_filters": len(sorted_jobs)
    }
    
    return sorted_jobs, warnings, counts

@router.post("/search")
async def search_endpoint(request: SearchRequest):
    """
    Streams search progress, findings, warnings, and finally the results.
    """
    async def progress_stream():
        try:
            # Step 1: Validation
            yield json.dumps({"step": "validate", "message": "Validating search criteria..."}) + "\n"
            await asyncio.sleep(0.3)
            
            # Step 2: Title expansion
            yield json.dumps({"step": "titles", "message": "Generating related job titles..."}) + "\n"
            expanded = generate_related_titles(request.job_title, request.industry)
            yield json.dumps({
                "step": "titles_list", 
                "message": f"Expanded to: {', '.join(expanded[:4])}...",
                "expanded": expanded
            }) + "\n"
            await asyncio.sleep(0.3)
            
            # Step 3: Scraping
            yield json.dumps({"step": "scraping", "message": "Searching LinkedIn, Indeed, and CV-Library UK concurrently..."}) + "\n"
            
            jobs, warnings, counts = await run_search_pipeline(
                request.job_title, request.industry, request.location, request.radius, expanded
            )
            
            yield json.dumps({
                "step": "scraped_counts",
                "message": f"LinkedIn: {counts['linkedin']['found']} found, Indeed: {counts['indeed']['found']} found, CV-Library: {counts['cvlibrary']['found']} found",
                "counts": counts
            }) + "\n"
            await asyncio.sleep(0.3)

            # Step 4: Filtering
            yield json.dumps({"step": "filtering", "message": "Removing duplicates and filtering recruitment agencies..."}) + "\n"
            await asyncio.sleep(0.3)
            
            # Send final results
            logger.info(f"Sending completed step with {len(jobs)} jobs to the frontend.")
            yield json.dumps({
                "step": "completed",
                "message": "Search completed.",
                "jobs": [job.model_dump() for job in jobs],
                "warnings": warnings
            }) + "\n"
            
        except Exception as e:
            logger.error(f"Error in search stream: {e}")
            yield json.dumps({"step": "error", "message": f"Search failed: {str(e)}"}) + "\n"

    return StreamingResponse(progress_stream(), media_type="text/event-stream")

@router.post("/bulk-search")
async def bulk_search_endpoint(file: UploadFile = File(...)):
    """
    Streams progress row-by-row and finishes with combined job results.
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid Excel file format.")
        
    contents = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse Excel: {str(e)}")

    # Standardize columns
    required_cols = ["job title", "industry", "location", "radius"]
    col_mapping = {col.lower().strip(): col for col in df.columns}
    
    missing = [c for c in required_cols if c not in col_mapping]
    if missing:
        raise HTTPException(
            status_code=400, 
            detail=f"Excel file missing required columns: {', '.join(missing)}"
        )

    rows = df.to_dict(orient="records")
    total_rows = len(rows)

    async def bulk_progress_stream():
        all_jobs = []
        all_warnings = []
        success_count = 0
        failure_count = 0
        
        yield json.dumps({"step": "init", "message": f"Parsed Excel file. Found {total_rows} rows to process."}) + "\n"
        await asyncio.sleep(0.5)

        for index, row in enumerate(rows):
            row_num = index + 1
            
            # Extract values dynamically
            title = row.get(col_mapping["job title"])
            industry = row.get(col_mapping["industry"], "General")
            location = row.get(col_mapping["location"])
            radius_val = row.get(col_mapping["radius"], 25)
            
            # Clean radius
            try:
                radius = int(radius_val)
            except ValueError:
                radius = 25

            if not title or not location:
                failure_count += 1
                yield json.dumps({
                    "step": "row_skipped",
                    "message": f"Row {row_num}/{total_rows}: Missing Job Title or Location. Skipped."
                }) + "\n"
                continue

            yield json.dumps({
                "step": "row_start",
                "message": f"Processing row {row_num} of {total_rows} ({title} in {location})...",
                "progress": {"current": row_num, "total": total_rows}
            }) + "\n"

            try:
                jobs, warnings, counts = await run_search_pipeline(
                    str(title), str(industry), str(location), radius
                )
                
                # Append row index details to each job
                for job in jobs:
                    job.match_reason += f" (From bulk row: {title} in {location})"
                    all_jobs.append(job)
                    
                for warning in warnings:
                    all_warnings.append(f"Row {row_num} ({title}): {warning}")

                success_count += 1
                yield json.dumps({
                    "step": "row_complete",
                    "message": f"Row {row_num} complete. Found {len(jobs)} jobs.",
                    "jobs_count": len(jobs)
                }) + "\n"

            except Exception as e:
                failure_count += 1
                logger.error(f"Error processing row {row_num}: {e}")
                yield json.dumps({
                    "step": "row_failed",
                    "message": f"Row {row_num} failed: {str(e)}. Continuing..."
                }) + "\n"

        # Unique sorting
        final_jobs = deduplicate_jobs(all_jobs)
        final_jobs = sorted(final_jobs, key=lambda x: x.date_posted, reverse=True)
        final_warnings = list(set(all_warnings))

        yield json.dumps({
            "step": "completed",
            "message": f"Bulk search completed. {success_count} succeeded, {failure_count} failed.",
            "success_count": success_count,
            "failure_count": failure_count,
            "jobs": [job.model_dump() for job in final_jobs],
            "warnings": final_warnings
        }) + "\n"

    return StreamingResponse(bulk_progress_stream(), media_type="text/event-stream")

@router.get("/bulk-template")
async def bulk_template_endpoint():
    """
    Generates and returns the Excel template file.
    """
    output = io.BytesIO()
    df = pd.DataFrame(columns=["Job Title", "Industry", "Location", "Radius"])
    
    # Add a sample row
    df.loc[0] = ["Estimator", "Construction", "London", 25]
    df.loc[1] = ["Software Engineer", "Technology", "Manchester", 15]

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Template")
        
    output.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="JobPulse_Bulk_Template.xlsx"'
    }
    return Response(
        output.getvalue(), 
        headers=headers, 
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
