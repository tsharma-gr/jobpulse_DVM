import datetime
import random
from typing import List
from models.schemas import JobItem

MOCK_COMPANIES = {
    "construction": [
        "Morgan Sindall", "Balfour Beatty", "Kier Group", "Laing O'Rourke", 
        "Mace Group", "Galliford Try", "Wates Group", "Willmott Dixon", "Sir Robert McAlpine"
    ],
    "technology": [
        "Monzo Bank", "Revolut", "Arm Holdings", "Deliveroo", "Wise", 
        "DeepMind", "Sage Group", "Darktrace", "Skyscanner", "Graphcore"
    ],
    "finance": [
        "Barclays", "HSBC UK", "Lloyds Banking Group", "NatWest Group",
        "Schroders", "Aviva", "Legal & General", "Standard Chartered"
    ],
    "general": [
        "Tesco", "Sainsbury's", "Marks & Spencer", "NHS England", 
        "BP", "Shell", "AstraZeneca", "GlaxoSmithKline", "Rolls-Royce"
    ]
}

def generate_mock_jobs(job_title: str, industry: str, location: str, website: str) -> List[JobItem]:
    """
    Generates realistic looking mock job vacancies for a search query.
    """
    ind_key = industry.lower()
    companies = MOCK_COMPANIES.get("general")
    if "construct" in ind_key:
        companies = MOCK_COMPANIES.get("construction")
    elif "tech" in ind_key or "software" in ind_key or "it" in ind_key:
        companies = MOCK_COMPANIES.get("technology")
    elif "finance" in ind_key or "bank" in ind_key or "invest" in ind_key:
        companies = MOCK_COMPANIES.get("finance")

    # Generate titles based on input
    title_variations = [
        f"{job_title}",
        f"Senior {job_title}",
        f"Assistant {job_title}",
        f"Lead {job_title}",
        f"Graduate {job_title}",
        f"Commercial {job_title}"
    ]

    jobs = []
    num_jobs = random.randint(3, 8)
    
    for i in range(num_jobs):
        title = random.choice(title_variations)
        company = random.choice(companies)
        
        # Ensure some agency names are generated to test agency filtering
        if i == 0:
            company = f"Hays {industry} Recruitment"
        elif i == 1:
            company = f"Reed Specialist Recruitment"

        days_ago = random.randint(1, 45)
        post_date = (datetime.date.today() - datetime.timedelta(days=days_ago)).isoformat()
        
        job_id = random.randint(1000000, 9999999)
        if website.lower() == "linkedin":
            url = f"https://www.linkedin.com/jobs/view/{job_id}"
        elif website.lower() == "indeed":
            url = f"https://www.indeed.com/viewjob?jk=mock{job_id}"
        else:
            url = f"https://www.cv-library.co.uk/job/{job_id}/mock-job"

        job_type = random.choice(["Full-time", "Permanent", "Contract", "Part-time"])

        jobs.append(JobItem(
            job_title=title,
            company_name=company,
            job_website=website,
            location=f"{location}, UK",
            date_posted=post_date,
            industry_match=True,
            job_type=job_type,
            job_url=url,
            match_reason=f"Matches title '{title}' and location '{location}' within {industry}.",
            job_description=f"We are looking for a {title} with expertise in the {industry} sector. The responsibilities of this role include managing project demands, collaborating with teams, and executing key deliverables within {industry}."
        ))

    return jobs
