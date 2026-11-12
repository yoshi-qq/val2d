"""Camera and screen of the game client. Edit freely; read when the game starts.

The field of view itself (fov, view_distance) is a game rule for everyone: config/rules/senses.py.
"""

VIEW = {
    "view_meters": 30.0,        # metres across the screen at normal zoom
    "height_draw": 0.7,         # screen lift per metre of height (jumps, platforms), share of a metre on screen
    "outside_darkness": 175,    # 0-255: how dark everything outside the own sight is drawn
    "behind_cover_grey": 110,   # 0-255: grey behind head-high cover (only taller things are seen there)
    "sight_rays": 220,          # rays cast for the sight area (more = smoother edges, slower)
    "body_sight": 0.9,          # metres around the own figure that are always lit
    "facing_marker": 1.3,       # metres: length of the line that shows exactly where a figure looks
}
