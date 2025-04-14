from classes.types import AbilityKey as a, SpriteSetKey as s, AgentKey, Agent, agents as agents_

k = AgentKey
agents: dict[AgentKey, Agent] = {
        k.OMEN: Agent(name="Omen", abilityKeys=(a.FROM_THE_SHADOWS, a.PARANOIA, a.DARK_COVER, a.FROM_THE_SHADOWS), sprites=s.AGENT_OMEN, description="A phantom of a memory, Omen hunts in the shadows. He renders enemies blind, teleports across the field, then lets paranoia take hold as his foe scrambles to learn where he might strike next."),
}

def init() -> None:
    agents_.update(agents)