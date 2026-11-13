from gameplay.geometry import Rect, Vec
from gameplay.match import Command
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from gameplay.world import Wall
from test_chamber import DT, advance, arena
from test_net import _free_port, _wait


def test_yoru_offline_selection_clone_blindside_and_drift(tmp_path, monkeypatch):
    from client.game import Game
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    game = Game(args(agent="yoru"))
    assert game.match.players[game.me].agent == "yoru"
    game.match.start()
    game.draw()
    match = arena()
    yoru = match.add_player("Yoru", 0, "yoru")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    yoru.pos, enemy.pos = Vec(20, 20), Vec(20, 28)
    yoru.charges.update(C=1, Q=1)
    match.tick(DT, {yoru.pid: Command(ability="C", facing=0)})
    advance(match, 0.8)
    decoy = next(e for e in match.effects if e.props.get("sprite") == "yoru_clone")
    assert decoy.pos.y > 23
    enemy.weapons["primary"] = match._new_weapon("operator")
    enemy.slot, enemy.equip_until, enemy.zoom_level = "primary", 0, 1
    match.tick(DT, {enemy.pid: Command(fire=True, facing=180, cursor_depth=enemy.pos.y - decoy.pos.y)})
    assert decoy not in match.effects
    for _ in range(45):
        match.tick(DT, {enemy.pid: Command(facing=180)})
    assert enemy.blind_until > match.time
    match.world.walls.append(Wall(Rect(18, 29, 22, 30), 3))
    match.tick(DT, {yoru.pid: Command(ability="Q", facing=0, cursor_depth=12)})
    flash = next(e for e in match.effects if e.kind == "flash")
    assert flash.pos.y < 29 and flash.start > match.time

    yoru.ult_points = 8
    match.tick(DT, {yoru.pid: Command(ability="X")})
    advance(match, 0.5)
    assert "yoru_drift" in yoru.status and not match.can_see(enemy, yoru)
    match._damage(enemy, yoru, 150, "body", "operator")
    assert yoru.hp == 100
    match.tick(DT, {yoru.pid: Command(ability="X")})
    assert "yoru_drift" not in yoru.status and yoru.equip_until > match.time


def test_guest_teleports_through_gatecrash_without_spending_a_second_charge():
    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "omen")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "yoru")
        try:
            _wait(lambda: client.pid in match.players, session)
            assert session.start(team_size=1)
            yoru = match.players[client.pid]
            match.phase, match.phase_until = "live", 100
            yoru.pos, host.pos = Vec(20, 20), Vec(20, 40)
            yoru.charges["E"] = 2
            client.send(Command(ability="E", ability_alt=True, facing=0))
            _wait(lambda: "yoru_gate" in yoru.status and yoru.prev_ability is None, session)
            assert not any(e.get("sprite") == "yoru_gate" for e in match.snapshot(host.pid)["effects"])
            yoru.pos = Vec(20, 30)
            client.send(Command(ability="E"))
            _wait(lambda: yoru.pos == Vec(20, 20), session)
            assert yoru.charges["E"] == 1 and "yoru_gate" not in yoru.status
            snapshots = []

            def guest_received_arrival():
                snapshots.extend(packet["snap"] for packet in client.take() if packet["type"] == "state")
                return any(row["pid"] == yoru.pid and row["y"] == 20 and row["charges"]["E"] == 1
                           and "yoru_gate" not in row["status"] for snap in snapshots for row in snap["players"])

            _wait(guest_received_arrival, session)
        finally:
            client.close()
    finally:
        session.close()
