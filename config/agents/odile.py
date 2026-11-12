"""Odile (Initiator). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Odile', role='Initiator', order=17,
    C=preset('wave', 'Pirouette', price=200, max=1, start=0, length=14.0, width=2.5, damage=0, status='nearsight', status_time=2.5),
    Q=preset('teleport', 'Pas', price=200, max=1, start=0, range=5.0),
    E=preset('shield', 'Grace', price=0, max=1, start=1, points=30, range=12.0, recharge=40.0),
    X=preset('zone', 'Swan Song', cost=7, range=30.0, radius=7.0, duration=6.0, delay=0.5, status='vulnerable', status_time=1.0, reveal=True),
)
