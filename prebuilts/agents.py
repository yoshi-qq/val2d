from classes.types import Agent, agents as agents_
from prebuilts.abilities import abilities as a
from prebuilts.spriteSets import spriteSets as s

# TODO 9: description

class Agents:
    def __init__(self) -> None:
        self.omen = Agent(name="Omen", abilities=[a.shroudedSteps, a.paranoia, a.darkCover, a.fromTheShadows], sprites=s.omen)

agents = Agents()

def init() -> None:
    agents_.update(agents)