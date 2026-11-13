import socket
import time

import pytest

from gameplay.geometry import Rect, Vec
from gameplay.match import Command, Match, playable_agents
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from gameplay.world import Site, WorldMap

DT = 1 / 64


def arena():
    return Match(WorldMap("test", "Test", 65, 65, spawns={0: [Vec(20, 20)], 1: [Vec(55, 55)]},
                          sites=[Site("A", Rect(17, 28, 24, 35))]), agent_roster=playable_agents())


def tick(match, seconds, commands=None):
    for _ in range(round(seconds / DT)):
        match.tick(DT, commands or {})


def offline(mode="standard"):
    match = arena()
    gekko = match.add_player("Gekko", 0, "gekko")
    enemy = match.add_player("Enemy", 1, "omen")
    match.set_mode(mode)
    match.start()
    match.time = match.phase_until
    match.tick(0, {})
    return match, gekko, enemy


def test_gekko_starts_from_the_offline_agent_menu(monkeypatch, tmp_path):
    import pygame
    from client.game import Game
    from menu import MainMenu
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    font = pygame.font.Font(None, 22)
    menu = MainMenu(screen, font, font, args())
    menu.activate("agent:gekko")
    menu.activate("pick_agent")
    game = Game(menu.activate("start"))
    assert game.match.players[game.me].agent == "gekko"
    game.draw()


@pytest.mark.parametrize(("mode", "delay"), [("standard", 15), ("deathmatch", 3)])
def test_mosh_explodes_in_two_damage_bands_and_can_be_reclaimed(mode, delay):
    match, gekko, enemy = offline(mode)
    gekko.pos, enemy.pos = Vec(20, 20), Vec(20, 34)
    enemy.hp = 100
    enemy.armor, enemy.armor_reserve, enemy.armor_key = 0, 0, ""
    gekko.charges["C"] = 1
    match.tick(DT, {gekko.pid: Command(ability="C", facing=0, cursor_depth=10)})
    tick(match, 3.2)
    assert 69 <= enemy.hp < 80
    tick(match, 0.75)
    assert not enemy.alive
    globule = next(e for e in match.effects if e.props.get("gekko_globule"))
    assert globule.until - globule.start == 20

    match.phase, match.phase_until = "live", 100
    enemy.alive, enemy.hp = True, 100
    gekko.pos = globule.pos
    tick(match, 1.25, {gekko.pid: Command(interact=True)})
    assert not gekko.ability_ready_at and not gekko.dm_device_recalls
    tick(match, 0.15)
    tick(match, 1.5, {gekko.pid: Command(interact=True)})
    tick(match, delay - DT)
    assert gekko.charges["C"] == 0
    tick(match, DT)
    assert gekko.charges["C"] == 1


@pytest.mark.parametrize(("mode", "delay"), [("standard", 15), ("deathmatch", 3)])
def test_dizzy_and_thrash_blind_and_detain_with_one_ultimate_reclaim(mode, delay):
    match, gekko, enemy = offline(mode)
    gekko.pos, enemy.pos = Vec(20, 20), Vec(20, 31)
    match.tick(DT, {gekko.pid: Command(ability="E", facing=0, cursor_depth=10)})
    tick(match, 1.1)
    assert enemy.status["gekko_plasma_blind"] > match.time
    tick(match, 0.6)
    dizzy = next(e for e in match.effects if e.props.get("gekko_globule"))

    gekko.ult_points = match.ultimate_cost(gekko)
    match.tick(DT, {gekko.pid: Command(ability="X", facing=0)})
    tick(match, 0.75)
    match.tick(DT, {gekko.pid: Command(fire=True, facing=0)})
    tick(match, 0.4)
    match.tick(DT, {gekko.pid: Command(fire=True, facing=0)})
    assert enemy.status["gekko_detained"] > match.time
    assert gekko.channel_until == 0 and gekko.ult_points == 0
    globule = next(e for e in match.effects if e.props.get("key") == "X")
    if mode == "deathmatch":
        assert match.ultimate_cost(gekko) == 70
        gekko.pos = dizzy.pos
        tick(match, 1.5, {gekko.pid: Command(interact=True)})
        ready = gekko.dm_device_recalls["E"][0]
        gekko.recharge_timers["E"] = 43.99
        tick(match, 0.1)
        assert gekko.charges["E"] == 0
        match.time = ready - DT
        match.tick(DT, {})
        assert gekko.charges["E"] == 1 and "E" not in gekko.dm_device_recalls
    gekko.pos = globule.pos
    tick(match, 1.5, {gekko.pid: Command(interact=True)})
    tick(match, delay - DT)
    assert "gekko_thrash_ready" not in gekko.status
    tick(match, DT)
    assert "gekko_thrash_ready" in gekko.status
    match.tick(DT, {gekko.pid: Command(ability="X", facing=0)})
    assert gekko.channel_until > match.time
    tick(match, 0.1)
    match.tick(DT, {gekko.pid: Command(ability="X")})
    assert gekko.channel_until == 0
    assert not any(e.props.get("key") == "X" for e in match.effects)


def test_wingman_defuses_and_credits_gekko():
    match, gekko, enemy = offline()
    match.attacking_team = enemy.team
    match.phase, match.spike_pos = "planted", Vec(20, 30)
    gekko.pos, enemy.pos = Vec(20, 20), Vec(55, 55)
    gekko.charges["Q"] = 1
    match.tick(DT, {gekko.pid: Command(ability="Q", ability_alt=True, facing=0, cursor_depth=10)})
    tick(match, 5.5)
    assert match.spike_half_defused and gekko.defuses == 0
    tick(match, 4)
    assert gekko.defuses == 1 and match.phase == "end"


@pytest.mark.parametrize("outcome", ["detour", "reopen", "expire"])
def test_wingman_reacts_to_door_closed_after_cast(outcome):
    from gameplay.world import Deck, Wall

    match, gekko, enemy = offline()
    gekko.pos, enemy.pos = Vec(20, 20), Vec(55, 55)
    if outcome == "expire":
        match.world.decks.append(Deck(Rect(18, 18, 22, 23), 1, 0))
    door = Wall(Rect(17, 24, 23, 25) if outcome == "detour" else Rect(0, 24, match.world.width, 25), 3, door=True)
    match.world.walls.append(door)
    match.open_doors.add(door.rect)
    match.spike_carrier, match.spike_pos = gekko.pid, None
    gekko.charges["Q"] = 1
    match.tick(DT, {gekko.pid: Command(ability="Q", ability_alt=True, facing=0, cursor_depth=11)})
    wingman = next(e for e in match.effects if e.props.get("gekko_objective"))
    assert list(wingman.data["path"]) == [Vec(20, 31)]
    match.open_doors.remove(door.rect)
    if outcome != "detour":
        pos = wingman.pos
        tick(match, 1)
        assert wingman.data["route_blocked"] and wingman.pos == pos
        assert wingman.data["carrying"] and wingman.data["progress"] == 0
        assert match.phase == "live" and match.spike_pos is None
        if outcome == "expire":
            match.time = wingman.until
            match.tick(DT, {})
            assert match.spike_pos == pos and match.spike_carrier is None
            assert match.phase == "live" and gekko.plants == 0
            assert match.spike_ground == 0
            gekko.pos, gekko.ground, gekko.level = pos, 1, 1
            match.time += 1
            match.tick(DT, {gekko.pid: Command(interact=True)})
            assert match.spike_carrier is None
            gekko.ground = gekko.level = 0
            match.tick(DT, {gekko.pid: Command(interact=True)})
            assert match.spike_carrier == gekko.pid
            return
        match.open_doors.add(door.rect)
        tick(match, 0.25)
        assert not wingman.data["route_blocked"] and wingman.pos.y > pos.y
    tick(match, 9)
    assert match.phase == "planted" and match.spike_pos == Vec(20, 31)


@pytest.mark.parametrize("outcome", ["plant", "shot", "reopen", "expire"])
def test_guest_wingman_plant_after_route_changes(outcome):
    from gameplay.world import Deck, Wall

    match = arena()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    session = HostSession(match, "Host", port)
    host = match.add_player("Host", 0, "omen")

    def wait_for(predicate):
        deadline = time.monotonic() + 5
        while not predicate():
            assert time.monotonic() < deadline
            session.step(DT)
            time.sleep(0.003)

    try:
        client = NetClient(f"127.0.0.1:{port}", "Guest", "gekko")
        try:
            wait_for(lambda: client.pid in match.players)
            assert session.start(team_size=1)
            gekko = match.players[client.pid]
            match.attacking_team = gekko.team
            match.phase, match.phase_until = "live", 100
            gekko.pos, host.pos = Vec(20, 20), Vec(20, 37)
            if outcome == "expire":
                match.world.decks.append(Deck(Rect(18, 18, 22, 23), 1, 0))
            door = Wall(Rect(0, 24, match.world.width, 25), 3, door=True)
            if outcome in ("reopen", "expire"):
                match.world.walls.append(door)
                match.open_doors.add(door.rect)
            gekko.charges["Q"] = 1
            match.spike_carrier, match.spike_pos = gekko.pid, None
            client.send(Command(ability="Q", ability_alt=True, facing=0, cursor_depth=11))
            wait_for(lambda: match.spike_carrier is None)
            packets = []

            def received_spike_carrier():
                packets.extend(packet["snap"] for packet in client.take() if packet["type"] == "state")
                return any(e.get("carrying_spike") for snap in packets for e in snap["effects"])

            wait_for(received_spike_carrier)
            if outcome == "shot":
                device = next(e for e in match.effects if e.data.get("carrying"))
                host.pos = device.pos + Vec(5, 0)
                host.weapons["primary"] = match._new_weapon("operator")
                host.slot, host.equip_until = "primary", 0
                host.zoom_level = 1
                events = session.step(DT, {host.pid: Command(fire=True, facing=270, cursor_depth=5)})
                assert any(e.kind == "shot" and e.data["stop"] == "device" for e in events), events
                assert match.phase == "live" and match.spike_pos == device.pos and gekko.plants == 0
                assert any(e.props.get("gekko_globule") for e in match.effects)
            else:
                if outcome in ("reopen", "expire"):
                    wingman = next(e for e in match.effects if e.data.get("carrying"))
                    match.open_doors.remove(door.rect)
                    wait_for(lambda: wingman.data.get("route_blocked"))
                    pos = wingman.pos
                    for _ in range(16):
                        session.step(DT)
                    assert wingman.pos == pos and wingman.data["progress"] == 0
                    assert match.phase == "live" and match.spike_pos is None
                    if outcome == "expire":
                        match.time = wingman.until
                        session.step(DT)
                        assert match.spike_pos == pos and match.spike_carrier is None
                        assert match.phase == "live" and gekko.plants == 0

                        def guest_sees_drop():
                            return any(packet["snap"]["spike"]["pos"] == [pos.x, pos.y]
                                       and packet["snap"]["spike"]["ground"] == 0
                                       for packet in client.take() if packet["type"] == "state")

                        wait_for(guest_sees_drop)
                        gekko.pos, gekko.ground, gekko.level = pos, 1, 1
                        match.time += 1
                        client.send(Command(interact=True))
                        wait_for(lambda: gekko.prev_interact)
                        assert match.spike_carrier is None
                        gekko.ground = gekko.level = 0
                        wait_for(lambda: match.spike_carrier == gekko.pid)
                        return
                    match.open_doors.add(door.rect)
                    wait_for(lambda: wingman.pos.y > pos.y)
                wait_for(lambda: match.phase == "planted")
                assert match.spike_pos == Vec(20, 31) and gekko.plants == 1 and gekko.pos == Vec(20, 20)
                if outcome == "reopen":
                    def guest_sees_plant():
                        packets.extend(packet["snap"] for packet in client.take() if packet["type"] == "state")
                        return any(snap["phase"] == "planted" and snap["spike"]["pos"] == [20, 31] for snap in packets)

                    wait_for(guest_sees_plant)
        finally:
            client.close()
    finally:
        session.close()
