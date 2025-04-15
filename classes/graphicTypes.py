from typing import Union
from classes.types import Printable

class SpriteSet(Printable):
    def __init__(self, name: str) -> None:
        self.name = name

class AgentSpriteSet(SpriteSet, Printable):
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
