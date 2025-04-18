from enum import Enum
from classes.heads import DebugProblem, DebugReason, DebugDetails, debugProblems, debugReasons, debugDetails
from dependencies.console import Console
# GENERAL
VERSION = (0,9,6)
STABLE = False
VERSION_STRING = f"{VERSION[0]}.{VERSION[1]}.{VERSION[2]}"

# DEBUG
class D(Enum):
    CRITICAL_ERROR = 0
    CRITICAL_ERROR_REASONED = 1
    CRITICAL_ERROR_DETAILS = 2
    ERROR = 10
    ERROR_REASONED = 11
    ERROR_DETAILS = 12
    WARNING = 20
    WARNING_REASONED = 21
    WARNING_DETAILS = 22
    LOG = 30
    LOG_REASONED = 31
    LOG_DETAILS = 32
    DEBUG = 40
    DEBUG_REASONED = 41
    DEBUG_DETAILS = 42
    TRACE = 50
    TRACE_REASONED = 51
    TRACE_DETAILS = 52
    
DEBUG_LEVEL: D = D.LOG_REASONED

DEBUG_SYMBOLS = {
    D.CRITICAL_ERROR: "🔥",
    D.CRITICAL_ERROR_REASONED: "🔥ℹ️",
    D.CRITICAL_ERROR_DETAILS: "📋",
    D.ERROR: "❌",
    D.ERROR_REASONED: "❌ℹ️",
    D.ERROR_DETAILS: "📋",
    D.WARNING: "⚠️",
    D.WARNING_REASONED: "⚠️ℹ️",
    D.WARNING_DETAILS: "📋",
    D.LOG: "📘",
    D.LOG_REASONED: "📘ℹ️",
    D.LOG_DETAILS: "📋",
    D.DEBUG: "🐞",
    D.DEBUG_REASONED: "🐞ℹ️",
    D.DEBUG_DETAILS: "📋",
    D.TRACE: "🔍",
    D.TRACE_REASONED: "🔍ℹ️",
    D.TRACE_DETAILS: "📋"
}

CONSOLE = Console()

def unpack(tup: tuple[str, str]) -> str:
    return f"{tup[0]} {tup[1]}".strip()

def debug(minimumLevel: D, problem: DebugProblem, reason: DebugReason = DebugReason.EXPECTED, details: DebugDetails = DebugDetails.EMPTY, detailsObject: object = None) -> None:
    symbol = DEBUG_SYMBOLS.get(minimumLevel, "❓")
    if ((details is not DebugDetails.EMPTY) or (detailsObject is not None)) and DEBUG_LEVEL.value >= minimumLevel.value + 2:
        detailsSymbol = DEBUG_SYMBOLS.get(D(minimumLevel.value + 1), "📋")
        CONSOLE.log(f"{symbol} |{unpack(debugProblems[problem])} <- {unpack(debugReasons[reason])} - ", f"{detailsSymbol}|{unpack(debugDetails[details])}")
    elif DEBUG_LEVEL.value >= minimumLevel.value + 1:
        CONSOLE.log(f"{symbol} |{unpack(debugProblems[problem])} <- {unpack(debugReasons[reason])}")
    elif DEBUG_LEVEL.value >= minimumLevel.value:
        CONSOLE.log(f"{symbol} |{unpack(debugProblems[problem])}")

#? FUTURE SETTINGS
DEFAULT_SENSITIVITY = 0.2

# GRAPHICS
RESOLUTION = (1920, 1080)
FONT = "font/fixed_sys.ttf"
AGENT_SPRITE_DIMENSIONS = (1, 2)
ZOOM_IN = RESOLUTION[0] / 30

# COMMUNICATION
DATA_SIZE = 8192
DEFAULT_IP = "localhost"
DEFAULT_PORT = 9009
PING_INTERVAL = 1
SERVER_NAME = "SERVER"

# TESTING
TESTING_WINDOW_POSITIONS = [
    (0, 0),
    (960, 0),
    (0, 540),
    (960, 540)
]

# SERVER 
TICK_RATE = 1/20

# GAMEPLAY
AGENT_SELECT_TIME = 30
BUY_PHASE_TIME = 20

# GAME CONSTANTS
PLAYER_HEIGHT = 2
DEFAULT_DECELERATION = 50 # TODO: find value
# DEFAULT_JERK = 426.7
# DEFAULT_MAX_ACCELERATION = 42.7 # TODO: ?make this dynamic
DEFAULT_ACCELERATION = 32
DEFAULT_KNIFE_SPEED = 6.75
DEFAULT_SPEED = 5.4
DEFAULT_ABILITY_SPEED = DEFAULT_SPEED
WALK_SPEED_MOD = 0.7 # TODO: find value
CROUCH_SPEED_MOD = 0.7 # TODO: find value
AIRBORNE_SPEED_MOD = 0.7 # TODO: find value
MAP_SKY = 10 # 20
ABYSS_HEIGHT = -64

# MAX_SPEED = 6.75
MAX_HP = 100
MAX_OVERHEAL = 50
MAX_SHIELD = 50
MAX_REGEN_SHIELD = 75
MAX_SPECIAL_BAR = 100