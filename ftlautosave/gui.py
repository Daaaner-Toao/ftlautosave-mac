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

from .config import Config
from .backup_manager import BackupManager, BackupSnapshot
from .file_watcher import FtlSaveWatcher


class FtlAutosaveApp:
    """Main application class"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("FTL Autosave (Mac)")
        self.root.geometry("600x500")
        self.root.minsize(500, 400)
        
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
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status bar at top
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="5")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="Initializing...")
        self.status_label.pack(side=tk.LEFT)
        
        self.watching_label = ttk.Label(status_frame, text="●", foreground="gray")
        self.watching_label.pack(side=tk.RIGHT)
        
        # Path configuration
        path_frame = ttk.LabelFrame(main_frame, text="FTL Save Path", padding="5")
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
        self._update_path_status()
        
        # Snapshots list
        list_frame = ttk.LabelFrame(main_frame, text="Snapshots", padding="5")
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
        details_frame = ttk.LabelFrame(main_frame, text="Details", padding="5")
        details_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.details_text = tk.Text(details_frame, height=6, font=("Monaco", 9), state='disabled')
        self.details_text.pack(fill=tk.X)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
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
        
        # Create backup manually button
        backup_btn = ttk.Button(
            button_frame,
            text="Create Backup Now",
            command=self._create_manual_backup
        )
        backup_btn.pack(side=tk.RIGHT)
    
    def _update_path_status(self):
        """Update the path status indicator"""
        save_path = Path(self.config.ftl_save_path)
        savefile = save_path / self.config.savefile
        profile = save_path / self.config.profile
        
        if save_path.exists():
            if savefile.exists():
                self.path_status.config(text="✓ Save path valid, save file found", foreground="green")
            else:
                self.path_status.config(text="⚠ Save path valid, but no save file found", foreground="orange")
        else:
            self.path_status.config(text="✗ Save path does not exist", foreground="red")
    
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
            return
        
        self.watcher = FtlSaveWatcher(
            self.config,
            self.backup_manager,
            on_backup=self._on_backup_created
        )
        self.watcher.start()
        
        self.status_label.config(text="Watching for changes...")
        self.watching_label.config(foreground="green")
    
    def _stop_watcher(self):
        """Stop the file watcher"""
        if self.watcher:
            self.watcher.stop()
            self.watcher = None
        
        self.status_label.config(text="Stopped")
        self.watching_label.config(foreground="gray")
    
    def _on_backup_created(self):
        """Called when a backup is created"""
        # Schedule UI update on main thread
        self.root.after(0, self._refresh_snapshots)
    
    def _refresh_snapshots(self):
        """Refresh the snapshot list"""
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
        
        # Clear details
        self._clear_details()
    
    def _schedule_refresh(self):
        """Schedule periodic refresh"""
        if self.config.auto_update_snapshots:
            self._refresh_snapshots()
        
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
        
        # Confirm
        if not messagebox.askyesno(
            "Confirm Restore",
            f"Restore snapshot from {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}?\n\n"
            "Make sure FTL is in the main menu before restoring!"
        ):
            return
        
        # Restore
        if self.backup_manager.restore_snapshot(snapshot):
            messagebox.showinfo("Success", "Snapshot restored!\n\nYou can now continue your game in FTL.")
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
