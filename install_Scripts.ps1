<#
.SYNOPSIS
    Installs Python packages into a local bin directory for easy command-line access.

.DESCRIPTION
    This script adds the current directory's bin folder to the PATH environment variable
    and installs Python packages from the current directory into that bin folder.

.EXAMPLE
    Run this script in a directory containing a setup.py file to install the package locally.

.NOTES
    After running this script, you can execute installed scripts directly from the command line.
#>

# Get the current directory
$currentDir = Get-Location

# Define the bin directory path
$binDir = Join-Path $currentDir "bin"

# Add the bin directory to the PATH environment variable for the current session
$env:Path = "$binDir;$env:Path"

# Run pip install with the target set to the bin directory
pip install . --target=$binDir --upgrade

