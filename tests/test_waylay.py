"""Waylay's controls, timing, movement and host-authoritative Refract."""
import socket
import time

import pytest

from gameplay.geometry import Rect, Vec
from gameplay.kit import statuses
from gameplay.kit.engine import place
from gameplay.kit.registry import Ctx
from gameplay.match import Command, Match, playable_agents
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from gameplay.world import Wall, WorldMap

DT = 1 / 64


def make_match():
    world = WorldMap("test", "Test", 80, 80, spawns={0: [Vec(20, 20)], 1: [Vec(50, 50)]})
    return Match(world, agent_roster=playable_agents())


def advance(match, seconds):
    for _ in range(round(seconds / DT)):
        match.tick(DT, {})


def test_waylay_selected_from_offline_menu_and_lightspeed_both_inputs(monkeypatch, tmp_path):
    import pygame
    from client.game import Game
    from menu import MainMenu
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    font = pygame.font.Font(None, 22)
    menu = MainMenu(screen, font, font, args())
    assert "waylay" in menu.agents()
    menu.activate("agent:waylay")
    menu.activate("pick_agent")
    game = Game(menu.activate("start"))
    assert game.match.players[game.me].agent == "waylay"
    game.draw()

    match = make_match()
    player = match.add_player("Waylay", 0, "waylay")
    match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    for alt, reach in ((True, 9), (False, 18)):
        player.pos, player.vel = Vec(20, 20), Vec(0, 0)
        player.charges["Q"] = 1
        match.tick(DT, {player.pid: Command(ability="Q", ability_alt=alt, facing=0, jump=not alt)})
        if not alt:
            assert player.z > 0 and player.vz > match._mv["jump_velocity"]
        advance(match, 1.2)
        assert player.pos.y == pytest.approx(20 + reach, abs=0.65)
        assert player.charges["Q"] == 0 and player.hp == 100


def test_saturate_ignores_smoke_but_respects_walls_and_intangibility():
    match = make_match()
    player = match.add_player("Waylay", 0, "waylay")
    ally = match.add_player("Ally", 0, "omen")
    enemy = match.add_player("Enemy", 1, "omen")
    intangible = match.add_player("Intangible", 1, "reyna")
    covered = match.add_player("Covered", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    player.pos, ally.pos, enemy.pos = Vec(20, 20), Vec(22, 28), Vec(24, 28)
    intangible.pos, covered.pos = Vec(19, 28), Vec(20, 33)
    match.world.walls.append(Wall(Rect(18, 30, 22, 31), 3))
    place(Ctx(match, player, 0, Vec(21, 28), player.pos, Vec(0, 1)),
          {"look": "smoke", "radius": 2, "lasts": 10}, Vec(21, 28))
    statuses.apply_status(match, intangible, "dismiss", 4)
    player.charges["C"] = 1
    match.tick(DT, {player.pid: Command(ability="C", facing=0, cursor_depth=10)})
    advance(match, 1)
    assert "waylay_hinder" not in ally.status
    advance(match, 0.25)
    assert ally.status["waylay_hinder"] == enemy.status["waylay_hinder"]
    assert 2.8 < ally.status["waylay_hinder"] - match.time <= 3
    assert all("waylay_hinder" not in p.status for p in (player, intangible, covered))


def test_convergent_paths_expands_sideways_and_grants_haste():
    match = make_match()
    player = match.add_player("Waylay", 0, "waylay")
    ally = match.add_player("Ally", 0, "omen")
    enemy = match.add_player("Enemy", 1, "omen")
    outside = match.add_player("Outside", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    player.pos, ally.pos, enemy.pos, outside.pos = Vec(20, 20), Vec(20, 30), Vec(26, 30), Vec(28, 30)
    player.ult_points = 8
    match.tick(DT, {player.pid: Command(ability="X", facing=0)})
    advance(match, 1.04)
    assert player.ult_points == 0 and statuses.speed_factor(match, player) == pytest.approx(1.1)
    assert "waylay_hinder" in ally.status and "waylay_hinder" not in enemy.status
    advance(match, 0.45)
    assert ally.status["waylay_hinder"] < enemy.status["waylay_hinder"]
    assert "waylay_hinder" not in outside.status


def test_refract_routes_around_a_wall_and_keeps_health():
    match = make_match()
    player = match.add_player("Waylay", 0, "waylay")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    match.world.walls.append(Wall(Rect(17, 24, 23, 25), 3))
    match.tick(DT, {player.pid: Command(ability="E")})
    player.pos, player.hp = Vec(20, 29), 65
    advance(match, 0.2)
    match.tick(DT, {player.pid: Command(ability="E")})
    assert not player.channel_until
    advance(match, 0.9)
    match.tick(DT, {player.pid: Command(ability="E")})
    advance(match, 0.15)
    assert statuses.flag(match, player, "intangible") and not match.can_see(player, enemy)
    match._damage(enemy, player, 90, "body", "classic")
    while statuses.flag(match, player, "intangible"):
        assert not match.world.walls[0].rect.circle_push(player.pos, match._mv["radius"])
        match.tick(DT, {})
    assert player.hp == 65 and player.charges["E"] == 0
    assert (player.pos - Vec(20, 20)).length() < 0.05
    assert player.blind_until > match.time


def test_remote_waylay_refracts_and_host_fire_cannot_hit_her():
    match = make_match()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    session = HostSession(match, "Host", port)
    host = match.add_player("Host", 0, "omen")

    def wait_for(predicate):
        deadline = time.monotonic() + 5
        while not predicate():
            assert time.monotonic() < deadline
            session.step(DT)
            time.sleep(0.003)

    try:
        client = NetClient(f"127.0.0.1:{port}", "Guest", "waylay")
        try:
            wait_for(lambda: client.pid in match.players)
            assert session.start(team_size=1)
            player = match.players[client.pid]
            assert player.agent == "waylay" and player.team != host.team
            match.phase, match.phase_until = "live", 100
            player.pos, host.pos = Vec(20, 20), Vec(20, 16)
            client.send(Command(ability="E"))
            wait_for(lambda: player.charges["E"] == 0)
            player.pos = Vec(20, 35)
            wait_for(lambda: statuses.has(match, player, "waylay_refract_ready"))
            client.send(Command(ability="E"))
            wait_for(lambda: statuses.flag(match, player, "intangible"))
            host.weapons["primary"] = match._new_weapon("operator")
            host.slot, host.equip_until = "primary", 0
            session.step(DT, {host.pid: Command(fire=True, facing=0, cursor_depth=19)})
            assert host.weapons["primary"].mag == 4 and player.hp == 100
            assert "waylay_refract_transit" in next(row["status"] for row in match.snapshot(host.pid)["players"]
                                                   if row["pid"] == player.pid)
            packets = []

            def received_transit():
                packets.extend(packet["snap"] for packet in client.take() if packet["type"] == "state")
                return next((snap for snap in packets if any(
                    "waylay_refract_transit" in row["status"] for row in snap["players"])), None)

            wait_for(received_transit)
            assert [row["pid"] for row in received_transit()["players"]] == [player.pid]
            wait_for(lambda: not statuses.flag(match, player, "intangible"))
            assert (player.pos - Vec(20, 20)).length() < 0.05 and player.hp == 100
        finally:
            client.close()
    finally:
        session.close()
