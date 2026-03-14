"""
FTL Autosave for Mac
A simple autosave utility for FTL: Faster Than Light
"""
from pathlib import Path

# Read version from VERSION file
_version_file = Path(__file__).parent.parent / "VERSION"
if _version_file.exists():
    with open(_version_file) as f:
        __version__ = f.read().strip()
else:
    __version__ = "1.2.0"  # Fallback version

from .config import Config
from .save_parser import FtlSaveFile
from .backup_manager import BackupManager, BackupSnapshot
from .file_watcher import FtlSaveWatcher

__all__ = ['Config', 'FtlSaveFile', 'BackupManager', 'BackupSnapshot', 'FtlSaveWatcher', '__version__']
