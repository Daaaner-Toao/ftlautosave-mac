#!/usr/bin/env python3
"""
FTL Autosave GUI for Mac
A simple tkinter-based GUI for FTL autosave functionality
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional
import threading
from datetime import datetime
import subprocess
import os

from .config import Config
from .backup_manager import BackupManager, BackupSnapshot
from .file_watcher import FtlSaveWatcher
from .save_parser import FtlSaveFile

# Get version
try:
    from . import __version__
except ImportError:
    __version__ = "1.2.0"


class FtlAutosaveApp:
    """Main application class"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"FTL Autosave v{__version__}")
        self.root.geometry("900x650")
        self.root.minsize(800, 550)
        
        # Load config
        self.config = Config.from_file()
        
        # Initialize backup manager
        self.backup_manager = BackupManager(self.config)
        
        # Initialize watcher (but don't start yet)
        self.watcher: Optional[FtlSaveWatcher] = None
        
        # Build UI
        self._build_ui()
        
        # Check if FTL is running and offer to start it
        self.root.after(100, self._check_ftl_running)
        
        # Start watching if path exists
        self._start_watcher()
        
        # Refresh snapshot list
        self._refresh_snapshots()
        
        # Schedule periodic refresh
        self._schedule_refresh()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _build_ui(self):
        """Build the user interface"""
        # Main container with two columns
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left column (snapshots)
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Right column (current values)
        right_frame = ttk.Frame(main_frame, padding=(10, 0, 0, 0))
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # === LEFT COLUMN ===
        
        # Status bar at top
        status_frame = ttk.LabelFrame(left_frame, text="Status", padding="5")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Status text and indicator
        status_left = ttk.Frame(status_frame)
        status_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.watching_label = ttk.Label(status_left, text="●", foreground="gray")
        self.watching_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.status_label = ttk.Label(status_left, text="Initializing...")
        self.status_label.pack(side=tk.LEFT)
        
        # Watcher control buttons
        button_frame = ttk.Frame(status_frame)
        button_frame.pack(side=tk.RIGHT)
        
        # Configure style for highlighted buttons
        style = ttk.Style()
        style.configure('Green.TButton', foreground='green')
        style.configure('Red.TButton', foreground='red')
        style.configure('Disabled.TButton', foreground='gray')
        
        self.start_btn = ttk.Button(
            button_frame,
            text="▶ Start",
            command=self._start_watcher_ui,
            width=10,
            style='Green.TButton'
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(
            button_frame,
            text="■ Stop",
            command=self._stop_watcher_ui,
            width=10,
            style='Red.TButton',
            state='disabled'
        )
        self.stop_btn.pack(side=tk.LEFT)
        
        # Path configuration
        path_frame = ttk.LabelFrame(left_frame, text="FTL Save Path", padding="5")
        path_frame.pack(fill=tk.X, pady=(0, 10))
        
        path_inner = ttk.Frame(path_frame)
        path_inner.pack(fill=tk.X)
        
        self.path_var = tk.StringVar(value=self.config.ftl_save_path)
        self.path_entry = ttk.Entry(path_inner, textvariable=self.path_var, state='readonly')
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        browse_btn = ttk.Button(path_inner, text="Browse...", command=self._browse_path)
        browse_btn.pack(side=tk.RIGHT)
        
        # Path status indicator
        self.path_status = ttk.Label(path_frame, text="")
        self.path_status.pack(anchor=tk.W)
        
        # Snapshots list
        list_frame = ttk.LabelFrame(left_frame, text="Snapshots", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Listbox with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.snapshot_list = tk.Listbox(
            list_container,
            yscrollcommand=scrollbar.set,
            selectmode=tk.EXTENDED,
            font=("Monaco", 10)
        )
        self.snapshot_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.snapshot_list.yview)
        
        self.snapshot_list.bind('<<ListboxSelect>>', self._on_snapshot_select)
        
        # Snapshot count label
        self.snapshot_count = ttk.Label(list_frame, text="0 snapshots")
        self.snapshot_count.pack(anchor=tk.W)
        
        # Details frame - structured layout
        details_frame = ttk.LabelFrame(left_frame, text="Details", padding="5")
        details_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Timestamp
        self.detail_timestamp_label = ttk.Label(
            details_frame, 
            text="Timestamp: ---",
            font=("Helvetica", 9)
        )
        self.detail_timestamp_label.pack(anchor=tk.W)
        
        # Ship info
        self.detail_ship_label = ttk.Label(
            details_frame, 
            text="Ship: ---",
            font=("Helvetica", 10, "bold")
        )
        self.detail_ship_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Separator
        ttk.Separator(details_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # Resources frame
        resources_frame = ttk.Frame(details_frame)
        resources_frame.pack(fill=tk.X)
        
        # Resources in 2 columns
        left_resources = ttk.Frame(resources_frame)
        left_resources.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        right_resources = ttk.Frame(resources_frame)
        right_resources.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        self.detail_hull_label = ttk.Label(left_resources, text="🛡 Hull: ---", font=("Monaco", 9))
        self.detail_hull_label.pack(anchor=tk.W)
        
        self.detail_fuel_label = ttk.Label(left_resources, text="⚡ Fuel: ---", font=("Monaco", 9))
        self.detail_fuel_label.pack(anchor=tk.W)
        
        self.detail_missiles_label = ttk.Label(left_resources, text="🚀 Missiles: ---", font=("Monaco", 9))
        self.detail_missiles_label.pack(anchor=tk.W)
        
        self.detail_drones_label = ttk.Label(right_resources, text="🤖 Drones: ---", font=("Monaco", 9))
        self.detail_drones_label.pack(anchor=tk.W)
        
        self.detail_scrap_label = ttk.Label(right_resources, text="💰 Scrap: ---", font=("Monaco", 9))
        self.detail_scrap_label.pack(anchor=tk.W)
        
        self.detail_sector_label = ttk.Label(right_resources, text="📍 Sector: ---", font=("Monaco", 9))
        self.detail_sector_label.pack(anchor=tk.W)
        
        # Separator
        ttk.Separator(details_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # Stats frame
        stats_frame = ttk.Frame(details_frame)
        stats_frame.pack(fill=tk.X)
        
        self.detail_defeated_label = ttk.Label(stats_frame, text="💀 Ships Defeated: ---", font=("Monaco", 9))
        self.detail_defeated_label.pack(anchor=tk.W)
        
        self.detail_explored_label = ttk.Label(stats_frame, text="🔍 Locations: ---", font=("Monaco", 9))
        self.detail_explored_label.pack(anchor=tk.W)
        
        # Version info
        self.detail_version_label = ttk.Label(
            details_frame, 
            text="Version: ---",
            font=("Helvetica", 8),
            foreground="gray"
        )
        self.detail_version_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Store details frame reference
        self.details_frame = details_frame
        
        # Buttons
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X)
        
        self.restore_btn = ttk.Button(
            button_frame,
            text="Restore Selected",
            command=self._restore_snapshot,
            state='disabled'
        )
        self.restore_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.delete_btn = ttk.Button(
            button_frame,
            text="Delete Selected",
            command=self._delete_snapshot,
            state='disabled'
        )
        self.delete_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.delete_all_btn = ttk.Button(
            button_frame,
            text="Delete All",
            command=self._delete_all_snapshots
        )
        self.delete_all_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        refresh_btn = ttk.Button(
            button_frame,
            text="Refresh",
            command=self._refresh_snapshots
        )
        refresh_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Settings button
        settings_btn = ttk.Button(
            button_frame,
            text="⚙ Settings",
            command=self._show_settings
        )
        settings_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Create backup manually button
        backup_btn = ttk.Button(
            button_frame,
            text="Create Backup Now",
            command=self._create_manual_backup
        )
        backup_btn.pack(side=tk.RIGHT)
        
        # === RIGHT COLUMN (Current Values) ===
        
        current_frame = ttk.LabelFrame(right_frame, text="Current Game", padding="10")
        current_frame.pack(fill=tk.BOTH, expand=True)
        
        # Ship name
        self.current_ship_label = ttk.Label(current_frame, text="Ship: ---", font=("Helvetica", 12, "bold"))
        self.current_ship_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Separator
        ttk.Separator(current_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 10))
        
        # Hull - editable
        hull_frame = ttk.Frame(current_frame)
        hull_frame.pack(fill=tk.X, pady=5)
        ttk.Label(hull_frame, text="🛡 Hull:", font=("Helvetica", 11)).pack(side=tk.LEFT)
        self.current_hull_var = tk.StringVar(value="---")
        self.current_hull_entry = ttk.Entry(hull_frame, textvariable=self.current_hull_var, width=8, justify='right')
        self.current_hull_entry.pack(side=tk.RIGHT)
        
        # Fuel - editable
        fuel_frame = ttk.Frame(current_frame)
        fuel_frame.pack(fill=tk.X, pady=5)
        ttk.Label(fuel_frame, text="⚡ Fuel:", font=("Helvetica", 11)).pack(side=tk.LEFT)
        self.current_fuel_var = tk.StringVar(value="---")
        self.current_fuel_entry = ttk.Entry(fuel_frame, textvariable=self.current_fuel_var, width=8, justify='right')
        self.current_fuel_entry.pack(side=tk.RIGHT)
        
        # Missiles - editable
        missiles_frame = ttk.Frame(current_frame)
        missiles_frame.pack(fill=tk.X, pady=5)
        ttk.Label(missiles_frame, text="🚀 Missiles:", font=("Helvetica", 11)).pack(side=tk.LEFT)
        self.current_missiles_var = tk.StringVar(value="---")
        self.current_missiles_entry = ttk.Entry(missiles_frame, textvariable=self.current_missiles_var, width=8, justify='right')
        self.current_missiles_entry.pack(side=tk.RIGHT)
        
        # Drone Parts - editable
        drones_frame = ttk.Frame(current_frame)
        drones_frame.pack(fill=tk.X, pady=5)
        ttk.Label(drones_frame, text="🤖 Drone Parts:", font=("Helvetica", 11)).pack(side=tk.LEFT)
        self.current_drones_var = tk.StringVar(value="---")
        self.current_drones_entry = ttk.Entry(drones_frame, textvariable=self.current_drones_var, width=8, justify='right')
        self.current_drones_entry.pack(side=tk.RIGHT)
        
        # Separator
        ttk.Separator(current_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Scrap - editable
        scrap_frame = ttk.Frame(current_frame)
        scrap_frame.pack(fill=tk.X, pady=5)
        ttk.Label(scrap_frame, text="💰 Scrap:", font=("Helvetica", 11)).pack(side=tk.LEFT)
        self.current_scrap_var = tk.StringVar(value="---")
        self.current_scrap_entry = ttk.Entry(scrap_frame, textvariable=self.current_scrap_var, width=8, justify='right')
        self.current_scrap_entry.pack(side=tk.RIGHT)
        
        # Sector (if available)
        sector_frame = ttk.Frame(current_frame)
        sector_frame.pack(fill=tk.X, pady=5)
        ttk.Label(sector_frame, text="📍 Sector:", font=("Helvetica", 11)).pack(side=tk.LEFT)
        self.current_sector_label = ttk.Label(sector_frame, text="---", font=("Monaco", 11, "bold"))
        self.current_sector_label.pack(side=tk.RIGHT)
        
        # Last updated
        ttk.Separator(current_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        self.current_updated_label = ttk.Label(current_frame, text="Last update: ---", font=("Helvetica", 9), foreground="gray")
        self.current_updated_label.pack(anchor=tk.W)
        
        # Apply Changes button
        self.apply_btn = ttk.Button(
            current_frame,
            text="Apply Changes",
            command=self._apply_value_changes
        )
        self.apply_btn.pack(fill=tk.X, pady=(10, 0))
        
        # Store right frame reference for updates
        self.right_frame = right_frame
        
        # Now update path status (after all UI elements are created)
        self._update_path_status()
    
    def _update_path_status(self):
        """Update the path status indicator"""
        save_path = Path(self.config.ftl_save_path)
        savefile = save_path / self.config.savefile
        profile = save_path / self.config.profile
        
        if save_path.exists():
            if savefile.exists():
                self.path_status.config(text="✓ Save path valid, save file found", foreground="green")
                self._update_watcher_buttons(running=self.watcher is not None, path_valid=True)
            else:
                self.path_status.config(text="⚠ Save path valid, but no save file found", foreground="orange")
                self._update_watcher_buttons(running=self.watcher is not None, path_valid=True)
        else:
            self.path_status.config(text="✗ Save path does not exist", foreground="red")
            self._update_watcher_buttons(running=False, path_valid=False)
        
        # Update current values display
        self._update_current_values()
    
    def _update_current_values(self):
        """Update the current game values display"""
        # Skip updating entry values if user is editing
        if self._is_entry_focused():
            # Only update timestamp
            self.current_updated_label.config(text=f"Last update: {datetime.now().strftime('%H:%M:%S')} (editing)")
            return
        
        save_path = Path(self.config.ftl_save_path)
        savefile = save_path / self.config.savefile
        
        if not savefile.exists():
            self.current_ship_label.config(text="Ship: No save file")
            self.current_hull_var.set("---")
            self.current_fuel_var.set("---")
            self.current_missiles_var.set("---")
            self.current_drones_var.set("---")
            self.current_scrap_var.set("---")
            self.current_sector_label.config(text="---")
            self.current_updated_label.config(text="Last update: ---")
            return
        
        try:
            parsed = FtlSaveFile(savefile)
            
            if parsed.is_profile:
                self.current_ship_label.config(text="Ship: Profile File")
                self.current_hull_var.set("---")
                self.current_fuel_var.set("---")
                self.current_missiles_var.set("---")
                self.current_drones_var.set("---")
                self.current_scrap_var.set("---")
                self.current_sector_label.config(text="---")
            else:
                # Ship name and type
                ship_display = f"{parsed.shipname or 'Unknown'} ({parsed.shiptype or 'Unknown'})"
                self.current_ship_label.config(text=ship_display)
                
                # Hull
                if parsed.hull is not None and parsed.hull > 0:
                    self.current_hull_var.set(str(parsed.hull))
                else:
                    self.current_hull_var.set("---")
                
                # Fuel
                self.current_fuel_var.set(str(parsed.fuel) if parsed.fuel is not None else "---")
                
                # Missiles
                self.current_missiles_var.set(str(parsed.missiles) if parsed.missiles is not None else "---")
                
                # Drone Parts
                self.current_drones_var.set(str(parsed.drone_parts) if parsed.drone_parts is not None else "---")
                
                # Scrap
                self.current_scrap_var.set(str(parsed.scrap) if parsed.scrap is not None else "---")
                
                # Sector (if available)
                if parsed.sector_number > 0 and parsed.sector_name:
                    self.current_sector_label.config(text=f"Sektor {parsed.sector_number} {parsed.sector_name}")
                else:
                    self.current_sector_label.config(text="---")
            
            # Update timestamp
            self.current_updated_label.config(text=f"Last update: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.current_ship_label.config(text="Ship: Error reading")
            self.current_hull_var.set("---")
            self.current_fuel_var.set("---")
            self.current_missiles_var.set("---")
            self.current_drones_var.set("---")
            self.current_scrap_var.set("---")
            self.current_sector_label.config(text="---")
            self.current_updated_label.config(text=f"Error: {str(e)[:20]}")
    
    def _browse_path(self):
        """Browse for FTL save directory"""
        current = self.path_var.get()
        path = filedialog.askdirectory(
            title="Select FTL Save Directory",
            initialdir=current if Path(current).exists() else str(Path.home())
        )
        
        if path:
            self.config.ftl_save_path = path
            self.path_var.set(path)
            self._update_path_status()
            
            # Restart watcher with new path
            self._stop_watcher()
            self._start_watcher()
            self._refresh_snapshots()
    
    def _start_watcher(self):
        """Start the file watcher"""
        if not Path(self.config.ftl_save_path).exists():
            self.status_label.config(text="Save path not found - waiting...")
            self.watching_label.config(foreground="red")
            self._update_watcher_buttons(running=False, path_valid=False)
            return
        
        self.watcher = FtlSaveWatcher(
            self.config,
            self.backup_manager,
            on_backup=self._on_backup_created
        )
        self.watcher.start()
        
        self.status_label.config(text="Watching for changes...")
        self.watching_label.config(foreground="green")
        self._update_watcher_buttons(running=True)
    
    def _stop_watcher(self):
        """Stop the file watcher"""
        if self.watcher:
            self.watcher.stop()
            self.watcher = None
        
        self.status_label.config(text="Stopped")
        self.watching_label.config(foreground="gray")
        self._update_watcher_buttons(running=False)
    
    def _start_watcher_ui(self):
        """Start watcher from UI button"""
        self._start_watcher()
    
    def _stop_watcher_ui(self):
        """Stop watcher from UI button"""
        self._stop_watcher()
    
    def _update_watcher_buttons(self, running: bool, path_valid: bool = True):
        """Update watcher control button states and styles"""
        if running:
            self.start_btn.config(state='disabled', style='Disabled.TButton')
            self.stop_btn.config(state='normal', style='Red.TButton')
        else:
            self.start_btn.config(state='normal' if path_valid else 'disabled', 
                                  style='Green.TButton' if path_valid else 'Disabled.TButton')
            self.stop_btn.config(state='disabled', style='Disabled.TButton')
    
    def _on_backup_created(self):
        """Called when a backup is created"""
        # Schedule UI update on main thread
        self.root.after(0, self._refresh_snapshots)
    
    def _refresh_snapshots(self):
        """Refresh the snapshot list"""
        # Save scroll position
        scroll_position = self.snapshot_list.yview()
        
        # Remember current selection
        current_selection = self.snapshot_list.curselection()
        selected_indices = list(current_selection) if current_selection else []
        
        # Get new snapshots
        new_snapshots = self.backup_manager.get_snapshots()
        
        # Check if list actually changed (by comparing timestamps)
        if hasattr(self, '_snapshots') and len(new_snapshots) == len(self._snapshots):
            old_timestamps = [s.timestamp for s in self._snapshots]
            new_timestamps = [s.timestamp for s in new_snapshots]
            if old_timestamps == new_timestamps:
                # No changes, just restore scroll position and return
                self.snapshot_list.yview_moveto(scroll_position[0])
                return
        
        # Clear current list
        self.snapshot_list.delete(0, tk.END)
        
        # Update snapshots
        self._snapshots = new_snapshots
        
        # Add to list
        for snapshot in self._snapshots:
            self.snapshot_list.insert(tk.END, snapshot.display_name)
        
        # Update count
        count = len(self._snapshots)
        self.snapshot_count.config(text=f"{count} snapshot{'s' if count != 1 else ''}")
        
        # Restore selection if possible
        if selected_indices:
            valid_indices = [i for i in selected_indices if i < len(self._snapshots)]
            if valid_indices:
                for idx in valid_indices:
                    self.snapshot_list.selection_set(idx)
                self._on_snapshot_select(None)
            else:
                self._clear_details()
        else:
            # No previous selection, clear details
            self._clear_details()
        
        # Restore scroll position
        self.snapshot_list.yview_moveto(scroll_position[0])
    
    def _schedule_refresh(self):
        """Schedule periodic refresh"""
        if self.config.auto_update_snapshots:
            self._refresh_snapshots()
        
        # Update current values display (only if no entry is focused)
        self._update_current_values()
        
        # Schedule next refresh
        self.root.after(3000, self._schedule_refresh)
    
    def _is_entry_focused(self) -> bool:
        """Check if any of the value entry fields is currently focused"""
        focused_widget = self.root.focus_get()
        entry_widgets = [
            self.current_hull_entry,
            self.current_fuel_entry,
            self.current_missiles_entry,
            self.current_drones_entry,
            self.current_scrap_entry
        ]
        return focused_widget in entry_widgets
    
    def _on_snapshot_select(self, event):
        """Handle snapshot selection"""
        selection = self.snapshot_list.curselection()
        
        if selection:
            # Get selected snapshot (use first if multiple selected)
            index = selection[0]
            snapshot = self._snapshots[index]
            
            # Check if we need to update details (only if selection changed)
            if not hasattr(self, '_last_selected_index') or self._last_selected_index != index:
                self._last_selected_index = index
                self._update_details_display(snapshot)
            
            # Enable buttons (for multi-select, enable if any selected)
            self.restore_btn.config(state='normal')
            self.delete_btn.config(state='normal')
        else:
            self._clear_details()
    
    def _update_details_display(self, snapshot):
        """Update the details display with snapshot info"""
        # Timestamp
        self.detail_timestamp_label.config(
            text=f"Timestamp: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        if snapshot.save_content and not snapshot.save_content.invalid_file:
            sc = snapshot.save_content
            
            if sc.is_profile:
                # Profile file
                self.detail_ship_label.config(text="Type: Achievement Profile")
                self.detail_hull_label.config(text="🛡 Hull: ---")
                self.detail_fuel_label.config(text="⚡ Fuel: ---")
                self.detail_missiles_label.config(text="🚀 Missiles: ---")
                self.detail_drones_label.config(text="🤖 Drones: ---")
                self.detail_scrap_label.config(text="💰 Scrap: ---")
                self.detail_sector_label.config(text="📍 Sector: ---")
                self.detail_defeated_label.config(text="💀 Ships Defeated: ---")
                self.detail_explored_label.config(text="🔍 Locations: ---")
                self.detail_version_label.config(text=f"Version: {sc.version} (Profile)")
            else:
                # Regular save file
                self.detail_ship_label.config(text=f"Ship: {sc.shipname or 'Unknown'} ({sc.shiptype or 'Unknown'})")
                self.detail_hull_label.config(text=f"🛡 Hull: {sc.hull or '---'}")
                self.detail_fuel_label.config(text=f"⚡ Fuel: {sc.fuel or '---'}")
                self.detail_missiles_label.config(text=f"🚀 Missiles: {sc.missiles or '---'}")
                self.detail_drones_label.config(text=f"🤖 Drones: {sc.drone_parts or '---'}")
                self.detail_scrap_label.config(text=f"💰 Scrap: {sc.scrap or '---'}")
                
                if sc.sector_number > 0 and sc.sector_name:
                    self.detail_sector_label.config(text=f"📍 Sector: {sc.sector_number} {sc.sector_name}")
                else:
                    self.detail_sector_label.config(text="📍 Sector: ---")
                
                self.detail_defeated_label.config(text=f"💀 Ships Defeated: {sc.total_ships_defeated or '---'}")
                self.detail_explored_label.config(text=f"🔍 Locations: {sc.total_locations_explored or '---'}")
                
                version_text = f"Version: {sc.version}"
                if sc.save_modifier:
                    version_text += f" ({sc.save_modifier})"
                self.detail_version_label.config(text=version_text)
        else:
            # Could not parse
            self.detail_ship_label.config(text="Ship: Unable to parse")
            self.detail_hull_label.config(text="🛡 Hull: ---")
            self.detail_fuel_label.config(text="⚡ Fuel: ---")
            self.detail_missiles_label.config(text="🚀 Missiles: ---")
            self.detail_drones_label.config(text="🤖 Drones: ---")
            self.detail_scrap_label.config(text="💰 Scrap: ---")
            self.detail_sector_label.config(text="📍 Sector: ---")
            self.detail_defeated_label.config(text="💀 Ships Defeated: ---")
            self.detail_explored_label.config(text="🔍 Locations: ---")
            self.detail_version_label.config(text="Version: ---")
    
    def _clear_details(self):
        """Clear the details display"""
        self._last_selected_index = None
        
        # Reset all detail labels
        self.detail_timestamp_label.config(text="Timestamp: ---")
        self.detail_ship_label.config(text="Ship: ---")
        self.detail_hull_label.config(text="🛡 Hull: ---")
        self.detail_fuel_label.config(text="⚡ Fuel: ---")
        self.detail_missiles_label.config(text="🚀 Missiles: ---")
        self.detail_drones_label.config(text="🤖 Drones: ---")
        self.detail_scrap_label.config(text="💰 Scrap: ---")
        self.detail_sector_label.config(text="📍 Sector: ---")
        self.detail_defeated_label.config(text="💀 Ships Defeated: ---")
        self.detail_explored_label.config(text="🔍 Locations: ---")
        self.detail_version_label.config(text="Version: ---")
        
        self.restore_btn.config(state='disabled')
        self.delete_btn.config(state='disabled')
    
    def _restore_snapshot(self):
        """Restore the selected snapshot"""
        selection = self.snapshot_list.curselection()
        
        if not selection:
            return
        
        index = selection[0]
        snapshot = self._snapshots[index]
        
        # Build confirmation message with snapshot details
        details = snapshot.get_details()
        confirm_msg = (
            f"Restore snapshot from {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}?\n\n"
            f"{details}\n\n"
            "⚠ Make sure FTL is in the main menu before restoring!"
        )
        
        # Confirm
        if not messagebox.askyesno("Confirm Restore", confirm_msg):
            return
        
        # Stop watcher before restore
        was_watching = self.watcher is not None
        if was_watching:
            self._stop_watcher()
        
        # Restore
        success = self.backup_manager.restore_snapshot(snapshot)
        
        # Restart watcher if it was running
        if was_watching:
            self._start_watcher()
        
        if success:
            messagebox.showinfo("Success", "Snapshot restored!\n\nYou can now continue your game in FTL.")
            self._refresh_snapshots()
        else:
            messagebox.showerror("Error", "Failed to restore snapshot.")
    
    def _delete_snapshot(self):
        """Delete the selected snapshot(s)"""
        selection = self.snapshot_list.curselection()
        
        if not selection:
            return
        
        # Get selected snapshots
        snapshots_to_delete = [self._snapshots[i] for i in selection]
        
        # Build confirmation message
        if len(snapshots_to_delete) == 1:
            snapshot = snapshots_to_delete[0]
            confirm_msg = (
                f"Delete snapshot from {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}?\n\n"
                "This cannot be undone!"
            )
        else:
            confirm_msg = (
                f"Delete {len(snapshots_to_delete)} selected snapshots?\n\n"
                "This cannot be undone!"
            )
        
        # Confirm
        if not messagebox.askyesno("Confirm Delete", confirm_msg):
            return
        
        # Delete all selected snapshots
        failed_count = 0
        for snapshot in snapshots_to_delete:
            if not snapshot.delete():
                failed_count += 1
        
        self._refresh_snapshots()
        
        if failed_count > 0:
            messagebox.showerror("Error", f"Failed to delete {failed_count} snapshot(s).")
    
    def _delete_all_snapshots(self):
        """Delete all snapshots except the most recent one"""
        if not hasattr(self, '_snapshots') or len(self._snapshots) <= 1:
            messagebox.showinfo("Info", "No snapshots to delete (or only one snapshot exists).")
            return
        
        count_to_delete = len(self._snapshots) - 1
        
        # Confirm
        if not messagebox.askyesno(
            "Confirm Delete All",
            f"Delete ALL {count_to_delete} snapshots?\n\n"
            "The most recent snapshot will be kept.\n"
            "This cannot be undone!"
        ):
            return
        
        # Delete all except the first (newest)
        failed_count = 0
        for snapshot in self._snapshots[1:]:
            if not snapshot.delete():
                failed_count += 1
        
        self._refresh_snapshots()
        
        if failed_count > 0:
            messagebox.showerror("Error", f"Failed to delete {failed_count} snapshot(s).")
        else:
            messagebox.showinfo("Success", f"Deleted {count_to_delete} snapshot(s).")
    
    def _create_manual_backup(self):
        """Create a manual backup"""
        snapshot = self.backup_manager.create_backup()
        
        if snapshot:
            self._refresh_snapshots()
            messagebox.showinfo("Backup Created", f"Backup created: {snapshot.display_name}")
        else:
            messagebox.showerror("Error", "Failed to create backup. Check if save file exists.")
    
    def _show_settings(self):
        """Show settings dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.geometry("400x350")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Main frame
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Watch interval
        ttk.Label(main_frame, text="Watch Interval (ms):").grid(row=0, column=0, sticky=tk.W, pady=5)
        watch_interval_var = tk.StringVar(value=str(self.config.watch_interval))
        watch_interval_entry = ttk.Entry(main_frame, textvariable=watch_interval_var, width=15)
        watch_interval_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Max snapshots
        ttk.Label(main_frame, text="Max Snapshots:").grid(row=1, column=0, sticky=tk.W, pady=5)
        max_snapshots_var = tk.StringVar(value=str(self.config.max_snapshots))
        max_snapshots_entry = ttk.Entry(main_frame, textvariable=max_snapshots_var, width=15)
        max_snapshots_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Limit backups checkbox
        limit_backups_var = tk.BooleanVar(value=self.config.limit_backup_saves)
        limit_backups_cb = ttk.Checkbutton(main_frame, text="Limit backup saves", variable=limit_backups_var)
        limit_backups_cb.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Auto-update snapshots checkbox
        auto_update_var = tk.BooleanVar(value=self.config.auto_update_snapshots)
        auto_update_cb = ttk.Checkbutton(main_frame, text="Auto-update snapshot list", variable=auto_update_var)
        auto_update_cb.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Auto-start FTL checkbox
        auto_start_var = tk.BooleanVar(value=self.config.auto_start_ftl)
        auto_start_cb = ttk.Checkbutton(main_frame, text="Auto-start FTL on launch", variable=auto_start_var)
        auto_start_cb.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Separator
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        # Save file names
        ttk.Label(main_frame, text="Save File Name:").grid(row=6, column=0, sticky=tk.W, pady=5)
        savefile_var = tk.StringVar(value=self.config.savefile)
        savefile_entry = ttk.Entry(main_frame, textvariable=savefile_var, width=20)
        savefile_entry.grid(row=6, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(main_frame, text="Profile File Name:").grid(row=7, column=0, sticky=tk.W, pady=5)
        profile_var = tk.StringVar(value=self.config.profile)
        profile_entry = ttk.Entry(main_frame, textvariable=profile_var, width=20)
        profile_entry.grid(row=7, column=1, sticky=tk.W, pady=5)
        
        # Info label
        info_label = ttk.Label(main_frame, text="Note: Save file names are for mod compatibility", 
                               foreground="gray")
        info_label.grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=9, column=0, columnspan=2, pady=15)
        
        def save_settings():
            try:
                self.config.watch_interval = int(watch_interval_var.get())
                self.config.max_snapshots = int(max_snapshots_var.get())
                self.config.limit_backup_saves = limit_backups_var.get()
                self.config.auto_update_snapshots = auto_update_var.get()
                self.config.auto_start_ftl = auto_start_var.get()
                self.config.savefile = savefile_var.get()
                self.config.profile = profile_var.get()
                self.config.to_file()
                dialog.destroy()
                messagebox.showinfo("Settings Saved", "Settings have been saved.")
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid value: {e}")
        
        ttk.Button(button_frame, text="Save", command=save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _apply_value_changes(self):
        """Apply changes to the current save file"""
        save_path = Path(self.config.ftl_save_path)
        savefile = save_path / self.config.savefile
        
        if not savefile.exists():
            messagebox.showerror("Error", "No save file found.")
            return
        
        # Parse current values
        try:
            hull = int(self.current_hull_var.get()) if self.current_hull_var.get() != "---" else None
            fuel = int(self.current_fuel_var.get()) if self.current_fuel_var.get() != "---" else None
            missiles = int(self.current_missiles_var.get()) if self.current_missiles_var.get() != "---" else None
            drones = int(self.current_drones_var.get()) if self.current_drones_var.get() != "---" else None
            scrap = int(self.current_scrap_var.get()) if self.current_scrap_var.get() != "---" else None
        except ValueError:
            messagebox.showerror("Error", "Invalid value format. Please enter numbers only.")
            return
        
        # Validate ranges
        errors = []
        if hull is not None and not (1 <= hull <= 30):
            errors.append("Hull must be between 1 and 30")
        if fuel is not None and not (0 <= fuel <= 100):
            errors.append("Fuel must be between 0 and 100")
        if missiles is not None and not (0 <= missiles <= 50):
            errors.append("Missiles must be between 0 and 50")
        if drones is not None and not (0 <= drones <= 50):
            errors.append("Drone Parts must be between 0 and 50")
        if scrap is not None and not (0 <= scrap <= 2000):
            errors.append("Scrap must be between 0 and 2000")
        
        if errors:
            messagebox.showerror("Invalid Values", "\n".join(errors))
            return
        
        # Confirm
        confirm_msg = (
            "Apply the following changes to the save file?\n\n"
            f"Hull: {hull if hull is not None else 'unchanged'}\n"
            f"Fuel: {fuel if fuel is not None else 'unchanged'}\n"
            f"Missiles: {missiles if missiles is not None else 'unchanged'}\n"
            f"Drone Parts: {drones if drones is not None else 'unchanged'}\n"
            f"Scrap: {scrap if scrap is not None else 'unchanged'}\n\n"
            "⚠ FTL MUST BE IN THE MAIN MENU!\n"
            "If FTL is currently running a game, changes will be overwritten."
        )
        
        if not messagebox.askyesno("Confirm Changes", confirm_msg):
            return
        
        # Stop watcher before making changes
        was_watching = self.watcher is not None
        if was_watching:
            self._stop_watcher()
        
        # Create backup before modifying
        self.backup_manager.create_backup()
        
        # Apply changes
        try:
            parsed = FtlSaveFile(savefile)
            success = parsed.write_resources(
                hull=hull,
                fuel=fuel,
                drone_parts=drones,
                missiles=missiles,
                scrap=scrap
            )
            
            if success:
                messagebox.showinfo("Success", "Changes applied!\n\nYou can now continue your game in FTL.")
                self._refresh_snapshots()
                self._update_current_values()
            else:
                messagebox.showerror("Error", "Failed to apply changes. Check console for details.")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply changes: {str(e)}")
        
        finally:
            # Restart watcher if it was running
            if was_watching:
                self._start_watcher()
    
    def _check_ftl_running(self):
        """Check if FTL is running and offer to start it if not"""
        # Only check if auto_start_ftl is enabled
        if not self.config.auto_start_ftl:
            return
        
        # Check if FTL is already running
        try:
            result = subprocess.run(
                ['pgrep', '-x', 'FTL'],
                capture_output=True,
                text=True
            )
            ftl_running = result.returncode == 0
        except Exception:
            ftl_running = False
        
        if ftl_running:
            # FTL is already running, no action needed
            return
        
        # FTL is not running, ask user if they want to start it
        if self.config.ftl_app_path and Path(self.config.ftl_app_path).exists():
            ftl_path = self.config.ftl_app_path
        else:
            # Try to find FTL.app
            ftl_path = self._find_ftl_app()
            if ftl_path:
                self.config.ftl_app_path = ftl_path
                self.config.to_file()
        
        if ftl_path:
            if messagebox.askyesno(
                "Start FTL?",
                "FTL is not running.\n\nWould you like to start FTL now?",
                icon='question'
            ):
                self._start_ftl(ftl_path)
        else:
            # Show message that FTL could not be found
            messagebox.showwarning(
                "FTL Not Found",
                "Could not find FTL.app.\n\n"
                "Please set the FTL app path in Settings."
            )
    
    def _find_ftl_app(self) -> Optional[str]:
        """Try to find FTL.app in common locations"""
        common_paths = [
            "/Applications/FTL.app",
            str(Path.home() / "Applications" / "FTL.app"),
            "/Applications/Games/FTL.app",
            "/Applications/Steam/steamapps/common/FTL Faster Than Light/FTL.app",
        ]
        
        for path in common_paths:
            if Path(path).exists():
                return path
        
        # Try to find using mdfind (Spotlight)
        try:
            result = subprocess.run(
                ['mdfind', 'kMDItemFSName == "FTL.app"'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                paths = result.stdout.strip().split('\n')
                if paths:
                    return paths[0]
        except Exception:
            pass
        
        return None
    
    def _start_ftl(self, app_path: str):
        """Start FTL app"""
        try:
            subprocess.run(
                ['open', app_path],
                check=True,
                timeout=10
            )
            messagebox.showinfo("FTL Started", "FTL has been launched.\n\nEnjoy your game!")
        except subprocess.TimeoutExpired:
            messagebox.showerror("Error", "Timeout while starting FTL. Please try manually.")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to start FTL: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {e}")
    
    def _on_close(self):
        """Handle window close"""
        # Stop watcher
        self._stop_watcher()
        
        # Save config
        self.config.to_file()
        
        # Destroy window
        self.root.destroy()


def main():
    """Main entry point"""
    root = tk.Tk()
    app = FtlAutosaveApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
