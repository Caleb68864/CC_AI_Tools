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
dotenv.load_dotenv()

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
    # subprocess.check_output(["git", "diff", "--name-only", branch])
    subprocess.check_output(["git", "diff", branch])
    .strip()
    .decode("utf-8")
)

# compile commit message using OpenAI

import openai

def get_lines_after_commit_message(text):
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
    print("🤖 Parsing git diff with Claude Haiku...")
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
            model="claude-3-5-haiku-20241022",
            max_tokens=1000,
            temperature=0,
            system=parse_prompt,
            messages=[
                {"role": "user", "content": diff_output}
            ]
        )

        # Parse the text response into a dictionary structure
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
            # Remove any non-numeric characters except minus sign
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
            # Parse overall statistics
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

def getAIOutput(extraMsg):
    print("\n🔍 Analyzing changes...")
    structured_diff = parse_diff_to_structured(diff_output, diff_files)
    
    if structured_diff:
        print("✨ Generated structured analysis")
    else:
        print("⚠️ Using basic diff analysis")
    
    print("🤖 Generating commit message with Claude...")
    # Replace OpenAI client with Anthropic
    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )

    prompt = (
        f"You are a Git commit message expert. Generate a professional, structured commit message following these exact rules:\n\n"
        f"1. First Line (Title):\n"
        f"   - Must be under 50 characters\n"
        f"   - Start with a capital verb in present tense (Add, Update, Fix, Refactor, etc.)\n"
        f"   - No period at the end\n"
        f"   - Must be immediately actionable and specific\n\n"
        f"2. Summary Section:\n"
        f"   - Start with 'Summary:'\n"
        f"   - 2-3 sentences explaining the WHY of the changes\n"
        f"   - Focus on business value and impact\n\n"
        f"3. Details Section:\n"
        f"   - Start with 'Details:'\n"
        f"   - Bullet points for each significant change\n"
        f"   - Include technical details and implementation notes\n"
        f"   - Reference any related issue numbers if mentioned\n\n"
        f"4. Files Changed:\n"
        f"   - Group related files together\n"
        f"   - Explain the purpose of each file change\n"
        f"Files Modified: {diff_files}\n\n"
        f"Important:\n"
        f"- Fix any typos or grammar issues in the user's comments\n"
        f"- Be concise but comprehensive\n"
        f"- Focus on the WHAT and WHY, not just the HOW\n"
        f"- Use technical terms appropriately\n"
    )
    
    max_tokens = 8000
    max_prompt = max_tokens * 3
    
    if extraMsg != "":
        prompt += (
            f"\n<user_comments>\n"
            f"{extraMsg.strip()}\n"
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

    # Updated API call with correct system parameter
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=max_tokens,
        temperature=0.2,
        system=prompt,  # Move prompt to system parameter
        messages=[
            {"role": "user", "content": extraMsg}
        ]
    )

    resp = response.content[0].text.strip()
    
    # Prepend the file name with the current date
    date_string = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = clean_file_name(f"{date_string}_ {extraMsg}")
    write_to_file(os.path.join(script_dir, "Commit_Logs", file_name), "txt", prompt)
    print("✅ Commit message generated")
    return resp

def commitMsg(userMsg):
    commit_message = getAIOutput(userMsg)
    
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

def clean_file_name(file_name):
    # Remove forbidden characters
    forbidden_chars = '<>"\\|?*:,'
    cleaned_file_name = ''.join(char for char in file_name if char not in forbidden_chars)
    
    # Replace spaces with underscores
    cleaned_file_name = cleaned_file_name.replace(' ', '_')
    
    # Take only first 50 characters of the message part
    if '_' in cleaned_file_name:
        date_part, message_part = cleaned_file_name.split('_', 1)
        message_part = message_part[:50]  # Limit message length
        cleaned_file_name = f"{date_part}_{message_part}"
    
    # Limit total length
    max_length = 245  # Windows max path is 260, leaving room for extension
    cleaned_file_name = cleaned_file_name[:max_length]
    
    return cleaned_file_name

def write_to_file(file_name, ext, content):
    # Create directory if it doesn't exist
    directory = os.path.dirname(file_name)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    # Add extension to the file name
    full_file_name = f"{file_name}.{ext}"

    # Write content to the file
    with open(full_file_name, 'w', encoding='utf-8') as file:
        file.write(content)
   

value = False
while value != True:
    extraMsg = input("Enter Your Commit Message: ")
    value = commitMsg(extraMsg)
    
