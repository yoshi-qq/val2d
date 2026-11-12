"""Loads game values (config/rules/, config/content/weapons.py) and the settings Christian tunes (config/settings/)."""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
CONFIG_DIR = ROOT / "config"
CONTENT_DIR = CONFIG_DIR / "content"
SETTINGS_DIR = CONFIG_DIR / "settings"
RULES_DIR = CONFIG_DIR / "rules"
CLIENT_DIR = CONFIG_DIR / "client"
WEAPONS_PATH = CONTENT_DIR / "weapons.py"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.warn(f"{path.name} unreadable ({exc}); defaults apply.")
        return {}


def _load_py(path: Path, name: str) -> Any:
    """Reads a variable from a Python config file (config/**/*.py). Errors warn and give None."""
    import runpy
    try:
        return runpy.run_path(str(path)).get(name)
    except Exception as exc:  # a broken config file must not crash the game
        warnings.warn(f"{path.name} unreadable ({exc}); {name} empty.")
        return None


def load_folder(folder: Path, name: str) -> dict[str, Any]:
    """Merges the dict `name` of every *.py in a config folder (files starting with _ are skipped).
    Sections of the same name in two files are merged key by key; a later file wins on equal keys (with a warning)."""
    out: dict[str, Any] = {}
    if not folder.is_dir():
        warnings.warn(f"Config folder {folder.name} missing; defaults apply.")
        return out
    for path in sorted(folder.glob("*.py")):
        if path.name.startswith("_"):
            continue
        part = _load_py(path, name)
        if not isinstance(part, dict):
            continue
        for section, values in part.items():
            if isinstance(values, dict) and isinstance(out.get(section), dict):
                clash = set(values) & set(out[section])
                if clash:
                    warnings.warn(f"{path.name}: {section} {sorted(clash)} set twice; this file wins.")
                out[section] = {**out[section], **values}
            else:
                out[section] = values
    return out


@dataclass(frozen=True)
class WeaponDef:
    key: str
    name: str
    slot: str
    price: int
    auto: bool
    rate: float
    mag: int
    reserve: int
    reload: float
    equip: float
    speed_mod: float
    penetration: int
    pellets: int
    range: float
    damage: tuple[tuple[float, int, int, int], ...]
    spread_first: float
    spread_run: float
    spray_step: float
    spray_max: float
    spray_recovery: float
    burst: bool = False
    silenced: bool = False
    rate_ramp: tuple[float, float] | None = None  # (max_rate, seconds of held fire to reach it)
    category: str = ""  # buy-menu column
    alt: tuple[tuple[str, Any], ...] = ()  # alternate fire settings (key, value) pairs; see config/content/weapons.py
    spread_unscoped: float = 0.0  # extra spread of a scoped weapon fired without its scope
    backstab: float = 1.0         # melee: damage factor from behind

    def zoom_levels(self) -> list[float]:
        """Zoom factors of the alternate fire; empty if it does not zoom."""
        if self.alt_get("kind") != "zoom":
            return []
        levels = self.alt_get("levels")
        return [float(x) for x in levels] if levels else [float(self.alt_get("factor", 1.25))]

    def zoom_after(self, level: int, alt_down: bool, alt_was_down: bool) -> int:
        """Zoom level after this frame: hold to aim, or (scopes) one more level per press, back to 0 after the last."""
        levels = self.zoom_levels()
        if not levels:
            return 0
        if not self.alt_get("scope"):
            return 1 if alt_down else 0
        if alt_down and not alt_was_down:
            return (level + 1) % (len(levels) + 1)
        return level

    def alt_get(self, key: str, default: Any = None) -> Any:
        return dict(self.alt).get(key, default)

    def damage_at(self, distance: float, zone: str) -> int:
        idx = {"head": 1, "body": 2, "legs": 3}[zone]
        for step in self.damage:
            if distance <= step[0]:
                return int(step[idx])
        return int(self.damage[-1][idx])

    @property
    def is_gun(self) -> bool:
        return self.slot != "melee"


@dataclass(frozen=True)
class ArmorDef:
    key: str
    name: str
    price: int
    points: int


@dataclass(frozen=True)
class HitZoneConfig:
    head_half_width: float = 0.25
    body_half_width: float = 0.375
    legs_half_width: float = 0.22
    head_depth_tolerance: float = 1.2
    body_depth_tolerance: float = 3.0


@dataclass(frozen=True)
class LobbySettings:
    all_around_sight: bool = False
    sound_rings: bool = False
    win_rounds: int = 13
    overtime: bool = True
    team_size: int = 1


@dataclass(frozen=True)
class PlayerSettings:
    camera_push: float = 0.35
    sensitivity: float = 0.25
    enemy_highlight: str = "#ee4c4a"


@dataclass(frozen=True)
class GameConfig:
    hit_zones: HitZoneConfig = field(default_factory=HitZoneConfig)
    lobby: LobbySettings = field(default_factory=LobbySettings)
    player: PlayerSettings = field(default_factory=PlayerSettings)


def _pick(cls: type, raw: dict[str, Any] | None) -> Any:
    raw = raw or {}
    names = cls.__dataclass_fields__.keys()
    unknown = set(raw) - set(names)
    if unknown:
        warnings.warn(f"Unknown entries in {cls.__name__}: {sorted(unknown)}")
    return cls(**{k: v for k, v in raw.items() if k in names})


@lru_cache(maxsize=1)
def load_config() -> GameConfig:
    raw = load_folder(SETTINGS_DIR, "CONFIG")
    return GameConfig(
        hit_zones=_pick(HitZoneConfig, raw.get("hit_zones")),
        lobby=_pick(LobbySettings, raw.get("lobby_defaults")),
        player=_pick(PlayerSettings, raw.get("player_defaults")),
    )


@lru_cache(maxsize=1)
def load_weapons() -> dict[str, WeaponDef]:
    raw = _load_py(WEAPONS_PATH, "WEAPONS") or {}
    out: dict[str, WeaponDef] = {}
    for key, w in raw.items():
        try:
            step, top, rec = w["spray"]
            out[key] = WeaponDef(
                key=key, name=w["name"], slot=w["slot"], price=int(w["price"]), auto=bool(w["auto"]),
                rate=float(w["rate"]), mag=int(w["mag"]), reserve=int(w["reserve"]), reload=float(w["reload"]),
                equip=float(w["equip"]), speed_mod=float(w["speed_mod"]), penetration=int(w["penetration"]),
                pellets=int(w["pellets"]), range=float(w["range"]),
                damage=tuple(tuple(s) for s in w["damage"]),  # type: ignore[misc]
                spread_first=float(w["spread_first"]), spread_run=float(w["spread_run"]),
                spray_step=float(step), spray_max=float(top), spray_recovery=float(rec),
                burst=bool(w.get("burst", False)), silenced=bool(w.get("silenced", False)),
                rate_ramp=(float(w["rate_ramp"][0]), float(w["rate_ramp"][1])) if w.get("rate_ramp") else None,
                category=str(w.get("category", w["slot"])),
                alt=tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in dict(w.get("alt") or {}).items())),
                spread_unscoped=float(w.get("spread_unscoped", 0.0)), backstab=float(w.get("backstab", 1.0)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            warnings.warn(f"Weapon {key} skipped: {exc}")
    return out


@lru_cache(maxsize=1)
def load_armor() -> dict[str, ArmorDef]:
    raw = _load_py(WEAPONS_PATH, "ARMOR") or {}
    return {k: ArmorDef(k, a["name"], int(a["price"]), int(a["points"])) for k, a in raw.items()}


@lru_cache(maxsize=1)
def load_rules() -> dict[str, Any]:
    return load_folder(RULES_DIR, "RULES")


def rule(section: str, key: str, default: Any) -> Any:
    value = load_rules().get(section, {}).get(key)
    if value is None:
        warnings.warn(f"Rule value {section}.{key} missing; using {default}.")
        return default
    return value
