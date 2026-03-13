# FTL Save File Format Reference

This document describes the structure of FTL save files (`continue.sav`) based on reverse engineering.

## File Overview

- **File Size**: ~4-6 KB (varies based on game state)
- **Byte Order**: Little-endian
- **Encoding**: UTF-8 for strings

## Header Section (Offset 0x00-0x0F)

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x00 | 4 | int32 | Version number (11 = current, 9 = legacy) |
| 0x04 | 4 | int32 | Unknown (usually 0) |
| 0x08 | 4 | int32 | Unknown (usually 1) |
| 0x0C | 4 | int32 | Unknown (usually 0) |

## Stats Section (Offset 0x10-0x1F)

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x10 | 4 | int32 | Total ships defeated |
| 0x14 | 4 | int32 | Total locations explored |
| 0x18 | 4 | int32 | Total scrap collected |
| 0x1C | 4 | int32 | Total crew obtained |

## Ship Info Section (Offset 0x20+)

Strings are stored with a 4-byte length prefix followed by the string data.

| Offset | Type | Description |
|--------|------|-------------|
| 0x20 | int32 | Ship name length |
| 0x24+ | string | Ship name (e.g., "Kestrel") |
| var | int32 | Ship type length |
| var+ | string | Ship type (e.g., "PLAYER_SHIP_HARD") |

## Variable Arrays Section

After ship info, there are several variable-length arrays:

### Achievements/Flags Array
- Count: 4-byte integer
- Each entry: string (length + data)
- Examples seen: "env_danger", "fired_shot", "higho2"

### Ship Variants Array
- Contains ship blueprint names
- Examples: "PLAYER_SHIP_HARD", "Kestrel", "kestral"

## Crew Section

Crew members are stored as:
```
[int32: name_length][string: name][int32: race_length][string: race]
```

Example crew found:
- "Grace" (human)
- "Mikhail" (human)
- "José" (human)

## Systems Section (Offset ~0x8C0+)

Ship systems appear to be stored as arrays of:
- System type
- Power levels
- Damage state
- Crew manning

## Weapons Section (Offset ~0xBB0+)

Weapons stored as strings:
- "MISSILES_2_PLAYER"
- "LASER_BURST_3"

## Sector/Map Section (Offset ~0xF40+)

Contains:
- Current sector information
- Beacon map data
- Event flags

### Observed Sector Data
- Event text: "REBEL_AUTO_REFUEL destroyed 1278"
- Ship references: "ship_REBEL_AUTO_REFUEL_destroyed_c1_text"

## Resources Section (Near End of File)

Resources are typically found in the last 200 bytes:

| Order | Resource | Typical Range |
|-------|----------|---------------|
| 1 | Hull | 1-30 |
| 2 | Fuel | 0-100 |
| 3 | Drone Parts | 0-50 |
| 4 | Missiles | 0-50 |
| 5 | Scrap | 0-2000 |

## Known String Patterns

### Ship Types
- `PLAYER_SHIP_HARD` - Player ship variant
- `PLAYER_SHIP_EASY` - Easy mode variant

### Achievements
- `env_danger` - Environment danger flag
- `fired_shot` - Combat flag
- `higho2` - O2 system flag

### Weapons
- `MISSILES_2_PLAYER` - Missile weapon
- `LASER_BURST_3` - Burst laser

### Events
- `REBEL_AUTO_REFUEL` - Rebel fleet event

## Parsing Strategy

Due to variable-length structures, a robust parser should:

1. **Read header** to determine version
2. **Parse stats** at fixed offset 0x10
3. **Read ship info** with length-prefixed strings
4. **Skip variable arrays** by reading count then skipping entries
5. **Scan for resources** in the last 200 bytes using pattern matching

## Version Differences

### Version 11 (Current)
- Stats at offset 0x10
- More complex structure with additional arrays

### Version 9 (Legacy)
- Stats at offset 0x0C
- Simpler structure

## Notes

- The format is not officially documented
- Structure can vary between FTL versions
- Modded games (Multiverse, etc.) may have additional data
- Some offsets may shift based on string lengths

## Future Investigation

Areas that need more research:
- [ ] Exact sector number location
- [ ] Sector type enumeration
- [ ] Beacon/jump count
- [ ] Quest progress tracking
- [ ] Exact system power allocation
- [ ] Drone loadout
- [ ] Augment list

---

*Document created from hex analysis of continue.sav*
*Last updated: 2026-03-13*
