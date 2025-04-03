"""
Git Commit Message Generator
---------------------------
A tool that leverages AI to generate professional and structured Git commit messages.

Features:
- Automatically detects current branch and staged changes
- Analyzes git diff output using Claude AI
- Generates structured commit messages with title, summary, and detailed changes
- Provides interactive commit and push workflow
- Saves commit message history with timestamps
"""

import os
import sys
import dotenv
from datetime import datetime
from pathlib import Path
import concurrent.futures
import tqdm  # Add tqdm import

# Add the src directory to the Python path
src_dir = str(Path(__file__).resolve().parents[2])
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from cc_ai_tools.ai.client import AIClient
from cc_ai_tools.git.utils import (
    get_current_branch,
    stage_all_changes,
    get_diff_files,
    get_diff_output,
    commit_changes,
    push_changes,
    prompt_yes_no,
    has_staged_changes,
    get_staged_files,
    get_unstaged_files,
    stage_files,
    parse_file_selection
)
from cc_ai_tools.yaml.utils import parse_yaml_response
from cc_ai_tools.utils.interrupt_handler import handle_interrupt

# Load environment variables
dotenv.load_dotenv()

# Configure AI model
AI_TEMPERATURE = 0.2
AI_LARGE_MODEL = os.getenv("CLAUDE_LARGE_MODEL", "claude-3-5-sonnet-20240620")
AI_SMALL_MODEL = os.getenv("CLAUDE_SMALL_MODEL", "claude-3-haiku-20240307")

def parse_diff_to_structured(diff_output, diff_files):
    """Parse git diff into a structured format using Claude."""
    print("🤖 Parsing git diff with Claude Haiku...")
    
    # Check if the diff is too large (over 10,000 characters)
    # If so, we'll split it into chunks for better processing
    if len(diff_output) > 10000:
        print("📊 Large diff detected, processing in chunks...")
        return parse_large_diff(diff_output, diff_files)
    
    ai_client = AIClient(
        model=AI_SMALL_MODEL,
        max_tokens=1000,
        temperature=AI_TEMPERATURE
    )
    
    parse_prompt = (
        "Parse the following git diff into a structured format. For each file, provide:\n\n"
        "FILE SUMMARY\n"
        "- Name: <filename>\n"
        "- Type: <add/modify/delete>\n"
        "- Summary: Brief description of changes\n"
        "- Lines Added: <number>\n"
        "- Lines Deleted: <number>\n"
        "- Modified Functions: List of changed functions\n"
        "- Key Changes:\n"
        "  * Change 1\n"
        "  * Change 2\n\n"
        "OVERALL STATISTICS\n"
        "- Total Files Changed: <number>\n"
        "- Total Additions: <number>\n"
        "- Total Deletions: <number>\n"
        "- Changes By Type:\n"
        "  * Modified: <number>\n"
        "  * Added: <number>\n"
        "  * Deleted: <number>\n\n"
        "Important:\n"
        "- Be specific and technical in descriptions\n"
        "- Include actual function names from the code\n"
        "- Count real additions and deletions\n"
        "- Identify meaningful code changes, not just formatting\n"
        "- Group related changes together\n"
    )
    
    try:
        response_text = retry_ai_request(
            ai_client.get_response,
            system_prompt=parse_prompt,
            user_message=diff_output,
            max_retries=args.max_retries,
            initial_delay=1,
            timeout=args.commit_timeout
        )
        
        structured_diff = parse_text_response(response_text)

        return structured_diff

    except Exception as e:
        if "overloaded_error" in str(e):
            print(f"\n⚠️ Claude API is currently overloaded when parsing diff.")
            print("Using fallback structure...")
            return create_fallback_structure(diff_files)
        else:
            print(f"\n⚠️ Unexpected error when parsing diff: {str(e)}")
            return create_fallback_structure(diff_files)

def parse_large_diff(diff_output, diff_files):
    """Parse a large diff by splitting it into file-based chunks and processing in parallel."""
    # Split the diff by file
    file_diffs = {}
    current_file = None
    current_content = []
    
    for line in diff_output.split('\n'):
        if line.startswith('diff --git'):
            # Save previous file content if exists
            if current_file and current_content:
                file_diffs[current_file] = '\n'.join(current_content)
                current_content = []
            
            # Extract new filename
            try:
                current_file = line.split(' b/')[1]
            except IndexError:
                current_file = f"unknown_file_{len(file_diffs)}"
            
        # Add line to current file content
        if current_file:
            current_content.append(line)
    
    # Add the last file
    if current_file and current_content:
        file_diffs[current_file] = '\n'.join(current_content)
    
    # If we couldn't parse any files, fall back to the regular method
    if not file_diffs:
        print("⚠️ Could not split diff by files, using fallback structure...")
        return create_fallback_structure(diff_files)
    
    # Process each file diff in parallel
    file_results = []
    
    # Calculate chunk size based on total number of files
    chunk_size = max(1, len(file_diffs) // 5)  # Process in 5 chunks by default
    chunks = []
    current_chunk = {}
    
    # Split files into chunks
    for file_name, content in file_diffs.items():
        current_chunk[file_name] = content
        if len(current_chunk) >= chunk_size:
            chunks.append(current_chunk)
            current_chunk = {}
    
    # Add the last chunk if it has any files
    if current_chunk:
        chunks.append(current_chunk)
    
    # Process each chunk
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(chunks))) as executor:
        # Create a progress bar for chunk processing
        with tqdm.tqdm(total=len(file_diffs), desc="Processing files", unit="file") as pbar:
            for chunk_idx, chunk in enumerate(chunks, 1):
                # Process files in the current chunk
                chunk_futures = {
                    executor.submit(parse_single_file_diff, file_name, file_content): file_name
                    for file_name, file_content in chunk.items()
                }
                
                for future in concurrent.futures.as_completed(chunk_futures):
                    file_name = chunk_futures[future]
                    try:
                        result = future.result()
                        if result:
                            file_results.append(result)
                            pbar.update(1)
                        else:
                            file_results.append({
                                "name": file_name,
                                "change_type": "modify",
                                "summary": f"Modified {file_name}",
                                "changes": {
                                    "additions": 0,
                                    "deletions": 0,
                                    "functions_modified": [],
                                    "key_changes": [f"Updated {file_name}"]
                                }
                            })
                            pbar.update(1)
                    except Exception as e:
                        file_results.append({
                            "name": file_name,
                            "change_type": "modify",
                            "summary": f"Modified {file_name}",
                            "changes": {
                                "additions": 0,
                                "deletions": 0,
                                "functions_modified": [],
                                "key_changes": [f"Error processing: {str(e)}"]
                            }
                        })
                        pbar.update(1)
    
    # Combine results
    total_additions = sum(f.get('changes', {}).get('additions', 0) for f in file_results)
    total_deletions = sum(f.get('changes', {}).get('deletions', 0) for f in file_results)
    
    # Count change types
    change_types = {"modify": 0, "add": 0, "delete": 0}
    for file in file_results:
        change_type = file.get('change_type', 'modify')
        change_types[change_type] = change_types.get(change_type, 0) + 1
    
    # Create a combined structured diff
    combined_diff = {
        "files": file_results,
        "overall_stats": {
            "total_files": len(file_results),
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "change_types": change_types
        }
    }
    
    # If we have a lot of files, try to generate a high-level summary
    if len(file_results) > 10:
        try:
            print("\n📝 Generating high-level summary for large commit...")
            summary_prompt = (
                "Generate a high-level summary of these changes:\n\n"
                f"Total Files: {len(file_results)}\n"
                f"Total Additions: {total_additions}\n"
                f"Total Deletions: {total_deletions}\n\n"
                "Key Changes:\n"
            )
            
            # Add summaries of key files
            for file in file_results[:5]:  # Look at first 5 files
                if file.get('summary'):
                    summary_prompt += f"- {file['name']}: {file['summary']}\n"
            
            ai_client = AIClient(
                model=AI_SMALL_MODEL,
                max_tokens=200,
                temperature=AI_TEMPERATURE
            )
            
            summary_response = ai_client.get_response(system_prompt=summary_prompt, user_message="")
            combined_diff["high_level_summary"] = summary_response.strip()
            
        except Exception as e:
            print(f"⚠️ Could not generate high-level summary: {str(e)}")
    
    return combined_diff

def parse_single_file_diff(file_name, file_content):
    """Parse a single file diff using Claude."""
    ai_client = AIClient(
        model=AI_SMALL_MODEL,
        max_tokens=500,
        temperature=AI_TEMPERATURE
    )
    
    parse_prompt = (
        f"Parse the git diff for file '{file_name}' and provide:\n\n"
        "- Type: <add/modify/delete>\n"
        "- Summary: Brief description of changes (1 sentence)\n"
        "- Lines Added: <number>\n"
        "- Lines Deleted: <number>\n"
        "- Modified Functions: List of changed functions\n"
        "- Key Changes: List 1-3 most important changes\n\n"
        "Be specific and technical. Include actual function names."
    )
    
    try:
        response = ai_client.get_response(system_prompt=parse_prompt, user_message=file_content)
        
        # Parse the response
        change_type = "modify"
        summary = ""
        additions = 0
        deletions = 0
        functions_modified = []
        key_changes = []
        
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("Type:"):
                change_type = line.split("Type:", 1)[1].strip().lower()
            elif line.startswith("Summary:"):
                summary = line.split("Summary:", 1)[1].strip()
            elif line.startswith("Lines Added:"):
                try:
                    additions = int(''.join(c for c in line.split("Lines Added:", 1)[1].strip() if c.isdigit()))
                except ValueError:
                    additions = 0
            elif line.startswith("Lines Deleted:"):
                try:
                    deletions = int(''.join(c for c in line.split("Lines Deleted:", 1)[1].strip() if c.isdigit()))
                except ValueError:
                    deletions = 0
            elif line.startswith("Modified Functions:"):
                functions_text = line.split("Modified Functions:", 1)[1].strip()
                if functions_text.lower() not in ["none", "n/a"]:
                    functions_modified = [f.strip() for f in functions_text.split(',')]
            elif line.startswith("Key Changes:"):
                continue  # Skip this line, we'll collect the actual changes below
            elif line.startswith("-") or line.startswith("*"):
                # This is likely a key change
                key_change = line.lstrip("-* ").strip()
                if key_change and key_change.lower() not in ["none", "n/a"]:
                    key_changes.append(key_change)
        
        # If we didn't get any key changes but have a summary, use that
        if not key_changes and summary:
            key_changes = [summary]
        
        return {
            "name": file_name,
            "change_type": change_type,
            "summary": summary,
            "changes": {
                "additions": additions,
                "deletions": deletions,
                "functions_modified": functions_modified,
                "key_changes": key_changes
            }
        }
    except Exception as e:
        print(f"⚠️ Error in parse_single_file_diff for {file_name}: {str(e)}")
        return None

def parse_text_response(text):
    """Parse the text response into a structured format"""
    result = {
        "files": [],
        "overall_stats": {
            "total_files": 0,
            "total_additions": 0,
            "total_deletions": 0,
            "change_types": {"modify": 0, "add": 0, "delete": 0}
        }
    }
    
    def safe_int_convert(value):
        """Safely convert various number formats to int"""
        try:
            cleaned = ''.join(c for c in value if c.isdigit() or c == '-')
            return int(cleaned) if cleaned else 0
        except ValueError:
            return 0

    current_file = None

    for line in text.split('\n'):
        original_line = line
        line = line.strip()
        if not line:
            continue

        # Normalize by stripping any leading "- " and extra whitespace
        normalized = line.lstrip('- ').strip()

        # Check for the overall statistics section start
        if normalized.startswith("OVERALL STATISTICS"):
            if current_file:
                result["files"].append(current_file)
                current_file = None
            continue

        # Detect the file summary header (typically appears once)
        if normalized.startswith("FILE SUMMARY"):
            if not current_file:
                current_file = {
                    "name": "",
                    "change_type": "",
                    "summary": "",
                    "changes": {
                        "additions": 0,
                        "deletions": 0,
                        "functions_modified": [],
                        "key_changes": []
                    }
                }
            continue

        # Detect a new file block by a "Name:" line.
        if normalized.startswith("Name:"):
            # If we already have a file with a name in progress, push it and start anew.
            if current_file and current_file["name"]:
                result["files"].append(current_file)
                current_file = {
                    "name": "",
                    "change_type": "",
                    "summary": "",
                    "changes": {
                        "additions": 0,
                        "deletions": 0,
                        "functions_modified": [],
                        "key_changes": []
                    }
                }
            if current_file is None:
                current_file = {
                    "name": "",
                    "change_type": "",
                    "summary": "",
                    "changes": {
                        "additions": 0,
                        "deletions": 0,
                        "functions_modified": [],
                        "key_changes": []
                    }
                }
            current_file["name"] = normalized.split("Name:", 1)[1].strip()
            continue

        if normalized.startswith("Type:"):
            if current_file is not None:
                current_file["change_type"] = normalized.split("Type:", 1)[1].strip()
            continue

        if normalized.startswith("Summary:"):
            if current_file is not None:
                current_file["summary"] = normalized.split("Summary:", 1)[1].strip()
            continue

        if normalized.startswith("Lines Added:"):
            if current_file is not None:
                current_file["changes"]["additions"] = safe_int_convert(normalized.split("Lines Added:", 1)[1].strip())
            continue

        if normalized.startswith("Lines Deleted:"):
            if current_file is not None:
                current_file["changes"]["deletions"] = safe_int_convert(normalized.split("Lines Deleted:", 1)[1].strip())
            continue

        if normalized.startswith("Modified Functions:"):
            if current_file is not None:
                funcs = normalized.split("Modified Functions:", 1)[1].strip()
                if funcs.lower() != "none":
                    current_file["changes"]["functions_modified"] = [f.strip() for f in funcs.split(',') if f.strip()]
            continue

        if normalized.startswith("Key Changes:"):
            # Skip the header, as key changes will be captured in subsequent lines that start with "*"
            continue

        if normalized.startswith("*"):
            if current_file is not None:
                current_file["changes"]["key_changes"].append(normalized.lstrip("*").strip())
            continue

        # Process overall statistics lines
        if normalized.startswith("Total Files Changed:"):
            result["overall_stats"]["total_files"] = safe_int_convert(normalized.split("Total Files Changed:", 1)[1].strip())
        elif normalized.startswith("Total Additions:"):
            result["overall_stats"]["total_additions"] = safe_int_convert(normalized.split("Total Additions:", 1)[1].strip())
        elif normalized.startswith("Total Deletions:"):
            result["overall_stats"]["total_deletions"] = safe_int_convert(normalized.split("Total Deletions:", 1)[1].strip())
        elif normalized.startswith("Modified:"):
            result["overall_stats"]["change_types"]["modify"] = safe_int_convert(normalized.split("Modified:", 1)[1].strip())
        elif normalized.startswith("Added:"):
            result["overall_stats"]["change_types"]["add"] = safe_int_convert(normalized.split("Added:", 1)[1].strip())
        elif normalized.startswith("Deleted:"):
            result["overall_stats"]["change_types"]["delete"] = safe_int_convert(normalized.split("Deleted:", 1)[1].strip())
    
    # Append any remaining file being processed
    if current_file:
        result["files"].append(current_file)
    
    return result

def create_fallback_structure(diff_files):
    """Create a basic structure when parsing fails"""
    # Split the diff files string into a list of files
    files = [f.strip() for f in diff_files.split('\n') if f.strip()]
    
    # Count the number of files by type (based on file extension)
    file_types = {}
    for file in files:
        ext = file.split('.')[-1] if '.' in file else 'unknown'
        file_types[ext] = file_types.get(ext, 0) + 1
    
    # Create a more informative fallback structure
    return {
        "files": [
            {
                "name": f, 
                "change_type": "modify", 
                "summary": f"Modified {f.split('.')[-1] if '.' in f else 'unknown'} file", 
                "changes": {
                    "additions": 0, 
                    "deletions": 0, 
                    "functions_modified": [], 
                    "key_changes": [f"Updated {f}"]
                }
            } for f in files if f
        ],
        "overall_stats": {
            "total_files": len(files),
            "total_additions": 0,
            "total_deletions": 0,
            "change_types": {"modify": len(files), "add": 0, "delete": 0},
            "file_types": file_types
        }
    }

def clean_file_name(file_name):
    """Clean the file name to ensure it's valid"""
    forbidden_chars = '<>"\\|?*:,'
    cleaned_file_name = ''.join(char for char in file_name if char not in forbidden_chars)
    cleaned_file_name = cleaned_file_name.replace(' ', '_')
    
    if '_' in cleaned_file_name:
        date_part, message_part = cleaned_file_name.split('_', 1)
        message_part = message_part[:50]
        cleaned_file_name = f"{date_part}_{message_part}"
    
    max_length = 245
    cleaned_file_name = cleaned_file_name[:max_length]
    
    return cleaned_file_name

def write_to_file(file_name, ext, content):
    """Write content to a file"""
    directory = os.path.dirname(file_name)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    full_file_name = f"{file_name}.{ext}"
    with open(full_file_name, 'w', encoding='utf-8') as file:
        file.write(content)

def commit_msg(user_msg):
    """Handle the commit message workflow"""
    print("\n📝 Analyzing changes...")
    
    # Check if there are already staged changes
    already_staged = has_staged_changes()
    staged_files = get_staged_files() if already_staged else []
    
    if already_staged:
        print(f"🔍 Found {len(staged_files)} already staged files:")
        for i, file in enumerate(staged_files, 1):
            print(f"  {i}. {file}")
        
        try:
            if prompt_yes_no("\nDo you want to work with these staged files?"):
                print("✅ Using already staged files.")
            else:
                # User wants to stage additional files
                unstaged_files = get_unstaged_files()
                
                if not unstaged_files:
                    print("❌ No additional unstaged files found.")
                else:
                    print(f"\n📋 Unstaged files ({len(unstaged_files)}):")
                    for i, file in enumerate(unstaged_files, 1):
                        print(f"  {i}. {file}")
                    
                    try:
                        selection = input("\n🔢 Enter file numbers to stage (e.g., '1,3,5-7', or press Enter for all): ")
                        selected_files = parse_file_selection(selection, unstaged_files)
                        
                        if selected_files:
                            with tqdm.tqdm(total=len(selected_files), desc="Staging files", unit="file") as pbar:
                                for file in selected_files:
                                    stage_files([file])
                                    pbar.update(1)
                            print("✅ Files staged successfully.")
                        else:
                            print("ℹ️ No additional files selected for staging.")
                    except KeyboardInterrupt:
                        handle_interrupt()
        except KeyboardInterrupt:
            handle_interrupt()
    else:
        # No staged changes, offer selective staging
        unstaged_files = get_unstaged_files()
        
        if not unstaged_files:
            print("❌ No changes to commit")
            return False
        
        print(f"\n📋 Unstaged files ({len(unstaged_files)}):")
        for i, file in enumerate(unstaged_files, 1):
            print(f"  {i}. {file}")
        
        try:
            selection = input("\n🔢 Enter file numbers to stage (e.g., '1,3,5-7', or press Enter for all): ")
            selected_files = parse_file_selection(selection, unstaged_files)
            
            if selected_files:
                with tqdm.tqdm(total=len(selected_files), desc="Staging files", unit="file") as pbar:
                    for file in selected_files:
                        stage_files([file])
                        pbar.update(1)
                print("✅ Files staged successfully.")
            else:
                print("❌ No files selected for staging")
                return False
        except KeyboardInterrupt:
            handle_interrupt()
    
    # Get structured diff data for staged changes
    diff_files = get_diff_files("--cached")
    diff_output = get_diff_output("--cached")
    
    # Check if there are any changes to commit
    if not diff_files and not diff_output:
        print("❌ No staged changes to commit")
        return False
    
    try:
        # Try to parse the diff with Claude
        structured_diff = parse_diff_to_structured(diff_output, diff_files)

        # Initialize message object with empty lists/strings instead of None
        message = {
            'title': '',
            'summary': '',
            'details': [],  # Initialize as empty list
            'files_changed': structured_diff.get('files', [])
        }

        # Generate title and summary concurrently
        print("🔍 Generating title and summary in parallel...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit tasks
            title_future = executor.submit(generate_title, user_msg, structured_diff)
            summary_future = executor.submit(generate_summary, user_msg, structured_diff)
            
            # Get results as they complete
            for future in concurrent.futures.as_completed([title_future, summary_future]):
                try:
                    result = future.result()
                    if future == title_future:
                        if result and result != 'Update files':
                            message['title'] = result
                            print(f"✅ Generated Title: {result}")
                    elif future == summary_future:
                        if result and result != 'No Summary':
                            message['summary'] = result
                            print(f"✅ Generated Summary: {result}")
                except Exception as e:
                    print(f"⚠️ Error in parallel processing: {str(e)}")

        # Use format_structured_diff directly instead of generate_details
        details = format_structured_diff(structured_diff)
        if details:
            message['details'] = details  # Store the details in the message object
            print("✅ Generated Details from structured diff:")
            for detail in details:
                print(f"  - {detail}")

        # Construct the final commit message
        final_commit_message = []  # Use list for better control of newlines

        if message['title']:
            final_commit_message.append(message['title'])
            final_commit_message.append("")  # Empty line after title

        if message['summary']:
            final_commit_message.append("Summary:")
            final_commit_message.append(message['summary'])
            final_commit_message.append("")  # Empty line after summary

        if message['details']:  # Add details section
            final_commit_message.append("Details:")
            for detail in message['details']:
                if detail.strip():  # Skip empty lines
                    # Don't add a dash for lines that are already file headers or indented
                    if detail.endswith(':') or detail.startswith('  '):
                        final_commit_message.append(f"{detail}")
                    else:
                        final_commit_message.append(f"- {detail}")
            final_commit_message.append("")  # Empty line after details

        if message['files_changed']:
            final_commit_message.append("Files Changed:")
            for file in message['files_changed']:
                if isinstance(file, dict) and 'name' in file:
                    final_commit_message.append(f"- {file['name']}")
                elif isinstance(file, str):
                    final_commit_message.append(f"- {file}")

        # Join all parts with newlines
        final_commit_message = "\n".join(final_commit_message)
        
    except Exception as e:
        print(f"\n⚠️ Critical error in commit message generation: {str(e)}")
        print("Using manual commit message fallback...")
        
        # Create a simple commit message with the user's input and list of changed files
        final_commit_message = user_msg if user_msg else "Update files"
        final_commit_message += "\n\nFiles Changed:\n"
        for file in diff_files.split('\n'):
            if file.strip():
                final_commit_message += f"- {file.strip()}\n"

    print("\n📝 Final Commit Message:")
    print("=" * 50)
    print(final_commit_message)
    print("=" * 50)

    # Ask the user if they want to commit the changes
    try:
        if prompt_yes_no("\nDo you want to commit these changes?"):
            commit_changes(final_commit_message)
            print("✅ Changes committed.")

            # Ask the user if they want to push the changes
            try:
                if prompt_yes_no("Do you want to push the changes to remote repository?"):
                    try:
                        push_changes()
                        print("✅ Changes pushed to the remote repository.")
                    except Exception as e:
                        print(f"❌ Failed to push changes: {str(e)}")
                else:
                    print("ℹ️ Changes not pushed to the remote repository.")
            except KeyboardInterrupt:
                handle_interrupt()
        else:
            print("ℹ️ Changes not committed.")
    except KeyboardInterrupt:
        handle_interrupt()

    # Save commit message to file
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        date_string = datetime.now().strftime('%Y%m%d%H%M%S')
        file_name = clean_file_name(f"{date_string}_{user_msg}")
        write_to_file(os.path.join(script_dir, "Commit_Logs", file_name), "txt", final_commit_message)
        print("✅ Commit message saved to log")
    except Exception as e:
        print(f"⚠️ Could not save commit message to log: {str(e)}")
        
    return final_commit_message

def format_structured_diff(structured_diff):
    """Format structured diff data into readable bullet points, grouped by file"""
    formatted_details = []
    
    for file in structured_diff.get('files', []):
        file_name = file.get('name', 'Unknown file')
        file_changes = []
        
        # Add file summary if available
        if file.get('summary'):
            file_changes.append(f"Summary: {file['summary']}")
        
        # Add modified functions
        if file.get('changes', {}).get('functions_modified'):
            functions = ', '.join(file['changes']['functions_modified'])
            file_changes.append(f"Modified functions: {functions}")
        
        # Add key changes
        if file.get('changes', {}).get('key_changes'):
            file_changes.append("Key changes:")
            for change in file['changes']['key_changes']:
                file_changes.append(f"  - {change}")
        
        # Only add the file if it has changes to report
        if file_changes:
            # Add the file name as the main entry
            formatted_details.append(f"{file_name}:")
            # Add all changes for this file as sub-entries
            formatted_details.extend([f"  {change}" for change in file_changes])
    
    return formatted_details

def generate_title(user_msg, structured_diff):
    """Generate a title using the structured diff data."""
    ai_client = AIClient(
        model=AI_SMALL_MODEL,
        max_tokens=50,
        temperature=AI_TEMPERATURE
    )

    unwanted_phrases = [
        "Concise Commit Title:",
        "Here is the title:",
        "Title:", 
        "Commit Title:",
        "Suggested Title:",
        "Generated Title:",
        "Commit Message:",
        "Here's a concise title:",
        "Based on the changes:",
        "I suggest this title:",
        "Proposed Title:"
    ]
    
    # Create a prompt using the structured diff data
    prompt = (
        "Generate a concise commit title (under 50 chars) based on these changes:\n"
        f"Files Changed: {len(structured_diff.get('files', []))}\n"
        f"Total Additions: {structured_diff.get('overall_stats', {}).get('total_additions', 0)}\n"
        f"Total Deletions: {structured_diff.get('overall_stats', {}).get('total_deletions', 0)}\n\n"
        "Key Changes:\n"
    )
    
    # Add key changes from each file
    for file in structured_diff.get('files', []):
        if file.get('changes', {}).get('key_changes'):
            prompt += f"- {file['name']}: {', '.join(file['changes']['key_changes'])}\n"
        
    prompt += f"Do not include any of the following phrases: {', '.join(unwanted_phrases)}\n"
    
    try:
        title = ai_client.get_response(system_prompt=prompt, user_message=user_msg).strip()

        # Clean up the title to ensure it doesn't contain unwanted phrases
        for phrase in unwanted_phrases:
            if phrase in title:
                title = title.replace(phrase, "").strip()

        return title
    except Exception as e:
        if "overloaded_error" in str(e):
            print("\n⚠️ Claude API is currently overloaded when generating title.")
            print("Using fallback title...")
        else:
            print(f"\n⚠️ Unexpected error when generating title: {str(e)}")
        
        # Use user_msg as title if it's not blank, otherwise use fallback
        if user_msg and user_msg.strip():
            # Ensure title is not too long (50 chars max)
            title = user_msg.strip()[:50]
            print(f"Using user message as title: {title}")
            return title
        else:
            # Generate a simple fallback title based on the first file changed
            if structured_diff.get('files'):
                first_file = structured_diff['files'][0].get('name', '').split('/')[-1]
                return f"Update {first_file}"
            return "Update files"

def generate_summary(user_msg, structured_diff):
    """Generate a summary using the structured diff data."""
    ai_client = AIClient(
        model=AI_SMALL_MODEL,
        max_tokens=100,
        temperature=AI_TEMPERATURE
    )
    
    # Create a prompt using the structured diff data
    prompt = (
        "Generate a concise summary of the following changes:\n"
        f"Total Files Changed: {len(structured_diff.get('files', []))}\n"
        f"Total Additions: {structured_diff.get('overall_stats', {}).get('total_additions', 0)}\n"
        f"Total Deletions: {structured_diff.get('overall_stats', {}).get('total_deletions', 0)}\n\n"
        "Here are the key changes:\n"
    )
    
    # Add summaries from each file
    for file in structured_diff.get('files', []):
        if file.get('summary'):
            prompt += f"- {file['name']}: {file['summary']}\n"
    
    prompt += "\nPlease provide a summary without any introductory phrases or unnecessary content."

    try:
        summary = ai_client.get_response(system_prompt=prompt, user_message=user_msg).strip()
        
        # Clean up the summary to ensure it doesn't contain unwanted phrases
        if "Concise Summary:" in summary:
            summary = summary.replace("Concise Summary:", "").strip()

        return summary
    except Exception as e:
        if "overloaded_error" in str(e):
            print("\n⚠️ Claude API is currently overloaded when generating summary.")
            print("Using fallback summary...")
            # Generate a simple fallback summary based on the overall stats
            files_count = len(structured_diff.get('files', []))
            additions = structured_diff.get('overall_stats', {}).get('total_additions', 0)
            deletions = structured_diff.get('overall_stats', {}).get('total_deletions', 0)
            return f"Updated {files_count} files with {additions} additions and {deletions} deletions."
        else:
            print(f"\n⚠️ Unexpected error when generating summary: {str(e)}")
            return "Updated files with various changes."

def generate_details(user_msg, structured_diff):
    """Generate details using the structured diff data."""
    # This function is no longer used directly, but kept for backward compatibility
    return format_structured_diff(structured_diff)

def create_git_commit_msg():
    """Main function to create a commit message"""
    print("RUNNING: Git Commit Message Generator")
    try:
        extra_msg = input("Enter Your Commit Message: ")
        value = commit_msg(extra_msg)
        
        if not value:
            print("Exiting script...")
            exit(0)
    except KeyboardInterrupt:
        handle_interrupt()

if __name__ == "__main__":
    try:
        create_git_commit_msg()
    except KeyboardInterrupt:
        handle_interrupt()
    
