"""Moraine (Controller). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Moraine', role='Controller', order=23,
    C=preset('zone', 'Scree', price=150, max=1, start=0, range=16.0, radius=3.0, duration=6.0, status='slow', status_time=0.5),
    Q=preset('smoke', 'Cairn', price=150, max=1, start=0, range=20.0, radius=3.0, duration=12.0),
    E=preset('smoke', 'Drift', price=0, max=2, start=2, range=40.0, radius=2.8, duration=14.0, remote=True, recharge=40.0),
    X=preset('wall', 'Glacier', cost=7, range=30.0, length=30.0, duration=15.0),
)
