"""
Interrupt Handler Utility
-----------------------
Common utility for handling keyboard interrupts (Ctrl+C) gracefully across all scripts.
"""

import sys

def handle_interrupt():
    """
    Handle keyboard interrupt (Ctrl+C) gracefully with a friendly exit message.
    Can be used across any script that needs to handle user interruptions.
    """
    print("\n\n🛑 Operation cancelled by user")
    print("👋 Exiting gracefully...")
    sys.exit(0) 