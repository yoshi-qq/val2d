"""Basil (Sentinel). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Basil', role='Sentinel', order=28,
    C=preset('heal', 'Salve', price=150, max=1, start=0, amount=40, duration=3.0, range=12.0),
    Q=preset('tripwire', 'Snare Root', price=200, max=1, start=0, length=5.0, duration=120.0, status='detain', status_time=2.0),
    E=preset('stim', 'Tonic', price=0, max=1, start=1, radius=5.0, duration=6.0, recharge=45.0),
    X=preset('zone', 'Garden', cost=7, range=15.0, radius=6.0, duration=8.0, heal_allies=12.0, status='slow', status_time=0.5),
)
