"""Miks through the client, match commands and the multiplayer protocol."""
import argparse
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


def make_match():
    world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(20, 20)], 1: [Vec(90, 90)]})
    return Match(world, agent_roster=playable_agents())


def advance(match, seconds):
    for _ in range(round(seconds / DT)):
        match.tick(DT, {})


def test_m_pulse_toggles_in_the_offline_client_and_heals_both_teams(tmp_path, monkeypatch):
    from client.game import Game

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    args = argparse.Namespace(agent="miks", team_size=1, rounds=13, map="ascent", all_around=False,
                              sound_rings=False, name="Tester", host=False, host_online=False, join=None,
                              find=False, port=9009, no_menu=True, practice=False, mode="standard", online=False)
    game = Game(args)
    game.match.start()
    me = game.match.players[game.me]
    assert me.agent == "miks"
    game.match.phase = "buy"
    me.credits = 500
    assert game.match.buy(me, "C")
    game.set_aim("C")
    game.cursor_depth = 4
    command = Command()
    game.aim_click(me, command, 3, (0, 0))
    assert command.ability is None and game.aiming == "C" and me.charges["C"] == 1
    game.aim_click(me, command, 1, (0, 0))
    assert command.ability == "C" and command.ability_alt and game.aiming is None
    game.step(DT, command)
    game.draw()
    assert any(e.props["sprite"] == "miks_pulse_heal" for e in game.match.effects)

    match = make_match()
    me = match.add_player("Miks", 0, "miks")
    ally = match.add_player("Ally", 0, "omen")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    me.pos, ally.pos, enemy.pos = Vec(20, 20), Vec(21, 28), Vec(19, 28)
    ally.hp = enemy.hp = 10
    me.charges["C"] = 2
    match.tick(DT, {me.pid: Command(ability="C", ability_alt=True, facing=0, cursor_depth=10)})
    advance(match, 1.65)
    assert ally.hp == enemy.hp >= 35
    advance(match, 4.2)
    assert not match.effects and ally.hp == enemy.hp == 100

    match.tick(DT, {me.pid: Command(ability="C", facing=0, cursor_depth=10)})
    advance(match, 1.65)
    device = next(e for e in match.effects if e.kind == "sensor")
    assert device.data["hp"] == 50 and device.props["friendly_fire"]
    assert match.time < ally.status["concuss"] < match.time + 2
    assert match.time < enemy.status["concuss"] < match.time + 2
    ally.pos = device.pos - Vec(0, 3)
    ally.weapons["primary"] = match._new_weapon("operator")
    ally.slot = "primary"
    ally.zoom_level = 1
    match.tick(DT, {ally.pid: Command(fire=True, facing=0, cursor_depth=3)})
    assert device not in match.effects


def test_harmonize_refreshes_after_the_linked_ally_gets_a_kill():
    match = make_match()
    me = match.add_player("Miks", 0, "miks")
    ally = match.add_player("Ally", 0, "omen")
    victim = match.add_player("Victim", 1, "omen")
    match.add_player("Opponent", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    me.pos, ally.pos, victim.pos = Vec(20, 20), Vec(20, 24), Vec(20, 29)
    me.charges["Q"], victim.hp = 1, 1
    match.tick(DT, {me.pid: Command(ability="Q", facing=0, cursor_depth=4)})
    assert "miks_haste" not in me.status
    advance(match, 0.1 + DT)
    assert me.status["miks_haste"] == ally.status["miks_haste"] == match.time + 8
    before = me.status["miks_haste"]
    advance(match, 3)
    match.tick(DT, {ally.pid: Command(fire=True, facing=0, cursor_depth=5)})
    assert not victim.alive
    assert me.status["miks_haste"] == ally.status["miks_stim"] == match.time + 8 > before


def test_waveform_uses_two_charges_and_bassquake_stays_inside_the_cone():
    match = make_match()
    me = match.add_player("Miks", 0, "miks")
    ally = match.add_player("Ally", 0, "omen")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    me.credits = 200
    assert match.buy(me, "E") and me.charges["E"] == 2
    assert match.sell(me, "E") and me.charges["E"] == 1
    assert match.buy(me, "E")
    match.phase, match.phase_until = "live", 100
    me.pos, ally.pos, enemy.pos = Vec(20, 20), Vec(20, 31), Vec(31, 20)
    match.tick(DT, {me.pid: Command(ability="E", points=[(20, 27), (30, 29)])})
    smokes = [e for e in match.effects if e.kind == "smoke"]
    assert len(smokes) == 2 and me.charges["E"] == 0
    assert all(e.start == match.time + 1 and e.until - e.start == 16.75 for e in smokes)
    advance(match, 18)
    assert not match.effects

    me.ult_points = 8
    match.tick(DT, {me.pid: Command(ability="X", facing=0)})
    assert me.ult_points == 0 and me.channel_until == match.time + 1.6
    assert not ally.status
    advance(match, 1.7)
    assert ally.pos.y == pytest.approx(36) and "deaf" in ally.status and "slow" in ally.status
    assert not enemy.status and enemy.pos == Vec(31, 20)
    advance(match, 21)
    assert me.charges["E"] == 1


def test_remote_miks_casts_and_receives_the_bassquake_cone():
    from map_fixtures import load_archived_map

    match = Match(load_archived_map("workyard"), agent_roster=playable_agents())
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    session = HostSession(match, "Host", port)
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "miks")
        try:
            deadline = time.monotonic() + 5
            while client.pid not in match.players and time.monotonic() < deadline:
                session.step(DT)
                time.sleep(0.005)
            session.start(team_size=1)
            me = match.players[client.pid]
            assert me.agent == "miks"
            me.ult_points = 8
            client.send(Command(ability="X", facing=90))
            shadow = Match(match.world, agent_roster=playable_agents())
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                session.step(DT)
                for packet in client.take():
                    if packet["type"] == "state":
                        apply_snapshot(shadow, packet["snap"], client.pid)
                if any(e.props.get("cone") for e in shadow.effects):
                    break
                time.sleep(0.005)
            cone = next(e for e in shadow.effects if e.props.get("cone"))
            assert cone.radius == 40 and cone.props["cone"] == 60 and cone.props["aim"][0] == pytest.approx(1)
            assert me.ult_points == 0
        finally:
            client.close()
    finally:
        session.close()
