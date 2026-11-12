"""Sable (Sentinel). Values: estimates by Claude Code, 11.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Sable', role='Sentinel', order=10,
    C=preset('anchor', 'Waypoint', price=150, max=1, start=0, duration=60.0),
    Q=preset('zone', 'Caltrops', price=200, max=1, start=0, range=10.0, radius=2.5, duration=30.0, dps=8, status='slow', status_time=1.0),
    E=preset('heal', 'Mend', price=0, max=1, start=1, amount=60, duration=4.0, range=12.0, recharge=40.0),
    X=preset('reveal_all', 'Watchtower', cost=7, duration=4.0),
)
