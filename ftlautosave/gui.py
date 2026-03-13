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

from .config import Config
from .backup_manager import BackupManager, BackupSnapshot
from .file_watcher import FtlSaveWatcher
from .save_parser import FtlSaveFile


class FtlAutosaveApp:
    """Main application class"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("FTL Autosave (Mac)")
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
        
        self.start_btn = ttk.Button(
            button_frame,
            text="▶ Start",
            command=self._start_watcher_ui,
            width=10
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(
            button_frame,
            text="■ Stop",
            command=self._stop_watcher_ui,
            width=10,
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
            selectmode=tk.SINGLE,
            font=("Monaco", 10)
        )
        self.snapshot_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.snapshot_list.yview)
        
        self.snapshot_list.bind('<<ListboxSelect>>', self._on_snapshot_select)
        
        # Snapshot count label
        self.snapshot_count = ttk.Label(list_frame, text="0 snapshots")
        self.snapshot_count.pack(anchor=tk.W)
        
        # Details frame
        details_frame = ttk.LabelFrame(left_frame, text="Details", padding="5")
        details_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.details_text = tk.Text(details_frame, height=8, font=("Monaco", 9), state='disabled')
        self.details_text.pack(fill=tk.X)
        
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
        
        # Hull
        hull_frame = ttk.Frame(current_frame)
        hull_frame.pack(fill=tk.X, pady=5)
        ttk.Label(hull_frame, text="🛡 Hull:", font=("Helvetica", 11)).pack(side=tk.LEFT)
        self.current_hull_label = ttk.Label(hull_frame, text="---/---", font=("Monaco", 11, "bold"))
        self.current_hull_label.pack(side=tk.RIGHT)
        
        # Fuel (Energy)
        fuel_frame = ttk.Frame(current_frame)
        fuel_frame.pack(fill=tk.X, pady=5)
        ttk.Label(fuel_frame, text="⚡ Fuel:", font=("Helvetica", 11)).pack(side=tk.LEFT)
        self.current_fuel_label = ttk.Label(fuel_frame, text="---", font=("Monaco", 11, "bold"))
        self.current_fuel_label.pack(side=tk.RIGHT)
        
        # Missiles
        missiles_frame = ttk.Frame(current_frame)
        missiles_frame.pack(fill=tk.X, pady=5)
        ttk.Label(missiles_frame, text="🚀 Missiles:", font=("Helvetica", 11)).pack(side=tk.LEFT)
        self.current_missiles_label = ttk.Label(missiles_frame, text="---", font=("Monaco", 11, "bold"))
        self.current_missiles_label.pack(side=tk.RIGHT)
        
        # Drone Parts
        drones_frame = ttk.Frame(current_frame)
        drones_frame.pack(fill=tk.X, pady=5)
        ttk.Label(drones_frame, text="🤖 Drone Parts:", font=("Helvetica", 11)).pack(side=tk.LEFT)
        self.current_drones_label = ttk.Label(drones_frame, text="---", font=("Monaco", 11, "bold"))
        self.current_drones_label.pack(side=tk.RIGHT)
        
        # Separator
        ttk.Separator(current_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Scrap
        scrap_frame = ttk.Frame(current_frame)
        scrap_frame.pack(fill=tk.X, pady=5)
        ttk.Label(scrap_frame, text="💰 Scrap:", font=("Helvetica", 11)).pack(side=tk.LEFT)
        self.current_scrap_label = ttk.Label(scrap_frame, text="---", font=("Monaco", 11, "bold"))
        self.current_scrap_label.pack(side=tk.RIGHT)
        
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
        save_path = Path(self.config.ftl_save_path)
        savefile = save_path / self.config.savefile
        
        if not savefile.exists():
            self.current_ship_label.config(text="Ship: No save file")
            self.current_hull_label.config(text="---/---")
            self.current_fuel_label.config(text="---")
            self.current_missiles_label.config(text="---")
            self.current_drones_label.config(text="---")
            self.current_scrap_label.config(text="---")
            self.current_sector_label.config(text="---")
            self.current_updated_label.config(text="Last update: ---")
            return
        
        try:
            parsed = FtlSaveFile(savefile)
            
            if parsed.is_profile:
                self.current_ship_label.config(text="Ship: Profile File")
                self.current_hull_label.config(text="---/---")
                self.current_fuel_label.config(text="---")
                self.current_missiles_label.config(text="---")
                self.current_drones_label.config(text="---")
                self.current_scrap_label.config(text="---")
                self.current_sector_label.config(text="---")
            else:
                # Ship name and type
                ship_display = f"{parsed.shipname or 'Unknown'} ({parsed.shiptype or 'Unknown'})"
                self.current_ship_label.config(text=ship_display)
                
                # Hull
                if parsed.hull is not None and parsed.hull > 0:
                    self.current_hull_label.config(text=str(parsed.hull))
                else:
                    self.current_hull_label.config(text="---")
                
                # Fuel
                self.current_fuel_label.config(text=str(parsed.fuel) if parsed.fuel is not None else "---")
                
                # Missiles
                self.current_missiles_label.config(text=str(parsed.missiles) if parsed.missiles is not None else "---")
                
                # Drone Parts
                self.current_drones_label.config(text=str(parsed.drone_parts) if parsed.drone_parts is not None else "---")
                
                # Scrap
                self.current_scrap_label.config(text=str(parsed.scrap) if parsed.scrap is not None else "---")
                
                # Sector (not yet implemented in parser)
                self.current_sector_label.config(text="---")
            
            # Update timestamp
            self.current_updated_label.config(text=f"Last update: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.current_ship_label.config(text="Ship: Error reading")
            self.current_hull_label.config(text="---/---")
            self.current_fuel_label.config(text="---")
            self.current_missiles_label.config(text="---")
            self.current_drones_label.config(text="---")
            self.current_scrap_label.config(text="---")
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
        """Update watcher control button states"""
        if running:
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
        else:
            self.start_btn.config(state='normal' if path_valid else 'disabled')
            self.stop_btn.config(state='disabled')
    
    def _on_backup_created(self):
        """Called when a backup is created"""
        # Schedule UI update on main thread
        self.root.after(0, self._refresh_snapshots)
    
    def _refresh_snapshots(self):
        """Refresh the snapshot list"""
        # Remember current selection
        current_selection = self.snapshot_list.curselection()
        selected_index = current_selection[0] if current_selection else None
        
        # Clear current list
        self.snapshot_list.delete(0, tk.END)
        
        # Get snapshots
        self._snapshots = self.backup_manager.get_snapshots()
        
        # Add to list
        for snapshot in self._snapshots:
            self.snapshot_list.insert(tk.END, snapshot.display_name)
        
        # Update count
        count = len(self._snapshots)
        self.snapshot_count.config(text=f"{count} snapshot{'s' if count != 1 else ''}")
        
        # Restore selection if possible
        if selected_index is not None and selected_index < len(self._snapshots):
            self.snapshot_list.selection_set(selected_index)
            self._on_snapshot_select(None)
        else:
            # Clear details
            self._clear_details()
    
    def _schedule_refresh(self):
        """Schedule periodic refresh"""
        if self.config.auto_update_snapshots:
            self._refresh_snapshots()
        
        # Update current values display
        self._update_current_values()
        
        # Schedule next refresh
        self.root.after(3000, self._schedule_refresh)
    
    def _on_snapshot_select(self, event):
        """Handle snapshot selection"""
        selection = self.snapshot_list.curselection()
        
        if selection:
            index = selection[0]
            snapshot = self._snapshots[index]
            
            # Update details
            self.details_text.config(state='normal')
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, snapshot.get_details())
            self.details_text.config(state='disabled')
            
            # Enable buttons
            self.restore_btn.config(state='normal')
            self.delete_btn.config(state='normal')
        else:
            self._clear_details()
    
    def _clear_details(self):
        """Clear the details text"""
        self.details_text.config(state='normal')
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, "Select a snapshot to see details")
        self.details_text.config(state='disabled')
        
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
        """Delete the selected snapshot"""
        selection = self.snapshot_list.curselection()
        
        if not selection:
            return
        
        index = selection[0]
        snapshot = self._snapshots[index]
        
        # Confirm
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete snapshot from {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}?\n\n"
            "This cannot be undone!"
        ):
            return
        
        # Delete
        if snapshot.delete():
            self._refresh_snapshots()
        else:
            messagebox.showerror("Error", "Failed to delete snapshot.")
    
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
