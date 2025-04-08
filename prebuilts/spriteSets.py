from classes.types import SpriteSetKey, SpriteSet, AgentSpriteSet, spriteSets as spriteSets_

k = SpriteSetKey
spriteSets: dict[SpriteSetKey, SpriteSet] = {
    k.AGENT_OMEN: AgentSpriteSet(logo="omen_logo"),
    0: AgentSpriteSet(logo="agent_logo"),
    # TODO 6
}

def init() -> None:
    spriteSets_.update(spriteSets)