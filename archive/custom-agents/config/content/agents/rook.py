"""Rook (Duelist). Values: estimates by Claude Code, 11.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Rook', role='Duelist', order=4,
    C=preset('blast', 'Tar', price=200, max=2, start=0, range=12.0, radius=3.0, delay=1.2, damage=15, status='slow', status_time=3.0),
    Q=preset('shield', 'Plating', price=200, max=1, start=0, points=30, range=10.0),
    E=preset('dash', 'Charge', price=0, max=1, start=1, distance=6.0, duration=0.25, recharge=30.0),
    X=preset('blast', 'Breach Shell', cost=8, range=40.0, radius=6.0, delay=0.6, damage=160),
)
