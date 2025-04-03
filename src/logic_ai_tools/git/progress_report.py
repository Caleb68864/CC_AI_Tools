"""
Git Progress Report Generator
---------------------------
A tool that uses AI to generate detailed progress reports from git history.

Features:
- Analyzes git log between specified dates
- Groups changes by type (features, fixes, etc.)
- Generates structured markdown report
- Supports custom date ranges and branch filtering
"""

import os
import sys
import dotenv
import argparse
import pyperclip
import re
import time
import signal
from datetime import datetime, timedelta
from pathlib import Path
import concurrent.futures
from functools import partial
import tqdm

# Add the src directory to the Python path
src_dir = str(Path(__file__).resolve().parents[2])
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from cc_ai_tools.ai.client import AIClient
from cc_ai_tools.git.utils import (
    get_repo,
    get_commit_history,
    get_commit_details,
    get_current_branch,
    list_recent_commits,
    prompt_yes_no
)
from cc_ai_tools.yaml.utils import load_yaml, save_yaml, parse_yaml_response
from cc_ai_tools.utils.interrupt_handler import handle_interrupt

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
        parser.add_argument('--workers', '-w', type=int, default=5, 
                            help='Number of parallel workers for commit processing (default: 5)')
        parser.add_argument('--batch-size', '-b', type=int, default=0,
                            help='Process commits in batches of this size (0 = process all at once)')
        parser.add_argument('--commit-timeout', '-ct', type=int, default=30,
                            help='Timeout in seconds for each commit analysis (default: 30)')
        parser.add_argument('--report-timeout', '-rt', type=int, default=60,
                            help='Timeout in seconds for final report generation (default: 60)')
        parser.add_argument('--max-retries', '-mr', type=int, default=3,
                            help='Maximum number of retries for AI requests (default: 3)')
        parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
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
            except KeyboardInterrupt:
                handle_interrupt()
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

    # Sort commits by date in ascending order (oldest first)
    new_commits.sort(key=lambda x: x.committed_date)
    
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
        "reformatting commit messages. Always use bullet points and keep responses concise. "
        "IMPORTANT: Always present changes in chronoccal order (from beginning to end)."
    )

    def retry_ai_request(func, *args, max_retries=3, initial_delay=1, timeout=30, **kwargs):
        """
        Retry an AI request with exponential backoff and timeout.
        
        Args:
            func: The function to retry
            *args: Positional arguments to pass to the function
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
            timeout: Timeout in seconds for each attempt
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
        """
        delay = initial_delay
        last_exception = None
        
        # Define a timeout handler
        def timeout_handler(signum, frame):
            raise TimeoutError(f"AI request timed out after {timeout} seconds")
        
        for attempt in range(max_retries):
            try:
                # Set up the timeout signal
                if sys.platform != 'win32':  # Signal-based timeout doesn't work well on Windows
                    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(timeout + 5)  # Add 5 seconds buffer to the ThreadPoolExecutor timeout
                
                try:
                    # Use ThreadPoolExecutor to implement timeout
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(func, *args, **kwargs)
                        try:
                            result = future.result(timeout=timeout)
                            # Reset the alarm if we're on a platform that supports it
                            if sys.platform != 'win32':
                                signal.alarm(0)
                            return result
                        except concurrent.futures.TimeoutError:
                            raise TimeoutError(f"AI request timed out after {timeout} seconds")
                finally:
                    # Restore the old signal handler if we're on a platform that supports it
                    if sys.platform != 'win32':
                        signal.signal(signal.SIGALRM, old_handler)
                        signal.alarm(0)
                        
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    sleep_time = delay * (2 ** attempt)
                    print(f"⚠️ AI request failed: {str(e)}. Retrying in {sleep_time:.1f} seconds...")
                    time.sleep(sleep_time)
        
        # If we get here, all retries failed
        raise last_exception

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
        
        try:
            response_text = retry_ai_request(
                ai_client.get_response,
                system_prompt=parse_prompt,
                user_message=message,
                max_retries=args.max_retries,
                initial_delay=1,
                timeout=args.commit_timeout
            )
        except Exception as e:
            print(f"⚠️ Error analyzing commit {commit.hexsha[:7]}: {str(e)}")
            return {
                "summary": f"Error analyzing commit: {commit.message.splitlines()[0][:60]}",
                "type": "unknown",
                "scope": "unknown",
                "files_changed": list(commit.stats.files.keys())[:5],
                "impact": "LOW"
            }

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
    
    # Process commits in parallel
    print(f"\n🔄 Processing {len(new_commits)} commits in parallel...")
    
    # Create a partial function with fixed parameters
    process_commit_partial = partial(parse_commit)
    
    # Use a thread pool to process commits in parallel
    max_workers = min(args.workers, len(new_commits))
    print(f"🧵 Using {max_workers} parallel workers")
    
    parsed_commits = []
    completed = 0
    errors = 0
    start_time = time.time()
    
    # Process commits in batches if batch size is specified
    batch_size = args.batch_size if args.batch_size > 0 else len(new_commits)
    num_batches = (len(new_commits) + batch_size - 1) // batch_size  # Ceiling division
    
    for batch_idx in range(num_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(new_commits))
        batch_commits = new_commits[start_idx:end_idx]
        
        if num_batches > 1:
            print(f"\n🔄 Processing batch {batch_idx + 1}/{num_batches} ({len(batch_commits)} commits)")
        
        # Create a progress bar
        with tqdm.tqdm(total=len(batch_commits), desc="Analyzing commits", unit="commit") as progress_bar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Create a dictionary mapping futures to commit indices
                future_to_idx = {
                    executor.submit(process_commit_partial, commit.message, commit): (i + start_idx, commit)
                    for i, commit in enumerate(batch_commits)
                }
                
                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_idx):
                    i, commit = future_to_idx[future]
                    try:
                        parsed_data = future.result()
                        completed += 1
                        progress_bar.update(1)
                        
                        # Only print detailed info if verbose
                        if args.verbose:
                            print(f"\n🔄 Processed commit {i + 1}/{len(new_commits)}: {commit.hexsha[:7]}")
                            print(f"🔍 Parsed data for commit {commit.hexsha[:7]}: {parsed_data}")
                        
                        parsed_commits.append(parsed_data)
                        branch_type = parsed_data.get('type', 'unknown')
                        branch_scope = parsed_data.get('scope', 'unknown')
                        branch_summary = parsed_data.get('summary', 'No summary available')[:60]
                        
                        if args.verbose:
                            print(f"  ↳ {branch_type}/{branch_scope}: {branch_summary}...")
                    except Exception as exc:
                        progress_bar.update(1)
                        errors += 1
                        print(f"\n⚠️ Error processing commit {commit.hexsha[:7]}: {exc}")
                        # Add a fallback entry for failed commits
                        fallback_data = {
                            "summary": f"Error processing commit: {commit.message.splitlines()[0][:60]}",
                            "type": "unknown",
                            "scope": "unknown",
                            "files_changed": list(commit.stats.files.keys())[:5],
                            "impact": "LOW"
                        }
                        parsed_commits.append(fallback_data)
    
    # Print summary of processing results
    elapsed_time = time.time() - start_time
    print(f"\n✅ Commit processing complete!")
    print(f"📊 Summary:")
    print(f"   - Total commits: {len(new_commits)}")
    print(f"   - Successfully processed: {completed - errors}")
    print(f"   - Errors: {errors}")
    print(f"   - Time taken: {elapsed_time:.2f} seconds")
    print(f"   - Average time per commit: {elapsed_time / len(new_commits):.2f} seconds")

    print("\n📊 Grouping commits by type and scope...")
    grouped_commits = {}
    for i, commit in enumerate(parsed_commits):
        key_group = f"{commit['type']}/{commit['scope']}"
        if key_group not in grouped_commits:
            grouped_commits[key_group] = []
        # Store the original index to maintain chronoccal order
        commit['original_index'] = i
        grouped_commits[key_group].append(commit)
    
    # Ensure commits within each group are in chronoccal order
    for group in grouped_commits:
        grouped_commits[group].sort(key=lambda x: x['original_index'])

    print(f"\n📑 Found {len(grouped_commits)} categories of changes:")
    for group in grouped_commits.keys():
        print(f"  ↳ {group} ({len(grouped_commits[group])} commits)")

    print("\n✍️ Generating final report...")

    extraMsg = (
        f"Please create a progress report from the following analyzed git commits that:\n"
        f"1. Uses exactly this title: '{report_title}'\n"
        f"2. Uses the grouped changes below\n"
        f"3. Uses bullet points for each change\n"
        f"4. Stays under {report_length} characters total\n"
        f"5. Lists changes in chronoccal order (from beginning to end, not end to beginning)\n\n"
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

    def get_ai_output(prompt: str, extra_msg: str) -> str:
        """
        Generate AI output using the small model.
        
        Args:
            prompt: System prompt for the AI
            extra_msg: User message for the AI
            
        Returns:
            Generated response text
        """
        # Use the small model for the final report as well
        ai_client = AIClient(
            model=os.getenv("CLAUDE_SMALL_MODEL", "claude-3-haiku-20240307"),
            max_tokens=4000,  # Reduced from 8000 to be more appropriate for the small model
            temperature=0.2
        )
        
        try:
            return retry_ai_request(
                ai_client.get_response,
                system_prompt=prompt,
                user_message=extra_msg,
                max_retries=args.max_retries,
                initial_delay=2,
                timeout=args.report_timeout
            )
        except Exception as e:
            print(f"⚠️ Error generating report: {str(e)}")
            # Create a simplified report if the AI fails
            simplified_report = f"{report_title}\n\n"
            simplified_report += "Error generating detailed report. Here's a simple summary:\n\n"
            
            for group, commits in grouped_commits.items():
                simplified_report += f"## {group}\n"
                # Sort commits by original_index to maintain chronoccal order
                sorted_commits = sorted(commits[:5], key=lambda x: x.get('original_index', 0))
                for commit in sorted_commits:
                    simplified_report += f"- {commit.get('summary', 'No summary')}\n"
                if len(commits) > 5:
                    simplified_report += f"- ... and {len(commits) - 5} more changes\n"
                simplified_report += "\n"
            
            return simplified_report

    progress_report = get_ai_output(prompt, extraMsg)
    output = progress_report

    print("📝 Git Progress Report:\n")
    print(output)

    print(f"\n✅ Report generated! ({len(output)} characters)")

    try:
        if prompt_yes_no("\n📋 Copy progress report to clipboard?"):
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
    except KeyboardInterrupt:
        handle_interrupt()

if __name__ == "__main__":
    try:
        create_git_progress_report()
    except KeyboardInterrupt:
        handle_interrupt()
