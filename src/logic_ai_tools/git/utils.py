"""
Git Utility Functions
-------------------
Common git operations used across the tools.

Provides standardized interfaces for:
- Repository access
- Branch operations
- Commit operations
- Diff analysis
"""

import os
import git
import subprocess
from datetime import datetime
from typing import List, Dict, Optional, Union

def get_repo(path: str = ".") -> git.Repo:
    """Get git repository instance."""
    try:
        return git.Repo(path)
    except git.InvalidGitRepositoryError:
        raise Exception("Not a valid git repository")

def get_current_branch() -> str:
    """Get current git branch name."""
    repo = get_repo()
    return repo.active_branch.name

def stage_all_changes():
    """
    Stage all changes in the repository.
    """
    subprocess.run(["git", "add", "."])

def get_diff_files(branch_or_option):
    """
    Return the list of files that have changes compared to the provided branch or option.
    
    Args:
        branch_or_option: Branch name or git option (e.g., "--cached")
        
    Returns:
        String containing the list of changed files
    """
    try:
        if branch_or_option == "--cached":
            files = subprocess.check_output(["git", "diff", "--cached", "--name-only"]).decode("utf-8")
        else:
            files = subprocess.check_output(["git", "diff", "--name-only", branch_or_option]).decode("utf-8")
        return files.strip()
    except subprocess.CalledProcessError:
        return ""

def get_diff_output(branch_or_option):
    """
    Return the diff output compared to the provided branch or option.
    
    Args:
        branch_or_option: Branch name or git option (e.g., "--cached")
        
    Returns:
        String containing the diff output
    """
    try:
        if branch_or_option == "--cached":
            diff_output = subprocess.check_output(["git", "diff", "--cached"]).decode("utf-8", errors="replace")
        else:
            diff_output = subprocess.check_output(["git", "diff", branch_or_option]).decode("utf-8", errors="replace")
        return diff_output.strip()
    except subprocess.CalledProcessError:
        return ""

def commit_changes(commit_message):
    """
    Commit the staged changes using the provided commit message.
    """
    subprocess.run(["git", "commit", "-m", commit_message])

def push_changes():
    """Push changes to remote repository"""
    current_branch = get_current_branch()
    try:
        # Try to push normally first
        subprocess.run(['git', 'push'], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        # If normal push fails, try pushing with --set-upstream
        subprocess.run(['git', 'push', '--set-upstream', 'origin', current_branch], check=True, capture_output=True, text=True)

def create_new_branch(branch_name):
    """
    Create a new branch with the given name and check it out.
    """
    repo = get_repo()
    if branch_name in repo.heads:
        raise Exception(f"Branch '{branch_name}' already exists!")
    new_branch = repo.create_head(branch_name)
    new_branch.checkout()
    return branch_name

def list_recent_commits(branch, count=5):
    """
    Return the last 'count' commits from the given branch as a list.
    """
    repo = get_repo()
    return list(repo.iter_commits(branch, max_count=count))

def get_commit_history(start_date: Optional[datetime] = None, 
                      end_date: Optional[datetime] = None, 
                      branch: Optional[str] = None) -> List[Dict]:
    """
    Get commit history within the specified date range.
    
    Args:
        start_date: Start date for commit range (optional)
        end_date: End date for commit range (optional)
        branch: Branch to get commits from (optional, defaults to current branch)
    
    Returns:
        List of commit dictionaries with metadata
    """
    repo = get_repo()
    if branch is None:
        branch = get_current_branch()

    # Build the git log command
    cmd = ['git', 'log', '--pretty=format:%H|%an|%at|%s']
    
    if start_date:
        cmd.append(f'--since={start_date.strftime("%Y-%m-%d")}')
    if end_date:
        cmd.append(f'--until={end_date.strftime("%Y-%m-%d")}')
    
    cmd.append(branch)

    try:
        output = subprocess.check_output(cmd, text=True)
        commits = []
        
        for line in output.split('\n'):
            if line.strip():
                hash_id, author, timestamp, message = line.split('|')
                commits.append({
                    'hash': hash_id,
                    'author': author,
                    'date': datetime.fromtimestamp(int(timestamp)),
                    'message': message
                })
        
        return commits
    except subprocess.CalledProcessError:
        return []

def get_commit_details(commit_hash: str) -> Dict[str, str]:
    """
    Get detailed information about a specific commit.
    
    Args:
        commit_hash: The hash of the commit to get details for
        
    Returns:
        Dictionary containing commit details (hash, author, date, message, and changes)
    """
    try:
        # Get commit message and metadata
        cmd_message = ['git', 'show', '-s', '--format=%H|%an|%at|%s', commit_hash]
        message_output = subprocess.check_output(cmd_message, text=True).strip()
        hash_id, author, timestamp, message = message_output.split('|')

        # Get commit changes
        cmd_changes = ['git', 'show', '--stat', commit_hash]
        changes_output = subprocess.check_output(cmd_changes, text=True).strip()

        return {
            'hash': hash_id,
            'author': author,
            'date': datetime.fromtimestamp(int(timestamp)),
            'message': message,
            'changes': changes_output
        }
    except subprocess.CalledProcessError:
        return {
            'hash': commit_hash,
            'author': 'Unknown',
            'date': datetime.now(),
            'message': 'Error retrieving commit details',
            'changes': ''
        }

def prompt_yes_no(prompt_text: str) -> bool:
    """
    Display a yes/no prompt with a default 'yes' answer.
    
    Args:
        prompt_text: The text to display in the prompt
        
    Returns:
        True if the user answers 'y' or presses Enter (default),
        False if the user answers 'n'
    """
    response = input(f"{prompt_text} (Y/n): ").strip().lower()
    # Return True if the response is empty (user pressed Enter) or 'y'
    return response == '' or response == 'y'

def has_staged_changes() -> bool:
    """
    Check if there are any staged changes in the repository.
    
    Returns:
        True if there are staged changes, False otherwise
    """
    try:
        # Get the diff of staged changes
        output = subprocess.check_output(["git", "diff", "--cached", "--name-only"], text=True)
        # If there's any output, there are staged changes
        return bool(output.strip())
    except subprocess.CalledProcessError:
        return False

def get_staged_files() -> List[str]:
    """
    Get a list of files that are currently staged.
    
    Returns:
        List of staged file paths
    """
    try:
        output = subprocess.check_output(["git", "diff", "--cached", "--name-only"], text=True)
        return [line.strip() for line in output.split('\n') if line.strip()]
    except subprocess.CalledProcessError:
        return []

def get_unstaged_files() -> List[str]:
    """
    Get a list of files that have changes but are not staged.
    
    Returns:
        List of unstaged file paths
    """
    try:
        output = subprocess.check_output(["git", "ls-files", "--modified", "--others", "--exclude-standard"], text=True)
        return [line.strip() for line in output.split('\n') if line.strip()]
    except subprocess.CalledProcessError:
        return []

def stage_files(file_paths: List[str]) -> bool:
    """
    Stage specific files.
    
    Args:
        file_paths: List of file paths to stage
        
    Returns:
        True if successful, False otherwise
    """
    if not file_paths:
        return True
    
    try:
        subprocess.run(["git", "add"] + file_paths, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def parse_file_selection(selection: str, file_list: List[str]) -> List[str]:
    """
    Parse user selection of files and return the corresponding file paths.
    
    Args:
        selection: User input string (e.g., "1,3,5-7")
        file_list: List of available files
        
    Returns:
        List of selected file paths
    """
    if not selection.strip():
        return file_list  # Return all files if no selection provided
    
    selected_indices = set()
    
    # Split by comma
    parts = selection.split(',')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        # Check if it's a range (e.g., "2-4")
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                # Convert to 0-based indices and ensure they're in bounds
                start = max(1, start) - 1
                end = min(len(file_list), end)
                selected_indices.update(range(start, end))
            except ValueError:
                # If parsing fails, try to interpret as a single number
                try:
                    idx = int(part) - 1  # Convert to 0-based index
                    if 0 <= idx < len(file_list):
                        selected_indices.add(idx)
                except ValueError:
                    pass
        else:
            # Single number
            try:
                idx = int(part) - 1  # Convert to 0-based index
                if 0 <= idx < len(file_list):
                    selected_indices.add(idx)
            except ValueError:
                pass
    
    # Convert indices to file paths
    return [file_list[i] for i in sorted(selected_indices)] 