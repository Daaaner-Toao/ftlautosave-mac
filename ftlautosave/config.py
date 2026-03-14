"""
Configuration management for FTL Autosave
"""
import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Config:
    """Configuration settings for FTL Autosave"""
    
    # Watch interval in milliseconds
    watch_interval: int = 1000
    
    # Save file names
    savefile: str = "continue.sav"
    profile: str = "ae_prof.sav"
    
    # FTL save path (Mac default)
    ftl_save_path: str = ""
    
    # FTL app path (for launching the game)
    ftl_app_path: str = ""
    
    # Auto-start FTL
    auto_start_ftl: bool = False
    
    # Auto-update snapshots list
    auto_update_snapshots: bool = True
    
    # Limit backup saves to 500
    limit_backup_saves: bool = True
    
    # Maximum number of snapshots to keep
    max_snapshots: int = 500
    
    def __post_init__(self):
        """Set default paths after initialization"""
        if not self.ftl_save_path:
            # Mac default path
            mac_path = Path.home() / "Library" / "Application Support" / "FasterThanLight"
            if mac_path.exists():
                self.ftl_save_path = str(mac_path)
            else:
                # Fallback
                self.ftl_save_path = str(mac_path)
        
        if not self.ftl_app_path:
            # Try to find FTL.app in common locations
            common_paths = [
                "/Applications/FTL.app",
                Path.home() / "Applications" / "FTL.app",
                "/Applications/Games/FTL.app",
            ]
            for path in common_paths:
                if Path(path).exists():
                    self.ftl_app_path = str(path)
                    break
    
    @classmethod
    def from_file(cls, filepath: str = "ftlautosave.json") -> "Config":
        """Load configuration from JSON file"""
        config_path = Path(filepath)
        
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                
                # Migration: ftl_run_path → ftl_app_path (renamed field)
                if "ftl_run_path" in data and "ftl_app_path" not in data:
                    data["ftl_app_path"] = data.pop("ftl_run_path")
                    print("Migrated config: ftl_run_path → ftl_app_path")
                
                return cls(**data)
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Could not load config: {e}, using defaults")
        
        # Create default config
        config = cls()
        config.to_file(filepath)
        return config
    
    def to_file(self, filepath: str = "ftlautosave.json"):
        """Save configuration to JSON file"""
        with open(filepath, "w") as f:
            json.dump(asdict(self), f, indent=2)
    
    def get_savefile_path(self) -> Path:
        """Get full path to save file"""
        return Path(self.ftl_save_path) / self.savefile
    
    def get_profile_path(self) -> Path:
        """Get full path to profile file"""
        return Path(self.ftl_save_path) / self.profile
