from classes.types import EffectKey, AbilityKey, Ability, SpriteSetKey, abilities as abilities_
from classes.categories import AbilityCategory as Cat

k = AbilityKey
abilities: dict[AbilityKey, Ability] = {
        k.SHROUDED_STEP: Ability(
            name="Shrouded Step", 
            sprites=SpriteSetKey.ABILITY_SHROUDED_STEP, 
            cost=100, 
            abilityCategory=Cat.BASIC, 
            maxCharges=2,
            maxCooldown=None, 
            maxKills=None, 
            equippable=True,
            heldUpdateEffectKey=None,  
            castEffectKey=EffectKey.SHROUDED_STEP_CAST, 
            description="EQUIP a shrouded step ability and see its range indicator. FIRE to begin a brief channel, then teleport to the marked location."),
        k.PARANOIA: Ability(
            name="Paranoia", 
            sprites=SpriteSetKey.ABILITY_PARANOIA, 
            cost=250, 
            abilityCategory=Cat.TACTICAL,  
            maxCharges=1,
            maxCooldown=None, 
            maxKills=None, 
            equippable=True, 
            heldUpdateEffectKey=None,  
            castEffectKey=EffectKey.PARANOIA_CAST, 
            description="EQUIP a blinding orb. FIRE to throw it forward, briefly Nearsighting and Deafening all players it touches. This projectile can pass straight through walls."),
        k.DARK_COVER: Ability(
            name="Dark Cover", 
            cost=150, 
            sprites=SpriteSetKey.ABILITY_DARK_COVER, 
            abilityCategory=Cat.SIGNATURE,  
            maxCharges=2,
            maxCooldown=30, 
            maxKills=None, 
            equippable=True, 
            heldUpdateEffectKey=None,  
            castEffectKey=EffectKey.DARK_COVER_CAST, 
            description="EQUIP a shadow orb, entering a phased world to place and target the orbs. PRESS the ability key to throw the shadow orb to the marked location, creating a long-lasting shadow sphere that blocks vision. HOLD FIRE while targeting to move the marker further away. HOLD ALT FIRE while targeting to move the marker closer. PRESS RELOAD to toggle normal targeting view."),
        k.FROM_THE_SHADOWS: Ability(
            name="From the Shadows", 
            sprites=SpriteSetKey.ABILITY_FROM_THE_SHADOWS, 
            cost=7, 
            abilityCategory=Cat.ULTIMATE,  
            maxCharges=1,
            maxCooldown=None, 
            maxKills=None, 
            equippable=True, 
            heldUpdateEffectKey=None,  
            castEffectKey=EffectKey.FROM_THE_SHADOWS_CAST, 
            description="EQUIP a tactical map. FIRE to begin teleporting to the selected location. While teleporting, Omen will appear as a Shade that can be destroyed by an enemy to cancel his teleport, or PRESS EQUIP for Omen to cancel his teleport.")
}

def init() -> None:
    abilities_.update(abilities)