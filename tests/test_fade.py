from gameplay.geometry import Vec
from gameplay.match import Command
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from test_chamber import DT, advance, arena
from test_net import _free_port, _wait


def test_fade_offline_selection_seize_and_nightfall(tmp_path, monkeypatch):
    from client.game import Game
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    game = Game(args(agent="fade"))
    assert game.match.players[game.me].agent == "fade"
    game.match.start()
    game.draw()
    match = arena()
    fade = match.add_player("Fade", 0, "fade")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    fade.pos, enemy.pos = Vec(20, 20), Vec(20, 28)
    fade.charges["Q"] = 1
    match.tick(DT, {fade.pid: Command(ability="Q", facing=0, cursor_depth=10)})
    advance(match, 2.3)
    assert enemy.decay_pool > 70 and "fade_tether" in enemy.status
    for _ in range(90):
        match.tick(DT, {enemy.pid: Command(move_y=1, facing=0)})
    assert enemy.pos.y <= 34.581
    advance(match, 5)
    assert enemy.hp == 100
    fade.ult_points = 8
    match.tick(DT, {fade.pid: Command(ability="X", facing=0)})
    advance(match, 2)
    assert enemy.status["deaf"] > match.time and enemy.decay_pool > 60
    assert any(e.data.get("fade_trail") == enemy.pid for e in match.effects)


def test_guest_haunt_marks_host_and_prowler_follows_team_only_trail():
    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "omen")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "fade")
        try:
            _wait(lambda: client.pid in match.players, session)
            assert session.start(team_size=1)
            fade = match.players[client.pid]
            match.phase, match.phase_until = "live", 100
            fade.pos, host.pos = Vec(20, 20), Vec(20, 32)
            fade.charges["C"] = 1
            client.send(Command(ability="E", facing=0, cursor_depth=12))
            _wait(lambda: fade.charges["E"] == 0 and fade.prev_ability is None, session)
            client.send(Command(ability="E", facing=0))
            _wait(lambda: any(e.data.get("fade_trail") == host.pid for e in match.effects), session)
            assert host.revealed_until > match.time
            assert not any(e.get("sprite") == "fade_trail" for e in match.snapshot(host.pid)["effects"])
            assert any(e.get("sprite") == "fade_trail" for e in match.snapshot(fade.pid)["effects"])
            client.send(Command(ability="C", facing=90))
            _wait(lambda: host.status.get("fade_nearsight", 0) > match.time, session)
            assert fade.charges["C"] == 0
        finally:
            client.close()
    finally:
        session.close()
