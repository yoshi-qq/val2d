from classes.types import EffectKey, AbilityKey, Ability, SpriteSetKey, AbilityCategory as Cat, abilities as abilities_
# TODO 9: descriptions

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
            effect=EffectKey.SHROUDED_STEP_CAST),
        k.PARANOIA: Ability(
            name="Paranoia", 
            sprites=SpriteSetKey.ABILITY_PARANOIA, 
            cost=250, 
            abilityCategory=Cat.TACTICAL,  
            maxCharges=1,
            maxCooldown=None, 
            maxKills=None, 
            equippable=True, 
            effect=EffectKey.PARANOIA_CAST),
        k.DARK_COVER: Ability(
            name="Dark Cover", 
            cost=150, 
            sprites=SpriteSetKey.ABILITY_DARK_COVER, 
            abilityCategory=Cat.SIGNATURE,  
            maxCharges=2,
            maxCooldown=30, 
            maxKills=None, 
            equippable=True, 
            effect=EffectKey.DARK_COVER_CAST),
        k.FROM_THE_SHADOWS: Ability(
            name="From the Shadows", 
            sprites=SpriteSetKey.ABILITY_FROM_THE_SHADOWS, 
            cost=7, 
            abilityCategory=Cat.ULTIMATE,  
            maxCharges=1,
            maxCooldown=None, 
            maxKills=None, 
            equippable=True, 
            effect=EffectKey.FROM_THE_SHADOWS_CAST)
}

def init() -> None:
    abilities_.update(abilities)