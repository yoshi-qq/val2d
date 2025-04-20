from typing import Union, Any, Callable, Optional
from math import sqrt, degrees, radians, cos, sin, atan2
from dependencies.communications import Event, Request
from classes.heads import MessageHead
from classes.keys import MapKey, EffectKey, AbilityKey, MeleeKey, SidearmKey, GunKey, AgentKey, SpriteSetKey, InputKey
from classes.categories import HoldableCategory

# Empty prebuilts
abilities: dict[AbilityKey, "Ability"] = {}
agents: dict[AgentKey, "Agent"] = {}
effects: dict[EffectKey, "Effect"] = {}
melees: dict[MeleeKey, "Melee"] = {}
sidearms: dict[SidearmKey, "Gun"] = {}
guns: dict[GunKey, "Gun"] = {}
maps: dict[MapKey, "Map"] = {}
spriteSets: dict[SpriteSetKey, "SpriteSet"] = {}

# BASE
class Printable:
    def __str__(self) -> str:
        attrs = ", ".join(f"{k}={v}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}[{attrs}]"
    def __repr__(self) -> str:
        return self.__str__()

class NullType:
    def __repr__(self):
        return "nullType"
    def __bool__(self):
        return False

Null = NullType()
JSONType = Union[dict[str, Any], list[Any], str, int, float, bool, None]

class BaseHoldable(Printable):
    def __init__(self, category: HoldableCategory) -> None:
        self._category = category
    def getCategory(self) -> HoldableCategory:
        return self._category

# COMMUNICATION
class Message:
    def __init__(self, head: MessageHead, body: Any):
        self.head = head
        self.body = body
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Message):
            return self.head == other.head and self.body == other.body
        else: return False
    def __str__(self) -> str:
        return f"Message[head={self.head}, body={self.body}]"
    def __repr__(self) -> str:
        return self.__str__()

class Ping:
    _nextID = 1
    def __init__(self, time: float) -> None:
        self.id = self.__genID__()
        self.time = time
    def __genID__(self) -> int:
        id = Ping._nextID
        Ping._nextID += 1
        return id
    def __str__(self) -> str:
        return f"Ping[id={self.id}, time={self.time}]"
    def __repr__(self) -> str:
        return self.__str__()

# DEBUGGING
class AutoMessageTrigger:
    def __init__(self, trigger: Message | Event | Request, responseMessage: Message, amountRequired: int = 1, cooldownIterations: int = 2, cooldownTime: float = 0) -> None:
        self.trigger = trigger
        self.responseMessage = responseMessage
        self.amountRequired = amountRequired
        self.cooldownIterations = cooldownIterations
        self.cooldownTime = cooldownTime
        self.counter = {"value": 0}
        self.lastUsedTime = -1
        self.lastUsedTick = -1
    def incrCheck(self, tickID: int, tickTime: float) -> bool:
        if tickID < self.lastUsedTick + self.cooldownIterations:
            return False
        if tickTime < self.lastUsedTime + self.cooldownTime:
            return False
        self.lastUsedTick = tickID
        self.lastUsedTime = tickTime
        self.counter["value"] += 1
        if self.counter["value"] >= self.amountRequired:
            self.counter["value"] = 0
            return True
        return False
    def __str__(self) -> str:
        return f"AutoMessageTrigger[trigger={self.trigger}, response={self.responseMessage}, amountRequired={self.amountRequired}, counter={self.counter['value']}]"
    def __repr__(self) -> str:
        return self.__str__()

# EFFECTS
class Effect(Printable):
    def __init__(self, effectFunc: Callable[[], None]) -> None:
        self.__effectFunc = effectFunc
    def activate(self) -> None:
        self.__effectFunc()
    def collapseToDict(self) -> JSONType:
        return {
            "effectFunc": self.__effectFunc.__name__
        }

# INFORMATION
class Rect:
    def __init__(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
    def getX1(self) -> float:
        return self.x1
    def getY1(self) -> float:
        return self.y1
    def getX2(self) -> float:
        return self.x2
    def getY2(self) -> float:
        return self.y2

class Angle:
    def __init__(self, angle: float = 0):
        self.__angle = angle
    def setAngle(self, newAngle: float = 0):
        self.__angle = newAngle % 360
    def changeAngle(self, angleMod: float = 0):
        self.__angle = (self.__angle + angleMod) % 360
    def getAngle(self) -> float:
        return self.__angle
    # return the middle angle of two angles, returns None if they are perfectly antipodale
    def getMiddle(self, secondAngle: "Angle") -> Optional["Angle"]:
        angle1 = self.getAngle()
        angle2 = secondAngle.getAngle()
        diff = ((angle1 - angle2 + 180) % 360) - 180
        return None if abs(diff) == 180 else Angle((angle1 + diff / 2) % 360)
    def __add__(self, other: "Angle") -> "Angle":
        return Angle((self.__angle + other.getAngle()) % 360)
    def __sub__(self, other: "Angle") -> "Angle":
        return Angle((self.__angle - other.getAngle()) % 360)
    def __mul__(self, scaling: float) -> "Angle":
        return Angle(self.__angle * scaling)
    def __truediv__(self, divisor: float) -> "Angle":
        return Angle(self.__angle / divisor)
    def __str__(self):
        return f"{self.__angle}"
    def __repr__(self) -> str:
        return self.__str__()

class Position:
    def __init__(self, x: float = 0, y: float = 0, z: float = 0):
        self.__x = x
        self.__y = y
        self.__z = z
    def changePosition(self, xMod: float, yMod: float, zMod: float):
        self.__x += xMod
        self.__y += yMod
        self.__z += zMod
    def setPosition(self, newX: float = 0, newY: float = 0, newZ: float = 0):
        self.__x = newX
        self.__y = newY
        self.__z = newZ
    def setY(self, newY: float = 0):
        self.__y = newY
    def setX(self, newX: float = 0):
        self.__x = newX
    def setZ(self, newZ: float = 0):
        self.__z = newZ
    def moveTo(self, newPosition: "Position") -> None:
        self.setPosition(*newPosition.getPosition())
    def move(self, relativePosition: "Position") -> None:
        self.changePosition(*relativePosition.getPosition())
    def multiplyInPlace(self, scaling: float) -> None:
        self.__x *= scaling
        self.__y *= scaling
        self.__z *= scaling
    def multiplyHorizontalInPlace(self, scaling: float) -> None:
        self.__x *= scaling
        self.__z *= scaling
    def multiplyYInPlace(self, scaling: float) -> None:
        self.__y *= scaling
    def getX(self) -> float:
        return self.__x
    def getY(self) -> float:
        return self.__y
    def getZ(self) -> float:
        return self.__z
    def getPosition(self) -> tuple[float, float, float]:
        return (self.__x, self.__y, self.__z)
    def translateToAngle(self, angle: Angle) -> "Position":
        angleRad = radians(angle.getAngle())
        newX = self.__x * cos(angleRad) - self.__z * sin(angleRad)
        newZ = self.__x * sin(angleRad) + self.__z * cos(angleRad)
        return Position(newX, self.__y, newZ)
    def translateFromAngle(self, angle: Angle) -> "Position":
        return self.translateToAngle(Angle(-angle.getAngle()))
    def rotate(self, angle: Angle) -> "Position":
        return self.translateFromAngle(angle)
    def getHorizontalPart(self) -> "Position":
        return Position(self.__x, 0, self.__z)
    def getMagnitude(self) -> float:
        return sqrt(self.__x**2 + self.__y**2 + self.__z**2)
    def getHorizontalMagnitude(self) -> float:
        return sqrt(self.__x**2 + self.__z**2)
    def getVerticalMagnitude(self) -> float:
        return abs(self.__y)
    def getDirectionUnit(self) -> "Position":
        if magnitude := self.getMagnitude():
            return self / magnitude
        else: return Position(0,0,0)
    def getHorizontalDirectionUnit(self) -> "Position":
        if magnitude := self.getHorizontalMagnitude():
            return self.getHorizontalPart() / magnitude
        return Position(0,0,0)
    def getHorizontalAngle(self) -> Angle:
        return Angle(degrees(atan2(self.__x, self.__y)))
    def cap(self, maximumMagnitude: float) -> None:
        if self.getMagnitude() != 0 and (magnitude := self.getMagnitude()) > maximumMagnitude:
            self.multiplyInPlace(maximumMagnitude / magnitude)
    def horizontalCap(self, maximumMagnitude: float) -> None:
        if self.getHorizontalMagnitude() != 0 and (magnitude := self.getHorizontalMagnitude()) > maximumMagnitude:
            self.multiplyHorizontalInPlace(maximumMagnitude / magnitude)
    def verticalCap(self, maximumMagnitude: float) -> None:
        if self.getVerticalMagnitude() != 0 and (magnitude := self.getVerticalMagnitude()) > maximumMagnitude:
            self.multiplyYInPlace(maximumMagnitude / magnitude)
    def __mul__(self, scaling: float) -> "Position":
        return Position(self.__x * scaling, self.__y * scaling, self.__z * scaling)
    def __add__(self, other: "Position") -> "Position":
        return Position(self.__x + other.getX(), self.__y + other.getY(), self.__z + other.getZ())
    def __sub__(self, other: "Position") -> "Position":
        return Position(self.__x - other.getX(), self.__y - other.getY(), self.__z - other.getZ())
    def __truediv__(self, divisor: float) -> "Position":
        return Position(self.__x / divisor, self.__y / divisor, self.__z / divisor)
    def __lmul__(self, other: "float") -> "Position":
        return self.__mul__(other)
    
    def __str__(self):
        return f"{self.__x}:{self.__y}:{self.__z}"
    def collapseToDict(self) -> JSONType:
        return {
            "x": self.__x,
            "y": self.__y,
            "z": self.__z
        }
    def __repr__(self) -> str:
        return self.__str__()

class Pose:
    def __init__(self, position: Position | None = None, orientation: Angle | None = None) -> None:
        self.__position = position if position else Position()
        self.__orientation = orientation if orientation else Angle()
    # Setters
    def moveTo(self, newPosition: Position) -> None:
        self.__position.setPosition(*newPosition.getPosition())
    def move(self, relativePosition: Position) -> None:
        self.__position.changePosition(*relativePosition.getPosition())
    def turnTo(self, newOrientation: Angle) -> None:
        self.__orientation.setAngle(newOrientation.getAngle())
    def turn(self, relativeOrientation: Angle) -> Angle:
        self.__orientation.changeAngle(relativeOrientation.getAngle())
        return self.__orientation
    # Getters
    def getPosition(self) -> Position:
        return self.__position
    def getOrientation(self) -> Angle:
        return self.__orientation
    def __str__(self):
        return f"{self.__position}:{self.__orientation}"
    def __repr__(self) -> str:
        return self.__str__()
    
    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "position": self.__position.collapseToDict(),
            "orientation": self.getOrientation().getAngle()
        }

# BACKEND
class Connection(Printable):
    def __init__(self, name: str):
        self.__name = name
    def getName(self) -> str:
        return self.__name

class Input:
    def __init__(self, type: InputKey, held: bool = False) -> None:
        self.type = type
        self.held = held
    def __str__(self) -> str:
        return f"Input[type={self.type}, {'held' if self.held else 'pressed'}]"
    def __repr__(self) -> str:
        return self.__str__()

from classes.agentTypes import Ability, Agent
from classes.inventoryTypes import Melee, Gun
from classes.mapTypes import Map
from classes.graphicTypes import SpriteSet