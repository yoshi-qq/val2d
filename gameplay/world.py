"""Map: walls, crates, levels, bomb sites, spawns. Own maps, no recreations."""
from __future__ import annotations

import json
import warnings
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

    def floor_level(self, p: Vec) -> int:
        """Level of the surface under a point (crates count as level 1)."""
        level = 0
        for pl in self.platforms:
            if pl.rect.contains(p):
                level = max(level, pl.level)
        for w in self.walls:
            if w.height == 1 and w.rect.contains(p):
                level = max(level, 1)
        return level

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
        return [w for w in self.walls if w.height > level]

    def sight_walls(self, level: int) -> list[Wall]:
        return [w for w in self.walls if w.blocks_sight and w.height > level]


def load_materials() -> tuple[dict[str, dict], dict[str, str]]:
    """(WALLS, FLOORS) from config/materials.py; empty if unreadable."""
    from gameplay.data import ROOT, _load_py
    path = ROOT / "config" / "materials.py"
    return dict(_load_py(path, "WALLS") or {}), dict(_load_py(path, "FLOORS") or {})


def _rect(v: list[float]) -> Rect:
    x0, y0, x1, y1 = v
    return Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def load_map(key: str) -> WorldMap:
    path = MAP_DIR / f"{key}.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.warn(f"Map {key} unreadable ({exc}); using an empty practice area.")
        return WorldMap(key="empty", name="Empty area", width=40, height=40,
                        spawns={0: [Vec(20, 4)], 1: [Vec(20, 36)]},
                        spawn_zones={0: Rect(15, 0, 25, 8), 1: Rect(15, 32, 25, 40)},
                        sites=[Site("A", Rect(16, 16, 24, 24))])
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
    m.floor = str(raw.get("floor", ""))
    m.floors = [(str(f["mat"]), _rect(f["rect"])) for f in raw.get("floors", [])]
    for b in raw.get("crates", []):
        m.walls.append(Wall(_rect(b), 1, False, 1))
    m.platforms = [Platform(_rect(p)) for p in raw.get("platforms", [])]
    m.walls += [Wall(pl.rect, 1, False, 1) for pl in m.platforms]
    m.ramps = [_rect(r) for r in raw.get("ramps", [])]
    m.sites = [Site(s["name"], _rect(s["rect"])) for s in raw.get("sites", [])]
    m.spawns = {int(t): [Vec(*p) for p in pts] for t, pts in raw.get("spawns", {}).items()}
    m.spawn_zones = {int(t): _rect(r) for t, r in raw.get("spawn_zones", {}).items()}
    m.callouts = [(c["name"], _rect(c["rect"])) for c in raw.get("callouts", [])]
    return m
