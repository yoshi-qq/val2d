from typing import Union
from enum import Enum

class AbilityCategory(Enum):
    BASIC = 0
    TACTICAL = 1
    SIGNATURE = 2
    ULTIMATE = 3

class MeleeCategory(Enum):
    MELEE = 0

class GunCategory(Enum):
    SIDEARM = 5
    SMG = 6
    SHOTGUN = 7
    RIFLE = 8
    SNIPER_RIFLE = 9
    MACHINE_GUN = 10

HoldableCategory = Union[AbilityCategory, MeleeCategory, GunCategory]

class PenetrationLevel(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
