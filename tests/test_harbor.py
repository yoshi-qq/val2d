from gameplay.geometry import Vec
from gameplay.match import Command
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from test_chamber import DT, advance, arena
from test_net import _free_port, _wait


def harbor_match():
    match = arena()
    harbor = match.add_player("Harbor", 0, "harbor")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    harbor.pos, enemy.pos = Vec(20, 20), Vec(20, 35)
    return match, harbor, enemy


def test_harbor_offline_selection_storm_surge_and_guided_tide(tmp_path, monkeypatch):
    from client.game import Game
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    game = Game(args(agent="harbor"))
    assert game.match.players[game.me].agent == "harbor"
    game.match.start()
    game.draw()

    match, harbor, enemy = harbor_match()
    harbor.charges.update(C=1, Q=1)
    enemy.pos = Vec(20, 27)
    match.tick(DT, {harbor.pid: Command(ability="C", facing=0, cursor_depth=8)})
    advance(match, 1.4)
    assert enemy.status["harbor_nearsight"] > match.time
    assert enemy.status["harbor_slow"] > match.time
    assert not harbor.status.get("harbor_slow")
    advance(match, 2)
    match.tick(DT, {harbor.pid: Command(ability="Q", facing=0)})
    advance(match, 0.2)
    for _ in range(36):
        match.tick(DT, {harbor.pid: Command(fire=True, facing=90)})
    match.tick(DT, {harbor.pid: Command(alt_fire=True)})
    advance(match, 0.9)
    walls = [e for e in match.effects if e.props.get("sprite") == "harbor_tide"]
    assert walls[0].a == harbor.pos
    assert 25 < walls[-1].b.x < 50
    assert walls[-1].b.y > walls[0].b.y
    enemy.pos = walls[-1].pos
    advance(match, 0.1)
    assert enemy.status["harbor_slow"] > match.time
    assert not match._line_clear(Vec(18, 21), Vec(22, 21), 0)
    assert match._line_clear(Vec(18, 21), Vec(22, 21), 8)


def test_cove_shell_blocks_incoming_and_outgoing_fire():
    match, harbor, enemy = harbor_match()
    match.tick(DT, {harbor.pid: Command(ability="E", points=[(20, 27)], facing=0)})
    advance(match, 1.2)
    smoke = next(e for e in match.effects if e.props.get("sprite") == "harbor_cove")
    assert smoke.start < match.time and harbor.charges["E"] == 0
    assert not match._line_clear(harbor.pos, enemy.pos, 0)
    match.tick(DT, {harbor.pid: Command(ability="E")})
    advance(match, 0.9)
    shield = next(e for e in match.effects if e.props.get("sprite") == "harbor_shield")
    assert shield.data["hp"] == 680 and harbor.charges["E"] == 0
    harbor.pos = smoke.pos
    for shooter, direction in ((harbor, Vec(0, 1)), (enemy, Vec(0, -1))):
        before = shield.data["hp"]
        match._trace(shooter, match._weapon_def(shooter), direction, direction)
        assert shield.data["hp"] < before
    assert harbor.hp == enemy.hp == 100
    shield.data["hp"] = 1
    match._trace(harbor, match._weapon_def(harbor), Vec(0, 1), Vec(0, 1))
    assert shield.props["ended"]
    assert smoke.until == match.time + 1
    advance(match, 1.1)
    assert smoke not in match.effects
    advance(match, 29)
    assert harbor.charges["E"] == 1


def test_guest_can_stop_reckoning_on_host_without_another_ultimate_charge():
    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "omen")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "harbor")
        try:
            _wait(lambda: client.pid in match.players, session)
            assert session.start(team_size=1)
            harbor = match.players[client.pid]
            assert harbor.agent == "harbor"
            match.phase, match.phase_until = "live", 100
            harbor.pos, host.pos = Vec(20, 20), Vec(20, 32)
            harbor.ult_points = 7
            client.send(Command(ability="X", facing=0))
            _wait(lambda: host.status.get("harbor_nearsight", 0) > match.time, session)
            wave = next(e for e in match.effects if e.props.get("sprite") == "harbor_wave")
            _wait(lambda: harbor.prev_ability is None, session)
            client.send(Command(ability="X", facing=90))
            _wait(lambda: wave.data.get("stopped"), session)
            assert harbor.ult_points == 0 and 6.8 < wave.until - match.time <= 7
            position = wave.pos
            _wait(lambda: wave.until - match.time < 6.7, session)
            assert wave.pos == position
            assert any(e.get("sprite") == "harbor_wave" for e in match.snapshot(host.pid)["effects"])
        finally:
            client.close()
    finally:
        session.close()
