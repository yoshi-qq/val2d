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


@pytest.mark.parametrize(("key", "sites"), [("bind", "AB"), ("haven", "ABC")])
def test_new_map_blockouts_connect_spawns_to_every_site(key: str, sites: str) -> None:
    from gameplay.nav import NavGrid

    world = load_map(key)
    nav = NavGrid(world)
    assert {site.name for site in world.sites} == set(sites)
    for spawns in world.spawns.values():
        assert len(spawns) == 5 and all(nav.free(nav.cell(p)) for p in spawns)
        for site in world.sites:
            path = nav.path(spawns[2], site.rect.center)
            assert path and site.rect.contains(path[-1]), (key, spawns[2], site.name)


@pytest.mark.parametrize(("key", "approach", "tower", "site", "facing"), [
    ("bind", Vec(98, 130), Vec(117, 126), Vec(117, 120), 0),
    ("haven", Vec(26, 102), Vec(41.5, 106), Vec(44, 106), 270),
])
def test_a_tower_has_a_walkable_ascent_and_cannot_be_jumped_from_site(
    key: str, approach: Vec, tower: Vec, site: Vec, facing: int,
) -> None:
    from gameplay.nav import NavGrid

    world = load_map(key)
    nav = NavGrid(world)
    assert world.ground_height(tower) == 3
    assert nav.path(approach, tower, start_ground=0, goal_ground=3)
    assert nav.line_free(tower, site, start_ground=3, goal_ground=0)
    assert not nav.line_free(site, tower, start_ground=0, goal_ground=3)
    match = Match(world)
    player = match.add_player("Test", 0, "omen")
    match.start()
    match.phase, match.phase_until = "live", match.time + 10
    player.pos, player.ground, player.level = site, 0, 0
    for _ in range(64):
        match.tick(1 / 64, {player.pid: Command(move_y=1, facing=facing, jump=True)})
    assert player.level == 0
    if key == "haven":
        assert world.ground_height(tower, reach=1) == 0
        assert world.deck_blocks(tower, 1.7, tower, 4.7)


def test_haven_garage_panels_leave_penetrable_wood_and_clear_centre() -> None:
    match = Match(load_map("haven"))
    shooter = match.add_player("Shooter", 0, "omen")
    target = match.add_player("Target", 1, "omen")
    match.start()
    match.phase = "live"
    shooter.pos, target.pos = Vec(69, 39), Vec(72, 39)
    panels = [wall for wall in match.world.walls if wall.material == "obj:haven_garage_panel"]
    assert [wall.hp for wall in panels] == [400, 400]
    assert not match.line_of_fire(shooter, target)
    match._damage_cover(panels[0], 399)
    assert not match.line_of_fire(shooter, target)
    match._damage_cover(panels[0], 1)
    assert match.line_of_fire(shooter, target)
    assert not match._line_clear(shooter.pos, target.pos, 0)
    assert panels[1].rect not in match.broken_cover
    assert match._line_clear(Vec(69, 40.65), Vec(72, 40.65), 0)


def test_bind_teleporters_move_players_one_way_and_emit_sound() -> None:
    match = Match(load_map("bind"))
    player = match.add_player("A", 0, "omen")
    match.start()
    match.phase_until = match.time
    assert len(match.world.teleporters) == 2
    for entry, destination in match.world.teleporters:
        player.pos = entry.center
        events = match.tick(1 / 64, {})
        assert player.pos == destination
        assert sum(event.kind == "sound_fx" and event.data["key"] == "ab_teleport" for event in events) == 2
        assert not any(event.kind == "sound_fx" for event in match.tick(1 / 64, {}))


@pytest.mark.parametrize(("key", "neutral"), [("bind", (54, 76)), ("haven", (66, 57))])
def test_buy_barriers_leave_sites_to_defenders_and_keep_mid_routes_closed(key, neutral) -> None:
    match = Match(load_map(key))
    match.add_player("A", 0, "omen")
    match.add_player("B", 1, "jett")
    match.start()
    grid, areas = match._buy_areas
    assert areas[0].isdisjoint(areas[1])
    for site in match.world.sites:
        cell = grid.nearest_free(grid.cell(site.rect.center))
        assert cell in areas[1] and cell not in areas[0]
    assert grid.cell(Vec(*neutral)) not in areas[0] | areas[1]


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
