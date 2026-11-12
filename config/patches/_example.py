"""Example balance patch. Copy to config/patches/01_my_patch.py (no leading underscore) and change the values;
patches apply in file-name order and never touch the original agent, weapon or map files.
How patches work: gameplay/patches.py. All fields: docs/MODDING.md.
"""

VERSION = "1.01"
NOTES = "Phoenix: flash price. Vandal: more expensive. Slow: a little weaker. Ascent: practice variant."

PATCH = {
    "agents": {
        "phoenix": {"Q": {"price": 300}},     # change single values of an ability
        "omen": {"E": {"tactical": None}},                    # None removes a field
    },
    "weapons": {"vandal": {"price": 3100}},
    "armor": {"heavy_armor": {"price": 1050}},
    "statuses": {"slow": {"speed": 0.6}},
    "rules": {"economy": {"start": 800}},
    "maps": {"ascent": {"set": {"name": "Ascent (practice)"}}},
}
