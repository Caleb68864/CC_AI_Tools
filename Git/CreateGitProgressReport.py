"""
Git Progress Report Generator
----------------------------
This script analyzes git commits since the last run and generates a structured progress report.

Features:
- Tracks last run time per repository and branch using a YAML file
- Analyzes commit messages using Claude AI to categorize changes
- Groups related changes by type (feat/fix/refactor etc.) and scope
- Generates a concise, bullet-pointed progress report
- Offers clipboard copy of the final report

Requirements:
- Anthropic API key in .env file (ANTHROPIC_API_KEY)
- Python packages: gitpython, pyperclip, python-dotenv, pyyaml, anthropic

Usage:
1. Run from within a git repository
2. Script will analyze commits since last run (or 3 AM if first run)
3. Progress report will be generated and displayed
4. Option to copy report to clipboard

Arguments:
- --recent-commits, -rc: List titles of last N commits (default: 5) and select one
- --since, -s: Start date/time (e.g. "2024-03-20" or "2024-03-20 14:30:00")
- --until, -u: End date/time (defaults to now)
- --date, -d: Start date (shorthand for --since)
"""

import os
import git
import re
import pyperclip
from datetime import datetime, timedelta
import dotenv
import yaml
import anthropic
import json
import argparse

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

def parse_datetime(datetime_str):
    """Parse datetime string in various formats"""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Time data '{datetime_str}' does not match any supported formats")

def setup_argument_parser():
    parser = argparse.ArgumentParser(description='Generate Git Progress Report')
    parser.add_argument('--recent-commits', '-rc', nargs='?', const=5, type=int, metavar='N', 
                        help='List titles of last N commits (default: 5) and select one')
    parser.add_argument('--since', '-s', help='Start date/time (e.g. "2024-03-20" or "2024-03-20 14:30:00")', type=str)
    parser.add_argument('--until', '-u', help='End date/time (defaults to now)', type=str)
    parser.add_argument('--date', '-d', help='Start date (shorthand for --since)', type=str)
    return parser

def list_recent_commits(n):
    """List the last N commits and let user select one"""
    print(f"\nProcessing: Listing last {n} commits...")  # Processing print
    commits = list(repo.iter_commits(branch_name, max_count=n))
    if not commits:
        print("No commits found")
        return None
    
    print("\nRecent commits:")
    for i, commit in enumerate(commits, 1):
        commit_date = datetime.fromtimestamp(commit.committed_date)
        print(f"{i}. {commit_date.strftime('%Y-%m-%d %H:%M:%S')} - {commit.message.splitlines()[0][:60]}")
    
    while True:
        try:
            choice = input("\nSelect a number to use as starting commit (or press Enter to cancel): ")
            if not choice:
                return None
            choice = int(choice)
            if 1 <= choice <= len(commits):
                selected_commit = commits[choice-1]
                print(f"\nProcessing: Selected commit - {selected_commit.message.splitlines()[0]}")  # Processing print
                # Get the date of the selected commit
                return datetime.fromtimestamp(selected_commit.committed_date)  # Return the date
            print(f"Please enter a number between 1 and {len(commits)}")
        except ValueError:
            print("Please enter a valid number")

# Parse arguments first
args = setup_argument_parser().parse_args()

# Processing print to show parsed arguments
print(f"\nProcessing: Arguments received - {vars(args)}")

# Handle --recent-commits before any other processing
if args.recent_commits is not None:
    print(f"\nProcessing: --recent-commits argument with value: {args.recent_commits}")  # Processing print
    selected_date = list_recent_commits(args.recent_commits)
    if selected_date:
        start_datetime = selected_date  # Ensure start_datetime is set
    else:
        print("No date selected. Exiting.")
        exit()
elif args.date:
    print(f"\nProcessing: Using date argument - {args.date}")  # Processing print
    start_datetime = parse_datetime(args.date)
elif args.since:
    print(f"\nProcessing: Using since argument - {args.since}")  # Processing print
    start_datetime = parse_datetime(args.since)
else:
    print("\nProcessing: No date arguments provided, using default.")  # Processing print
    start_datetime = (last_datetime + timedelta(minutes=2)) if last_datetime_str else datetime.now().replace(hour=3, minute=0, second=0, microsecond=0)

end_datetime = parse_datetime(args.until) if args.until else datetime.now()

print(f"\nAnalyzing commits on branch: {branch_name}")
print(f"Starting from: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Until: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

new_commits = list(repo.iter_commits(
    branch_name,
    since=start_datetime.isoformat(),
    until=end_datetime.isoformat()
))

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
        "You are a commit message analyzer. Analyze the git commit message and return information in this exact format:\n"
        "COMMIT ANALYSIS\n"
        "Summary: <clear, concise technical description of changes (max 100 chars)>\n"
        "Type: <feat/fix/refactor/docs/style/test/chore>\n"
        "Scope: <main component or area affected>\n"
        "Files Changed:\n"
        "- <file1>\n"
        "- <file2>\n"
        "Impact: <LOW/MEDIUM/HIGH>\n\n"
        "Be specific and technical. Return only the structured format above, no other text."
    )
    
    response = client.messages.create(
        model=os.getenv("CLAUDE_SMALL_MODEL", "claude-3-haiku-20240307"),
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
    
    return parse_yaml_response(response.content[0].text.strip(), commit)

def parse_yaml_response(text, commit):
    """Parse the YAML-style response into a structured format"""
    result = {
        "summary": "",
        "type": "unknown",
        "scope": "unknown",
        "files_changed": list(commit.stats.files.keys()),
        "impact": "LOW"
    }
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('Summary:'):
            result["summary"] = line.split(':', 1)[1].strip()[:100]
        elif line.startswith('Type:'):
            result["type"] = line.split(':', 1)[1].strip().lower()
        elif line.startswith('Scope:'):
            result["scope"] = line.split(':', 1)[1].strip()
        elif line.startswith('Impact:'):
            result["impact"] = line.split(':', 1)[1].strip().upper()
        elif line.startswith('- '):  # File entries
            if 'files_changed' not in result:
                result['files_changed'] = []
            result['files_changed'].append(line[2:].strip())
    
    return result

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
        model=os.getenv("CLAUDE_LARGE_MODEL", "claude-3-5-sonnet-20240620"),
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
