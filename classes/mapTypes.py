from classes.types import Printable, JSONType, Position, Angle
from classes.keys import SpriteSetKey

# OBJECTS
class Object(Printable):
    def __init__(self, id: int, sprite: SpriteSetKey, position: Position = Position(), orientation: Angle = Angle()):
        self.__id = id
        self.__sprite = sprite
        self.__position = position
        self.__orientation = orientation
    def getID(self) -> int:
        return self.__id
    def collapseToDict(self) -> JSONType:
        return {}

class Wall(Object):
    def __init__(self, size: Position, penetrationLevel: int) -> None:
        self.size = size
        self.penepenetrationLevel = penetrationLevel
class Box(Object):
    def __init__(self, size: Position, penetrationLevel: int) -> None:
        self.size = size
        self.penepenetrationLevel = penetrationLevel
class Cylinder(Object):
    def __init__(self, size: Position, penetrationLevel: int) -> None:
        self.size = size
        self.penepenetrationLevel = penetrationLevel
class Stair(Object):
    def __init__(self, size: Position) -> None:
        self.size = size
class Decoration(Object):
    def __init__(self, size: Position) -> None:
        self.size = size
class BreakableDoor(Object):
    def __init__(self, size: Position, HP: int) -> None:
        self.size = size
        self.HP = HP
class Switch(Object):
    def __init__(self, doorID: int) -> None:
        self.doorID = doorID
class Bike(Object):
    def __init__(self) -> None:
        pass
class UltOrb(Object):
    def __init__(self) -> None:
        pass
class Zipline(Object):
    def __init__(self, size: Position, direction: Position, force: bool = False) -> None:
        self.size = size
        self.direction = direction
        self.force = force
class Teleporter(Object):
    def __init__(self, teleportPosition: Position) -> None:
        self.teleportPosition = teleportPosition
class TPDoor(Object):
    def __init__(self) -> None:
        pass
class RotatingDoor(Object):
    def __init__(self) -> None:
        pass
class CrouchDoor(Object):
    def __init__(self) -> None:
        pass
class Abyss(Object):
    def __init__(self, size: Position) -> None:
        self.size = size

# MAP
class Map(Printable):
    def __init__(self, name: str, objects: list[Object]) -> None:
        self.__objects = objects
        self.__name = name
    def collapseToDict(self) -> JSONType:
        return {}