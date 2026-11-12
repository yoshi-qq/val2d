"""Sorrel (Duelist). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Sorrel', role='Duelist', order=13,
    C=preset('smoke', 'Thicket', price=150, max=2, start=0, range=8.0, radius=2.0, duration=8.0),
    Q=preset('zone', 'Sap', price=150, max=1, start=0, range=12.0, radius=2.5, duration=5.0, status='slow', status_time=0.5),
    E=preset('hop', 'Spring', price=0, max=1, start=1, velocity=7.0, recharge=20.0),
    X=preset('immunity', 'Overgrowth', cost=7, duration=8.0, regen=10.0),
)
