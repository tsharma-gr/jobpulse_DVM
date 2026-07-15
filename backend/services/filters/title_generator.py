import os
import json
import logging
from typing import List
from utils.llm import generate_ai_title_expansions

logger = logging.getLogger(__name__)

def generate_related_titles(job_title: str, industry: str = "") -> List[str]:
    """
    Expands a job title to include common variations.
    Supports logical 'OR' operators to split composite queries.
    """
    import re
    cleaned_title = job_title.strip()
    if not cleaned_title:
        return []

    # Parse OR query into individual titles
    parts = re.split(r'\s+or\s+', cleaned_title, flags=re.IGNORECASE)
    parsed_titles = [p.strip().strip('"').strip("'").strip() for p in parts if p.strip()]
    
    variations = []
    prefixes = ["Senior", "Junior", "Lead", "Assistant", "Associate", "Graduate", "Trainee", "Pre"]
    
    for pt in parsed_titles:
        variations.append(pt)
        pt_lower = pt.lower()
        for prefix in prefixes:
            # Avoid prefixing if it already starts with it
            if not pt_lower.startswith(prefix.lower()):
                variations.append(f"{prefix} {pt}")

    # Try DeepSeek AI first (if API key is present) for the full query
    if industry:
        ai_titles = generate_ai_title_expansions(cleaned_title, industry)
        if ai_titles and len(ai_titles) > 0:
            variations.extend(ai_titles)

    # Deduplicate while preserving case
    seen = set()
    result = []
    for var in variations:
        var_low = var.lower()
        if var_low not in seen:
            seen.add(var_low)
            result.append(var)

    return result
