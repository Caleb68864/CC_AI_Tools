"""
YAML Utilities
-------------
Functions for parsing and formatting YAML data.

Features:
- Structured data parsing
- Response formatting
- Error handling
- File I/O operations
"""

import yaml
from typing import Dict, Any, Optional, List

def load_yaml(file_path: str) -> Dict[str, Any]:
    """
    Load YAML data from a file.
    
    Args:
        file_path: Path to the YAML file
        
    Returns:
        Dict containing the YAML data, or empty dict if file is empty
    """
    with open(file_path, 'r') as file:
        return yaml.safe_load(file) or {}

def save_yaml(data: Dict[str, Any], file_path: str) -> None:
    """
    Save data to a YAML file.
    
    Args:
        data: Dictionary to save as YAML
        file_path: Path where to save the file
    """
    with open(file_path, 'w') as file:
        yaml.dump(data, file)

def parse_yaml_response(text: str) -> Dict[str, Any]:
    """
    Parse the YAML-style response into a structured format.
    
    Args:
        text: YAML-formatted string to parse
        
    Returns:
        Dictionary containing parsed data with default values for missing fields
    """
    result = {
        "title": "Default Title",
        "summary": "",
        "details": [],
        "files_changed": [],
        "impact": "LOW",
        "type": "unknown",
        "scope": "unknown"
    }
    
    try:
        # First try to parse as proper YAML
        parsed = yaml.safe_load(text)
        if isinstance(parsed, dict):
            result.update(parsed)
            return result
    except yaml.YAMLError:
        # If not valid YAML, fall back to line-by-line parsing
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('title:'):
                result["title"] = line.split(':', 1)[1].strip()
            elif line.startswith('summary:'):
                result["summary"] = line.split(':', 1)[1].strip()
            elif line.startswith('details:'):
                result["details"].append(line.split(':', 1)[1].strip())
            elif line.startswith('Impact:'):
                result["impact"] = line.split(':', 1)[1].strip().upper()
            elif line.startswith('Type:'):
                result["type"] = line.split(':', 1)[1].strip()
            elif line.startswith('Scope:'):
                result["scope"] = line.split(':', 1)[1].strip()
            elif line.startswith('- '):  # File entries
                result['files_changed'].append(line[2:].strip())
    
    return result

# ... rest of the utility functions ... 