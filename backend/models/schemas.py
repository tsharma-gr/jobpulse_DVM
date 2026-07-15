from pydantic import BaseModel, Field
from typing import List, Optional, Union

class SearchRequest(BaseModel):
    job_title: str = Field(..., description="Job Title to search for, e.g. Estimator")
    industry: str = Field(..., description="Industry or Sector, e.g. Construction")
    location: str = Field(..., description="Location to search in, e.g. London")
    radius: int = Field(25, description="Search radius in miles, e.g. 25")

class JobItem(BaseModel):
    job_title: str
    company_name: str
    job_website: str
    location: str
    date_posted: str
    industry_match: Union[str, bool]
    job_type: Optional[str] = "Permanent"
    job_url: str
    match_reason: str
    job_description: Optional[str] = ""

class SearchResponse(BaseModel):
    jobs: List[JobItem]
    warnings: List[str] = []

class ProgressUpdate(BaseModel):
    step: str
    message: str
    jobs_found: Optional[dict] = None  # e.g., {"linkedin": 5, "indeed": 10, "cvlibrary": 2}
