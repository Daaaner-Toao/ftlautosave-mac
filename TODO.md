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

- [x] **FTL Save Format Reference** - Documentation for save file structure
  - Created `docs/FTL_SAVE_FORMAT.md`
  - Documents header, stats, ship info, crew, weapons, sector/map sections
  - Lists areas for future investigation (sector number, beacon count, etc.)

- [x] **GUI Layout Improvements** - Better window proportions and layout
  - Window size increased to 900x650 (from 600x500)
  - Two-column layout: snapshots on left, current values on right
  - Details section height increased to 8 lines
  - Right panel shows: Ship, Hull, Fuel, Missiles, Drone Parts, Scrap, Sector

- [x] **Snapshot Display Format** - New format for snapshot list
  - Format: "Datum, Zeit, Sektor, Schiffstyp - Hülle"
  - Example: "13.03.2026, 02:05, Sektor ---, Kestrel Cruiser - Hülle: 15"
  - Sector extraction not yet implemented (shows "---")

- [x] **Live-Value Editing** - Edit resources directly in the save file
  - Editable fields for Hull, Fuel, Missiles, Drone Parts, Scrap
  - "Apply Changes" button with confirmation dialog
  - Warning: FTL must be in main menu before applying changes
  - Automatic backup before applying changes
  - Resource offset detection fixed (now finds correct offset at 0xF3)
  - Validation of value ranges (Hull: 1-30, Fuel: 0-100, etc.)

## Medium Priority

- [ ] **Auto-start FTL** - Option to launch FTL when starting the app
- [ ] **System tray** - Minimize to menu bar instead of taskbar
- [ ] **Keyboard shortcuts** - Common actions via keyboard
- [ ] **Sector extraction** - Parse sector number from save file

## Low Priority

- [ ] **Export/Import snapshots** - Backup snapshots to external location
- [ ] **Multi-profile support** - Handle multiple FTL profiles
- [ ] **Dark mode** - Better dark mode support for macOS
