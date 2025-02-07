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

# AI Configuration
AI_TEMPERATURE = 0.2
AI_LARGE_MODEL = os.getenv("CLAUDE_LARGE_MODEL", "claude-3-5-sonnet-20240620")
AI_SMALL_MODEL = os.getenv("CLAUDE_SMALL_MODEL", "claude-3-haiku-20240307")

def parse_diff_to_structured(diff_output, diff_files):
    """Parse git diff into a structured format using Claude."""
    print("🤖 Parsing git diff with Claude Haiku...")
    ai_client = AIClient(
        model=AI_SMALL_MODEL,
        max_tokens=1000,
        temperature=AI_TEMPERATURE
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
    print("\n📝 Analyzing changes...")
    
    # Stage all changes first
    print("📝 Adding changes to git...")
    stage_all_changes()
    
    # Get structured diff data
    diff_files = get_diff_files(get_current_branch())
    diff_output = get_diff_output(get_current_branch())
    
    # Check if there are any changes to commit
    if not diff_files and not diff_output:
        print("❌ No changes to commit")
        return False
        
    structured_diff = parse_diff_to_structured(diff_output, diff_files)

    # Initialize message object with empty lists/strings instead of None
    message = {
        'title': '',
        'summary': '',
        'details': [],  # Initialize as empty list
        'files_changed': structured_diff.get('files', [])
    }

    # Generate title using structured diff
    title = generate_title(user_msg, structured_diff)
    if title and title != 'Update files':
        message['title'] = title
        print(f"✅ Generated Title: {title}")

    # Generate summary using structured diff
    summary = generate_summary(user_msg, structured_diff)
    if summary and summary != 'No Summary':
        message['summary'] = summary
        print(f"✅ Generated Summary: {summary}")

    # Generate details using structured diff
    details = generate_details(user_msg, structured_diff)
    if details:
        message['details'] = details  # Store the details in the message object
        print("✅ Generated Details:")
        for detail in details:
            print(f"  - {detail}")

    # Construct the final commit message
    final_commit_message = []  # Use list for better control of newlines

    if message['title']:
        final_commit_message.append(message['title'])
        final_commit_message.append("")  # Empty line after title

    if message['summary']:
        final_commit_message.append("Summary:")
        final_commit_message.append(message['summary'])
        final_commit_message.append("")  # Empty line after summary

    if message['details']:  # Add details section
        final_commit_message.append("Details:")
        for detail in message['details']:
            if detail.strip():  # Skip empty lines
                final_commit_message.append(f"- {detail}")
        final_commit_message.append("")  # Empty line after details

    if message['files_changed']:
        final_commit_message.append("Files Changed:")
        for file in message['files_changed']:
            if isinstance(file, dict) and 'name' in file:
                final_commit_message.append(f"- {file['name']}")
            elif isinstance(file, str):
                final_commit_message.append(f"- {file}")

    # Join all parts with newlines
    final_commit_message = "\n".join(final_commit_message)

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
        model=AI_SMALL_MODEL,
        max_tokens=50,
        temperature=AI_TEMPERATURE
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
        model=AI_SMALL_MODEL,
        max_tokens=100,
        temperature=AI_TEMPERATURE
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
        model=AI_LARGE_MODEL,
        max_tokens=8000,
        temperature=AI_TEMPERATURE
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
        file_name = file.get('name', 'Unknown file')
        
        # Add modified functions with file name
        if file.get('changes', {}).get('functions_modified'):
            prompt += f"- {file_name}: Modified functions: {', '.join(file['changes']['functions_modified'])}\n"
        
        # Add key changes with file name
        if file.get('changes', {}).get('key_changes'):
            prompt += f"Changes in {file_name}:\n"
            for change in file['changes']['key_changes']:
                prompt += f"- {file_name}: {change}\n"
    
    # Generate the details response
    details = ai_client.get_response(system_prompt=prompt, user_message=user_msg).strip().splitlines()
    
    # Clean up the details
    cleaned_details = []
    for detail in details:
        detail = detail.strip()
        if detail:
            # Remove bullet points and unwanted phrases
            detail = detail.replace("•", "").replace("-", "").strip()
            if not any(phrase in detail.lower() for phrase in [
                "based on the changes made",
                "here are the detailed bullet points",
                "here are the modified functions"
            ]):
                cleaned_details.append(detail)

    return cleaned_details


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
    
