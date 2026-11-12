"""Look of menus and HUD: colours, fonts, sizes. Edit freely; read when the game starts.

Colours as "#rrggbb" or "#rrggbbaa". Fonts: a file under font/ or "" for the clean built-in sans font.
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
        "gold": "#f2c94c",         # credits, ultimate ready
        "good": "#5ee38a",
        "shade": "#000000b4",      # dimming behind dialogs
    },
    "fonts": {
        "ui": "",                  # body text
        "title": "",               # big headings
        "numbers": "",             # HUD numbers (health, ammo, timer)
    },
    "sizes": {"xs": 13, "s": 16, "m": 20, "l": 30, "xl": 46, "xxl": 72},
}
