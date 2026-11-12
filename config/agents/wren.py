"""Wren (Initiator). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Wren', role='Initiator', order=16,
    C=preset('sensor', 'Peep', price=200, max=2, start=0, range=20.0, radius=6.0, duration=6.0, pulse=1.0),
    Q=preset('flash', 'Chirp', price=250, max=1, start=0, range=16.0, fuse=0.6, blind=1.5, cone=130.0),
    E=preset('hop', 'Flit', price=0, max=1, start=1, velocity=6.5, recharge=20.0),
    X=preset('zone', 'Murmuration', cost=8, range=40.0, radius=10.0, duration=5.0, delay=0.8, status='nearsight', status_time=1.0, reveal=True),
)
