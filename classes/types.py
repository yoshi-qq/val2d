from typing import Union, Any
from config.contstants import MAX_HP, MAX_OVERHEALTH, MAX_SHIELD, MAX_REGEN_SHIELD, MAX_SPECIAL_BAR
from enum import Enum

# GRAPHICS
class SpriteSet:
    def __init__(self) -> None:
        pass # TODO 2

# CATEGORIES
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

# EFFECTS
class Effect:
    def __init__(self) -> None:
        pass # TODO 7

# INFORMATION
class Position:
    def __init__(self, x: float = 0, y: float = 0, z: float = 0):
        self.__x = x
        self.__y = y
        self.__z = z
    def changePosition(self, xMod, yMod, zMod):
        self.__x += xMod
        self.__y += yMod
        self.__z += zMod
    def setPosition(self, newX: float = 0, newY: float = 0, newZ: float = 0):
        self.__x = newX
        self.__y = newY
        self.__z = newZ
    def getPosition(self) -> tuple[float, float, float]:
        return (self.__x, self.__y, self.__z)
    def __str__(self):
        return f"{self.__x}:{self.__y}:{self.__z}"
    
class Angle:
    def __init__(self, angle: float = 0):
        self.__angle = angle
    def changeAngle(self, angleMod: float = 0):
        self.__angle += angleMod
    def getAngle(self) -> float:
        return self.__angle
    def __str__(self):
        return f"{self.__angle}"

class Pose:
    def __init__(self, position: Position, orientation: Angle) -> None:
        self.__position = position
        self.__orientation = orientation
    # Setters
    def moveTo(self, newPosition: Position) -> None:
        self.__position.setPosition(*newPosition.getPosition())
    def move(self, relativePosition: Position) -> None:
        self.__position.changePosition(*relativePosition.getPosition())
    def turnTo(self, newOrientation: Angle) -> None:
        self.__orientation.changeAngle(newOrientation.getAngle())
    def turn(self, relativeOrientation: Angle) -> None:
        self.__orientation.changeAngle(relativeOrientation.getAngle())
    # Getters
    def getPosition(self) -> Position:
        return self.__position
    def getOrientation(self) -> Angle:
        return self.__orientation
    def __str__(self):
        return f"{self.__position}:{self.__orientation}"

class Vitals:
    def __init__(self, hp: int = 100, overheal: int= 0, shield: int = 0, regenShield: int = 0, specialBar: int = 100) -> None:
        self.__hp = hp
        self.__overheal = overheal
        self.__shield = shield
        self.__regenShield = regenShield
        self.__specialBar = specialBar
    # Getters
    def getHP(self) -> int:
        return self.__hp
    def getOverheal(self) -> int:
        return self.__overheal
    def getShield(self) -> int:
        return self.__shield
    def getRegenShield(self) -> int:
        return self.__regenShield
    def getSpecialBar(self) -> int:
        return self.__specialBar
    # Setters
    def setHP(self, newHP: int) -> None:
        self.__hp = newHP
    def setOverheal(self, newOverheal: int) -> None:
        self.__overheal = newOverheal
    def setShield(self, newShield: int) -> None:
        self.__shield = newShield
    def setRegenShield(self, newRegenShield: int) -> None:
        self.__regenShield = newRegenShield
    def setSpecialBar(self, newSpecialBar: int) -> None:
        self.__specialBar = newSpecialBar
    
class Buff:
    def __init__(self, name: str, effect: Any) -> None:
        self.__name = name
        self.__effect = effect
    def getName(self) -> str:
        return self.__name
    def getEffect(self) -> Any:
        return self.__effect

class Status:
    def __init__(self, basicCharges: int = 0, tacticalCharges: int = 0, signatureCharges: int = 1,  ultimateCharges: int = 0, ultimatePoints: int = 0, signatureCooldown: float = 45, signatureKills: int = 0) -> None:
        # Ability
        self.__basicCharges = basicCharges
        self.__tacticalCharges = tacticalCharges
        self.__signatureCharges = signatureCharges
        self.__ultimateCharges = ultimateCharges
        self.__ultimatePoints = ultimatePoints
        self.__signatureCooldown = signatureCooldown
        self.__signatureKills = signatureKills

        self.__buffs = list[tuple[Buff, float]]
        
    # Getters
    def getBasicCharges(self) -> int:
        return self.__basicCharges
    def getTacticalCharges(self) -> int:
        return self.__tacticalCharges
    def getSignatureCharges(self) -> int:
        return self.__signatureCharges
    def getUltimateCharges(self) -> int:
        return self.__ultimateCharges
    def getUltimatePoints(self) -> int:
        return self.__ultimatePoints
    def getSignatureCooldown(self) -> float:
        return self.__signatureCooldown
    def getSignatureKills(self) -> int:
        return self.__signatureKills
    def getBuffs(self) -> list[tuple[Buff, float]]:
        return self.__buffs
    
class Stats:
    def __init__(self, kills: int, deaths: int, assists: int) -> None:
        self.__kills = kills
        self.__deaths = deaths
        self.__assists = assists
    
class DamageValues:
    def __init__(self, values1: tuple[int, int, int], range1: int, values2: Union[None, tuple[int, int, int]], range2: Union[None, int], values3: Union[None, tuple[int, int, int]], range3: Union[None, int]):
        self.__damageValues1 = values1
        self.__range1 = range1
        self.__damageValues2 = values2
        self.__range2 = range2
        self.__damageValues3 = values3
        self.__range3 = range3
    def getDamage(self, range: int) -> tuple[int, int, int]:
        if range <= self.__range1:
            return self.__damageValues1
        elif self.__range2 is not None and range <= self.__range2:
            return self.__damageValues2
        elif self.__range3 is not None and range <= self.__range3:
            return self.__damageValues3
        else:
            return self.__damageValues3 if self.__damageValues3 is not None else self.__damageValues2 if self.__damageValues2 is not None else self.__damageValues1


# PLAYER
class Holdable:
    def __init__(self, category: int) -> None:
        self.__category = category
    def getCategory(self) -> int:
        return self.__category
        
class Scope:
    def __init__(self, zoom: float, fireRateMultiplier: float, moveSpeedMultiplier: float, accuracy: float) -> None:
        self.__zoom = zoom
        self.__fireRateMultiplier = fireRateMultiplier
        self.__moveSpeedMultiplier = moveSpeedMultiplier
        self.__accuracy = accuracy
    def getZoom(self) -> float:
        return self.__zoom
    def getFireRateMultiplier(self) -> float:
        return self.__fireRateMultiplier
    def getMoveSpeedMultiplier(self) -> float: 
        return self.__moveSpeedMultiplier
    def getAccuracy(self) -> float:
        return self.__accuracy

class Knife(Holdable):
    def __init__(self, sprites: SpriteSet) -> None:
        super().__init__(category=1)
        self.__sprites = sprites
        self.__damage = DamageValues((50, 50, 50), 1, None, None, None, None)
        self.__altDamage = DamageValues((75, 75, 75), 1, None, None, None, None)
    
class Gun(Holdable):
    def __init__(self, name: str, sprites: SpriteSet, category: GunCategory, automatic: bool = False, penetration: PenetrationLevel = PenetrationLevel.MEDIUM, runSpeed: int = 5.4, equipSpeed: int = 0.75, reloadSpeed: int = 2, magazine: int = 1, fireRate: int = 2, firstShotSpread: tuple[int, int] = (0, 0), damage: DamageValues = DamageValues(), scope: Union[None, Scope] = None, altFireEffect: Union[None, Effect] = None) -> None:
        self.__name = name
        self.__sprites = sprites
        super().__init__(category=category)
        self.__automatic = automatic
        self.__penetration = penetration
        self.__runSpeed = runSpeed
        self.__equipSpeed = equipSpeed
        self.__reloadSpeed = reloadSpeed
        self.__magazine = magazine
        self.__fireRate = fireRate
        self.__firstShotSpread = firstShotSpread
        self.__damage = damage
        self.__scope = scope
        self.__altFireEffect = altFireEffect

class Ability(Holdable):
    def __init__(self, name: str, cost: int, abilityCategory: AbilityCategory, maxCharges: int, maxCooldown: Union[None, int] = None, maxKills: Union[None, int] = None, equippable: bool = False, effect: Any = None, description: str = "") -> None:
        self.__name = name
        self.__cost = cost
        super().__init__(category=0)
        self.__abilityCategory = abilityCategory
        self.__maxCharges = maxCharges
        self.__maxCooldown = maxCooldown
        self.__maxKills = maxKills
        self.__effect = effect
        self.__equippable = equippable
        self.__description = description
    # Getters
    def getName(self) -> str:
        return self.__name
    def getCost(self) -> int:
        return self.__cost
    def getAbilityCategory(self) -> AbilityCategory:
        return self.__AbilityCategory
    def getMaxCharges(self) -> int:
        return self.__maxCharges
    def getMaxCooldown(self) -> Union[None, int]:
        return self.__maxCooldown
    def getMaxKills(self) -> Union[None, int]:
        return self.__maxKills
    def getEquippable(self) -> bool:
        return self.__equippable
    def getEffect(self) -> Any:
        return self.__effect
    def getDescription(self) -> str:
        return self.__description

class Agent:
    def __init__(self, name: str, abilities: list[Ability, Ability, Ability, Ability], sprites: SpriteSet, description: str) -> None:
        self.__name = name
        self.__abilities = abilities
        self.__sprites = sprites
        self.__description = description

class Player:
    def __init__(self, pose: Pose, vitals: Vitals, status: Status, stats: Stats, agent: Agent) -> None:
        self.__pose = pose
        self.__vitals = vitals
        self.__status = status
        self.__stats = stats
        self.__agent = agent
    

# BACKEND
class GameState:
    def __init__(self):
        pass
    def __str__(self) -> str:
        return f"GameState[]"

class Input:
    def __init__(self, type: str):
        self.type = type
    def __str__(self) -> str:
        return f"Input[type={self.type}]"

class Action:
    def __init__(self, type: str, content: Any):
        self.type = type
        self.content = content
    def __str__(self) -> str:
        return f"Action[type={self.type}, content={self.content}]"

class Message:
    def __init__(self, head: str, body: Any):
        self.head = head
        self.body = body
    def __str__(self) -> str:
        return f"Message[head={self.head}, body={self.body}]"