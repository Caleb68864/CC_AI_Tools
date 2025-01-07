import os
import git
import re
import pyperclip
from datetime import datetime, timedelta
import dotenv
import yaml
import anthropic
dotenv.load_dotenv()

# Setup API_KEY with your actual OpenAI API key in .env file in the same directory.
api_key = os.getenv("ANTHROPIC_API_KEY")

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
        all_data = yaml.safe_load(file) or {}
except FileNotFoundError:
    all_data = {}

runs = all_data.get("Runs", {})

repo_name = repo.working_dir.split(os.sep)[-1]
key = f"{repo_name}_{branch_name}"

last_run_info = runs.get(key, {})
last_datetime_str = last_run_info.get('last_run', '')
try:
    last_datetime = datetime.strptime(last_datetime_str, "%Y-%m-%d %H:%M:%S")
except ValueError:
    # If the date is not in the right format, set the date to today with a time of 3 AM
    last_datetime = datetime.now().replace(hour=3, minute=0, second=0, microsecond=0)

# Calculate start_datetime based on the last run
start_datetime = (last_datetime + timedelta(minutes=2)) if last_datetime_str else datetime.now().replace(hour=3, minute=0, second=0, microsecond=0)

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

#extraMsg = (f"Create a list of changes made based on the git Commit Logs below.\n"
#            f"Each change should be formatted as a bullet point.\n"
#            f"The Reports Title should be: {report_title}"
#            f"The Report must be less than {report_length} characters.\n"
#           f"Combine comments about the same file and summarize where possible.\n"
#            f"Example Report:"
#            f"{report_title}"
#            f" - Summary Comment.\n"
#            f" - Summary Comment.\n"
#            )
max_tokens = 8000
max_length = max_tokens * 3
            
extraMsg = (
    f"Generate a concise and clear progress report based on the git commit logs provided below.\n"
    f"Format each change as a bullet point.\n"
    f"The report should have a title: '{report_title}'.\n"
    f"The entire report must be less than {report_length} characters.\n"
    f"Combine comments related to the same file or feature and summarize them where possible to avoid repetition.\n"
    f"The format of the report should be as follows:\n\n"
    f"{report_title}\n"
    f"- Summary of change 1.\n"
    f"- Summary of change 2.\n"
    f"- Further summaries as needed...\n\n"
    f"Here are the git commit logs to use for generating the report:\n"
)


for commit_comment in commit_comments:
    commit_string = f"- {commit_comment}\n"
    #print(commit_string)
    charactersToGet = max_length - len(extraMsg) 
    
    # Check if there is enough space to add the entire commit_string
    if charactersToGet >= len(commit_string):
        extraMsg += commit_string
    else:
        # If not enough space, add as much of the commit_string as possible
        if charactersToGet > 0:
            extraMsg += commit_string[:charactersToGet]
        break
        
#print(extraMsg)

def get_ai_output(prompt, extra_msg):
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=max_tokens,
        temperature=0.2,
        system=prompt,
        messages=[
            {"role": "user", "content": extra_msg}
        ]
    )

    return response.content[0].text.strip()

progress_report = get_ai_output(prompt, extraMsg)

output = progress_report

print("Git Progress Report:\n")
print(output)

# prompt user to copy progress report to clipboard
copy_to_clipboard = input("Do you want to copy the progress report to clipboard? (y/n): ")
if copy_to_clipboard.lower() == 'y':
    pyperclip.copy(output)
    print("Progress report copied to clipboard!")
    # Save the current date and time, repo name, and branch name to the YAML file
    current_datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Update the information for the current run
    runs[key] = {
        'last_run': current_datetime_str,
        'repo': repo_name,
        'branch': branch_name,
    }

    # Write the updated runs data back to the YAML file
    with open(yaml_file_path, 'w') as file:
        yaml.dump({'Runs': runs}, file)
    print("YAML file updated.")
else:
    print("Progress report not copied to clipboard.")
