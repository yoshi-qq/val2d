from gameplay.geometry import Vec
from gameplay.match import Command
from gameplay.netgame import NetClient
from test_chamber import DT, advance, arena
from test_net import _free_port, _wait
from gameplay.session import HostSession


def test_raze_offline_menu_and_kit(monkeypatch, tmp_path):
    import pygame
    from client.game import Game
    from menu import MainMenu
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    pygame.init()
    menu = MainMenu(pygame.display.set_mode((1280, 720)), pygame.font.Font(None, 22),
                    pygame.font.Font(None, 22), args())
    menu.activate("agent:raze")
    menu.activate("pick_agent")
    game = Game(menu.activate("start"))
    assert game.match.players[game.me].agent == "raze"
    game.draw()

    match = arena()
    raze = match.add_player("Raze", 0, "raze")
    enemy = match.add_player("Enemy", 1, "omen")
    match.add_player("Second enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    raze.pos, enemy.pos = Vec(20, 20), Vec(20, 27)
    raze.charges.update(C=1, Q=2)
    match.tick(DT, {raze.pid: Command(ability="C", facing=0)})
    advance(match, 2.5)
    assert 20 <= enemy.hp < 50 and raze.hp == 100
    match.tick(DT, {raze.pid: Command(ability="Q", facing=0, cursor_depth=1)})
    advance(match, 0.05)
    match.tick(DT, {raze.pid: Command(ability="Q", facing=0)})
    assert raze.charges["Q"] == 1 and raze.vz > 0 and raze.hp == 100

    advance(match, 1)
    raze.pos, enemy.pos = Vec(20, 20), Vec(20, 28)
    enemy.hp = 100
    match.tick(DT, {raze.pid: Command(ability="E", facing=0, cursor_depth=10)})
    advance(match, 2.3)
    assert enemy.hp == 45
    assert len([e for e in match.effects if e.props.get("sprite") == "raze_grenade"]) == 4
    advance(match, 0.75)
    assert not enemy.alive


def test_guest_showstopper_fires_one_rocket_and_host_applies_impact():
    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "omen")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "raze")
        try:
            _wait(lambda: client.pid in match.players, session)
            assert session.start(team_size=1)
            raze = match.players[client.pid]
            assert raze.agent == "raze"
            match.phase, match.phase_until = "live", 100
            raze.pos, host.pos = Vec(20, 20), Vec(20, 34)
            raze.ult_points = 8
            client.send(Command(ability="X", facing=0))
            _wait(lambda: raze.ult_points == 0, session)
            _wait(lambda: match.time >= raze.equip_until, session)
            client.send(Command(fire=True, facing=0))
            _wait(lambda: any(e.props.get("sprite") == "raze_rocket" for e in match.effects), session)
            packets = []

            def saw_rocket():
                packets.extend(p["snap"] for p in client.take() if p["type"] == "state")
                return any(e.get("sprite") == "raze_rocket" for snap in packets for e in snap["effects"])

            _wait(saw_rocket, session)
            _wait(lambda: not host.alive, session)
            assert raze.kills == 1 and "raze_showstopper" not in raze.status
        finally:
            client.close()
    finally:
        session.close()
