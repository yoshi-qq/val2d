import pytest

from gameplay.geometry import Rect, Vec
from gameplay.match import Command
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from gameplay.world import Wall
from test_chamber import DT, advance, arena
from test_net import _free_port, _wait


def test_neon_offline_selection_utility_and_slide(tmp_path, monkeypatch):
    from client.game import Game
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    game = Game(args(agent="neon"))
    assert game.match.players[game.me].agent == "neon"
    game.match.start()
    game.draw()

    match = arena()
    neon = match.add_player("Neon", 0, "neon")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    neon.pos, enemy.pos = Vec(20, 20), Vec(20, 27)
    neon.charges.update(C=1, Q=1)
    match.tick(DT, {neon.pid: Command(ability="C", facing=0)})
    advance(match, 0.45)
    assert not match._line_clear(Vec(16, 32), Vec(20, 32), 0)
    assert match._line_clear(Vec(20, 25), Vec(20, 32), 0)
    match.world.walls.append(Wall(Rect(18, 29, 22, 30), 3))
    match.tick(DT, {neon.pid: Command(ability="Q", facing=0, cursor_depth=12)})
    zones = [e for e in match.effects if e.props.get("sprite") == "neon_relay"]
    assert len(zones) == 2 and zones[0].pos.y == 29 and zones[1].pos.y < zones[0].pos.y
    advance(match, 1.4)
    assert enemy.status["concuss"] > match.time

    match.tick(DT, {neon.pid: Command(ability="E")})
    assert "neon_sprint" in neon.status and neon.charges["E"] == 1
    assert match._max_speed(neon) == pytest.approx(8.1)
    neon.z = 1
    assert match._max_speed(neon) == pytest.approx(5.4)
    neon.z = 0
    match.tick(DT, {neon.pid: Command(move_x=1, alt_fire=True, facing=0)})
    assert neon.charges["E"] == 0 and neon.dash_until > match.time and neon.crouching
    assert "neon_sprint" not in neon.status


def test_guest_overdrive_beam_damage_and_battery_are_host_authoritative():
    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "omen")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "neon")
        try:
            _wait(lambda: client.pid in match.players, session)
            assert session.start(team_size=1)
            neon = match.players[client.pid]
            match.phase, match.phase_until = "live", 100
            neon.pos, host.pos = Vec(20, 20), Vec(20, 30)
            neon.ult_points = 8
            neon.charges["E"] = 0
            client.send(Command(ability="X", facing=0))
            _wait(lambda: "neon_overdrive" in neon.status, session)
            assert neon.charges["E"] == 1 and neon.ult_points == 0
            _wait(lambda: match.time > neon.equip_until, session)
            assert neon.passive_state["neon_battery"] < 98
            client.send(Command(fire=True, facing=0, cursor_depth=10))
            _wait(lambda: not host.alive, session)
            assert neon.passive_state["neon_battery"] > 99
            assert neon.passive_state["neon_ammo"] == 38
        finally:
            client.close()
    finally:
        session.close()
