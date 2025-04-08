from classes.types import AbilityKey as a, SpriteSetKey as s, AgentKey, Agent, agents as agents_

# TODO 9: description

k = AgentKey
agents: dict[AgentKey, Agent] = {
        12: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        13: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        14: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        15: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        16: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        17: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        18: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        19: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        k.OMEN: Agent(name="Omen", abilityKeys=[a.FROM_THE_SHADOWS, a.PARANOIA, a.DARK_COVER, a.FROM_THE_SHADOWS], sprites=s.AGENT_OMEN, description=""),
        20: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        21: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        22: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        23: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        24: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        25: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        26: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        27: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        28: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        29: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        30: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        31: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        32: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        33: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
        34: Agent(name="Test", abilityKeys=[0, 1, 2, 3], sprites=0, description=""),
}

def init() -> None:
    agents_.update(agents)