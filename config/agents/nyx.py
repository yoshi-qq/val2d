"""Nyx (Controller). Values: estimates by Claude Code, 11.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Nyx', role='Controller', order=8,
    C=preset('blast', 'Static', price=200, max=1, start=0, range=14.0, radius=4.0, delay=0.8, damage=0, status='deaf', status_time=4.0),
    Q=preset('smoke', 'Shade', price=150, max=2, start=0, range=20.0, radius=2.6, duration=12.0),
    E=preset('wall', 'Curtain', price=0, max=1, start=1, range=20.0, length=12.0, duration=12.0, cross_status='nearsight', cross_time=2.0, recharge=45.0),
    X=preset('smoke', 'Eclipse', cost=7, range=30.0, radius=8.0, duration=10.0),
)
