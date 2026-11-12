"""Editor draft for Ascent. Open with python map_editor.py _ascent."""
from gameplay.mapkit import MapBuilder

WIDTH, HEIGHT = 72, 64
b = MapBuilder(
    "Ascent (editor draft)", WIDTH, HEIGHT, floor="ascent_cobble",
    source="VALORANT Ascent tactical map and gameplay references; approximate Val2d blockout",
)

# Coordinates are measured from the top-left of the reference. Convert once
# here because Val2d world Y increases upward.
def rect(x0, top, x1, bottom):
    return x0, HEIGHT - bottom, x1, HEIGHT - top


def at(x, top):
    return x, HEIGHT - top


def area(name, x0, top, x1, bottom, floor=None):
    b.callout(name, *rect(x0, top, x1, bottom))
    if floor:
        b.floor(*rect(x0, top, x1, bottom), f"ascent_{floor}")


def prop(name, x, top, rotation=0):
    b.data["objects"].append({"key": f"ascent_{name}", "pos": at(x, top), "rot": rotation})


# Walkable footprint, drawn in 2 m blocks. Named rooms below provide more
# precise callouts, and the complement is solid so the lanes cannot be bypassed.
footprint = (
    (26, 4, 48, 12), (10, 10, 64, 16),                 # defender spawn and rotation
    (8, 14, 24, 34), (22, 22, 32, 30),                 # A Site and Tree
    (8, 32, 16, 50), (8, 46, 32, 54),                  # A Main and A Lobby
    (32, 14, 42, 30), (28, 24, 46, 44),                # Mid Bottom and Courtyard
    (26, 28, 32, 42), (32, 42, 42, 56),                # Catwalk and Mid Top
    (42, 22, 52, 30), (50, 14, 64, 36),                # Market and B Site
    (58, 32, 64, 50), (42, 46, 64, 54),                # B Main and B Lobby
    (24, 52, 50, 62),                                  # attacker spawn
)
walkable = {
    (x, y)
    for x0, y0, x1, y1 in footprint
    for x in range(x0, x1, 2)
    for y in range(y0, y1, 2)
}
solid = {(x, y) for x in range(0, WIDTH, 2) for y in range(0, HEIGHT, 2)} - walkable
while solid:
    x, y = min(solid, key=lambda point: (point[1], point[0]))
    right = x + 2
    while (right, y) in solid:
        right += 2
    bottom = y + 2
    while all((column, bottom) in solid for column in range(x, right, 2)):
        bottom += 2
    solid.difference_update((column, row) for column in range(x, right, 2) for row in range(y, bottom, 2))
    b.wall(*rect(x, y, right, bottom), mat="ascent_roof")

# Add specific labels before larger areas so callout_at picks the landmark.
area("A Rafters", 9, 15, 19, 19)
area("A Hell", 9, 19, 13, 22, "timber")
area("A Generator", 14, 22, 18, 26)
area("A Dice", 18, 28, 22, 32)
area("B Boathouse", 51, 29, 58, 35, "timber")
area("B Lane", 58, 25, 64, 36)
area("Mid Pizza", 39, 21, 43, 25, "terracotta")
area("A Tree", 23, 22, 30, 29, "garden")
area("Mid Catwalk", 26, 29, 30, 42, "courtyard")
area("Mid Bottom", 32, 15, 42, 24, "courtyard")
area("Mid Courtyard", 29, 25, 46, 43, "courtyard")
area("Mid Top", 32, 43, 42, 53, "terracotta")
area("B Market", 43, 22, 51, 30, "market")
area("A Main", 8, 33, 16, 46)
area("B Main", 58, 36, 64, 46)
area("A Lobby", 8, 46, 32, 53, "terracotta")
area("B Lobby", 42, 46, 64, 53, "terracotta")
b.spawn_area(0, *rect(27, 55, 46, 60))
b.spawn_area(1, *rect(28, 5, 46, 9))
area("Attacker Side Spawn", 24, 53, 50, 62, "courtyard")
area("Defender Side Spawn", 26, 4, 48, 12, "courtyard")
b.site("A", *rect(9, 19, 23, 32))
b.site("B", *rect(51, 19, 63, 29))

# The current height model has one walkable surface per point. Rafters
# and Hell sit next to each other until the map supports stacked floors.
rafters = rect(9, 15, 19, 19)
steps = rect(19, 15, 22, 19)
b.platform(*rafters)
b.data["ramps"].append(steps)
for key, surface in (("ascent_rafters", rafters), ("ascent_steps", steps)):
    b.data["decals"].append({"key": key, "rect": surface})

# Doorways leave exactly 2.5 m for a 90°-rotated door. The current door
# interaction is reversible with F; the switch and broken art are staged.
for x, top, material in ((24, 25, "ascent_stucco"), (50, 25, "ascent_brick")):
    for t0, t1 in ((22, top - 1.25), (top + 1.25, 30)):
        b.wall(*rect(x - 0.25, t0, x + 0.25, t1), mat=material)
    prop("site_door", x, top, rotation=90)
    prop("door_switch", x + (-1 if x == 24 else 1), top - 1.7)

# Each spawn approach gets its own buy-phase barrier. Rectangles span the lane.
for opening in (
    (8, 43, 16, 43.5), (32, 45, 42, 45.5), (58, 43, 64, 43.5),
    (8, 15, 24, 15.5), (32, 17, 42, 17.5), (50, 16, 64, 16.5),
):
    b.data["objects"].append({"key": "spawn_barrier", "rect": rect(*opening)})

for name, x, y in (
    ("generator", 16, 24), ("radianite_crate", 20, 29),
    ("radianite_half", 12, 30), ("wood_crate", 10, 22),
    ("olive_tree", 27, 27), ("planter", 27, 23.5),
    ("fountain", 35, 32), ("planter", 31, 39),
    ("radianite_stack", 54.5, 23.5), ("radianite_crate", 60, 21),
    ("boat_crate", 56, 32), ("boathouse_skiff", 53, 33.5),
    ("market_stall", 45.5, 27.5), ("market_awning", 46, 23.5),
    ("market_sign", 46, 22.8), ("pizza_sign", 40, 22),
    ("stone_arch", 12, 34.5), ("stone_arch", 61, 36.5),
):
    prop(name, x, y)
for name, x, y in (
    ("ivy", 21, 16), ("ivy", 52, 16), ("drain", 37, 39),
    ("drain", 61, 31), ("paint_a", 10, 31), ("paint_b", 62, 28),
):
    b.decal(f"ascent_{name}", *at(x, y))
for strip_rect in ((10, 31.5, 21, 32), (52, 28.5, 62, 29)):
    b.data["decals"].append({"key": "ascent_site_line", "rect": rect(*strip_rect)})

MAP = b.build()
