"""Juniper (Controller). Values: estimates by Claude Code, 11.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Juniper', role='Controller', order=7,
    C=preset('zone', 'Muffle', price=150, max=1, start=0, range=18.0, radius=3.5, duration=8.0, status='deaf', status_time=1.0),
    Q=preset('zone', 'Rot', price=200, max=1, start=0, range=18.0, radius=3.0, duration=7.0, dps=0, status='decay', status_time=1.0),
    E=preset('smoke', 'Cloudcast', price=0, max=3, start=3, range=40.0, radius=3.0, duration=14.0, remote=True, recharge=40.0,
             multi=3),  # mark up to 3 points, right click places them all
    X=preset('zone', 'Blackout', cost=8, range=30.0, radius=9.0, duration=6.0, delay=1.0, status='suppress', status_time=1.0),
)
