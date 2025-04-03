from .project_type import ProjectType
from .base_profile import BaseProfile
from .dotnet_core import DotNetCoreProfile
from .dotnet_framework import DotNetFrameworkProfile
from .dotnet_blazor import DotNetBlazorProfile
from .python import PythonProfile
from .python_flask import PythonFlaskProfile

def get_profile(project_type: ProjectType) -> BaseProfile:
    """Get the appropriate profile for the project type"""
    profile_map = {
        ProjectType.DOTNET_CORE: DotNetCoreProfile,
        ProjectType.DOTNET_FRAMEWORK: DotNetFrameworkProfile,
        ProjectType.DOTNET_BLAZOR: DotNetBlazorProfile,
        ProjectType.PYTHON: PythonProfile,
        ProjectType.PYTHON_FLASK: PythonFlaskProfile
    }
    return profile_map[project_type]() 