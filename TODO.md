# TODO

## High Priority

- [ ] **Start/Stop/Continue Watcher Buttons** - Add buttons to manually control the file watcher
  - Start watching button
  - Stop watching button  
  - Show current watcher state clearly

- [ ] **Fix Save File Parser** - The parser currently fails on some save files
  - Debug why `ae_prof.sav` shows as invalid
  - Test with actual `continue.sav` files
  - Add better error handling and fallback parsing

- [ ] **Configuration UI** - Add a settings panel for important options
  - Watch interval
  - Max snapshots
  - Auto-purge toggle
  - Save file names (for mods)

- [ ] **Mac App Bundle** - Create a proper `.app` bundle for easy launching
  - Use `py2app` or similar
  - Include icon
  - Double-click to start

## Medium Priority

- [ ] **Auto-start FTL** - Option to launch FTL when starting the app
- [ ] **System tray** - Minimize to menu bar instead of taskbar
- [ ] **Keyboard shortcuts** - Common actions via keyboard

## Low Priority

- [ ] **Export/Import snapshots** - Backup snapshots to external location
- [ ] **Multi-profile support** - Handle multiple FTL profiles
- [ ] **Dark mode** - Better dark mode support for macOS
