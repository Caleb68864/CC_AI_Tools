<#
.SYNOPSIS
    Sets up Python script aliases and environment files for easy command-line access.

.DESCRIPTION
    This installation script performs two main tasks:
    1. Creates global PowerShell functions for all Python scripts in specified directories,
       allowing them to be run from anywhere like regular commands.
    2. Sets up environment files by copying .env.example to .env if needed.

.EXAMPLE
    To add a new script directory, add an entry to the $scriptDirs array:
    $scriptDirs = @(
        @{Path = "Git"; Description = "Git scripts"},
        @{Path = "Utils"; Description = "Utility scripts"}
    )

.NOTES
    After running this script, you can execute any Python script by its filename
    (without the .py extension) from any location in PowerShell.
#>

# Get the current directory where the script is located
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# Define array of script directories to add
$scriptDirs = @(
    @{Path = "Git"; Description = "Git scripts"}
    # Add more directories here as needed, for example:
    # @{Path = "Utils"; Description = "Utility scripts"}
)

foreach ($dir in $scriptDirs) {
    $dirPath = Join-Path $scriptPath $dir.Path
    
    # Check for .env file
    $envPath = Join-Path $dirPath ".env"
    $envExamplePath = Join-Path $dirPath ".env.example"
    
    if (Test-Path $envExamplePath) {
        if (-not (Test-Path $envPath)) {
            Copy-Item $envExamplePath $envPath
            Write-Host "✅ Created .env file from .env.example in $($dir.Description)"
        } else {
            Write-Host "ℹ️ .env file already exists in $($dir.Description)"
        }
    }
    
    # Create aliases for the Python scripts
    # Get all Python files in the directory
    $pythonFiles = Get-ChildItem -Path $dirPath -Filter "*.py" -ErrorAction SilentlyContinue
    
    if ($pythonFiles) {
        foreach ($file in $pythonFiles) {
            $aliasName = $file.BaseName
            $fullScriptPath = $file.FullName
            
            # Create the function if it doesn't exist
            $functionDef = @"
function global:$aliasName {
    param(`$args)
    & python "$fullScriptPath" `$args
}
"@
            Invoke-Expression $functionDef
            Write-Host "✅ Created function for $($file.Name)"
        }
    }
}

Write-Host "`n🎉 Installation complete! You can now run scripts directly from any location."
