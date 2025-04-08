from classes.types import EffectKey, Effect, effects as effects_

# TODO 6: add real effects
k = EffectKey
effects: dict[EffectKey, Effect] = {
        k.SHROUDED_STEP_CAST: Effect(),
        k.PARANOIA_CAST: Effect(),
        k.DARK_COVER_CAST: Effect(),
        k.FROM_THE_SHADOWS_CAST: Effect()
}

def init() -> None:
    effects_.update(effects)