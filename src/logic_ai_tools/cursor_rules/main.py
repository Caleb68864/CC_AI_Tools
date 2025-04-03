import os
import sys
from pathlib import Path

# Add the src directory to the Python path
src_dir = str(Path(__file__).parent.parent.parent)
if src_dir not in sys.path:
    sys.path.append(src_dir)

from cc_ai_tools.cursor_rules.file_operations import get_rules_files, get_project_folder, get_rules_dir
from cc_ai_tools.cursor_rules.gui_manager import select_files
from cc_ai_tools.cursor_rules.rule_manager import copy_rules_to_project
from cc_ai_tools.cursor_rules.project_scanner import ProjectScanner
from cc_ai_tools.utils.interrupt_handler import handle_interrupt

def main():
    # Use current working directory as project folder
    project_folder = get_project_folder()
    
    # Get available rules files
    grouped_files = get_rules_files(project_folder)
    
    # Let user select files
    selected_files = select_files(grouped_files, project_folder)
    if not selected_files:
        return
    
    # Copy selected rules to project
    copy_rules_to_project(selected_files, project_folder)
    
    # After rules are copied, scan the project to update project context
    print("\nScanning project for context...")
    scanner = ProjectScanner(project_folder)
    scanner.scan_project()
    
    print("\nRules have been saved to:", get_rules_dir(project_folder))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        handle_interrupt()