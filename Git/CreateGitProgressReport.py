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
import re
import pyperclip
from datetime import datetime, timedelta
import dotenv
import json
import argparse
from AI.ai_client import AIClient  # Import the reusable AI client
# Import consolidated git functions
from Git.git_utils import get_repo, get_current_branch, list_recent_commits
# Import YAML utils
from YAML.yaml_utils import load_yaml, save_yaml, parse_yaml_response
import yaml
import anthropic

print("📁 Loading environment variables and configuration...")
dotenv.load_dotenv()

# Setup API_KEY with your actual Anthropics API key in .env file
api_key = os.getenv("ANTHROPIC_API_KEY")

def create_git_progress_report():
    print("🚀 STARTING: Git Progress Report Generator")
    
    print("🔍 Initializing Git repository using git_utils...")
    repo = get_repo()
    branch_name = get_current_branch()
    
    # Retrieve the path to the 'last_run.yaml' file in the same directory as the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_file_path = os.path.join(script_dir, 'last_run.yaml')

    # Read data from the YAML file
    try:
        all_data = load_yaml(yaml_file_path)
    except FileNotFoundError:
        all_data = {}

    runs = all_data.get("Runs", {})

    repo_name = os.path.basename(repo.working_dir)
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

    def interactive_select_commit(n, branch):
        """List the last N commits on a branch and let the user select one"""
        print(f"\n📜 Retrieving last {n} commits on branch '{branch}'...")
        commits = list_recent_commits(branch, n)
        if not commits:
            print("❌ No commits found")
            return None
        
        print("\n📋 Recent commits:")
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
                    print(f"\n📜 Processing: Selected commit - {selected_commit.message.splitlines()[0]}")
                    return datetime.fromtimestamp(selected_commit.committed_date)
                print(f"Please enter a number between 1 and {len(commits)}")
            except ValueError:
                print("Please enter a valid number")

    # Parse command-line arguments
    args = setup_argument_parser().parse_args()
    print(f"\n⚙️ Processing arguments: {vars(args)}")

    # Handle --recent-commits before any other processing
    if args.recent_commits is not None:
        print(f"\n🔄 Processing recent commits: {args.recent_commits}")
        selected_date = interactive_select_commit(args.recent_commits, branch_name)
        if selected_date:
            start_datetime = selected_date  # Use the date of the selected commit
        else:
            print("No date selected. Exiting.")
            exit()
    elif args.date:
        print(f"\n📅 Using specified date: {args.date}")
        start_datetime = parse_datetime(args.date)
    elif args.since:
        print(f"\n📅 Using since argument - {args.since}")
        start_datetime = parse_datetime(args.since)
    else:
        print("\n📅 No date arguments provided, using default.")
        start_datetime = (last_datetime + timedelta(minutes=2)) if last_datetime_str else datetime.now().replace(hour=3, minute=0, second=0, microsecond=0)

    end_datetime = parse_datetime(args.until) if args.until else datetime.now()

    print(f"\n📊 Analysis Configuration:")
    print(f"🔀 Branch: {branch_name}")
    print(f"⏰ Start: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🏁 End: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

    new_commits = list(repo.iter_commits(
        branch_name,
        since=start_datetime.isoformat(),
        until=end_datetime.isoformat()
    ))

    if not new_commits:
        print("❌ No new commits since last run.")
        exit()

    print(f"\n🔍 Found {len(new_commits)} new commits to analyze...")

    commit_comments = [commit.message for commit in new_commits]

    # Sanitize branch name for report title
    title = re.sub(r'[^\w\s]', ' ', branch_name).replace('-', ' ').strip()
    for i in range(10, 2, -1):
        title = title.replace(' ' * i, ' ').strip()

    report_title = f"Progress Report for {title} on {datetime.now().strftime('%m/%d/%Y')}\n"
    report_length = 475 - len(report_title)

    prompt = (
        "You are a technical writer tasked with creating progress reports from git commit logs. "
        "You analyze commit messages to create clear, organized summaries that group related changes "
        "and use professional, technical language. Focus on the actual changes made rather than "
        "reformatting commit messages. Always use bullet points and keep responses concise."
    )

    def parse_commit(commit_message, commit):
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
        
        # Debugging print to show the commit message being analyzed
        # print(f"🔍 Analyzing commit message: {commit_message}")

        ai_client = AIClient(
            model=os.getenv("CLAUDE_SMALL_MODEL", "claude-3-haiku-20240307"),
            max_tokens=150,
            temperature=0.1
        )
        
        message = (
            f"Analyze this commit:\n"
            f"Message: {commit_message}\n"
            f"Files Changed: {', '.join(commit.stats.files.keys())}\n"
            f"Insertions: {commit.stats.total['insertions']}\n"
            f"Deletions: {commit.stats.total['deletions']}\n"
        )
        
        response_text = ai_client.get_response(system_prompt=parse_prompt, user_message=message)

        # Debugging print to show the raw response from the AI
        # print(f"🔍 Raw AI response: {response_text}")

        # Instead of parsing the response as YAML, directly construct the parsed data
        parsed_data = {
            "summary": "",  # Default value
            "type": "unknown",  # Default value
            "scope": "unknown",  # Default value
            "files_changed": [],  # Default value
            "impact": "LOW"  # Default value
        }

        # Extract the relevant information from the response_text
        lines = response_text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("Summary:"):
                parsed_data["summary"] = line.split(':', 1)[1].strip()
            elif line.startswith("Type:"):
                parsed_data["type"] = line.split(':', 1)[1].strip()
            elif line.startswith("Scope:"):
                parsed_data["scope"] = line.split(':', 1)[1].strip()
            elif line.startswith("Files Changed:"):
                # Assuming the next lines contain the files
                continue  # Skip to the next line
            elif line.startswith("- "):
                parsed_data["files_changed"].append(line[2:].strip())
            elif line.startswith("Impact:"):
                parsed_data["impact"] = line.split(':', 1)[1].strip()

        return parsed_data

    parsed_commits = []
    for i, commit in enumerate(new_commits, 1):
        print(f"\n🔄 Processing commit {i}/{len(new_commits)}: {commit.hexsha[:7]}")
        parsed_data = parse_commit(commit.message, commit)
        
        # Debugging print to show the parsed data for each commit
        print(f"🔍 Parsed data for commit {commit.hexsha[:7]}: {parsed_data}")

        parsed_commits.append(parsed_data)
        branch_type = parsed_data.get('type', 'unknown')
        branch_scope = parsed_data.get('scope', 'unknown')
        branch_summary = parsed_data.get('summary', 'No summary available')[:60]
        print(f"  ↳ {branch_type}/{branch_scope}: {branch_summary}...")

    print("\n📊 Grouping commits by type and scope...")
    grouped_commits = {}
    for commit in parsed_commits:
        key_group = f"{commit['type']}/{commit['scope']}"
        if key_group not in grouped_commits:
            grouped_commits[key_group] = []
        grouped_commits[key_group].append(commit)

    print(f"\n📑 Found {len(grouped_commits)} categories of changes:")
    for group in grouped_commits.keys():
        print(f"  ↳ {group} ({len(grouped_commits[group])} commits)")

    print("\n✍️ Generating final report...")

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
            # Ensure the summary is included
            summary = commit.get('summary', 'No summary available')
            impact = commit.get('impact', 'No impact specified')
            extraMsg += f"- {summary} (Impact: {impact})\n"

    # Debugging print to show the final prompt before sending it to the AI
    # print("🔍 Final prompt being sent to AI:")
    # print(f"Prompt: {prompt}\nExtra Message: {extraMsg}")

    def get_ai_output(prompt, extra_msg):
        from AI.ai_client import AIClient

        ai_client = AIClient(
            model=os.getenv("CLAUDE_LARGE_MODEL", "claude-3-5-sonnet-20240620"),
            max_tokens=8000,
            temperature=0.2
        )
        response_text = ai_client.get_response(system_prompt=prompt, user_message=extra_msg)
        return response_text

    progress_report = get_ai_output(prompt, extraMsg)
    output = progress_report

    print("📝 Git Progress Report:\n")
    print(output)

    print(f"\n✅ Report generated! ({len(output)} characters)")

    copy_to_clipboard = input("\n📋 Copy progress report to clipboard? (y/n): ")
    if copy_to_clipboard.lower() == 'y':
        pyperclip.copy(output)
        print("✅ Progress report copied to clipboard!")
        current_datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        runs[key] = {
            'last_run': current_datetime_str,
            'repo': repo_name,
            'branch': branch_name,
        }

        save_yaml({'Runs': runs}, yaml_file_path)
        print("💾 YAML file updated.")
    else:
        print("ℹ️ Progress report not copied to clipboard.")

if __name__ == "__main__":
    create_git_progress_report()
