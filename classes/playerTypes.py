from typing import Union
from config.constants import DEFAULT_SPEED, debug, D, WALK_SPEED_MOD, CROUCH_SPEED_MOD, AIRBORNE_SPEED_MOD, DEFAULT_DECELERATION
from classes.types import Printable, JSONType, Position, Pose, agents, abilities
from classes.keys import EffectKey, HandItemKey, BuffKey, AgentKey, AbilityKey
from classes.inventoryTypes import Inventory
from classes.finalTypes import Holdable

class Vitals(Printable):
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

class Buff(Printable):
    def __init__(self, name: str, effectKey: EffectKey) -> None:
        self.__name = name
        self.__effectKey = effectKey
    def getName(self) -> str:
        return self.__name
    def getEffectKey(self) -> EffectKey:
        return self.__effectKey
    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "name": self.__name,
            "effectKey": self.__effectKey
        }

class Status(Printable):
    def __init__(self, alive: bool = True, grounded: bool = True, velocity: Position | None = None, acceleration: Position | None = None, walking: bool = False, crouched: bool = False, team: int = 0, handItem: HandItemKey = HandItemKey.SIDEARM, basicCharges: int = 0, tacticalCharges: int = 0, signatureCharges: int = 1,  ultimateCharges: int = 0, ultimatePoints: int = 0, signatureCooldown: float = 45, signatureKills: int = 0) -> None:
        self.__parent: Player | None = None
        self.__alive = alive
        self.__grounded = grounded
        # self.__jerk: Position = jerk if jerk else Position()
        self.__velocity: Position = velocity if velocity else Position()
        self.__acceleration: Position = acceleration if acceleration else Position()
        self.__walking = walking
        self.__crouched = crouched
        self.__team = team
        self.__handItem: HandItemKey = handItem
        self.__basicCharges = basicCharges
        self.__tacticalCharges = tacticalCharges
        self.__signatureCharges = signatureCharges
        self.__ultimateCharges = ultimateCharges
        self.__ultimatePoints = ultimatePoints
        self.__signatureCooldown = signatureCooldown
        self.__signatureKills = signatureKills

        self.__buffs: list[tuple[BuffKey, float]] = []

    # Getters
    def isAlive(self) -> bool:
        return self.__alive
    def isGrounded(self) -> bool:
        return self.__grounded
    def getVelocity(self) -> Position:
        return self.__velocity
    def isWalking(self) -> bool:
        return self.__walking
    def isCrouched(self) -> bool:
        return self.__crouched
    def isHorizontallyMoving(self) -> bool:
        return self.__velocity.getX() != 0 or self.__velocity.getZ() != 0
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
    def getBuffs(self) -> list[tuple[BuffKey, float]]:
        return self.__buffs
    def getSpeedMod(self) -> float:
        speedMod: float = 1.0
        # TODO: Implement Buffs
        if self.__crouched:
            speedMod *= CROUCH_SPEED_MOD
        elif self.__walking:
            speedMod *= WALK_SPEED_MOD
        if not self.__grounded:
            speedMod *= AIRBORNE_SPEED_MOD
        return speedMod
    # Setters
    def setParent(self, parent: "Player") -> None:
        self.__parent = parent
    def setAcceleration(self, acceleration: Position) -> None:
        self.__acceleration = acceleration
    # Ticking
    def applyAcceleration(self, passedTime: float, maxSpeed: float) -> None:
        if self.__acceleration.getHorizontalMagnitude() != 0:
            self.__velocity.move(self.__acceleration * passedTime) # TODO: change to better time measurement
        else:
            horizontalVel = self.__velocity.getHorizontalPart()
            speed = horizontalVel.getMagnitude()
            if speed < DEFAULT_DECELERATION * passedTime:
                self.__velocity = Position(0, 0, 0)
            else:
                self.__velocity.move(horizontalVel.getDirectionUnit() * -DEFAULT_DECELERATION * passedTime)
        self.__velocity.cap(maxSpeed)
        
    def applySpeed(self, passedTime: float) -> None:
        # TODO: Collision boundaries
        if self.__parent:
            self.__parent.getPose().move(self.__velocity*passedTime)
    
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
            "buffs": [(buffKey, duration) for buffKey, duration in self.__buffs]
        }

class Stats(Printable):
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


class Player(Printable):
    def __init__(self, name: str, pose: Pose | None = None, vitals: Vitals | None = None, status: Status | None = None, inventory: Inventory | None = None, stats: Stats | None = None, agentKey: Union[AgentKey, None] = None) -> None:
        self.__name = name
        self.__pose = pose if pose else Pose()
        self.__vitals = vitals if vitals else Vitals()
        self.__status = status if status else Status()
        self.__status.setParent(self)
        self.__inventory = inventory if inventory else Inventory()
        self.__stats = stats if stats else Stats()
        self.__agentKey = agentKey

    def getAgentKey(self) -> Union[None, AgentKey]:
        return self.__agentKey
    def getHandItem(self) -> Holdable | None:
        handItemKey = self.__status.getHandItemKey()
        if handItemKey in (HandItemKey.MELEE, HandItemKey.SIDEARM, HandItemKey.PRIMARY):
            return self.__inventory.getItemByKey(handItemKey)
        if self.__agentKey is None:
            return None
        abilityKey: AbilityKey = agents[self.__agentKey].getAbilityKey(handItemKey)
        return abilities[abilityKey]
        
    def getBaseSpeed(self) -> float:
        handItem = self.getHandItem()
        if handItem is None:
            debug(D.ERROR, "Couldn't get Base Speed, falling back to DEFAULT_SPEED", f"HandItem is None (Name: {self.__name})")
            return DEFAULT_SPEED
        else:
            return handItem.getMovementSpeed()
    
    def setAgent(self, agentKey: AgentKey) -> None:
        self.__agentKey = agentKey
    # def setJerk(self, jerk: Position) -> None:
    #     self.__status.setJerk(jerk)
    def setAcceleration(self, acceleration: Position) -> None:
        self.__status.setAcceleration(acceleration)
    
    def getName(self) -> str:
        return self.__name
    def getPose(self) -> Pose:
        return self.__pose
    def getStatus(self) -> Status:
        return self.__status
    def getInventory(self) -> Inventory:
        return self.__inventory
    def getMaxSpeed(self) -> float:
        baseSpeed: float = self.getBaseSpeed()
        speedMod: float = self.getStatus().getSpeedMod()
        return baseSpeed * speedMod
    
    def tickMovement(self, passedTime: float) -> None:
        # self.__status.applyJerk(passedTime, DEFAULT_MAX_ACCELERATION)
        self.__status.applyAcceleration(passedTime, self.getMaxSpeed())
        self.__status.applySpeed(passedTime)
    
    def collapseToDict(self) -> JSONType:
        return {
            "pose": self.__pose.collapseToDict(),
            "vitals": self.__vitals.collapseToDict(),
            "status": self.__status.collapseToDict(),
            "inventory": self.__inventory.collapseToDict(),
            "stats": self.__stats.collapseToDict(),
            "agentKey": self.__agentKey
        }
