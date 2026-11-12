"""A whole match through the game client to the end: bots on both sides, every frame stepped and drawn now and then;
the result lands in the match history and the Career page shows it. Plus: no spawn sees the enemy spawn."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from gameplay.geometry import Vec  # noqa: E402
from gameplay.match import Command, Match  # noqa: E402
from gameplay.world import load_map, map_keys  # noqa: E402


@pytest.mark.parametrize("key", [k for k in map_keys() if k != "range"])
def test_no_spawn_sees_the_enemy_spawn(key: str) -> None:
    w = load_map(key)
    m = Match(w)
    zones = w.spawn_zones
    pts = {t: [Vec(x + 0.5, y + 0.5) for x in range(int(z.x0), int(z.x1)) for y in range(int(z.y0), int(z.y1))] for t, z in zones.items()}
    clear = [(a, b) for a in pts[0][::3] for b in pts[1][::3] if m._line_clear(a, b, 0, ignore_effects=True)]
    assert not clear, f"{key}: spawns see each other, e.g. {clear[:2]}"


def test_whole_match_to_the_end_is_recorded_for_the_career_page(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from test_client import args  # tests/ is on the path under pytest
    from client import history
    from client.game import Game
    monkeypatch.setattr(history, "HISTORY_PATH", tmp_path / "history.json")
    game = Game(args(team_size=2))
    game.match.set_rules(win_rounds=2, overtime=False)
    game.match.players[game.me].is_bot = True  # the own player is played by a bot as well
    from gameplay.bots import BotDirector
    game.bots = BotDirector(game.match)
    game.start_from_lobby()
    for i in range(30 * 60 * 8):
        events = game.step(1 / 30, Command())
        game.handle_events(events)
        if game.match.phase == "over" and not game.recorded:
            history.record(game.match, game.me, game.score_of)
            game.recorded = True
        if i % 90 == 0 or game.match.phase == "over":
            game.draw()
        if game.match.phase == "over":
            break
    assert game.match.phase == "over"
    data = history.load()
    assert len(data) == 1 and max(data[0]["score"]) == 2
    from menu import MainMenu
    import pygame
    menu = MainMenu(game.screen, pygame.font.Font(None, 22), pygame.font.Font(None, 22), args(no_menu=False))
    menu.tab = "career"
    menu.draw()
    assert any(h.action == "career:0" for h in menu.ui.hits)
    menu.activate("career:0")
    menu.draw()
    assert any(h.action == "career_back" for h in menu.ui.hits)
