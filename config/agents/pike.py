"""Pike (Initiator). Values: estimates by Claude Code, 12.11.2026. Tune freely; how it works: docs/MODDING.md."""
from gameplay.kit.dsl import agent, preset

AGENT = agent(
    'Pike', role='Initiator', order=18,
    C=preset('blast', 'Hook', price=250, max=1, start=0, range=14.0, radius=2.0, delay=0.5, damage=0, status='detain', status_time=1.5),
    Q=preset('decoy', 'Lure', price=100, max=2, start=0, duration=5.0, speed=4.0),
    E=preset('sensor', 'Scan', price=0, max=1, start=1, range=25.0, radius=7.0, duration=4.0, pulse=1.0, recharge=40.0),
    X=preset('wave', 'Harpoon', cost=7, length=45.0, width=1.0, damage=100, status='detain', status_time=2.0),
)
