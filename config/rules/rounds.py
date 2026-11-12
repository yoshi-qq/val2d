"""Rounds, the bomb and the modes. Estimates by Claude Code, 11.11.2026; units: metres, seconds, credits. Edit freely."""

RULES = {
    'rounds': {
        'buy_time': 30,
        'round_time': 100,
        'end_time': 6,
        'half_after': 12,
        'win_rounds': 13,
        'overtime_margin': 2,
        'overtime_credits': 5000,
    },
    'spike': {
        'plant_time': 4.0,
        'fuse_time': 45.0,
        'defuse_time': 7.0,
        'defuse_checkpoint': 3.5,
        'blast_radius': 12.0,
    },
    'modes': {
        'quick': {'win_rounds': 4, 'half_after': 3, 'buy_time': 20, 'round_time': 80, 'overtime': False},
        'deathmatch': {'kill_limit': 40, 'time_limit': 360, 'respawn': 3.0, 'spawn_shield': 50},
    },
}
