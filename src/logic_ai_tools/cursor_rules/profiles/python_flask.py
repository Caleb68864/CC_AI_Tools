from .base_profile import BaseProfile
from .project_type import ProjectType

class PythonFlaskProfile(BaseProfile):
    def __init__(self):
        super().__init__(ProjectType.PYTHON_FLASK)
        self.important_files = {
            'requirements.txt': 'Python dependencies',
            'app.py': 'Flask application entry',
            'config.py': 'Flask configuration',
            '.env': 'Environment variables',
            'templates/': 'Flask templates directory',
            'static/': 'Flask static files directory'
        }
        self.solution_patterns = []
        self.project_patterns = ['setup.py', 'pyproject.toml']
        self.config_patterns = ['.env', 'config.py', '*.ini', '*.cfg'] 