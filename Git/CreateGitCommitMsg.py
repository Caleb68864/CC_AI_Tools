"""
Git Commit Message Generator
---------------------------
A tool that leverages AI to generate professional and structured Git commit messages.

Features:
- Automatically detects current branch and staged changes
- Analyzes git diff output using Claude AI
- Generates structured commit messages with title, summary, and detailed changes
- Provides interactive commit and push workflow
- Saves commit message history with timestamps

The generated commit messages follow best practices:
- Clear, action-oriented titles under 50 characters
- Detailed summaries explaining the why behind changes
- Structured details section with technical implementation notes
- Organized listing of modified files and their purposes

Usage:
1. Stage your changes (git add)
2. Run the script
3. Provide any additional context when prompted
4. Review and approve/reject the generated message
5. Optionally push changes to remote
"""

import anthropic
import os
import datetime
import subprocess
import dotenv
import json
import yaml
from AI.ai_client import AIClient
from Git.git_utils import (
    get_current_branch,
    stage_all_changes,
    get_diff_files,
    get_diff_output,
    commit_changes,
    push_changes

)
from YAML.yaml_utils import parse_yaml_response

def get_lines_after_commit_message(text):
    """Extract lines after the commit message."""
    lines = text.split("\n")
    commit_message_index = None

    for i, line in enumerate(lines):
        if line.startswith("Comments"):
            commit_message_index = i
            break

    if commit_message_index is not None:
        return "\n".join(lines[commit_message_index + 1:])
    else:
        return ""

def parse_diff_to_structured(diff_output, diff_files):
    """Parse git diff into a structured format using Claude."""
    print("🤖 Parsing git diff with Claude Haiku...")
    ai_client = AIClient(
        model=os.getenv("CLAUDE_SMALL_MODEL", "claude-3-haiku-20240307"),
        max_tokens=1000,
        temperature=0
    )
    
    parse_prompt = (
        "Parse the following git diff into a structured format. For each file, provide:\n\n"
        "FILE SUMMARY\n"
        "- Name: <filename>\n"
        "- Type: <add/modify/delete>\n"
        "- Summary: Brief description of changes\n"
        "- Lines Added: <number>\n"
        "- Lines Deleted: <number>\n"
        "- Modified Functions: List of changed functions\n"
        "- Key Changes:\n"
        "  * Change 1\n"
        "  * Change 2\n\n"
        "OVERALL STATISTICS\n"
        "- Total Files Changed: <number>\n"
        "- Total Additions: <number>\n"
        "- Total Deletions: <number>\n"
        "- Changes By Type:\n"
        "  * Modified: <number>\n"
        "  * Added: <number>\n"
        "  * Deleted: <number>\n\n"
        "Important:\n"
        "- Be specific and technical in descriptions\n"
        "- Include actual function names from the code\n"
        "- Count real additions and deletions\n"
        "- Identify meaningful code changes, not just formatting\n"
        "- Group related changes together\n"
    )
    
    try:
        response_text = ai_client.get_response(system_prompt=parse_prompt, user_message=diff_output)
        
        structured_diff = parse_text_response(response_text)

        return structured_diff

    except Exception as e:
        print(f"⚠️ Error communicating with Claude: {str(e)}")
        return create_fallback_structure(diff_files)

def parse_text_response(text):
    """Parse the text response into a structured format"""
    result = {
        "files": [],
        "overall_stats": {
            "total_files": 0,
            "total_additions": 0,
            "total_deletions": 0,
            "change_types": {"modify": 0, "add": 0, "delete": 0}
        }
    }
    
    def safe_int_convert(value):
        """Safely convert various number formats to int"""
        try:
            cleaned = ''.join(c for c in value if c.isdigit() or c == '-')
            return int(cleaned) if cleaned else 0
        except ValueError:
            return 0

    current_file = None

    for line in text.split('\n'):
        original_line = line
        line = line.strip()
        if not line:
            continue

        # Normalize by stripping any leading "- " and extra whitespace
        normalized = line.lstrip('- ').strip()

        # Check for the overall statistics section start
        if normalized.startswith("OVERALL STATISTICS"):
            if current_file:
                result["files"].append(current_file)
                current_file = None
            continue

        # Detect the file summary header (typically appears once)
        if normalized.startswith("FILE SUMMARY"):
            if not current_file:
                current_file = {
                    "name": "",
                    "change_type": "",
                    "summary": "",
                    "changes": {
                        "additions": 0,
                        "deletions": 0,
                        "functions_modified": [],
                        "key_changes": []
                    }
                }
            continue

        # Detect a new file block by a "Name:" line.
        if normalized.startswith("Name:"):
            # If we already have a file with a name in progress, push it and start anew.
            if current_file and current_file["name"]:
                result["files"].append(current_file)
                current_file = {
                    "name": "",
                    "change_type": "",
                    "summary": "",
                    "changes": {
                        "additions": 0,
                        "deletions": 0,
                        "functions_modified": [],
                        "key_changes": []
                    }
                }
            if current_file is None:
                current_file = {
                    "name": "",
                    "change_type": "",
                    "summary": "",
                    "changes": {
                        "additions": 0,
                        "deletions": 0,
                        "functions_modified": [],
                        "key_changes": []
                    }
                }
            current_file["name"] = normalized.split("Name:", 1)[1].strip()
            continue

        if normalized.startswith("Type:"):
            if current_file is not None:
                current_file["change_type"] = normalized.split("Type:", 1)[1].strip()
            continue

        if normalized.startswith("Summary:"):
            if current_file is not None:
                current_file["summary"] = normalized.split("Summary:", 1)[1].strip()
            continue

        if normalized.startswith("Lines Added:"):
            if current_file is not None:
                current_file["changes"]["additions"] = safe_int_convert(normalized.split("Lines Added:", 1)[1].strip())
            continue

        if normalized.startswith("Lines Deleted:"):
            if current_file is not None:
                current_file["changes"]["deletions"] = safe_int_convert(normalized.split("Lines Deleted:", 1)[1].strip())
            continue

        if normalized.startswith("Modified Functions:"):
            if current_file is not None:
                funcs = normalized.split("Modified Functions:", 1)[1].strip()
                if funcs.lower() != "none":
                    current_file["changes"]["functions_modified"] = [f.strip() for f in funcs.split(',') if f.strip()]
            continue

        if normalized.startswith("Key Changes:"):
            # Skip the header, as key changes will be captured in subsequent lines that start with "*"
            continue

        if normalized.startswith("*"):
            if current_file is not None:
                current_file["changes"]["key_changes"].append(normalized.lstrip("*").strip())
            continue

        # Process overall statistics lines
        if normalized.startswith("Total Files Changed:"):
            result["overall_stats"]["total_files"] = safe_int_convert(normalized.split("Total Files Changed:", 1)[1].strip())
        elif normalized.startswith("Total Additions:"):
            result["overall_stats"]["total_additions"] = safe_int_convert(normalized.split("Total Additions:", 1)[1].strip())
        elif normalized.startswith("Total Deletions:"):
            result["overall_stats"]["total_deletions"] = safe_int_convert(normalized.split("Total Deletions:", 1)[1].strip())
        elif normalized.startswith("Modified:"):
            result["overall_stats"]["change_types"]["modify"] = safe_int_convert(normalized.split("Modified:", 1)[1].strip())
        elif normalized.startswith("Added:"):
            result["overall_stats"]["change_types"]["add"] = safe_int_convert(normalized.split("Added:", 1)[1].strip())
        elif normalized.startswith("Deleted:"):
            result["overall_stats"]["change_types"]["delete"] = safe_int_convert(normalized.split("Deleted:", 1)[1].strip())
    
    # Append any remaining file being processed
    if current_file:
        result["files"].append(current_file)
    
    return result

def create_fallback_structure(diff_files):
    """Create a basic structure when parsing fails"""
    return {
        "files": [{"name": f, "change_type": "modify", "summary": "File modified", 
                  "changes": {"additions": 0, "deletions": 0, 
                  "functions_modified": [], "key_changes": []}} for f in diff_files.split('\n') if f],
        "overall_stats": {
            "total_files": len(diff_files.split('\n')),
            "total_additions": 0,
            "total_deletions": 0,
            "change_types": {"modify": 1, "add": 0, "delete": 0}
        }
    }

def clean_yaml_response(resp):
    """Clean the response text to ensure valid YAML format"""
    lines = resp.split('\n')
    cleaned_lines = []
    yaml_started = False
    
    # Only keep lines that are part of the YAML structure
    for line in lines:
        # Skip code block markers and empty lines
        if line.strip().startswith('```') or not line.strip():
            continue
            
        # Start collecting lines when we see the first YAML key
        if line.startswith('title:') or line.startswith('summary:') or line.startswith('details:') or line.startswith('files_changed:'):
            yaml_started = True
            
        if yaml_started:
            # Ensure proper indentation for list items
            if line.strip().startswith('-'):
                cleaned_lines.append('  ' + line.strip())
            else:
                cleaned_lines.append(line.strip())
    
    cleaned_text = '\n'.join(cleaned_lines)
    
    # Validate basic YAML structure
    try:
        yaml.safe_load(cleaned_text)
        return cleaned_text
    except yaml.YAMLError:
        # Create fallback YAML if structure is invalid
        return """title: Update repository files
summary: Changes made to multiple files in the repository
details:
  - Multiple files were modified
files_changed:
  - Various files updated"""

def get_ai_output(extra_msg):
    """Generate commit message using AI"""
    print("\n🔍 Analyzing changes...")
    
    # Get current branch using our module
    branch = get_current_branch()
    print(f"📁 Working on branch: {branch}")

    # Stage all changes
    print("📝 Adding any new files to git...")
    stage_all_changes()

    # Get diff output and files using our module
    print("🔄 Analyzing git differences...")
    diff_files = get_diff_files(branch)
    diff_output = get_diff_output(branch)
    
    # Check if there are any changes to commit
    if not diff_files and not diff_output:
        print("❌ No changes to commit")
        return None

    # Calculate max tokens and prompt length
    max_tokens = 8000
    max_prompt = max_tokens * 3
    
    # Define base prompt structure
    base_prompt = """# Git Commit Message Guidelines
1. Title: Must be under 50 characters, start with a capital verb in present tense (Add, Update, Fix, Refactor, etc.), and no period at the end.
2. Summary: 2-3 sentences explaining the WHY of the changes.
3. Details: Bullet points for each significant change.
4. Files Changed: Group related files together and explain the purpose of each file change.

# Required YAML Format
title: <commit title>
summary: <commit summary>
details:
  - <detail 1>
  - <detail 2>
files_changed:
  - <file 1>
  - <file 2>

# Modified Files
"""

    # Calculate available length for diff
    diff_length = max_prompt - len(base_prompt) - 1000  # Buffer for structured diff and other content
    
    structured_diff = parse_diff_to_structured(diff_output, diff_files)
    
    if not structured_diff:
        print("⚠️ Using basic diff analysis")
        structured_section = f"\n# Git Diff\n{diff_output[:diff_length].strip()}"
    else:
        print("✨ Generated structured analysis")
        structured_section = "\n# Structured Changes\n"
        structured_section += f"Total Files: {structured_diff['overall_stats']['total_files']}\n"
        structured_section += f"Additions: {structured_diff['overall_stats']['total_additions']}\n"
        structured_section += f"Deletions: {structured_diff['overall_stats']['total_deletions']}\n\n"
        
        for file in structured_diff['files']:
            structured_section += f"File: {file['name']}\n"
            structured_section += f"Type: {file['change_type']}\n"
            structured_section += f"Summary: {file['summary']}\n"
            if file['changes']['functions_modified']:
                structured_section += f"Modified Functions: {', '.join(file['changes']['functions_modified'])}\n"
            structured_section += "Key Changes:\n"
            for change in file['changes']['key_changes']:
                structured_section += f"  - {change}\n"
            structured_section += "\n"
    
    # Construct final prompt
    prompt = f"{base_prompt}{diff_files}\n\n" \
             f"{(f'# User Comments\n{extra_msg.strip()}\n' if extra_msg else '')}{structured_section}"

    print("🤖 Generating commit message with Claude...")
    ai_client = AIClient(
        model=os.getenv("CLAUDE_LARGE_MODEL", "claude-3-5-sonnet-20240620"),
        max_tokens=max_tokens,
        temperature=0.2
    )
    resp = ai_client.get_response(system_prompt=prompt, user_message=extra_msg)

    # Clean the response before parsing
    cleaned_resp = clean_yaml_response(resp)
    
    # Parse the YAML response
    try:
        commit_message_data = parse_yaml_response(cleaned_resp)
    except Exception as e:
        print(f"⚠️ Error parsing YAML: {str(e)}")
        print("Using fallback format...")
        commit_message_data = {
            'title': 'Update files',  # Default title
            'summary': 'Changes made to repository files.',
            'details': ['Files were modified'],
            'files_changed': diff_files.split('\n')
        }

    # Construct the final commit message
    commit_message = f"{commit_message_data.get('title', 'No Title')}\n\nSummary:\n{commit_message_data.get('summary', 'No Summary')}\n\nDetails:\n"
    for detail in commit_message_data.get('details', []):
        commit_message += f"- {detail}\n"
    commit_message += "Files Changed:\n"
    for file in commit_message_data.get('files_changed', []):
        commit_message += f"- {file}\n"
    
    # Save commit message to file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    date_string = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    file_name = clean_file_name(f"{date_string}_{extra_msg}")
    write_to_file(os.path.join(script_dir, "Commit_Logs", file_name), "txt", prompt)
    print("✅ Commit message generated")
    return commit_message

def clean_file_name(file_name):
    """Clean the file name to ensure it's valid"""
    forbidden_chars = '<>"\\|?*:,'
    cleaned_file_name = ''.join(char for char in file_name if char not in forbidden_chars)
    cleaned_file_name = cleaned_file_name.replace(' ', '_')
    
    if '_' in cleaned_file_name:
        date_part, message_part = cleaned_file_name.split('_', 1)
        message_part = message_part[:50]
        cleaned_file_name = f"{date_part}_{message_part}"
    
    max_length = 245
    cleaned_file_name = cleaned_file_name[:max_length]
    
    return cleaned_file_name

def write_to_file(file_name, ext, content):
    """Write content to a file"""
    directory = os.path.dirname(file_name)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    full_file_name = f"{file_name}.{ext}"
    with open(full_file_name, 'w', encoding='utf-8') as file:
        file.write(content)

def commit_msg(user_msg):
    """Handle the commit message workflow"""
    commit_message = get_ai_output(user_msg)
    
    # Check if there's a commit message
    if commit_message is None:
        return False
        
    print("\n📝 Analyzing changes...")
    
    # Get structured diff data
    diff_files = get_diff_files(get_current_branch())
    diff_output = get_diff_output(get_current_branch())
    structured_diff = parse_diff_to_structured(diff_output, diff_files)

    # Initialize message object
    message = {
        'title': None,
        'summary': None,
        'details': None,
        'files_changed': structured_diff.get('files', [])
    }

    # Generate title using structured diff
    print("\n🔍 Generating title...")
    title = generate_title(user_msg, structured_diff)
    if title and title != 'Update files':
        message['title'] = title
        print(f"✅ Generated Title: {title}")

    # Generate summary using structured diff
    print("\n🔍 Generating summary...")
    summary = generate_summary(user_msg, structured_diff)
    if summary and summary != 'No Summary':
        message['summary'] = summary
        print(f"✅ Generated Summary: {summary}")

    # Generate details using structured diff
    print("\n🔍 Generating details using the large AI model...")
    ai_client = AIClient(
        model=os.getenv("CLAUDE_LARGE_MODEL", "claude-3-5-sonnet-20240620"),
        max_tokens=150,
        temperature=0.5
    )
    
    # Create a prompt using the structured diff data
    prompt = (
        "Generate detailed bullet points about the following changes:\n"
        "Focus on the modifications made, including any new features, bug fixes, or enhancements.\n"
        "Here are the modified functions and key changes:\n"
    )
    
    # Add modified functions and key changes from each file
    for file in structured_diff.get('files', []):
        if file.get('changes', {}).get('functions_modified'):
            prompt += f"- {file['name']}: {', '.join(file['changes']['functions_modified'])}\n"
        if file.get('changes', {}).get('key_changes'):
            for change in file['changes']['key_changes']:
                prompt += f"- {change}\n"
    
    # Generate the details response
    details = ai_client.get_response(system_prompt=prompt, user_message=user_msg).strip().splitlines()
    
    # Clean up the details to remove unwanted phrases or bullet points
    filtered_details = [d for d in details if d.strip() and "•" not in d and "Based on the changes made," not in d]
    
    if filtered_details:
        message['details'] = [d.strip('- ') for d in filtered_details if d.strip()]
        print("✅ Generated Details:")
        for detail in message['details']:
            print(f"  - {detail}")

    # Construct the final commit message from the message object
    final_commit_message = ""

    if message['title']:
        final_commit_message += f"{message['title']}\n\n"

    if message['summary']:
        final_commit_message += f"Summary:\n{message['summary']}\n\n"

    if message['details']:
        final_commit_message += "Details:\n"
        for detail in message['details']:
            if detail.strip():  # Ensure no empty lines are added
                final_commit_message += f"- {detail}\n"

    if message['files_changed']:
        final_commit_message += "\nFiles Changed:\n"
        for file in message['files_changed']:
            if isinstance(file, dict) and 'name' in file:
                final_commit_message += f"- {file['name']}\n"
            elif isinstance(file, str):
                final_commit_message += f"- {file}\n"

    print("\n📝 Final Commit Message:")
    print("=" * 50)
    print(final_commit_message)
    print("=" * 50)

    # Ask the user if they want to commit the changes
    confirm_commit = input("\nDo you want to commit these changes? (y/n): ")
    if confirm_commit.lower() == 'y':
        commit_changes(final_commit_message)
        print("✅ Changes committed.")

        # Ask the user if they want to push the changes
        confirm_push = input("Do you want to push the changes to the remote repository? (y/n): ")
        if confirm_push.lower() == 'y':
            push_changes()
            print("✅ Changes pushed to the remote repository.")
        else:
            print("ℹ️ Changes not pushed to the remote repository.")
    else:
        print("ℹ️ Changes not committed.")

    # Save commit message to file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    date_string = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    file_name = clean_file_name(f"{date_string}_{user_msg}")
    write_to_file(os.path.join(script_dir, "Commit_Logs", file_name), "txt", final_commit_message)
    print("✅ Commit message generated")
    return final_commit_message

def generate_title(user_msg, structured_diff):
    """Generate a title using the structured diff data."""
    print("🔍 Generating a title using the small AI model...")
    ai_client = AIClient(
        model=os.getenv("CLAUDE_SMALL_MODEL", "claude-3-haiku-20240307"),
        max_tokens=50,
        temperature=0.5
    )
    
    # Create a prompt using the structured diff data
    prompt = (
        "Generate a concise commit title (under 50 chars) based on these changes:\n"
        f"Files Changed: {len(structured_diff.get('files', []))}\n"
        f"Total Additions: {structured_diff.get('overall_stats', {}).get('total_additions', 0)}\n"
        f"Total Deletions: {structured_diff.get('overall_stats', {}).get('total_deletions', 0)}\n\n"
        "Key Changes:\n"
    )
    
    # Add key changes from each file
    for file in structured_diff.get('files', []):
        if file.get('changes', {}).get('key_changes'):
            prompt += f"- {file['name']}: {', '.join(file['changes']['key_changes'])}\n"
    
    title = ai_client.get_response(system_prompt=prompt, user_message=user_msg).strip()
    return title

def generate_summary(user_msg, structured_diff):
    """Generate a summary using the structured diff data."""
    print("🔍 Generating a summary using the small AI model...")
    ai_client = AIClient(
        model=os.getenv("CLAUDE_SMALL_MODEL", "claude-3-haiku-20240307"),
        max_tokens=100,
        temperature=0.5
    )
    
    # Create a prompt using the structured diff data
    prompt = (
        "Generate a concise summary of the following changes:\n"
        f"Total Files Changed: {len(structured_diff.get('files', []))}\n"
        f"Total Additions: {structured_diff.get('overall_stats', {}).get('total_additions', 0)}\n"
        f"Total Deletions: {structured_diff.get('overall_stats', {}).get('total_deletions', 0)}\n\n"
        "Here are the key changes:\n"
    )
    
    # Add summaries from each file
    for file in structured_diff.get('files', []):
        if file.get('summary'):
            prompt += f"- {file['name']}: {file['summary']}\n"
    
    prompt += "\nPlease provide a summary without any introductory phrases or unnecessary content."

    summary = ai_client.get_response(system_prompt=prompt, user_message=user_msg).strip()
    
    # Clean up the summary to ensure it doesn't contain unwanted phrases
    if "Concise Summary:" in summary:
        summary = summary.replace("Concise Summary:", "").strip()

    return summary

def generate_details(user_msg, structured_diff):
    """Generate details using the structured diff data."""
    print("🔍 Generating details using the large AI model...")
    ai_client = AIClient(
        model=os.getenv("CLAUDE_LARGE_MODEL", "claude-3-5-sonnet-20240620"),
        max_tokens=8000,
        temperature=0.5
    )
    
    # Create a prompt using the structured diff data
    prompt = (
        "Please provide a details without any introductory phrases or unnecessary content.\n"
        "Don't use any phrases like 'Based on the changes made, here are the detailed bullet points about the commit:' or 'Here are the modified functions and key changes: or Based on the information provided, here are detailed bullet points about the changes:'.\n"
        "Generate detailed bullet points about the following changes:\n"
        "Focus on the modifications made, including any new features, bug fixes, or enhancements.\n"
        "Here are the modified functions and key changes:\n"
    )
    
    # Add modified functions and key changes from each file
    for file in structured_diff.get('files', []):
        if file.get('changes', {}).get('functions_modified'):
            prompt += f"- {file['name']}: {', '.join(file['changes']['functions_modified'])}\n"
        if file.get('changes', {}).get('key_changes'):
            for change in file['changes']['key_changes']:
                prompt += f"- {change}\n"
    
    # Generate the details response
    details = ai_client.get_response(system_prompt=prompt, user_message=user_msg).strip().splitlines()
    
    # Clean up the details to remove unwanted phrases or bullet points
    filtered_details = [d for d in details if d.strip() and "•" not in d and "Based on the changes made," not in d]
    
    return [d.strip('- ') for d in filtered_details if d.strip()]

def create_git_commit_msg():
    """Main function to create a commit message"""
    print("RUNNING: Git Commit Message Generator")
    extra_msg = input("Enter Your Commit Message: ")
    value = commit_msg(extra_msg)
    
    if not value:
        print("Exiting script...")
        exit(0)

if __name__ == "__main__":
    create_git_commit_msg()
    
