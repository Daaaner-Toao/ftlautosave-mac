"""
Backup Manager for FTL Autosave
Manages save snapshots and backup operations
"""
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Tuple
import threading
import time

from .config import Config
from .save_parser import FtlSaveFile


@dataclass
class BackupSnapshot:
    """Represents a backup snapshot"""
    savefile_path: Path
    profile_path: Path
    timestamp: datetime
    save_content: Optional[FtlSaveFile] = None
    
    def __post_init__(self):
        """Parse save file content if not already done"""
        if self.save_content is None and self.savefile_path.exists():
            self.save_content = FtlSaveFile(self.savefile_path)
    
    @property
    def display_name(self) -> str:
        """Generate display name for the snapshot"""
        date_str = self.timestamp.strftime("%d.%m.%Y")
        time_str = self.timestamp.strftime("%H:%M")
        
        if self.save_content and not self.save_content.invalid_file:
            if self.save_content.is_profile:
                return f"{date_str}, {time_str} - Profile Backup [v{self.save_content.version}]"
            
            # Format: Datum, Zeit, Sektor, Schiffstyp - Hülle
            if self.save_content.sector_number > 0 and self.save_content.sector_name:
                sector = f"{self.save_content.sector_number} {self.save_content.sector_name}"
            else:
                sector = "---"
            shiptype = self.save_content.shiptype or "Unknown"
            hull = self.save_content.hull if self.save_content.hull else "---"
            
            return f"{date_str}, {time_str}, Sektor {sector}, {shiptype} - Hülle: {hull}"
        
        return f"{date_str}, {time_str}"
    
    def get_details(self) -> str:
        """Get detailed information about the snapshot"""
        lines = [f"Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"]
        
        if self.save_content and not self.save_content.invalid_file:
            sc = self.save_content
            if sc.is_profile:
                lines.append(f"Type: Achievement Profile")
                lines.append(f"Version: {sc.version}")
                lines.append("")
                lines.append("(Profile files store achievements and unlocks,")
                lines.append("not game progress)")
            else:
                lines.append(f"Ship: {sc.shipname} ({sc.shiptype})")
                lines.append(f"Version: {sc.version}" + (f" ({sc.save_modifier})" if sc.save_modifier else ""))
                lines.append("")
                lines.append("Resources:")
                lines.append(f"  Hull: {sc.hull}")
                lines.append(f"  Fuel: {sc.fuel}")
                lines.append(f"  Drone Parts: {sc.drone_parts}")
                lines.append(f"  Missiles: {sc.missiles}")
                lines.append(f"  Scrap: {sc.scrap}")
                lines.append("")
                lines.append("Stats:")
                lines.append(f"  Ships Defeated: {sc.total_ships_defeated}")
                lines.append(f"  Locations Explored: {sc.total_locations_explored}")
                lines.append(f"  Scrap Collected: {sc.total_scrap_collected}")
                lines.append(f"  Crew Obtained: {sc.total_crew_obtained}")
        else:
            lines.append("(Save file could not be parsed)")
        
        return "\n".join(lines)
    
    def delete(self) -> bool:
        """Delete the backup files"""
        try:
            if self.savefile_path.exists():
                self.savefile_path.unlink()
            if self.profile_path.exists():
                self.profile_path.unlink()
            return True
        except OSError as e:
            print(f"Error deleting backup: {e}")
            return False


class BackupManager:
    """Manages backup snapshots"""
    
    def __init__(self, config: Config):
        self.config = config
        self._lock = threading.Lock()
    
    def get_snapshots(self) -> List[BackupSnapshot]:
        """Get all available snapshots, sorted by time (newest first)"""
        snapshots = []
        save_path = Path(self.config.ftl_save_path)
        
        if not save_path.exists():
            return snapshots
        
        # Find all backup files
        savefile_backups = {}
        profile_backups = {}
        
        savefile_pattern = f"{self.config.savefile}.*"
        profile_pattern = f"{self.config.profile}.*"
        
        for file in save_path.glob(savefile_pattern):
            if file.name.count('.') >= 2:  # Has timestamp suffix
                try:
                    timestamp_ms = int(file.name.split('.')[-1])
                    savefile_backups[timestamp_ms] = file
                except ValueError:
                    continue
        
        for file in save_path.glob(profile_pattern):
            if file.name.count('.') >= 2:  # Has timestamp suffix
                try:
                    timestamp_ms = int(file.name.split('.')[-1])
                    profile_backups[timestamp_ms] = file
                except ValueError:
                    continue
        
        # Match savefiles with profiles (within 500ms tolerance)
        for ts_ms, savefile in savefile_backups.items():
            # Find matching profile
            matching_profile = None
            for profile_ts, profile in profile_backups.items():
                if abs(ts_ms - profile_ts) < 500:
                    matching_profile = profile
                    break
            
            if matching_profile:
                timestamp = datetime.fromtimestamp(ts_ms / 1000)
                snapshot = BackupSnapshot(
                    savefile_path=savefile,
                    profile_path=matching_profile,
                    timestamp=timestamp
                )
                snapshots.append(snapshot)
        
        # Sort by timestamp, newest first
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)
        
        return snapshots
    
    def create_backup(self) -> Optional[BackupSnapshot]:
        """Create a backup of current save files"""
        with self._lock:
            savefile = self.config.get_savefile_path()
            profile = self.config.get_profile_path()
            
            if not savefile.exists():
                print(f"Save file not found: {savefile}")
                return None
            
            # Use current timestamp in milliseconds
            timestamp_ms = int(time.time() * 1000)
            
            # Create backup filenames
            savefile_backup = savefile.parent / f"{savefile.name}.{timestamp_ms}"
            profile_backup = profile.parent / f"{profile.name}.{timestamp_ms}"
            
            try:
                # Copy save file
                shutil.copy2(savefile, savefile_backup)
                print(f"Created backup: {savefile_backup.name}")
                
                # Copy profile if it exists
                if profile.exists():
                    shutil.copy2(profile, profile_backup)
                    print(f"Created backup: {profile_backup.name}")
                
                return BackupSnapshot(
                    savefile_path=savefile_backup,
                    profile_path=profile_backup,
                    timestamp=datetime.fromtimestamp(timestamp_ms / 1000)
                )
                
            except OSError as e:
                print(f"Error creating backup: {e}")
                return None
    
    def restore_snapshot(self, snapshot: BackupSnapshot) -> bool:
        """Restore a snapshot to the current save files"""
        with self._lock:
            savefile = self.config.get_savefile_path()
            profile = self.config.get_profile_path()
            
            try:
                # Restore save file
                if snapshot.savefile_path.exists():
                    shutil.copy2(snapshot.savefile_path, savefile)
                    print(f"Restored: {savefile}")
                
                # Restore profile
                if snapshot.profile_path.exists():
                    shutil.copy2(snapshot.profile_path, profile)
                    print(f"Restored: {profile}")
                
                return True
                
            except OSError as e:
                print(f"Error restoring snapshot: {e}")
                return False
    
    def purge_old_snapshots(self, max_count: Optional[int] = None) -> int:
        """Delete oldest snapshots if count exceeds max_count"""
        if max_count is None:
            max_count = self.config.max_snapshots
        
        snapshots = self.get_snapshots()
        
        if len(snapshots) <= max_count:
            return 0
        
        # Delete oldest snapshots
        to_delete = snapshots[max_count:]
        deleted_count = 0
        
        for snapshot in to_delete:
            if snapshot.delete():
                deleted_count += 1
        
        print(f"Purged {deleted_count} old snapshots")
        return deleted_count
