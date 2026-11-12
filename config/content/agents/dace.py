"""Dace (Duelist). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Dace', role='Duelist', order=14,
    C=preset('flash', 'Ripple', price=250, max=2, start=0, range=10.0, fuse=0.3, blind=1.2, cone=110.0),
    Q=preset('teleport', 'Undertow', price=250, max=1, start=0, range=6.0),
    E=preset('dash', 'Current', price=0, max=1, start=1, distance=5.0, duration=0.18, kills_to_recharge=1),
    X=preset('overdrive', 'Riptide', cost=7, duration=10.0, rate_mult=1.2),
)
