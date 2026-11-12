"""Marrow (Controller). Values: estimates by Claude Code, 11.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Marrow', role='Controller', order=2,
    C=preset('sensor', 'Listener', price=200, max=1, start=0, range=12.0, radius=10.0, duration=30.0, pulse=2.0),
    Q=preset('wall', 'Veil', price=300, max=1, start=0, range=25.0, length=10.0, duration=10.0),
    E=preset('smoke', 'Haze', price=0, max=2, start=2, range=30.0, radius=2.8, duration=15.0, recharge=35.0),
    X=preset('zone', 'Binding', cost=8, range=30.0, radius=7.0, duration=8.0, status='slow', status_time=0.5, reveal=True),
)
