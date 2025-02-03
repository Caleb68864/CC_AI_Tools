"""
Git Branch Name Generator
------------------------
A tool that uses AI to generate standardized, descriptive git branch names.

Features:
- Generates 5 branch name suggestions based on your description
- Uses Claude AI to ensure naming convention compliance
- Automatically adds date prefix (YYYY/MM/DD-type-description)
- Follows git branch naming best practices
- Provides one-click clipboard copy

Branch naming rules:
- Uses kebab-case (lowercase with hyphens)
- Starts with type (feat/fix/refactor/docs/style/test/hotfix)
- Includes brief but clear description
- Keeps total length under 50 characters
- No special characters except hyphens

Requirements:
- Anthropic API key in .env file (ANTHROPIC_API_KEY)
- Python packages: python-dotenv, pyyaml, anthropic, git

Usage:
1. Run the script
2. Enter a description of your planned changes
3. Select from generated branch name suggestions
4. Selected name is used to create a new branch
"""

import os
import dotenv
from datetime import datetime
import yaml
# Use git_utils for all Git-related operations instead of using git directly
from git_utils import get_repo, create_new_branch
from AI.ai_client import AIClient  # Importing the reusable AI client

def get_branch_suggestions(description):
    """Get branch name suggestions from Claude using AIClient."""
    prompt = (
        "Generate 5 git branch names based on the provided description. Return the response in YAML format like this:\n"
        "suggestions:\n"
        "  - number: 1\n"
        "    name: feat/example-branch\n"
        "    description: Brief explanation of the branch\n"
        "  - number: 2\n"
        "    name: fix/another-example\n"
        "    description: Another brief explanation\n\n"
        "Rules for branch names:\n"
        "1. Use kebab-case (lowercase with hyphens)\n"
        "2. Start with type (feat/fix/refactor/docs/style/test/hotfix) only use these types\n"
        "3. Include a brief but clear description\n"
        "4. Keep total length under 50 characters\n"
        "5. No special characters except hyphens\n"
        "6. Make each unique and specific\n\n"
        "Return ONLY the YAML, no other text."
    )
    
    ai_client = AIClient(
        model=os.getenv("CLAUDE_SMALL_MODEL", "claude-3-haiku-20240307"),
        max_tokens=300,
        temperature=0.7
    )
    
    response_text = ai_client.get_response(system_prompt=prompt, user_message=description)
    return response_text

def create_git_branch_name():
    """Main function to create a git branch name"""
    print("RUNNING: Git Branch Name Generator")
    print("🌿 Git Branch Name Generator")
    print("=" * 50)
    
    # Initialize git repo using git_utils
    try:
        repo = get_repo()
    except Exception as e:
        print("❌", e)
        return

    description = input("\n📝 Describe the changes you'll make in this branch: ")
    
    print("\n🤖 Generating branch name suggestions...")
    yaml_response = get_branch_suggestions(description)
    
    try:
        # Parse YAML response
        suggestions = yaml.safe_load(yaml_response)
        branch_names = []
        
        print("\nSuggested branch names:")
        print("=" * 50)
        for suggestion in suggestions['suggestions']:
            print(f"{suggestion['number']}. {suggestion['name']} - {suggestion['description']}")
            branch_names.append(suggestion['name'])
        print("=" * 50)
        
        while True:
            try:
                choice = input("\n📋 Enter the number of the branch name you would like to create (or 'q' to quit): ")
                
                if choice.lower() == 'q':
                    break
                    
                choice = int(choice)
                
                if 1 <= choice <= len(branch_names):
                    # Get branch name from our parsed list
                    branch_name = branch_names[choice - 1]
                    
                    # Split the branch name into type and description
                    type_desc = branch_name.split('/', 1)
                    if len(type_desc) == 2:
                        branch_type = type_desc[0]
                        description_part = type_desc[1]
                    else:
                        branch_type = "feat"  # default type if not found
                        description_part = branch_name
                    
                    # Format date and branch name
                    now = datetime.now()
                    branch_name_formatted = f"{now.year}/{now.month:02d}/{now.day:02d}-{branch_type}-{description_part}"
                    
                    # Ask for confirmation
                    confirm = input(f"\n🤔 Create new branch '{branch_name_formatted}'? (y/n): ")
                    
                    if confirm.lower() == 'y':
                        try:
                            # Create and checkout branch using git_utils
                            created_branch = create_new_branch(branch_name_formatted)
                            print(f"\n✅ Created and switched to new branch: {created_branch}")
                        except Exception as e:
                            print(f"\n❌ {e}")
                    break
                else:
                    print("❌ Invalid number. Please try again.")
                    
            except (ValueError, IndexError):
                print("❌ Please enter a valid number or 'q' to quit.")
                
    except yaml.YAMLError as e:
        print(f"❌ Error parsing suggestions: {e}")
        print("Raw response:", yaml_response)

if __name__ == "__main__":
    create_git_branch_name()
