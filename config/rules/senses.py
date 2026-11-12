"""What players see and hear. fov: field of view in degrees (also the drawn sight cone); view_distance: metres the sight cone reaches. Estimates by Claude Code, 11.11.2026; units: metres, seconds, credits. Edit freely."""

RULES = {
    'sight': {'fov': 103.0, 'view_distance': 60.0},
    'sound': {'run_radius': 18.0, 'shot_radius': 45.0, 'silenced_radius': 12.0},
}
