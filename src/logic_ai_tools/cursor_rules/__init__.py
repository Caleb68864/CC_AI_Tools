"""
Cursor Rules package for managing and applying rules in projects.
"""

from .main import main
from .file_operations import get_rules_files, get_project_folder
from .gui_manager import select_files
from .rule_manager import copy_rules_to_project
from .project_scanner import ProjectScanner
from .profiles import ProjectType, get_profile

__version__ = '0.1.0'

__all__ = [
    'main',
    'get_rules_files',
    'get_project_folder',
    'select_files',
    'copy_rules_to_project',
    'ProjectScanner',
    'ProjectType',
    'get_profile'
]
