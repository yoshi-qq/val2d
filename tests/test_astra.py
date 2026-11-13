from gameplay.geometry import Vec
from gameplay.match import Command, GameEvent
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from test_chamber import DT, advance, arena
from test_net import _free_port, _wait


def test_astra_offline_stars_nova_well_and_dissipate(monkeypatch, tmp_path):
    from client.game import Game
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    game = Game(args(agent="astra"))
    assert game.match.players[game.me].agent == "astra"
    game.match.start()
    game.set_aim("X")
    game.draw()
    match = arena()
    astra = match.add_player("Astra", 0, "astra")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    astra.pos, enemy.pos = Vec(20, 20), Vec(22, 30)
    astra.charges["E"] = 3

    def star(y):
        match.tick(DT, {astra.pid: Command(ability="X", points=[(20, y)])})
        advance(match, 0.7)

    star(30)
    match.tick(DT, {astra.pid: Command(ability="Q", facing=0, cursor_depth=10)})
    advance(match, 1.1)
    assert enemy.status["concuss"] > match.time and astra.ult_points == 0
    star(31)
    match.tick(DT, {astra.pid: Command(ability="C", facing=0, cursor_depth=11)})
    advance(match, 3.4)
    assert (enemy.pos - Vec(20, 31)).length() < 0.2 and enemy.status["iso_vulnerable"] > match.time
    star(35)
    match.tick(DT, {astra.pid: Command(interact=True, facing=0, cursor_depth=15)})
    assert any(e.props.get("sprite") == "astra_dissipate" for e in match.effects)
    assert astra.charges["E"] == 0
    advance(match, 25.1)
    assert astra.charges["E"] == 1


def test_guest_astra_creates_divide_that_blocks_host_shots_and_sound():
    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "omen")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "astra")
        try:
            _wait(lambda: client.pid in match.players, session)
            assert session.start(team_size=1)
            astra = match.players[client.pid]
            match.phase, match.phase_until = "live", 100
            astra.pos, host.pos = Vec(20, 20), Vec(20, 32)
            client.send(Command(ability="X", points=[(20, 26)]))
            _wait(lambda: astra.charges["E"] == 0 and astra.prev_ability is None, session)
            astra.ult_points = 7
            client.send(Command(ability="X", points=[(20, 26), (26, 26)]))
            _wait(lambda: match.sound_blocked(host.pos, astra.pos), session)
            assert astra.ult_points == 0
            assert not match._line_clear(host.pos, astra.pos, 0)
            match._trace(host, match._weapon_def(host), Vec(0, -1), Vec(0, -1))
            assert astra.hp == 100 and match.events[-1].data["stop"] == "wall"
            assert any(row.get("blocks_sound") for row in match.snapshot(host.pid)["effects"])
            assert not session.net._event_visible(host, GameEvent("sound", match.time, {
                "pid": astra.pid, "pos": (20, 20), "radius": 30, "kind": "step",
            }))
        finally:
            client.close()
    finally:
        session.close()


def test_astra_rejoins_through_halftime_and_finishes_match():
    match = arena()
    match.set_rules(win_rounds=2, overtime=False)
    match._r["half_after"] = 1
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "omen")
    address = f"127.0.0.1:{session.net.port}"
    client = None
    try:
        client = NetClient(address, "Guest", "astra")
        pid, token = client.pid, client.token
        _wait(lambda: pid in match.players, session)
        assert session.start(team_size=1)
        astra = match.players[pid]
        first_side = match.side(astra.team)
        client.send(Command(ability="X", points=[(20, 26)]))
        _wait(lambda: any(e.props.get("sprite") == "astra_star" for e in match.effects), session)
        assert astra.charges["E"] == 0
        client.close()
        client = None
        _wait(lambda: astra.is_bot, session)
        match.phase_until = match.time
        session.step(DT)
        session.step(DT, {host.pid: Command()})
        match._damage(host, astra, 150, "body", "classic")
        session.step(DT)
        assert match.phase == "end"
        match.phase_until = match.time
        session.step(DT)
        assert match.round_no == 2 and match.side(astra.team) != first_side
        client = NetClient(address, "Guest", "astra", token=token)
        assert client.rejoined and client.pid == pid and not astra.is_bot
        assert astra.agent == "astra" and astra.charges["E"] == 1
        assert not any(e.props.get("sprite") == "astra_star" for e in match.effects)
        client.send(Command(ability="X", points=[(20, 26)]))
        _wait(lambda: astra.charges["E"] == 0, session)
        match.phase_until = match.time
        session.step(DT)
        match._damage(host, astra, 150, "body", "classic")
        session.step(DT)
        assert match.phase == "over" and match.match_winner == host.team
    finally:
        if client is not None:
            client.close()
        session.close()
