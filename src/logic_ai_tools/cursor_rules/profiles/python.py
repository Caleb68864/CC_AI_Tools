from .base_profile import BaseProfile
from .project_type import ProjectType
from pathlib import Path
from typing import Dict, List

class PythonProfile(BaseProfile):
    def __init__(self):
        super().__init__(ProjectType.PYTHON)
        self.important_files = {
            'requirements.txt': 'Python dependencies',
            'setup.py': 'Package configuration',
            'README.md': 'Project documentation',
            '.env': 'Environment variables'
        }
        self.solution_patterns = []
        self.project_patterns = ['setup.py', 'pyproject.toml']
        self.config_patterns = ['.env', '*.ini', '*.cfg']

    def get_dependencies(self, root: Path) -> List[Dict[str, str]]:
        """Get Python project dependencies from requirements.txt or setup.py"""
        dependencies = []
        
        # Check requirements.txt
        req_file = root / 'requirements.txt'
        if req_file.exists():
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Handle different formats: package==version, package>=version, etc.
                            parts = line.split('==')
                            if len(parts) != 2:
                                parts = line.split('>=')
                            if len(parts) != 2:
                                parts = line.split('<=')
                            if len(parts) != 2:
                                parts = [line, '']
                                
                            dependencies.append({
                                'name': parts[0].strip(),
                                'version': parts[1].strip() if len(parts) > 1 else '',
                                'source': 'requirements.txt'
                            })
            except Exception as e:
                print(f"Error reading requirements.txt: {e}")
        
        # Check setup.py
        setup_file = root / 'setup.py'
        if setup_file.exists():
            try:
                with open(setup_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Look for install_requires list
                    if 'install_requires=' in content:
                        # Very basic parsing - in real code you'd want to use ast
                        start = content.find('install_requires=[') + len('install_requires=[')
                        end = content.find(']', start)
                        if start > -1 and end > -1:
                            deps = content[start:end].split(',')
                            for dep in deps:
                                dep = dep.strip().strip("'").strip('"')
                                if dep:
                                    parts = dep.split('>=')
                                    if len(parts) != 2:
                                        parts = dep.split('==')
                                    if len(parts) != 2:
                                        parts = [dep, '']
                                        
                                    dependencies.append({
                                        'name': parts[0].strip(),
                                        'version': parts[1].strip() if len(parts) > 1 else '',
                                        'source': 'setup.py'
                                    })
            except Exception as e:
                print(f"Error reading setup.py: {e}")
        
        # Check pyproject.toml
        pyproject_file = root / 'pyproject.toml'
        if pyproject_file.exists():
            try:
                with open(pyproject_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Very basic TOML parsing - in real code you'd want to use a TOML parser
                    if 'dependencies =' in content:
                        start = content.find('dependencies =') + len('dependencies =')
                        end = content.find('\n[', start)
                        if end == -1:
                            end = len(content)
                        deps_section = content[start:end]
                        for line in deps_section.split('\n'):
                            line = line.strip()
                            if '=' in line:
                                name, version = line.split('=', 1)
                                dependencies.append({
                                    'name': name.strip(),
                                    'version': version.strip().strip('"').strip("'"),
                                    'source': 'pyproject.toml'
                                })
            except Exception as e:
                print(f"Error reading pyproject.toml: {e}")
        
        return dependencies 