import os
import git
import openai
import re
import pyperclip
from datetime import datetime, timedelta
import dotenv
import yaml
dotenv.load_dotenv()

# Setup API_KEY with your actual OpenAI API key in .env file in the same directory.
openai.api_key = os.getenv("API_KEY")

# create GitPython repo object
repo = git.Repo()

# get current branch
branch = repo.active_branch
branch_name = branch.name

# Retrieve the path to the 'last_run.yaml' file in the same directory as the script
script_dir = os.path.dirname(os.path.abspath(__file__))
yaml_file_path = os.path.join(script_dir, 'last_run.yaml')

# Read data from the YAML file
try:
    with open(yaml_file_path, 'r') as file:
        data = yaml.safe_load(file) or {}
        repo_name = data.get('repo', repo.working_dir.split(os.sep)[-1])
        last_branch_name = data.get('branch', branch_name)
        last_datetime_str = data.get('last_run', '')
        last_datetime = datetime.strptime(last_datetime_str, "%Y-%m-%d %H:%M:%S")
except (FileNotFoundError, ValueError):
    repo_name = repo.working_dir.split(os.sep)[-1]
    last_branch_name = branch_name
    # If the file does not exist, is blank, or the date is not in the right format,
    # Set the date to today with a time of 3 AM
    last_datetime = datetime.now().replace(hour=3, minute=0, second=0, microsecond=0)

# Check if we're operating on the same repo and branch as the last run
if (repo_name == repo.working_dir.split(os.sep)[-1] and last_branch_name == branch_name):
    # Subtract 5 minutes from the stored date and time
    start_datetime = last_datetime - timedelta(minutes=5)
else:
    # If different repo or branch, use fallback datetime
    start_datetime = datetime.now().replace(hour=3, minute=0, second=0, microsecond=0)

# Subtract 5 minutes from the stored date and time
start_datetime = last_datetime - timedelta(minutes=5)

# get list of new commits after the start_datetime
new_commits = list(repo.iter_commits(branch_name, since=start_datetime.isoformat()))

# If new_commits is empty, exit the script
if not new_commits:
    print("No new commits since last run.")
    exit()

# retrieve all commit comments for new commits
commit_comments = [commit.message for commit in new_commits]

# sanitize branch name for report title
title = re.sub(r'[^\w\s]', ' ', branch_name).replace('-', ' ').strip()
for i in range(10, 2, -1):
    title = title.replace(' ' * i, ' ').strip()

# generate report title with current date
report_title = f"Progress Report for {title} on {datetime.now().strftime('%m/%d/%Y')}\n"
report_length = 475 - len(report_title)

# compile progress report using OpenAI
prompt = "Changes Made:\n"

extraMsg = (f"Create a list of changes made based on the git Commit Logs below.\n"
            f"Each change should be formatted as a bullet point.\n"
            f"The Reports Title should be: {report_title}"
            f"The Report must be less than {report_length} characters.\n"
            f"Combine comments about the same file and summarize where possible.\n"
            f"Example Report:"
            f"{report_title}"
            f" - Summary Comment.\n"
            f" - Summary Comment.\n"
            )

for commit_comment in commit_comments:
    commit_string = f"- {commit_comment}\n"
    if len(prompt) + len(commit_string) + len(extraMsg) < 4096:
        prompt += commit_string
    else:
        break

def get_ai_output(prompt, extra_msg):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": extra_msg}],
        temperature=.2,
        max_tokens=4096,
        n=1,
        stop=None,
        timeout=30,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    return response.choices[0].message['content'].strip()

progress_report = get_ai_output(prompt, extraMsg)

output = progress_report

print("Git Progress Report:\n")
print(output)

# prompt user to copy progress report to clipboard
copy_to_clipboard = input("Do you want to copy the progress report to clipboard? (y/n): ")
if copy_to_clipboard.lower() == 'y':
    pyperclip.copy(output)
    print("Progress report copied to clipboard!")
    # Save the current date and time, repo name, and branch name to the YAML file again after copying to clipboard
    current_datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(yaml_file_path, 'w') as file:
        yaml.dump({
            'last_run': current_datetime_str,
            'repo': repo.working_dir.split(os.sep)[-1],
            'branch': branch_name,
        }, file)
    print("YAML file updated.")
else:
    print("Progress report not copied to clipboard.")