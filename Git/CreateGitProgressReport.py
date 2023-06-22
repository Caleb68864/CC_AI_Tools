import git
import openai
import re
import pyperclip
import datetime
import sys
from datetime import datetime

# replace API_KEY with your actual OpenAI API key
openai.api_key = "API_KEY"

# create GitPython repo object
repo = git.Repo()

# get current branch and its creation date
branch = repo.active_branch
branch_name = branch.name

# branch_creation_date = "2023-03-27 10:15"
# check if the user provided a date in the command line
if len(sys.argv) > 1:
    branch_creation_date = sys.argv[1]
else:
    while True:
        branch_creation_date = input("Enter the branch creation date in yyyy-mm-dd HH:MM format: ")
        try:
            datetime.datetime.strptime(branch_creation_date, "%Y-%m-%d %H:%M")
            break
        except ValueError:
            print("Invalid date format. Please enter the date in yyyy-mm-dd HH:MM format.")

# get list of commits in branch after its creation
commits = list(repo.iter_commits(branch, since=branch_creation_date))


#for commit in commits:
#    print(commit.summary)

# sanitize branch name
title = re.sub(r'[^\w\s]', ' ', branch_name).replace('-', ' ').strip()


report_title = f"Progress Report for {title} on {datetime.now().strftime('%m/%d/%Y')}:\n"
report_length = 475 - len(report_title)

# compile progress report using OpenAI
prompt = (f"You are a seasoned Full Stack Developer.\n"
          f"Create a progress report based on the git commits below.\n"
          # f"The Reports Title should be: {report_title}"
          f"The Report must be less than {report_length} characters.\n"
          )
          
for commit in commits:
    if "asdf" not in commit.summary:
        #prompt += "<Begin Commit Log>\n"
        commit_string = f"{commit.hexsha} - {commit.summary}\n"
        test = len(prompt) + len(commit_string)
        if test < 1023:
            prompt += commit_string
        else:
            break
        #prompt += "<End Commit Log>\n"


#prompt += f"Report Title: {report_title}"



prompt = prompt[:1023]

# print(prompt)

response = openai.Completion.create(
    engine="text-davinci-003",
    prompt=prompt,
    temperature=.7,
    max_tokens=1024,
    n=1,
    stop=None,
    timeout=30,
)

progress_report = response.choices[0].text.strip()

# output = f"Progress report for branch {branch}:\n\n{progress_report}"
# output = progress_report
output = report_title + progress_report

print("Git Progress Report:\n")
print(output)

# prompt user to copy progress report to clipboard
copy_to_clipboard = input("Do you want to copy the progress report to clipboard? (y/n): ")
if copy_to_clipboard.lower() == "y":
    pyperclip.copy(output)
    print("Progress report copied to clipboard!")
else:
    print("Progress report not copied to clipboard.")