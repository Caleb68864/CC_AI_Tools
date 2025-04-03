import os
import glob
from pathlib import Path

def rename_files():
    # Get the Rules directory path
    rules_dir = Path(__file__).parent / 'Rules'
    
    # Find all .mdc files recursively
    mdc_files = []
    for root, _, files in os.walk(rules_dir):
        for file in files:
            if file.endswith('.mdc'):
                mdc_files.append(os.path.join(root, file))
    
    print(f"Found {len(mdc_files)} .mdc files to rename")
    
    # Rename each file
    for mdc_file in mdc_files:
        mdct_file = mdc_file.replace('.mdc', '.mdct')
        if os.path.exists(mdc_file):
            os.rename(mdc_file, mdct_file)
            print(f"Renamed: {os.path.relpath(mdc_file, rules_dir)} -> {os.path.relpath(mdct_file, rules_dir)}")
    
    print("\nRenaming complete!")

if __name__ == "__main__":
    rename_files() 