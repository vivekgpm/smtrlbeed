from typing import List, Dict, Any, Optional
import pandas as pd
import re

class Normalizer:
    def __init__(self, raw_data: List[List[Any]], test_config: Dict[str, Any]):
        self.raw_data = raw_data
        self.config = test_config

    def normalize(self) -> Dict[str, Any]:
        """
        Converts raw data into Canonical JSON using the test config rules.
        """
        # 1. Extract Metadata (Basic global scan for now)
        meta = self._extract_metadata()
        
        # 2. Extract Tables
        tables = []
        if "extraction_rules" in self.config:
            rules = self.config["extraction_rules"]
            
            if "columns" in rules:
                # Table-based extraction (e.g. Cube)
                table_data = self._extract_table(rules)
                if table_data:
                    tables.append({
                        "title": self.config["name"],
                        "headers": list(table_data[0].keys()) if table_data else [],
                        "rows": table_data
                    })
            elif rules.get("type") == "key_value":
                # Key-Value extraction (e.g. Aggregate)
                kv_data = self._extract_key_values(rules)
                if kv_data:
                     tables.append({
                        "title": self.config["name"],
                        "type": "key_value",
                        "rows": kv_data
                    })

        return {
            "meta": meta,
            "tests": [
                {
                    "test_type": self.config["id"],
                    "tables": tables,
                    "derived": {},
                    "warnings": []
                }
            ]
        }

    def _extract_metadata(self) -> Dict[str, Any]:
        """Scan for common metadata patterns."""
        meta = {
            "report_no": None,
            "date": None,
            "client": None
        }
        
        # Simple heuristic: Look for "Report No" and take next cell
        for i, row in enumerate(self.raw_data):
            for j, cell in enumerate(row):
                cell_str = str(cell).lower().strip()
                if "report no" in cell_str:
                    meta["report_no"] = self._get_next_value(i, j)
                if "date" in cell_str and not meta["date"]:
                    meta["date"] = self._get_next_value(i, j)
                if "client" in cell_str or "agency" in cell_str:
                     meta["client"] = self._get_next_value(i, j)
        return meta

    def _get_next_value(self, r: int, c: int) -> Optional[str]:
        """Get value from same cell (split by :) or next few cells."""
        row = self.raw_data[r]
        cell_str = str(row[c])
        
        if ":" in cell_str:
             parts = cell_str.split(":", 1)
             if len(parts) > 1 and parts[1].strip():
                 return parts[1].strip()
        
        # Check next cells
        for k in range(1, 4):
            if c + k < len(row):
                val = str(row[c+k]).strip()
                if val and val != ":":
                    return val
        return None

    def _extract_table(self, rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extracts tabular data based on column aliases."""
        # Finds header row
        header_row_idx = -1
        col_map = {} # canonical_name -> index

        for i, row in enumerate(self.raw_data):
            row_text = " ".join([str(c).lower() for c in row])
            
            # Check if this row looks like a header
            matches = 0
            temp_map = {}
            for field, aliases in rules["columns"].items():
                for col_idx, cell in enumerate(row):
                    if any(alias.lower() in str(cell).lower() for alias in aliases):
                        temp_map[field] = col_idx
                        matches += 1
                        break
            
            if matches >= 2: # At least 2 columns matched
                header_row_idx = i
                col_map = temp_map
                break
        
        if header_row_idx == -1:
            return []

        # Extract rows
        data = []
        for i in range(header_row_idx + 1, len(self.raw_data)):
            row = self.raw_data[i]
            # Stop condition
            if "table_end_keywords" in rules:
                row_str = " ".join([str(c) for c in row])
                if any(kw.lower() in row_str.lower() for kw in rules["table_end_keywords"]):
                    break
            
            # Skip empty rows
            if not any(str(c).strip() for c in row):
                continue

            entry = {}
            has_data = False
            for field, col_idx in col_map.items():
                if col_idx < len(row):
                    val = row[col_idx]
                    entry[field] = val
                    if str(val).strip(): has_data = True
            
            if has_data:
                data.append(entry)
                
        return data

    def _extract_key_values(self, rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extracts key-value pairs."""
        data = []
        target_keys = [k.lower() for k in rules.get("pairs", [])]
        
        for row in self.raw_data:
            for j, cell in enumerate(row):
                cell_str = str(cell).strip()
                if not cell_str: continue
                
                # Check if cell matches a target key
                match_key = next((k for k in target_keys if k in cell_str.lower()), None)
                
                if match_key:
                    # Look for value in next columns
                    val = self._get_next_value(self.raw_data.index(row), j)
                    if val:
                         # Use original styling/capitalization from config if possible, else cell content
                         data.append({"parameter": cell_str, "value": val})
        return data
