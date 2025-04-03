import os
import glob
from datetime import datetime
from .file_operations import get_rules_dir, get_trash_dir, get_rules_source_dir

def copy_rules_to_project(selected_files, project_folder):
    rules_dir = get_rules_dir(project_folder)
    trash_dir = get_trash_dir(project_folder)
    os.makedirs(rules_dir, exist_ok=True)
    os.makedirs(trash_dir, exist_ok=True)
    
    rules_source_dir = get_rules_source_dir()
    
    # Track added and removed rules
    added_rules = []
    removed_rules = []
    
    # Get list of all existing rule files
    existing_rules = glob.glob(os.path.join(rules_dir, "*.mdc"))
    existing_rule_names = [os.path.basename(r) for r in existing_rules]
    
    # Move unselected rules to trash with timestamp prefix
    for rule_path in existing_rules:
        rule_name = os.path.basename(rule_path)
        if not any(os.path.basename(f) == rule_name for f in selected_files):
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_UTC_")
            trash_name = timestamp + rule_name
            trash_path = os.path.join(trash_dir, trash_name)
            os.rename(rule_path, trash_path)
            removed_rules.append(rule_name)
    
    # Copy selected rules
    for file in selected_files:
        file_name = os.path.basename(file)
        dest_path = os.path.join(rules_dir, file_name)
        
        # Skip project-context.mdc as it's handled separately by the scanner
        if file_name == "project-context.mdc":
            continue
            
        source_path = os.path.join(rules_source_dir, file)
        
        # Only count as added if it's a new file
        if file_name not in existing_rule_names:
            added_rules.append(file_name)
            
        with open(source_path, 'r', encoding='utf-8') as source:
            with open(dest_path, 'w', encoding='utf-8') as dest:
                dest.write(source.read())
    
    # Ensure essential files are included
    essential_files = [
        "cursor-rule-format.mdc",
        "cursor-rules-location.mdc"
    ]
    
    for file in essential_files:
        source_path = os.path.join(rules_source_dir, file)
        # Save file to project
        dest_path = os.path.join(rules_dir, file)
        
        # Copy essential file if it exists in source
        if os.path.exists(source_path):
            with open(source_path, 'r', encoding='utf-8') as source:
                with open(dest_path, 'w', encoding='utf-8') as dest:
                    dest.write(source.read())
            
            # Add to added_rules if it's new
            if file not in existing_rule_names and file not in added_rules:
                added_rules.append(file)
    
    # Print summary
    print(f"\nRules copied successfully to: {rules_dir}")
    if added_rules:
        print("\nAdded rules:")
        for rule in added_rules:
            print(f"  • {rule}")
    if removed_rules:
        print("\nRemoved rules:")
        for rule in removed_rules:
            print(f"  • {rule}")
    if not (added_rules or removed_rules):
        print("\nNo changes to rules") 