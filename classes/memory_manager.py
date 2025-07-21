import pymem
import pymem.process
import struct

from classes.logger import Logger
from classes.utility import Utility

# Initialize the logger for consistent logging
logger = Logger.get_logger()

class MemoryManager:
    def __init__(self, offsets: dict, client_data: dict, buttons_data: dict) -> None:
        """Initialize MemoryManager with offsets and client data."""
        self.offsets = offsets
        self.client_data = client_data
        self.buttons_data = buttons_data
        self.pm = None
        self.client_base = None
        self.ent_list = None  # Cache for entity list pointer
        self.config = None  # Configuration cache
        # Offset attributes
        self.dwEntityList = None
        self.dwLocalPlayerPawn = None
        self.dwLocalPlayerController = None
        self.dwViewMatrix = None
        self.m_iHealth = None
        self.m_iTeamNum = None
        self.m_iIDEntIndex = None
        self.m_iszPlayerName = None
        self.m_vOldOrigin = None
        self.m_pGameSceneNode = None
        self.m_bDormant = None
        self.m_hPlayerPawn = None
        self.m_flFlashDuration = None
        self.m_pBoneArray = None
        self.dwForceJump = None
        self.m_clrGlow = None
        self.m_bIsGlowing = None

    def initialize(self) -> bool:
        """
        Initialize memory access by attaching to the process and setting up necessary data.
        Returns True if successful, False otherwise.
        """
        # Check if pymem is initialized and the client module is retrieved
        if not self.initialize_pymem() or not self.get_client_module():
            return False
        # Cache the entity list pointer
        self.load_offsets()
        if self.dwEntityList is None:  # Ensure offsets were loaded successfully
            return False
        self.ent_list = self.read_longlong(self.client_base + self.dwEntityList)
        return True

    def initialize_pymem(self) -> bool:
        """Attach pymem to the game process."""
        try:
            # Attempt to attach to the cs2.exe process
            self.pm = pymem.Pymem("cs2.exe")
            logger.debug("Successfully attached to cs2.exe process.")
            return True
        except pymem.exception.ProcessNotFound:
            # Log an error if the process is not found
            logger.error("cs2.exe process not found. Ensure the game is running.")
            return False
        except Exception as e:
            # Log any other exceptions that may occur
            logger.error(f"Unexpected error while attaching to cs2.exe: {e}")
            return False

    def get_client_module(self) -> bool:
        """Retrieve the client.dll module base address."""
        try:
            # Attempt to retrieve the client.dll module
            client_module = pymem.process.module_from_name(self.pm.process_handle, "client.dll")
            self.client_base = client_module.lpBaseOfDll
            logger.debug("client.dll module found and base address retrieved.")
            return True
        except pymem.exception.ModuleNotFoundError:
            # Log an error if the module is not found
            logger.error("client.dll not found. Ensure it is loaded.")
            return False
        except Exception as e:
            # Log any other exceptions that may occur
            logger.error(f"Unexpected error while retrieving client.dll module: {e}")
            return False

    def load_offsets(self) -> None:
        """Load memory offsets from Utility.extract_offsets."""
        extracted = Utility.extract_offsets(self.offsets, self.client_data, self.buttons_data)
        if extracted:
            self.dwEntityList = extracted["dwEntityList"]
            self.dwLocalPlayerPawn = extracted["dwLocalPlayerPawn"]
            self.dwLocalPlayerController = extracted["dwLocalPlayerController"]
            self.dwViewMatrix = extracted["dwViewMatrix"]
            self.dwForceJump = extracted["dwForceJump"]
            self.m_iHealth = extracted["m_iHealth"]
            self.m_iTeamNum = extracted["m_iTeamNum"]
            self.m_iIDEntIndex = extracted["m_iIDEntIndex"]
            self.m_iszPlayerName = extracted["m_iszPlayerName"]
            self.m_vOldOrigin = extracted["m_vOldOrigin"]
            self.m_pGameSceneNode = extracted["m_pGameSceneNode"]
            self.m_bDormant = extracted["m_bDormant"]
            self.m_hPlayerPawn = extracted["m_hPlayerPawn"]
            self.m_flFlashDuration = extracted["m_flFlashDuration"]
            self.m_pBoneArray = extracted["m_pBoneArray"]
            self.m_clrGlow = extracted.get("m_clrGlow")
            self.m_bIsGlowing = extracted.get("m_bIsGlowing")
        else:
            logger.error("Failed to initialize offsets from extracted data.")

    def get_entity(self, index: int):
        """Retrieve an entity from the entity list."""
        try:
            # Use cached entity list pointer
            list_offset = 0x8 * (index >> 9)
            ent_entry = self.read_longlong(self.ent_list + list_offset + 0x10)
            entity_offset = 120 * (index & 0x1FF)
            return self.read_longlong(ent_entry + entity_offset)
        except Exception as e:
            logger.error(f"Error reading entity: {e}")
            return None

    def get_fire_logic_data(self) -> dict | None:
        """Retrieve data necessary for firing logic."""
        try:
            # Read the local player and entity ID
            player = self.read_longlong(self.client_base + self.dwLocalPlayerPawn)
            entity_id = self.read_int(player + self.m_iIDEntIndex)

            if entity_id > 0:
                # Retrieve the entity, team, and health
                entity = self.get_entity(entity_id)
                if entity:
                    entity_team = self.read_int(entity + self.m_iTeamNum)
                    player_team = self.read_int(player + self.m_iTeamNum)
                    entity_health = self.read_int(entity + self.m_iHealth)
                    return {
                        "entity_team": entity_team,
                        "player_team": player_team,
                        "entity_health": entity_health
                    }
            return None
        except Exception as e:
            # Log any exceptions that may occur during the process
            if "Could not read memory at" in str(e):
                logger.error("Game was updated, new offsets are required. Please wait for the offsets update.")
            else:
                logger.error(f"Error in fire logic: {e}")
            return None
        
    def write_float(self, address: int, value: float) -> None:
        """Write a float to memory."""
        try:
            self.pm.write_float(address, value)
            logger.debug(f"Wrote float {value} to address {hex(address)}")
        except Exception as e:
            logger.error(f"Failed to write float at address {hex(address)}: {e}")
            raise

    def write_int(self, address: int, value: int) -> None:
        """Write an integer to memory."""
        try:
            self.pm.write_int(address, value)
            logger.debug(f"Wrote int {value} to address {hex(address)}")
        except Exception as e:
            logger.error(f"Failed to write int at address {hex(address)}: {e}")
            raise

    def write_bool(self, address: int, value: bool) -> None:
        """Write a boolean to memory."""
        try:
            self.pm.write_bool(address, value)
            logger.debug(f"Wrote bool {value} to address {hex(address)}")
        except Exception as e:
            logger.error(f"Failed to write bool at address {hex(address)}: {e}")
            raise

    def write_color4(self, address: int, color: tuple) -> None:
        """Write a color (RGBA) to memory."""
        try:
            data = struct.pack('BBBB', int(color[0]), int(color[1]), int(color[2]), int(color[3]))
            self.pm.write_bytes(address, data, len(data))
            logger.debug(f"Wrote color {color} to address {hex(address)}")
        except Exception as e:
            logger.error(f"Failed to write color at address {hex(address)}: {e}")
            raise

    def read_vec3(self, address: int) -> dict | None:
        """
        Reads a 3D vector (three floats) from memory at the specified address.
        """
        try:
            return {
                "x": self.pm.read_float(address),
                "y": self.pm.read_float(address + 4),
                "z": self.pm.read_float(address + 8)
            }
        except Exception as e:
            logger.error(f"Failed to read vec3 at address {hex(address)}: {e}")
            return {"x": 0.0, "y": 0.0, "z": 0.0}

    def read_string(self, address: int, max_length: int = 256) -> str:
        """
        Reads a null-terminated string from memory at the specified address.
        """
        try:
            data = self.pm.read_bytes(address, max_length)
            string_data = data.split(b'\x00')[0]
            return string_data.decode('utf-8', errors='replace')
        except Exception as e:
            logger.error(f"Failed to read string at address {hex(address)}: {e}")
            return ""

    def read_floats(self, address: int, count: int) -> list[float]:
        """
        Reads an array of `count` floats from memory.
        """
        try:
            data = self.pm.read_bytes(address, count * 4)
            return list(struct.unpack(f'{count}f', data))
        except Exception as e:
            logger.error(f"Failed to read {count} floats at address {hex(address)}: {e}")
            return []

    def read_int(self, address: int) -> int:
        """Read an integer from memory."""
        try:
            return self.pm.read_int(address)
        except Exception as e:
            logger.error(f"Failed to read int at address {hex(address)}: {e}")
            return 0

    def read_longlong(self, address: int) -> int:
        """Read a long long from memory."""
        try:
            return self.pm.read_longlong(address)
        except Exception as e:
            logger.error(f"Failed to read longlong at address {hex(address)}: {e}")
            return 0

    @property
    def client_dll_base(self) -> int:
        """Get the base address of client.dll."""
        return self.client_base
