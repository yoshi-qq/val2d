"""Mako (Duelist). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Mako', role='Duelist', order=15,
    C=preset('decoy', 'Chum', price=100, max=2, start=0, duration=4.0, speed=4.5),
    Q=preset('blast', 'Bite', price=250, max=1, start=0, range=10.0, radius=2.0, delay=0.4, damage=50, status='concuss', status_time=1.0),
    E=preset('stim', 'Hunt', price=0, max=1, start=1, radius=0.5, duration=6.0, recharge=40.0),
    X=preset('reveal_all', 'Bloodline', cost=8, duration=3.0),
)
