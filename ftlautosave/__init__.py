"""
FTL Autosave for Mac
A simple autosave utility for FTL: Faster Than Light
"""
from .config import Config
from .save_parser import FtlSaveFile
from .backup_manager import BackupManager, BackupSnapshot
from .file_watcher import FtlSaveWatcher

__version__ = "1.0.0"
__all__ = ['Config', 'FtlSaveFile', 'BackupManager', 'BackupSnapshot', 'FtlSaveWatcher']
