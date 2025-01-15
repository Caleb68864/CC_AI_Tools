# CC AI Tools
Productivity Tools Using AI


## Git
### Setup
Create a .env in the same folder as the script with following line containing your openai api key.
- API_KEY=your_api_key_here
- ANTHROPIC_API_KEY=your_claude_api_key_here

### Git Tools
#### CreateGitCommitMsg.py
 * AI-powered tool that analyzes staged changes and generates professional commit messages
 * Automatically detects current branch and git diff content
 * Creates structured messages with title, summary, and detailed changes
 * Provides interactive commit and push workflow
 * Maintains commit message history with timestamps
##### How to use
 * Run the script
 * Enter a comment describing the changes you want to commit
 * Approve or Disapprove the generated commit message
   * If approved, the message is copied to clipboard
   * If disapproved, the message is not copied to clipboard and the script will prompt you again.

#### CreateGitProgressReport.py
 * Generates structured progress reports from git commit history
 * Tracks last run time per repository and branch
 * Uses AI to categorize and group related changes
 * Organizes changes by type (feat/fix/refactor) and scope
 * Outputs concise, bullet-pointed summaries
 * Includes clipboard copy functionality
##### How to use
 * Run the script
 * If the output is acceptable, press y.
   * The report is copied to clipboard.
   * The last run time is updated in the .yaml file.
 * If the output is not acceptable, press n.
   * The script will exit.
   * The last run time is not updated in the .yaml file.

#### CreateGitBranchName.py
 * AI-powered tool for generating standardized git branch names
 * Follows git branch naming best practices and conventions
 * Automatically adds date prefix (YYYYMMDD/)
 * Generates 5 unique suggestions based on your description
 * Uses kebab-case with proper type prefixes (feat/fix/refactor/etc.)
 * Ensures names are clear, concise, and under 50 characters
 * Includes one-click clipboard copy functionality 
##### How to use
 * Run the script
 * Enter a description of the changes you want to make
 * Select from generated branch name suggestions by entering the number of the name you want to use.
 * The selected name is copied to clipboard with date prefix.
 * The script will remain open until you press q to exit.
   * This allows you to select multiple names and copy them to clipboard.
