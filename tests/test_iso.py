from gameplay.geometry import Vec
from gameplay.match import Command
from gameplay.net import apply_snapshot
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from test_chamber import DT, advance, arena
from test_net import _free_port, _wait


def setup_round():
    match = arena()
    iso = match.add_player("Iso", 0, "iso")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    iso.pos, enemy.pos = Vec(20, 20), Vec(20, 35)
    return match, iso, enemy


def test_iso_offline_focus_absorbs_one_hit_and_orb_refreshes(monkeypatch, tmp_path):
    from client.game import Game
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    game = Game(args(agent="iso"))
    assert game.match.players[game.me].agent == "iso"
    game.match.start()
    game.draw()
    match, iso, enemy = setup_round()
    match.tick(DT, {iso.pid: Command(ability="E")})
    advance(match, 1.1)
    match._damage(enemy, iso, 45, "body", "classic")
    assert iso.hp == 100 and "iso_shield" not in iso.status
    match._damage(enemy, iso, 45, "body", "classic")
    assert iso.hp == 55
    enemy2 = match.add_player("Spare", 1, "sage")
    enemy2.pos = Vec(40, 40)
    enemy.hp = 1
    iso.cursor_depth = 15
    match.tick(DT, {iso.pid: Command(fire=True, facing=0, cursor_depth=15)})
    assert not enemy.alive
    assert any(e.props.get("sprite") == "iso_orb" for e in match.effects)
    match._trace(iso, match._weapon_def(iso), Vec(0, 1), Vec(0, 1))
    assert iso.status["iso_shield"] > match.time


def test_iso_screen_stops_shots_and_undercut_crosses_walls():
    from gameplay.geometry import Rect
    from gameplay.world import Wall

    match, iso, enemy = setup_round()
    iso.charges.update(C=1, Q=1)
    match.tick(DT, {iso.pid: Command(ability="C", facing=0, ability_alt=True)})
    advance(match, 0.9)
    screen = next(e for e in match.effects if e.props.get("sprite") == "iso_screen")
    assert 26 < screen.pos.y < 27
    match._trace(iso, match._weapon_def(iso), Vec(0, 1), Vec(0, 1))
    assert enemy.hp == 100 and match.events[-1].data["stop"] == "wall"
    match.world.walls.append(Wall(Rect(18, 30, 22, 31), 3))
    match.tick(DT, {iso.pid: Command(ability="Q", facing=0)})
    advance(match, 0.8)
    assert enemy.status["iso_vulnerable"] > match.time and enemy.status["suppress"] > match.time


def test_deathmatch_kill_contract_cannot_capture_while_caster_is_ghost():
    match = arena()
    match.set_mode("deathmatch")
    assert match.set_rules(allow_cheats=True)
    iso = match.add_player("Iso", 0, "iso")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.time = match.phase_until
    match.tick(0, {})
    iso.pos, enemy.pos = Vec(20, 20), Vec(20, 32)
    iso.ult_points = match.ultimate_cost(iso)
    match.tick(DT, {iso.pid: Command(ability="X", facing=0)})
    assert iso.ult_points == 0
    match.tick(DT, {iso.pid: Command(buy=["tdm:toggle_ghost"])})
    advance(match, 1)
    assert iso.dm_ghost and iso.duel_id == enemy.duel_id == 0
    assert iso.pos == Vec(20, 20) and enemy.pos == Vec(20, 32)


def test_kill_contract_timeout_kills_both_duelists():
    match, iso, enemy = setup_round()
    iso.ult_points = 7
    match.tick(DT, {iso.pid: Command(ability="X", facing=0)})
    advance(match, 1)
    assert iso.duel_id == enemy.duel_id == iso.pid
    advance(match, 15.1)
    assert not iso.alive and not enemy.alive
    assert iso.duel_id == enemy.duel_id == 0


def test_deathmatch_duel_does_not_transfer_station_ammo_to_loadout():
    match = arena()
    match.set_mode("deathmatch")
    iso = match.add_player("Iso", 0, "iso")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.time = match.phase_until
    match.tick(0, {})
    iso.pos, enemy.pos = Vec(20, 20), Vec(20, 32)
    loadout = match._new_weapon("vandal")
    loadout.mag, loadout.reserve = 7, 15
    station = match._new_weapon("shorty")
    station.from_station = True
    station.mag, station.reserve = 1, 0
    iso.dm_stowed_primary = loadout
    iso.weapons["primary"] = station
    iso.slot = "primary"
    iso.ult_points = match.ultimate_cost(iso)
    match.tick(DT, {iso.pid: Command(ability="X", facing=0)})
    advance(match, 4.6)
    assert iso.duel_id == enemy.duel_id == iso.pid
    assert (station.mag, station.reserve) == (1, 0)
    match.tick(DT, {iso.pid: Command(fire=True, facing=90)})
    assert iso.weapon is loadout
    match._kill(iso, enemy, "classic", "body")
    advance(match, 2.1)
    assert iso.duel_id == 0 and iso.weapon is loadout
    assert (loadout.mag, loadout.reserve) == (7, 15)


def test_guest_iso_duels_host_in_isolated_arena_and_returns_with_original_hp():
    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "omen")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "iso")
        try:
            _wait(lambda: client.pid in match.players, session)
            assert session.start(team_size=2)
            iso = match.players[client.pid]
            for p in match.players.values():
                p.is_bot = False
            outsider = next(p for p in match.players.values() if p.pid != host.pid and p.team == host.team)
            match.phase, match.phase_until = "live", 100
            iso.pos, host.pos, outsider.pos = Vec(20, 20), Vec(20, 32), Vec(42, 42)
            match.spike_carrier = iso.pid
            iso.ult_points, iso.hp = 7, 38
            remote = arena()
            positions = {}
            apply_snapshot(remote, match.snapshot(iso.pid), iso.pid, predict_own=True, server_pos=positions)
            predicted = remote.players[iso.pid]
            predicted.vel, predicted.vz = Vec(3, 0), 2.0
            client.send(Command(ability="X", facing=0))
            _wait(lambda: bool(iso.duel_id), session)
            assert iso.duel_id == host.duel_id and iso.hp == 100 and iso.ult_points == 0
            assert match.spike_carrier is None and match.spike_pos == Vec(20, 20)
            apply_snapshot(remote, match.snapshot(iso.pid), iso.pid, predict_own=True, server_pos=positions)
            assert predicted.duel_bounds == iso.duel_bounds and predicted.pos == iso.pos
            assert predicted.vel == Vec(0, 0) and predicted.vz == 0
            assert all(row["pid"] != iso.pid for row in match.snapshot(outsider.pid)["players"])
            match._damage(outsider, iso, 100, "body", "classic")
            assert iso.hp == 100
            advance(match, 4.6)
            match._damage(iso, host, 150, "head", "classic")
            advance(match, 2.1)
            assert not host.alive and iso.duel_id == 0 and iso.hp == 38 and iso.pos == Vec(20, 20)
            predicted.vel, predicted.vz = Vec(0, 3), 2.0
            apply_snapshot(remote, match.snapshot(iso.pid), iso.pid, predict_own=True, server_pos=positions)
            assert predicted.duel_id == 0 and predicted.pos == iso.pos
            assert predicted.vel == Vec(0, 0) and predicted.vz == 0
        finally:
            client.close()
    finally:
        session.close()
