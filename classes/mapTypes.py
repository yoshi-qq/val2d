from typing import Literal, Optional
from enum import Enum
from classes.types import Printable, JSONType, Position, Angle, Rect, Pose
from classes.categories import PenetrationLevel

# OBJECTS
class Callout(Enum):
    # BASE
    ATTACKER_SPAWN = "Attacker Side Spawn"
    DEFENDER_SPAWN = "Defender Side Spawn"
    A_SITE = "A Site"
    B_SITE = "B Site"
    C_SITE = "C Site"
    # MID
    MID = "Middle"
    MID_TOP = "Middle Top"
    MID_BOTTOM = "Middle Bottom"
    MID_VENTS = "Middle Vents"
    # SITE_ADJACENT
    A_MAIN = "A Main"
    B_MAIN = "B Main"
    C_MAIN = "C Main"
    A_LONG = "A Long"
    B_LONG = "B Long"
    C_LONG = "C Long"
    A_SHORT = "A Short"
    B_SHORT = "B Short"
    C_SHORT = "C Short"
    A_BACK = "A Back"
    B_BACK = "B Back"
    C_BACK = "C Back"
    A_LINK = "A Link"
    B_LINK = "B Link"
    C_LINK = "C Link"
    A_TOWER = "A Tower"
    B_TOWER = "B Tower"
    C_TOWER = "C Tower"
    A_WINDOW = "A Window"
    B_WINDOW = "B Window"
    C_WINDOW = "C Window"
    A_LOBBY = "A Lobby"
    B_LOBBY = "B Lobby"
    C_LOBBY = "C Lobby"
    A_STAIRS = "A Stairs"
    B_STAIRS = "B Stairs"
    C_STAIRS = "C Stairs"
    A_RAMPS = "A Ramps"
    B_RAMPS = "B Ramps"
    C_RAMPS = "C Ramps"
    A_SEWER = "A Sewer"
    B_SEWER = "B Sewer"
    C_SEWER = "C Sewer"
    A_ALLEY = "A Alley"
    B_ALLEY = "B Alley"
    C_ALLEY = "C Alley"
    A_GARAGE = "A Garage"
    B_GARAGE = "B Garage"
    C_GARAGE = "C Garage"
    A_SCREENS = "A Screens"
    B_SCREENS = "B Screens"
    C_SCREENS = "C Screens"
    A_RAFTERS = "A Rafters"
    B_RAFTERS = "B Rafters"
    C_RAFTERS = "C Rafters"
    

class Object(Printable):
    def __init__(self, id: int, sprite: Optional[str], callout: Callout, position: Position = Position(), orientation: Angle = Angle()) -> None:
        self.__id = id
        self.__sprite = sprite
        self.__callout = callout
        self.__position = position
        self.__orientation = orientation
    def getID(self) -> int:
        return self.__id
    def getCallout(self) -> Callout:
        return self.__callout
    def getSprite(self) -> Optional[str]:
        return self.__sprite
    def getPose(self) -> Pose:
        return Pose(self.__position, self.__orientation)
    def getPosition(self) -> Position:
        return self.__position
    def getOrientation(self) -> Angle:
        return self.__orientation
    def collapseToDict(self) -> JSONType:
        return {}

class Wall(Object):
    def __init__(self, id: int, sprite: Optional[str], callout: Callout, position: Position = Position(), orientation: Angle = Angle(), size: Position = Position(1, 1, 1), penetrationLevel: PenetrationLevel = PenetrationLevel.MEDIUM) -> None:
        super().__init__(id, sprite, callout, position, orientation)
        self.size = size
        self.penetrationLevel = penetrationLevel
    def getSize(self) -> Position:
        return self.size
class Box(Object):
    def __init__(self, id: int, sprite: Optional[str], callout: Callout, position: Position = Position(), orientation: Angle = Angle(), size: Position = Position(1, 1, 1), penetrationLevel: PenetrationLevel = PenetrationLevel.MEDIUM) -> None:
        super().__init__(id, sprite, callout, position, orientation)
        self.size = size
        self.penetrationLevel = penetrationLevel
    def getSize(self) -> Position:
        return self.size
class Cylinder(Object):
    def __init__(self, id: int, sprite: Optional[str], callout: Callout, position: Position = Position(), orientation: Angle = Angle(), size: Position = Position(1, 1, 1), penetrationLevel: PenetrationLevel = PenetrationLevel.MEDIUM) -> None:
        super().__init__(id, sprite, callout, position, orientation)
        self.size = size
        self.penetrationLevel = penetrationLevel
    def getSize(self) -> Position:
        return self.size
class Stair(Object):
    def __init__(self, id: int, sprite: Optional[str], callout: Callout, position: Position = Position(), orientation: Angle = Angle(), size: Position = Position(1, 1, 1)) -> None:
        self.size = size
        super().__init__(id, sprite, callout, position, orientation)
class Decoration(Object):
    def __init__(self, id: int, sprite: Optional[str], callout: Callout, position: Position = Position(), orientation: Angle = Angle(), size: Position = Position(1, 1, 1)) -> None:
        self.size = size
        super().__init__(id, sprite, callout, position, orientation)
class BreakableDoor(Object):
    def __init__(self, id: int, sprite: Optional[str], callout: Callout, position: Position = Position(), orientation: Angle = Angle(), size: Position = Position(1, 1, 1), HP: int = 500) -> None:
        self.size = size
        self.HP = HP
        super().__init__(id, sprite, callout, position, orientation)
class Switch(Object):
    def __init__(self, id: int, doorID: int, sprite: Optional[str], callout: Callout, position: Position = Position(), orientation: Angle = Angle()) -> None:
        self.doorID = doorID
        super().__init__(id, sprite, callout, position, orientation)
class Bike(Object):
    def __init__(self, id: int, sprite: Optional[str], callout: Callout, position: Position = Position(), orientation: Angle = Angle()) -> None:
        super().__init__(id, sprite, callout, position, orientation)
class UltOrb(Object):
    def __init__(self, id: int, sprite: Optional[str], callout: Callout, position: Position = Position(), orientation: Angle = Angle()) -> None:
        super().__init__(id, sprite, callout, position, orientation)
class Zipline(Object):
    def __init__(self, id: int, sprite: Optional[str], callout: Callout, position: Position = Position(), orientation: Angle = Angle(), size: Position = Position(1, 1, 1), direction: Position = Position(0, 0, 1), force: bool = False) -> None:
        self.size = size
        self.direction = direction
        self.force = force
        super().__init__(id, sprite, callout, position, orientation)
class Teleporter(Object):
    def __init__(self, id: int, sprite: Optional[str], callout: Callout, position: Position = Position(), orientation: Angle = Angle(), teleportPosition: Position = Position()) -> None:
        self.teleportPosition = teleportPosition
        super().__init__(id, sprite, callout, position, orientation)
class TPDoor(Object):
    def __init__(self, id: int, sprite: Optional[str], callout: Callout, position: Position = Position(), orientation: Angle = Angle()) -> None:
        super().__init__(id, sprite, callout, position, orientation)
class RotatingDoor(Object):
    def __init__(self, id: int, sprite: Optional[str], callout: Callout, position: Position = Position(), orientation: Angle = Angle(), currentRotation: Angle = Angle()) -> None:
        self.currentRotation = currentRotation
        super().__init__(id, sprite, callout, position, orientation)
class CrouchDoor(Object):
    def __init__(self, id: int, sprite: Optional[str], callout: Callout, position: Position = Position(), orientation: Angle = Angle()) -> None:
        super().__init__(id, sprite, callout, position, orientation)
class Abyss(Object):
    def __init__(self, id: int, sprite: Optional[str], callout: Callout, position: Position = Position(), orientation: Angle = Angle(), size: Position = Position(1, 1, 1)) -> None:
        self.size = size
        super().__init__(id, sprite, callout, position, orientation)
class SpawnPoint(Object):
    def __init__(self, TeamNumber: int, id: int, callout: Callout, position: Position = Position(), orientation: Angle = Angle()) -> None:
        self.TeamNumber = TeamNumber
        super().__init__(id, None, callout, position, orientation)
class PlantSite(Object):
    def __init__(self, letter: Literal['A', 'B', 'C'], id: int, callout: Callout, position: Position = Position(), orientation: Angle = Angle(), size: Position = Position(1, 1, 1)) -> None:
        self.letter = letter
        self.size = size
        super().__init__(id, None, callout, position, orientation)

# MAP
class Map(Printable):
    def __init__(self, name: str, objects: list[Object], bounds: Rect, backgroundSprite: str) -> None:
        self.__objects = objects
        self.__name = name
    def getName(self) -> str:
        return self.__name
    def getObjects(self) -> list[Object]:
        return self.__objects
    def collapseToDict(self) -> JSONType:
        return {}