import os
import json
import logging

logger = logging.getLogger(__name__)

class EmployerValidator:
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Locate relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, "..", "..", "data", "agencies.json")
        
        self.agencies = []
        self.keywords = []
        self.load_config(config_path)

    def load_config(self, path: str):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.agencies = [a.lower().strip() for a in data.get("agencies", [])]
                    self.keywords = [k.lower().strip() for k in data.get("keywords", [])]
                logger.info(f"Loaded {len(self.agencies)} agencies and {len(self.keywords)} keywords from {path}")
            else:
                logger.warning(f"Agencies config not found at {path}, using defaults.")
                self._fallback_defaults()
        except Exception as e:
            logger.error(f"Error loading agencies config: {e}. Using defaults.")
            self._fallback_defaults()

    def _fallback_defaults(self):
        self.agencies = ["hays", "reed", "adecco", "michael page", "randstad", "robert half", "manpower"]
        self.keywords = ["recruitment", "staffing", "consultant", "consultants", "consultancy", "agency", "agencies"]

    def is_recruitment_agency(self, company_name: str) -> bool:
        """
        Returns True if the company name indicates it is a recruitment agency.
        """
        if not company_name:
            return False
            
        name_lower = company_name.lower().strip()

        # Check exact matches against agencies list
        for agency in self.agencies:
            if name_lower == agency or name_lower.startswith(agency + " ") or name_lower.endswith(" " + agency):
                return True

        # Check substring matches with keywords
        for keyword in self.keywords:
            # Match word boundaries or broad substring for terms like 'recruitment'
            if keyword in name_lower:
                return True

        return False
