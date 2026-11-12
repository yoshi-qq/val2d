"""Tamsin (Initiator). Values: estimates by Claude Code, 11.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Tamsin', role='Initiator', order=5,
    C=preset('zone', 'Hush', price=200, max=1, start=0, range=20.0, radius=4.0, duration=6.0, delay=0.5, status='deaf', status_time=1.0, reveal=True),
    Q=preset('wave', 'Haze Line', price=250, max=1, start=0, length=22.0, width=2.0, damage=0, status='nearsight', status_time=3.5),
    E=preset('sensor', 'Dart', price=0, max=1, start=1, range=30.0, radius=8.0, duration=4.0, pulse=1.0, recharge=40.0),
    X=preset('wave', 'Shockline', cost=8, length=50.0, width=1.2, damage=80, status='vulnerable', status_time=6.0),
)
