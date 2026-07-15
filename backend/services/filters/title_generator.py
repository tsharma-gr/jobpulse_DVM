import os
import json
import logging
from typing import List
from utils.llm import generate_ai_title_expansions

logger = logging.getLogger(__name__)

def generate_related_titles(job_title: str, industry: str = "") -> List[str]:
    """
    Expands a job title to include common variations.
    Loads variations dynamically from data/titles.json, falling back to rule-based generation.
    """
    cleaned_title = job_title.strip()
    if not cleaned_title:
        return []

    # 1. Try DeepSeek AI first (if API key is present)
    if industry:
        ai_titles = generate_ai_title_expansions(cleaned_title, industry)
        if ai_titles and len(ai_titles) > 0:
            return ai_titles

    # Try loading from titles.json
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "..", "..", "data", "titles.json")
    
    exact_maps = {}
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                exact_maps = json.load(f)
        else:
            logger.warning(f"Titles expansion config not found at {config_path}")
    except Exception as e:
        logger.error(f"Error loading titles config: {e}")

    # Standardize lookup key
    lower_title = cleaned_title.lower()
    
    # Try finding exact matching list or key contains match
    for key, variations in exact_maps.items():
        if lower_title == key.lower():
            return variations

    # Rule-based fallback expansion if no match found in config
    variations = [cleaned_title]
    prefixes = ["Senior", "Junior", "Lead", "Assistant", "Associate", "Graduate", "Trainee"]
    suffixes = ["Manager", "Specialist", "Engineer", "Analyst"]

    for prefix in prefixes:
        variations.append(f"{prefix} {cleaned_title}")
    
    for suffix in suffixes:
        if suffix.lower() not in lower_title:
            variations.append(f"{cleaned_title} {suffix}")

    return list(dict.fromkeys(variations))
