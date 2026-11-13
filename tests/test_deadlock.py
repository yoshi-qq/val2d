from gameplay.geometry import Rect, Vec
from gameplay.match import Command
from gameplay.net import apply_snapshot
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from gameplay.world import Wall
from test_chamber import DT, advance, arena
from test_net import _free_port, _wait


def setup_round(match):
    deadlock = match.add_player("Deadlock", 0, "deadlock")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    deadlock.pos, enemy.pos = Vec(20, 20), Vec(20, 35)
    return deadlock, enemy


def objects(match, name):
    return [e for e in match.effects if e.props.get("sprite") == f"deadlock_{name}" and not e.props.get("ended")]


def test_offline_deadlock_and_gravnet_hold_to_remove(monkeypatch, tmp_path):
    from client.game import Game
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    game = Game(args(agent="deadlock"))
    assert game.match.players[game.me].agent == "deadlock"
    game.match.start()
    game.draw()
    me = game.match.players[game.me]
    me.status["deadlock_netted"] = float("inf")
    game.draw_statuses(me)

    match = arena()
    deadlock, enemy = setup_round(match)
    enemy.pos = Vec(21, 30)
    match.tick(DT, {deadlock.pid: Command(ability="E", facing=0, cursor_depth=25, ability_alt=True)})
    advance(match, 1.2)
    assert enemy.crouching and "deadlock_netted" in enemy.status
    assert not deadlock.status.get("deadlock_netted")
    for _ in range(65):
        match.tick(DT, {enemy.pid: Command(interact=True, jump=True)})
    assert enemy.z == 0 and enemy.crouching and "deadlock_netted" in enemy.status
    advance(match, 0.1)
    for _ in range(95):
        match.tick(DT, {enemy.pid: Command(interact=True)})
    assert "deadlock_netted" in enemy.status
    match.tick(DT, {enemy.pid: Command(interact=True)})
    assert "deadlock_netted" not in enemy.status


def test_mesh_blocks_walk_but_passes_fire_and_loses_arm_when_node_breaks():
    match = arena()
    deadlock, enemy = setup_round(match)
    deadlock.charges["C"] = 1
    match.tick(DT, {deadlock.pid: Command(ability="C", facing=0, cursor_depth=12.5)})
    advance(match, 4)
    assert sorted(e.data["hp"] for e in objects(match, "node")) == [480, 480, 480, 480, 1200]
    assert len(match.ability_walls()) == 4
    remote = arena()
    apply_snapshot(remote, match.snapshot(deadlock.pid), deadlock.pid)
    assert remote.ability_walls() == match.ability_walls()
    deadlock.pos, enemy.pos = Vec(24, 28), Vec(24, 34)
    for _ in range(45):
        match.tick(DT, {enemy.pid: Command(move_y=1, facing=180)})
    assert enemy.pos.y >= 30.4
    match._trace(deadlock, match._weapon_def(deadlock), Vec(0, 1), Vec(0, 1))
    assert enemy.hp < 100
    node = next(e for e in objects(match, "node") if e.pos == Vec(30, 30) and e.data["hp"] == 480)
    node.data["hp"] = 1
    deadlock.pos = Vec(30, 28)
    match._trace(deadlock, match._weapon_def(deadlock), Vec(0, 1), Vec(0, 1))
    assert len(match.ability_walls()) == 3


def test_sonic_sensor_ignores_walking_and_triggers_on_gunfire():
    match = arena()
    match.world.walls.append(Wall(Rect(13, 30, 27, 31), 3))
    deadlock, enemy = setup_round(match)
    deadlock.charges["Q"] = 2
    match.tick(DT, {deadlock.pid: Command(ability="Q", facing=0, cursor_depth=12)})
    advance(match, 2)
    match.tick(DT, {deadlock.pid: Command(interact=True, facing=0, cursor_depth=9.7)})
    assert deadlock.charges["Q"] == 2
    match.tick(DT, {deadlock.pid: Command(ability="Q", facing=0, cursor_depth=12)})
    advance(match, 2)
    sensor = objects(match, "sensor")[0]
    enemy.pos = Vec(20, 24)
    for _ in range(45):
        match.tick(DT, {enemy.pid: Command(walk=True, move_x=1, facing=0)})
    assert "trigger_at" not in sensor.data
    match.tick(DT, {enemy.pid: Command(fire=True, facing=90)})
    assert "trigger_at" in sensor.data
    advance(match, 0.6)
    assert enemy.status["concuss"] > match.time and not objects(match, "sensor")


def test_annihilation_bounces_and_executes_after_seven_seconds():
    match = arena()
    match.world.walls.append(Wall(Rect(10, 30, 55, 31), 3))
    deadlock, enemy = setup_round(match)
    enemy.pos = Vec(42, 16)
    deadlock.ult_points = 7
    match.tick(DT, {deadlock.pid: Command(ability="X", facing=45)})
    advance(match, 1.15)
    match.tick(DT, {deadlock.pid: Command(fire=True, facing=45)})
    advance(match, 1.1)
    cocoon = objects(match, "cocoon")[0]
    assert cocoon.data["victim"] == enemy.pid
    assert len(cocoon.data["path"]) >= 2
    assert enemy.status["deadlock_cocooned"] > match.time
    advance(match, 7)
    assert not enemy.alive and deadlock.kills == 1


def test_guest_annihilation_cocoon_can_be_destroyed_by_host_teammate():
    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "omen")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "deadlock")
        try:
            _wait(lambda: client.pid in match.players, session)
            assert session.start(team_size=2)
            deadlock = match.players[client.pid]
            rescuer = next(p for p in match.players.values() if p.pid != host.pid and p.team == host.team)
            for player in match.players.values():
                player.is_bot = False
            match.phase, match.phase_until = "live", 100
            deadlock.pos, host.pos, rescuer.pos = Vec(20, 20), Vec(20, 32), Vec(24, 32)
            deadlock.ult_points = 7
            client.send(Command(ability="X", facing=0))
            _wait(lambda: ("deadlock_accelerator_equipped" in deadlock.status
                           and match.time >= deadlock.equip_until and deadlock.prev_ability is None), session)
            client.send(Command(fire=True, facing=0))
            _wait(lambda: bool(objects(match, "cocoon")), session)
            cocoon = objects(match, "cocoon")[0]
            assert deadlock.agent == "deadlock" and cocoon.data["victim"] == host.pid
            assert cocoon.data["hp"] == 600 and host.status["deadlock_cocooned"] > match.time
            assert any(e["sprite"] == "deadlock_cocoon" for e in match.snapshot(host.pid)["effects"])
            aim = (cocoon.pos - rescuer.pos).normalized()
            for _ in range(40):
                if cocoon.props.get("ended"):
                    break
                match._trace(rescuer, match._weapon_def(rescuer), aim, aim)
            assert cocoon.props["ended"] and host.hp == 100 and "deadlock_cocooned" not in host.status
        finally:
            client.close()
    finally:
        session.close()


def test_accelerator_reequip_and_timeout():
    match = arena()
    deadlock, _ = setup_round(match)
    deadlock.ult_points = 7
    match.tick(DT, {deadlock.pid: Command(ability="X")})
    deadline = deadlock.status["deadlock_accelerator_ready"]
    assert deadlock.ult_points == 0 and not objects(match, "pulse")
    match.tick(DT, {deadlock.pid: Command(slot="melee")})
    assert "deadlock_accelerator_equipped" not in deadlock.status
    match.tick(DT, {deadlock.pid: Command(ability="X")})
    assert deadlock.status["deadlock_accelerator_equipped"] == deadline
    assert 0.69 < deadlock.equip_until - match.time < 0.71
    advance(match, 10)
    match.tick(DT, {deadlock.pid: Command(fire=True)})
    assert "deadlock_accelerator_equipped" not in deadlock.status and not objects(match, "pulse")
