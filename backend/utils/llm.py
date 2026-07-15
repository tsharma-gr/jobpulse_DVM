import os
import json
import logging
from typing import List
from models.schemas import JobItem

logger = logging.getLogger(__name__)

def generate_batch_match_reasons(target_title: str, target_industry: str, target_location: str, jobs: List[JobItem]) -> List[JobItem]:
    """
    Takes a list of JobItems and uses DeepSeek via OpenAI SDK to generate a highly contextual,
    intelligent 1-sentence match reason for each job based on the original search criteria.
    Updates the match_reason field on the objects and returns the list.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key or api_key == "your-deepseek-api-key-here" or len(jobs) == 0:
        logger.info("Skipping LLM match reason generation (no API key or no jobs).")
        return jobs

    try:
        from openai import OpenAI
        
        # DeepSeek uses the OpenAI Python SDK architecture
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        
        logger.info(f"Generating LLM match reasons for {len(jobs)} jobs via DeepSeek...")
        
        # Construct the batch payload
        jobs_payload = []
        for i, job in enumerate(jobs):
            jobs_payload.append({
                "id": i,
                "job_title": job.job_title,
                "company_name": job.company_name,
                "job_website": job.job_website
            })
            
        system_prompt = (
            "You are an expert HR analyst verifying job market demand. "
            "Your task is to analyze each provided job posting against a user searching for "
            f"'{target_title}' roles in the '{target_industry}' sector.\n\n"
            "For each job, provide:\n"
            "1. A brief, professional 1-sentence 'reason' explaining why it matches.\n"
            "2. An 'industry_match' string representing the percentage relevance to the requested industry (e.g., '95%', '80%').\n\n"
            "Return ONLY a valid JSON array of objects, where each object has 'reason' and 'industry_match' string properties, "
            "in the exact same order as the provided jobs. Do not include markdown formatting or explanations."
        )
        
        user_prompt = json.dumps(jobs_payload, indent=2)
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"} if False else None # DeepSeek may not strictly support JSON mode in the same way, we rely on prompting
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean markdown formatting if the model still included it
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        content = content.strip()
        
        reasons_data = json.loads(content)
        
        if isinstance(reasons_data, list) and len(reasons_data) == len(jobs):
            for i, job in enumerate(jobs):
                item = reasons_data[i]
                if isinstance(item, dict):
                    job.match_reason = item.get("reason", job.match_reason)
                    job.industry_match = item.get("industry_match", "Unknown")
            logger.info("Successfully mapped LLM generated match reasons and percentages.")
        else:
            logger.warning("LLM returned an invalid array size or format. Falling back to default reasons.")
            
    except Exception as e:
        logger.error(f"Failed to generate LLM match reasons: {e}")
        
    return jobs

def generate_ai_title_expansions(target_title: str, target_industry: str) -> List[str]:
    """
    Uses DeepSeek to generate a JSON array of 5-8 closely related, real-world job titles
    based on the user's input and industry.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key or api_key == "your-deepseek-api-key-here":
        logger.info("Skipping AI title expansion (no API key).")
        return []

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        
        logger.info(f"Generating AI title expansions for '{target_title}' in '{target_industry}' via DeepSeek...")
        
        system_prompt = (
            "You are an expert HR recruiter. The user is searching for job vacancies. "
            f"Their target role is '{target_title}' in the '{target_industry}' industry.\n\n"
            "Return a JSON array of strings containing 5 to 8 closely related, standard industry job titles "
            "that a recruiter would also search for to find candidates for this role. "
            "Ensure the titles are realistic and commonly used on job boards. "
            "Include the original title as the first element. "
            "Return ONLY a valid JSON array. Do not include markdown formatting."
        )
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean markdown formatting if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        content = content.strip()
        
        titles = json.loads(content)
        
        if isinstance(titles, list) and len(titles) > 0:
            logger.info(f"Successfully generated {len(titles)} AI title expansions.")
            return titles
            
    except Exception as e:
        logger.error(f"Failed to generate AI title expansions: {e}")
        
    return []
