from typing import Union, Literal
from config.constants import DEFAULT_KNIFE_SPEED
from classes.types import Printable, JSONType, melees, sidearms, guns, BaseHoldable
from classes.keys import SpriteSetKey, EffectKey, MeleeKey, SidearmKey, GunKey, HandItemKey
from classes.categories import MeleeCategory, GunCategory, PenetrationLevel

class DamageValues(Printable):
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
        elif self.__range2 and self.__damageValues2 and range <= self.__range2:
            return self.__damageValues2
        elif self.__range3 and self.__damageValues3 and range <= self.__range3:
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

# INVENTORY

class Scope(Printable):
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

    def collapseToDict(self) -> JSONType:
        return {
            "zoom": self.__zoom,
            "fireRateMultiplier": self.__fireRateMultiplier,
            "moveSpeedMultiplier": self.__moveSpeedMultiplier,
            "accuracy": self.__accuracy
        }

class Melee(BaseHoldable, Printable):
    def __init__(self, name: str, sprites: SpriteSetKey) -> None:
        self.__name = name
        super().__init__(category=MeleeCategory.MELEE)
        self.__sprites = sprites
        self.__runSpeed = DEFAULT_KNIFE_SPEED
        self.__damage = DamageValues((50, 50, 50), 1, None, None, None, None)
        self.__altDamage = DamageValues((75, 75, 75), 1, None, None, None, None)
    def getMovementSpeed(self) -> float:
        return self.__runSpeed
    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "damage": self.__damage.collapseToDict(),
            "altDamage": self.__altDamage.collapseToDict()
        }

class Gun(BaseHoldable, Printable):
    def __init__(self, name: str, sprites: SpriteSetKey, category: GunCategory, automatic: bool = False, penetration: PenetrationLevel = PenetrationLevel.MEDIUM, runSpeed: float = 5.4, equipSpeed: float = 0.75, reloadSpeed: float = 2, magazine: int = 1, reserveAmmo: int = 3, fireRate: float = 2, firstShotSpread: tuple[float, float] = (0, 0), damage: DamageValues = DamageValues(values1=(1,1,1), range1=50), scope: Union[None, Scope] = None, silenced: bool = False, altFireEffectKey: Union[None, EffectKey] = None) -> None:
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
        self.__altFireEffectKey = altFireEffectKey
    def getMovementSpeed(self) -> float:
        return self.__runSpeed
    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "name": self.__name,
            "category": self._category,
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
            "altFireEffectKey": self.__altFireEffectKey
        }

class Inventory(Printable):
    def __init__(self, meleeKey: MeleeKey = MeleeKey.DEFAULT, sidearmKey: Union[SidearmKey, None] = SidearmKey.CLASSIC, primaryKey: Union[GunKey, None] = None):
        self.__meleeKey = meleeKey
        self.__sidearmKey = sidearmKey
        self.__primaryKey = primaryKey
    def getMeleeKey(self) -> MeleeKey:
        return self.__meleeKey
    def getSidearmKey(self) -> Union[None, SidearmKey]:
        return self.__sidearmKey
    def getPrimaryKey(self) -> Union[None, GunKey]:
        return self.__primaryKey
    def getItemByKey(self, handItemKey: Literal[HandItemKey.MELEE, HandItemKey.SIDEARM, HandItemKey.PRIMARY]) -> Union[None, Union[Melee, Gun]]:
        match handItemKey:
            case HandItemKey.MELEE:
                return melees[self.__meleeKey]
            case HandItemKey.SIDEARM:
                if self.__sidearmKey is None:
                    return None
                return sidearms[self.__sidearmKey]
            case HandItemKey.PRIMARY:
                if self.__primaryKey is None:
                    return None
                return guns[self.__primaryKey]
    # JSON
    def collapseToDict(self) -> JSONType:
        return {
            "meleeKey": self.__meleeKey,
            "sidearmKey": self.__sidearmKey,
            "primaryKey": self.__primaryKey
        }
