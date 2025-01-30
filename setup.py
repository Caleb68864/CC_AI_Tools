from setuptools import setup, find_packages

setup(
    name='cc-ai-tools',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'anthropic',
        'python-dotenv',
        'gitpython',
        'pyyaml',
        'pyperclip'
    ],
    entry_points={
        'console_scripts': [
            'CreateGitProgressReport=Git.CreateGitProgressReport:main',
            'CreateGitCommitMsg=Git.CreateGitCommitMsg:main',
            'CreateGitBranchName=Git.CreateGitBranchName:main'
        ],
    },
    author='CC AI Tools',
    description='Productivity Tools Using AI',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/Caleb68864/CC_AI_Tools',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6'
)
