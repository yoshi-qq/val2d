from typing import Union
from config.constants import DEFAULT_ABILITY_SPEED
from classes.types import Printable, JSONType, BaseHoldable, spriteSets
from classes.keys import SpriteSetKey, EffectKey, AbilitySlotKey, AbilityKey, AgentSpriteSetKey
from classes.categories import AbilityCategory
from classes.graphicTypes import AgentSpriteSet

class Ability(BaseHoldable, Printable):
    def __init__(self, name: str, sprites: SpriteSetKey, cost: int, abilityCategory: AbilityCategory, maxCharges: int, maxCooldown: Union[None, int] = None, maxKills: Union[None, int] = None, equippable: bool = False, heldUpdateEffectKey: Union[None, EffectKey] = None, castEffectKey: Union[None, EffectKey] = None, description: str = "", runSpeed: float = DEFAULT_ABILITY_SPEED) -> None:
        self.__name = name
        self.__sprites = sprites
        self.__cost = cost
        super().__init__(category=abilityCategory)
        self.__abilityCategory = abilityCategory
        self.__maxCharges = maxCharges
        self.__maxCooldown = maxCooldown
        self.__maxKills = maxKills
        self.__heldUpdateEffectKey = heldUpdateEffectKey
        self.__castEffectKey = castEffectKey
        self.__equippable = equippable
        self.__description = description
        self.__runSpeed = runSpeed
    # Getters
    def getName(self) -> str:
        return self.__name
    def getCost(self) -> int:
        return self.__cost
    def getAbilityCategory(self) -> AbilityCategory:
        return self.__abilityCategory
    def getMaxCharges(self) -> int:
        return self.__maxCharges
    def getMaxCooldown(self) -> Union[None, int]:
        return self.__maxCooldown
    def getMaxKills(self) -> Union[None, int]:
        return self.__maxKills
    def getEquippable(self) -> bool:
        return self.__equippable
    def getCastEffectKey(self) -> Union[None, EffectKey]:
        return self.__castEffectKey
    def getDescription(self) -> str:
        return self.__description
    def getMovementSpeed(self) -> float:
        return self.__runSpeed
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
            "effectKey": self.__castEffectKey,
            "description": self.__description
        }


class Agent(Printable):
    def __init__(self, name: str, abilityKeys: dict[AbilitySlotKey, AbilityKey], sprites: AgentSpriteSetKey, description: str) -> None:
        self.__name = name
        self.__abilityKeys = abilityKeys
        self.__sprites = sprites
        self.__description = description
    def getSpriteSet(self) -> AgentSpriteSet:
        return spriteSets[self.__sprites] # type: ignore TODO 3
    def getAbilityKey(self, slotKey: AbilitySlotKey) -> AbilityKey:
        return self.__abilityKeys[slotKey]
    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "name": self.__name,
            "abilityKeys": [abilityKey for abilityKey in self.__abilityKeys],
            "description": self.__description
        }
