# TODO

## Completed

- [x] **Snapshot Restore** - Restore snapshots to current save files
  - Backend: `BackupManager.restore_snapshot()` in backup_manager.py
  - GUI: "Restore Selected" button with confirmation dialog
  - Warning to ensure FTL is in main menu before restoring
  - Stops watcher during restore, restarts after

- [x] **Start/Stop Watcher Buttons** - Manual control for file watcher
  - Start button (▶ Start) - starts watching
  - Stop button (■ Stop) - stops watching
  - Button states update based on watcher status
  - Status indicator (●) shows current state

- [x] **Fix Save File Parser** - Parser now handles both save types correctly
  - Profile files (ae_prof.sav, prof.sav) are detected and marked as `is_profile=True`
  - Save files (continue.sav) are parsed with robust resource detection
  - Resources are found by scanning for valid patterns instead of fixed offsets
  - Better error handling with fallback values

- [x] **Configuration UI** - Settings dialog for all options
  - Watch interval, Max snapshots
  - Limit backups, Auto-update snapshots
  - Auto-start FTL
  - Save file names (for mods)

- [x] **Mac App Bundle** - Standalone `.app` bundle
  - Created with py2app
  - Size: ~25MB
  - Build: `python setup.py py2app`
  - Output: `dist/FTL Autosave.app`

## Medium Priority

- [ ] **Auto-start FTL** - Option to launch FTL when starting the app
- [ ] **System tray** - Minimize to menu bar instead of taskbar
- [ ] **Keyboard shortcuts** - Common actions via keyboard

## Low Priority

- [ ] **Export/Import snapshots** - Backup snapshots to external location
- [ ] **Multi-profile support** - Handle multiple FTL profiles
- [ ] **Dark mode** - Better dark mode support for macOS
