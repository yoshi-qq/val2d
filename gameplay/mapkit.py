"""Building maps in Python: gameplay/data/maps/<key>.py defines MAP = builder.build().

Prefabs (rooms with doorways, crate stacks, platforms with ramps, sites, spawn areas) save writing every
wall by hand; the result is the same data as a map-editor .json file. If both <key>.json and <key>.py
exist, the .json wins (the editor saves .json), so a Python map opened and saved in the editor becomes a .json.

    from gameplay.mapkit import MapBuilder
    b = MapBuilder("Yard", 48, 40, floor="concrete", source="Christian, 12.11.2026")
    b.room(4, 4, 20, 16, doors=[("s", 6, 2), ("e", 4, 2)]).door(11, 15)
    b.platform(26, 6, 34, 12, ramp="w")
    b.crates(22, 20, count=3)
    b.site("A", 26, 4, 36, 14)
    b.spawn_area(0, 18, 34, 30, 40, points=5)
    b.spawn_area(1, 18, 0, 30, 4, points=5)
    MAP = b.build()
"""
from __future__ import annotations

from typing import Any

Rect4 = tuple[float, float, float, float]


class MapBuilder:
    def __init__(self, name: str, width: float, height: float, floor: str = "concrete", source: str = "") -> None:
        self.data: dict[str, Any] = {"name": name, "source": source, "width": width, "height": height, "floor": floor,
                                     "floors": [], "walls": [], "crates": [], "platforms": [], "ramps": [], "sites": [],
                                     "spawns": {"0": [], "1": []}, "spawn_zones": {}, "callouts": [], "objects": [],
                                     "decals": []}

    # ---------------------------------------------------------------- single pieces
    def wall(self, x0: float, y0: float, x1: float, y1: float, mat: str = "concrete", **extra: Any) -> MapBuilder:
        """A wall; extra keys (pen, sight, height) override the material's values."""
        if x1 > x0 and y1 > y0:
            self.data["walls"].append({"rect": [x0, y0, x1, y1], "mat": mat, **extra})
        return self

    def door(self, x: float, y: float) -> MapBuilder:
        """A door (opens with F) centred at x, y; put it in a doorway of room(...)."""
        return self.thing("door", x, y)

    def floor(self, x0: float, y0: float, x1: float, y1: float, mat: str) -> MapBuilder:
        self.data["floors"].append({"rect": [x0, y0, x1, y1], "mat": mat})
        return self

    def crate(self, x: float, y: float, size: float = 2.0) -> MapBuilder:
        """Low cover one level high (players can jump on it)."""
        self.data["crates"].append([x, y, x + size, y + size])
        return self

    def site(self, name: str, x0: float, y0: float, x1: float, y1: float) -> MapBuilder:
        self.data["sites"].append({"name": name, "rect": [x0, y0, x1, y1]})
        return self.callout(f"{name} Site", x0, y0, x1, y1)

    def spawn(self, team: int, x: float, y: float) -> MapBuilder:
        self.data["spawns"][str(team)].append([x, y])
        return self

    def callout(self, name: str, x0: float, y0: float, x1: float, y1: float) -> MapBuilder:
        self.data["callouts"].append({"name": name, "rect": [x0, y0, x1, y1]})
        return self

    def thing(self, key: str, x: float, y: float) -> MapBuilder:
        """A prop from config/content/materials.py OBJECTS."""
        self.data["objects"].append({"key": key, "pos": [x, y]})
        return self

    def decal(self, key: str, x: float, y: float) -> MapBuilder:
        self.data["decals"].append({"key": key, "pos": [x, y]})
        return self

    def target(self, x: float, y: float, move: float = 0.0) -> MapBuilder:
        """A practice target (practice range only)."""
        self.data.setdefault("practice_targets", []).append({"pos": [x, y], "move": move})
        return self

    # ---------------------------------------------------------------- prefabs
    def room(self, x0: float, y0: float, x1: float, y1: float, mat: str = "concrete", thickness: float = 1.0,
             doors: list[tuple[str, float, float]] = ()) -> MapBuilder:
        """Four walls around a rectangle (outer edge). doors: (side n/s/e/w, offset from the side's start, width)
        leave gaps; add door(...) in a gap for a door that opens."""
        t = thickness
        sides = {"n": (x0, y0, x1, y0 + t, "x"), "s": (x0, y1 - t, x1, y1, "x"),
                 "w": (x0, y0 + t, x0 + t, y1 - t, "y"), "e": (x1 - t, y0 + t, x1, y1 - t, "y")}
        for side, (a0, b0, a1, b1, axis) in sides.items():
            gaps = sorted((off, width) for s, off, width in doors if s == side)
            start = a0 if axis == "x" else b0
            end = a1 if axis == "x" else b1
            cursor = start
            for off, width in gaps:
                g0 = (a0 if axis == "x" else b0) + off
                if axis == "x":
                    self.wall(cursor, b0, g0, b1, mat)
                else:
                    self.wall(a0, cursor, a1, g0, mat)
                cursor = g0 + width
            if axis == "x":
                self.wall(cursor, b0, end, b1, mat)
            else:
                self.wall(a0, cursor, a1, end, mat)
        return self

    def crates(self, x: float, y: float, count: int = 3, size: float = 2.0, along: str = "x") -> MapBuilder:
        """A row of crates touching each other."""
        for i in range(count):
            self.crate(x + i * size if along == "x" else x, y + i * size if along == "y" else y, size)
        return self

    def platform(self, x0: float, y0: float, x1: float, y1: float, ramp: str = "", ramp_length: float = 2.0,
                 ramp_width: float = 0.0, level: float = 1, mat: str = "") -> MapBuilder:
        """A raised area; ramp n/s/e/w adds a ramp on that side, centred (width = ramp_width or the full side).
        mat: floor material drawn on it (also its footstep floor); "floor" keeps the material below."""
        if level == 1 and not mat:
            self.data["platforms"].append([x0, y0, x1, y1])
        else:
            self.data["platforms"].append({"rect": [x0, y0, x1, y1], "level": level, **({"mat": mat} if mat else {})})
        if mat and mat != "floor":
            self.floor(x0, y0, x1, y1, mat)
        if ramp:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            wx = ramp_width or (x1 - x0)
            wy = ramp_width or (y1 - y0)
            rect = {"w": [x0 - ramp_length, cy - wy / 2, x0, cy + wy / 2], "e": [x1, cy - wy / 2, x1 + ramp_length, cy + wy / 2],
                    "n": [cx - wx / 2, y0 - ramp_length, cx + wx / 2, y0], "s": [cx - wx / 2, y1, cx + wx / 2, y1 + ramp_length]}[ramp]
            self.data["ramps"].append(rect)
        return self

    def stairs(self, x0: float, y0: float, x1: float, y1: float, rise: str, low: float, high: float) -> MapBuilder:
        """Ramp or stairs between two floor levels; rise n/s/e/w is the direction it goes up (n = +y)."""
        self.data["ramps"].append({"rect": [x0, y0, x1, y1], "rise": rise, "low": low, "high": high})
        return self

    def spawn_area(self, team: int, x0: float, y0: float, x1: float, y1: float, points: int = 5,
                   barrier: str = "") -> MapBuilder:
        """Spawn zone with `points` spawns spread across it; barrier n/s/e/w adds a buy-phase barrier on that side."""
        self.data["spawn_zones"][str(team)] = [x0, y0, x1, y1]
        for i in range(points):
            self.spawn(team, x0 + (x1 - x0) * (i + 1) / (points + 1), (y0 + y1) / 2)
        if barrier:  # 2 m barrier pieces along that side
            horizontal = barrier in ("n", "s")
            length = (x1 - x0) if horizontal else (y1 - y0)
            for i in range(max(1, round(length / 2))):
                along = (x0 if horizontal else y0) + 1 + i * 2
                at = {"n": (along, y0 - 1), "s": (along, y1 + 1), "w": (x0 - 1, along), "e": (x1 + 1, along)}[barrier]
                self.thing("spawn_barrier", *at)
        return self

    def mirror(self, axis: str = "y") -> MapBuilder:
        """Adds a mirrored copy of every wall, crate, platform and ramp (symmetric maps). Call once, after building one half."""
        w, h = self.data["width"], self.data["height"]

        def flip(r: list[float]) -> list[float]:
            x0, y0, x1, y1 = r
            return [x0, h - y1, x1, h - y0] if axis == "y" else [w - x1, y0, w - x0, y1]
        self.data["walls"] += [{**wl, "rect": flip(wl["rect"])} for wl in list(self.data["walls"])]
        self.data["crates"] += [flip(c) for c in list(self.data["crates"])]
        self.data["platforms"] += [flip(p) if isinstance(p, list) else {**p, "rect": flip(p["rect"])} for p in list(self.data["platforms"])]
        self.data["ramps"] += [flip(r) for r in list(self.data["ramps"])]
        return self

    def build(self) -> dict[str, Any]:
        return self.data
