"""Look of menus and HUD: colours, fonts, sizes. Edit freely; read when the game starts.

Colours as "#rrggbb" or "#rrggbbaa". Fonts: a file under font/ or "" for the built-in sans font.
Pixel look: text is drawn with the pixel font at its native size and enlarged by whole numbers (no smoothing),
borders are whole pixels of the UI grid, so menus and HUD match the pixel-art sprites.
"""

THEME = {
    "colors": {
        "bg": "#0f1923",           # menu background
        "panel": "#0f1923d8",      # translucent panels
        "panel_light": "#1f2d3ae6",
        "line": "#ece8e133",       # thin separators and outlines
        "text": "#ece8e1",
        "muted": "#8b978f",
        "accent": "#ff4655",       # buttons, highlights, enemy colour
        "accent_dark": "#bd3944",
        "ally": "#4fd6c8",
        "enemy": "#ff4655",
        "gold": "#f2c94c",         # credits, own highlights
        "ult": "#f7f0a8",          # ultimate points and ready ultimate
        "good": "#5ee38a",
        "shade": "#000000b4",      # dimming behind dialogs
    },
    "fonts": {
        "ui": "fixed_sys.ttf",     # body text
        "title": "fixed_sys.ttf",  # big headings
        "numbers": "fixed_sys.ttf",  # HUD numbers (health, ammo, timer)
    },
    "pixel": True,                 # False: smooth text at the sizes below (in pixels)
    "native": 16,                  # native size of the pixel font; every text size is a whole multiple of it
    "sizes": {"xs": 1, "s": 1, "m": 1, "l": 2, "xl": 3, "xxl": 4},  # pixel look: multiples of native
    "smooth_sizes": {"xs": 13, "s": 16, "m": 20, "l": 30, "xl": 46, "xxl": 72},
    "border": 2,                   # outline width in screen pixels
}
