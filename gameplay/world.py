"""Map: walls, crates, levels, bomb sites, spawns."""
from __future__ import annotations

import json
import warnings
from functools import lru_cache
from dataclasses import dataclass, field, replace
from pathlib import Path

from gameplay.geometry import Rect, Vec

MAP_DIR = Path(__file__).resolve().parent / "data" / "maps"


@dataclass(frozen=True)
class Wall:
    rect: Rect
    penetration: int  # material: 0 thin, 1 medium, 2 thick, 3 impenetrable
    blocks_sight: bool = True
    height: int = 2  # levels; crates have 1 and can be climbed
    material: str = ""  # key in config/content/materials.py WALLS (decides the tile)
    buy_phase_only: bool = False  # blocks only during the buy phase (spawn barrier)
    door: bool = False  # can be opened; then it blocks nothing
    solid: bool = True  # False: blocks only sight (bushes), never movement or bullets
    low: bool = False   # lower than head height: players see and shoot over it (barrels, benches)
    base: float = 0.0   # level of the floor it stands on (crates on a raised site, platform sides)

    hp: int = 0
    switch: Vec | None = None
    on_deck: bool = False
    reopenable: bool = True
    ceiling: float | None = None
    movement_only: bool = False

    @property
    def full(self) -> bool:
        """Full-height walls are taller than every floor level: never climbed, seen or shot over."""
        return self.ceiling is None and self.height >= FULL_HEIGHT

    @property
    def top(self) -> float:
        """Absolute level of the top edge (infinite for full walls)."""
        if self.ceiling is not None:
            return self.ceiling
        return float("inf") if self.full else self.base + self.height


FULL_HEIGHT = 2  # walls this many levels high are full walls
PLATFORM = "platform"  # material of the walls that stand for platform sides (floor, not cover)


@dataclass(frozen=True)
class MapThing:
    """Placed object or decal: key from config/content/materials.py, rect in metres, rotation in 90° steps."""
    key: str
    rect: Rect
    rot: int = 0


@dataclass(frozen=True)
class Platform:
    """Raised area (level 1 or higher). Ramps connect it to lower floors."""
    rect: Rect
    level: float = 1
    mat: str = ""  # floor material drawn on top (FLOORS key); empty: the shared platform tile


@dataclass(frozen=True)
class Deck:
    """Walkable overhead floor with an optional solid volume beneath it."""
    rect: Rect
    level: float
    lower: float
    closed_below: bool = False
    walkable: bool = True

    @property
    def underside(self) -> float:
        return self.level - 0.2


@dataclass(frozen=True)
class Site:
    name: str
    rect: Rect
    upper: tuple[Rect, ...] = ()
    ground_extra: tuple[Rect, ...] = ()

    @property
    def plant_rects(self) -> tuple[Rect, ...]:
        return (self.rect, *self.ground_extra, *self.upper)


@dataclass(frozen=True)
class Zipline:
    start: Vec
    end: Vec
    level: float
    reach: float
    speed: float
    lower: float | None = None

    def progress(self, point: Vec) -> float:
        axis = self.end - self.start
        return max(0.0, min(1.0, (point - self.start).dot(axis) / axis.dot(axis)))


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
    floor: str = ""  # key in config/content/materials.py FLOORS for the whole map
    art: str = ""    # folder under assets/maps with the map's own tiles (defaults to the key)
    floors: list[tuple[str, Rect]] = field(default_factory=list)  # floor material patches
    objects: list[MapThing] = field(default_factory=list)
    practice_targets: list[tuple[Vec, float]] = field(default_factory=list)  # (position, sideways travel in m)
    decals: list[MapThing] = field(default_factory=list)
    # explicit ramps by index into ramps: (axis it rises along, high end at the smaller coordinate, low, high level)
    ramp_spans: dict[int, tuple[str, bool, float, float]] = field(default_factory=dict)
    decks: list[Deck] = field(default_factory=list)
    teleporters: list[tuple[Rect, Vec]] = field(default_factory=list)  # one-way entry area and destination
    lock_spawn_during_buy: bool = True  # maps with complete barriers can use them as the buy-phase boundary
    orbs: list[Vec] = field(default_factory=list)
    drop_zones: list[tuple[Rect, Vec]] = field(default_factory=list)
    drop_wall_links: dict[Rect, Rect] = field(default_factory=dict)
    buy_teleporters: set[Rect] = field(default_factory=set)
    automatic_doors: dict[Rect, Rect] = field(default_factory=dict)
    timed_doors: dict[Rect, float] = field(default_factory=dict)
    quiet_landings: list[Rect] = field(default_factory=list)
    lintels: list[tuple[Rect, float, float]] = field(default_factory=list)
    ziplines: list[Zipline] = field(default_factory=list)

    def deck_at(self, p: Vec) -> Deck | None:
        return next((deck for deck in self.decks if deck.rect.contains(p)), None)

    def smoke_target_heights(self, point: Vec, under_deck: bool, lift: float) -> tuple[float, float]:
        ground = self.ground_height(point, -float("inf") if under_deck else float("inf"))
        if under_deck and (deck := self.deck_at(point)) is not None:
            lift = min(lift, max(0.0, deck.underside - ground))
        return ground, ground + lift

    def ground_height(self, p: Vec, reach: float = float("inf")) -> float:
        """Height of the surface under a point in levels: platforms at their level, low cover one level above the
        floor it stands on, ramps rising evenly from their low end to the level they lead onto."""
        if self.drop_zones and self.drop_recovery(p) is not None:
            return -8.0
        deck = self.deck_at(p) if self.decks else None
        if deck is not None and (not deck.walkable or reach < deck.level):
            return deck.lower
        h = deck.level if deck is not None else 0.0
        for pl in self.platforms:
            if pl.rect.contains(p):
                h = max(h, float(pl.level))
        for w in self.low_walls():
            if w.rect.contains(p):
                h = max(h, w.top)
        for rect, axis, high_at_min, top, low in self.ramp_profiles():
            if rect.contains(p):
                span = (rect.x1 - rect.x0) if axis == "x" else (rect.y1 - rect.y0)
                along = (p.x - rect.x0) if axis == "x" else (p.y - rect.y0)
                t = along / span if span > 0 else 1.0
                h = max(h, low + (top - low) * ((1.0 - t) if high_at_min else t))
        return h

    def drop_recovery(self, p: Vec) -> Vec | None:
        """Safe edge to return the spike to after it falls into a death drop."""
        return next((safe for rect, safe in self.drop_zones if rect.contains(p)), None)

    def low_walls(self) -> list[Wall]:
        """Solid walls lower than full height (crates, platform sides); cached until the wall list changes."""
        cached = getattr(self, "_low_cache", None)
        if cached is None or cached[0] != len(self.walls):
            cached = (len(self.walls), [w for w in self.walls if not w.full and w.solid])
            self._low_cache = cached
        return cached[1]

    def ramp_profiles(self) -> list[tuple[Rect, str, bool, float, float]]:
        """Per ramp: (rect, axis it rises along, True if the high end is at the smaller coordinate, top, low level)."""
        cached = getattr(self, "_ramp_cache", None)
        if cached is not None:
            return cached
        out: list[tuple[Rect, str, bool, float, float]] = []
        for i, r in enumerate(self.ramps):
            if i in self.ramp_spans:
                axis, high_min, low, high = self.ramp_spans[i]
                out.append((r, axis, high_min, high, low))
                continue
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
            out.append((r, best[1], best[2], best[3], 0.0))
        self._ramp_cache = out
        return out

    def floor_level(self, p: Vec, reach: float = float("inf")) -> int:
        """Level of the surface under a point (rounded ground height)."""
        return int(self.ground_height(p, reach) + 0.5)

    def deck_blocks(self, a: Vec, a_height: float, b: Vec, b_height: float) -> bool:
        """Test sight and shots against horizontal slabs and doorway lintels."""
        for deck in self.decks:
            slab = (deck.underside + deck.level) / 2
            if min(a_height, b_height) < slab < max(a_height, b_height):
                t = (slab - a_height) / (b_height - a_height)
                if deck.rect.contains(a + (b - a) * t):
                    return True
        for rect, bottom, top in self.lintels:
            interval = rect.ray_interval(a, b - a)
            if interval is None:
                continue
            enter, leave = max(0.0, interval[0]), min(1.0, interval[1])
            if enter > leave:
                continue
            rise = b_height - a_height
            low, high = sorted((a_height + rise * enter, a_height + rise * leave))
            if low <= top and high >= bottom:
                return True
        return False

    def floor_material(self, p: Vec) -> str:
        """Floor material key under a point (last matching patch wins), else the map's floor."""
        found = self.floor
        for mat, rect in self.floors:
            if rect.contains(p):
                found = mat
        return found

    def on_ramp(self, p: Vec) -> bool:
        return any(r.contains(p) for r in self.ramps)

    def site_at(self, p: Vec, level: float | None = None) -> Site | None:
        deck = self.deck_at(p) if self.decks and level is not None else None
        upper = deck is not None and level >= int(deck.level + 0.5)
        for s in self.sites:
            if (upper or level is None) and any(rect.contains(p) for rect in s.upper):
                return s
            if (not upper and (s.rect.contains(p) or any(rect.contains(p) for rect in s.ground_extra))
                    and (not s.upper or level is None or level <= self.floor_level(p, level))):
                return s
        return None

    def callout_at(self, p: Vec, level: float = float("inf")) -> str:
        deck = self.deck_at(p) if self.decks else None
        if deck is not None and self.key == "ascent":
            return "A Rafters" if level >= deck.level else "A Hell"
        for name, r in self.callouts:
            if r.contains(p):
                return name
        return ""

    def blocking_walls(self, level: int) -> list[Wall]:
        """Walls that block movement on this level."""
        return [w for w in self.walls if w.top > level and w.solid and (not w.on_deck or w.base <= level)]

    def sight_walls(self, level: int) -> list[Wall]:
        return [w for w in self.walls if w.blocks_sight and w.top > level and not w.low
                and (not w.on_deck or w.base <= level)]


@lru_cache(maxsize=1)
def prop_heights() -> dict[str, float]:
    """Prop heights in metres (config/content/prop_heights.py)."""
    from gameplay.data import CONTENT_DIR, _load_py
    return {str(k): float(v) for k, v in dict(_load_py(CONTENT_DIR / "prop_heights.py", "HEIGHTS") or {}).items()}


def head_height() -> float:
    from gameplay.data import rule
    return float(rule("sight", "head_height", 1.4))


@lru_cache(maxsize=1)
def load_materials() -> tuple[dict[str, dict], dict[str, str]]:
    """(WALLS, FLOORS) from config/content/materials.py; empty if unreadable."""
    from gameplay.data import ROOT, _load_py
    path = ROOT / "config" / "content" / "materials.py"
    return dict(_load_py(path, "WALLS") or {}), dict(_load_py(path, "FLOORS") or {})


@lru_cache(maxsize=1)
def load_things() -> tuple[dict[str, dict], dict[str, dict]]:
    """(OBJECTS, DECALS) from config/content/materials.py; empty if unreadable."""
    from gameplay.data import ROOT, _load_py
    path = ROOT / "config" / "content" / "materials.py"
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


def _floor_under(platforms: list[Platform], rect: Rect) -> float:
    """Level of the highest platform under the centre of a rect (0 on the ground)."""
    c = rect.center
    return float(max((pl.level for pl in platforms if pl.rect.contains(c)), default=0))


def _rect(v: list[float]) -> Rect:
    x0, y0, x1, y1 = v
    return Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


DEFAULT_MAP = "ascent"
PLAYABLE_MAP_KEYS = (
    DEFAULT_MAP, "bind", "haven", "split", "icebox", "breeze", "fracture",
    "pearl", "lotus", "sunset", "abyss", "corrode", "summit",
)
LEGACY_MAP_ART = {"werkhof": "workyard", "gasse": "alley", "hafen": "harbour"}
LEGACY_WALL_MATERIAL = {"werkhof_thick": "workyard_thick", "werkhof_thin": "workyard_thin"}


def map_keys() -> list[str]:
    """All maps: gameplay/data/maps/*.json (map editor) and *.py (built in Python, MAP = ...); _files are skipped."""
    return sorted({
        path.stem
        for pattern in ("*.json", "*.py")
        for path in MAP_DIR.glob(pattern)
        if not path.name.startswith("_")
    })


def load_map_raw(key: str) -> dict:
    """Map data of `key`: the .json if there is one (editor saves win), else MAP from the .py. Raises OSError/ValueError."""
    from gameplay.patches import apply_map
    path = MAP_DIR / f"{key}.json"
    if path.exists():
        return apply_map(key, json.loads(path.read_text(encoding="utf-8")))
    py = MAP_DIR / f"{key}.py"
    if py.exists():
        from gameplay.data import _load_py
        raw = _load_py(py, "MAP")
        if isinstance(raw, dict):
            return apply_map(key, raw)
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


def load_playable_map(key: str) -> WorldMap:
    if key not in PLAYABLE_MAP_KEYS:
        raise OSError(f"Map {key!r} is disabled.")
    return parse_map(key, load_map_raw(key))


def parse_map(key: str, raw: dict) -> WorldMap:
    """Builds a WorldMap from map-file data (also used by the map editor for its preview)."""
    m = WorldMap(key=key, name=raw["name"], width=raw["width"], height=raw["height"])
    w, h = m.width, m.height
    m.walls += [Wall(Rect(-1, -1, w + 1, 0), 3), Wall(Rect(-1, h, w + 1, h + 1), 3),
                Wall(Rect(-1, 0, 0, h), 3), Wall(Rect(w, 0, w + 1, h), 3)]
    mats = load_materials()[0]
    for wl in raw.get("walls", []):
        mat = str(wl.get("mat", ""))
        mat = LEGACY_WALL_MATERIAL.get(mat, mat)
        base = mats.get(mat, {})
        if mat and not base:
            warnings.warn(f"Map {key}: unknown wall material {mat!r}")
        ceiling = wl.get("ceiling")
        m.walls.append(Wall(_rect(wl["rect"]), int(wl.get("pen", base.get("pen", 2))), bool(wl.get("sight", base.get("sight", True))),
                            int(wl.get("height", base.get("height", 2))), mat,
                            low=bool(wl.get("low", base.get("low", False))),
                            base=float(wl.get("deck_level", 0)), on_deck="deck_level" in wl,
                            ceiling=float(ceiling) if ceiling is not None else None))
    objects, decals = load_things()
    for kind, table, target in (("objects", objects, m.objects), ("decals", decals, m.decals)):
        for item in raw.get(kind, []):
            thing = _thing(item, table, key)
            if thing is None:
                continue
            target.append(thing)
            spec = table[thing.key]
            if kind == "objects" and spec.get("door") and "trigger" in item:
                m.automatic_doors[thing.rect] = _rect(item["trigger"])
            if kind == "objects" and spec.get("door") and "close_after" in item:
                m.timed_doors[thing.rect] = float(item["close_after"])
            if kind == "objects" and spec.get("blocks"):
                rect = thing.rect
                share = float(spec.get("trunk", 1.0))
                if share < 1.0:  # only the centre blocks (tree trunk)
                    c = rect.center
                    hw, hh = (rect.x1 - rect.x0) * share / 2, (rect.y1 - rect.y0) * share / 2
                    rect = Rect(c.x - hw, c.y - hh, c.x + hw, c.y + hh)
                height_m = prop_heights().get(thing.key)
                low = height_m is not None and height_m < head_height()
                ceiling = item.get("ceiling")
                m.walls.append(Wall(rect, int(spec.get("pen", 1)), bool(spec.get("sight", True)) and not low,
                                    int(spec.get("height", 2)), "obj:" + thing.key, bool(spec.get("buy_phase_only", False)),
                                    bool(spec.get("door", False)), low=low, hp=int(spec.get("hp", 0)),
                                    switch=Vec(*item["switch"]) if "switch" in item else None,
                                    reopenable=bool(spec.get("reopenable", True)),
                                    ceiling=float(ceiling) if ceiling is not None else None))
            elif kind == "objects" and spec.get("sight_only"):
                m.walls.append(Wall(thing.rect, 0, True, 2, "obj:" + thing.key, False, False, False))
    m.practice_targets = [(Vec(*t["pos"]), float(t.get("move", 0.0))) for t in raw.get("practice_targets", [])]
    m.floor = str(raw.get("floor", ""))
    m.art = str(raw.get("art", key))
    m.art = LEGACY_MAP_ART.get(m.art, m.art)
    m.floors = [(str(f["mat"]), _rect(f["rect"])) for f in raw.get("floors", [])]
    for b in raw.get("crates", []):
        m.walls.append(Wall(_rect(b), 1, False, 1))
    m.platforms = [Platform(_rect(p["rect"]), float(p.get("level", 1)), str(p.get("mat", ""))) if isinstance(p, dict)
                   else Platform(_rect(p)) for p in raw.get("platforms", [])]
    m.decks = [Deck(_rect(d["rect"]), float(d["level"]), float(d["lower"]), bool(d.get("closed_below")),
                    bool(d.get("walkable", True)))
               for d in raw.get("decks", [])]
    # cover stands on the floor under it: a crate on a raised site is one level above that site
    m.walls = [replace(wl, base=_floor_under(m.platforms, wl.rect)) if not wl.full else wl for wl in m.walls]
    for i, wall in enumerate(m.walls):
        deck = m.deck_at(wall.rect.center) if m.decks and wall.material.startswith("obj:") else None
        if deck is not None:
            m.walls[i] = replace(wall, base=deck.level, on_deck=True)
    m.walls += [Wall(pl.rect, 1, False, 1, PLATFORM, base=float(pl.level - 1)) for pl in m.platforms]
    m.walls += [Wall(deck.rect, 3, material="container", ceiling=deck.level)
                for deck in m.decks if deck.closed_below]
    m.ramps = []
    for i, r in enumerate(raw.get("ramps", [])):
        if isinstance(r, dict):
            m.ramps.append(_rect(r["rect"]))
            rise = str(r.get("rise", "n"))  # direction the ramp goes up, map coordinates (n = +y)
            m.ramp_spans[i] = ("y" if rise in ("n", "s") else "x", rise in ("s", "w"),
                               float(r.get("low", 0.0)), float(r.get("high", 1.0)))
        else:
            m.ramps.append(_rect(r))
    m.sites = [Site(s["name"], _rect(s["rect"]), tuple(_rect(r) for r in s.get("upper", [])),
                    tuple(_rect(r) for r in s.get("ground_extra", [])))
               for s in raw.get("sites", [])]
    m.teleporters = [(_rect(t["entry"]), Vec(*t["exit"])) for t in raw.get("teleporters", [])]
    m.buy_teleporters = {_rect(t["entry"]) for t in raw.get("teleporters", []) if t.get("during_buy")}
    m.ziplines = [Zipline(Vec(*z["start"]), Vec(*z["end"]), float(z["level"]), float(z["reach"]), float(z["speed"]),
                         float(z["lower"]) if "lower" in z else None)
                  for z in raw.get("ziplines", [])]
    m.orbs = [Vec(*point) for point in raw.get("orbs", [])]
    m.quiet_landings = [_rect(bounds) for bounds in raw.get("quiet_landings", [])]
    m.lintels = [(_rect(item["rect"]), float(item["bottom"]), float(item["top"]))
                 for item in raw.get("lintels", [])]
    m.drop_zones = [(_rect(zone["rect"]), Vec(*zone["recovery"])) for zone in raw.get("drop_zones", [])]
    m.drop_wall_links = {_rect(link["switch"]): _rect(link["wall"]) for link in raw.get("drop_wall_links", [])}
    m.spawns = {int(t): [Vec(*p) for p in pts] for t, pts in raw.get("spawns", {}).items()}
    m.spawn_zones = {int(t): _rect(r) for t, r in raw.get("spawn_zones", {}).items()}
    m.lock_spawn_during_buy = bool(raw.get("lock_spawn_during_buy", True))
    m.callouts = [(c["name"], _rect(c["rect"])) for c in raw.get("callouts", [])]
    return m
