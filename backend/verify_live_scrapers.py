import os
import asyncio
import sys

# Ensure backend folder is in Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Force Live Mode
os.environ["DEMO_MODE"] = "false"
os.environ["HEADLESS"] = "true"

from api.routes import run_search_pipeline
from utils.browser import BrowserManager

async def test_live_search():
    print("Initializing Live Scrapers Verification...")
    print("Search Parameters: 'Estimator', 'Construction', 'London', 25 miles")
    print("Please wait, executing concurrent Playwright scrape...")
    
    try:
        jobs, warnings, counts = await run_search_pipeline(
            job_title="Estimator",
            industry="Construction",
            location="London",
            radius=25
        )
        
        print("\n=== SEARCH RESULTS ===")
        print(f"Total jobs found before filtering: {counts.get('total_before_filters', 0)}")
        print(f"Total jobs found after filters (agency & duplicates): {counts.get('total_after_filters', 0)}")
        print(f"LinkedIn: {counts.get('linkedin', 0)} found")
        print(f"Indeed UK: {counts.get('indeed', 0)} found")
        print(f"CV-Library: {counts.get('cvlibrary', 0)} found")
        
        print("\n=== SYSTEM WARNINGS ===")
        for warning in warnings:
            print(f"- {warning}")
            
        print("\n=== SAMPLE RUN OUTPUT (Top 5 Jobs) ===")
        for i, job in enumerate(jobs[:5]):
            print(f"{i+1}. {job.job_title} at {job.company_name} ({job.job_website})")
            print(f"   Location: {job.location} | Date: {job.date_posted}")
            print(f"   URL: {job.job_url[:80]}...")
            print(f"   Reason: {job.match_reason}")
            print("-" * 50)
            
    except Exception as e:
        print(f"\nCRITICAL PIPELINE ERROR: {e}")
    finally:
        await BrowserManager.close_browser()

if __name__ == "__main__":
    asyncio.run(test_live_search())
