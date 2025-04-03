from .base_profile import BaseProfile
from .project_type import ProjectType
from pathlib import Path
from typing import Dict, List
import xml.etree.ElementTree as ET

class DotNetCoreProfile(BaseProfile):
    def __init__(self):
        super().__init__(ProjectType.DOTNET_CORE)
        self.important_files = {
            'appsettings.json': 'Application configuration',
            'Program.cs': 'Application entry point',
            'Startup.cs': 'Application startup configuration',
            'launchSettings.json': 'Debug/launch configuration',
            'global.json': '.NET SDK version',
            'Directory.Build.props': 'Common build properties',
            'Directory.Build.targets': 'Common build targets'
        }
        self.solution_patterns = ['*.sln']
        self.project_patterns = ['*.csproj']
        self.config_patterns = ['appsettings*.json', 'web.config']

    def get_dependencies(self, root: Path) -> List[Dict[str, str]]:
        """Get .NET Core project dependencies from .csproj files"""
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
                    
            except Exception as e:
                print(f"Error reading {csproj_file}: {e}")
                
        return dependencies 