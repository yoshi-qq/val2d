"""Loads game values (gameplay/data) and the game config (config/game_config.json)."""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
CONFIG_PATH = ROOT / "config" / "game_config.json"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.warn(f"{path.name} unreadable ({exc}); defaults apply.")
        return {}


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
    raw = _load_json(CONFIG_PATH)
    return GameConfig(
        hit_zones=_pick(HitZoneConfig, raw.get("hit_zones")),
        lobby=_pick(LobbySettings, raw.get("lobby_defaults")),
        player=_pick(PlayerSettings, raw.get("player_defaults")),
    )


@lru_cache(maxsize=1)
def load_weapons() -> dict[str, WeaponDef]:
    raw = _load_json(DATA_DIR / "weapons.json").get("weapons", {})
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
            )
        except (KeyError, TypeError, ValueError) as exc:
            warnings.warn(f"Weapon {key} skipped: {exc}")
    return out


@lru_cache(maxsize=1)
def load_armor() -> dict[str, ArmorDef]:
    raw = _load_json(DATA_DIR / "weapons.json").get("armor", {})
    return {k: ArmorDef(k, a["name"], int(a["price"]), int(a["points"])) for k, a in raw.items()}


@lru_cache(maxsize=1)
def load_rules() -> dict[str, Any]:
    return _load_json(DATA_DIR / "rules.json")


def rule(section: str, key: str, default: Any) -> Any:
    value = load_rules().get(section, {}).get(key)
    if value is None:
        warnings.warn(f"Regelwert {section}.{key} fehlt; nutze {default}.")
        return default
    return value
