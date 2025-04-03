[CmdletBinding()]
param(
    [Parameter()]
    [Alias("d")]
    [switch]$dev
)

<#
.SYNOPSIS
    Installs Python packages into a local bin directory for easy command-line access.

.DESCRIPTION
    This script adds the current directory's bin folder to the PATH environment variable
    and installs Python packages from the current directory into that bin folder.
    By default, it will checkout and pull the Production branch unless --dev flag is used.

.PARAMETER dev
    Skip checking out the Production branch. Use this for development work.

.EXAMPLE
    Run this script in a directory containing a pyproject.toml file to install the package locally:
    .\install_Scripts.ps1

    Run in development mode (skip Production branch checkout):
    .\install_Scripts.ps1 -dev

.NOTES
    After running this script, you can execute installed scripts directly from the command line.
#>

# Get the current directory
$currentDir = Get-Location

# Handle Git operations if not in dev mode
if (-not $dev) {
    Write-Host "Checking out Production branch..." -ForegroundColor Yellow
    try {
        git fetch origin
        git checkout Production
        git pull origin Production
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error: Git operations failed. Please resolve any Git issues and try again." -ForegroundColor Red
            exit 1
        }
        Write-Host "Successfully updated to latest Production branch." -ForegroundColor Green
    }
    catch {
        Write-Host "Error performing Git operations: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Development mode: Skipping Production branch checkout." -ForegroundColor Yellow
}

# Define the bin directory
$installBinDir = Join-Path $currentDir "Release"
$binDir = Join-Path $installBinDir "bin"

Write-Host "Installing Python packages into $binDir"

# Create directories if they don't exist
New-Item -ItemType Directory -Force -Path $installBinDir | Out-Null
New-Item -ItemType Directory -Force -Path $binDir | Out-Null

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

# Copy env.example to .env if it exists and .env doesn't
$envExample = Join-Path $currentDir "env.example"
$envFile = Join-Path $currentDir ".env"

if (Test-Path $envExample) {
    if (-not (Test-Path $envFile)) {
        Copy-Item $envExample $envFile
        Write-Host "Copied env.example to .env" -ForegroundColor Green
    } else {
        Write-Host ".env file already exists, skipping copy" -ForegroundColor Yellow
    }
}

# Run pip install with the target set to the bin directory
try {
    # Uninstall existing packages if present
    pip uninstall cc-ai-tools -y
    pip uninstall cc-ai-tools -y

    # Clean up any existing installation
    if (Test-Path $installBinDir) {
        Write-Host "Cleaning up existing installation..."
        Remove-Item -Path $installBinDir -Recurse -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2  # Give Windows time to release file handles
    }

    # Install build dependencies
    Write-Host "Installing build dependencies..."
    pip install --upgrade pip
    pip install hatch wheel build

    # Install in editable mode first
    Write-Host "Installing in editable mode..."
    pip install -e . --no-cache-dir

    # Then install executables to the Release directory
    Write-Host "Installing executables..."
    # First install dependencies
    pip install -r requirements.txt --target=$installBinDir
    
    # Create the package directory in Release
    $packageDir = Join-Path $installBinDir "cc_ai_tools"
    New-Item -ItemType Directory -Force -Path $packageDir | Out-Null
    
    # Create __init__.py in the package directory if it doesn't exist
    $initPy = Join-Path $packageDir "__init__.py"
    if (-not (Test-Path $initPy)) {
        Set-Content -Path $initPy -Value @"
__version__ = '0.1.0'

from .git.commit_msg import create_git_commit_msg
from .git.branch_name import create_git_branch_name
from .git.progress_report import create_git_progress_report
from .cursor_rules.apply_rules import main as apply_cursor_rules

__all__ = [
    'create_git_commit_msg',
    'create_git_branch_name',
    'create_git_progress_report',
    'apply_cursor_rules'
]
"@
    }
    
    # Create subdirectories
    $gitDir = Join-Path $packageDir "git"
    $cursorRulesDir = Join-Path $packageDir "cursor_rules"
    $aiDir = Join-Path $packageDir "ai"
    $yamlDir = Join-Path $packageDir "yaml"
    
    New-Item -ItemType Directory -Force -Path $gitDir | Out-Null
    New-Item -ItemType Directory -Force -Path $cursorRulesDir | Out-Null
    New-Item -ItemType Directory -Force -Path $aiDir | Out-Null
    New-Item -ItemType Directory -Force -Path $yamlDir | Out-Null
    
    # Create __init__.py files in subdirectories
    Set-Content -Path (Join-Path $gitDir "__init__.py") -Value @"
from .commit_msg import create_git_commit_msg
from .branch_name import create_git_branch_name
from .progress_report import create_git_progress_report

__all__ = [
    'create_git_commit_msg',
    'create_git_branch_name',
    'create_git_progress_report'
]
"@
    
    Set-Content -Path (Join-Path $cursorRulesDir "__init__.py") -Value ""
    Set-Content -Path (Join-Path $aiDir "__init__.py") -Value ""
    Set-Content -Path (Join-Path $yamlDir "__init__.py") -Value ""
    
    # Copy the package files
    Write-Host "Copying package files..."
    # Check if we're using the old or new structure
    if (Test-Path "src/cc_ai_tools") {
        Copy-Item -Path "src/cc_ai_tools/*" -Destination $packageDir -Recurse -Force
    } elseif (Test-Path "Git") {
        # Copy from old structure
        Copy-Item -Path "Git/*" -Destination $gitDir -Recurse -Force
        Copy-Item -Path "Cursor_Rules/*" -Destination $cursorRulesDir -Recurse -Force
        Copy-Item -Path "AI/*" -Destination $aiDir -Recurse -Force
        Copy-Item -Path "YAML/*" -Destination $yamlDir -Recurse -Force
    } else {
        Write-Host "Could not find source files in either src/cc_ai_tools or old directory structure" -ForegroundColor Red
        exit 1
    }
    
    # Then install the package itself
    pip install . --target=$installBinDir --no-deps --upgrade --no-cache-dir

    Write-Host "Installation completed successfully." -ForegroundColor Green
} catch {
    Write-Host "An error occurred during installation: $_" -ForegroundColor Red
    Write-Host "Try running this script with administrator privileges if the error persists." -ForegroundColor Yellow
    exit 1
}

Write-Host "Installation complete. You can now use the installed scripts from the command line." -ForegroundColor Green
