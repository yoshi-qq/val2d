"""Example balance patch. Copy to config/patches/01_my_patch.py (no leading underscore) and change the values;
patches apply in file-name order and never touch the original agent, weapon or map files.
How patches work: gameplay/patches.py. All fields: docs/MODDING.md.
"""

VERSION = "1.01"
NOTES = "Kestrel: shorter flash. Hammer: more expensive. Slow: a little weaker. Workyard: one more crate in mid."

PATCH = {
    "agents": {
        "kestrel": {"C": {"blind": 1.3, "price": 300}},     # change single values of an ability
        "marrow": {"Q": {"alt": None}},                      # None removes a field (here: the right-click wall)
    },
    "weapons": {"assault_rifle": {"price": 3100}},
    "armor": {"heavy_shield": {"price": 1050}},
    "statuses": {"slow": {"speed": 0.6}},
    "rules": {"economy": {"start": 800}},
    "maps": {"workyard": {"add": {"crates": [[23, 19, 25, 21]]}}},
}
