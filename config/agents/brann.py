"""Brann (Duelist). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Brann', role='Duelist', order=11,
    C=preset('blast', 'Clinker', price=200, max=2, start=0, range=14.0, radius=2.2, delay=0.7, damage=45),
    Q=preset('hop', 'Bellows', price=150, max=1, start=0, velocity=6.0),
    E=preset('dash', 'Forge Step', price=0, max=1, start=1, distance=6.0, duration=0.2, recharge=25.0),
    X=preset('zone', 'Slag Field', cost=7, range=25.0, radius=5.0, duration=7.0, dps=20, status='slow', status_time=0.5),
)
