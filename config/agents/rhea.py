"""Rhea (Initiator). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Rhea', role='Initiator', order=20,
    C=preset('wave', 'Tremor', price=250, max=1, start=0, length=12.0, width=3.0, damage=0, status='concuss', status_time=2.0),
    Q=preset('blast', 'Quarry', price=200, max=2, start=0, range=14.0, radius=3.0, delay=1.0, damage=30),
    E=preset('alarm', 'Tell', price=0, max=1, start=1, range=12.0, radius=6.0, duration=90.0, status='slow', status_time=2.0, recharge=45.0),
    X=preset('blast', 'Landslide', cost=8, range=40.0, radius=7.0, delay=2.0, damage=120, status='slow', status_time=3.0),
)
