"""Vesper (Duelist). Values: estimates by Claude Code, 11.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Vesper', role='Duelist', order=3,
    C=preset('decoy', 'Footfall', price=150, max=2, start=0, duration=4.0, speed=5.0),
    Q=preset('teleport', 'Slip', price=250, max=1, start=0, range=8.0),
    E=preset('blast', 'Jolt', price=0, max=1, start=1, range=14.0, radius=3.5, delay=1.0, damage=0, status='concuss', status_time=2.5, kills_to_recharge=2),
    X=preset('immunity', 'Second Wind', cost=7, duration=10.0, regen=6.0),
)
