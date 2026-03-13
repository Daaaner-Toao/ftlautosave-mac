# FTL Autosave for Mac

A simple autosave utility for **FTL: Faster Than Light** on macOS.

## Why This Exists

Look, I'm a dad with a full-time job. I love FTL - it's one of those perfect "30 minutes before bed" games. But you know what's not fun? Losing 45 minutes of careful exploration because your ship got destroyed by a random encounter. 

FTL is designed to be unforgiving. That's part of its charm. But when you only have limited gaming time, starting over from scratch every time gets old fast. This tool lets you create save snapshots so you can go back to an earlier point if things go sideways.

Think of it as a "casual mode" for those of us who can't afford to lose an entire evening to one bad jump.

## What It Does

- **Watches your save files** - Monitors `continue.sav` and `ae_prof.sav` for changes
- **Creates automatic backups** - Every time FTL saves, a snapshot is created
- **Shows game info** - Ship name, hull, fuel, scrap, and stats for each snapshot
- **Current game values** - Right panel shows live hull, fuel, missiles, drone parts, scrap
- **Easy restore** - Pick any snapshot and restore it (go to FTL main menu first)
- **Manual controls** - Start/Stop watcher buttons, create backup on demand
- **Settings dialog** - Configure watch interval, max snapshots, save file names
- **No bloat** - Pure Python, uses tkinter (built into Python), no heavy dependencies

## Requirements

- macOS
- Python 3.11 with tkinter

```bash
# Install Python 3.11 with tkinter via Homebrew
brew install python-tk@3.11
```

## Running

### Option 1: Direct with Python

```bash
/opt/homebrew/bin/python3.11 run_ftlautosave.py
```

### Option 2: Build Mac App Bundle

Create a standalone `.app` that you can put in your Applications folder:

```bash
# Install py2app (if not already installed)
/opt/homebrew/bin/python3.11 -m pip install py2app

# Build the app
/opt/homebrew/bin/python3.11 setup.py py2app

# The app will be created at:
# dist/FTL Autosave.app
```

You can then copy `dist/FTL Autosave.app` to your Applications folder.

**Note:** The build process will show some warnings about Windows modules not found - this is normal for macOS builds and can be ignored.

## How to Use

1. Start FTL and load your game
2. Start this tool
3. Play normally - snapshots are created automatically
4. If things go wrong:
   - Go to FTL's main menu (don't close the game)
   - Select a snapshot in FTL Autosave
   - Click "Restore Selected"
   - Go back to FTL and click "Continue"

## GUI Overview

The main window shows:

**Left Panel:**
- Status indicator (green = watching, gray = stopped)
- Start/Stop buttons for manual watcher control
- FTL save path with Browse button
- Snapshot list with format: "Date, Time, Sector, Ship Type - Hull"
- Details section showing full snapshot info
- Action buttons: Restore, Delete, Refresh, Settings, Create Backup

**Right Panel:**
- Current game values (updated every 3 seconds):
  - Ship name and type
  - Hull
  - Fuel
  - Missiles
  - Drone Parts
  - Scrap
  - Sector (not yet implemented)

## Where Are My Saves?

The tool looks in the default macOS location:
```
~/Library/Application Support/FasterThanLight/
```

If your saves are somewhere else, you can change the path in the GUI.

## Configuration

A `ftlautosave.json` file is created on first run:

```json
{
  "watch_interval": 1000,
  "savefile": "continue.sav",
  "profile": "ae_prof.sav",
  "ftl_save_path": "~/Library/Application Support/FasterThanLight",
  "limit_backup_saves": true,
  "max_snapshots": 500,
  "auto_update_snapshots": true,
  "auto_start_ftl": false
}
```

- `watch_interval`: How often to check for changes (milliseconds)
- `limit_backup_saves`: If true, deletes oldest snapshots when exceeding max_snapshots
- `max_snapshots`: Maximum number of snapshots to keep
- `auto_update_snapshots`: Automatically refresh snapshot list
- `auto_start_ftl`: Launch FTL when starting the app (not yet implemented)

## Supported Versions

- FTL Advanced Edition (save format versions 9 and 11)
- Multiverse mod

## Project Structure

```
ftlautosave/
├── __init__.py        # Package initialization
├── config.py          # Configuration management
├── save_parser.py     # FTL save file parser
├── backup_manager.py  # Backup creation and management
├── file_watcher.py    # File monitoring
└── gui.py             # Tkinter GUI

docs/
└── FTL_SAVE_FORMAT.md # Save file format documentation

setup.py               # py2app configuration for Mac app bundle
run_ftlautosave.py     # Main entry point
```

## How Backups Work

Backups are created with timestamps:
- `continue.sav.1700000000000`
- `ae_prof.sav.1700000000000`

The number is a Unix timestamp in milliseconds. The tool matches save files with profile files that have timestamps within 500ms of each other.

## Known Limitations

- This runs alongside FTL, not integrated into the game
- Restore while FTL is in the main menu, not during gameplay
- Sector number extraction not yet implemented (shows "---" in snapshot list)

## Development

### Save File Format

See [`docs/FTL_SAVE_FORMAT.md`](docs/FTL_SAVE_FORMAT.md) for documentation on the FTL save file structure.

### Key Findings

Resources (hull, fuel, drones, missiles, scrap) are stored as 5 consecutive 4-byte little-endian integers, typically found around offset 0xF0-0x110 after the crew data section.

## Credits

Based on the original [ftlautosave](https://github.com/synogen/ftlautosave) by synogen. Rewritten in Python for macOS because sometimes you just want something that works on your Mac without installing Java.

## License

MIT License - do whatever you want with it.

---

*Made by a dad who just wants to enjoy his 30 minutes of gaming without starting over for the 50th time.*
