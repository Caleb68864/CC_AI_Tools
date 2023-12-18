# This script is designed to automate the process of creating a professional commit message based on the changes in a Git branch. 
# It retrieves the current branch, adds any new files, and generates the diff output. 
# The commit message is then compiled using the OpenAI API, using the branch name, user comments, and diff output as input. 
# The proposed commit message is displayed to the user and the user is asked to confirm or reject it. 
# If confirmed, the script commits the changes and gives the option to push them to the remote repository.

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
    # Setup API_KEY with your actual OpenAI API key in .env file in the same directory.
    openai.api_key = os.getenv("API_KEY")
    prompt = (
        #f"Compile a professional sounding commit message based on the changes in branch {branch}:\n"
        f"Compile a professional sounding commit message based on the Example below.\n Use the Subject, Comments and Diff Output section and Expand verbage where possible.\n"
        f"Fix any typos in the User Comments.\n"
        f"Make User Comments grammatically correct .\n"
        f"Create a title based on the users comment.\n"
        f"Always put the title on the first line of the commit message.\n"
        f"Example Commit Message:\n"
        f"This is the title of the commit message\n"
        f"Files Updated: Example Files\n"
        "\n"
        f"Comments: User Comments\n"
        "\n"
        "Changes Made:\n"
        '- In Example File, the code was updated to replace the usage of "ObjectId" with "EntityId" in the query.\n'
        # f"Include details about the code if possible.\n"
        #f"The following files were changed:\n"
        #"Here is the git diff output:\n"
        f"<Subject Start>\nFiles Updated: {diff_files}\n<Subject End>\n"
    )
    
    max_prompt = 15999
    
    if extraMsg != "":
        prompt += f"<Comments Start>\n{extraMsg}\n<Comments End>\n"
    prompt += f"\n\n\n"
    prompt += f"<Diff Output Start>\n"
    diff_length = max_prompt-len(prompt) - 25
    prompt += f"{diff_output[:diff_length]}\n"
    prompt += f"<Diff Output End>\n"
    # prompt += "Commit Message:"


    # print(prompt)
    prompt = prompt[:max_prompt]
    

    response = openai.ChatCompletion.create(
        # model="text-davinci-003",
        model="gpt-3.5-turbo-16k",
        #prompt=prompt,
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": extraMsg}],
        temperature=.2,
        max_tokens=4096,
        n=1,
        stop=None,
        timeout=30,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    resp = response['choices'][0]['message']['content'].strip()
    # Prepend the file name with the current date
    date_string = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    file_name = clean_file_name(f"{date_string}_ {extraMsg}")
    write_to_file(f"C:/Users/Caleb/Documents/GitHub/CC_AI_Tools/Git/Commit_Logs/{file_name}", "txt", prompt)
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
    
