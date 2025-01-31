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
    dotenv.load_dotenv()
    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY")
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
        response = client.messages.create(
            model=os.getenv("CLAUDE_SMALL_MODEL", "claude-3-haiku-20240307"),
            max_tokens=1000,
            temperature=0,
            system=parse_prompt,
            messages=[
                {"role": "user", "content": diff_output}
            ]
        )

        structured_diff = parse_text_response(response.content[0].text)
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
    for line in lines:
        if line.strip().startswith('```') or line.strip().endswith('```'):
            continue
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)

def get_ai_output(extra_msg):
    """Generate commit message using AI"""
    print("\n🔍 Analyzing changes...")
    
    # get current branch
    print("🔍 Getting current branch information...")
    branch = (
        subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        .strip()
        .decode("utf-8")
    )
    print(f"📁 Working on branch: {branch}")

    # add any new files
    print("📝 Adding any new files to git...")
    subprocess.run(["git", "add", "."])

    # get diff output
    print("🔄 Analyzing git differences...")
    diff_files = (
        subprocess.check_output(["git", "diff", "--name-only", branch])
        .strip()
        .decode("utf-8")
    )
    diff_output = (
        subprocess.check_output(["git", "diff", branch])
        .strip()
        .decode("utf-8")
    )
    
    structured_diff = parse_diff_to_structured(diff_output, diff_files)
    
    if structured_diff:
        print("✨ Generated structured analysis")
    else:
        print("⚠️ Using basic diff analysis")
    
    print("🤖 Generating commit message with Claude...")
    dotenv.load_dotenv()
    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )

    prompt = (
        f"You are a Git commit message expert. Generate a professional, structured commit message in YAML format following these exact rules:\n\n"
        f"1. Title: Must be under 50 characters, start with a capital verb in present tense (Add, Update, Fix, Refactor, etc.), and no period at the end.\n"
        f"2. Summary: 2-3 sentences explaining the WHY of the changes.\n"
        f"3. Details: Bullet points for each significant change.\n"
        f"4. Files Changed: Group related files together and explain the purpose of each file change.\n"
        f"Files Modified: {diff_files}\n\n"
        f"Return the output in the following YAML format:\n"
        f"title: <commit title>\n"
        f"summary: <commit summary>\n"
        f"details:\n"
        f"  - <detail 1>\n"
        f"  - <detail 2>\n"
        f"files_changed:\n"
        f"  - <file 1>\n"
        f"  - <file 2>\n"
    )
    
    max_tokens = 8000
    max_prompt = max_tokens * 3
    
    if extra_msg != "":
        prompt += (
            f"\n<user_comments>\n"
            f"{extra_msg.strip()}\n"
            f"</user_comments>\n"
        )

    # Split diff output into files for better context
    files_list = diff_files.split('\n')
    prompt += (
        f"\n<modified_files>\n"
        f"{', '.join(files_list)}\n"
        f"</modified_files>\n"
    )

    # Add diff output with clear markers and limited length
    diff_length = max_prompt - len(prompt) - 25
    prompt += (
        f"\n<diff_output>\n"
        f"{diff_output[:diff_length].strip()}\n"
        f"</diff_output>\n"
    )

    prompt = prompt[:max_prompt]

    response = client.messages.create(
        model=os.getenv("CLAUDE_LARGE_MODEL", "claude-3-5-sonnet-20240620"),
        max_tokens=max_tokens,
        temperature=0.2,
        system=prompt,
        messages=[
            {"role": "user", "content": extra_msg}
        ]
    )

    resp = response.content[0].text.strip()
    
    # Clean the response before parsing
    cleaned_resp = clean_yaml_response(resp)
    
    # Parse the YAML response
    try:
        commit_message_data = yaml.safe_load(cleaned_resp)
    except yaml.YAMLError as e:
        print(f"⚠️ Error parsing YAML: {str(e)}")
        print("Using fallback format...")
        # Create a basic structure if YAML parsing fails
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
    
    print("\n📝 Proposed commit message:")
    print("=" * 50)
    print(f"{commit_message}")
    print("=" * 50 + "\n")

    choice = input("✋ Do you want to commit with this message? (y/n): ")
    if choice.lower() == "y":
        print("📦 Committing changes...")
        subprocess.run(["git", "commit", "-m", commit_message])
        print("✅ Changes committed")
        
        choice = input("🚀 Do you want to push these changes? (y/n): ")
        if choice.lower() == "y":
            print("📤 Pushing to remote...")
            subprocess.run(["git", "push"])
            print("✅ Changes pushed")
        
        return True
    else:
        print("❌ Commit aborted")
        return False

def main():
    """Main function to create a commit message"""
    print("RUNNING: Git Commit Message Generator")
    value = False
    while value != True:
        extra_msg = input("Enter Your Commit Message: ")
        value = commit_msg(extra_msg)

if __name__ == "__main__":
    main()
    
