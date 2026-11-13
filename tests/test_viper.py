from gameplay.geometry import Vec
from gameplay.match import Command
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from test_chamber import DT, advance, arena
from test_net import _free_port, _wait


def test_viper_offline_selection_snake_bite_and_pit(tmp_path, monkeypatch):
    from client.game import Game
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    game = Game(args(agent="viper"))
    assert game.match.players[game.me].agent == "viper"
    game.match.start()
    game.draw()

    match = arena()
    viper = match.add_player("Viper", 0, "viper")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    viper.pos, enemy.pos = Vec(20, 20), Vec(20, 28)
    viper.charges["C"] = 1
    match.tick(DT, {viper.pid: Command(ability="C", facing=0, cursor_depth=10)})
    advance(match, 1.3)
    assert enemy.hp < 100 and "viper_vulnerable" in enemy.status
    enemy.pos = Vec(26, 20)
    advance(match, 7)
    viper.ult_points = 9
    match.tick(DT, {viper.pid: Command(ability="X", facing=0, cursor_depth=0)})
    advance(match, 5)
    assert enemy.decay_pool >= 30
    viper.pos = Vec(40, 20)
    advance(match, 8.2)
    assert not any(e.props.get("sprite") == "viper_pit" for e in match.effects)


def test_guest_viper_uses_one_fuel_pool_for_two_host_synced_smokes():
    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "omen")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "viper")
        try:
            _wait(lambda: client.pid in match.players, session)
            assert session.start(team_size=1)
            viper = match.players[client.pid]
            match.phase, match.phase_until = "live", 100
            viper.pos, host.pos = Vec(20, 20), Vec(20, 29)
            viper.charges["Q"] = 1
            client.send(Command(ability="Q", facing=0, cursor_depth=10))
            _wait(lambda: "viper_cloud" in viper.status and viper.prev_ability is None, session)
            client.send(Command(ability="E", facing=0))
            _wait(lambda: "viper_screen" in viper.status and viper.prev_ability is None, session)
            client.send(Command(ability="Q", facing=0))
            _wait(lambda: viper.passive_state["viper_fuel"] < 99, session)
            client.send(Command(ability="E", facing=90))
            _wait(lambda: host.decay_pool >= 10 and viper.passive_state["viper_fuel"] < 85, session)
            assert not match._line_clear(Vec(16, 42), Vec(24, 42), 0)
            packets = []

            def saw_both():
                packets.extend(p["snap"] for p in client.take() if p["type"] == "state")
                return any({"viper_cloud", "viper_screen"} <= {e.get("sprite") for e in snap["effects"]}
                           and any(row.get("viper_fuel", 100) is not None and row["viper_fuel"] < 85
                                   for row in snap["players"]) for snap in packets)

            _wait(saw_both, session)
            _wait(lambda: viper.passive_state["viper_fuel"] == 0, session)
            assert match._line_clear(Vec(16, 42), Vec(24, 42), 0)
        finally:
            client.close()
    finally:
        session.close()
