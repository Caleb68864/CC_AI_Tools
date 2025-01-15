"""
Git Branch Name Generator
------------------------
A tool that uses AI to generate standardized, descriptive git branch names.

Features:
- Generates 5 branch name suggestions based on your description
- Uses Claude AI to ensure naming convention compliance
- Automatically adds date prefix (YYYYMMDD/)
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
- Python packages: pyperclip, python-dotenv, pyyaml, anthropic

Usage:
1. Run the script
2. Enter a description of your planned changes
3. Select from generated branch name suggestions
4. Selected name is copied to clipboard with date prefix
"""

import anthropic
import os
import pyperclip
import dotenv
from datetime import datetime
import yaml
dotenv.load_dotenv()

def get_branch_suggestions(description):
    """Get branch name suggestions from Claude"""
    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    
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
        "2. Start with type (feat/fix/refactor/docs/style/test/hotfix)\n"
        "3. Include a brief but clear description\n"
        "4. Keep total length under 50 characters\n"
        "5. No special characters except hyphens\n"
        "6. Make each unique and specific\n\n"
        "Return ONLY the YAML, no other text."
    )

    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=300,
        temperature=0.7,
        system=prompt,
        messages=[
            {"role": "user", "content": description}
        ]
    )
    
    return response.content[0].text.strip()

def main():
    print("🌿 Git Branch Name Generator")
    print("=" * 50)
    
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
                choice = input("\n📋 Enter the number of the branch name to copy (or 'q' to quit): ")
                
                if choice.lower() == 'q':
                    break
                    
                choice = int(choice)
                
                if 1 <= choice <= len(branch_names):
                    # Get branch name from our parsed list
                    branch_name = branch_names[choice-1]
                    
                    # Add date prefix
                    date_prefix = datetime.now().strftime('%Y%m%d/')
                    branch_name = f"{date_prefix}{branch_name}"
                    
                    pyperclip.copy(branch_name)
                    print(f"\n✅ Copied to clipboard: {branch_name}")
                else:
                    print("❌ Invalid number. Please try again.")
                    
            except (ValueError, IndexError) as e:
                print("❌ Please enter a valid number or 'q' to quit.")
                
    except yaml.YAMLError as e:
        print(f"❌ Error parsing suggestions: {e}")
        print("Raw response:", yaml_response)

if __name__ == "__main__":
    main()
