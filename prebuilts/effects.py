from classes.types import Effect, effects as effects_
from classes.keys import EffectKey

# TODO L6: add real effects
l = lambda: None
k = EffectKey
effects: dict[EffectKey, Effect] = {
        k.SHROUDED_STEP_CAST: Effect(l),
        k.PARANOIA_CAST: Effect(l),
        k.DARK_COVER_CAST: Effect(l),
        k.FROM_THE_SHADOWS_CAST: Effect(l)
}

def init() -> None:
    effects_.update(effects)