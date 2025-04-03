from .base_profile import BaseProfile
from .project_type import ProjectType

class DotNetFrameworkProfile(BaseProfile):
    def __init__(self):
        super().__init__(ProjectType.DOTNET_FRAMEWORK)
        self.important_files = {
            'Global.asax': 'Application entry point',
            'Web.config': 'Application configuration',
            'App.config': 'Application settings',
            'packages.config': 'Package dependencies'
        }
        self.solution_patterns = ['*.sln']
        self.project_patterns = ['*.csproj']
        self.config_patterns = ['*.config'] 