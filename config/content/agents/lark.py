"""Lark (Initiator). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Lark', role='Initiator', order=19,
    C=preset('zone', 'Trill', price=150, max=1, start=0, range=16.0, radius=4.0, duration=6.0, status='deaf', status_time=1.0),
    Q=preset('flash', 'Dawn', price=250, max=2, start=0, range=12.0, fuse=0.8, blind=1.4, cone=140.0, through_walls=True),
    E=preset('stim', 'Lift', price=0, max=1, start=1, radius=6.0, duration=6.0, recharge=40.0),
    X=preset('zone', 'Aria', cost=8, range=30.0, radius=8.0, duration=4.0, delay=1.5, status='concuss', status_time=1.0),
)
