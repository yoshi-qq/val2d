# GENERAL
VERSION = (0,7,1)
STABLE = False
VERSION_STRING = f"{VERSION[0]}.{VERSION[1]}.{VERSION[2]}"

# GRAPHICS
FONT = "font/fixed_sys.ttf"

# COMMUNICATION
DEFAULT_IP = "localhost"
DEFAULT_PORT = 9009

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

MAP_SKY = 10 # 20
ABYSS_HEIGHT = -64

# MAX_SPEED = 6.75
MAX_HP = 100
MAX_OVERHEAL = 50
MAX_SHIELD = 50
MAX_REGEN_SHIELD = 75
MAX_SPECIAL_BAR = 100