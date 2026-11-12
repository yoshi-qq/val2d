"""Per-player settings (not game values): stored in ~/.val2d/settings.json, defaults from config/game_config.json.

Game values that Christian tunes stay in config/; this file only holds a player's own preferences.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

from gameplay.data import load_config

SETTINGS_PATH = Path.home() / ".val2d" / "settings.json"
LIMITS: dict[str, tuple[float, float]] = {"sensitivity": (0.05, 1.0), "camera_push": (0.0, 0.8), "volume": (0.0, 1.0)}


def defaults() -> dict[str, Any]:
    cfg = load_config()
    return {"sensitivity": cfg.player.sensitivity, "camera_push": cfg.player.camera_push, "volume": 0.8,
            "name": "Player", "all_around": cfg.lobby.all_around_sight, "sound_rings": cfg.lobby.sound_rings,
            "fullscreen": False}


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
                elif key in ("all_around", "sound_rings", "fullscreen") and isinstance(value, bool):
                    values[key] = value
    except (OSError, json.JSONDecodeError) as exc:
        warnings.warn(f"Settings unreadable ({exc}); using defaults.")
    return values


def save(values: dict[str, Any]) -> None:
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(json.dumps(values, indent=2), encoding="utf-8")
    except OSError as exc:
        warnings.warn(f"Settings not saved: {exc}")
