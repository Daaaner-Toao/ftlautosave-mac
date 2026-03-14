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
    
    # Sector info
    sector_number: int = 0
    sector_name: str = ""
    
    # Resource offset (for writing)
    _resource_offset: int = 0
    
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
        
        # Resources are located after ship type, but we need to scan for them
        # They appear after crew data and other structures
        self._find_resources_after_ship(f)
        
        # Try to find sector information
        self._find_sector_info(f)
    
    def _find_resources_after_ship(self, f):
        """Find resources by scanning the file for the resource pattern"""
        # Get current position and file size
        start_pos = f.tell()
        f.seek(0, 2)  # Seek to end
        file_size = f.tell()
        
        # Resources: hull (1-30), fuel (0-100), drones (0-50), missiles (0-50), scrap (0-2000)
        # Search from current position to end
        f.seek(start_pos)
        data = f.read()
        
        best_pos = None
        best_score = 0
        
        # Check every byte position, not just aligned ones
        for i in range(0, len(data) - 20):
            try:
                values = []
                for j in range(5):
                    val = struct.unpack('<i', data[i+j*4:i+j*4+4])[0]
                    values.append(val)
                
                hull, fuel, drones, missiles, scrap = values
                
                # Skip if fuel is unreasonably high (not a valid game state)
                if fuel > 100:
                    continue
                
                # Score based on how reasonable the values are
                score = 0
                if 1 <= hull <= 30:
                    score += 3  # Hull is most specific
                if 0 <= fuel <= 100:
                    score += 2
                if 0 <= drones <= 50:
                    score += 2
                if 0 <= missiles <= 50:
                    score += 2
                if 0 <= scrap <= 2000:
                    score += 2
                
                # Bonus for non-zero values (active game)
                if hull > 0:
                    score += 1
                if fuel > 0:
                    score += 1
                if scrap > 0:
                    score += 1
                
                # Must have reasonable hull and fuel > 0 (active game)
                if score > best_score and score >= 11 and hull > 0 and fuel > 0:
                    best_score = score
                    best_pos = i + start_pos
                    
            except struct.error:
                continue
        
        if best_pos is not None:
            self._resource_offset = best_pos
            f.seek(best_pos)
            self.hull = self._read_integer(f)
            self.fuel = self._read_integer(f)
            self.drone_parts = self._read_integer(f)
            self.missiles = self._read_integer(f)
            self.scrap = self._read_integer(f)
        else:
            # Fallback: couldn't find resources
            self._resource_offset = 0
            self.hull = 0
            self.fuel = 0
            self.drone_parts = 0
            self.missiles = 0
            self.scrap = 0
    
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
    
    def _find_sector_info(self, f):
        """Find sector information by searching for known sector names"""
        # Get file size and read entire file
        f.seek(0, 2)
        file_size = f.tell()
        f.seek(0)
        data = f.read()
        
        # List of sector names to search for (in different languages)
        # Note: These are the final sector names. Regular sectors use different names.
        sector_names = [
            # English
            "Rebel Fortress",
            "Rebel Stronghold",
            "Last Stand",
            "Hidden Base",
            "Crystal Home",
            # German
            "Rebellenfestung",
            "Rebellenhochburg",
            "Letzter Stand",
            "Versteckte Basis",
            "Kristall-Heimat",
        ]
        
        for sector_name in sector_names:
            name_bytes = sector_name.encode('utf-8')
            name_len = len(name_bytes)
            
            # Search for the sector name in the file
            pos = data.find(name_bytes)
            while pos != -1:
                # Check if there is a 4-byte length prefix before the string
                if pos >= 4:
                    length_prefix = data[pos-4:pos]
                    # Convert length prefix to integer (little-endian)
                    length = struct.unpack('<i', length_prefix)[0]
                    if length == name_len:
                        # Found a length-prefixed string match
                        # Now look for sector number nearby
                        # Check 4 bytes before the length prefix
                        if pos >= 8:
                            candidate_bytes = data[pos-8:pos-4]
                            try:
                                candidate = struct.unpack('<i', candidate_bytes)[0]
                                if 1 <= candidate <= 36:
                                    self.sector_number = candidate
                                    self.sector_name = sector_name
                                    return
                            except struct.error:
                                pass
                        # Check 4 bytes after the string
                        if pos + 4 + name_len <= file_size:
                            candidate_bytes = data[pos+4+name_len:pos+8+name_len]
                            try:
                                candidate = struct.unpack('<i', candidate_bytes)[0]
                                if 1 <= candidate <= 36:
                                    self.sector_number = candidate
                                    self.sector_name = sector_name
                                    return
                            except struct.error:
                                pass
                        # Try 2-byte and 1-byte integers for the sector number
                        # 2-byte before length prefix
                        if pos >= 6:
                            candidate_bytes = data[pos-6:pos-4]
                            try:
                                candidate = struct.unpack('<h', candidate_bytes)[0]  # signed short
                                if 1 <= candidate <= 36:
                                    self.sector_number = candidate
                                    self.sector_name = sector_name
                                    return
                            except struct.error:
                                pass
                        # 2-byte after string
                        if pos + 4 + name_len + 2 <= file_size:
                            candidate_bytes = data[pos+4+name_len:pos+6+name_len]
                            try:
                                candidate = struct.unpack('<h', candidate_bytes)[0]
                                if 1 <= candidate <= 36:
                                    self.sector_number = candidate
                                    self.sector_name = sector_name
                                    return
                            except struct.error:
                                pass
                        # 1-byte before length prefix
                        if pos >= 5:
                            candidate = data[pos-5]
                            if 1 <= candidate <= 36:
                                self.sector_number = candidate
                                self.sector_name = sector_name
                                return
                        # 1-byte after string
                        if pos + 4 + name_len + 1 <= file_size:
                            candidate = data[pos+4+name_len]
                            if 1 <= candidate <= 36:
                                self.sector_number = candidate
                                self.sector_name = sector_name
                                return
                # Move to next occurrence
                pos = data.find(name_bytes, pos + 1)
        
        # If we get here, we didn't find sector info with the above method
        # Fallback: set to unknown
        self.sector_number = 0
        self.sector_name = ""
    
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
            'sector_number': self.sector_number,
            'sector_name': self.sector_name,
        }
    
    def find_resource_offset(self) -> Optional[int]:
        """Find the offset where resources are stored in the file.
        
        Returns the cached offset from parsing, or searches for it if not cached.
        """
        # Return cached offset if available
        if self._resource_offset > 0:
            return self._resource_offset
        
        # Otherwise search for it
        try:
            with open(self.path, 'rb') as f:
                data = f.read()
            
            best_pos = None
            best_score = 0
            
            # Start search from offset 0x40 to skip header section
            # Check every byte position, not just aligned ones
            for i in range(0x40, len(data) - 20):
                try:
                    values = []
                    for j in range(5):
                        val = struct.unpack('<i', data[i+j*4:i+j*4+4])[0]
                        values.append(val)
                    
                    hull, fuel, drones, missiles, scrap = values
                    
                    # Skip if fuel is unreasonably high (not a valid game state)
                    if fuel > 100:
                        continue
                    
                    # Score based on how reasonable the values are
                    score = 0
                    if 1 <= hull <= 30:
                        score += 3  # Hull is most specific
                    if 0 <= fuel <= 100:
                        score += 2
                    if 0 <= drones <= 50:
                        score += 2
                    if 0 <= missiles <= 50:
                        score += 2
                    if 0 <= scrap <= 2000:
                        score += 2
                    
                    # Bonus for non-zero values (active game)
                    if hull > 0:
                        score += 1
                    if fuel > 0:
                        score += 1
                    if scrap > 0:
                        score += 1
                    
                    # Must have reasonable hull and fuel > 0 (active game)
                    if score > best_score and score >= 11 and hull > 0 and fuel > 0:
                        best_score = score
                        best_pos = i
                        
                except struct.error:
                    continue
            
            return best_pos
            
        except IOError:
            return None
    
    def write_resources(self, hull: Optional[int] = None, fuel: Optional[int] = None,
                        drone_parts: Optional[int] = None, missiles: Optional[int] = None,
                        scrap: Optional[int] = None) -> bool:
        """
        Write resources to the save file at the known offset.
        
        Args:
            hull: New hull value (1-30)
            fuel: New fuel value (0-100)
            drone_parts: New drone parts value (0-50)
            missiles: New missiles value (0-50)
            scrap: New scrap value (0-2000)
        
        Returns:
            True if successful, False otherwise
        
        Warning:
            FTL must be in the main menu when calling this, otherwise
            the game will overwrite the changes when it saves.
        """
        if self.is_profile:
            print("Cannot write resources to profile file")
            return False
        
        # Find the resource offset
        offset = self.find_resource_offset()
        if offset is None:
            print("Could not find resource offset in file")
            return False
        
        # Validate values
        if hull is not None and not (1 <= hull <= 30):
            print(f"Invalid hull value: {hull} (must be 1-30)")
            return False
        if fuel is not None and not (0 <= fuel <= 100):
            print(f"Invalid fuel value: {fuel} (must be 0-100)")
            return False
        if drone_parts is not None and not (0 <= drone_parts <= 50):
            print(f"Invalid drone_parts value: {drone_parts} (must be 0-50)")
            return False
        if missiles is not None and not (0 <= missiles <= 50):
            print(f"Invalid missiles value: {missiles} (must be 0-50)")
            return False
        if scrap is not None and not (0 <= scrap <= 2000):
            print(f"Invalid scrap value: {scrap} (must be 0-2000)")
            return False
        
        try:
            # Read the entire file
            with open(self.path, 'rb') as f:
                data = bytearray(f.read())
            
            # Write the new values at the resource offset
            # Order: hull, fuel, drone_parts, missiles, scrap
            if hull is not None:
                struct.pack_into('<i', data, offset, hull)
                self.hull = hull
            if fuel is not None:
                struct.pack_into('<i', data, offset + 4, fuel)
                self.fuel = fuel
            if drone_parts is not None:
                struct.pack_into('<i', data, offset + 8, drone_parts)
                self.drone_parts = drone_parts
            if missiles is not None:
                struct.pack_into('<i', data, offset + 12, missiles)
                self.missiles = missiles
            if scrap is not None:
                struct.pack_into('<i', data, offset + 16, scrap)
                self.scrap = scrap
            
            # Write back to file
            with open(self.path, 'wb') as f:
                f.write(data)
            
            print(f"Resources written successfully at offset 0x{offset:x}")
            return True
            
        except IOError as e:
            print(f"Error writing resources: {e}")
            return False
