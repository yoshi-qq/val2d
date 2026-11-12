"""Headless smoke tests of the game client: menu, a local match drawn frame by frame, overlays."""
from __future__ import annotations

import argparse
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from client.game import Game  # noqa: E402


def args(**over: object) -> argparse.Namespace:
    base = dict(agent="kestrel", team_size=2, rounds=13, map="werkhof", all_around=False, sound_rings=False, name="Tester",
                host=False, host_online=False, join=None, find=False, port=9009, no_menu=True, practice=False,
                mode="standard", online=False)
    base.update(over)
    return argparse.Namespace(**base)


def frames(game: Game, n: int) -> None:
    from gameplay.match import Command
    for _ in range(n):
        events = game.step(1 / 60, Command())
        game.handle_events(events)
        game.draw()


def test_menu_opens_and_lists_maps() -> None:
    from menu import MainMenu
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    font = pygame.font.Font(None, 22)
    menu = MainMenu(screen, font, font, args())
    assert "werkhof" in menu.maps
    menu.draw()


def test_local_match_draws_buy_and_live_frames() -> None:
    game = Game(args())
    game.match.start()
    frames(game, 30)
    game.match.phase_until = game.match.time  # skip the buy phase
    frames(game, 60)
    assert game.match.phase in ("live", "planted", "end")


def test_practice_range_draws() -> None:
    game = Game(args(practice=True))
    game.match.start_practice()
    frames(game, 20)


def test_menu_start_path_local_and_range() -> None:
    """The real path: main menu builds the arguments, the game starts from them and draws."""
    from menu import MainMenu
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    font = pygame.font.Font(None, 22)
    for action in ("local", "range"):
        menu = MainMenu(screen, font, font, args(no_menu=False))
        chosen = menu.activate(action)
        assert chosen is not None and chosen is not False
        game = Game(chosen)
        if game.practice:
            game.match.start_practice()
        else:
            game.match.start()
        frames(game, 10)
