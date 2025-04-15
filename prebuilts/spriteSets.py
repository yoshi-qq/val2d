from classes.types import  SpriteSet, spriteSets as spriteSets_
from classes.keys import SpriteSetKey
from classes.graphicTypes import AgentSpriteSet

k = SpriteSetKey
spriteSets: dict[SpriteSetKey, SpriteSet] = {
    # k.AGENT_OMEN: AgentSpriteSet(name="Omen", logo="omen_logo", idle="omen_idle", walk="omen_walk", crouch="omen_crouch", jump="omen_jump", fall="omen_fall", land="omen_land", dead="omen_dead", reload="omen_reload", holdMelee="omen_holdMelee", holdSidearm="omen_holdSidearm", holdPrimary="omen_holdPrimary", holdBasic="omen_holdBasic", holdTactical="omen_holdTactical", holdSignature="omen_holdSignature", holdUltimate="omen_holdUltimate", castBasic="omen_castBasic", castTactical="omen_castTactical", castSignature="omen_castSignature", castUltimate="omen_castUltimate"),
    k.AGENT_OMEN: AgentSpriteSet(name="Omen", logo="omen_logo", idle="omen_idle", walk="omen_idle", crouch="omen_crouch", jump="omen_jump", fall="omen_fall", land="omen_land", dead="omen_dead", reload="omen_idle", holdMelee="omen_idle", holdSidearm="omen_idle", holdPrimary="omen_idle", holdBasic="omen_idle", holdTactical="omen_idle", holdSignature="omen_idle", holdUltimate="omen_idle", castBasic="omen_idle", castTactical="omen_idle", castSignature="omen_idle", castUltimate="omen_idle"),
}

def init() -> None:
    spriteSets_.update(spriteSets)