import os
import git
import re
import pyperclip
from datetime import datetime, timedelta
import dotenv
import yaml
import anthropic
import json
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

print(f"\nAnalyzing commits on branch: {branch_name}")
print(f"Starting from: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

new_commits = list(repo.iter_commits(branch_name, since=start_datetime.isoformat()))

if not new_commits:
    print("No new commits since last run.")
    exit()

print(f"\nFound {len(new_commits)} new commits to analyze...")

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
prompt = (
    "You are a technical writer tasked with creating progress reports from git commit logs. "
    "You analyze commit messages to create clear, organized summaries that group related changes "
    "and use professional, technical language. Focus on the actual changes made rather than "
    "reformatting commit messages. Always use bullet points and keep responses concise."
)

def parse_commit(commit_message, commit):
    client = anthropic.Anthropic(api_key=api_key)
    parse_prompt = (
        "You are a commit message analyzer. Analyze the git commit message and return a JSON object with the following properties:\n"
        "- summary: A clear, concise technical description of the changes (max 100 chars)\n"
        "- type: The type of change (feat, fix, refactor, docs, style, test, chore)\n"
        "- scope: The main component or area affected\n"
        "- files_changed: List of primary files or areas modified\n"
        "- impact: LOW, MEDIUM, or HIGH based on the significance of the change\n"
        "Return only valid JSON, no other text."
    )
    
    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=150,
        temperature=0.1,
        system=parse_prompt,
        messages=[{
            "role": "user", 
            "content": f"""Analyze this commit:
            Message: {commit_message}
            Files Changed: {', '.join(commit.stats.files.keys())}
            Insertions: {commit.stats.total['insertions']}
            Deletions: {commit.stats.total['deletions']}
            """
        }]
    )
    
    try:
        return json.loads(response.content[0].text.strip())
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        return {
            "summary": commit_message[:100],
            "type": "unknown",
            "scope": "unknown",
            "files_changed": list(commit.stats.files.keys()),
            "impact": "LOW"
        }

# Update the commit processing section
parsed_commits = []
for i, commit in enumerate(new_commits, 1):
    print(f"\nProcessing commit {i}/{len(new_commits)}: {commit.hexsha[:7]}")
    parsed_data = parse_commit(commit.message, commit)
    parsed_commits.append(parsed_data)
    print(f"→ {parsed_data['type']}/{parsed_data['scope']}: {parsed_data['summary'][:60]}...")

print("\nGrouping commits by type and scope...")
grouped_commits = {}
for commit in parsed_commits:
    key = f"{commit['type']}/{commit['scope']}"
    if key not in grouped_commits:
        grouped_commits[key] = []
    grouped_commits[key].append(commit)

print(f"\nFound {len(grouped_commits)} categories of changes:")
for group in grouped_commits.keys():
    print(f"- {group} ({len(grouped_commits[group])} commits)")

print("\nGenerating final report...")

# Build the extraMsg with grouped commits
extraMsg = (
    f"Please create a progress report from the following analyzed git commits that:\n"
    f"1. Uses exactly this title: '{report_title}'\n"
    f"2. Uses the grouped changes below\n"
    f"3. Uses bullet points for each change\n"
    f"4. Stays under {report_length} characters total\n\n"
    f"Analyzed commits by category:\n"
)

for group, commits in grouped_commits.items():
    extraMsg += f"\n{group}:\n"
    for commit in commits:
        extraMsg += f"- {commit['summary']} (Impact: {commit['impact']})\n"

max_tokens = 8000
max_length = max_tokens * 3
            
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

# After generating report
print(f"\nReport generated! ({len(output)} characters)")

# prompt user to copy progress report to clipboard
copy_to_clipboard = input("\nDo you want to copy the progress report to clipboard? (y/n): ")
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
