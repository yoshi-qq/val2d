"""Thorne (Controller). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Thorne', role='Controller', order=22,
    C=preset('tripwire', 'Briar', price=150, max=2, start=0, length=5.0, duration=120.0, status='slow', status_time=3.0),
    Q=preset('wall', 'Bramble', price=250, max=1, start=0, range=18.0, length=8.0, duration=10.0, cross_status='vulnerable', cross_time=3.0),
    E=preset('smoke', 'Shroud', price=0, max=2, start=2, range=25.0, radius=2.6, duration=15.0, recharge=35.0),
    X=preset('zone', 'Thornfield', cost=7, range=30.0, radius=7.0, duration=8.0, dps=15, status='slow', status_time=0.5),
)
