"""Hit zones, set by Christian: half widths across the line of fire (metres, from sprite width 16 px = 1 m) and allowed depth deviation of the cursor (metres)."""

CONFIG = {
    'hit_zones': {
        'head_half_width': 0.25,
        'body_half_width': 0.375,
        'legs_half_width': 0.22,
        'head_depth_tolerance': 1.2,
        'body_depth_tolerance': 3.0,
    },
}
