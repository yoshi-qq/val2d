"""Game config: values Christian tunes. Read at start; per-player settings live in ~/.val2d/settings.json.

Set by Christian. Hit zones: half widths across the line of fire (metres, from sprite width 16 px = 1 m), allowed depth deviation of the cursor (metres).
"""

CONFIG = {
    'hit_zones': {
        'head_half_width': 0.25,
        'body_half_width': 0.375,
        'legs_half_width': 0.22,
        'head_depth_tolerance': 1.2,
        'body_depth_tolerance': 3.0,
    },
    'lobby_defaults': {
        'all_around_sight': False,
        'sound_rings': False,
        'win_rounds': 13,
        'overtime': True,
        'team_size': 1,
    },
    'player_defaults': {'camera_push': 0.35, 'sensitivity': 0.25, 'enemy_highlight': '#ee4c4a'},
}
