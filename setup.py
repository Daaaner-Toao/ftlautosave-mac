"""
Setup script for creating Mac App Bundle
Usage:
    python setup.py py2app
"""
from setuptools import setup

APP = ['run_ftlautosave.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['ftlautosave'],
    'includes': ['tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog'],
    'excludes': ['PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'wx', 'matplotlib', 'numpy', 'pandas'],
    'iconfile': None,  # Can be set to .icns file path
    'plist': {
        'CFBundleName': 'FTL Autosave',
        'CFBundleDisplayName': 'FTL Autosave',
        'CFBundleIdentifier': 'com.ftlautosave.mac',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13.0',
        'NSRequiresAquaSystemAppearance': False,
    }
}

setup(
    name='FTL Autosave',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
