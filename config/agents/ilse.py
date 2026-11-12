"""Ilse (Sentinel). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Ilse', role='Sentinel', order=27,
    C=preset('alarm', 'Chill', price=150, max=1, start=0, range=10.0, radius=5.0, duration=120.0, status='slow', status_time=2.5),
    Q=preset('tripwire', 'Frost Line', price=200, max=1, start=0, length=6.0, duration=120.0, status='slow', status_time=3.0),
    E=preset('heal', 'Hearth', price=0, max=1, start=1, amount=50, duration=4.0, range=12.0, recharge=45.0),
    X=preset('zone', 'Winterhold', cost=8, range=25.0, radius=8.0, duration=6.0, delay=1.0, status='suppress', status_time=1.0),
)
