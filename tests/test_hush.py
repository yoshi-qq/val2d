import pytest

from gameplay.geometry import Vec
from gameplay.match import Command
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from test_chamber import DT, advance, arena
from test_net import _free_port, _wait


def test_hush_offline_flow_and_redirected_flash(monkeypatch, tmp_path):
    from client.game import Game
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    game = Game(args(agent="hush"))
    assert game.match.players[game.me].agent == "hush"
    game.match.start()
    game.draw()
    match = arena()
    hush = match.add_player("Hush", 0, "hush")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    hush.pos, enemy.pos = Vec(20, 20), Vec(35, 28)
    hush.charges.update(C=1, Q=1)
    match.tick(DT, {hush.pid: Command(ability="C", facing=0, cursor_depth=8)})
    advance(match, 0.8)
    assert 27 < hush.pos.y < 30
    match.tick(DT, {hush.pid: Command(ability="Q", ability_alt=True, facing=0)})
    advance(match, 0.2)
    assert not enemy.blind_until
    match.tick(DT, {hush.pid: Command(ability="Q", facing=90),
                    enemy.pid: Command(facing=65)})
    advance(match, 1.2)
    assert enemy.blind_until > match.time and hush.charges["Q"] == 0


@pytest.mark.parametrize("duel", [False, True])
def test_deathmatch_flow_cannot_start_in_spawn_or_duel(duel):
    from gameplay.geometry import Rect

    match = arena()
    match.world.spawn_zones[0] = Rect(2, 2, 10, 10)
    match.set_mode("deathmatch")
    hush = match.add_player("Hush", 0, "hush")
    match.start()
    match.time = match.phase_until
    match.tick(0, {})
    hush.pos = Vec(20, 20)
    hush.charges["C"] = 1
    match.tick(DT, {hush.pid: Command(ability="C", facing=0, cursor_depth=8)})
    assert any(e.props.get("sprite") == "hush_anchor" for e in match.effects)
    destination = Vec(20, 20) if duel else Vec(5, 5)
    hush.pos = destination
    if duel:
        hush.duel_id = hush.pid
    advance(match, 0.55)
    assert hush.pos == destination and hush.dash_until == 0


def test_telekinesis_and_displacement_kill_refresh():
    match = arena()
    hush = match.add_player("Hush", 0, "hush")
    enemy = match.add_player("Enemy", 1, "omen")
    other = match.add_player("Other", 1, "sage")
    match.start()
    match.phase, match.phase_until = "live", 100
    hush.pos, enemy.pos, other.pos = Vec(20, 20), Vec(24, 36), Vec(48, 48)
    drop = match._ground_weapon(hush, match._new_weapon("vandal", hush), Vec(23, 20))
    assert match.drop_in_reach(hush, drop)
    assert not match.drop_in_reach(enemy, match._ground_weapon(enemy, match._new_weapon("vandal", enemy), Vec(24, 33)))
    match.tick(DT, {hush.pid: Command(ability="E", facing=0)})
    advance(match, 1.2)
    assert enemy.pos.x < 22 and hush.charges["E"] == 0
    match._kill(hush, enemy, "classic", "body")
    assert hush.charges["E"] == 0
    match._kill(hush, other, "classic", "body")
    assert hush.charges["E"] == 1


def test_guest_hush_steers_and_detonates_suspension():
    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "omen")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "hush")
        try:
            _wait(lambda: client.pid in match.players, session)
            assert session.start(team_size=1)
            hush = match.players[client.pid]
            match.phase, match.phase_until = "live", 100
            hush.pos, host.pos = Vec(20, 20), Vec(30, 25)
            hush.ult_points = 8
            client.send(Command(ability="X", facing=0))
            _wait(lambda: hush.ult_points == 0 and hush.prev_ability is None, session)
            orb = next(e for e in match.effects if e.props.get("sprite") == "hush_ult")
            client.send(Command(fire=True, facing=0))
            _wait(lambda: orb.data.get("launched"), session)
            client.send(Command(fire=False, facing=0))
            _wait(lambda: orb.pos.y >= 25 and not hush.prev_fire, session)
            client.send(Command(facing=90))
            _wait(lambda: orb.pos.x >= 25, session)
            client.send(Command(ability="X", facing=90))
            _wait(lambda: host.z > 0.5, session)
            assert host.status["hush_suspended"] > match.time and hush.ult_points == 0
        finally:
            client.close()
    finally:
        session.close()
