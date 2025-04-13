from classes.types import AbilityKey as a, SpriteSetKey as s, AgentKey, Agent, agents as agents_

# TODO 9: description

k = AgentKey
agents: dict[AgentKey, Agent] = {
        k.OMEN: Agent(name="Omen", abilityKeys=[a.FROM_THE_SHADOWS, a.PARANOIA, a.DARK_COVER, a.FROM_THE_SHADOWS], sprites=s.AGENT_OMEN, description=""),
}

def init() -> None:
    agents_.update(agents)