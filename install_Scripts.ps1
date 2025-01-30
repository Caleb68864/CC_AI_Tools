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

    # Get current Path environment variable
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    
    # Check if the path is already in the environment variable
    if ($currentPath -notlike "*$dirPath*") {
        # Add the scripts directory to Path
        $newPath = $currentPath + ";" + $dirPath
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-Host "✅ Added $($dir.Description) directory to Path environment variable"
    } else {
        Write-Host "ℹ️ $($dir.Description) directory is already in Path"
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
