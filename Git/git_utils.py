import os
import subprocess
import git

def get_repo():
    """
    Return the git repository object from the current working directory.
    """
    try:
        repo = git.Repo(os.getcwd(), search_parent_directories=True)
        return repo
    except git.InvalidGitRepositoryError:
        raise Exception("Not a git repository!")

def get_current_branch():
    """
    Return the name of the currently active branch.
    """
    repo = get_repo()
    return repo.active_branch.name

def stage_all_changes():
    """
    Stage all changes in the repository.
    """
    subprocess.run(["git", "add", "."])

def get_diff_files(branch):
    """
    Return the list of files that have changes compared to the provided branch.
    """
    try:
        files = subprocess.check_output(["git", "diff", "--name-only", branch]).decode("utf-8")
        return files.strip()
    except subprocess.CalledProcessError:
        return ""

def get_diff_output(branch):
    """
    Return the diff output compared to the provided branch.
    """
    try:
        diff_output = subprocess.check_output(["git", "diff", branch]).decode("utf-8")
        return diff_output.strip()
    except subprocess.CalledProcessError:
        return ""

def commit_changes(commit_message):
    """
    Commit the staged changes using the provided commit message.
    """
    subprocess.run(["git", "commit", "-m", commit_message])

def push_changes():
    """
    Push commits to the remote repository.
    """
    subprocess.run(["git", "push"])

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