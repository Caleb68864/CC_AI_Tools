"""
Git Branch Name Generator
------------------------
A tool that uses AI to generate standardized, descriptive git branch names.

Features:
- Generates 5 branch name suggestions based on your description
- Uses Claude AI to ensure naming convention compliance
- Automatically adds date prefix (YYYY/MM/DD-type-description)
- Includes username in branch name
- Follows git branch naming best practices
- Provides one-click clipboard copy
- Allows custom branch name creation with type selection

Branch naming rules:
- Uses kebab-case (lowercase with hyphens)
- Format: YYYY/MM/DD-HHMM-username-type-description
- Starts with type (feat/fix/refactor/docs/style/test/hotfix)
- Includes brief but clear description
- Keeps total length under 50 characters
- No special characters except hyphens

Requirements:
- Anthropic API key in .env file (ANTHROPIC_API_KEY)
- Username in .env file (GIT_USERNAME)
- Python packages: python-dotenv, pyyaml, anthropic, git
"""

import os
import sys
import dotenv
import yaml
import re
from datetime import datetime
from pathlib import Path

# Add the src directory to the Python path
src_dir = str(Path(__file__).resolve().parents[2])
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from cc_ai_tools.ai.client import AIClient
from cc_ai_tools.git.utils import get_repo, create_new_branch, get_current_branch, prompt_yes_no
from cc_ai_tools.utils.interrupt_handler import handle_interrupt

# Get the project root directory (where .env should be located)
project_root = Path(__file__).resolve().parents[3]

# Load environment variables from project root
dotenv.load_dotenv(project_root / '.env')

# Define branch types
BRANCH_TYPES = ["feat", "fix", "refactor", "docs", "style", "test", "hotfix"]

def get_branch_suggestions(description: str) -> str:
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
    
    return ai_client.get_response(system_prompt=prompt, user_message=description)

def sanitize_username(username: str) -> str:
    """Convert username to git branch name compatible format."""
    # Convert to lowercase
    username = username.lower()
    # Replace spaces and special characters with hyphens
    username = re.sub(r'[^a-z0-9]+', '-', username)
    # Remove leading/trailing hyphens
    return username.strip('-')

def get_or_create_username() -> str:
    """Get username from .env file or prompt user to create one."""
    username = os.getenv('GIT_USERNAME', '').strip()
    env_path = project_root / '.env'
    
    if not username:
        print("\n⚠️ No username found in .env file")
        while True:
            try:
                username = input("👤 Please enter your username: ").strip()
            except KeyboardInterrupt:
                handle_interrupt()
                
            if username:
                # Sanitize the username
                sanitized = sanitize_username(username)
                print(f"\nYour sanitized username will be: {sanitized}")
                try:
                    if prompt_yes_no("Is this username correct?"):
                        # Check if .env file exists and if GIT_USERNAME is already present
                        if env_path.exists():
                            with open(env_path, 'r') as f:
                                env_contents = f.read()
                            
                            if 'GIT_USERNAME=' in env_contents:
                                # Replace existing GIT_USERNAME line
                                new_contents = re.sub(
                                    r'GIT_USERNAME=.*',
                                    f'GIT_USERNAME={sanitized}',
                                    env_contents
                                )
                                with open(env_path, 'w') as f:
                                    f.write(new_contents)
                            else:
                                # Append new GIT_USERNAME line
                                with open(env_path, 'a') as f:
                                    f.write(f"\nGIT_USERNAME={sanitized}")
                        else:
                            # Create new .env file
                            with open(env_path, 'w') as f:
                                f.write(f"GIT_USERNAME={sanitized}")
                        
                        print("✅ Username saved to .env file")
                        return sanitized
                except KeyboardInterrupt:
                    handle_interrupt()
            else:
                print("❌ Username cannot be empty. Please try again.")
    
    return username

def format_branch_name(branch_type: str, description: str) -> str:
    """Format branch name with date prefix, username and proper formatting."""
    # Get username
    username = get_or_create_username()
    
    # Convert to kebab-case (lowercase with hyphens)
    description = description.lower()
    # Replace spaces and special characters with hyphens
    description = re.sub(r'[^a-z0-9]+', '-', description)
    # Remove leading/trailing hyphens
    description = description.strip('-')
    
    # Format date and branch name
    now = datetime.now()
    return f"{now.year}/{now.month:02d}/{now.day:02d}-{now.hour:02d}{now.minute:02d}-{username}-{branch_type}-{description}"

def display_branch_types():
    """Display available branch types for selection."""
    print("\nAvailable branch types:")
    print("=" * 50)
    for i, branch_type in enumerate(BRANCH_TYPES, 1):
        print(f"{i}. {branch_type}")
    print("=" * 50)

def get_branch_type_selection() -> str:
    """Get branch type selection from user."""
    display_branch_types()
    
    while True:
        try:
            choice = input("\n🔖 Select a branch type (enter number): ")
            choice = int(choice)
            
            if 1 <= choice <= len(BRANCH_TYPES):
                return BRANCH_TYPES[choice - 1]
            else:
                print("❌ Invalid number. Please try again.")
        except KeyboardInterrupt:
            handle_interrupt()
        except ValueError:
            print("❌ Please enter a valid number.")

def create_custom_branch():
    """Create a custom branch name with user input."""
    # Get branch type
    branch_type = get_branch_type_selection()
    
    # Get description
    while True:
        try:
            description = input(f"\n📝 Enter a description for your {branch_type} branch: ")
            if description.strip():
                break
            print("❌ Description cannot be empty. Please try again.")
        except KeyboardInterrupt:
            handle_interrupt()
    
    # Format branch name
    branch_name = format_branch_name(branch_type, description)
    
    return branch_type, description, branch_name

def create_git_branch_name():
    """Main function to create a git branch name"""
    print("RUNNING: Git Branch Name Generator")
    print("🌿 Git Branch Name Generator")
    print("=" * 50)
    
    # Initialize git repo using git_utils
    try:
        repo = get_repo()
        current_branch = get_current_branch()
    except Exception as e:
        print("❌", e)
        return

    # Ask user if they want to create a custom branch or use AI suggestions
    print("\n🔄 Branch Creation Options:")
    print("1. Generate AI suggestions based on description (default)")
    print("2. Create custom branch name")
    
    while True:
        try:
            option_input = input("\n🔖 Select an option (1/2, default: 1): ")
            
            # Default to option 1 if no input is given
            if option_input.strip() == "":
                option = 1
                break
                
            option = int(option_input)
            
            if option in [1, 2]:
                break
            else:
                print("❌ Invalid option. Please enter 1 or 2.")
        except KeyboardInterrupt:
            handle_interrupt()
        except ValueError:
            print("❌ Please enter a valid number.")
    
    # Option 1: AI-generated suggestions
    if option == 1:
        try:
            description = input("\n📝 Describe the changes you'll make in this branch: ")
        except KeyboardInterrupt:
            handle_interrupt()
        
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
            print(f"6. Create custom branch name instead")
            print("=" * 50)
            
            while True:
                try:
                    choice = input("\n📋 Enter the number of the branch name you would like to create (or 'q' to quit): ")
                    
                    if choice.lower() == 'q':
                        return
                        
                    choice = int(choice)
                    
                    if 1 <= choice <= len(branch_names):
                        branch_name = branch_names[choice - 1]
                        
                        # Split the branch name into type and description
                        type_desc = branch_name.split('/', 1)
                        if len(type_desc) == 2:
                            branch_type = type_desc[0]
                            description_part = type_desc[1]
                        else:
                            branch_type = "feat"
                            description_part = branch_name
                        
                        # Format date and branch name
                        branch_name_formatted = format_branch_name(branch_type, description_part)
                        
                        # Ask for confirmation with current branch information
                        try:
                            if prompt_yes_no(f"\n🤔 Create new branch '{branch_name_formatted}' from '{current_branch}'?"):
                                try:
                                    created_branch = create_new_branch(branch_name_formatted)
                                    print(f"\n✅ Created and switched to new branch: {created_branch}")
                                    
                                    # Ask about creating remote branch
                                    if prompt_yes_no("\n🌐 Would you like to push this branch to remote?"):
                                        try:
                                            repo.git.push('--set-upstream', 'origin', branch_name_formatted)
                                            print(f"✅ Successfully pushed branch to remote: origin/{branch_name_formatted}")
                                        except Exception as e:
                                            print(f"❌ Failed to push to remote: {e}")
                                except Exception as e:
                                    print(f"\n❌ {e}")
                            else:
                                # If user doesn't confirm, go back to the selection
                                continue
                        except KeyboardInterrupt:
                            handle_interrupt()
                        return
                    elif choice == 6:
                        # Switch to custom branch creation
                        option = 2
                        break
                    else:
                        print("❌ Invalid number. Please try again.")
                        
                except KeyboardInterrupt:
                    handle_interrupt()
                except (ValueError, IndexError):
                    print("❌ Please enter a valid number or 'q' to quit.")
                    
        except yaml.YAMLError as e:
            print(f"❌ Error parsing suggestions: {e}")
            print("Raw response:", yaml_response)
            # Fall back to custom branch creation
            option = 2
    
    # Option 2: Custom branch creation
    if option == 2:
        while True:
            branch_type, description, branch_name_formatted = create_custom_branch()
            
            # Ask for confirmation with current branch information
            try:
                if prompt_yes_no(f"\n🤔 Create new branch '{branch_name_formatted}' from '{current_branch}'?"):
                    try:
                        created_branch = create_new_branch(branch_name_formatted)
                        print(f"\n✅ Created and switched to new branch: {created_branch}")
                        
                        # Ask about creating remote branch
                        if prompt_yes_no("\n🌐 Would you like to push this branch to remote?"):
                            try:
                                repo.git.push('--set-upstream', 'origin', branch_name_formatted)
                                print(f"✅ Successfully pushed branch to remote: origin/{branch_name_formatted}")
                            except Exception as e:
                                print(f"❌ Failed to push to remote: {e}")
                    except Exception as e:
                        print(f"\n❌ {e}")
                    break
                else:
                    # If user doesn't confirm, ask if they want to try again or use AI suggestions
                    print("\n🔄 Options:")
                    print("1. Try creating a custom branch again")
                    print("2. Use AI suggestions instead")
                    print("q. Quit")
                    
                    while True:
                        try:
                            choice = input("\n🔖 Select an option (1/2/q): ").strip().lower()
                        except KeyboardInterrupt:
                            handle_interrupt()
                        
                        if choice == 'q':
                            print("\n👋 Exiting Git Branch Name Generator.")
                            return
                        elif choice == '1' or choice == '':
                            # Try creating a custom branch again
                            break
                        elif choice == '2':
                            # Use AI suggestions instead
                            create_git_branch_name()  # Restart the whole process
                            return
                        else:
                            print("❌ Invalid option. Please enter 1, 2, or q.")
                    
                    if choice == '1':
                        continue
                    else:
                        break
            except KeyboardInterrupt:
                handle_interrupt()

if __name__ == "__main__":
    try:
        create_git_branch_name()
    except KeyboardInterrupt:
        handle_interrupt() 