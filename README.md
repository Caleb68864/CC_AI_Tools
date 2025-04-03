# CC AI Tools
Productivity Tools Using AI

## Installation

First, clone the repository and navigate to the project directory:

```bash
git clone https://github.com/Caleb68864/CC_AI_Tools
cd CCAITools
```

Install the package and its dependencies using pip:

```bash
pip install .
```

For development installation with editable mode:

```bash
pip install -e .
```

### PowerShell Setup (Windows)

Run the included PowerShell installation script to set up command-line aliases and environment files:

**Note:** You may need to run this script with administrator privileges.

```powershell
# Standard installation (pulls Production branch)
.\install_Scripts.ps1

# Development mode (skips Production branch)
.\install_Scripts.ps1 -dev
# or
.\install_Scripts.ps1 -d
```

This script will:
- By default, checkout and pull the latest Production branch (skip with -dev flag)
- Create global PowerShell functions for all Python scripts, allowing them to run from any location
- Automatically set up `.env` files from `.env.example` templates if they don't exist
- Enable you to run scripts by their name without the `.py` extension (e.g., `CreateGitCommitMsg` instead of `python CreateGitCommitMsg.py`)

### Setup

The PowerShell installation script (`install_Scripts.ps1`) will automatically create a `.env` file from `.env.example` if it doesn't exist. You can then edit the `.env` file with your settings:

**Required API Keys:**
- `API_KEY=your_api_key_here` (deprecated)
- `ANTHROPIC_API_KEY=your_claude_api_key_here`
- `GIT_USERNAME=your_username` (for branch naming)

**Optional AI Model Settings:**
- `CLAUDE_SMALL_MODEL=claude-3-haiku-20240307`
- `CLAUDE_MEDIUM_MODEL=claude-3-5-sonnet-20240620`
- `CLAUDE_LARGE_MODEL=claude-3-5-sonnet-20240620`

The AI model settings allow you to specify which Claude models to use for different tasks. If not set, the scripts will use default values.

## Feature Requests

## Changelog

### v1.0.3 - Username Integration and Installation Improvements
- Added GIT_USERNAME support in .env file for consistent branch naming
- Implemented automatic username validation and formatting for branch names
- Added fallback to AI-generated branch names when username is not set
- Enhanced install_Scripts.ps1 to support Production branch deployment
- Added -dev/-d flag to skip Production branch checkout during installation
- Improved .env file handling with automatic username updates

### v1.0.2 - Smart File Staging
- Added intelligent handling of file staging to preserve already staged changes
- Detects if files are already staged when running `CreateGitCommitMsg`
- Asks users if they want to work with already staged files or stage additional ones
- Displays numbered lists of unstaged files for easy selection
- Supports selective staging through individual numbers or ranges (e.g., `1`, `1,3`, `2-4`)
- Defaults to staging all files if no specific selection is provided
- Generates commit messages based only on the final set of staged files
- Provides a more streamlined and flexible git workflow

### v1.0.1 - Customizable Branch Names
- Added an option to choose between AI suggestions or custom branch creation
- Presents users with a list of branch types to select from (feat, fix, refactor, docs, style, test, hotfix)
- Ensures users select a type before entering their description
- Formats input into a properly structured name (YYYY/MM/DD-HHMM-type-description)
- Displays the complete branch name for confirmation
- If the user doesn't confirm, provides options to try again, use AI suggestions instead, or quit
- Defaults to AI suggestions when no option is selected (press Enter)
- Provides a clean exit option at key decision points

### v1.0.0 - Default Yes for Y/N Questions
- Added a utility function `prompt_yes_no()` that displays prompts with "(Y/n)" format
- When the user presses Enter without typing anything, the function returns `True` (equivalent to "yes")
- All interactive prompts across Git tools have been updated to use this function
- The prompt format clearly indicates that "Y" is the default option by using capital "Y"

## Git Tools

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
- **Smart file staging**  
  Preserves already staged changes and offers selective staging of additional files.
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
5. **Smart File Staging**  
   - Detects already staged changes and asks if you want to keep or add to them
   - Displays numbered lists of unstaged files for easy selection
   - Supports selective staging through individual numbers or ranges (e.g., `1`, `1,3`, `2-4`)
   - Defaults to staging all files if no specific selection is provided
6. **User Prompt**  
   - Allows you to add extra context for the AI to incorporate into the commit message.
7. **Interactive Approval**  
   - Prompts you to "approve or reject" the AI-generated commit text before actually committing.
8. **Optional Push**  
   - If you approve, you can also push to remote in the same workflow.

---


#### Usage

You can stage your changes before running the script, or let the script help you stage files:

Run the script:

```bash
python CreateGitCommitMsg.py
```

Or if you have a direct alias or console script set up:

```bash
CreateGitCommitMsg
```

- If you have already staged changes, the script will:
  - Show you the list of staged files
  - Ask if you want to work with these files or stage additional ones
  - If you choose to stage more, it will display unstaged files with numbers for selection

- If no files are staged yet, the script will:
  - Show you a list of all unstaged files with numbers
  - Let you select specific files by entering numbers or ranges (e.g., `1`, `1,3`, `2-4`)
  - Stage all files if you just press Enter without selecting any

- Enter your own commit context (e.g., "Refactor login logic for clarity").
- The script:
  - Analyzes your staged changes,
  - Sends the diff to Claude AI for analysis,
  - Returns a formatted commit message (with Title, Summary, and Details).
- Review the message displayed in the console.
- If you confirm "y", it commits with that message and optionally pushes.
- If you decline "n", it aborts and lets you try again or exit.

#### Example

**File Staging**

```plaintext
📝 Analyzing changes...
🔍 Found 2 already staged files:
  1. src/auth.py
  2. src/login_utils.py

Do you want to work with these staged files? (Y/n): n

📋 Unstaged files (3):
  1. src/config.py
  2. src/utils.py
  3. README.md

🔢 Enter file numbers to stage (e.g., '1,3,5-7', or press Enter for all): 1,3
📌 Staging 2 additional files...
✅ Files staged successfully.
```

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

A Python script that uses Claude AI (Anthropic) to generate **standardized** and **descriptive** Git branch names. It enforces best practices like consistent naming conventions, date prefixes, and concise descriptions. The script now supports personalized branch naming with usernames and provides AI-powered fallback options.

---

#### Overview

- **Generates 5 branch name suggestions** based on a user-provided description
- **Allows custom branch creation** with user-selected type and description
- **Ensures naming convention compliance** (kebab-case, type prefix, 50-char max length)
- **Automatically adds a date prefix** (e.g. `YYYY/MM/DD-HHMM-username-feat-branch-description`)
- **Integrates with Claude AI** to produce clear, well-structured suggestions
- **Provides an interactive selection** to create a new Git branch directly
- **Username Integration** for consistent branch ownership tracking
- **Smart AI Fallback** when username is not configured

---

#### Features

1. **Kebab-case format**  
   Lowercase letters and hyphens only.  
2. **Username Integration**  
   - Reads username from `.env` file (`GIT_USERNAME`)
   - Automatically formats username for branch naming
   - Prompts for username if not found or blank
   - Updates `.env` file with provided username
3. **AI Fallback System**  
   - Provides AI-generated branch names if username is not set
   - Maintains consistent naming structure even without username
   - Can switch between personal and AI-generated formats
4. **Prefixed by type**  
   (`feat`, `fix`, `refactor`, `docs`, `style`, `test`, `hotfix`)  
5. **Short branch descriptions**  
   Under 50 characters (including the type)  
6. **Date stamping**  
   Adds `YYYY/MM/DD-HHMM-` to the front of the final branch name  
7. **Custom branch creation**  
   Choose your own branch type and description without using AI suggestions
8. **Graceful error handling**  
   - Detects non-Git folders
   - Prevents creating a branch if it already exists
   - Handles invalid input selections
   - Provides options to try again, switch methods, or quit

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

**Username Configuration**
- The script checks for `GIT_USERNAME` in your `.env` file
- If not found or blank, you'll be prompted to enter your username
- Usernames are automatically formatted for branch naming (lowercase, no spaces)
- Your username is saved to `.env` for future use

**Option 1: AI-Generated Suggestions**
- Choose option 1 (default) when prompted
- Enter a short description of your changes or feature
- View suggestions (the script prints five possible branch names)
- Select a branch by number (1–5) or choose option 6 to create a custom branch instead
- Confirm the final branch name with date and username prefix
- Optionally push to remote

**Option 2: Custom Branch Creation**
- Choose option 2 when prompted
- Select a branch type from the list (feat, fix, refactor, docs, style, test, hotfix)
- Enter a description for your branch
- Confirm the final branch name with date and username prefix
- Optionally push to remote

```plaintext
📝 Checking username configuration...
❓ Username not found in .env file. Please enter your username: johndoe
✅ Username saved to .env file

🔄 Branch Creation Options:
1. Generate AI suggestions based on description (default)
2. Create custom branch name

🔖 Select an option (1/2, default: 1): 2

Available branch types:
==================================================
1. feat
2. fix
3. refactor
4. docs
5. style
6. test
7. hotfix
==================================================

🔖 Select a branch type (enter number): 1

📝 Enter a description for your feat branch: user authentication system

🤔 Create new branch '2024/03/20-1423-johndoe-feat-user-authentication-system' from 'main'? (Y/n):
```

If you don't confirm the branch name, you'll be presented with options to:
- Try creating a custom branch again
- Use AI suggestions instead
- Quit the script

#### Implementation Details

- **AI Prompt**: Sends a system prompt to Claude specifying rules for the branch name format.
- **YAML Parsing**: The AI response is expected in strict YAML, which is parsed using `pyyaml`.
- **GitPython**: Used to check if the current directory is a valid Git repo and create the new branch if requested.
- **Date Prefix**: The script automatically calculates `YYYY/MM/DD-HHMM-` and prepends it to the branch name.
- **Error Handling**:
  - If a branch name already exists, the script notifies you and does not overwrite it.
  - If any issue arises in parsing the AI output, it logs the raw response for troubleshooting.

## Cursor IDE

### ApplyCursorRules.py

A Python script that manages Cursor IDE rules for your project, allowing you to selectively apply coding standards, documentation requirements, and other development guidelines.

#### Overview

- **Interactive Rule Selection** via a searchable GUI interface
- **Rule Version Control** with automatic archiving of removed rules
- **Organized Rule Categories** for easy navigation
- **Change Tracking** showing added and removed rules
- **Automatic .cursor Directory Management**

#### Features

1. **Visual Rule Selection**
   - Hierarchical view of available rules
   - Group checkboxes to select/deselect categories
   - Search functionality to filter rules
   - Current project rules auto-selected

2. **Rule Management**
   - Automatically creates `.cursor/rules` directory
   - Archives removed rules with timestamps
   - Maintains rule history in `.cursor/.trash`
   - Shows summary of changes after updates

3. **Project Integration**
   - Works with existing Cursor IDE configurations
   - Preserves custom rule modifications
   - Compatible with version control systems

#### Usage

Run the script from your project's root directory:

```bash
python ApplyCursorRules.py
```

Or if you have the alias set up:

```bash
ApplyCursorRules
```

⚠️ **Important**: Always run this script from your project's root directory (where your `.git` folder is located). This ensures that:
- Rules are installed in the correct `.cursor` directory
- All project files can access the rules
- Version control properly tracks rule changes

1. A window appears showing available rules grouped by category
2. Use the search box to filter rules by name
3. Select/deselect individual rules or entire categories
4. Click "Confirm Selection" to apply changes
5. Review the summary of added/removed rules

#### Example Output

```plaintext
Rules copied successfully to: /your/project/.cursor/rules

Added rules:
  • comment-maintenance.mdc
  • code-style.mdc

Removed rules:
  • old-standard.mdc
```

The script maintains a clean, organized rule structure while preserving history of removed rules in case you need to reference them later.
