"""
FTL Save File Parser
Parses FTL save files to extract game state information
"""
import struct
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple


class FTLSaveFormatInvalid(Exception):
    """Raised when save file format is invalid"""
    pass


@dataclass
class FtlSaveFile:
    """Represents a parsed FTL save file"""
    
    path: Path
    version: int = 0
    save_modifier: str = ""
    invalid_file: bool = False
    is_profile: bool = False  # True for ae_prof.sav / prof.sav (achievement profiles)
    
    # Stats
    total_ships_defeated: int = 0
    total_locations_explored: int = 0
    total_scrap_collected: int = 0
    total_crew_obtained: int = 0
    
    # Ship info
    shipname: str = "Unknown"
    shiptype: str = "Unknown"
    
    # Resources
    hull: int = 0
    fuel: int = 0
    drone_parts: int = 0
    missiles: int = 0
    scrap: int = 0
    
    def __init__(self, path: Path):
        self.path = Path(path)
        self._parse()
    
    def _parse(self):
        """Parse the save file"""
        try:
            with open(self.path, 'rb') as f:
                # Read version (first 4 bytes, little-endian integer)
                self.version = struct.unpack('<i', f.read(4))[0]
                
                # Check if this is a profile file (achievements) vs save file
                filename = self.path.name.lower()
                if 'prof' in filename:
                    self._parse_profile(f)
                    return
                
                # Determine mapping based on version
                if self.version == 9:
                    self._parse_v9(f)
                elif self.version == 11:
                    self._parse_v11(f)
                else:
                    # Try closest version
                    self._parse_v11(f)
                    
        except (IOError, struct.error) as e:
            self.invalid_file = True
            print(f"Could not read save file: {e}")
    
    def _parse_profile(self, f):
        """Parse achievement profile file (ae_prof.sav, prof.sav)"""
        self.is_profile = True
        self.shipname = "Profile"
        self.shiptype = "Achievement Data"
        # Profile files are valid but don't contain game state
        # They store achievements and unlocks, not ship resources
    
    def _read_integer(self, f) -> int:
        """Read a 4-byte little-endian integer"""
        data = f.read(4)
        if len(data) < 4:
            raise FTLSaveFormatInvalid("Unexpected end of file")
        return struct.unpack('<i', data)[0]
    
    def _read_string(self, f) -> str:
        """Read a variable-length string (length prefix + data)"""
        length = self._read_integer(f)
        if length <= 0 or length > 2048:
            raise FTLSaveFormatInvalid(f"Invalid string length: {length}")
        data = f.read(length)
        return data.decode('utf-8', errors='replace')
    
    def _skip_structure(self, f, structure: str):
        """Skip over a structure in the file"""
        for char in structure:
            if char == 'i':
                self._read_integer(f)
            elif char == 's':
                self._read_string(f)
    
    def _skip_variable_structures(self, f, structure: str):
        """Skip variable number of structures"""
        times = self._read_integer(f)
        if times < 0 or times > 256:
            raise FTLSaveFormatInvalid(f"Invalid structure count: {times}")
        for _ in range(times):
            self._skip_structure(f, structure)
    
    def _parse_v9(self, f):
        """Parse version 9 save format"""
        # Mapping for version 9: start at offset 12
        f.seek(12)
        try:
            self._parse_common(f)
        except FTLSaveFormatInvalid:
            self.invalid_file = True
    
    def _parse_v11(self, f):
        """Parse version 11 save format (vanilla)"""
        # Mapping for version 11: start at offset 16
        f.seek(16)
        try:
            self._parse_common(f)
        except FTLSaveFormatInvalid:
            # Try Multiverse format
            f.seek(16)
            try:
                self._parse_multiverse(f)
                self.save_modifier = "Multiverse"
            except FTLSaveFormatInvalid:
                self.invalid_file = True
    
    def _parse_common(self, f):
        """Parse common save structure"""
        # Stats
        self.total_ships_defeated = self._read_integer(f)
        self.total_locations_explored = self._read_integer(f)
        self.total_scrap_collected = self._read_integer(f)
        self.total_crew_obtained = self._read_integer(f)
        
        # Ship info
        self.shipname = self._read_string(f)
        self.shiptype = self._read_string(f)
        
        # Try to find resources by searching for the pattern at end of file
        # Resources are typically near the end: hull, fuel, drones, missiles, scrap
        # Each is a 4-byte integer, values are typically small (< 1000)
        self._find_resources(f)
    
    def _find_resources(self, f):
        """Find and extract resources by scanning the file"""
        # Save current position
        current_pos = f.tell()
        
        # Get file size
        f.seek(0, 2)  # Seek to end
        file_size = f.tell()
        
        # Resources are typically in the last 100 bytes
        # Search backwards for a valid resource pattern
        # Pattern: 5 consecutive integers that could be hull, fuel, drones, missiles, scrap
        # hull: typically 1-30, fuel: 0-100, drones: 0-50, missiles: 0-50, scrap: 0-1000
        
        f.seek(max(0, file_size - 200))
        
        # Read remaining bytes and search for pattern
        data = f.read()
        
        best_pos = None
        best_score = 0
        
        for i in range(0, len(data) - 20, 4):
            # Try to read 5 integers at this position
            try:
                values = []
                for j in range(5):
                    val = struct.unpack('<i', data[i+j*4:i+j*4+4])[0]
                    values.append(val)
                
                hull, fuel, drones, missiles, scrap = values
                
                # Score based on how reasonable the values are
                score = 0
                if 1 <= hull <= 30:
                    score += 2
                if 0 <= fuel <= 100:
                    score += 2
                if 0 <= drones <= 50:
                    score += 2
                if 0 <= missiles <= 50:
                    score += 2
                if 0 <= scrap <= 2000:
                    score += 2
                
                # Bonus if values are non-zero (active game)
                if hull > 0:
                    score += 1
                if fuel > 0:
                    score += 1
                if scrap > 0:
                    score += 1
                
                if score > best_score and score >= 10:
                    best_score = score
                    best_pos = i + (file_size - len(data))
                    
            except struct.error:
                continue
        
        if best_pos is not None:
            f.seek(best_pos)
            self.hull = self._read_integer(f)
            self.fuel = self._read_integer(f)
            self.drone_parts = self._read_integer(f)
            self.missiles = self._read_integer(f)
            self.scrap = self._read_integer(f)
        else:
            # Fallback: couldn't find resources
            self.hull = 0
            self.fuel = 0
            self.drone_parts = 0
            self.missiles = 0
            self.scrap = 0
    
    def _parse_multiverse(self, f):
        """Parse Multiverse mod save format"""
        # Stats
        self.total_ships_defeated = self._read_integer(f)
        self.total_locations_explored = self._read_integer(f)
        self.total_scrap_collected = self._read_integer(f)
        self.total_crew_obtained = self._read_integer(f)
        
        # Ship info
        self.shipname = self._read_string(f)
        self.shiptype = self._read_string(f)
        
        # Use the same resource-finding approach
        self._find_resources(f)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display"""
        return {
            'version': self.version,
            'shipname': self.shipname,
            'shiptype': self.shiptype,
            'hull': self.hull,
            'fuel': self.fuel,
            'drone_parts': self.drone_parts,
            'missiles': self.missiles,
            'scrap': self.scrap,
            'total_ships_defeated': self.total_ships_defeated,
            'total_locations_explored': self.total_locations_explored,
            'total_scrap_collected': self.total_scrap_collected,
            'total_crew_obtained': self.total_crew_obtained,
            'save_modifier': self.save_modifier,
            'invalid': self.invalid_file,
            'is_profile': self.is_profile,
        }
