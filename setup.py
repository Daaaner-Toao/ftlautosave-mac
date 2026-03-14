"""
Setup script for creating Mac App Bundle
Usage:
    python setup.py py2app
"""
from setuptools import setup
from pathlib import Path

# Read version from VERSION file
version_file = Path(__file__).parent / "VERSION"
if version_file.exists():
    with open(version_file) as f:
        VERSION = f.read().strip()
else:
    VERSION = "1.2.0"  # Fallback version

APP = ['run_ftlautosave.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['ftlautosave'],
    'includes': ['tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog'],
    'excludes': [
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'wx', 'matplotlib', 'numpy', 'pandas',
        '_decimal',  # Exclude _decimal to avoid permission issues during build
        'decimal',   # Exclude decimal module
        'test',      # Exclude test modules
        'unittest',
    ],
    'iconfile': None,  # Can be set to .icns file path
    'semi_standalone': True,  # Use semi-standalone mode (requires Python on target system)
    'plist': {
        'CFBundleName': 'FTL Autosave',
        'CFBundleDisplayName': 'FTL Autosave',
        'CFBundleIdentifier': 'com.ftlautosave.mac',
        'CFBundleVersion': VERSION,
        'CFBundleShortVersionString': VERSION,
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13.0',
        'NSRequiresAquaSystemAppearance': False,
    }
}

setup(
    name='FTL Autosave',
    version=VERSION,
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
