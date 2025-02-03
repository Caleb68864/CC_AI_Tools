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
from ai_client import AIClient
from git_utils import (
    get_current_branch,
    stage_all_changes,
    get_diff_files,
    get_diff_output,
    commit_changes,
    push_changes
)

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
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('FILE SUMMARY'):
            if current_file:
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
        elif line.startswith('OVERALL STATISTICS'):
            if current_file:
                result["files"].append(current_file)
            current_file = None
        elif current_file is not None:
            if line.startswith('- Name:'):
                current_file["name"] = line.split(':', 1)[1].strip()
            elif line.startswith('- Type:'):
                current_file["change_type"] = line.split(':', 1)[1].strip()
            elif line.startswith('- Summary:'):
                current_file["summary"] = line.split(':', 1)[1].strip()
            elif line.startswith('- Lines Added:'):
                current_file["changes"]["additions"] = safe_int_convert(line.split(':', 1)[1].strip())
            elif line.startswith('- Lines Deleted:'):
                current_file["changes"]["deletions"] = safe_int_convert(line.split(':', 1)[1].strip())
            elif line.startswith('- Modified Functions:'):
                functions = line.split(':', 1)[1].strip()
                current_file["changes"]["functions_modified"] = [f.strip() for f in functions.split(',')]
            elif line.startswith('  *'):
                current_file["changes"]["key_changes"].append(line[3:].strip())
        else:
            if line.startswith('- Total Files Changed:'):
                result["overall_stats"]["total_files"] = safe_int_convert(line.split(':', 1)[1].strip())
            elif line.startswith('- Total Additions:'):
                result["overall_stats"]["total_additions"] = safe_int_convert(line.split(':', 1)[1].strip())
            elif line.startswith('- Total Deletions:'):
                result["overall_stats"]["total_deletions"] = safe_int_convert(line.split(':', 1)[1].strip())
            elif line.startswith('  * Modified:'):
                result["overall_stats"]["change_types"]["modify"] = safe_int_convert(line.split(':', 1)[1].strip())
            elif line.startswith('  * Added:'):
                result["overall_stats"]["change_types"]["add"] = safe_int_convert(line.split(':', 1)[1].strip())
            elif line.startswith('  * Deleted:'):
                result["overall_stats"]["change_types"]["delete"] = safe_int_convert(line.split(':', 1)[1].strip())
    
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
        commit_message_data = yaml.safe_load(cleaned_resp)
    except yaml.YAMLError as e:
        print(f"⚠️ Error parsing YAML: {str(e)}")
        print("Using fallback format...")
        commit_message_data = {
            'title': 'Update files',
            'summary': 'Changes made to repository files.',
            'details': ['Files were modified'],
            'files_changed': diff_files.split('\n')
        }

    # Construct the final commit message
    commit_message = f"{commit_message_data['title']}\n\nSummary:\n{commit_message_data['summary']}\n\nDetails:\n"
    for detail in commit_message_data['details']:
        commit_message += f"- {detail}\n"
    commit_message += "Files Changed:\n"
    for file in commit_message_data['files_changed']:
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
        
    print("\n📝 Proposed commit message:")
    print("=" * 50)
    print(f"{commit_message}")
    print("=" * 50 + "\n")

    choice = input("✋ Do you want to commit with this message? (y/n): ")
    if choice.lower() == "y":
        print("📦 Committing changes...")
        commit_changes(commit_message)
        print("✅ Changes committed")
        
        choice = input("🚀 Do you want to push these changes? (y/n): ")
        if choice.lower() == "y":
            print("📤 Pushing to remote...")
            push_changes()
            print("✅ Changes pushed")
        
        return True
    else:
        print("❌ Commit aborted")
        return False

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
    
