"""Sloane (Controller). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Sloane', role='Controller', order=24,
    C=preset('smoke', 'Ash', price=100, max=2, start=0, range=10.0, radius=1.8, duration=8.0),
    Q=preset('teleport', 'Back Alley', price=250, max=1, start=0, range=10.0),
    E=preset('smoke', 'Fog Bank', price=0, max=2, start=2, range=35.0, radius=3.0, duration=14.0, remote=True, recharge=40.0),
    X=preset('zone', 'Long Night', cost=8, range=30.0, radius=10.0, duration=7.0, delay=1.0, status='nearsight', status_time=1.0),
)
