import json
import os
from typing import List, Dict, Any

class TestDetector:
    def __init__(self, config_path: str = "config/test_definitions.json"):
        with open(config_path, "r") as f:
            self.config = json.load(f)

    def detect_test_type(self, rows: List[List[str]]) -> Dict[str, Any]:
        """
        Scans rows and determines which test type is most likely present.
        Returns the config object for the winning test type and a confidence score.
        """
        best_match = None
        highest_score = 0
        
        flat_text = " ".join([" ".join(row) for row in rows]).lower()

        for test_type in self.config["test_types"]:
            score = 0
            
            # 1. Keyword scoring
            for keyword in test_type["signatures"]["keywords"]:
                if keyword.lower() in flat_text:
                    score += 10
            
            # 2. Column header scoring (checking if known headers exist in any row)
            # This is a bit expensive, simplified for now
            if "required_columns" in test_type["signatures"]:
                for req_col in test_type["signatures"]["required_columns"]:
                    if req_col.lower() in flat_text:
                        score += 5

            if score > highest_score:
                highest_score = score
                best_match = test_type

        return {
            "test_type": best_match,
            "confidence": highest_score
        }
