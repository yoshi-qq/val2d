"""Kestrel (Duelist). Values: estimates by Claude Code, 11.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Kestrel', role='Duelist', order=1,
    C=preset('flash', 'Spark', price=250, max=2, start=0, range=12.0, fuse=0.5, blind=1.6, cone=120.0),
    Q=preset('hop', 'Leap', price=150, max=2, start=0, velocity=6.5),
    E=preset('dash', 'Glide', price=0, max=1, start=1, distance=7.0, duration=0.2, kills_to_recharge=2),
    X=preset('overdrive', 'Overdrive', cost=7, duration=8.0, rate_mult=1.15),
)
