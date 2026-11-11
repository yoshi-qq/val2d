"""Tests for the character state resolver (docs/design/CHARACTER_SHEETS.md), headless."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame

from sprite_bank import CharacterSprites, SpriteBank


def chars() -> CharacterSprites:
    pygame.init()
    return CharacterSprites(SpriteBank())


def test_spec_is_read() -> None:
    c = chars()
    assert c.states["cast_x"][2] == "cast"
    assert c.states["channel_q"][2] == "cast_q"


def test_required_cast_slots_exist_for_kestrel() -> None:
    c = chars()
    for slot in "cqex":
        found = c.resolve("kestrel", f"cast_{slot}", enemy=False)
        assert found is not None and found[1] == f"cast_{slot}"


def test_optional_state_falls_back() -> None:
    c = chars()
    found = c.resolve("kestrel", "mech_does_not_exist", enemy=False)
    assert found is not None and found[1] == "idle"
    found = c.resolve("kestrel", "channel_c", enemy=True)
    assert found is not None and found[1] in ("channel_c", "cast_c")


def test_unknown_form_uses_normal_sprite() -> None:
    c = chars()
    plain = c.resolve("kestrel", "walk", enemy=False)
    assert c.resolve("kestrel", "walk", enemy=False, form="nope") == plain


def test_frame_sizes_follow_cells() -> None:
    c = chars()
    assert c.frame("kestrel", "idle", False, 32, 0.0).get_size() == (32, 64)
    assert c.frame("kestrel", "dead", False, 32, 0.0).get_size() == (64, 32)


def test_screen_pictures_ignore_enemy_flag() -> None:
    c = chars()
    for tag in ("portrait", "killfeed", "select"):
        found = c.resolve("kestrel", tag, enemy=True)
        assert found is not None and found[1] == tag and "_feind" not in found[0]
