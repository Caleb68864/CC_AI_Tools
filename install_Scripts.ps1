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

# Define the bin directory
$installBinDir = Join-Path $currentDir "Release"
$binDir = Join-Path $installBinDir "bin"

Write-Host "Installing Python packages into $binDir"


# Check if the bin directory is already in the PATH
if (-not ($env:Path -like "*$binDir*")) {
    # Add the bin directory to the PATH environment variable permanently for the user
    [System.Environment]::SetEnvironmentVariable("Path", $binDir + ";" + [System.Environment]::GetEnvironmentVariable("Path"), [System.EnvironmentVariableTarget]::User)
    Write-Host "Added $binDir to the PATH environment variable."
} else {
    Write-Host "$binDir is already in the PATH environment variable."
}

# Update current environment variable so the scripts are available without restarting the terminal
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", [System.EnvironmentVariableTarget]::Process) + ";" + $binDir

# Run pip install with the target set to the bin directory
try {
    pip uninstall cc-ai-tools -y
    # Remove the Release directory
    Remove-Item -Path "Release" -Recurse -Force -ErrorAction SilentlyContinue
    # Install in editable mode first
    pip install -e .
    # Then install executables to the Release directory
    pip install . --target=$installBinDir --upgrade
    Write-Host "Installation completed successfully."
} catch {
    Write-Host "An error occurred during installation: $_"
}

Write-Host "Installation complete. You can now use the installed scripts from the command line."
