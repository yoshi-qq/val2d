"""Quill (Duelist). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Quill', role='Duelist', order=12,
    C=preset('wave', 'Prick', price=200, max=2, start=0, length=10.0, width=1.0, damage=25, status='vulnerable', status_time=3.0),
    Q=preset('decoy', 'Feint', price=100, max=2, start=0, duration=3.0, speed=5.5),
    E=preset('sensor', 'Quill Dart', price=0, max=1, start=1, range=18.0, radius=5.0, duration=3.0, pulse=0.75, recharge=35.0),
    X=preset('wave', 'Volley', cost=7, length=40.0, width=2.0, damage=70, status='nearsight', status_time=3.0),
)
