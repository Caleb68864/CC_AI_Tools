import yaml

def load_yaml(file_path):
    """Load YAML data from a file."""
    with open(file_path, 'r') as file:
        return yaml.safe_load(file) or {}

def save_yaml(data, file_path):
    """Save data to a YAML file."""
    with open(file_path, 'w') as file:
        yaml.dump(data, file)

def parse_yaml_response(text):
    """Parse the YAML-style response into a structured format."""
    result = {
        "title": "Default Title",  # Initialize with a default value
        "summary": "",
        "details": [],
        "files_changed": [],
        "impact": "LOW",
        "type": "unknown",  # Add default value for 'type'
        "scope": "unknown"  # Add default value for 'scope'
    }
    
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
            result["type"] = line.split(':', 1)[1].strip()  # Ensure 'type' is set
        elif line.startswith('Scope:'):
            result["scope"] = line.split(':', 1)[1].strip()  # Ensure 'scope' is set
        elif line.startswith('- '):  # File entries
            result['files_changed'].append(line[2:].strip())
    
    return result 