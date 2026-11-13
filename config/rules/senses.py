"""What players see and hear. fov: field of view in degrees (also the drawn sight cone); view_distance: metres the sight cone reaches. Estimates by Claude Code, 11.11.2026; units: metres, seconds, credits. Edit freely."""

RULES = {
    'sight': {'fov': 103.0, 'view_distance': 60.0,
              'head_height': 1.4},   # props lower than this (config/content/prop_heights.py) do not block sight or shots
    'sound': {'run_radius': 18.0, 'shot_radius': 45.0, 'silenced_radius': 40.0,
              'silenced_forward_radius': 80.0, 'silenced_half_angle': 30.0},
}
