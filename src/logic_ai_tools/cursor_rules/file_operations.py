import os
import glob
from datetime import datetime

def get_rules_files(project_folder=None):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rules_dir = os.path.join(script_dir, "Rules")
    
    # Get existing rules in project if project_folder is provided
    existing_rules = set()
    if project_folder:
        project_rules_dir = get_rules_dir(project_folder)
        if os.path.exists(project_rules_dir):
            for file in glob.glob(os.path.join(project_rules_dir, "*.mdc")):
                basename = os.path.basename(file)
                existing_rules.add(basename)
    
    rules_files = []
    essential_files = {"cursor-rule-format.mdc", "cursor-rules-location.mdc"}
    
    # Walk through all subdirectories
    for root, _, files in os.walk(rules_dir):
        for file in files:
            if file.endswith(".mdc") and file not in essential_files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, rules_dir)
                # Add metadata about whether the rule exists in the project
                rules_files.append({
                    'path': rel_path,
                    'exists': file in existing_rules
                })
    
    # Group files by directory
    grouped_files = {}
    for file_info in rules_files:
        directory = os.path.dirname(file_info['path']) or "Root"
        if directory not in grouped_files:
            grouped_files[directory] = []
        # Include both path and exists flag in the grouped files
        grouped_files[directory].append({
            'path': file_info['path'],
            'exists': file_info['exists']
        })
    
    return grouped_files

def get_project_folder():
    return os.getcwd()

def get_rules_dir(project_folder):
    return os.path.join(project_folder, ".cursor", "rules")

def get_trash_dir(project_folder):
    return os.path.join(project_folder, ".cursor", ".trash")

def get_rules_source_dir():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "Rules") 