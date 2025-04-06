from types import SimpleNamespace
from classes.types import DictLike, Effect

# TODO 8: add real effects

class Effects:
    def __init__(self) -> None:
        self.ShroudedStepTeleport = Effect()
        self.paranoiaShoot = Effect()
        self.darkCoverPlace = Effect()
        self.fromTheShadowsTeleport = Effect()

effects = Effects()
