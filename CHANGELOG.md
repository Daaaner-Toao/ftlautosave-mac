# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-03-14

### Added
- FTL Auto-Start: Prüft beim Start ob FTL läuft und bietet an, es zu starten
- Multi-Select für Snapshots: Shift+Click und Ctrl+Click für Mehrfachauswahl
- Delete All Button: Löscht alle Snapshots außer dem neuesten
- Verbessertes Details-Layout: Strukturierte Anzeige mit Emojis und 2-Spalten-Layout
- Sektor-Erkennung: Zeigt Sektor-Name und Nummer an (unterstützt EN/DE)

### Fixed
- IndentationError in gui.py behoben
- Scroll-Position springt nicht mehr nach oben nach Refresh
- Timeout für FTL-Start (10 Sekunden) verhindert GUI-Einfrieren
- Build-Prozess mit py2app semi-standalone Modus

### Changed
- Config: `ftl_run_path` → `ftl_app_path` (mit Migration für alte Configs)
- Details-Anzeige: Text-Widget durch strukturierte Labels ersetzt

## [1.1.0] - Previous Release

### Added
- Initial GUI implementation
- Snapshot management (create, restore, delete)
- Current game values display and editing
- File watcher for automatic backups
- Settings dialog

---

## Version Naming Convention

This project follows **Semantic Versioning (SemVer)**:

- **MAJOR** (X.0.0): Breaking changes, major rewrites
- **MINOR** (1.X.0): New features, backwards compatible
- **PATCH** (1.1.X): Bug fixes, minor improvements

### Examples:
- `1.0.0` → `1.1.0`: New feature added (e.g., multi-select)
- `1.1.0` → `1.1.1`: Bug fix (e.g., fixed scroll position)
- `1.1.0` → `2.0.0`: Breaking change (e.g., removed old API)
