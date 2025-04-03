from typing import Dict, List
from pathlib import Path
from enum import Enum

class BaseProfile:
    def __init__(self, project_type: Enum):
        self.project_type = project_type
        self.important_files: Dict[str, str] = {}
        self.solution_patterns: List[str] = []
        self.project_patterns: List[str] = []
        self.config_patterns: List[str] = []

    def find_solution_files(self, root: Path) -> List[Path]:
        """Find solution files based on project type"""
        if not self.solution_patterns:
            return []
        solution_files = []
        for pattern in self.solution_patterns:
            solution_files.extend(root.glob(pattern))
        return solution_files

    def find_project_files(self, root: Path) -> List[Path]:
        """Find project files based on project type"""
        project_files = []
        for pattern in self.project_patterns:
            project_files.extend(root.rglob(pattern))
        return project_files

    def find_config_files(self, root: Path) -> List[Path]:
        """Find configuration files based on project type"""
        config_files = []
        for pattern in self.config_patterns:
            config_files.extend(root.rglob(pattern))
        return config_files

    def get_dependencies(self, root: Path) -> List[Dict[str, str]]:
        """Get project dependencies. Override in specific profiles."""
        return [] 