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


def test_escape_pauses_and_double_alt_f4_quits() -> None:
    game = Game(args())
    game.match.start()
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=41))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    game.run()  # returns once the second Alt+F4 arrives
    assert game.quit_program


def test_escape_opens_pause_and_closes_it_again() -> None:
    game = Game(args())
    game.match.start()
    game.open_overlay("pause")
    game.draw()
    game.draw_overlay()
    assert game.overlay == "pause" and any(h.action == "resume" for h in game.kit.hits)
    game.overlay_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=41))
    assert game.overlay == ""


def test_menu_escape_never_quits_and_alt_f4_asks_first() -> None:
    from menu import MainMenu
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    menu = MainMenu(screen, pygame.font.Font(None, 22), pygame.font.Font(None, 22), args(no_menu=False))
    menu.tab, menu.view = "agents", "settings"
    esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=41)
    assert menu.handle(esc) is None and menu.view == "main"
    assert menu.handle(esc) is None and menu.tab == "play"
    assert menu.handle(esc) is None
    assert menu.handle(pygame.event.Event(pygame.QUIT)) is None and menu.dialog == "quit"
    assert menu.handle(pygame.event.Event(pygame.QUIT)) is False


def test_crosshair_is_symmetric_for_any_size_and_gap() -> None:
    from client.crosshair import shape
    for size in (0.5, 0.73, 1.0, 1.37, 2.5):
        for gap in (0.0, 2.4, 4.0, 7.6, 12.0):
            for center in ((100, 100), (100.5, 99.5), (101.3, 100.7)):
                right, left, down, up, dot = shape(center, size, gap, True)
                cx2 = dot.x * 2 + dot.w  # twice the centre, exact in whole pixels
                cy2 = dot.y * 2 + dot.h
                assert right.x + left.right == cx2 and down.y + up.bottom == cy2
                assert right.size == left.size and down.size == up.size and right.w == down.h


def _post_key(key: int) -> None:
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0))


def test_ability_is_taken_in_hand_cast_with_left_click_and_put_away_with_its_key() -> None:
    game = Game(args(agent="marrow"))
    game.match.start()
    key_e = game.keys["ability_e"]
    before = len(game.match.effects)
    pygame.event.clear()
    _post_key(key_e)          # in hand
    _post_key(key_e)          # same key: put away again
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    game.run()
    assert game.aiming is None and len(game.match.effects) == before
    game2 = Game(args(agent="marrow"))
    game2.match.start()
    before = len(game2.match.effects)
    pygame.event.clear()
    _post_key(key_e)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 360)))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    game2.run()
    assert len(game2.match.effects) == before + 1 and game2.aiming is None


def test_right_click_casts_the_alternative_wall_along_the_aim() -> None:
    from gameplay.geometry import Vec
    from gameplay.match import Command
    game = Game(args(agent="marrow"))
    game.match.start()
    me = game.match.players[game.me]
    me.charges["Q"], me.facing = 1, 0.0
    game.match.tick(1 / 64, {game.me: Command(facing=0.0, cursor_depth=6.0, ability="Q", ability_alt=True)})
    wall = next(e for e in game.match.effects if e.kind == "wall")
    assert abs(wall.a.x - wall.b.x) < 1e-6 and abs(wall.a.y - wall.b.y) > 1.0  # along the aim (aim = +y)


def test_escape_menu_opens_full_settings_and_applies_them() -> None:
    import user_settings
    game = Game(args())
    game.match.start()
    saved = user_settings.load()
    try:
        game.open_overlay("pause")
        game.draw()
        game.draw_overlay()
        settings = next(h for h in game.kit.hits if h.action == "settings")
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            game.overlay_event(pygame.event.Event(kind, button=1, pos=settings.rect.center))
        assert game.overlay == "settings"
        game.settings_panel.settings["sensitivity"] = 0.6
        game.draw_overlay()
        game.overlay_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=41))
        assert game.overlay == "pause" and abs(game.sens - 0.6) < 1e-9
    finally:
        user_settings.save(saved)


def test_match_over_has_a_back_to_menu_button() -> None:
    game = Game(args())
    game.match.start()
    game.match.phase = "over"
    game.draw()
    assert any(h.action == "to_menu" for h in game.kit.hits)
