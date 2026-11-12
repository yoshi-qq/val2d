"""Shared imports, colours, constants, small types and the sound player of the game client."""
from __future__ import annotations

import argparse
import sys
import math
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import pygame

from gameplay import abilities
from gameplay.bots import BotDirector
from gameplay.data import LobbySettings, load_config
from gameplay.data import rule as rule_value
from gameplay.geometry import Vec, heading
from gameplay.match import Command, Effect, GameEvent, Match, PlayerState
from gameplay.net import apply_snapshot, events_from_json
from gameplay.netgame import DEFAULT_PORT, NetClient, discover
from gameplay.session import HostSession
from gameplay.world import load_map
from sprite_bank import CharacterSprites, SpriteBank, build_map_surface, draw_nine_slice

ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = ROOT / "font" / "fixed_sys.ttf"
VIEW_METERS = 30.0

C_BG = (22, 21, 28)
C_FLOOR = (52, 50, 60)
C_WALL = (110, 106, 120)
C_WALL_THIN = (138, 120, 96)
C_CRATE = (77, 106, 119)
C_PLATFORM = (70, 68, 82)
C_RAMP = (90, 86, 100)
C_SITE = (224, 180, 55)
C_ALLY = (79, 214, 200)
C_ENEMY = (238, 76, 74)
C_TEXT = (232, 230, 239)
C_MUTED = (155, 152, 170)
C_SMOKE = (150, 150, 170)


@dataclass
class Tracer:
    a: Vec
    b: Vec
    until: float
    own: bool


@dataclass
class Ring:
    pos: Vec
    radius: float
    start: float


@dataclass
class UiState:
    buy_open: bool = False
    show_scores: bool = False
    tracers: list[Tracer] = field(default_factory=list)
    rings: list[Ring] = field(default_factory=list)
    feed: list[tuple[float, str, str | None, str | None, bool]] = field(default_factory=list)  # until, text, killer agent, victim agent, head
    banner: tuple[float, str] = (0.0, "")
    banner_art: str = ""  # file name under assets/ui/banner/ shown above the banner text
    hit_marker: float = 0.0
    last_shot: dict[int, float] = field(default_factory=dict)
    last_cast: dict[int, tuple[float, str]] = field(default_factory=dict)  # pid -> (time, slot)
    last_hit: dict[int, float] = field(default_factory=dict)
    died_at: dict[int, float] = field(default_factory=dict)
    landed_at: dict[int, float] = field(default_factory=dict)
    prev_z: dict[int, float] = field(default_factory=dict)
    blasts: list[tuple[Vec, float, float]] = field(default_factory=list)  # pos, radius, start
    oneshots: list[tuple[str, Vec, float, float, int, tuple[float, float]]] = field(default_factory=list)
    # (file, world pos, start, duration, frame width in px, size in metres)
    scorches: list[tuple[Vec, float]] = field(default_factory=list)       # pos, until
    figure_fx: list[tuple[int, str, float, float]] = field(default_factory=list)  # pid, fx file, start, duration
    waves: list[tuple[int, Vec, float]] = field(default_factory=list)      # pid, end point, start


STATUS_TINT = {"slow": (150, 110, 220), "decay": (120, 200, 90), "vulnerable": (230, 120, 80), "deaf": (120, 160, 230),
               "suppress": (200, 80, 160), "nearsight": (90, 80, 120), "concuss": (230, 210, 90), "detain": (200, 200, 200),
               "stim": (90, 220, 160)}


SOUND_DIR = ROOT / "assets" / "sounds"
HEIGHT_DRAW = 0.7  # screen lift per metre of height, as a share of the map scale
def key_codes(names: dict[str, str]) -> dict[str, int]:
    """Action -> pygame key code from the player's bindings; unknown names fall back to the default key."""
    import user_settings
    out: dict[str, int] = {}
    for action, default in user_settings.DEFAULT_KEYS.items():
        for name in (names.get(action, default), default):
            try:
                out[action] = pygame.key.key_code(name)
                break
            except (ValueError, pygame.error):
                warnings.warn(f"Unknown key {name!r} for {action}; using {default}.")
    return out
STEP_SOUND = {"metal_plate": "step_metal", "grate": "step_metal", "grass": "step_soft", "dirt": "step_soft",
              "sand": "step_soft", "gravel": "step_soft", "carpet": "step_soft", "planks": "step_wood"}
SHOT_SOUND = {"sidearm": "shot_pistol", "smg": "shot_smg", "shotgun": "shot_shotgun", "rifle": "shot_rifle",
              "sniper": "shot_sniper", "heavy": "shot_heavy", "melee": "knife"}
ABILITY_SOUND = {"smoke": "ab_smoke", "wall": "ab_wall", "vapor_wall": "ab_wall", "flash": "ab_throw", "blast": "ab_throw",
                 "wave": "ab_wave", "sensor": "ab_sensor", "alarm": "ab_alarm", "tripwire": "ab_trap", "dash": "ab_dash",
                 "hop": "ab_hop", "teleport": "ab_teleport", "anchor": "ab_teleport", "heal": "ab_heal", "shield": "ab_shield",
                 "revive": "ab_revive", "stim": "ab_stim", "reveal_all": "ab_reveal", "decoy": "ab_decoy", "zone": "ab_zone",
                 "slow_field": "ab_zone", "overdrive": "ab_power", "immunity": "ab_power"}


class Sound:
    """Sound effects from assets/sounds (made by tools/make_sounds.py) with stereo panning, distance falloff and
    muffling behind walls. Missing files are skipped with one warning; no sound device means silent play."""

    def __init__(self) -> None:
        self.ok = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.volume = 0.8
        self._warned: set[str] = set()
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
            pygame.mixer.set_num_channels(48)
            for path in sorted(SOUND_DIR.glob("*.wav")):
                self.sounds[path.stem] = pygame.mixer.Sound(str(path))
            self.ok = True
        except Exception as exc:  # sound is not essential to play
            warnings.warn(f"Sound disabled: {exc}")

    def play(self, key: str, listener: PlayerState | None = None, pos: Vec | None = None, radius: float = 40.0,
             occluded: bool = False, gain: float = 1.0) -> None:
        if not self.ok:
            return
        snd = self.sounds.get(key)
        if snd is None:
            if key not in self._warned:
                self._warned.add(key)
                warnings.warn(f"Sound missing: assets/sounds/{key}.wav")
            return
        left = right = 0.5
        if listener is not None and pos is not None:
            rel = (pos - listener.pos).rotated(-listener.facing)  # x: right of the view, y: ahead
            dist = rel.length()
            vol = max(0.0, 1.0 - dist / max(radius, 1.0)) ** 1.6
            if occluded:
                vol *= 0.45
            if dist > 0.3:
                side = max(-1.0, min(1.0, rel.x / dist))       # -1 full left … 1 full right
                if rel.y < 0:
                    vol *= 0.7 + 0.3 * abs(side)                # behind: a little quieter, so front and back differ
                angle = (side + 1.0) * math.pi / 4.0            # equal-power pan, nearly full separation
                left, right = vol * math.cos(angle) * 1.35, vol * math.sin(angle) * 1.35
            else:
                left = right = vol * 0.9
        left, right = left * gain * self.volume, right * gain * self.volume
        if left + right < 0.01:
            return
        ch = snd.play()
        if ch:
            ch.set_volume(min(1.0, left), min(1.0, right))




def display_mode(fullscreen: bool) -> pygame.Surface:
    """1280x720 game area; fullscreen scales it to the monitor (nearest, keeps the pixel look)."""
    flags = (pygame.FULLSCREEN | pygame.SCALED) if fullscreen else 0
    try:
        return pygame.display.set_mode((1280, 720), flags)
    except pygame.error as exc:
        warnings.warn(f"Fullscreen not available ({exc}); using a window.")
        return pygame.display.set_mode((1280, 720))


__all__ = ['display_mode', 'ABILITY_SOUND', 'BotDirector', 'C_ALLY', 'C_BG', 'C_CRATE', 'C_ENEMY', 'C_FLOOR', 'C_MUTED', 'C_PLATFORM', 'C_RAMP', 'C_SITE', 'C_SMOKE', 'C_TEXT', 'C_WALL', 'C_WALL_THIN', 'CharacterSprites', 'Command', 'DEFAULT_PORT', 'Effect', 'FONT_PATH', 'GameEvent', 'HEIGHT_DRAW', 'HostSession', 'LobbySettings', 'Match', 'NetClient', 'Path', 'PlayerState', 'ROOT', 'Ring', 'SHOT_SOUND', 'SOUND_DIR', 'STATUS_TINT', 'STEP_SOUND', 'Sound', 'SpriteBank', 'Tracer', 'UiState', 'VIEW_METERS', 'Vec', 'abilities', 'apply_snapshot', 'argparse', 'build_map_surface', 'dataclass', 'discover', 'draw_nine_slice', 'events_from_json', 'field', 'heading', 'key_codes', 'load_config', 'load_map', 'math', 'pygame', 'rule_value', 'sys', 'warnings']
