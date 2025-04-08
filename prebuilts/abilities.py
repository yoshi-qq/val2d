from classes.types import Ability, AbilityCategory as Cat
from prebuilts.effects import effects
# TODO 9: descriptions

class Abilities:
    def __init__(self) -> None:
        # Omen
        self.shroudedStep = Ability(
            name="Shrouded Step", 
            cost=100, 
            category=Cat.BASIC, 
            maxCharges=2,
            maxCooldown=None, 
            maxKills=None, 
            equippable=True, 
            effect=effects.ShroudedStepTeleport)
        self.paranoia = Ability(
            name="Paranoia", 
            cost=250, 
            category=Cat.TACTICAL,  
            maxCharges=1,
            maxCooldown=None, 
            maxKills=None, 
            equippable=True, 
            effect=effects.paranoiaShoot)
        self.darkCover = Ability(
            name="Dark Cover", 
            cost=150, 
            category=Cat.SIGNATURE,  
            maxCharges=2,
            maxCooldown=30, 
            maxKills=None, 
            equippable=True, 
            effect=effects.darkCoverPlace)
        self.fromTheShadows = Ability(
            name="From the Shadows", 
            cost=7, 
            category=Cat.ULTIMATE,  
            maxCharges=1,
            maxCooldown=None, 
            maxKills=None, 
            equippable=True, 
            effect=effects.fromTheShadowsTeleport)

abilities = Abilities()