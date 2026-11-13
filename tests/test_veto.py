import pytest

from gameplay.geometry import Vec
from gameplay.kit import statuses
from gameplay.match import Command
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from test_chamber import DT, advance, arena
from test_net import _free_port, _wait


def setup_round():
    match = arena()
    veto = match.add_player("Veto", 0, "veto")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    veto.pos, enemy.pos = Vec(20, 20), Vec(20, 35)
    return match, veto, enemy


def cast(match, player, key, **kwargs):
    match.tick(DT, {player.pid: Command(ability=key, **kwargs)})


def test_veto_offline_crosscut_and_evolution(monkeypatch, tmp_path):
    from client.game import Game
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    game = Game(args(agent="veto"))
    assert game.match.players[game.me].agent == "veto"
    game.match.start()
    game.draw()
    match, veto, enemy = setup_round()
    veto.charges["C"] = 2
    cast(match, veto, "C", facing=0, cursor_depth=8)
    advance(match, 0.8)
    cast(match, veto, "C", facing=0)
    advance(match, 1.7)
    assert veto.pos == Vec(20, 28) and veto.charges["C"] == 1
    veto.ult_points = 7
    cast(match, veto, "X")
    advance(match, 1.1)
    statuses.apply_status(match, veto, "suppress", 4)
    match._damage(enemy, veto, 40, "body", "ability:Paint Shells")
    assert veto.hp == 100 and not statuses.has(match, veto, "suppress")
    match._damage(enemy, veto, 40, "body", "classic")
    assert veto.hp == 60
    advance(match, 1.2)
    assert veto.hp == 100


@pytest.mark.parametrize("duel", [False, True])
def test_deathmatch_crosscut_respects_ghost_and_duel(duel):
    match, veto, enemy = setup_round()
    match.phase = "lobby"
    match.set_mode("deathmatch")
    assert match.set_rules(allow_cheats=True)
    match.start()
    match.time = match.phase_until
    match.tick(0, {})
    veto.pos = Vec(20, 20)
    veto.charges["C"] = 1
    cast(match, veto, "C", facing=0, cursor_depth=8)
    advance(match, 0.8)
    cast(match, veto, "C", facing=0)
    assert any(e.props.get("interruptible_teleport") for e in match.effects)
    if duel:
        veto.duel_id = enemy.pid
    else:
        match.tick(DT, {veto.pid: Command(buy=["tdm:toggle_ghost"])})
    advance(match, 1.2)
    assert veto.pos == Vec(20, 20)


def test_crosscut_can_be_reclaimed_during_buy_phase():
    match, veto, _ = setup_round()
    match.phase = "buy"
    veto.charges["C"] = 1
    cast(match, veto, "C", facing=0, cursor_depth=8)
    advance(match, 0.8)
    assert veto.charges["C"] == 0
    match.tick(DT, {veto.pid: Command(interact=True, facing=0, cursor_depth=8)})
    assert veto.charges["C"] == 1
    assert not any(e.props.get("sprite") == "veto_vortex" for e in match.effects)


def test_veto_chokehold_deafens_decays_and_tethers():
    match, veto, enemy = setup_round()
    veto.charges["Q"] = 1
    enemy.pos = Vec(20, 29)
    cast(match, veto, "Q", facing=0, cursor_depth=12.5)
    advance(match, 2.8)
    assert enemy.hp < 35 and enemy.status["veto_tether"] > match.time and enemy.status["deaf"] > match.time
    for _ in range(100):
        match.tick(DT, {enemy.pid: Command(move_y=1, facing=0)})
    assert enemy.pos.y <= 36.581
    advance(match, 4.5)
    assert abs(enemy.hp + enemy.hp_frac - 100) < 1e-6


@pytest.mark.parametrize(("action", "seconds"),
                         [("activate", 40), ("destroy", 40), ("recall", 5), ("respawn", 40), ("revive", 40)])
def test_deathmatch_guest_interceptor_recharges(action, seconds):
    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "sage" if action == "revive" else "omen")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "veto")
        try:
            _wait(lambda: client.pid in match.players, session)
            if action == "revive":
                client.choose_team(0)
                _wait(lambda: match.players[client.pid].team == 0, session)
            assert session.configure_lobby(mode="deathmatch")
            assert session.start(team_size=2 if action == "revive" else 1)
            match = session.match
            veto = match.players[client.pid]
            match.time = match.phase_until
            session.step(0)
            veto.pos = Vec(20, 20)
            client.send(Command(ability="E", facing=0, cursor_depth=5))
            _wait(lambda: any(e.props.get("sprite") == "veto_interceptor" and match.time >= e.start
                              for e in match.effects) and veto.prev_ability is None, session)
            veto.recharge_timers["E"] = 40
            if action == "respawn":
                match._kill(None, veto, "test", "body")
                match.time = veto.died_at + match.deathmatch_rules["respawn"]
                session.step(0)
                assert veto.alive and statuses.has(match, veto, "veto_interceptor_ready")
                veto.pos = Vec(20, 20)
            elif action == "revive":
                host.pos = veto.pos
                host.ult_points = match.ultimate_cost(host)
                match._kill(None, veto, "test", "body")
                session.step(0, {host.pid: Command(ability="X", cursor_depth=0)})
                marker = next(e for e in match.effects if e.props.get("revive_pid") == veto.pid)
                match.time = marker.until
                session.step(0)
                assert veto.alive and statuses.has(match, veto, "veto_interceptor_ready")
                match.time = veto.channel_until
            session.step(0)
            assert veto.charges["E"] == 0
            if action == "destroy":
                from gameplay.kit.engine import remove_device

                device = next(e for e in match.effects if e.props.get("sprite") == "veto_interceptor")
                veto.recharge_timers["E"] = 39
                remove_device(match, device, "destroy")
            elif action == "recall":
                client.send(Command(interact=True, facing=0, cursor_depth=5))
            else:
                client.send(Command(ability="E"))
            _wait(lambda: bool(veto.dm_device_recalls.get("E")), session)
            deadline = veto.dm_device_recalls["E"][0]
            assert deadline - match.time == pytest.approx(seconds, abs=0.1)
            match.time = deadline - 0.01
            session.step(0)
            assert veto.charges["E"] == 0
            match.time = deadline
            session.step(0)
            assert veto.charges["E"] == 1
            assert veto.recharge_timers["E"] == 0
        finally:
            client.close()
    finally:
        session.close()


def test_guest_interceptor_destroys_host_missile_before_landing():
    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "tejo")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "veto")
        try:
            _wait(lambda: client.pid in match.players, session)
            assert session.start(team_size=1)
            veto = match.players[client.pid]
            match.phase, match.phase_until = "live", 100
            veto.pos, host.pos = Vec(20, 20), Vec(20, 36)
            client.send(Command(ability="E", facing=0, cursor_depth=5))
            _wait(lambda: any(e.props.get("sprite") == "veto_interceptor" and match.time >= e.start
                              for e in match.effects) and veto.prev_ability is None, session)
            client.send(Command(ability="E"))
            _wait(lambda: any(e.data.get("active_at", 999) <= match.time for e in match.effects), session)
            host.charges["E"] = 1
            match.tick(DT, {host.pid: Command(ability="E", points=[(20, 20)])})
            assert host.charges["E"] == 0
            assert any(e.props.get("sprite") == "veto_beam" for e in match.effects)
            advance(match, 4)
            assert veto.hp == 100 and not any(e.props.get("sprite") == "tejo_blast" for e in match.effects)
        finally:
            client.close()
    finally:
        session.close()
