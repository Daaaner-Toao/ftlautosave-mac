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
- **Easy restore** - Pick any snapshot and restore it (go to FTL main menu first)
- **No bloat** - Pure Python, uses tkinter (built into Python), no heavy dependencies

## Requirements

- macOS
- Python 3.11 with tkinter

```bash
# Install Python 3.11 with tkinter via Homebrew
brew install python-tk@3.11
```

## Running

```bash
/opt/homebrew/bin/python3.11 run_ftlautosave.py
```

That's it. A small window opens, you see your snapshots, and it runs in the background while you play.

## How to Use

1. Start FTL and load your game
2. Start this tool
3. Play normally - snapshots are created automatically
4. If things go wrong:
   - Go to FTL's main menu (don't close the game)
   - Select a snapshot in FTL Autosave
   - Click "Restore Selected"
   - Go back to FTL and click "Continue"

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
  "max_snapshots": 500
}
```

- `watch_interval`: How often to check for changes (milliseconds)
- `limit_backup_saves`: If true, deletes oldest snapshots when exceeding max_snapshots
- `max_snapshots`: Maximum number of snapshots to keep

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
```

## How Backups Work

Backups are created with timestamps:
- `continue.sav.1700000000000`
- `ae_prof.sav.1700000000000`

The number is a Unix timestamp in milliseconds. The tool matches save files with profile files that have timestamps within 500ms of each other.

## Known Limitations

- This runs alongside FTL, not integrated into the game
- Restore while FTL is in the main menu, not during gameplay
- No auto-launch of FTL (yet)

## Credits

Based on the original [ftlautosave](https://github.com/synogen/ftlautosave) by synogen. Rewritten in Python for macOS because sometimes you just want something that works on your Mac without installing Java.

## License

MIT License - do whatever you want with it.

---

*Made by a dad who just wants to enjoy his 30 minutes of gaming without starting over for the 50th time.*
