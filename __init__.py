"""
CC AI Tools - Productivity Tools Using AI
"""

__version__ = "0.1.0"

# Import the main functions to make them available at package level
from .git.commit_msg import create_git_commit_msg
from .git.branch_name import create_git_branch_name
from .git.progress_report import create_git_progress_report
from .cursor_rules.main import main as apply_cursor_rules

__all__ = [
    "create_git_commit_msg",
    "create_git_branch_name",
    "create_git_progress_report",
    "apply_cursor_rules"
]
