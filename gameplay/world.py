"""Map: walls, crates, levels, bomb sites, spawns."""
from __future__ import annotations

import json
import warnings
from functools import lru_cache
from dataclasses import dataclass, field
from pathlib import Path

from gameplay.geometry import Rect, Vec

MAP_DIR = Path(__file__).resolve().parent / "data" / "maps"


@dataclass(frozen=True)
class Wall:
    rect: Rect
    penetration: int  # material: 0 thin, 1 medium, 2 thick, 3 impenetrable
    blocks_sight: bool = True
    height: int = 2  # levels; crates have 1 and can be climbed
    material: str = ""  # key in config/materials.py WALLS (decides the tile)
    buy_phase_only: bool = False  # blocks only during the buy phase (spawn barrier)
    door: bool = False  # can be opened; then it blocks nothing
    solid: bool = True  # False: blocks only sight (bushes), never movement or bullets


@dataclass(frozen=True)
class MapThing:
    """Placed object or decal: key from config/materials.py, rect in metres, rotation in 90° steps."""
    key: str
    rect: Rect
    rot: int = 0


@dataclass(frozen=True)
class Platform:
    """Raised area (level 1). Ramps connect it to the ground."""
    rect: Rect
    level: int = 1


@dataclass(frozen=True)
class Site:
    name: str
    rect: Rect


@dataclass
class WorldMap:
    key: str
    name: str
    width: float
    height: float
    walls: list[Wall] = field(default_factory=list)
    platforms: list[Platform] = field(default_factory=list)
    ramps: list[Rect] = field(default_factory=list)
    sites: list[Site] = field(default_factory=list)
    spawns: dict[int, list[Vec]] = field(default_factory=dict)  # 0 Angreifer, 1 Verteidiger
    spawn_zones: dict[int, Rect] = field(default_factory=dict)
    callouts: list[tuple[str, Rect]] = field(default_factory=list)
    floor: str = ""  # key in config/materials.py FLOORS for the whole map
    floors: list[tuple[str, Rect]] = field(default_factory=list)  # floor material patches
    objects: list[MapThing] = field(default_factory=list)
    practice_targets: list[tuple[Vec, float]] = field(default_factory=list)  # (position, sideways travel in m)
    decals: list[MapThing] = field(default_factory=list)

    def ground_height(self, p: Vec) -> float:
        """Height of the surface under a point in metres: platforms and low cover are one level high,
        ramps rise evenly from their low end to the platform they lead onto."""
        h = 0.0
        for pl in self.platforms:
            if pl.rect.contains(p):
                h = max(h, float(pl.level))
        for w in self.walls:
            if w.height == 1 and w.solid and w.rect.contains(p):
                h = max(h, 1.0)
        for rect, axis, high_at_min, top in self.ramp_profiles():
            if rect.contains(p):
                span = (rect.x1 - rect.x0) if axis == "x" else (rect.y1 - rect.y0)
                along = (p.x - rect.x0) if axis == "x" else (p.y - rect.y0)
                t = along / span if span > 0 else 1.0
                h = max(h, top * ((1.0 - t) if high_at_min else t))
        return h

    def ramp_profiles(self) -> list[tuple[Rect, str, bool, float]]:
        """Per ramp: (rect, axis it rises along, True if the high end is at the smaller coordinate, top height)."""
        cached = getattr(self, "_ramp_cache", None)
        if cached is not None:
            return cached
        out: list[tuple[Rect, str, bool, float]] = []
        for r in self.ramps:
            best: tuple[float, str, bool, float] | None = None
            for pl in self.platforms:
                p = pl.rect
                overlap_y = min(r.y1, p.y1) - max(r.y0, p.y0)
                overlap_x = min(r.x1, p.x1) - max(r.x0, p.x0)
                for gap, axis, high_min in ((abs(r.x0 - p.x1), "x", True), (abs(r.x1 - p.x0), "x", False),
                                            (abs(r.y0 - p.y1), "y", True), (abs(r.y1 - p.y0), "y", False)):
                    touching = overlap_y > 0 if axis == "x" else overlap_x > 0
                    if touching and gap < 0.6 and (best is None or gap < best[0]):
                        best = (gap, axis, high_min, float(pl.level))
            if best is None:  # no platform next to it: rise along the longer side toward larger coordinates
                axis = "x" if (r.x1 - r.x0) >= (r.y1 - r.y0) else "y"
                best = (0.0, axis, False, 1.0)
            out.append((r, best[1], best[2], best[3]))
        self._ramp_cache = out
        return out

    def floor_level(self, p: Vec) -> int:
        """Level of the surface under a point (rounded ground height)."""
        return int(self.ground_height(p) + 0.5)

    def floor_material(self, p: Vec) -> str:
        """Floor material key under a point (last matching patch wins), else the map's floor."""
        found = self.floor
        for mat, rect in self.floors:
            if rect.contains(p):
                found = mat
        return found

    def on_ramp(self, p: Vec) -> bool:
        return any(r.contains(p) for r in self.ramps)

    def site_at(self, p: Vec) -> Site | None:
        for s in self.sites:
            if s.rect.contains(p):
                return s
        return None

    def callout_at(self, p: Vec) -> str:
        for name, r in self.callouts:
            if r.contains(p):
                return name
        return ""

    def blocking_walls(self, level: int) -> list[Wall]:
        """Walls that block movement on this level."""
        return [w for w in self.walls if w.height > level and w.solid]

    def sight_walls(self, level: int) -> list[Wall]:
        return [w for w in self.walls if w.blocks_sight and w.height > level]


@lru_cache(maxsize=1)
def load_materials() -> tuple[dict[str, dict], dict[str, str]]:
    """(WALLS, FLOORS) from config/materials.py; empty if unreadable."""
    from gameplay.data import ROOT, _load_py
    path = ROOT / "config" / "materials.py"
    return dict(_load_py(path, "WALLS") or {}), dict(_load_py(path, "FLOORS") or {})


@lru_cache(maxsize=1)
def load_things() -> tuple[dict[str, dict], dict[str, dict]]:
    """(OBJECTS, DECALS) from config/materials.py; empty if unreadable."""
    from gameplay.data import ROOT, _load_py
    path = ROOT / "config" / "materials.py"
    return dict(_load_py(path, "OBJECTS") or {}), dict(_load_py(path, "DECALS") or {})


def _thing(item: dict, table: dict[str, dict], map_key: str) -> MapThing | None:
    key = str(item.get("key", ""))
    spec = table.get(key)
    if spec is None:
        warnings.warn(f"Map {map_key}: unknown object or decal {key!r}")
        return None
    rot = int(item.get("rot", 0)) % 360 // 90 * 90
    if "rect" in item:
        return MapThing(key, _rect(item["rect"]), rot)
    w, h = spec.get("size", (1.0, 1.0))
    if rot in (90, 270):
        w, h = h, w
    x, y = item["pos"]
    return MapThing(key, Rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2), rot)


def _rect(v: list[float]) -> Rect:
    x0, y0, x1, y1 = v
    return Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def map_keys() -> list[str]:
    """All maps: gameplay/data/maps/*.json (map editor) and *.py (built in Python, MAP = ...); _files are skipped."""
    return sorted({p.stem for p in MAP_DIR.glob("*.json")} | {p.stem for p in MAP_DIR.glob("*.py") if not p.name.startswith("_")})


def load_map_raw(key: str) -> dict:
    """Map data of `key`: the .json if there is one (editor saves win), else MAP from the .py. Raises OSError/ValueError."""
    path = MAP_DIR / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    py = MAP_DIR / f"{key}.py"
    if py.exists():
        from gameplay.data import _load_py
        raw = _load_py(py, "MAP")
        if isinstance(raw, dict):
            return raw
        raise ValueError(f"{py.name} defines no MAP dict")
    raise OSError(f"no map file {key}.json or {key}.py")


def load_map(key: str) -> WorldMap:
    try:
        raw = load_map_raw(key)
    except (OSError, ValueError) as exc:
        warnings.warn(f"Map {key} unreadable ({exc}); using an empty practice area.")
        return WorldMap(key="empty", name="Empty area", width=40, height=40,
                        spawns={0: [Vec(20, 4)], 1: [Vec(20, 36)]},
                        spawn_zones={0: Rect(15, 0, 25, 8), 1: Rect(15, 32, 25, 40)},
                        sites=[Site("A", Rect(16, 16, 24, 24))])
    return parse_map(key, raw)


def parse_map(key: str, raw: dict) -> WorldMap:
    """Builds a WorldMap from map-file data (also used by the map editor for its preview)."""
    m = WorldMap(key=key, name=raw["name"], width=raw["width"], height=raw["height"])
    w, h = m.width, m.height
    m.walls += [Wall(Rect(-1, -1, w + 1, 0), 3), Wall(Rect(-1, h, w + 1, h + 1), 3),
                Wall(Rect(-1, 0, 0, h), 3), Wall(Rect(w, 0, w + 1, h), 3)]
    mats = load_materials()[0]
    for wl in raw.get("walls", []):
        mat = str(wl.get("mat", ""))
        base = mats.get(mat, {})
        if mat and not base:
            warnings.warn(f"Map {key}: unknown wall material {mat!r}")
        m.walls.append(Wall(_rect(wl["rect"]), int(wl.get("pen", base.get("pen", 2))), bool(wl.get("sight", base.get("sight", True))),
                            int(wl.get("height", base.get("height", 2))), mat))
    objects, decals = load_things()
    for kind, table, target in (("objects", objects, m.objects), ("decals", decals, m.decals)):
        for item in raw.get(kind, []):
            thing = _thing(item, table, key)
            if thing is None:
                continue
            target.append(thing)
            spec = table[thing.key]
            if kind == "objects" and spec.get("blocks"):
                rect = thing.rect
                share = float(spec.get("trunk", 1.0))
                if share < 1.0:  # only the centre blocks (tree trunk)
                    c = rect.center
                    hw, hh = (rect.x1 - rect.x0) * share / 2, (rect.y1 - rect.y0) * share / 2
                    rect = Rect(c.x - hw, c.y - hh, c.x + hw, c.y + hh)
                m.walls.append(Wall(rect, int(spec.get("pen", 1)), bool(spec.get("sight", True)),
                                    int(spec.get("height", 2)), "obj:" + thing.key, bool(spec.get("buy_phase_only", False)),
                                    bool(spec.get("door", False))))
            elif kind == "objects" and spec.get("sight_only"):
                m.walls.append(Wall(thing.rect, 0, True, 2, "obj:" + thing.key, False, False, False))
    m.practice_targets = [(Vec(*t["pos"]), float(t.get("move", 0.0))) for t in raw.get("practice_targets", [])]
    m.floor = str(raw.get("floor", ""))
    m.floors = [(str(f["mat"]), _rect(f["rect"])) for f in raw.get("floors", [])]
    for b in raw.get("crates", []):
        m.walls.append(Wall(_rect(b), 1, False, 1))
    m.platforms = [Platform(_rect(p["rect"]), int(p.get("level", 1))) if isinstance(p, dict) else Platform(_rect(p))
                   for p in raw.get("platforms", [])]
    m.walls += [Wall(pl.rect, 1, False, 1) for pl in m.platforms]
    m.ramps = [_rect(r) for r in raw.get("ramps", [])]
    m.sites = [Site(s["name"], _rect(s["rect"])) for s in raw.get("sites", [])]
    m.spawns = {int(t): [Vec(*p) for p in pts] for t, pts in raw.get("spawns", {}).items()}
    m.spawn_zones = {int(t): _rect(r) for t, r in raw.get("spawn_zones", {}).items()}
    m.callouts = [(c["name"], _rect(c["rect"])) for c in raw.get("callouts", [])]
    return m
