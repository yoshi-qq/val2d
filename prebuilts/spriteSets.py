from classes.types import SpriteSetKey, SpriteSet, spriteSets as spriteSets_

k = SpriteSetKey
spriteSets: dict[SpriteSetKey, SpriteSet] = {
    k.AGENT_OMEN: SpriteSet() # TODO 6
}

def init() -> None:
    spriteSets_.update(spriteSets)