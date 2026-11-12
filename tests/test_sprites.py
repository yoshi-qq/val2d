"""Tests for the character state resolver (docs/design/CHARACTER_SHEETS.md), headless."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame

from gameplay.match import PLAYABLE_AGENT_KEYS
from sprite_bank import CharacterSprites, SpriteBank


def chars() -> CharacterSprites:
    pygame.init()
    return CharacterSprites(SpriteBank())


def test_spec_is_read() -> None:
    c = chars()
    assert c.states["cast_x"][2] == "cast"
    assert c.states["channel_q"][2] == "cast_q"


def test_required_cast_slots_exist_for_omen() -> None:
    c = chars()
    for slot in "cqex":
        found = c.resolve("omen", f"cast_{slot}", enemy=False)
        assert found is not None and found[1] == f"cast_{slot}"


def test_optional_state_falls_back() -> None:
    c = chars()
    found = c.resolve("omen", "mech_does_not_exist", enemy=False)
    assert found is not None and found[1] == "idle"
    found = c.resolve("omen", "channel_c", enemy=True)
    assert found is not None and found[1] in ("channel_c", "cast_c")


def test_unknown_form_uses_normal_sprite() -> None:
    c = chars()
    plain = c.resolve("omen", "walk", enemy=False)
    assert c.resolve("omen", "walk", enemy=False, form="nope") == plain


def test_frame_sizes_follow_cells() -> None:
    c = chars()
    assert c.frame("omen", "idle", False, 32, 0.0).get_size() == (32, 64)
    assert c.frame("omen", "dead", False, 32, 0.0).get_size() == (64, 32)


def test_screen_pictures_ignore_enemy_flag() -> None:
    c = chars()
    for tag in ("portrait", "killfeed", "select"):
        found = c.resolve("omen", tag, enemy=True)
        assert found is not None and found[1] == tag and "_enemy" not in found[0]


def test_figure_view_by_relative_facing() -> None:
    from client.characters import figure_view
    assert figure_view(0) == ("back", False)
    assert figure_view(-30) == ("back", False)
    assert figure_view(90) == ("side", False)    # looks right on screen: side sprite as drawn
    assert figure_view(270) == ("side", True)    # looks left: mirrored
    assert figure_view(180) == ("front", False)
    assert figure_view(-180) == ("front", False)


def test_back_and_side_files_win_else_front(tmp_path: Path, monkeypatch) -> None:
    import shutil
    import sprite_bank
    src = sprite_bank.ASSETS / "agents" / "omen"
    dst = tmp_path / "agents" / "omen"
    dst.mkdir(parents=True)
    for name in ("omen_idle.png", "omen_walk.png", "omen_idle_enemy.png"):
        shutil.copy(src / name, dst / name)
    shutil.copy(src / "omen_idle.png", dst / "omen_idle_back.png")
    monkeypatch.setattr(sprite_bank, "ASSETS", tmp_path)
    c = chars()
    assert c.has_view("omen", "idle", False, "back")
    assert c.resolve("omen", "idle", False, view="back") == ("agents/omen/omen_idle_back.png", "idle")
    assert not c.has_view("omen", "idle", True, "back")       # no enemy back view: front view of the enemy
    assert not c.has_view("omen", "walk", False, "side")      # missing side view: front walk
    assert c.resolve("omen", "walk", False, view="side") == ("agents/omen/omen_walk.png", "walk")


def test_playable_agents_have_complete_directional_strips() -> None:
    c = chars()
    excluded = {"dead", "dying", "portrait", "killfeed", "select"}
    for agent in PLAYABLE_AGENT_KEYS:
        for state in c.states.keys() - excluded:
            stem = f"agents/{agent}/{agent}_{state}"
            front = c.bank.raw(f"{stem}.png")
            assert front is not None, (agent, state)
            for view in ("back", "side"):
                for enemy in (False, True):
                    suffix = "_enemy" if enemy else ""
                    path = f"{stem}_{view}{suffix}.png"
                    assert c.resolve(agent, state, enemy, view=view) == (path, state)
                    strip = c.bank.raw(path)
                    assert strip is not None and strip.get_size() == front.get_size(), path
