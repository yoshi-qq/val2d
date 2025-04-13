from enum import Enum

class AbilityCategory(Enum):
    BASIC = 0
    TACTICAL = 1
    SIGNATURE = 2
    ULTIMATE = 3

class GunCategory(Enum):
    SIDEARM = 2
    SMG = 3
    SHOTGUN = 4
    RIFLE = 5
    SNIPER_RIFLE = 6
    MACHINE_GUN = 7

class PenetrationLevel(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
