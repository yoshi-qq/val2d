"""Fen (Controller). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Fen', role='Controller', order=21,
    C=preset('zone', 'Bog', price=150, max=1, start=0, range=18.0, radius=3.0, duration=8.0, status='slow', status_time=0.5),
    Q=preset('wall', 'Reed Wall', price=250, max=1, start=0, range=20.0, length=10.0, duration=12.0, cross_status='slow', cross_time=2.0),
    E=preset('smoke', 'Mist', price=0, max=2, start=2, range=35.0, radius=2.8, duration=14.0, remote=True, recharge=40.0),
    X=preset('zone', 'Drown', cost=8, range=30.0, radius=8.0, duration=7.0, delay=0.5, status='decay', status_time=1.0),
)
