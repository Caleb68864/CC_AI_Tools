import os
import json
import re
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Any, List, Tuple, Set
from pathlib import Path
import time

from .profiles import ProjectType, get_profile

class ProjectScanner:
    def __init__(self, project_root: str, project_type: Optional[ProjectType] = None):
        self.project_root = Path(project_root)
        self.rules_dir = self.project_root / '.cursor' / 'rules'
        self.rules_dir.mkdir(parents=True, exist_ok=True)
        self.context_file = self.rules_dir / 'project-context.mdc'
        self.template_dir = Path(__file__).parent / 'templates'
        self.profile = get_profile(project_type or self._detect_project_type())
        self.solution_info = None

    def _detect_project_type(self) -> ProjectType:
        """Detect the project type based on project structure and files"""
        # Check for Python projects
        if any(self.project_root.glob('*.py')):
            if any(self.project_root.glob('templates/*')) or any(self.project_root.glob('static/*')):
                return ProjectType.PYTHON_FLASK
            return ProjectType.PYTHON

        # Check for .NET projects
        if any(self.project_root.glob('*.csproj')):
            if any(self.project_root.glob('*.razor')):
                return ProjectType.DOTNET_BLAZOR
            if any(self.project_root.glob('appsettings.json')):
                return ProjectType.DOTNET_CORE
            return ProjectType.DOTNET_FRAMEWORK

        # Default to Python if no specific type is detected
        return ProjectType.PYTHON

    def scan_project(self):
        """Scan the project and return the context content"""
        print(f"\nScanning {self.profile.project_type.value} project...")
        
        # Get project name
        project_name = self._get_project_name()
        
        # Get project structure
        project_structure = self._get_project_structure()
        
        # Get project files and dependencies
        project_files = self.profile.find_project_files(self.project_root)
        config_files = self.profile.find_config_files(self.project_root)
        
        # Get dependencies based on project type
        dependencies = self._get_project_dependencies()
        
        # Get important files
        important_files = self._find_important_files()
        
        # Get file extensions
        file_extensions = self._get_file_extensions()
        
        # For .NET projects, parse solution and project files
        dotnet_info = {}
        if self.profile.project_type in [ProjectType.DOTNET_CORE, ProjectType.DOTNET_BLAZOR, ProjectType.DOTNET_FRAMEWORK]:
            dotnet_info = self._analyze_dotnet_structure()
        
        # Create context data
        context_data = {
            'project_name': project_name,
            'project_root': str(self.project_root),
            'project_type': self.profile.project_type.value,
            'source_path': str(project_structure['source_path']),
            'test_path': str(project_structure['test_path']),
            'docs_path': str(project_structure['docs_path']),
            'project_files': [str(f.relative_to(self.project_root)) for f in project_files],
            'config_files': [str(f.relative_to(self.project_root)) for f in config_files],
            'dependencies': dependencies,
            'important_files': important_files,
            'file_extensions': self._format_file_extensions(file_extensions),
            **dotnet_info
        }
        
        # Generate the context content
        return self._generate_context_content(context_data)

    def _get_project_name(self) -> str:
        """Get the project name from various sources"""
        # Try to get name from .NET project file first
        if self.profile.project_type in [ProjectType.DOTNET_CORE, ProjectType.DOTNET_BLAZOR, ProjectType.DOTNET_FRAMEWORK]:
            project_files = list(self.project_root.glob('*.csproj'))
            if project_files:
                try:
                    tree = ET.parse(project_files[0])
                    root = tree.getroot()
                    # Try to get AssemblyName first
                    assembly_name = root.find(".//AssemblyName")
                    if assembly_name is not None and assembly_name.text:
                        return assembly_name.text
                    # Try to get RootNamespace as fallback
                    root_namespace = root.find(".//RootNamespace")
                    if root_namespace is not None and root_namespace.text:
                        return root_namespace.text
                except Exception as e:
                    print(f"Error reading project file: {e}")
        
        # Fallback to folder name
        return self.project_root.name

    def _get_project_structure(self) -> Dict[str, Path]:
        """Analyze project structure"""
        structure = {
            'source_path': self.project_root / 'src',
            'test_path': self.project_root / 'tests',
            'docs_path': self.project_root / 'docs'
        }
        
        # Create directories if they don't exist
        for path in structure.values():
            path.mkdir(exist_ok=True)
            
        return structure

    def _get_project_dependencies(self) -> list:
        """Get project dependencies based on project type"""
        dependencies = []
        
        # Get dependencies based on project type using profile
        dependencies = self.profile.get_dependencies(self.project_root)
                    
        return dependencies

    def _find_important_files(self) -> list:
        """Find important project files based on profile"""
        important_files = []
        
        for file in self.project_root.rglob('*'):
            if file.is_file():
                relative_path = str(file.relative_to(self.project_root))
                for pattern, description in self.profile.important_files.items():
                    if pattern in relative_path:
                        important_files.append({
                            'path': relative_path,
                            'description': description
                        })
                        break
                
        return important_files

    def _get_file_extensions(self) -> Set[str]:
        """Get all file extensions in the project"""
        extensions = set()
        ignored_dirs = {'.git', '.vs', 'node_modules', 'bin', 'obj', '__pycache__', '.pytest_cache', '.mypy_cache'}
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext:
                    # Remove the dot from the extension
                    extensions.add(ext[1:])
        
        return extensions

    def _format_file_extensions(self, extensions: Set[str]) -> str:
        """Format file extensions for template"""
        # Sort extensions and format them with metadata
        formatted_extensions = []
        for ext in sorted(extensions):
            ext_info = {
                'extension': ext,
                'description': self._get_extension_description(ext),
                'category': self._get_extension_category(ext)
            }
            formatted_extensions.append(ext_info)
            
        return json.dumps(formatted_extensions, indent=4)

    def _get_extension_description(self, ext: str) -> str:
        """Get description for file extension"""
        descriptions = {
            'cs': 'C# source code file',
            'cshtml': 'Razor view template file',
            'razor': 'Razor component file',
            'py': 'Python source code file',
            'js': 'JavaScript source code file',
            'ts': 'TypeScript source code file',
            'html': 'HTML web page file',
            'css': 'CSS stylesheet file',
            'scss': 'SASS stylesheet file',
            'less': 'LESS stylesheet file',
            'json': 'JSON data file',
            'xml': 'XML data file',
            'yaml': 'YAML configuration file',
            'yml': 'YAML configuration file',
            'md': 'Markdown documentation file',
            'sql': 'SQL database script file',
            'txt': 'Plain text file',
            'gitignore': 'Git ignore rules file',
            'dockerignore': 'Docker ignore rules file',
            'env': 'Environment variables file',
            'config': 'Configuration file',
            'ini': 'INI configuration file',
            'bat': 'Windows batch script file',
            'sh': 'Shell script file',
            'ps1': 'PowerShell script file',
            'sln': 'Visual Studio solution file',
            'csproj': 'C# project file',
            'vbproj': 'Visual Basic project file',
            'fsproj': 'F# project file',
            'pyproj': 'Python project file',
            'jsx': 'React JavaScript file',
            'tsx': 'React TypeScript file',
            'vue': 'Vue.js component file',
            'go': 'Go source code file',
            'rs': 'Rust source code file',
            'java': 'Java source code file',
            'cpp': 'C++ source code file',
            'h': 'C/C++ header file',
            'hpp': 'C++ header file'
        }
        return descriptions.get(ext, f'{ext.upper()} file')

    def _get_extension_category(self, ext: str) -> str:
        """Get category for file extension"""
        categories = {
            'cs': 'Backend',
            'cshtml': 'Frontend',
            'razor': 'Frontend',
            'py': 'Backend',
            'js': 'Frontend',
            'ts': 'Frontend',
            'html': 'Frontend',
            'css': 'Frontend',
            'scss': 'Frontend',
            'less': 'Frontend',
            'json': 'Data',
            'xml': 'Data',
            'yaml': 'Configuration',
            'yml': 'Configuration',
            'md': 'Documentation',
            'sql': 'Database',
            'txt': 'Documentation',
            'gitignore': 'Configuration',
            'dockerignore': 'Configuration',
            'env': 'Configuration',
            'config': 'Configuration',
            'ini': 'Configuration',
            'bat': 'Script',
            'sh': 'Script',
            'ps1': 'Script',
            'sln': 'Project',
            'csproj': 'Project',
            'vbproj': 'Project',
            'fsproj': 'Project',
            'pyproj': 'Project',
            'jsx': 'Frontend',
            'tsx': 'Frontend',
            'vue': 'Frontend',
            'go': 'Backend',
            'rs': 'Backend',
            'java': 'Backend',
            'cpp': 'Backend',
            'h': 'Backend',
            'hpp': 'Backend'
        }
        return categories.get(ext, 'Other')

    def _generate_context_content(self, context_data: Dict) -> str:
        """Generate the context file content without writing it"""
        return f"""---
description: Project context and structure information
globs: **/*
---

# {context_data['project_name']} Project Context

This file contains the project structure and configuration information for a {context_data['project_type'].lower().replace('_', ' ')} project.

<rule>
name: project_context
description: Provides project structure and configuration information for {context_data['project_type'].lower().replace('_', ' ')} projects

metadata:
  project_name: {context_data['project_name']}
  project_root: .
  project_type: {context_data['project_type'].lower()}
  source_path: {Path(context_data['source_path']).relative_to(self.project_root)}
  test_path: {Path(context_data['test_path']).relative_to(self.project_root)}
  docs_path: {Path(context_data['docs_path']).relative_to(self.project_root)}
  language: {context_data['project_type'].split('_')[0].capitalize()}

file_extensions:
{context_data['file_extensions']}

project_files:
{json.dumps(context_data['project_files'], indent=2)}

config_files:
{json.dumps(context_data['config_files'], indent=2)}

dependencies:
{json.dumps(context_data['dependencies'], indent=2)}

important_files:
{json.dumps(context_data['important_files'], indent=2)}
</rule>"""

    def _analyze_dotnet_structure(self) -> Dict:
        """Analyze .NET solution and project structure"""
        # Find solution file
        sln_files = list(self.project_root.glob('**/*.sln'))
        if not sln_files:
            return {}

        solution_path = sln_files[0]
        projects_info = self._parse_solution_file(solution_path)
        
        # Parse each project file
        csproj_info = {}
        for proj_path in projects_info['project_paths']:
            csproj_info.update(self._parse_csproj_file(Path(proj_path)))

        return {
            'solution_path': str(solution_path.relative_to(self.project_root)),
            'projects_info': self._format_projects_info(projects_info),
            'csproj_files': self._format_csproj_list(csproj_info['csproj_files']),
            'project_references': self._format_project_references(csproj_info['project_references']),
            'package_references': self._format_package_references(csproj_info['package_references']),
            'target_frameworks': self._format_target_frameworks(csproj_info['target_frameworks']),
            'assembly_info': self._format_assembly_info(csproj_info['assembly_info'])
        }

    def _parse_solution_file(self, sln_path: Path) -> Dict:
        """Parse Visual Studio solution file"""
        projects = []
        project_paths = []
        
        try:
            with open(sln_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extract project information using regex
            project_pattern = r'Project\("\{[^}]+\}"\)\s*=\s*"([^"]+)",\s*"([^"]+)",\s*"\{[^}]+\}"'
            matches = re.finditer(project_pattern, content)
            
            for match in matches:
                project_name, project_path = match.groups()
                abs_path = (sln_path.parent / project_path).resolve()
                if abs_path.exists():
                    projects.append({
                        'name': project_name,
                        'path': str(abs_path.relative_to(self.project_root))
                    })
                    project_paths.append(str(abs_path))
                    
        except Exception as e:
            print(f"Error parsing solution file: {e}")
            
        return {
            'projects': projects,
            'project_paths': project_paths
        }

    def _parse_csproj_file(self, csproj_path: Path) -> Dict:
        """Parse .NET project file"""
        info = {
            'csproj_files': [],
            'project_references': [],
            'package_references': [],
            'target_frameworks': [],
            'assembly_info': {}
        }
        
        try:
            tree = ET.parse(csproj_path)
            root = tree.getroot()
            
            # Get relative path
            rel_path = str(csproj_path.relative_to(self.project_root))
            info['csproj_files'].append(rel_path)
            
            # Get project references
            for proj_ref in root.findall(".//ProjectReference"):
                ref_path = proj_ref.get('Include', '')
                if ref_path:
                    abs_path = (csproj_path.parent / ref_path).resolve()
                    if abs_path.exists():
                        info['project_references'].append({
                            'from': rel_path,
                            'to': str(abs_path.relative_to(self.project_root))
                        })
            
            # Get package references
            for pkg_ref in root.findall(".//PackageReference"):
                info['package_references'].append({
                    'project': rel_path,
                    'package': pkg_ref.get('Include', ''),
                    'version': pkg_ref.get('Version', '')
                })
            
            # Get target frameworks
            target_framework = root.find(".//TargetFramework")
            if target_framework is not None:
                info['target_frameworks'].append({
                    'project': rel_path,
                    'framework': target_framework.text
                })
            
            # Get assembly info
            assembly_info = {
                'project': rel_path,
                'assembly_name': '',
                'root_namespace': '',
                'guid': ''
            }
            
            assembly_name = root.find(".//AssemblyName")
            if assembly_name is not None:
                assembly_info['assembly_name'] = assembly_name.text
                
            root_namespace = root.find(".//RootNamespace")
            if root_namespace is not None:
                assembly_info['root_namespace'] = root_namespace.text
                
            project_guid = root.find(".//ProjectGuid")
            if project_guid is not None:
                assembly_info['guid'] = project_guid.text
                
            info['assembly_info'] = assembly_info
            
        except Exception as e:
            print(f"Error parsing project file {csproj_path}: {e}")
            
        return info

    def _format_projects_info(self, info: Dict) -> str:
        """Format projects info for template"""
        return json.dumps(info['projects'], indent=4)

    def _format_csproj_list(self, csproj_files: List[str]) -> str:
        """Format csproj files list for template"""
        return json.dumps(csproj_files, indent=4)

    def _format_project_references(self, references: List[Dict]) -> str:
        """Format project references for template"""
        return json.dumps(references, indent=4)

    def _format_package_references(self, references: List[Dict]) -> str:
        """Format package references for template"""
        return json.dumps(references, indent=4)

    def _format_target_frameworks(self, frameworks: List[Dict]) -> str:
        """Format target frameworks for template"""
        return json.dumps(frameworks, indent=4)

    def _format_assembly_info(self, info: Dict) -> str:
        """Format assembly info for template"""
        return json.dumps(info, indent=4)

def main():
    """Main entry point"""
    # Get the directory where the script is being run from
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    # Create scanner and scan project
    scanner = ProjectScanner(project_root)
    scanner.scan_project()

if __name__ == "__main__":
    main()