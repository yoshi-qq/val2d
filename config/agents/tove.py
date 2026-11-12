"""Tove (Controller). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Tove', role='Controller', order=25,
    C=preset('flash', 'Flurry', price=200, max=1, start=0, range=12.0, fuse=0.5, blind=1.3, cone=120.0),
    Q=preset('wall', 'Snowbank', price=250, max=1, start=0, range=18.0, length=9.0, duration=12.0),
    E=preset('smoke', 'Whiteout', price=0, max=2, start=2, range=30.0, radius=2.8, duration=15.0, recharge=35.0),
    X=preset('zone', 'Hoarfrost', cost=7, range=30.0, radius=6.0, duration=6.0, delay=0.8, status='suppress', status_time=1.0),
)
