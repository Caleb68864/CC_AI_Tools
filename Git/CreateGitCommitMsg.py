# This script is designed to automate the process of creating a professional commit message based on the changes in a Git branch. 
# It retrieves the current branch, adds any new files, and generates the diff output. 
# The commit message is then compiled using the OpenAI API, using the branch name, user comments, and diff output as input. 
# The proposed commit message is displayed to the user and the user is asked to confirm or reject it. 
# If confirmed, the script commits the changes and gives the option to push them to the remote repository.

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
        "Parse the following git diff into detailed structured JSON. Analyze each file and provide:\n\n"
        "1. Basic Information:\n"
        "   - File name\n"
        "   - Change type (add/modify/delete)\n"
        "   - Brief summary of changes\n\n"
        "2. Detailed Analysis:\n"
        "   - Count of additions and deletions\n"
        "   - Modified functions or methods\n"
        "   - Key changes with technical details\n"
        "   - Modified sections or components\n\n"
        "3. Overall Statistics:\n"
        "   - Total number of files changed\n"
        "   - Total additions and deletions\n"
        "   - Breakdown of change types\n\n"
        "Output format:\n"
        "{\n"
        '  "files": [{\n'
        '    "name": "filename",\n'
        '    "change_type": "add|modify|delete",\n'
        '    "summary": "brief technical description",\n'
        '    "modified_sections": ["section1", "section2"],\n'
        '    "changes": {\n'
        '      "additions": <number>,\n'
        '      "deletions": <number>,\n'
        '      "functions_modified": ["function1", "function2"],\n'
        '      "key_changes": [\n'
        '        "Detailed change description 1",\n'
        '        "Detailed change description 2"\n'
        '      ]\n'
        '    }\n'
        '  }],\n'
        '  "overall_stats": {\n'
        '    "total_files": <number>,\n'
        '    "total_additions": <number>,\n'
        '    "total_deletions": <number>,\n'
        '    "change_types": {\n'
        '      "modify": <number>,\n'
        '      "add": <number>,\n'
        '      "delete": <number>\n'
        '    }\n'
        '  }\n'
        "}\n\n"
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

        try:
            # Add debug output to see what we're trying to parse
            print("DEBUG: Attempting to parse response:", response.content[0].text[:200] + "...")
            structured_diff = json.loads(response.content[0].text)
            
            print(f"�� Found changes in {structured_diff['overall_stats']['total_files']} files")
            print(f"   Added: {structured_diff['overall_stats']['total_additions']} lines")
            print(f"   Deleted: {structured_diff['overall_stats']['total_deletions']} lines")
            
            # Validate and clean up the response
            if "files" not in structured_diff:
                structured_diff["files"] = []
            if "overall_stats" not in structured_diff:
                structured_diff["overall_stats"] = {
                    "total_files": len(structured_diff["files"]),
                    "total_additions": sum(f["changes"]["additions"] for f in structured_diff["files"]),
                    "total_deletions": sum(f["changes"]["deletions"] for f in structured_diff["files"]),
                    "change_types": {
                        "modify": sum(1 for f in structured_diff["files"] if f["change_type"] == "modify"),
                        "add": sum(1 for f in structured_diff["files"] if f["change_type"] == "add"),
                        "delete": sum(1 for f in structured_diff["files"] if f["change_type"] == "delete")
                    }
                }
            
            return structured_diff
        except json.JSONDecodeError as e:
            print(f"⚠️ Error parsing JSON response: {str(e)}")
            # Fallback to a basic structure
            return {
                "files": [{"name": f, "change_type": "modify", "summary": "File modified", 
                          "modified_sections": [], "changes": {"additions": 0, "deletions": 0, 
                          "functions_modified": [], "key_changes": []}} for f in diff_files.split('\n') if f],
                "overall_stats": {
                    "total_files": len(diff_files.split('\n')),
                    "total_additions": 0,
                    "total_deletions": 0,
                    "change_types": {"modify": 1, "add": 0, "delete": 0}
                }
            }
    except Exception as e:
        print(f"⚠️ Error communicating with Claude: {str(e)}")
        return None

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
    file_name = clean_file_name(f"{date_string}_ {extraMsg}")
    write_to_file(f"C:/Users/CalebBennett/Documents/GitHub/CC_AI_Tools/Git/Commit_Logs/{file_name}", "txt", prompt)
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
    forbidden_chars = '<>"\\|?*,'
    cleaned_file_name = ''.join(char for char in file_name if char not in forbidden_chars)

    # Limit file name length to maximum for Windows
    max_length = 245
    cleaned_file_name = cleaned_file_name[:max_length]

    return cleaned_file_name

def write_to_file(file_name, ext, content):
    
    file_name = f"{file_name}.{ext}"

    # Write content to the file
    file = open(file_name, 'w', encoding='utf-8')
    file.write(content)
    file.close()
   

value = False
while value != True:
    extraMsg = input("Enter Your Commit Message: ")
    value = commitMsg(extraMsg)
    
