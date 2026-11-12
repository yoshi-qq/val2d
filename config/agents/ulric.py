"""Ulric (Sentinel). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Ulric', role='Sentinel', order=30,
    C=preset('zone', 'Howl', price=150, max=1, start=0, range=14.0, radius=4.0, duration=4.0, status='deaf', status_time=1.0, reveal=True),
    Q=preset('tripwire', 'Jaw Trap', price=200, max=2, start=0, length=4.0, duration=120.0, status='concuss', status_time=2.0),
    E=preset('alarm', 'Den', price=0, max=1, start=1, range=10.0, radius=6.0, duration=120.0, status='vulnerable', status_time=3.0, recharge=45.0),
    X=preset('immunity', 'Pack', cost=7, duration=9.0, regen=8.0),
)
