"""Template for a map built in Python. Copy to gameplay/data/maps/<key>.py (no leading underscore); the map
then shows up in the menu. Materials and props: config/content/materials.py. Helpers: gameplay/mapkit.py.
Open it in the map editor to fine-tune; saving there writes <key>.json, which then replaces this file.
"""
from gameplay.mapkit import MapBuilder

b = MapBuilder("Yard", 48, 40, floor="concrete", source="template, 12.11.2026")
# attacker spawn in the south, defender spawn in the north, each with a buy-phase barrier toward the map
b.spawn_area(0, 16, 34, 32, 39, points=5, barrier="n")
b.spawn_area(1, 16, 1, 32, 6, points=5, barrier="s")
# site A: a room with two doorways and a door in one of them, a platform with a ramp, crates as cover
b.room(4, 10, 20, 24, mat="brick", doors=[("s", 6, 2), ("e", 5, 2)]).door(11, 23)
b.site("A", 5, 11, 19, 23)
b.platform(8, 12, 14, 15, ramp="s", ramp_length=2.0, ramp_width=2.0)
b.crates(15, 18, count=2)
# site B: open area with a crate stack and a low wall
b.site("B", 30, 12, 44, 24)
b.crates(34, 16, count=3, along="y")
b.wall(38, 20, 42, 20.5, mat="wood_fence")
# mid: cover between spawns
b.wall(22, 18, 26, 22)
b.callout("Mid", 20, 14, 28, 26)
MAP = b.build()
