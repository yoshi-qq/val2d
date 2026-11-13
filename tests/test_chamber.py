import socket
import time

import pytest

from gameplay.geometry import Vec
from gameplay.match import Command, Match, playable_agents
from gameplay.net import apply_snapshot
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from gameplay.world import WorldMap

DT = 1 / 64


def arena():
    return Match(WorldMap("test", "Test", 80, 80, spawns={0: [Vec(20, 20)], 1: [Vec(50, 50)]}),
                 agent_roster=playable_agents(), seed=3)


def advance(match, seconds):
    for _ in range(round(seconds / DT)):
        match.tick(DT, {})


def offline():
    match = arena()
    chamber = match.add_player("Chamber", 0, "chamber")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    return match, chamber, enemy


def test_chamber_starts_offline_and_headhunter_spends_rounds_only_when_fired(monkeypatch, tmp_path):
    import pygame
    from client.game import Game
    from menu import MainMenu
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    font = pygame.font.Font(None, 22)
    menu = MainMenu(screen, font, font, args())
    menu.activate("agent:chamber")
    menu.activate("pick_agent")
    game = Game(menu.activate("start"))
    assert game.match.players[game.me].agent == "chamber"
    game.draw()
    assert not any(k in ("headhunter", "tour_de_force") for group in game.buy_groups().values() for k, _ in group)

    match, chamber, enemy = offline()
    chamber.credits = 500
    assert not match.buy(chamber, "headhunter")
    assert match.buy(chamber, "Q") and match.buy(chamber, "Q")
    assert chamber.credits == 300 and chamber.charges["Q"] == 2
    match.phase, match.phase_until = "live", 100
    chamber.pos, enemy.pos = Vec(20, 20), Vec(20, 27)
    match.tick(DT, {chamber.pid: Command(ability="Q", facing=0)})
    assert chamber.weapon.key == "headhunter" and chamber.weapon.mag == chamber.charges["Q"] == 2
    advance(match, 0.35)
    match.tick(DT, {chamber.pid: Command(alt_fire=True, fire=True, facing=0, cursor_depth=9)})
    assert enemy.hp == 45
    assert chamber.weapon.mag == chamber.charges["Q"] == 1
    match.tick(DT, {chamber.pid: Command(slot="sidearm")})
    assert chamber.weapon.key == "classic"
    match.tick(DT, {chamber.pid: Command(ability="Q")})
    assert chamber.weapon.mag == 1


def test_trademark_targets_enemies_and_tour_de_force_slows_after_a_kill():
    match, chamber, enemy = offline()
    match.add_player("Second enemy", 1, "omen").pos = Vec(60, 60)
    match.phase, match.phase_until = "live", 100
    chamber.pos, enemy.pos = Vec(20, 20), Vec(20, 30)
    chamber.charges["C"] = 1
    match.tick(DT, {chamber.pid: Command(ability="C", facing=0, cursor_depth=4)})
    advance(match, 2.4)
    assert "chamber_slow" not in enemy.status
    advance(match, 0.7)
    assert "chamber_slow" in enemy.status and chamber.charges["C"] == 0
    advance(match, 4.1)
    chamber.ult_points = 8
    match.tick(DT, {chamber.pid: Command(ability="X", facing=0)})
    assert chamber.weapon.key == "tour_de_force" and chamber.weapon.mag == 5
    assert chamber.ult_points == 0
    advance(match, 2.35)
    match.tick(DT, {chamber.pid: Command(alt_fire=True, fire=True, facing=0, cursor_depth=10)})
    assert not enemy.alive and chamber.weapon.mag == 4
    assert any(e.pos == enemy.pos and e.props["sprite"] == "chamber_slow" for e in match.effects)
    match.tick(DT, {chamber.pid: Command(slot="melee")})
    match.tick(DT, {chamber.pid: Command(ability="X")})
    assert chamber.weapon.key == "tour_de_force" and chamber.weapon.mag == 4


def test_rendezvous_range_cooldown_recall_and_no_refund_on_destruction():
    match, chamber, enemy = offline()
    match.phase, match.phase_until = "live", 100
    chamber.pos, enemy.pos = Vec(20, 20), Vec(50, 50)
    match.tick(DT, {chamber.pid: Command(ability="E", facing=0, cursor_depth=5)})
    anchor = next(e for e in match.effects if e.props.get("chamber_anchor"))
    assert anchor.pos == Vec(20, 25) and chamber.charges["E"] == 0
    chamber.pos = Vec(20, 45)
    advance(match, 0.1)
    match.tick(DT, {chamber.pid: Command(ability="E")})
    assert not chamber.channel_until
    chamber.pos = Vec(20, 38)
    advance(match, 0.1)
    match.tick(DT, {chamber.pid: Command(ability="E")})
    advance(match, 1.4)
    assert chamber.pos == anchor.pos
    assert anchor.data["ready_at"] > match.time + 28
    chamber.pos = Vec(20, 20)
    match.tick(DT, {chamber.pid: Command(interact=True, facing=0, cursor_depth=5)})
    assert anchor not in match.effects and "chamber_anchor" not in chamber.status
    advance(match, 30.1)
    assert chamber.charges["E"] == 1

    match.tick(DT, {chamber.pid: Command(ability="E", facing=0, cursor_depth=5)})
    anchor = next(e for e in match.effects if e.props.get("chamber_anchor"))
    enemy.pos = anchor.pos + Vec(5, 0)
    enemy.weapons["primary"] = match._new_weapon("operator")
    enemy.slot, enemy.equip_until, enemy.zoom_level = "primary", 0, 1
    match.tick(DT, {enemy.pid: Command(fire=True, facing=270, cursor_depth=5)})
    assert anchor not in match.effects and "chamber_anchor" not in chamber.status
    advance(match, 30.1)
    assert chamber.charges["E"] == 0


def test_guest_chamber_teleports_and_receives_host_synced_headhunter():
    match = arena()
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
        client = NetClient(f"127.0.0.1:{port}", "Guest", "chamber")
        try:
            wait_for(lambda: client.pid in match.players)
            assert session.start(team_size=1)
            guest = match.players[client.pid]
            assert guest.agent == "chamber"
            match.phase, match.phase_until = "live", 100
            guest.pos, host.pos = Vec(20, 20), Vec(55, 55)
            guest.charges["Q"] = 2
            client.send(Command(ability="E", facing=0, cursor_depth=4))
            wait_for(lambda: bool(match.effects))
            guest.pos = Vec(20, 35)
            wait_for(lambda: guest.prev_ability is None)
            client.send(Command(ability="E"))
            wait_for(lambda: guest.pos == Vec(20, 24) and guest.channel_until <= match.time)
            client.send(Command(ability="Q"))
            mirror = Match(match.world, agent_roster=playable_agents())

            def got_weapon():
                for packet in client.take():
                    if packet["type"] == "state":
                        apply_snapshot(mirror, packet["snap"], client.pid)
                p = mirror.players.get(client.pid)
                return p is not None and p.weapon is not None and p.weapon.key == "headhunter"

            wait_for(got_weapon)
            assert mirror.players[client.pid].weapon.mag == 2 and mirror.players[client.pid].pos == Vec(20, 24)
        finally:
            client.close()
    finally:
        session.close()
