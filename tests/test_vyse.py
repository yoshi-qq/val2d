from gameplay.geometry import Rect, Vec
from gameplay.match import Command
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from gameplay.world import Wall
from test_chamber import DT, advance, arena
from test_net import _free_port, _wait


def setup_round():
    match = arena()
    match.world.walls.append(Wall(Rect(12, 30, 28, 31), 3))
    vyse = match.add_player("Vyse", 0, "vyse")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    vyse.pos, enemy.pos = Vec(20, 20), Vec(25, 25)
    return match, vyse, enemy


def cast(match, player, key, **kwargs):
    match.tick(DT, {player.pid: Command(ability=key, **kwargs)})


def test_offline_vyse_razorvine_damages_only_with_movement(monkeypatch, tmp_path):
    from client.game import Game
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    game = Game(args(agent="vyse"))
    assert game.match.players[game.me].agent == "vyse"
    game.match.start()
    game.draw()

    match, vyse, enemy = setup_round()
    vyse.charges["C"] = 2
    cast(match, vyse, "C", facing=0, cursor_depth=10)
    advance(match, 1.5)
    assert not any(e["sprite"] == "vyse_nest" for e in match.snapshot(enemy.pid)["effects"])
    match.tick(DT, {vyse.pid: Command(interact=True, facing=0, cursor_depth=8)})
    enemy.pos = Vec(21, 27)
    advance(match, 0.8)
    assert enemy.hp == 100 and enemy.status["vyse_vine_slow"] > match.time
    for _ in range(29):
        match.tick(DT, {enemy.pid: Command(move_x=1, facing=0)})
    assert enemy.hp == 90


def test_shear_rises_only_after_enemy_exits_trigger():
    match, vyse, enemy = setup_round()
    vyse.charges["Q"] = 1
    cast(match, vyse, "Q", facing=0, cursor_depth=10)
    advance(match, 2.1)
    enemy.pos = Vec(20, 25)
    match.tick(DT, {})
    assert not match.ability_walls()
    enemy.pos = Vec(19, 25)
    match.tick(DT, {})
    assert len(match.ability_walls()) == 1
    assert not match._line_clear(Vec(17, 25), Vec(22, 25), 0)
    advance(match, 6.1)
    assert not match.ability_walls()


def test_arc_rose_places_through_wall_and_recharges_after_flash():
    match, vyse, enemy = setup_round()
    cast(match, vyse, "E", facing=0, cursor_depth=10, ability_alt=True)
    advance(match, 0.9)
    rose = next(e for e in match.effects if e.props.get("sprite") == "vyse_rose")
    assert rose.pos.y > 31
    enemy.pos, enemy.facing = Vec(20, 36), 180
    cast(match, vyse, "E", facing=90)
    advance(match, 0.6)
    assert enemy.blind_until > match.time and vyse.blind_until <= match.time
    assert vyse.charges["E"] == 0
    advance(match, 20)
    assert vyse.charges["E"] == 1


def test_guest_steel_garden_jams_host_primary_but_leaves_sidearm():
    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "omen")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "vyse")
        try:
            _wait(lambda: client.pid in match.players, session)
            assert session.start(team_size=1)
            vyse = match.players[client.pid]
            assert vyse.agent == "vyse"
            match.phase, match.phase_until = "live", 100
            vyse.pos, host.pos = Vec(20, 20), Vec(24, 22)
            host.weapons["primary"] = match._new_weapon("vandal", host)
            host.slot = "primary"
            vyse.ult_points = 8
            client.send(Command(ability="X"))
            _wait(lambda: host.status.get("vyse_jammed", 0) > match.time, session, timeout=12)
            assert host.slot == "sidearm" and vyse.ult_points == 0
            assert "vyse_jammed" in next(p for p in match.snapshot(host.pid)["players"] if p["pid"] == host.pid)["status"]
            advance(match, 1)
            before = host.weapon.mag
            match.tick(DT, {host.pid: Command(slot="primary", fire=True, facing=90)})
            assert host.slot == "sidearm" and host.weapon.mag == before - 1
            advance(match, 8)
            match.tick(DT, {host.pid: Command(slot="primary")})
            assert host.slot == "primary"
        finally:
            client.close()
    finally:
        session.close()
