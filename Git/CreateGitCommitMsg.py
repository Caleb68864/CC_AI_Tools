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
dotenv.load_dotenv()

# get current branch
branch = (
    subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    .strip()
    .decode("utf-8")
)

# add any new files
subprocess.run(["git", "add", "."])

# get diff output
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

def getAIOutput(extraMsg):
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
    return resp

def commitMsg(userMsg):
    commit_message = getAIOutput(userMsg)
    
    #print("AI Msg", commit_message)
    
    #commit_message = get_lines_after_commit_message(commit_message)

    #commit_message += f"\n\n"
    #commit_message += f"Files changed:\n{diff_files}\n"
    
   
    # show proposed commit message and changed files
    print(f"Proposed commit message:\n\n{commit_message}\n")


    # ask user to confirm commit message
    choice = input("Do you want to commit with this message? (y/n): ")
    if choice.lower() == "y":
        # commit changes
        subprocess.run(["git", "commit", "-m", commit_message])
        print("Changes committed.")
        
        choice = input("Do you want to push these changes? (y/n): ")
        if choice.lower() == "y":
            subprocess.run(["git", "push"])
            print("Changes pushed.")
        
        return True
    else:
        print("Aborted.")
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
    
