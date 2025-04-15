from typing import Callable
from classes.types import agents as agents_
from classes.keys import AgentKey, AbilitySlotKey, HandItemKey, AbilityKey as a, SpriteSetKey as s
from classes.agentTypes import Agent

A: Callable[[a, a, a, a], dict[AbilitySlotKey, a]] = lambda b, t, s, u: {HandItemKey.BASIC: b, HandItemKey.TACTICAL: t, HandItemKey.SIGNATURE: s, HandItemKey.ULTIMATE: u} 

k = AgentKey
agents: dict[AgentKey, Agent] = {
        k.OMEN: Agent(name="Omen", abilityKeys=A(a.FROM_THE_SHADOWS, a.PARANOIA, a.DARK_COVER, a.FROM_THE_SHADOWS), sprites=s.AGENT_OMEN, description="A phantom of a memory, Omen hunts in the shadows. He renders enemies blind, teleports across the field, then lets paranoia take hold as his foe scrambles to learn where he might strike next."),
}

def init() -> None:
    agents_.update(agents)