"""Garrick (Sentinel). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Garrick', role='Sentinel', order=26,
    C=preset('shield', 'Plate', price=200, max=1, start=0, points=40, range=10.0),
    Q=preset('tripwire', 'Bell Line', price=200, max=2, start=0, length=6.0, duration=120.0, status='detain', status_time=1.5),
    E=preset('sensor', 'Watch', price=0, max=1, start=1, range=10.0, radius=8.0, duration=25.0, pulse=2.0, recharge=45.0),
    X=preset('stim', 'Bastion', cost=7, radius=10.0, duration=10.0),
)
