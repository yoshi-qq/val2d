from gameplay.geometry import Vec
from gameplay.match import Command
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from test_chamber import DT, advance, arena
from test_net import _free_port, _wait


def test_skye_offline_menu_healing_hawk_and_seekers(monkeypatch, tmp_path):
    import pygame
    from client.game import Game
    from menu import MainMenu
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    pygame.init()
    menu = MainMenu(pygame.display.set_mode((1280, 720)), pygame.font.Font(None, 22),
                    pygame.font.Font(None, 22), args())
    menu.activate("agent:skye")
    menu.activate("pick_agent")
    game = Game(menu.activate("start"))
    assert game.match.players[game.me].agent == "skye"
    game.draw()

    match = arena()
    skye = match.add_player("Skye", 0, "skye")
    ally = match.add_player("Ally", 0, "omen")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 120
    skye.pos, ally.pos, enemy.pos = Vec(20, 20), Vec(23, 20), Vec(20, 31)
    skye.hp = ally.hp = enemy.hp = 50
    skye.charges["C"] = 1
    match.tick(DT, {skye.pid: Command(ability="C")})
    for _ in range(64):
        match.tick(DT, {skye.pid: Command(fire=True)})
    assert (skye.hp, ally.hp, enemy.hp) == (50, 70, 50)
    match.tick(DT, {skye.pid: Command(slot="sidearm")})
    match.tick(DT, {skye.pid: Command(ability="C")})
    assert skye.passive_state["skye_heal_pool"] == 80

    match.tick(DT, {skye.pid: Command(ability="E", facing=0), enemy.pid: Command(facing=180)})
    advance(match, 0.1)
    match.tick(DT, {skye.pid: Command(ability="E")})
    for _ in range(24):
        match.tick(DT, {enemy.pid: Command(facing=180)})
    assert enemy.blind_until > match.time and skye.charges["E"] == 0
    skye.ult_points = 8
    match.tick(DT, {skye.pid: Command(ability="X")})
    advance(match, 2)
    assert enemy.status["skye_seeker_sight"] > match.time
    assert enemy.status["skye_seeker_slow"] > match.time


def test_guest_trailblazer_moves_leaps_and_hits_host():
    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "omen")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "skye")
        try:
            _wait(lambda: client.pid in match.players, session)
            assert session.start(team_size=1)
            skye = match.players[client.pid]
            match.phase, match.phase_until = "live", 100
            skye.pos, host.pos = Vec(20, 20), Vec(20, 30)
            skye.charges["Q"] = 1
            client.send(Command(ability="Q", facing=0))
            _wait(lambda: any(e.props.get("sprite") == "skye_tiger" for e in match.effects), session)
            tiger = next(e for e in match.effects if e.props.get("sprite") == "skye_tiger")
            _wait(lambda: match.time >= tiger.start, session)
            client.send(Command(move_y=1, facing=0))
            _wait(lambda: tiger.pos.y > 22, session)
            client.send(Command(fire=True, facing=0))
            _wait(lambda: host.hp == 70, session)
            assert host.status["concuss"] > match.time and skye.channel_until == 0
            assert skye.pos == Vec(20, 20)
        finally:
            client.close()
    finally:
        session.close()
