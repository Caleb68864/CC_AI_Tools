from .base_profile import BaseProfile
from .project_type import ProjectType
from pathlib import Path
from typing import Dict, List
import xml.etree.ElementTree as ET

class DotNetBlazorProfile(BaseProfile):
    def __init__(self):
        super().__init__(ProjectType.DOTNET_BLAZOR)
        self.important_files = {
            'appsettings.json': 'Application configuration',
            'Program.cs': 'Application entry point',
            '_Imports.razor': 'Razor component imports',
            'App.razor': 'Root component',
            'launchSettings.json': 'Debug/launch configuration',
            'global.json': '.NET SDK version',
            'Directory.Build.props': 'Common build properties',
            'Directory.Build.targets': 'Common build targets',
            'wwwroot/index.html': 'Static web assets',
            'wwwroot/css/site.css': 'Site styles',
            'wwwroot/js/site.js': 'Site scripts'
        }
        self.solution_patterns = ['*.sln']
        self.project_patterns = ['*.csproj']
        self.config_patterns = ['appsettings*.json', 'web.config']

    def get_dependencies(self, root: Path) -> List[Dict[str, str]]:
        """Get Blazor project dependencies from .csproj files"""
        dependencies = []
        
        # Find all .csproj files
        for csproj_file in root.rglob('*.csproj'):
            try:
                tree = ET.parse(csproj_file)
                root_elem = tree.getroot()
                
                # Get package references
                for pkg_ref in root_elem.findall(".//PackageReference"):
                    dependencies.append({
                        'name': pkg_ref.get('Include', ''),
                        'version': pkg_ref.get('Version', ''),
                        'source': str(csproj_file.relative_to(root))
                    })
                    
                # Get framework references
                for framework_ref in root_elem.findall(".//FrameworkReference"):
                    dependencies.append({
                        'name': framework_ref.get('Include', ''),
                        'version': '',  # Framework references don't typically have versions
                        'source': str(csproj_file.relative_to(root)),
                        'type': 'framework'
                    })
                    
                # Get project references
                for proj_ref in root_elem.findall(".//ProjectReference"):
                    dependencies.append({
                        'name': proj_ref.get('Include', ''),
                        'version': '',  # Project references don't have versions
                        'source': str(csproj_file.relative_to(root)),
                        'type': 'project'
                    })
                    
                # Check for Blazor-specific dependencies
                sdk_elem = root_elem.find(".//Sdk")
                if sdk_elem is not None and 'Microsoft.NET.Sdk.BlazorWebAssembly' in sdk_elem.get('Name', ''):
                    dependencies.append({
                        'name': 'Microsoft.AspNetCore.Components.WebAssembly',
                        'version': '',  # Version is typically determined by SDK
                        'source': str(csproj_file.relative_to(root)),
                        'type': 'sdk'
                    })
                    
            except Exception as e:
                print(f"Error reading {csproj_file}: {e}")
                
        return dependencies 