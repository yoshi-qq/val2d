from types import SimpleNamespace, effects as effects_
from classes.types import DictLike, Effect

# TODO 6: add real effects

class Effects:
    def __init__(self) -> None:
        self.ShroudedStepTeleport = Effect()
        self.paranoiaShoot = Effect()
        self.darkCoverPlace = Effect()
        self.fromTheShadowsTeleport = Effect()

effects = Effects()

def init() -> None:
    effects_.update(effects)