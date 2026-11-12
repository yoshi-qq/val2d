"""Okoro (Initiator). Values: estimates by Claude Code, 11.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Okoro', role='Initiator', order=6,
    C=preset('flash', 'Glare', price=250, max=2, start=0, range=14.0, fuse=0.35, blind=1.4, cone=140.0, through_walls=False),
    Q=preset('zone', 'Mark', price=200, max=1, start=0, range=20.0, radius=3.5, duration=5.0, delay=0.3, status='vulnerable', status_time=1.0, reveal=True),
    E=preset('blast', 'Rattle', price=0, max=1, start=1, range=16.0, radius=4.0, delay=0.8, damage=0, status='concuss', status_time=2.0, recharge=40.0),
    X=preset('blast', 'Barrage', cost=7, range=60.0, radius=7.0, delay=2.5, damage=150),
)
