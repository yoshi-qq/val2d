from gameplay.geometry import Rect, Vec
from gameplay.match import Command
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from gameplay.world import Wall
from test_chamber import DT, advance, arena
from test_net import _free_port, _wait


def setup_round():
    match = arena()
    tejo = match.add_player("Tejo", 0, "tejo")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    tejo.pos, enemy.pos = Vec(20, 20), Vec(20, 34)
    return match, tejo, enemy


def effects(match, name):
    return [e for e in match.effects if e.props.get("sprite") == f"tejo_{name}"]


def test_tejo_offline_and_sticky_grenade_bounce(monkeypatch, tmp_path):
    from client.game import Game
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    game = Game(args(agent="tejo"))
    assert game.match.players[game.me].agent == "tejo"
    game.match.start()
    game.draw()

    match, tejo, enemy = setup_round()
    match.world.walls.append(Wall(Rect(16, 30, 24, 31), 3))
    enemy.pos = Vec(20, 22.9)
    tejo.charges["Q"] = 1
    match.tick(DT, {tejo.pid: Command(ability="Q", ability_alt=True, facing=0, cursor_depth=17)})
    advance(match, 1.8)
    assert enemy.hp == 65 and enemy.status["concuss"] > match.time
    assert not effects(match, "grenade")


def test_guided_salvo_spends_one_charge_for_each_target():
    match, tejo, enemy = setup_round()
    enemy.pos = Vec(20, 28)
    tejo.charges["E"] = 2
    match.tick(DT, {tejo.pid: Command(ability="E", points=[(20, 28), (40, 28)])})
    assert tejo.charges["E"] == 0 and len(effects(match, "missile")) == 2
    advance(match, 1.8)
    assert enemy.hp == 35
    advance(match, 0.8)
    assert not enemy.alive


def test_guided_salvo_routes_around_solid_cover():
    match, tejo, enemy = setup_round()
    match.world.walls.append(Wall(Rect(18, 24, 22, 26), 3))
    match.tick(DT, {tejo.pid: Command(ability="E", points=[(20, 34)])})
    missile, = effects(match, "missile")
    route = missile.data["route"]
    assert len(route) > 1 and route[-1] == enemy.pos
    assert any(point.x < 18 or point.x > 22 for point in route)
    advance(match, 2.8)
    assert enemy.hp < 100


def test_armageddon_uses_map_direction_and_rolls_forward():
    match, tejo, enemy = setup_round()
    enemy.pos = Vec(39, 28)
    tejo.ult_points = 9
    match.tick(DT, {tejo.pid: Command(ability="X", facing=0, points=[(26, 28), (78, 28)])})
    segments = effects(match, "strike")
    assert len(segments) == 16 and tejo.ult_points == 0
    assert segments[0].a == Vec(26, 28) and segments[-1].b == Vec(58, 28)
    advance(match, 4.5)
    assert enemy.hp == 100
    advance(match, 0.2)
    assert enemy.hp == 40
    advance(match, 0.3)
    assert not enemy.alive


def test_guest_tejo_pilots_drone_and_suppresses_host():
    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "omen")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "tejo")
        try:
            _wait(lambda: client.pid in match.players, session)
            assert session.start(team_size=1)
            tejo = match.players[client.pid]
            match.phase, match.phase_until = "live", 100
            tejo.pos, host.pos = Vec(20, 20), Vec(20, 32)
            tejo.charges["C"] = 1
            client.send(Command(ability="C", facing=0))
            _wait(lambda: any(e.start <= match.time for e in effects(match, "drone")), session)
            drone = effects(match, "drone")[0]
            assert drone.data["hp"] == 42
            start = drone.pos
            client.send(Command(move_y=1, facing=0))
            _wait(lambda: drone.pos != start, session)
            client.send(Command(fire=True, facing=0))
            _wait(lambda: host.status.get("suppress", 0) > match.time, session)
            assert tejo.pos == Vec(20, 20) and tejo.channel_until == 0
            assert host.revealed_until > match.time and tejo.charges["C"] == 0
        finally:
            client.close()
    finally:
        session.close()
