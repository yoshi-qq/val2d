from typing import Union, Any, Callable
from dependencies.communications import Message, Event, Request
from classes.keys import HandItemKey, MenuKey, MapKey, EffectKey, AbilityKey, MeleeKey, SidearmKey, GunKey, AgentKey, SpriteSetKey, GameModeKey, ObjectiveKey, InputKey
from classes.categories import AbilityCategory, GunCategory, PenetrationLevel
from config.constants import MAX_HP, MAX_OVERHEAL, MAX_SHIELD, MAX_REGEN_SHIELD, MAX_SPECIAL_BAR


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

# GRAPHICS
class SpriteSet:
    def __init__(self, name: str) -> None:
        self.name = name

class AgentSpriteSet(SpriteSet):
    def __init__(self, name: str, logo: str, idle: str, walk: str, crouch: str, jump: str, fall: str, land: str, dead: str, reload: str, holdMelee: str, holdSidearm: str, holdPrimary: str, holdBasic: Union[None, str], holdTactical: Union[None, str], holdSignature: Union[None, str], holdUltimate: Union[None, str], castBasic: Union[None, str], castTactical: Union[None, str], castSignature: Union[None, str], castUltimate: Union[None, str]) -> None:
        super().__init__(name)
        self.logo = logo
        self.idle = idle
        self.walk = walk #
        self.crouch = crouch
        self.jump = jump
        self.fall = fall
        self.land = land
        self.dead = dead
        self.reload = reload #
        self.holdMelee = holdMelee #
        self.holdSidearm = holdSidearm #
        self.holdPrimary = holdPrimary #
        self.holdBasic = holdBasic #
        self.holdTactical = holdTactical #
        self.holdSignature = holdSignature #
        self.holdUltimate = holdUltimate #
        self.castBasic = castBasic #
        self.castTactical = castTactical #
        self.castSignature = castSignature #
        self.castUltimate = castUltimate #

# EFFECTS
class Effect:
    def __init__(self, effectFunc: Callable) -> None:
        self.__effectFunc = effectFunc
    def activate(self, *args) -> None:
        self.__effectFunc(*args)

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
    def __init__(self, team: int = 0, handItem: HandItemKey = HandItemKey.SIDEARM, basicCharges: int = 0, tacticalCharges: int = 0, signatureCharges: int = 1,  ultimateCharges: int = 0, ultimatePoints: int = 0, signatureCooldown: float = 45, signatureKills: int = 0) -> None:
        # Ability
        self.__team = team
        self.__handItem: HandItemKey = handItem
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
    def getHandItemKey(self) -> HandItemKey:
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
    def __init__(self, name: str, objective: ObjectiveKey = ObjectiveKey.SPIKE, winThreshold: int = 13, roundTime: int = 100, overTime: bool = False) -> None:
        self.__name = name
        self.__objective = objective
        self.__winThreshold = winThreshold
        self.__roundTime = roundTime
        self.__overTime = overTime
    def getName(self) -> str:
        return self.__name
    def getObjectiveKey(self) -> ObjectiveKey:
        return self.__objective
    def getWinThreshold(self) -> int:
        return self.__winThreshold
    def getRoundTime(self) -> int:
        return self.__roundTime
    def getOverTime(self) -> bool:
        return self.__overTime

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
    def __init__(self, name: str, sprites: SpriteSetKey, category: GunCategory, automatic: bool = False, penetration: PenetrationLevel = PenetrationLevel.MEDIUM, runSpeed: int = 5.4, equipSpeed: int = 0.75, reloadSpeed: int = 2, magazine: int = 1, reserveAmmo: int = 3, fireRate: int = 2, firstShotSpread: tuple[int, int] = (0, 0), damage: DamageValues = DamageValues(values1=(1,1,1), range1=50), scope: Union[None, Scope] = None, silenced: bool = False, altFireEffect: Union[None, EffectKey] = None) -> None:
        self.__name = name
        self.__sprites = sprites
        super().__init__(category=category)
        self.__automatic = automatic
        self.__penetration = penetration
        self.__runSpeed = runSpeed
        self.__equipSpeed = equipSpeed
        self.__reloadSpeed = reloadSpeed
        self.__magazine = magazine
        self.__reserveAmmo = reserveAmmo
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
            "reserveAmmo": self.__reserveAmmo,
            "fireRate": self.__fireRate,
            "firstShotSpread": self.__firstShotSpread,
            "damage": self.__damage.collapseToDict(),
            "scope": self.__scope.collapseToDict() if self.__scope is not None else None,
            "silenced": self.__silenced,
            "altFireEffect": self.__altFireEffect.collapseToDict() if self.__altFireEffect is not None else None
        }
    
class Ability(Holdable):
    def __init__(self, name: str, sprites: SpriteSetKey, cost: int, abilityCategory: AbilityCategory, maxCharges: int, maxCooldown: Union[None, int] = None, maxKills: Union[None, int] = None, equippable: bool = False, heldUpdateEffect: Effect = None, castEffect: Effect = None, description: str = "") -> None:
        self.__name = name
        self.__sprites = sprites
        self.__cost = cost
        super().__init__(category=0)
        self.__abilityCategory = abilityCategory
        self.__maxCharges = maxCharges
        self.__maxCooldown = maxCooldown
        self.__maxKills = maxKills
        self.__heldUpdateEffect = heldUpdateEffect
        self.__castEffect = castEffect
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
        pass # TODO L8

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
    def __init__(self, type: InputKey, held: bool = False) -> None:
        self.type = type
        self.held = held
    def __str__(self) -> str:
        return f"Input[type={self.type}, {'held' if self.held else 'pressed'}]"

class Message:
    def __init__(self, head: str, body: Any):
        self.head = head
        self.body = body
    def __eq__(self, other: "Message") -> bool:
        return self.head == other.head and self.body == other.body
    def __str__(self) -> str:
        return f"Message[head={self.head}, body={self.body}]"
