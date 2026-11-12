"""Cato (Sentinel). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Cato', role='Sentinel', order=29,
    C=preset('shield', 'Rampart', price=200, max=1, start=0, points=35, range=10.0),
    Q=preset('sensor', 'Watchpost', price=200, max=1, start=0, range=12.0, radius=9.0, duration=40.0, pulse=2.5),
    E=preset('anchor', 'Recall', price=0, max=1, start=1, duration=60.0, recharge=45.0),
    X=preset('reveal_all', 'Overwatch', cost=7, duration=5.0),
)
