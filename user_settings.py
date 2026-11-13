"""Per-player settings (not game values): stored in ~/.val2d/settings.json, defaults from config/settings/.

Game values that Christian tunes stay in config/; this file only holds a player's own preferences.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

from gameplay.data import load_config, load_weapons
from gameplay.skins import clean_loadout

SETTINGS_PATH = Path.home() / ".val2d" / "settings.json"
LIMITS: dict[str, tuple[float, float]] = {"sensitivity": (0.05, 1.0), "camera_push": (0.0, 0.8), "volume": (0.0, 1.0),
                                          "crosshair_size": (0.5, 2.5), "crosshair_gap": (0.0, 12.0)}
# action -> key name as pygame.key.name() spells it
DEFAULT_KEYS: dict[str, str] = {
    "forward": "w", "back": "s", "left": "a", "right": "d", "walk": "left shift", "crouch": "left ctrl", "jump": "space",
    "reload": "r", "interact": "f", "drop": "g", "buy": "b", "scoreboard": "tab",
    "ability_c": "c", "ability_q": "q", "ability_e": "e", "ability_x": "x",
    "primary": "1", "sidearm": "2", "melee": "3", "spike": "4",
}
CROSSHAIR_COLORS = ["#78ffc8", "#ffffff", "#ffe14d", "#ff5ad2", "#5ad2ff", "#ff6b4d"]


def defaults() -> dict[str, Any]:
    cfg = load_config()
    return {"sensitivity": cfg.player.sensitivity, "camera_push": cfg.player.camera_push, "volume": 0.55,
            "name": "Player", "last_join": "",
            "fullscreen": False, "keys": dict(DEFAULT_KEYS), "weapon_skins": {}, "crosshair_color": CROSSHAIR_COLORS[0],
            "crosshair_size": 1.0, "crosshair_gap": 4.0, "crosshair_dot": True}


def clamp(key: str, value: float) -> float:
    low, high = LIMITS[key]
    return max(low, min(high, float(value)))


def load() -> dict[str, Any]:
    values = defaults()
    try:
        if SETTINGS_PATH.exists():
            raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            for key, value in raw.items():
                if key in LIMITS and isinstance(value, (int, float)):
                    values[key] = clamp(key, value)
                elif key == "name" and isinstance(value, str):
                    values[key] = value[:16] or "Player"
                elif key == "last_join" and isinstance(value, str):
                    values[key] = value.strip()[:128]
                elif key in ("fullscreen", "crosshair_dot") and isinstance(value, bool):
                    values[key] = value
                elif key == "crosshair_color" and isinstance(value, str) and len(value) == 7 and value.startswith("#"):
                    values[key] = value
                elif key == "keys" and isinstance(value, dict):
                    values["keys"].update({a: str(k) for a, k in value.items() if a in DEFAULT_KEYS and isinstance(k, str)})
                elif key == "weapon_skins":
                    values[key] = clean_loadout(value, load_weapons())
    except (OSError, json.JSONDecodeError) as exc:
        warnings.warn(f"Settings unreadable ({exc}); using defaults.")
    return values


def save(values: dict[str, Any]) -> None:
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(json.dumps(values, indent=2), encoding="utf-8")
    except OSError as exc:
        warnings.warn(f"Settings not saved: {exc}")
