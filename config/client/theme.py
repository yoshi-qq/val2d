"""Menu and HUD colours, fonts and sizes. An empty font name selects the bundled sans serif."""

THEME = {
    "colors": {
        "bg": "#0f1923",
        "panel": "#15232ee8",
        "panel_light": "#293d48ec",
        "line": "#bdcbd15c",
        "text": "#ece8e1",
        "muted": "#a6b7be",
        "accent": "#ff4655",       # buttons, highlights, enemy colour
        "accent_dark": "#bd3944",
        "ally": "#62e4cb",
        "enemy": "#ff4655",
        "gold": "#f2c94c",         # credits, own highlights
        "ult": "#ffe6a4",          # ultimate points and ready ultimate
        "good": "#5ee38a",
        "shade": "#000000b4",      # dimming behind dialogs
    },
    "fonts": {
        "ui": "fixed_sys.ttf",
        "title": "fixed_sys.ttf",
        "numbers": "fixed_sys.ttf",
    },
    "pixel": True,
    "native": 16,                  # native size of the pixel font; every text size is a whole multiple of it
    "sizes": {"xs": 1, "s": 1, "m": 1, "l": 2, "xl": 3, "xxl": 4},  # pixel look: multiples of native
    "smooth_sizes": {"xs": 16, "s": 19, "m": 23, "l": 34, "xl": 56, "xxl": 78},
    "border": 1,
}
