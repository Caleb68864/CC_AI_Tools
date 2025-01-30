# CC AI Tools
Productivity Tools Using AI

## Installation

Install required Python packages using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

### PowerShell Setup (Windows)

Run the included PowerShell installation script to set up command-line aliases and environment files:

```powershell
.\install_Scripts.ps1
```

This script will:
- Create global PowerShell functions for all Python scripts, allowing them to run from any location.
- Automatically set up `.env` files from `.env.example` templates if they don't exist.
- Enable you to run scripts by their name without the `.py` extension (e.g., `CreateGitCommitMsg` instead of `python CreateGitCommitMsg.py`).

## Git Tools

### Setup

The PowerShell installation script (`install_Scripts.ps1`) will automatically create a `.env` file from `.env.example` if it doesn't exist. You can then edit the `.env` file with your settings:

**Required API Keys:**
- `API_KEY=your_api_key_here` (deprecated)
- `ANTHROPIC_API_KEY=your_claude_api_key_here`

**Optional AI Model Settings:**
- `CLAUDE_SMALL_MODEL=claude-3-haiku-20240307`
- `CLAUDE_MEDIUM_MODEL=claude-3-5-sonnet-20240620`
- `CLAUDE_LARGE_MODEL=claude-3-5-sonnet-20240620`

The AI model settings allow you to specify which Claude models to use for different tasks. If not set, the scripts will use default values.


### CreateGitCommitMsg.py

A Python script that leverages **Anthropic's Claude AI** to generate **professional**, **structured** Git commit messages based on your staged changes. It follows best practices for message formatting (title under 50 characters, summary section, detailed notes, etc.) and offers an **interactive commit workflow**.

---

#### Overview

- **Automatic branch & diff detection**  
  Scans your current Git branch and staged changes to gather context.
- **Intelligent commit messages**  
  Uses Claude AI to parse file diffs and create concise, action-oriented messages.
- **Structured formatting**  
  Splits commit text into a short title, summary (the "why"), and details (the "what/how").
- **Interactive commit + push**  
  Optionally push your changes immediately after reviewing the AI-generated message.
- **Commit history logging**  
  Stores commit message logs (with timestamps) to keep a personal record of generated messages.

---

#### Features

1. **Title line under 50 characters**  
   - Starts with a capital verb (e.g., "Add," "Fix," "Update").
2. **Summary section**  
   - Explains the "why" in 2–3 sentences.
3. **Details section**  
   - Uses bullet points for key technical changes or additional info.
4. **Files Changed**  
   - Mentions changed files, grouped logically and explained briefly.
5. **User Prompt**  
   - Allows you to add extra context for the AI to incorporate into the commit message.
6. **Interactive Approval**  
   - Prompts you to "approve or reject" the AI-generated commit text before actually committing.
7. **Optional Push**  
   - If you approve, you can also push to remote in the same workflow.

---


#### Usage

Stage your changes as usual:

```bash
git add .
```

Run the script:

```bash
python CreateGitCommitMsg.py
```

Or if you have a direct alias or console script set up:

```bash
CreateGitCommitMsg
```

- Enter your own commit context (e.g., "Refactor login logic for clarity").
- The script:
  - Gathers your staged diff,
  - Sends it to Claude AI for analysis,
  - Returns a formatted commit message (with Title, Summary, and Details).
- Review the message displayed in the console.
- If you confirm "y", it commits with that message and optionally pushes.
- If you decline "n", it aborts and lets you try again or exit.

#### Example

**User Prompt**

```plaintext
Enter Your Commit Message: Refactor login flow, remove unused functions
```

**AI-Generated Commit Message might look like:**

```plaintext
Refactor login flow

Summary:
Streamline the login process by removing redundant calls and
improving error-handling for failed authentications.

Details:
- Removed duplicate validation methods
- Updated error messages in auth helpers
- Deleted unused login_utils.py functions

Files Changed:
- auth.py: consolidated login checks
- login_utils.py: removed deprecated methods
```

The script shows you this commit text, and asks:

```plaintext
✋ Do you want to commit with this message? (y/n):
```

Approve with "y" to commit, then it prompts:

```plaintext
🚀 Do you want to push these changes? (y/n):
```

If you choose "y", it pushes your branch to remote.

#### Implementation Details

- **AI Prompting**: Claude AI is called twice:
  - **Diff Parsing**: A system prompt instructs Claude to parse the git diff into a structured summary of changes (files, lines added/deleted, key changes).
  - **Commit Message Generation**: Another system prompt instructs Claude to produce a high-quality commit message from that structured diff, plus any user-provided context.
- **Commit History Logging**: The script writes out the full prompt text to a time-stamped file (in Commit_Logs) for reference, so you can review later what was sent to the AI. File names are sanitized for cross-platform compatibility and truncated to avoid Windows path length issues.
- **Error Handling & Edge Cases**:
  - Checks if the current directory is a valid Git repo.
  - If Claude's response is invalid or parsing fails, it falls back to a basic structure.
  - If the user aborts the commit, no changes are committed or pushed.

---

### CreateGitProgressReport.py

Below is detailed documentation for the Git Progress Report Generator script.

#### Overview

This Python script analyzes Git commits since the last run and generates a structured progress report, leveraging Anthropic's Claude AI to categorize commit messages by type and scope. It is especially useful for summarizing changes at the end of a sprint or for daily standups.

#### Features

- Tracks last run time per repository + branch (using `last_run.yaml`).
- Analyzes commit messages with Claude AI to extract a short summary, change type, scope, files changed, and impact level.
- Organizes commits by type (feat/fix/refactor/docs/style/test/chore) and scope.
- Generates a concise, bullet-pointed report ready for standups or release notes.
- Optional clipboard copy of the final report.

#### Requirements

- Python 3.6+
- `gitpython`, `pyperclip`, `python-dotenv`, `pyyaml`, `anthropic`
- A `.env` file containing `ANTHROPIC_API_KEY=your_claude_api_key_here`.

#### Usage

- Run the script within a Git repository (so it can detect commits on the active branch).

  ```bash
  CreateGitProgressReport
  ```

- The script finds commits since your last run (or 3 AM of the current day if no prior run is recorded).
- A report is displayed in the terminal.
- You can copy the final report to your clipboard by pressing "y" when prompted; pressing "n" keeps it in the console only.
- If you approve and copy the report, the script updates your `last_run.yaml` to record the new run time. If not, the run time remains unchanged.

#### Command-Line Arguments

| Argument               | Short Flag | Description                                                                 |
|------------------------|------------|-----------------------------------------------------------------------------|
| `--recent-commits [N]` | `-rc [N]`  | Interactively select a commit from the last N commits (default 5). You can then analyze all commits after that point. |
| `--since "DATE/TIME"`  | `-s "DATE/TIME"` | Start date/time (e.g. "2025-01-01", "2025-01-01 14:30:00")                  |
| `--until "DATE/TIME"`  | `-u "DATE/TIME"` | End date/time (default is now)                                              |
| `--date "DATE"`        | `-d "DATE"` | Shorthand for --since; sets a start date (e.g. "2025-01-01")                |

Dates/times are parsed in multiple common formats (e.g. YYYY-MM-DD, MM/DD/YYYY, with optional times).

#### Examples

- Use default since-last-run

  ```bash
  CreateGitProgressReport
  ```

  or:

  ```bash
  python CreateGitProgressReport.py
  ```

- Select from the last 10 commits

  ```bash
  CreateGitProgressReport --recent-commits 10
  ```

  The script displays commit titles, lets you pick one as a starting point, then summarizes everything after it.

- Specify an explicit date range

  ```bash
  CreateGitProgressReport --since "2025-01-01" --until "2025-01-31"
  ```

  or, using short flags:

  ```bash
  CreateGitProgressReport -s "2025-01-01" -u "2025-01-31"
  ```

#### How It Works

- Determines the 'start date/time' (from `--recent-commits`, `--since`, `--date`, or `last_run.yaml`).
- Pulls commits from `start_datetime` to `end_datetime`.
- Sends commit data (message + file stats) to Claude AI for analysis.
- Groups commits by type and scope.
- Generates a concise, AI-written bullet-list of changes.
- Prompts to copy the summary to clipboard and updates `last_run.yaml` if confirmed.

#### YAML Storage (last_run.yaml)

- Stored beside the script.
- Tracks the last run time per `[repo]_[branch]`.
- Updated after a successful run (if you choose to copy the report).

---

### CreateGitBranchName.py

A Python script that uses Claude AI (Anthropic) to generate **standardized** and **descriptive** Git branch names. It enforces best practices like consistent naming conventions, date prefixes, and concise descriptions.

---

#### Overview

- **Generates 5 branch name suggestions** based on a user-provided description.
- **Ensures naming convention compliance** (kebab-case, type prefix, 50-char max length).
- **Automatically adds a date prefix** (e.g. `YYYY/MM/DD-feat-branch-description`).
- **Integrates with Claude AI** to produce clear, well-structured suggestions.
- **Provides an interactive selection** to create a new Git branch directly.

---

#### Features

1. **Kebab-case format**  
   Lowercase letters and hyphens only.  
2. **Prefixed by type**  
   (`feat`, `fix`, `refactor`, `docs`, `style`, `test`, `hotfix`).  
3. **Short branch descriptions**  
   Under 50 characters (including the type).  
4. **Date stamping**  
   Adds `YYYY/MM/DD-` to the front of the final branch name.  
5. **Clipboard copy** *(optional)*  
   Although the current script clones and checks out the branch directly, it can be adapted to simply copy names to the clipboard if desired.  
6. **Graceful error handling**  
   - Detects non-Git folders.  
   - Prevents creating a branch if it already exists.  
   - Handles invalid input selections.

---

#### Usage

Place the script (e.g. CreateGitBranchName.py) in your project or somewhere on your PATH.

In a Git repository, run the script:

```bash
python CreateGitBranchName.py
```

Or if you have a direct alias/console script set up:

```bash
CreateGitBranchName
```

- Enter a short description of your changes or feature when prompted.
- View suggestions (the script prints five possible branch names):

```plaintext
1. feat/add-cool-feature - A branch to add cool feature
2. fix/typo-error - ...
...
```

- Select a branch by number (1–5). The script will:
  - Insert the date prefix to create a final name, e.g. `2025/01/30-feat-add-cool-feature`.
  - Prompt for confirmation to create and switch to that new branch.
  - Check out the new branch automatically if you confirm "y".

#### Example

Assume you want to add a new user authentication flow:

- Run the tool:

  ```bash
  python CreateGitBranchName.py
  ```

- Provide a description:

  ```plaintext
  📝 Describe the changes you'll make in this branch: user authentication flow
  ```

- Receive suggestions like:

  ```plaintext
  1. feat/user-auth - Branch for user authentication flow
  2. fix/auth-typo - ...
  3. ...
  ```

- Choose "1":

  ```plaintext
  📋 Enter the number of the branch name you would like to create (or 'q' to quit): 1
  ```

- The script forms a new branch name with a date prefix, e.g. `2025/01/30-feat-user-auth`, and asks:

  ```plaintext
  🤔 Create new branch '2025/01/30-feat-user-auth'? (y/n):
  ```

- Confirm "y". The script creates and checks out the branch:

  ```plaintext
  ✅ Created and switched to new branch: 2025/01/30-feat-user-auth
  ```

#### Implementation Details

- **AI Prompt**: Sends a system prompt to Claude specifying rules for the branch name format.
- **YAML Parsing**: The AI response is expected in strict YAML, which is parsed using `pyyaml`.
- **GitPython**: Used to check if the current directory is a valid Git repo and create the new branch if requested.
- **Date Prefix**: The script automatically calculates `YYYY/MM/DD-` and prepends it to the AI-suggested branch name.
- **Error Handling**:
  - If a branch name already exists, the script notifies you and does not overwrite it.
  - If any issue arises in parsing the AI output, it logs the raw response for troubleshooting.
