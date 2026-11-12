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
        # VALORANT patch 5.12 (Swiftplay) and patch 10.09 (9-point ultimates).
        'quick': {
            'win_rounds': 5, 'half_after': 4, 'buy_time': 20, 'round_time': 100, 'overtime': False,
            'round_credits': (2400, 4250, 4250), 'pistol_win_bonus': 600,
            'half_ult_points': 2, 'high_cost_ult_points': 3,
        },
        'deathmatch': {'kill_limit': 40, 'time_limit': 360, 'respawn': 3.0, 'spawn_shield': 50},
    },
}
