"""Headless smoke tests of the game client: menu, a local match drawn frame by frame, overlays."""
from __future__ import annotations

import argparse
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from client.game import Game  # noqa: E402


def args(**over: object) -> argparse.Namespace:
    base = dict(agent="omen", team_size=2, rounds=13, map="ascent", all_around=False, sound_rings=False, name="Tester",
                host=False, host_online=False, join=None, find=False, port=9009, no_menu=True, practice=False,
                mode="standard", online=False)
    base.update(over)
    return argparse.Namespace(**base)


@pytest.fixture(autouse=True)
def settings_path(monkeypatch, tmp_path):
    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")


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
    menu = MainMenu(screen, font, font, args(map="workyard", agent="kestrel"))
    assert menu.maps == ["ascent"]
    assert set(menu.agents()) == {"brimstone", "omen", "jett", "sova", "sage", "cypher", "phoenix", "killjoy"}
    assert (menu.args.map, menu.args.agent) == ("ascent", "omen")
    menu.draw()


def test_local_match_draws_buy_and_live_frames() -> None:
    game = Game(args())
    game.match.start()
    frames(game, 30)
    game.match.phase_until = game.match.time  # skip the buy phase
    frames(game, 60)
    assert game.match.phase in ("live", "planted", "end")


@pytest.mark.parametrize("options", [{"map": "workyard"}, {"map": "harbour", "host": True}, {"practice": True}])
def test_custom_maps_are_disabled(options) -> None:
    with pytest.raises(OSError, match="disabled"):
        Game(args(**options))


def test_menu_start_path_local() -> None:
    """The real path: main menu builds the arguments, the game starts from them and draws."""
    from menu import MainMenu
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    font = pygame.font.Font(None, 22)
    menu = MainMenu(screen, font, font, args(no_menu=False))
    chosen = menu.activate("start")
    assert isinstance(chosen, argparse.Namespace)
    game = Game(chosen)
    assert game.match.world.key == "ascent"
    assert all(p.agent in menu.agents() for p in game.match.players.values())
    game.reload_content()
    assert set(game.match.agents) == set(menu.agents())
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


@pytest.mark.parametrize("zoom,scoped", [(0, False), (1, False), (1, True)])
def test_cursor_stops_at_the_view_edge_and_reverses_immediately(zoom, scoped) -> None:
    from gameplay.geometry import heading

    game = Game(args())
    me = game.match.players[game.me]
    game.zoom_level, game.scoped = zoom, scoped
    game.scale *= 1.5 if zoom else 1.0
    game.move_cursor(me, -100_000)
    _, y = game.to_screen(me.pos + heading(me.facing) * game.cursor_depth, me)
    assert y == pytest.approx(game.h / 2 if scoped else 1)
    limit = game.cursor_depth
    game.move_cursor(me, -100_000)
    assert game.cursor_depth == limit
    game.move_cursor(me, 1)
    assert game.cursor_depth == pytest.approx(limit - 0.03)


@pytest.mark.parametrize("level", [1, 2])
def test_scoped_map_rotates_with_world_positions(level) -> None:
    from client.common import VIEW_METERS
    from gameplay.geometry import Vec
    from gameplay.match import WeaponState

    game = Game(args())
    me = game.match.players[game.me]
    me.pos = Vec(10, game.match.world.height - 20)
    me.weapons["primary"] = WeaponState("operator", 5, 10)
    me.slot, me.zoom_level = "primary", level
    game.cursor_depth = 5.0
    game.apply_zoom(me, holding_alt=False)
    assert game.scoped
    base = game.w / VIEW_METERS
    game.map_surface = pygame.Surface((round(25 * base), round(25 * base)))
    marker = Vec(13, me.pos.y + 5)
    color = (240, 40, 140)
    pygame.draw.circle(game.map_surface, color,
                       (round(marker.x * base), round((game.match.world.height - marker.y) * base)), 10)
    previous_x = game.w
    for facing in (25.0, 35.0):
        me.facing = facing
        game.screen.fill((0, 0, 0))
        game.draw_map_texture(me)
        x, y = map(round, game.to_screen(marker, me))
        assert x < previous_x
        assert game.screen.get_at((x, y))[:3] == color
        previous_x = x


@pytest.mark.parametrize("mode", ["local", "client"])
def test_minimap_contacts_require_the_players_own_view(mode) -> None:
    from gameplay.geometry import Rect, Vec
    from gameplay.world import Wall

    game = Game(args())
    game.mode = mode
    match = game.match
    me = match.players[game.me]
    ally = next(p for p in match.players.values() if p.team == me.team and p is not me)
    enemy = next(p for p in match.players.values() if p.team != me.team)
    me.pos, me.facing = Vec(15, 10), 0
    ally.pos, ally.facing = Vec(15, 16), 0
    enemy.visible = True
    match.world.walls = [Wall(Rect(14, 14, 16, 15), 3)]
    enemy.pos = Vec(15, 17)
    assert match.can_see(ally, enemy)
    assert not game.minimap_sees_enemy(me, enemy)
    enemy.pos = Vec(15, 12)
    assert game.minimap_sees_enemy(me, enemy)
    match.world.walls = []
    enemy.pos = Vec(15, 32)
    assert match.can_see(me, enemy)
    assert not game.minimap_sees_enemy(me, enemy)


def test_weapon_wheel_skips_empty_slots_and_hud_shows_the_actual_keys(monkeypatch) -> None:
    from gameplay.match import Command

    game = Game(args(keys={"sidearm": "8"}))
    game.match.start()
    me = game.match.players[game.me]
    assert me.slot == "sidearm" and "primary" not in me.weapons
    cmd = Command()
    game.scroll_weapons(me, cmd, -1)
    assert cmd.slot == "melee"
    game.scroll_weapons(me, cmd, -1)
    assert cmd.slot == "sidearm"

    labels = []
    monkeypatch.setattr(game.kit, "text", lambda label, *args, **kwargs: labels.append(label))
    game.draw_weapon_box(me)
    assert "8" in labels and "3" in labels and "1" not in labels


def test_main_menu_inventory_scrolls_between_pages(monkeypatch) -> None:
    from menu import MainMenu

    monkeypatch.setattr("client.inventory.WEAPONS_PER_PAGE", 2)
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    font = pygame.font.Font(None, 22)
    menu = MainMenu(screen, font, font, args())
    menu.activate("tab:inventory")
    menu.inventory.page = 0
    menu.handle(pygame.event.Event(pygame.MOUSEWHEEL, y=-1))
    assert menu.inventory.page == 1
    menu.handle(pygame.event.Event(pygame.MOUSEWHEEL, y=5))
    assert menu.inventory.page == 0


def _post_key(key: int) -> None:
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0))


@pytest.fixture
def legacy_wall_agent(monkeypatch, archived_agents):
    from gameplay.match import playable_agents
    roster = playable_agents()
    roster["marrow"] = archived_agents["marrow"]
    monkeypatch.setattr("client.game.playable_agents", lambda: roster)


def test_ability_is_taken_in_hand_cast_with_left_click_and_put_away_with_its_key() -> None:
    game = Game(args(agent="omen"))
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
    game2 = Game(args(agent="omen"))
    game2.match.start()
    before = len(game2.match.effects)
    pygame.event.clear()
    _post_key(key_e)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 360)))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    game2.run()
    assert len(game2.match.effects) == before + 1 and game2.aiming is None


def test_right_click_casts_the_alternative_wall_along_the_aim(legacy_wall_agent) -> None:
    from gameplay.match import Command
    game = Game(args(agent="marrow"))
    game.match.start()
    me = game.match.players[game.me]
    me.charges["Q"], me.facing = 1, 0.0
    assert me.agent == "marrow"
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


def test_spectator_camera_turns_smoothly() -> None:
    game = Game(args(team_size=3))
    game.match.start()
    game.match.phase, game.match.phase_until = "live", game.match.time + 100
    me = game.match.players[game.me]
    game.match._kill(None, me, "test", "body")
    first = game.view_player(me)
    mate = game.match.players[first.pid]
    mate.facing = (first.facing + 170.0) % 360.0  # the teammate snaps round
    game.match.time += 1 / 60
    cam = game.view_player(me)
    turned = abs((cam.facing - first.facing + 540) % 360 - 180)
    assert 0 < turned < 60, "the camera follows, but not in one jump"


@pytest.mark.parametrize(("agent", "slot"), [("phoenix", "Q"), ("brimstone", "C")])
def test_throwable_in_hand_draws_its_aim_preview(agent, slot) -> None:
    game = Game(args(agent=agent))
    game.match.start()
    me = game.match.players[game.me]
    ab = game.match.agents[me.agent]["abilities"][slot]
    assert game.is_throwable(ab) and game.needs_aim(me, slot)
    game.aiming = slot
    game.draw()


def test_buy_menu_sells_with_a_second_click_and_surrender_ends_the_match() -> None:
    game = Game(args())
    game.match.start()
    me = game.match.players[game.me]
    me.credits = 5000
    game.match.buy(me, "vandal")
    assert game.item_sellable(me, "vandal")
    game.ui.buy_open = True
    game.draw()
    game.ui.buy_open = False
    game.open_overlay("pause")
    game.draw_overlay()
    assert any(h.action == "surrender" for h in game.kit.hits)
    game.overlay = "surrender"
    game.draw_overlay()
    yes = next(h for h in game.kit.hits if h.action == "surrender_yes")
    for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        game.overlay_event(pygame.event.Event(kind, button=1, pos=yes.rect.center))
    assert game.match.phase == "over"


def test_multi_placement_marks_with_left_and_confirms_with_right_click() -> None:
    from gameplay.geometry import Vec

    game = Game(args(agent="brimstone"))
    game.match.start()
    me = game.match.players[game.me]
    assert me.agent == "brimstone"
    me.charges["E"] = 3
    rect, scale = game.tactical_layout()
    origin = (round(rect.left + me.pos.x * scale), round(rect.top + (game.match.world.height - me.pos.y) * scale))
    clicks = [(origin[0] - 8, origin[1]), (origin[0] + 8, origin[1])]
    targets = [Vec((x - rect.left) / scale, game.match.world.height - (y - rect.top) / scale) for x, y in clicks]
    pygame.event.clear()
    _post_key(game.keys["ability_e"])
    for click in clicks:
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=click))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=clicks[-1]))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    game.run()
    assert [effect.pos for effect in game.match.effects if effect.kind == "smoke"] == targets
    assert me.charges["E"] == 1 and game.aiming is None
