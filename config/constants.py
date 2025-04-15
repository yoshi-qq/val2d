from enum import Enum
# GENERAL
VERSION = (0,8,3)
STABLE = True
VERSION_STRING = f"{VERSION[0]}.{VERSION[1]}.{VERSION[2]}"

# DEBUG
class D(Enum):
    CRITICAL_ERROR = 0
    CRITICAL_ERROR_DETAILS = 1
    ERROR = 2
    ERROR_DETAILS = 3
    WARNING = 4
    WARNING_DETAILS = 5
    LOG = 6
    LOG_DETAILS = 7
    DEBUG = 8
    DEBUG_DETAILS = 9
    TRACE = 10
    TRACE_DETAILS = 11
    
DEBUG_SYMBOLS = {
    D.CRITICAL_ERROR: "🔥",
    D.CRITICAL_ERROR_DETAILS: "📋",
    D.ERROR: "❌",
    D.ERROR_DETAILS: "📋",
    D.WARNING: "⚠️",
    D.WARNING_DETAILS: "📋",
    D.LOG: "📘",
    D.LOG_DETAILS: "📋",
    D.DEBUG: "🐞",
    D.DEBUG_DETAILS: "📋",
    D.TRACE: "🔍",
    D.TRACE_DETAILS: "📋"
}

DEBUG_LEVEL: D = D.LOG

def debug(minimumLevel: D, message: object, details: object = None) -> None:
    symbol = DEBUG_SYMBOLS.get(minimumLevel, "❓")
    if details is not None and DEBUG_LEVEL.value >= minimumLevel.value + 1:
        detailsSymbol = DEBUG_SYMBOLS.get(D(minimumLevel.value + 1), "📋")
        print(f"{symbol} |{str(message)} - {detailsSymbol}|{str(details)}")
    elif DEBUG_LEVEL.value >= minimumLevel.value:
         print(f"{symbol} |{str(message)}")

# GRAPHICS
FONT = "font/fixed_sys.ttf"
AGENT_SPRITE_DIMENSIONS = (16, 32)
ZOOM_IN = 3

# COMMUNICATION
DATA_SIZE = 8192
DEFAULT_IP = "localhost"
DEFAULT_PORT = 9009
PING_INTERVAL = 1

# TESTING
TESTING_WINDOW_POSITIONS = [
    (0, 0),
    (960, 0),
    (0, 540),
    (960, 540)
]

# SERVER GAMEPLAY
AGENT_SELECT_TIME = 30
BUY_PHASE_TIME = 20

# GAME CONSTANTS
PLAYER_HEIGHT = 2
MAP_SKY = 10 # 20
ABYSS_HEIGHT = -64

# MAX_SPEED = 6.75
MAX_HP = 100
MAX_OVERHEAL = 50
MAX_SHIELD = 50
MAX_REGEN_SHIELD = 75
MAX_SPECIAL_BAR = 100