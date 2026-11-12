"""Harrow (Sentinel). Values: estimates by Claude Code, 11.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Harrow', role='Sentinel', order=9,
    C=preset('tripwire', 'Snare', price=200, max=2, start=0, length=6.0, duration=120.0, status='detain', status_time=2.0),
    Q=preset('alarm', 'Bell', price=200, max=1, start=0, range=10.0, radius=5.0, duration=120.0, status='concuss', status_time=2.0),
    E=preset('shield', 'Bulwark', price=0, max=1, start=1, points=40, range=12.0, recharge=45.0),
    X=preset('revive', 'Rally', cost=8, range=12.0),
)
