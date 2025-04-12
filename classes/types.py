from typing import Union, Any
from dependencies.communications import Message, Event, Request
from config.constants import MAX_HP, MAX_OVERHEAL, MAX_SHIELD, MAX_REGEN_SHIELD, MAX_SPECIAL_BAR
from enum import Enum

# Empty prebuilts
abilities: dict["AbilityKey", "Ability"] = {}
agents: dict["AgentKey", "Agent"] = {}
effects: dict["EffectKey", "Effect"] = {}
melees: dict["MeleeKey", "Melee"] = {}
sidearms: dict["SidearmKey", "Gun"] = {}
guns: dict["GunKey", "Gun"] = {}
maps: dict["MapKey", "Map"] = {}
spriteSets: dict["SpriteSetKey", "SpriteSet"] = {}

# BASE
class NullType:
    def __repr__(self):
        return "null"
    def __bool__(self):
        return False

Null = NullType()
JSONType = Union[dict[str, Any], list[Any], str, int, float, bool, None]

# DEBUGGING
class AutoMessageTrigger:
    def __init__(self, trigger: Message | Event | Request, responseMessage: Message) -> None:
        self.trigger = trigger
        self.responseMessage = responseMessage

# MENUING
class MenuKey(Enum):
    EMPTY = "empty"
    PLAY = "play"
    HOST_LOBBY = "hostLobby"
    PLAYER_LOBBY = "playerLobby"
    AGENT_SELECT = "agentSelect"
    HOST_AGENT_SELECT = "hostAgentSelect"
    IN_GAME_PLAYER = "inGamePlayer"
    IN_GAME_HOST = "inGameHost"

# GRAPHICS
class SpriteSet:
    def __init__(self) -> None:
        pass # TODO 6

class AgentSpriteSet(SpriteSet):
    def __init__(self, logo: str) -> None:
        self.logo = logo
        # TODO 6

# KEYS
class MapKey(Enum):
    BIND = 1
    HAVEN = 2
    SPLIT = 3
    ASCENT = 4
    ICEBOX = 5
    BREEZE = 6
    FRACTURE = 7
    PEARL = 8
    LOTUS = 9
    SUNSET = 10
    ABYSS = 11

class EffectKey(Enum):
    # 01 Brimstone (1-10)
    # 02 Viper (11-20)
    # 03 Omen (21-30)
    SHROUDED_STEP_CAST = 21
    PARANOIA_CAST = 22
    DARK_COVER_CAST = 23
    FROM_THE_SHADOWS_CAST = 24
    # 04 Killjoy (31-40)
    # 05 Cypher (41-50)
    # 06 Sova (51-60)
    # 07 Sage (61-70)
    # 08 - (71-80)
    # 09 Phoenix (81-90)
    # 10 Jett (91-100)
    # 11 Reyna (101-110)
    # 12 Raze (111-120)
    # 13 Breach (121-130)
    # 14 Skye (131-140)
    # 15 Yoru (141-150)
    # 16 Astra (151-160)
    # 17 KAY/O (161-170)
    # 18 Chamber (171-180)
    # 19 Neon (181-190)
    # 20 Fade (191-200)
    # 21 Harbor (201-210)
    # 22 Gekko (211-220)
    # 23 Deadlock (221-230)
    # 24 Iso (231-240)
    # 25 Clove (241-250)
    # 26 Vyse (251-260)
    # 27 Tejo (261-270)
    # 28 Waylay (271-280)

class AbilityKey(Enum):
    # 01 Brimstone (1-4)
    # 02 Viper (5-8)
    # 03 Omen (9-12)
    SHROUDED_STEP = 9
    PARANOIA = 10
    DARK_COVER = 11
    FROM_THE_SHADOWS = 12
    # 04 Killjoy (13-16)
    # 05 Cypher (17-20)
    # 06 Sova (21-24)
    # 07 Sage (25-28)
    # 08 - (29-32)
    # 09 Phoenix (33-36)
    # 10 Jett (37-40)
    # 11 Reyna (41-44)
    # 12 Raze (45-48)
    # 13 Breach (49-52)
    # 14 Skye (53-56)
    # 15 Yoru (57-60)
    # 16 Astra (61-64)
    # 17 KAY/O (65-68)
    # 18 Chamber (69-72)
    # 19 Neon (73-76)
    # 20 Fade (77-80)
    # 21 Harbor (81-84)
    # 22 Gekko (85-88)
    # 23 Deadlock (89-92)
    # 24 Iso (93-96)
    # 25 Clove (97-100)
    # 26 Vyse (101-104)
    # 27 Tejo (105-108)
    # 28 Waylay (109-112)

class MeleeKey(Enum):
    DEFAULT = 0
class SidearmKey(Enum):
    CLASSIC = 1
    SHORTY = 2
    FRENZY = 3
    GHOST = 4
    SHERIFF = 5
    GOLDEN_GUN = 6
    SNOWBALL_LAUNCHER = 7
    # 8-10 unused
class GunKey(Enum):
    # SMGs
    STINGER = 11
    SPECTRE = 12
    # Shotguns
    BUCKY = 13
    JUDGE = 14
    # Rifles
    BULLDOG = 15
    GUARDIAN = 16
    PHANTOM = 17
    VANDAL = 18
    # Sniper Rifles
    MARSHAL = 19
    OUTLAW = 20
    OP = 21
    # Machine Guns
    ARES = 22
    ODIN = 23

class AgentKey(Enum):
    BRIMSTONE = 1
    VIPER = 2
    OMEN = 3
    KILLJOY = 4
    CYPHER = 5
    SOVA = 6
    SAGE = 7
    # -- = 8
    PHOENIX = 9
    JETT = 10
    REYNA = 11
    RAZE = 12
    BREACH = 13
    SKYE = 14
    YORU = 15
    ASTRA = 16
    KAYO = 17
    CHAMBER = 18
    NEON = 19
    FADE = 20
    HARBOR = 21
    GEKKO = 22
    DEADLOCK = 23
    ISO = 24
    CLOVE = 25
    VYSE = 26
    TEJO = 27
    WAYLAY = 28

class SpriteSetKey(Enum):
    # AGENTS
    AGENT_BRIMSTONE = 1
    AGENT_VIPER = 2
    AGENT_OMEN = 3
    AGENT_KILLJOY = 4
    AGENT_CYPHER = 5
    AGENT_SOVA = 6
    AGENT_SAGE = 7
    AGENT_PHOENIX = 9
    AGENT_JETT = 10
    AGENT_REYNA = 11
    AGENT_RAZE = 12
    AGENT_BREACH = 13
    AGENT_SKYE = 14
    AGENT_YORU = 15
    AGENT_ASTRA = 16
    AGENT_KAYO = 17
    AGENT_CHAMBER = 18
    AGENT_NEON = 19
    AGENT_FADE = 20
    AGENT_HARBOR = 21
    AGENT_GEKKO = 22
    AGENT_DEADLOCK = 23
    AGENT_ISO = 24
    AGENT_CLOVE = 25
    AGENT_VYSE = 26
    AGENT_TEJO = 27
    AGENT_WAYLAY = 28
    
    # WEAPONS
    # Melee
    WEAPON_MELEE = 51
    # Sidearms
    WEAPON_CLASSIC = 52
    WEAPON_SHORTY = 53
    WEAPON_FRENZY = 54
    WEAPON_GHOST = 55
    WEAPON_SHERIFF = 56
    WEAPON_GOLDEN_GUN = 57
    WEAPON_SNOWBALL_LAUNCHER = 58
    # Primaries
    WEAPON_STINGER = 61
    WEAPON_SPECTRE = 62
    WEAPON_BUCKY = 63
    WEAPON_JUDGE = 64
    WEAPON_BULLDOG = 65
    WEAPON_GUARDIAN = 66
    WEAPON_PHANTOM = 67
    WEAPON_VANDAL = 68
    WEAPON_MARSHAL = 69
    WEAPON_OUTLAW = 70
    WEAPON_OP = 71
    WEAPON_ARES = 72
    WEAPON_ODIN = 73
    
    # Abilities
    # 01 Brimstone (1-4)
    # 02 Viper (5-8)
    # 03 Omen (9-12)
    ABILITY_SHROUDED_STEP = 9
    ABILITY_PARANOIA = 10
    ABILITY_DARK_COVER = 11
    ABILITY_FROM_THE_SHADOWS = 12
    # 04 Killjoy (13-16)
    # 05 Cypher (17-20)
    # 06 Sova (21-24)
    # 07 Sage (25-28)
    # 08 - (29-32)
    # 09 Phoenix (33-36)
    # 10 Jett (37-40)
    # 11 Reyna (41-44)
    # 12 Raze (45-48)
    # 13 Breach (49-52)
    # 14 Skye (53-56)
    # 15 Yoru (57-60)
    # 16 Astra (61-64)
    # 17 KAY/O (65-68)
    # 18 Chamber (69-72)
    # 19 Neon (73-76)
    # 20 Fade (77-80)
    # 21 Harbor (81-84)
    # 22 Gekko (85-88)
    # 23 Deadlock (89-92)
    # 24 Iso (93-96)
    # 25 Clove (97-100)
    # 26 Vyse (101-104)
    # 27 Tejo (105-108)
    # 28 Waylay (109-112)
    
    # OBJECTS

class GameModeKey(Enum):
    UNRATED = 0
    COMPETITIVE = 1
    DEATHMATCH = 2
    ESCALATION = 3
    SPIKE_RUSH = 4
    SWIFT_PLAY = 5
    TEAM_DEATHMATCH = 6
    REPLICATION = 7
    CUSTOM = 8

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

# SIMPLES
class HandItem(Enum):
    MELEE = 0
    SIDEARM = 1
    PRIMARY = 2
    BASIC = 3
    TACTICAL = 4
    SIGNATURE = 5
    ULTIMATE = 6

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
    def collapseToDict(self) -> JSONType:
        return {
            "x": self.__x,
            "y": self.__y,
            "z": self.__z
        }
    
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
    def __init__(self, position: Position = Position(), orientation: Angle = Angle()) -> None:
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

    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "position": self.__position.collapseToDict(),
            "orientation": self.getOrientation().getAngle()  
        }
    
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
    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "hp": self.__hp,
            "overheal": self.__overheal,
            "shield": self.__shield,
            "regenShield": self.__regenShield,
            "specialBar": self.__specialBar
        }

class Buff:
    def __init__(self, name: str, effectKey: EffectKey) -> None:
        self.__name = name
        self.__effectKey = effectKey
    def getName(self) -> str:
        return self.__name
    def getEffect(self) -> Effect:
        return 
    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "name": self.__name,
            "effectKey": self.__effectKey
        }

class Status:
    def __init__(self, team: int = 0, handItem: HandItem = HandItem.SIDEARM, basicCharges: int = 0, tacticalCharges: int = 0, signatureCharges: int = 1,  ultimateCharges: int = 0, ultimatePoints: int = 0, signatureCooldown: float = 45, signatureKills: int = 0) -> None:
        # Ability
        self.__team = team
        self.__handItem: HandItem = handItem
        self.__basicCharges = basicCharges
        self.__tacticalCharges = tacticalCharges
        self.__signatureCharges = signatureCharges
        self.__ultimateCharges = ultimateCharges
        self.__ultimatePoints = ultimatePoints
        self.__signatureCooldown = signatureCooldown
        self.__signatureKills = signatureKills

        self.__buffs: list[tuple[Buff, float]] = []
    
    # Getters
    def getTeam(self) -> int:
        return self.__team
    def getHandItem(self) -> HandItem:
        return self.__handItem
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
    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "team": self.__team,
            "handItem": self.__handItem,
            "basicCharges": self.__basicCharges,
            "tacticalCharges": self.__tacticalCharges,
            "signatureCharges": self.__signatureCharges,
            "ultimateCharges": self.__ultimateCharges,
            "ultimatePoints": self.__ultimatePoints,
            "signatureCooldown": self.__signatureCooldown,
            "signatureKills": self.__signatureKills,
            "buffs": [(buff.collapseToDict(), duration) for buff, duration in self.__buffs]
        }
    
class Stats:
    def __init__(self, kills: int = 0, deaths: int = 0, assists: int = 0) -> None:
        self.__kills = kills
        self.__deaths = deaths
        self.__assists = assists
    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "kills": self.__kills,
            "deaths": self.__deaths,
            "assists": self.__assists
        }
    
class DamageValues:
    def __init__(self, values1: tuple[int, int, int], range1: int, values2: Union[None, tuple[int, int, int]] = None, range2: Union[None, int] = None, values3: Union[None, tuple[int, int, int]] = None, range3: Union[None, int] = None):
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
    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "values1": self.__damageValues1,
            "range1": self.__range1,
            "values2": self.__damageValues2,
            "range2": self.__range2,
            "values3": self.__damageValues3,
            "range3": self.__range3
        }

# OBJECTS
class Object:
    def __init__(self, id: int, sprite: SpriteSetKey, position: Position = Position, orientation: Angle = Angle):
        self.__id = id
        self.__sprite = sprite
        self.__position = position
        self.__orientation = orientation
    def getID(self) -> int:
        return self.__id
    def collapseToDict(self) -> JSONType:
        return {}

class Wall:
    def __init__(self, size: Position, penetrationLevel: int) -> None:
        self.size = size
        self.penepenetrationLevel = penetrationLevel
class Box:
    def __init__(self, size: Position, penetrationLevel: int) -> None:
        self.size = size
        self.penepenetrationLevel = penetrationLevel
class Cylinder:
    def __init__(self, size: Position, penetrationLevel: int) -> None:
        self.size = size
        self.penepenetrationLevel = penetrationLevel
class Stair:
    def __init__(self, size: Position) -> None:
        self.size = size
class Decoration:
    def __init__(self, size: Position) -> None:
        self.size = size
class BreakableDoor:
    def __init__(self, size: Position, HP: int) -> None:
        self.size = size
        self.HP = HP
class Switch:
    def __init__(self, doorID: int) -> None:
        self.doorID = doorID
class Bike:
    def __init__(self) -> None:
        pass
class UltOrb:
    def __init__(self) -> None:
        pass
class Zipline:
    def __init__(self, size: Position, direction: Position, force: bool = False) -> None:
        self.size = size
        self.direction = direction
        self.force = force
class Teleporter:
    def __init__(self, teleportPosition: Position) -> None:
        self.teleportPosition = teleportPosition
class TPDoor:
    def __init__(self) -> None:
        pass
class RotatingDoor:
    def __init__(self) -> None:
        pass
class CrouchDoor:
    def __init__(self) -> None:
        pass
class Abyss:
    def __init__(self, size: Position) -> None:
        self.size = size
 
# GAME
class GameMode:
    def __init__(self, name: str):
        self.__name = name
        pass # TODO 6

class Map:
    def __init__(self, name: str, objects: list[Object]) -> None:
        self.__objects = objects
    def collapseToDict(self) -> JSONType:
        return {}

# INVENTORY
class Holdable:
    def __init__(self, category: int) -> None:
        self.__category = category
    def getCategory(self) -> int:
        return self.__category
        
class Scope:
    def __init__(self, zoom: float, fireRateMultiplier: float, moveSpeedMultiplier: float, accuracy: float = 1.2) -> None:
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

class Melee(Holdable):
    def __init__(self, name: str, sprites: SpriteSetKey) -> None:
        self.__name = name
        super().__init__(category=1)
        self.__sprites = sprites
        self.__damage = DamageValues((50, 50, 50), 1, None, None, None, None)
        self.__altDamage = DamageValues((75, 75, 75), 1, None, None, None, None)
    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "damage": self.__damage.collapseToDict(),
            "altDamage": self.__altDamage.collapseToDict()
        }
    
class Gun(Holdable):
    def __init__(self, name: str, sprites: SpriteSetKey, category: GunCategory, automatic: bool = False, penetration: PenetrationLevel = PenetrationLevel.MEDIUM, runSpeed: int = 5.4, equipSpeed: int = 0.75, reloadSpeed: int = 2, magazine: int = 1, fireRate: int = 2, firstShotSpread: tuple[int, int] = (0, 0), damage: DamageValues = DamageValues(values1=(1,1,1), range1=50), scope: Union[None, Scope] = None, silenced: bool = False, altFireEffect: Union[None, Effect] = None) -> None:
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
        self.__silenced = silenced
        self.__altFireEffect = altFireEffect
    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "name": self.__name,
            "category": self.__category,
            "automatic": self.__automatic,
            "penetration": self.__penetration,
            "runSpeed": self.__runSpeed,
            "equipSpeed": self.__equipSpeed,
            "reloadSpeed": self.__reloadSpeed,
            "magazine": self.__magazine,
            "fireRate": self.__fireRate,
            "firstShotSpread": self.__firstShotSpread,
            "damage": self.__damage.collapseToDict(),
            "scope": self.__scope.collapseToDict() if self.__scope is not None else None,
            "altFireEffect": self.__altFireEffect.collapseToDict() if self.__altFireEffect is not None else None
        }
    
class Ability(Holdable):
    def __init__(self, name: str, sprites: SpriteSetKey, cost: int, abilityCategory: AbilityCategory, maxCharges: int, maxCooldown: Union[None, int] = None, maxKills: Union[None, int] = None, equippable: bool = False, effect: Effect = None, description: str = "") -> None:
        self.__name = name
        self.__sprites = sprites
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
    def getEffect(self) -> Effect:
        return self.__effect
    def getDescription(self) -> str:
        return self.__description
    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "name": self.__name,
            "cost": self.__cost,
            "abilityCategory": self.__abilityCategory,
            "maxCharges": self.__maxCharges,
            "maxCooldown": self.__maxCooldown,
            "maxKills": self.__maxKills,
            "equippable": self.__equippable,
            "effect": self.__effect.collapseToDict() if self.__effect is not None else None,
            "description": self.__description
        }
        
class Inventory:
    def __init__(self, meleeKey: MeleeKey = MeleeKey.DEFAULT, secondaryKey: Union[SidearmKey, None] = SidearmKey.CLASSIC, primaryKey: Union[GunKey, None] = None):
        self.__meleeKey = meleeKey
        self.__secondaryKey = secondaryKey
        self.__primaryKey = primaryKey
    def getMeleeKey(self) -> Melee:
        return self.__meleeKey
    def getSecondaryKey(self) -> Gun:
        return self.__secondaryKey
    def getPrimaryKey(self) -> Gun:   
        return self.__primaryKey
    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "meleeKey": self.__meleeKey,
            "secondaryKey": self.__secondaryKey,
            "primaryKey": self.__primaryKey
        }

# PLAYER
class Agent:
    def __init__(self, name: str, abilityKeys: list[AbilityKey, AbilityKey, AbilityKey, AbilityKey], sprites: SpriteSetKey, description: str) -> None:
        self.__name = name
        self.__abilityKeys = abilityKeys
        self.__sprites = sprites
        self.__description = description
    def getSpriteSet(self) -> SpriteSet:
        return spriteSets[self.__sprites]
    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "name": self.__name,
            "abilityKeys": [abilityKey for abilityKey in self.__abilityKeys],
            "description": self.__description
        }

class Player:
    def __init__(self, name: str, pose: Pose = Pose(), vitals: Vitals = Vitals(), status: Status = Status(), inventory: Inventory = Inventory(), stats: Stats = Stats(), agent: Union[AgentKey, None] = None) -> None:
        self.__name = name
        self.__pose = pose
        self.__vitals = vitals
        self.__status = status
        self.__inventory = inventory
        self.__stats = stats
        self.__agent = agent
        
    def getAgent(self) -> AgentKey:
        return self.__agent
    def setAgent(self, agentKey: AgentKey) -> None:
        self.__agent = agents[agentKey]
    
    def getName(self) -> str:
        return self.__name
    
    def collapseToDict(self) -> JSONType:
        return {
            "pose": self.__pose.collapseToDict(),
            "vitals": self.__vitals.collapseToDict(),
            "status": self.__status.collapseToDict(),
            "inventory": self.__inventory.collapseToDict(),
            "stats": self.__stats.collapseToDict(),
            "agent": self.__agent.collapseToDict()
        }

# BACKEND
class Connection:
    def __init__(self, name: str):
        self.__name = name
    def getName(self) -> str:
        return self.__name

class GameState:
    def __init__(self, players: list[Player], time: float, roundNo: int, score: tuple[int, int], mapKey: MapKey, gameMode: GameModeKey, roundTime: float, objects: list[Object]) -> None:
        self.players = players
        self.time = time
        self.round = roundNo
        self.score = score
        self.mapKey = mapKey
        self.gameMode = gameMode
        self.roundTime = roundTime
        self.objects = objects
    def cutForPlayer(self, playerId: int) -> "GameState":
        pass # TODO 9

    def collapseToDict(self) -> JSONType:
        return {
            "players": [player.collapseToDict() for player in self.players],
            "time": self.time,
            "round": self.round,
            "score": self.score,
            "mapKey": self.mapKey,
            "gameMode": self.gameMode,
            "roundTime": self.roundTime,
            "objects": [obj.collapseToDict() for obj in self.objects]
        }
    
    def __str__(self) -> str:
        return str(self.collapseToDict())

class Input:
    def __init__(self, type: str):
        self.type = type
    def __str__(self) -> str:
        return f"Input[type={self.type}]"

class Message:
    def __init__(self, head: str, body: Any):
        self.head = head
        self.body = body
    def __eq__(self, other: "Message") -> bool:
        return self.head == other.head and self.body == other.body
    def __str__(self) -> str:
        return f"Message[head={self.head}, body={self.body}]"
