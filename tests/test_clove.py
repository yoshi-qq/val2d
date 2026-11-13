from gameplay.geometry import Vec
from gameplay.match import Command
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from test_chamber import DT, advance, arena
from test_net import _free_port, _wait


def setup_round():
    match = arena()
    clove = match.add_player("Clove", 0, "clove")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    clove.pos, enemy.pos = Vec(20, 20), Vec(20, 30)
    return match, clove, enemy


def test_clove_offline_meddle_and_pick_me_up(monkeypatch, tmp_path):
    from client.game import Game
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    game = Game(args(agent="clove"))
    assert game.match.players[game.me].agent == "clove"
    game.match.start()
    game.draw()
    match, clove, enemy = setup_round()
    spare = match.add_player("Spare", 1, "sage")
    spare.pos = Vec(40, 40)
    clove.charges.update(C=1, Q=1)
    match.tick(DT, {clove.pid: Command(ability="Q", facing=0, cursor_depth=12.5)})
    advance(match, 2.4)
    assert 8 <= enemy.hp <= 14 and clove.hp == 100
    advance(match, 5)
    assert abs(enemy.hp + enemy.hp_frac - 100) < 1e-6
    enemy.hp = 1
    match.tick(DT, {clove.pid: Command(fire=True, facing=0, cursor_depth=10)})
    assert enemy.alive is False
    match.tick(DT, {clove.pid: Command(ability="C")})
    assert clove.overheal == 50 and clove.status["clove_haste"] > match.time


def test_clove_last_player_can_revive_but_dies_without_a_takedown():
    match, clove, enemy = setup_round()
    clove.ult_points = 8
    match._kill(enemy, clove, "classic", "head")
    match.tick(DT, {})
    assert match.phase == "live"
    match.tick(DT, {clove.pid: Command(ability="X")})
    advance(match, 1.6)
    assert clove.alive and clove.status["clove_phase"] > match.time
    match.tick(DT, {clove.pid: Command(ability="X")})
    assert "clove_phase" not in clove.status
    advance(match, 10.9)
    assert not clove.alive


def test_guest_clove_casts_ruse_after_death_and_survives_with_damaging_assist():
    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "omen")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "clove")
        try:
            _wait(lambda: client.pid in match.players, session)
            assert session.start(team_size=2)
            clove = match.players[client.pid]
            for p in match.players.values():
                p.is_bot = False
            ally = next(p for p in match.players.values() if p.pid != clove.pid and p.team == clove.team)
            match.phase, match.phase_until = "live", 100
            clove.pos, host.pos = Vec(20, 20), Vec(20, 30)
            clove.charges["E"], clove.ult_points = 2, 8
            match._kill(host, clove, "classic", "head")
            assert clove.charges["E"] == 1
            client.send(Command(ability="E", points=[(20, 27), (20, 32)]))
            _wait(lambda: any(e.props.get("sprite") == "clove_smoke_dead" for e in match.effects), session)
            smoke, = [e for e in match.effects if e.props.get("sprite") == "clove_smoke_dead"]
            assert smoke.until - smoke.start == 6
            client.send(Command(ability="X"))
            _wait(lambda: clove.alive, session)
            advance(match, 3)
            match._damage(clove, host, 25, "body", "classic")
            host.hp = 1
            ally.pos = Vec(21, 30)
            match.tick(DT, {ally.pid: Command(fire=True, facing=270, cursor_depth=1)})
            assert not host.alive
            assert clove.alive and "clove_second_chance" not in clove.status
        finally:
            client.close()
    finally:
        session.close()
