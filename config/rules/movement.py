"""Movement, jumping, steps and falls. Estimates by Claude Code, 11.11.2026; units: metres, seconds, credits. Edit freely."""

RULES = {
    'movement': {
        'run_speed': 6.0,
        'walk_mod': 0.55,
        'crouch_mod': 0.4,
        'air_mod': 0.9,
        'accel': 60.0,
        'decel': 45.0,
        'jump_velocity': 4.2,
        'gravity': 14.0,
        'radius': 0.4,
        'level_height': 1.0,
        'step_up': 0.4,
        'step_down': 0.35,
    },
    'fall': {'safe_speed': 7.0, 'damage_per_speed': 15.0, 'max_damage': 60},
}
