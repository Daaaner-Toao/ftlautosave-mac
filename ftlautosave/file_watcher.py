"""
File Watcher for FTL Autosave
Monitors save files for changes and triggers backups
"""
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from .config import Config
from .backup_manager import BackupManager


class FileWatcher(threading.Thread):
    """Watches a file for modifications and triggers callback on change"""
    
    def __init__(self, filepath: Path, on_change: Callable[[Path], None], interval_ms: int = 1000):
        super().__init__(daemon=True)
        self.filepath = Path(filepath)
        self.on_change = on_change
        self.interval = interval_ms / 1000.0  # Convert to seconds
        self._running = False
        self._last_modified: Optional[float] = None
    
    def run(self):
        """Main watch loop"""
        self._running = True
        print(f"Watching: {self.filepath}")
        
        while self._running:
            try:
                if self.filepath.exists():
                    current_modified = self.filepath.stat().st_mtime
                    
                    if self._last_modified is not None and current_modified != self._last_modified:
                        print(f"File changed: {self.filepath.name}")
                        self.on_change(self.filepath)
                    
                    self._last_modified = current_modified
            except OSError as e:
                print(f"Error watching file: {e}")
            
            time.sleep(self.interval)
    
    def stop(self):
        """Stop the watcher"""
        self._running = False


class FtlSaveWatcher:
    """Manages watching of FTL save files"""
    
    def __init__(self, config: Config, backup_manager: BackupManager, on_backup: Optional[Callable[[], None]] = None):
        self.config = config
        self.backup_manager = backup_manager
        self.on_backup = on_backup
        
        self._savefile_watcher: Optional[FileWatcher] = None
        self._profile_watcher: Optional[FileWatcher] = None
        self._watching = False
    
    def _on_file_changed(self, filepath: Path):
        """Called when a watched file changes"""
        snapshot = self.backup_manager.create_backup()
        
        # Purge old snapshots if enabled
        if self.config.limit_backup_saves:
            self.backup_manager.purge_old_snapshots()
        
        # Notify callback
        if self.on_backup:
            self.on_backup()
    
    def start(self):
        """Start watching save files"""
        if self._watching:
            return
        
        savefile = self.config.get_savefile_path()
        profile = self.config.get_profile_path()
        
        interval = self.config.watch_interval
        
        self._savefile_watcher = FileWatcher(
            savefile,
            self._on_file_changed,
            interval
        )
        self._profile_watcher = FileWatcher(
            profile,
            self._on_file_changed,
            interval
        )
        
        self._savefile_watcher.start()
        self._profile_watcher.start()
        self._watching = True
        
        print(f"Started watching FTL save files in: {self.config.ftl_save_path}")
    
    def stop(self):
        """Stop watching save files"""
        if self._savefile_watcher:
            self._savefile_watcher.stop()
        if self._profile_watcher:
            self._profile_watcher.stop()
        
        self._watching = False
        print("Stopped watching FTL save files")
    
    @property
    def is_watching(self) -> bool:
        """Check if currently watching"""
        return self._watching
