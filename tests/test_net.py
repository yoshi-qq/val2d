"""Network tests over localhost: host session and client in one process, real sockets."""
from __future__ import annotations

import socket
import sys
import time
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from gameplay.match import Command, Match
from gameplay.net import apply_snapshot, command_from_json, recv_msg, send_msg
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from map_fixtures import load_archived_map


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("", 0))
        return int(probe.getsockname()[1])


def _wait(condition: Callable[[], bool], session: HostSession | None = None, timeout: float = 5.0) -> None:
    end = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > end:
            raise TimeoutError("condition not met")
        if session:
            session.step(1 / 64)
        time.sleep(0.005)


@pytest.fixture
def session() -> HostSession:
    s = HostSession(Match(load_archived_map("workyard"), seed=1), "Test host", _free_port())
    yield s
    s.close()


def test_command_from_json_clamps_and_drops_junk() -> None:
    cmd = command_from_json({"move_x": 9, "move_y": "x", "facing": 725, "cursor_depth": -3, "fire": 1,
                             "slot": "rakete", "ability": "Z", "buy": ["phantom", 5, "x" * 40] + ["a"] * 20})
    assert cmd.move_x == 1.0 and cmd.move_y == 0.0
    assert cmd.facing == pytest.approx(5.0)
    assert cmd.cursor_depth == 0.0 and cmd.fire is True
    assert cmd.slot is None and cmd.ability is None
    assert cmd.buy[0] == "phantom" and len(cmd.buy) == 8


def test_snapshot_syncs_inventory_and_resets_interpolation_for_new_contacts() -> None:
    from gameplay.geometry import Vec

    match = Match(load_archived_map("workyard"))
    own = match.add_player("A", 0, "omen")
    enemy = match.add_player("B", 1, "omen")
    match.start()
    own.pos, own.facing = Vec(17, 15), 0
    enemy.pos = Vec(17, 14)
    shadow = Match(match.world)
    positions = {}
    apply_snapshot(shadow, match.snapshot(own.pid), own.pid, server_pos=positions)
    assert shadow.players[own.pid].weapons.keys() == own.weapons.keys()
    remote = shadow.players[enemy.pid]
    assert not remote.visible
    remote.pos = Vec(17, 14)

    enemy.pos = Vec(17, 18)
    apply_snapshot(shadow, match.snapshot(own.pid), own.pid, server_pos=positions)
    assert remote.visible and remote.pos == enemy.pos


def test_client_joins_receives_snapshot_and_moves(session: HostSession) -> None:
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "sage",
                       weapon_skins={"classic": "prime", "tactical_knife": "reaver", "warden": "oni"})
    try:
        assert client.map_key == "workyard"
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        shadow = Match(load_archived_map(client.map_key))
        states: list = []
        _wait(lambda: states.extend(m for m in client.take() if m["type"] == "state") or bool(states), session)
        apply_snapshot(shadow, states[-1]["snap"], client.pid)
        assert client.pid in shadow.players
        assert session.match.players[client.pid].weapon_skins == {"classic": "prime", "tactical_knife": "reaver"}
        assert shadow.players[client.pid].weapons["sidearm"].skin == "prime"
        assert shadow.phase == "buy"
        # skip the buy phase, then walk forward
        session.match.phase_until = session.match.time
        start = session.match.players[client.pid].pos
        for _ in range(40):
            client.send(Command(move_y=1.0, facing=session.match.players[client.pid].facing))
            session.step(1 / 64)
            time.sleep(0.004)
        assert (session.match.players[client.pid].pos - start).length() > 0.3
    finally:
        client.close()


@pytest.mark.parametrize("destroyed", [False, True], ids=["pulse", "destroyed"])
def test_lockdown_report_reaches_only_allied_guest(session: HostSession, destroyed: bool) -> None:
    from contextlib import ExitStack

    from gameplay.geometry import Vec
    from gameplay.net import events_from_json
    from gameplay.world import WorldMap

    match = session.match
    match.world = WorldMap("test", "Test", 120, 120, spawns={0: [Vec(50, 50)], 1: [Vec(100, 100)]})
    caster = match.add_player("Killjoy host", 0, "killjoy")
    address = f"127.0.0.1:{session.net.port}"
    with ExitStack() as stack:
        ally = NetClient(address, "Ally", "sage")
        stack.callback(ally.close)
        enemy = NetClient(address, "Enemy", "omen")
        stack.callback(enemy.close)
        assert session.net.choose_team(ally.pid, caster.team)
        assert session.net.choose_team(enemy.pid, 1 - caster.team)
        assert session.start(team_size=2)
        match.phase, match.phase_until = "live", match.time + 60
        caster.ult_points = match.ultimate_cost(caster)
        match.players[enemy.pid].pos = caster.pos + Vec(3, 0)
        session.step(1 / 64, {caster.pid: Command(ability="X")})
        [device] = [e for e in match.effects if e.props.get("sprite") == "killjoy_lockdown_pulse"]
        if destroyed:
            shooter = match.players[enemy.pid]
            shooter.pos = device.pos + Vec(3, 0)
            shooter.equip_until = 0
            device.data["hp"] = 1
            enemy.send(Command(fire=True, facing=270))
            _wait(lambda: device.props.get("ended", False), session)
            enemy.send(Command(facing=270))
            assert match.time < device.start
        while match.time < device.start:
            session.step(0.125)
        reported = {ally.pid: [], enemy.pid: []}
        state_time = dict.fromkeys(reported, 0.0)

        def received_after_pulse() -> bool:
            for guest in (ally, enemy):
                for message in guest.take():
                    if message["type"] == "events":
                        reported[guest.pid].extend((e.kind, e.data.get("count"))
                                                   for e in events_from_json(message["events"])
                                                   if e.kind in ("lockdown_result", "lockdown_destroyed"))
                    elif message["type"] == "state":
                        state_time[guest.pid] = message["snap"]["time"]
            return all(t > device.start for t in state_time.values()) and bool(reported[ally.pid])

        _wait(received_after_pulse, session)
        expected = ("lockdown_destroyed", None) if destroyed else ("lockdown_result", 1)
        assert reported == {ally.pid: [expected], enemy.pid: []}


@pytest.mark.parametrize("ending", ["leave", "pulse", "destroyed"])
def test_lockdown_warning_tracks_connected_guest(session: HostSession, monkeypatch, ending: str) -> None:
    import numpy as np

    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    from client.common import Sound, UiState, pygame
    from client.events import EventsMixin
    from gameplay.geometry import Vec
    from gameplay.world import WorldMap

    match = session.match
    match.world = WorldMap("test", "Test", 120, 120, spawns={0: [Vec(50, 50)], 1: [Vec(100, 100)]})
    caster = match.add_player("Killjoy host", 0, "killjoy")
    guest = NetClient(f"127.0.0.1:{session.net.port}", "Enemy", "omen")
    client = EventsMixin()
    client.match = Match(match.world, match.cfg, agent_roster=match.agents)
    client.ui = UiState()
    client.sound = Sound()
    try:
        assert client.sound.ok
        assert session.net.choose_team(guest.pid, 1 - caster.team)
        assert session.start(team_size=1)
        match.phase, match.phase_until = "live", match.time + 60
        caster.ult_points = match.ultimate_cost(caster)
        session.step(1 / 64, {caster.pid: Command(ability="X")})
        [device] = [e for e in match.effects if e.props.get("sprite") == "killjoy_lockdown_pulse"]
        cast_at = match.time
        assert device.props["warning_start"] == cast_at < device.start

        def update_guest(ready: Callable[[], bool]) -> None:
            def received_state() -> bool:
                for message in guest.take():
                    if message["type"] == "state":
                        apply_snapshot(client.match, message["snap"], guest.pid)
                return guest.pid in client.match.players and ready()

            _wait(received_state, session)
            client.update_lockdown_audio(client.match.players[guest.pid])

        def has_device() -> bool:
            return any(e.props.get("sprite") == "killjoy_lockdown_pulse" for e in client.match.effects)

        player = match.players[guest.pid]
        outside = device.pos + Vec(device.radius + 1, 0)
        player.pos = outside
        update_guest(lambda: client.match.players[guest.pid].pos == outside and has_device())
        assert not client.ui.lockdown_sounds
        for _ in range(16):
            session.step(1 / 64)
        inside = device.pos + Vec(3, 0)
        player.pos = inside
        update_guest(lambda: client.match.players[guest.pid].pos == inside and has_device())
        [channel] = client.ui.lockdown_sounds.values()
        assert channel.get_busy()
        [replica] = [e for e in client.match.effects if e.props.get("sprite") == "killjoy_lockdown_pulse"]
        assert replica.props["warning_start"] == cast_at
        listener = client.match.players[guest.pid]
        _, _, muffled = client.sound.spatial_mix(
            listener, replica.pos, replica.radius * 1.25, client.occluded(listener, replica.pos), 0.55
        )
        source = (client.sound.muffled if muffled else client.sound.sounds)["lockdown_warning"]
        elapsed_ms = round((client.match.time - cast_at) * 1_000_000_000) // 1_000_000
        frames = round(elapsed_ms * pygame.mixer.get_init()[0] / 1000)
        assert np.array_equal(pygame.sndarray.array(channel.get_sound()),
                              np.roll(pygame.sndarray.array(source), -frames, axis=0))
        if ending == "leave":
            player.pos = outside
            update_guest(lambda: client.match.players[guest.pid].pos == outside)
            assert match.time < device.start
        elif ending == "pulse":
            while match.time < device.start:
                session.step(1 / 64)
            update_guest(lambda: client.match.time >= device.start and has_device())
        else:
            player.equip_until = 0
            device.data["hp"] = 1
            guest.send(Command(fire=True, facing=270))
            update_guest(lambda: device.props.get("ended", False) and not has_device())
            assert match.time < device.start
        if ending != "leave":
            assert client.match.players[guest.pid].pos == inside
        assert not client.ui.lockdown_sounds and not channel.get_busy()
    finally:
        client.update_lockdown_audio(None)
        guest.close()


@pytest.mark.parametrize("ending", ["shot", "pilot_hit", "cancel", "expiry"])
def test_owl_drone_rotor_stops_for_connected_guest(session: HostSession, monkeypatch, ending: str) -> None:
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    from client.common import Sound, UiState
    from client.events import EventsMixin
    from gameplay.geometry import Vec
    from gameplay.net import events_from_json
    from gameplay.world import WorldMap

    match = session.match
    match.world = WorldMap("test", "Test", 120, 120, spawns={0: [Vec(50, 50)], 1: [Vec(100, 100)]})
    caster = match.add_player("Sova host", 0, "sova")
    client = EventsMixin()
    client.match = Match(match.world, match.cfg, agent_roster=match.agents)
    client.ui, client.sound = UiState(), Sound()
    address = f"127.0.0.1:{session.net.port}"
    guest = NetClient(address, "Enemy", "omen")
    observer = None
    try:
        observer = NetClient(address, "Other enemy", "sage")
        assert client.sound.ok
        assert session.net.choose_team(guest.pid, 1 - caster.team)
        assert session.net.choose_team(observer.pid, 1 - caster.team)
        assert session.start(team_size=2)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match.phase, match.phase_until = "live", match.time + 60
        caster.charges["C"] = 1
        session.step(1 / 64, {caster.pid: Command(ability="C", facing=0)})
        [drone] = [e for e in match.effects if e.props.get("sprite") == "sova_owl_drone"]
        shooter = match.players[guest.pid]
        shooter.pos = drone.pos + Vec(0, 6)
        match.players[observer.pid].pos = drone.pos + Vec(12, 5)
        confirmations = []
        dart_hits = []

        def update_guest(ready: Callable[[], bool]) -> None:
            def received_state() -> bool:
                for message in guest.take():
                    if message["type"] == "state":
                        apply_snapshot(client.match, message["snap"], guest.pid)
                    elif message["type"] == "events":
                        events = events_from_json(message["events"])
                        confirmations.extend(e for e in events if e.kind == "device_hit_audio")
                        dart_hits.extend(e for e in events if e.kind == "owl_dart_hit")
                return guest.pid in client.match.players and ready()

            _wait(received_state, session)
            listener = client.match.players[guest.pid]
            client.update_rotor_audio(listener)
            client.update_drone_warning(listener)

        def drone_positions() -> list[Vec]:
            return [e.pos for e in client.match.effects if e.props.get("sprite") == "sova_owl_drone"]

        start = drone.pos
        _wait(lambda: match.time >= drone.start, session)
        update_guest(lambda: client.match.time >= drone.start and bool(drone_positions())
                     and client.match.players[guest.pid].pos == shooter.pos)
        [channel] = client.ui.rotor_sounds.values()
        assert channel.get_busy()
        for _ in range(32):
            session.step(1 / 64, {caster.pid: Command(move_y=1, facing=0)})
        assert (drone.pos - start).length() >= 1
        update_guest(lambda: any((pos - start).length() >= 1 for pos in drone_positions()))
        assert list(client.ui.rotor_sounds.values()) == [channel]
        if ending != "shot":
            if ending == "cancel":
                session.step(1 / 64, {caster.pid: Command(ability="C")})
                assert drone.props.get("ended") and match.time < drone.until
            elif ending == "pilot_hit":
                shooter.pos, shooter.equip_until = caster.pos + Vec(5, 0), 0
                hp = caster.hp
                guest.send(Command(fire=True, facing=270))
                update_guest(lambda: caster.hp < hp and not drone_positions())
                assert caster.alive and caster.channel_until == 0 and caster.equip_until > match.time
            else:
                while match.time < drone.until:
                    session.step(1 / 64)
            update_guest(lambda: not drone_positions())
            assert (client.match.players[guest.pid].pos - drone.pos).length() < 10
            assert not client.ui.rotor_sounds
            # A personal warning can reuse the mixer channel freed by the rotor.
            assert channel.get_sound() not in (client.sound.sounds["owl_rotor"], client.sound.muffled["owl_rotor"])
            assert not confirmations
            return

        while match.time < 1.35:
            session.step(1 / 64)
        shooter.pos = drone.pos + Vec(0, 5)
        events = session.step(1 / 64, {caster.pid: Command(fire=True, facing=0)})
        assert [e.data for e in events if e.kind == "owl_dart_hit"] == [
            {"pid": caster.pid, "key": "hit_body"}, {"pid": guest.pid, "key": "cast_tech"},
        ]
        update_guest(lambda: bool(dart_hits) and "owl_drone_spotted" in client.match.players[guest.pid].status)
        [dart_hit] = dart_hits
        assert dart_hit.data == {"pid": guest.pid, "key": "cast_tech"}
        warning = client.ui.drone_warning
        assert warning is not None and warning.get_busy()

        shooter.equip_until = 0
        drone.data["hp"] = 1
        guest.send(Command(fire=True, facing=180))
        update_guest(lambda: drone.props.get("ended", False) and not drone_positions() and bool(confirmations))
        assert match.time < drone.until
        assert (client.match.players[guest.pid].pos - drone.pos).length() < 10
        assert not client.ui.rotor_sounds and not channel.get_busy()
        assert client.ui.drone_warning is warning and warning.get_busy()
        [cue] = confirmations
        assert cue.data == {"pid": guest.pid, "key": "hit_body"}
        client.me = guest.pid
        played = []
        with monkeypatch.context() as patch:
            patch.setattr(client.sound, "play", lambda key, **kwargs: played.append(key))
            client.handle_events([dart_hit, cue])
        assert played == ["cast_tech", "hit_body"]

        def observer_caught_up() -> bool:
            messages = observer.take()
            assert not any(e.kind in ("device_hit_audio", "owl_dart_hit") for msg in messages if msg["type"] == "events"
                           for e in events_from_json(msg["events"]))
            for msg in messages:
                if msg["type"] == "state" and msg["snap"]["time"] > cue.t:
                    apply_snapshot(observer_match, msg["snap"], observer.pid)
                    return True
            return False

        observer_match = Match(match.world, match.cfg, agent_roster=match.agents)
        _wait(observer_caught_up, session)
        observer_audio = EventsMixin()
        observer_audio.match, observer_audio.ui, observer_audio.sound = observer_match, UiState(), client.sound
        listener = observer_match.players[observer.pid]
        assert "owl_drone_spotted" not in listener.status
        observer_audio.update_drone_warning(listener)
        assert observer_audio.ui.drone_warning is None
        update_guest(lambda: "owl_drone_spotted" not in client.match.players[guest.pid].status)
        assert client.ui.drone_warning is None and not warning.get_busy()
    finally:
        client.update_drone_warning(None)
        client.update_rotor_audio(None)
        if observer is not None:
            observer.close()
        guest.close()


@pytest.mark.parametrize("expired", [False, True])
def test_rejoin_restores_drone_warning(session: HostSession, monkeypatch, tmp_path, expired) -> None:
    import numpy as np

    from client.common import pygame
    from client.game import Game
    from gameplay.world import load_playable_map
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    match = session.match
    match.world = load_playable_map("ascent")
    match.add_player("Host", 0, "sova")
    guest = Game(args(join=f"127.0.0.1:{session.net.port}", name="Marked guest"))
    dt = 1 / 64
    try:
        assert session.net.choose_team(guest.me, 1)
        assert session.start(team_size=1)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match.phase, match.time, match.phase_until = "live", 2.0, 60.0
        player = match.players[guest.me]
        marked_at = 1.5
        player.status["owl_drone_spotted"] = marked_at + 4
        player.passive_state["owl_drone_spotted_at"] = marked_at

        def received_first_state():
            session.step(dt)
            guest.step(dt, Command())
            return not guest.restore_spike_audio and guest.me in guest.match.players

        _wait(received_first_state)
        listener = guest.view_player(guest.match.players[guest.me])
        guest.update_drone_warning(listener)
        previous = guest.ui.drone_warning
        assert previous is not None and previous.get_busy()
        old = guest.client
        old.close()
        guest.update_drone_warning(listener)
        assert guest.ui.drone_warning is None and not previous.get_busy()
        match.time += 0.375
        if expired:
            match.time = marked_at + 4
        guest.rejoin()
        assert guest.client is not old and guest.client.rejoined and guest.me == player.pid
        guest.update_drone_warning(listener)
        assert guest.ui.drone_warning is None

        _wait(received_first_state)
        listener = guest.view_player(guest.match.players[guest.me])
        guest.update_drone_warning(listener)
        warning = guest.ui.drone_warning
        if expired:
            assert warning is None
            assert "owl_drone_spotted_at" not in listener.passive_state
        else:
            assert listener.passive_state["owl_drone_spotted_at"] == marked_at
            assert warning is not None and warning.get_busy()
            original = pygame.sndarray.array(guest.sound.sounds["ab_alarm"])
            elapsed_ms = round((guest.match.time - marked_at) * 1_000_000_000) // 1_000_000
            frames = round(elapsed_ms * pygame.mixer.get_init()[0] / 1000)
            assert np.array_equal(pygame.sndarray.array(warning.get_sound()), np.roll(original, -frames, axis=0))
            guest.update_drone_warning(listener)
            assert guest.ui.drone_warning is warning
    finally:
        guest.update_drone_warning(None)
        guest.client.close()


@pytest.mark.parametrize("kind", ["jump", "land"])
def test_movement_sound_position_reaches_only_visible_or_nearby_guest(session: HostSession, monkeypatch, kind) -> None:
    from gameplay.geometry import Vec
    from gameplay.net import events_from_json
    from gameplay.world import WorldMap

    match = session.match
    match.world = WorldMap("test", "Test", 150, 150, spawns={0: [Vec(20, 20)], 1: [Vec(100, 100)]})
    lander = match.add_player("Host", 0, "omen")
    guest = NetClient(f"127.0.0.1:{session.net.port}", "Listener", "sage")
    dt = 1 / 64
    try:
        assert session.net.choose_team(guest.pid, 1)
        assert session.start(team_size=1)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match.phase, match.phase_until = "live", 60
        listener = match.players[guest.pid]
        for distance, facing, visible, expected in ((70, 0, False, False), (10, 0, False, True),
                                                    (15, 0, False, kind == "land"),
                                                    (30, 180, True, True)):
            listener.pos = lander.pos + Vec(0, distance)
            listener.facing = facing
            assert match.can_see(listener, lander) == visible
            if kind == "jump":
                lander.z = lander.vz = 0
                events = session.step(dt, {lander.pid: Command(jump=True)})
            else:
                lander.z, lander.vz = 0.01, -2
                events = session.step(dt)
            [movement] = [event for event in events if event.kind == kind]
            received = []

            def received_state():
                current = False
                for message in guest.take():
                    if message["type"] == "events":
                        received.extend(e for e in events_from_json(message["events"]) if e.kind == kind)
                    elif message["type"] == "state":
                        current |= message["snap"]["time"] > movement.t + 0.125
                return current and (not expected or bool(received))

            _wait(received_state, session)
            assert [Vec(*event.data["pos"]) for event in received] == ([lander.pos] if expected else [])
    finally:
        guest.close()


def test_rejoin_baselines_landing_audio(session: HostSession, monkeypatch, tmp_path) -> None:
    from unittest.mock import Mock

    from client.game import Game
    from gameplay.world import load_playable_map
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    match = session.match
    match.world = load_playable_map("ascent")
    jumper = match.add_player("Host", 0, "omen")
    guest = Game(args(join=f"127.0.0.1:{session.net.port}", name="Listener"))
    dt = 1 / 64
    try:
        assert session.net.choose_team(guest.me, 0)
        assert session.start(team_size=2)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match.phase, match.phase_until = "live", 60
        play = Mock()
        monkeypatch.setattr(guest.sound, "play", play)

        def receive(predicate):
            session.step(dt)
            guest.handle_events(guest.step(dt, Command()))
            return jumper.pid in guest.match.players and predicate(guest.match.players[jumper.pid])

        jumper.z = 0.8
        _wait(lambda: receive(lambda p: p.z > 0.05))
        me = guest.match.players[guest.me]
        guest.character_state(guest.match.players[jumper.pid], me)
        assert jumper.pid not in guest.ui.landed_at
        guest.client.close()
        jumper.z = jumper.vz = 0
        guest.rejoin()
        assert guest.client.rejoined and not guest.ui.landed_at
        _wait(lambda: receive(lambda p: not guest.restore_spike_audio and p.z == 0))
        me = guest.match.players[guest.me]
        guest.character_state(guest.match.players[jumper.pid], me)
        guest.audio_tick(me)
        assert jumper.pid not in guest.ui.landed_at
        assert not any(call.args[0] == "land" for call in play.call_args_list)
        jumper.z = 0.8
        _wait(lambda: receive(lambda p: p.z > 0.05))
        guest.character_state(guest.match.players[jumper.pid], me)
        jumper.vz = -2
        _wait(lambda: receive(lambda p: p.z == 0 and any(call.args[0] == "land" for call in play.call_args_list)))
        guest.character_state(guest.match.players[jumper.pid], me)
        landed = guest.ui.landed_at[jumper.pid]
        _wait(lambda: receive(lambda p: guest.match.time > landed))
        guest.audio_tick(me)
        guest.audio_tick(me)
        assert sum(call.args[0] == "land" for call in play.call_args_list) == 1
        # This hop finishes in one host tick, so the guest only sees grounded snapshots.
        jumper.z, jumper.vz = 0.01, -2
        _wait(lambda: receive(lambda p: p.z == 0 and
                              sum(call.args[0] == "land" for call in play.call_args_list) == 2))
        assert guest.match.players[jumper.pid].z == 0
        assert guest.character_state(guest.match.players[jumper.pid], me)[0] == "land"
    finally:
        guest.client.close()


@pytest.mark.parametrize("tick_while_disconnected", [False, True])
def test_rejoin_discards_pending_reload_audio(session: HostSession, monkeypatch, tmp_path, tick_while_disconnected) -> None:
    from unittest.mock import Mock

    from client.game import Game
    from gameplay.world import load_playable_map
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    match = session.match
    match.world = load_playable_map("ascent")
    reloader = match.add_player("Host", 0, "omen")
    guest = Game(args(join=f"127.0.0.1:{session.net.port}", name="Listener"))
    dt = 1 / 64
    try:
        assert session.net.choose_team(guest.me, 1)
        assert session.start(team_size=1)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match.phase, match.phase_until = "live", 60
        reloader.weapon.mag -= 1
        reloader.equip_until = 0
        play = Mock()
        monkeypatch.setattr(guest.sound, "play", play)

        def receive():
            session.step(dt)
            guest.handle_events(guest.step(dt, Command()))

        _wait(lambda: receive() or not guest.restore_spike_audio)
        session.step(dt, {reloader.pid: Command(reload=True)})
        _wait(lambda: receive() or bool(guest.ui.pending_sounds))
        [(due, key, *_)] = guest.ui.pending_sounds
        assert key == "reload_in"
        assert any(call.args[0] == "reload_out" for call in play.call_args_list)
        play.reset_mock()
        guest.client.close()
        if tick_while_disconnected:
            guest.match.time = due
            guest.audio_tick(guest.match.players[guest.me])
            assert not guest.ui.pending_sounds
            assert not any(call.args[0] == "reload_in" for call in play.call_args_list)
        match.time = due + dt
        guest.rejoin()
        assert guest.client.rejoined
        _wait(lambda: receive() or not guest.restore_spike_audio)
        guest.audio_tick(guest.match.players[guest.me])
        assert not guest.ui.pending_sounds
        assert not any(call.args[0] == "reload_in" for call in play.call_args_list)
    finally:
        guest.client.close()


def test_spike_countdown_resumes_on_next_beat_after_rejoin(session: HostSession, monkeypatch, tmp_path) -> None:
    from unittest.mock import Mock

    from client.game import Game
    from gameplay.world import load_playable_map
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    match = session.match
    match.world = load_playable_map("ascent")
    planter = match.add_player("Host", 0, "omen")
    guest = Game(args(join=f"127.0.0.1:{session.net.port}", name="Listener"))
    dt = 1 / 64
    try:
        assert session.net.choose_team(guest.me, 1)
        assert session.start(team_size=1)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match._plant(planter, "A")
        match.time = match.spike_planted_at + 35.25
        play = Mock()
        monkeypatch.setattr(guest.sound, "play", play)

        def audio_tick():
            player = guest.match.players[guest.me]
            guest.audio_tick(player)

        def receive():
            session.step(dt)
            guest.step(dt, Command())
            return not guest.restore_spike_audio and guest.match.phase == "planted"

        _wait(receive)
        audio_tick()
        assert any(call.args[0] == "bomb_beep" for call in play.call_args_list)
        play.reset_mock()
        old = guest.client
        old.close()
        guest._next_beep = guest.match.time
        audio_tick()
        assert not any(call.args[0] == "bomb_beep" for call in play.call_args_list)
        guest.rejoin()
        assert guest.client.rejoined
        audio_tick()
        _wait(receive)
        audio_tick()
        assert not any(call.args[0] == "bomb_beep" for call in play.call_args_list)
        next_beat = match.spike_planted_at + 35.4

        def heard_next_beat():
            receive()
            audio_tick()
            return any(call.args[0] == "bomb_beep" for call in play.call_args_list)

        _wait(heard_next_beat)
        assert next_beat <= guest.match.time <= next_beat + 3 * dt
    finally:
        guest.client.close()


@pytest.mark.parametrize("expired", [False, True])
def test_rejoin_restores_incendiary_loop(session: HostSession, monkeypatch, tmp_path, expired) -> None:
    import numpy as np

    from client.common import pygame
    from client.game import Game
    from gameplay.geometry import Vec
    from gameplay.match import Effect
    from gameplay.world import load_playable_map
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    match = session.match
    match.world = load_playable_map("ascent")
    caster = match.add_player("Host", 0, "brimstone")
    guest = Game(args(join=f"127.0.0.1:{session.net.port}", name="Listener"))
    dt = 1 / 64
    try:
        assert session.net.choose_team(guest.me, 1)
        assert session.start(team_size=1)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        monkeypatch.setattr(guest, "occluded", lambda *_: False)
        match.phase, match.time, match.phase_until = "live", 2.0, 60.0
        player = match.players[guest.me]
        player.facing = 0
        pos = player.pos + Vec(0, 1)
        effect = Effect("zone", caster.pid, caster.team, pos, 4.0, 2, start=1.5,
                        props={"sprite": "brimstone_incendiary_burning"})
        match.effects.append(effect)

        def received_state():
            session.step(dt)
            guest.step(dt, Command(facing=0))
            return not guest.restore_spike_audio and guest.me in guest.match.players

        _wait(received_state)
        listener = guest.match.players[guest.me]
        guest.update_incendiary_audio(listener)
        [previous] = guest.ui.fire_sounds.values()
        [(alternate, _)] = guest.ui.effect_sound_alternates.values()
        assert previous.get_busy() and alternate.get_busy()
        old = guest.client
        old.close()
        guest.update_incendiary_audio(listener)
        assert not guest.ui.fire_sounds and not guest.ui.effect_sound_alternates
        assert not previous.get_busy() and not alternate.get_busy()
        match.time = effect.until if expired else match.time + 0.375
        guest.rejoin()
        assert guest.client.rejoined
        guest.update_incendiary_audio(listener)
        assert not guest.ui.fire_sounds
        _wait(received_state)
        guest.update_incendiary_audio(guest.match.players[guest.me])
        if expired:
            assert not guest.ui.fire_sounds
        else:
            [resumed] = guest.ui.fire_sounds.values()
            original = pygame.sndarray.array(guest.sound.sounds["incendiary_fire"])
            elapsed_ms = round((guest.match.time - effect.start) * 1_000_000_000) // 1_000_000
            frames = round(elapsed_ms * pygame.mixer.get_init()[0] / 1000)
            assert np.array_equal(pygame.sndarray.array(resumed.get_sound()), np.roll(original, -frames, axis=0))
    finally:
        guest.stop_ability_audio()
        guest.client.close()


def test_spectator_switches_between_drone_marks_over_localhost(session: HostSession, monkeypatch) -> None:
    import numpy as np

    from client.common import Sound, UiState, pygame
    from client.events import EventsMixin
    from client.world_view import WorldViewMixin

    class SpectatorAudio(EventsMixin, WorldViewMixin):
        pass

    match = session.match
    first = match.add_player("First", 0, "sage")
    second = match.add_player("Second", 0, "omen")
    guest = NetClient(f"127.0.0.1:{session.net.port}", "Spectator", "omen")
    audio = SpectatorAudio()
    audio.match = Match(match.world, match.cfg, agent_roster=match.agents)
    audio.ui, audio.sound = UiState(), Sound()
    try:
        assert audio.sound.ok
        assert session.net.choose_team(guest.pid, 0)
        assert session.start(team_size=3)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match.phase, match.time, match.phase_until = "live", 2, 60
        match.players[guest.pid].alive = False
        for target, marked_at in ((first, 1.5), (second, 1.875)):
            target.status["owl_drone_spotted"] = marked_at + 4
            target.passive_state["owl_drone_spotted_at"] = marked_at

        def received_marks():
            for message in guest.take():
                if message["type"] == "state":
                    apply_snapshot(audio.match, message["snap"], guest.pid)
            return audio.match.time >= 2 and guest.pid in audio.match.players

        _wait(received_marks, session)
        viewer = audio.match.players[guest.pid]
        original = pygame.sndarray.array(audio.sound.sounds["ab_alarm"])
        rate = pygame.mixer.get_init()[0]
        previous = None
        for index, target in enumerate((first, second)):
            audio.spectate_index = index
            listener = audio.view_player(viewer)
            assert listener.pid == target.pid
            marked_at = target.passive_state["owl_drone_spotted_at"]
            assert listener.passive_state["owl_drone_spotted_at"] == marked_at
            audio.update_drone_warning(listener)
            warning = audio.ui.drone_warning
            assert warning is not None and warning.get_busy()
            elapsed_ms = round((audio.match.time - marked_at) * 1_000_000_000) // 1_000_000
            sample = warning.get_sound()
            assert np.array_equal(pygame.sndarray.array(sample),
                                  np.roll(original, -round(elapsed_ms * rate / 1000), axis=0))
            if previous is not None:
                assert previous.get_num_channels() == 0
            previous = sample
    finally:
        audio.update_drone_warning(None)
        guest.close()


@pytest.mark.parametrize("scenario", [
    "hit", "miss", "wall", "pitched_hit", "late_hit", "rejoin_between_pulses", "rejoin_during_pulse",
    "rejoin_after_pulses",
])
def test_connected_sova_dart_confirmation(session: HostSession, monkeypatch, scenario: str) -> None:
    from client.events import EventsMixin
    from gameplay.geometry import Rect, Vec
    from gameplay.net import events_from_json
    from gameplay.world import Wall, WorldMap
    from types import SimpleNamespace

    match = session.match
    match.world = WorldMap("test", "Test", 120, 120, spawns={0: [Vec(50, 50)], 1: [Vec(100, 100)]})
    target = match.add_player("Target host", 1, "omen")
    guest = NetClient(f"127.0.0.1:{session.net.port}", "Sova guest", "sova")
    try:
        assert session.net.choose_team(guest.pid, 0)
        assert session.start(team_size=1)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match.phase, match.phase_until = "live", match.time + 60
        caster = match.players[guest.pid]
        caster.charges["C"] = 1
        target.pos = caster.pos + Vec(0, 5)
        guest.send(Command(ability="C", facing=0))
        _wait(lambda: any(e.props.get("sprite") == "sova_owl_drone" for e in match.effects), session)
        [drone] = [e for e in match.effects if e.props.get("sprite") == "sova_owl_drone"]
        _wait(lambda: match.time >= drone.start, session)
        hit = scenario not in ("miss", "wall")
        pitch = 0
        if scenario == "pitched_hit":
            guest.send(Command(jump=True, facing=0))
            _wait(lambda: drone.props.get("flight_height", 0) >= 1.75, session)
            guest.send(Command(facing=0))
            pitch = -15
        if scenario == "miss":
            target.pos += Vec(2, 0)
        elif scenario == "wall":
            x, y = drone.pos.x, drone.pos.y
            match.world.walls.append(Wall(Rect(x - 2, y + 2, x + 2, y + 3), 3))
            assert not match._line_clear(drone.pos, target.pos, target.level, ignore_effects=True)
        guest.send(Command(fire=True, facing=0, drone_pitch=pitch))
        received = []
        host_events = []

        def received_shot_state() -> bool:
            host_events.extend(session.step(1 / 64))
            fired_at = drone.data.get("dart_ready", 0) - 5
            state_after_shot = False
            for message in guest.take():
                if message["type"] == "events":
                    received.extend(e for e in events_from_json(message["events"]) if e.kind == "owl_dart_hit")
                elif message["type"] == "state" and fired_at > 0:
                    state_after_shot |= message["snap"]["time"] > fired_at
            return state_after_shot and (bool(received) or not hit)

        _wait(received_shot_state)
        assert (target.status.get("owl_drone_spotted", 0) > match.time) == hit
        assert [e.data for e in received] == ([{"pid": guest.pid, "key": "hit_body"}] if hit else [])
        if not hit:
            assert not any(e.kind == "owl_dart_hit" for e in host_events)
        played = []
        client = EventsMixin()
        client.me, client.match = guest.pid, match
        client.sound = SimpleNamespace(play=lambda key, **kw: played.append(key))
        client.handle_events(received)
        assert played == (["hit_body"] if hit else [])
        if scenario == "late_hit" or scenario.startswith("rejoin_"):
            from gameplay.net import apply_snapshot

            impact = drone.data["dart_ready"] - 5
            drone.until = match.time + 0.5
            replica = Match(match.world)
            reveal_starts = []
            revealed = False

            def receive_pulses():
                nonlocal revealed
                session.step(1 / 64)
                for message in guest.take():
                    if message["type"] != "state":
                        continue
                    apply_snapshot(replica, message["snap"], guest.pid)
                    victim = replica.players.get(target.pid)
                    active = victim is not None and victim.revealed_until > replica.time
                    if active and not revealed:
                        assert not any(e.props.get("sprite") == "sova_owl_drone" for e in replica.effects)
                        reveal_starts.append(replica.time - impact)
                    revealed = active
                return not revealed

            if scenario.startswith("rejoin_"):
                during = scenario == "rejoin_during_pulse"
                after = scenario == "rejoin_after_pulses"
                _wait(lambda: receive_pulses() != during and len(reveal_starts) == (2 if after else 1))
                pid, token = guest.pid, guest.token
                assert (match.time >= impact + 4) if after else (match.time < impact + 3.4)
                guest.close()
                _wait(lambda: match.players[pid].is_bot, session)
                guest = NetClient(f"127.0.0.1:{session.net.port}", "Sova guest", "sova", token=token)
                assert guest.pid == pid and guest.rejoined
                replica = Match(match.world)
                if after:
                    _wait(lambda: receive_pulses() and replica.time >= impact + 4.5)
                    victim = replica.players.get(target.pid)
                    assert victim is None or victim.revealed_until <= replica.time
                    assert reveal_starts == pytest.approx([1.6, 3.4], abs=0.12)
                    return
                assert match.time < impact + 3.4
                if during:
                    expires = target.revealed_until
                    assert match.time < expires
                    _wait(lambda: (receive_pulses(), replica.time)[1] > 0)
                    assert replica.time < expires
                    assert replica.players[target.pid].revealed_until == pytest.approx(expires)
            _wait(lambda: receive_pulses() and len(reveal_starts) >= 2)
            assert reveal_starts == pytest.approx([1.6, 3.4], abs=0.12)
            return
        if hit:
            ready_at = drone.data["dart_ready"]
            received.clear()
            host_events.clear()
            guest.send(Command(facing=0))
            _wait(lambda: not caster.prev_fire, session)
            guest.send(Command(fire=True, facing=0, drone_pitch=pitch))
            _wait(lambda: caster.prev_fire, session)
            assert match.time < ready_at and drone.data["dart_ready"] == ready_at
            while match.time < ready_at:
                received_shot_state()
            assert not received
            assert not any(e.kind == "owl_dart_hit" for e in host_events)
            guest.send(Command(facing=0))
            _wait(lambda: not caster.prev_fire, session)
            guest.send(Command(fire=True, facing=0, drone_pitch=pitch))
            _wait(lambda: received_shot_state() and drone.data["dart_ready"] > ready_at)
            assert [e.data for e in received] == [{"pid": guest.pid, "key": "hit_body"}]
            assert [e.data for e in host_events if e.kind == "owl_dart_hit"] == [
                {"pid": guest.pid, "key": "hit_body"}, {"pid": target.pid, "key": "cast_tech"},
            ]
    finally:
        guest.close()


@pytest.mark.parametrize("spectating", [False, True])
def test_silenced_shot_reaches_only_guest_in_forward_cone(session: HostSession, monkeypatch, spectating) -> None:
    from contextlib import ExitStack
    from unittest.mock import Mock

    from client.common import UiState
    from client.events import EventsMixin
    from gameplay.geometry import Vec
    from gameplay.net import events_from_json
    from gameplay.world import WorldMap

    match = session.match
    origin = Vec(70, 70)
    match.world = WorldMap("test", "Test", 150, 150, spawns={0: [origin], 1: [Vec(130, 130)]})
    shooter = match.add_player("Shooter", 0, "omen")
    address = f"127.0.0.1:{session.net.port}"
    with ExitStack() as stack:
        guests = [NetClient(address, "East", "sage")]
        stack.callback(guests[0].close)
        guests.append(NetClient(address, "North", "sage"))
        stack.callback(guests[1].close)
        for guest in guests:
            assert session.net.choose_team(guest.pid, 1)
        assert session.start(team_size=3 if spectating else 2)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match.phase, match.phase_until = "live", match.time + 60
        shooter.pos, shooter.slot, shooter.equip_until = origin, "primary", 0
        shooter.weapons[shooter.slot] = match._new_weapon("phantom", shooter)
        for guest, offset in zip(guests, (Vec(55, 0), Vec(0, 55))):
            match.players[guest.pid].pos = origin + offset
        if spectating:
            spectator = match.players[guests[1].pid]
            spectator.alive = False
            teammate = next(p for p in match.players.values() if p.team == spectator.team and p.is_bot)
            teammate.pos = origin + Vec(0, 55)

        for facing, expected_guest in zip((90, 0), guests):
            events = session.step(1 / 64, {shooter.pid: Command(fire=True, facing=facing)})
            [shot] = [event for event in events if event.kind == "sound" and event.data.get("weapon") == "phantom"]
            received = {guest.pid: [] for guest in guests}
            observed = set()

            def received_shot_state() -> bool:
                for guest in guests:
                    for message in guest.take():
                        if message["type"] == "events":
                            received[guest.pid].extend(
                                event for event in events_from_json(message["events"])
                                if event.kind == "sound" and event.data.get("weapon") == "phantom"
                            )
                        elif message["type"] == "state" and message["snap"]["time"] > shot.t + 0.25:
                            observed.add(guest.pid)
                return len(observed) == len(guests) and bool(received[expected_guest.pid])

            _wait(received_shot_state, session)
            for guest in guests:
                expected = guest is expected_guest or spectating and guest is guests[1]
                assert [event.t for event in received[guest.pid]] == ([shot.t] if expected else [])
            if spectating:
                audio = EventsMixin()
                audio.me, audio.match, audio.ui = spectator.pid, match, UiState()
                audio.sound = Mock()
                audio.handle_events(received[spectator.pid], spike_listener=teammate)
                if facing == 0:
                    assert audio.sound.play.call_args.args == ("shot_silenced", teammate, origin, 80)
                else:
                    audio.sound.play.assert_not_called()


@pytest.mark.parametrize("agent", ["neon", "kayo"])
def test_ultimate_cast_audio_reaches_both_teams(session: HostSession, monkeypatch, agent: str) -> None:
    from contextlib import ExitStack
    from types import SimpleNamespace

    from client.events import EventsMixin
    from gameplay.geometry import Vec
    from gameplay.net import events_from_json
    from gameplay.world import WorldMap

    match = session.match
    match.world = WorldMap("test", "Test", 150, 150, spawns={0: [Vec(30, 30)], 1: [Vec(130, 130)]})
    caster = match.add_player("Caster host", 0, agent)
    address = f"127.0.0.1:{session.net.port}"
    with ExitStack() as stack:
        ally = NetClient(address, "Ally", "sage")
        stack.callback(ally.close)
        enemy = NetClient(address, "Enemy", "omen")
        stack.callback(enemy.close)
        guests = (ally, enemy)
        assert session.net.choose_team(ally.pid, caster.team)
        assert session.net.choose_team(enemy.pid, 1 - caster.team)
        assert session.start(team_size=2)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match.phase, match.phase_until = "live", match.time + 60
        ally_distance = 6 if agent == "kayo" else 80
        for guest, offset in [(ally, Vec(ally_distance, 0)), (enemy, Vec(0, 80))]:
            match.players[guest.pid].pos = caster.pos + offset
        caster.ult_points = match.ultimate_cost(caster)
        session.step(1 / 64, {caster.pid: Command(ability="X")})
        cast_time = match.time
        if agent == "kayo":
            assert caster.status["kayo_overload"] > cast_time
        else:
            assert caster.overdrive_until > cast_time
        casts = {guest.pid: [] for guest in guests}
        pulses = {guest.pid: [] for guest in guests}
        snapshot_times = {}

        def received_casts() -> bool:
            for guest in guests:
                for message in guest.take():
                    if message["type"] == "state":
                        snapshot_times[guest.pid] = message["snap"]["time"]
                    elif message["type"] == "events":
                        events = events_from_json(message["events"])
                        pulses[guest.pid].extend(e for e in events if e.kind == "sound_fx"
                                                and e.data.get("key") == "cast_sonic")
                        casts[guest.pid].extend(e for e in events
                                                if e.kind in ("ability", "sound_fx")
                                                and e.data.get("pid") == caster.pid)
            return all(any(e.kind == "ability" for e in batch) for batch in casts.values())

        _wait(received_casts, session)
        ally_sound, enemy_sound = ("cast_tech", "cast_electric") if agent == "kayo" else ("cast_electric", "cast_burst")
        for guest, sound in [(ally, ally_sound), (enemy, enemy_sound)]:
            batch = casts[guest.pid]
            assert all(e.t == cast_time for e in batch)
            played = []
            client = EventsMixin()
            client.me, client.match = guest.pid, match
            client.ui = SimpleNamespace(last_cast={})
            client.aiming = None
            client.sound = SimpleNamespace(sounds={}, play=lambda key, *args, **kw: played.append((key, args)))
            client.handle_events(batch)
            expected = [(sound, ())]
            if agent == "kayo" and guest is ally:
                expected.insert(0, ("cast_charge_up", (match.players[ally.pid], caster.pos, 30.0)))
            assert played == expected

        if agent == "kayo":
            assert not any(pulses.values())
            first_pos = caster.pos
            for index, (listener, pos) in enumerate(((ally, first_pos), (enemy, Vec(30, 100)))):
                caster.pos = pos
                pulse_time = cast_time + 1 + index * 3

                def received_pulse() -> bool:
                    received_casts()
                    return all(snapshot_times.get(guest.pid, 0) > pulse_time + 0.2 for guest in guests) and bool(
                        pulses[listener.pid]
                    )

                _wait(received_pulse, session)
                [pulse] = pulses[listener.pid]
                assert pulse.t == pytest.approx(pulse_time, abs=1 / 64)
                assert Vec(*pulse.data["pos"]) == pos
                assert pulse.data["radius"] == 42.5
                assert not pulses[(enemy if listener is ally else ally).pid]
                pulses[listener.pid].clear()


@pytest.mark.parametrize("ability", ["E", "X"])
def test_neon_battery_cues_are_private(session: HostSession, monkeypatch, ability: str) -> None:
    from contextlib import ExitStack
    from types import SimpleNamespace

    from client.events import EventsMixin
    from gameplay.geometry import Vec
    from gameplay.kit.statuses import apply_status
    from gameplay.net import events_from_json
    from gameplay.world import WorldMap

    match = session.match
    match.world = WorldMap("test", "Test", 120, 120, spawns={0: [Vec(40, 40)], 1: [Vec(100, 100)]})
    address = f"127.0.0.1:{session.net.port}"
    with ExitStack() as stack:
        neon = NetClient(address, "Neon guest", "neon")
        stack.callback(neon.close)
        enemy = NetClient(address, "Other guest", "omen")
        stack.callback(enemy.close)
        assert session.net.choose_team(neon.pid, 0)
        assert session.net.choose_team(enemy.pid, 1)
        assert session.start(team_size=1)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match.phase, match.phase_until = "live", match.time + 60
        player = match.players[neon.pid]
        player.ult_points = match.ultimate_cost(player)
        neon.send(Command(ability=ability))
        _wait(lambda: "neon_sprint" in player.status or "neon_overdrive" in player.status, session)
        player.passive_state["neon_battery"] = 20.1
        guests = (neon, enemy)
        warnings = {guest.pid: [] for guest in guests}
        state_times = dict.fromkeys(warnings, 0.0)
        end = match.time + 0.5

        def received_states() -> bool:
            for guest in guests:
                for message in guest.take():
                    if message["type"] == "events":
                        warnings[guest.pid].extend(e for e in events_from_json(message["events"])
                                                   if e.kind.startswith("neon_battery_"))
                    elif message["type"] == "state":
                        state_times[guest.pid] = message["snap"]["time"]
            return min(state_times.values()) > end

        _wait(received_states, session)
        assert player.passive_state["neon_battery"] < 20
        assert [e.data for e in warnings[neon.pid]] == [{"pid": neon.pid}]
        assert not warnings[enemy.pid]
        played = []
        client = EventsMixin()
        client.me, client.match = neon.pid, match
        client.sound = SimpleNamespace(play=lambda key, **kw: played.append(key))
        client.handle_events(warnings[neon.pid])
        assert played == ["ab_alarm"]
        assert warnings[neon.pid][0].kind == "neon_battery_low"
        if ability == "X":
            reserve = match.add_player("Reserve enemy", 1, "omen")
            reserve.pos = Vec(100, 100)
            victim = match.players[enemy.pid]
            victim.pos, victim.hp = player.pos + Vec(0, 5), 1
            _wait(lambda: match.time >= player.equip_until, session)
            assert 0 < player.passive_state["neon_battery"] < 20
            neon.send(Command(fire=True, facing=0, cursor_depth=5))
            _wait(lambda: not victim.alive, session)
            assert player.passive_state["neon_battery"] > 99
            neon.send(Command())
            end = match.time + 0.1
            _wait(received_states, session)
            assert len(warnings[neon.pid]) == 1 and not warnings[enemy.pid]
            while player.passive_state["neon_battery"] >= 20:
                session.step(1 / 64)
            end = match.time + 0.5
            _wait(received_states, session)
            [after_kill] = warnings[neon.pid][1:]
            assert (after_kill.kind, after_kill.data) == ("neon_battery_low", {"pid": neon.pid})
            assert not warnings[enemy.pid]
            client.handle_events([after_kill])
            assert played.pop() == "ab_alarm"
            warnings[neon.pid].pop()
            victim.alive, victim.hp = True, 100
        player.passive_state["neon_battery"] = 0.05
        events = session.step(1 / 64)
        [depleted] = [e for e in events if e.kind == "neon_battery_empty"]
        assert depleted.t == match.time and player.passive_state["neon_battery"] == 0
        assert "neon_sprint" not in player.status and "neon_overdrive" not in player.status
        end = match.time + 0.5
        _wait(received_states, session)
        assert not warnings[enemy.pid]
        assert [(e.kind, e.data) for e in warnings[neon.pid]] == [
            ("neon_battery_low", {"pid": neon.pid}), ("neon_battery_empty", {"pid": neon.pid}),
        ]
        client.handle_events(warnings[neon.pid][1:])
        assert played == ["ab_alarm", "cast_whoosh"]
        player.passive_state["neon_battery"] = 0
        neon.send(Command(ability="E"))
        end = match.time + 0.5
        _wait(received_states, session)
        assert "neon_sprint" not in player.status
        [rejected] = warnings[neon.pid][2:]
        assert rejected.kind == "neon_battery_insufficient" and rejected.data == {"pid": neon.pid}
        assert not warnings[enemy.pid]
        client.handle_events([rejected])
        assert played == ["ab_alarm", "cast_whoosh", "empty"]
        client.me = enemy.pid
        client.handle_events([rejected])
        assert played == ["ab_alarm", "cast_whoosh", "empty"]

        neon.send(Command())
        _wait(lambda: player.prev_ability is None, session)
        neon.send(Command(ability="E"))

        def started_at_threshold() -> bool:
            player.passive_state["neon_battery"] = 2.0
            events = session.step(1 / 64)
            assert not any(e.kind.startswith("neon_battery_") for e in events)
            return "neon_sprint" in player.status

        _wait(started_at_threshold)
        assert player.passive_state["neon_battery"] < 2
        end = match.time + 0.1
        _wait(received_states, session)
        assert warnings[neon.pid][2:] == [rejected] and not warnings[enemy.pid]

        _wait(lambda: "neon_sprint" not in player.status, session)
        end = match.time + 0.1
        _wait(received_states, session)
        before_recharge = list(warnings[neon.pid])
        assert before_recharge[-1].kind == "neon_battery_empty"
        while player.passive_state["neon_battery"] < 20.1:
            session.step(1 / 64)
        neon.send(Command(ability="E"))
        _wait(lambda: "neon_sprint" in player.status, session)
        _wait(lambda: player.passive_state["neon_battery"] < 20, session)
        end = match.time + 0.5
        _wait(received_states, session)
        assert warnings[neon.pid][:len(before_recharge)] == before_recharge
        [recharged_warning] = warnings[neon.pid][len(before_recharge):]
        assert (recharged_warning.kind, recharged_warning.data) == ("neon_battery_low", {"pid": neon.pid})
        assert not warnings[enemy.pid]
        client.me = neon.pid
        client.handle_events([recharged_warning])
        assert played == ["ab_alarm", "cast_whoosh", "empty", "ab_alarm"]
        remaining = player.passive_state["neon_battery"]
        assert 0 < remaining < 20
        before_cancel = list(warnings[neon.pid])
        neon.send(Command())
        _wait(lambda: player.prev_ability is None, session)
        neon.send(Command(ability="E"))
        _wait(lambda: "neon_sprint" not in player.status, session)
        assert player.passive_state["neon_battery"] > 0
        end = match.time + 0.5
        _wait(received_states, session)
        assert player.passive_state["neon_battery"] > remaining
        assert warnings[neon.pid] == before_cancel and not warnings[enemy.pid]

        neon.send(Command())
        _wait(lambda: player.prev_ability is None, session)
        player.ult_points = match.ultimate_cost(player)
        active_status = "neon_sprint" if ability == "E" else "neon_overdrive"
        neon.send(Command(ability=ability))
        _wait(lambda: active_status in player.status, session)
        player.passive_state["neon_battery"] = 0.05
        apply_status(match, player, "suppress", 1.0)
        assert player.status["suppress"] > match.time
        events = session.step(1 / 64)
        assert active_status not in player.status
        assert player.passive_state["neon_battery"] > 0.05
        assert not any(e.kind.startswith("neon_battery_") for e in events)
        end = match.time + 0.5
        _wait(received_states, session)
        assert warnings[neon.pid] == before_cancel and not warnings[enemy.pid]


        neon.send(Command())
        _wait(lambda: player.prev_ability is None and player.status.get("suppress", 0) <= match.time, session)
        _wait(lambda: player.passive_state["neon_battery"] >= 2, session)
        player.ult_points = match.ultimate_cost(player)
        neon.send(Command(ability=ability))
        _wait(lambda: active_status in player.status, session)
        shooter = match.players[enemy.pid]
        shooter.pos = player.pos + Vec(0, 5)
        shooter.equip_until = 0
        player.hp = 1
        teammate = match.add_player("Reserve ally", player.team, "sage")
        teammate.pos = Vec(110, 110)
        enemy.send(Command(fire=True, facing=180, cursor_depth=5))
        _wait(lambda: enemy.pid in session.net.pending)
        player.passive_state["neon_battery"] = 0.05
        events = session.step(1 / 64)
        assert not player.alive and active_status not in player.status
        assert not any(e.kind.startswith("neon_battery_") for e in events)
        end = match.time + 0.1
        _wait(received_states, session)
        assert warnings[neon.pid] == before_cancel and not warnings[enemy.pid]


def test_waylay_ultimate_audio_reaches_guests(session: HostSession, monkeypatch) -> None:
    from contextlib import ExitStack
    from types import SimpleNamespace

    from client.events import EventsMixin
    from gameplay.geometry import Vec
    from gameplay.net import events_from_json
    from gameplay.world import WorldMap

    match = session.match
    match.world = WorldMap("test", "Test", 150, 150, spawns={0: [Vec(40, 40)], 1: [Vec(130, 130)]})
    caster = match.add_player("Waylay host", 0, "waylay")
    address = f"127.0.0.1:{session.net.port}"
    with ExitStack() as stack:
        ally = NetClient(address, "Near ally", "sage")
        stack.callback(ally.close)
        enemy = NetClient(address, "Far enemy", "omen")
        stack.callback(enemy.close)
        near_enemy = NetClient(address, "Near enemy", "omen")
        stack.callback(near_enemy.close)
        assert session.net.choose_team(ally.pid, caster.team)
        assert session.net.choose_team(enemy.pid, 1 - caster.team)
        assert session.net.choose_team(near_enemy.pid, 1 - caster.team)
        assert session.start(team_size=2)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match.phase, match.phase_until = "live", match.time + 60
        origin = caster.pos
        match.players[ally.pid].pos = origin + Vec(6, 0)
        match.players[enemy.pid].pos = origin + Vec(80, 0)
        match.players[near_enemy.pid].pos = origin + Vec(40, 0)
        caster.ult_points = match.ultimate_cost(caster)
        session.step(1 / 64, {caster.pid: Command(ability="X", facing=0)})
        cast_time = match.time
        [beam] = [e for e in match.effects if e.props.get("status") == "waylay_hinder"]
        guests = (ally, near_enemy, enemy)
        events = {guest.pid: [] for guest in guests}
        state_times = dict.fromkeys(events, 0.0)

        def read_guests() -> None:
            for guest in guests:
                for message in guest.take():
                    if message["type"] == "events":
                        events[guest.pid].extend(events_from_json(message["events"]))
                    elif message["type"] == "state":
                        state_times[guest.pid] = message["snap"]["time"]

        def received_beam() -> bool:
            read_guests()
            return min(state_times.values()) > beam.start and all(
                any(e.kind == "sound_fx" and e.data.get("key") == "ab_wave" for e in events[guest.pid])
                for guest in (ally, near_enemy))

        _wait(received_beam, session)
        for guest in guests:
            batch = [e for e in events[guest.pid] if e.kind in ("ability", "sound_fx")]
            waves = [e for e in batch if e.kind == "sound_fx" and e.data.get("key") == "ab_wave"]
            assert len(waves) == (0 if guest is enemy else 1)
            for wave in waves:
                assert wave.t == pytest.approx(beam.start, abs=1 / 64)
                assert Vec(*wave.data["pos"]) == beam.pos
            played = []
            client = EventsMixin()
            client.me, client.match = guest.pid, match
            client.ui = SimpleNamespace(last_cast={})
            client.aiming = None
            client.sound = SimpleNamespace(sounds={}, play=lambda key, *args, **kw: played.append((key, args)))
            client.handle_events(batch)
            expected = [("cast_buff" if guest is ally else "cast_beam", ())]
            if guest is ally:
                expected.insert(0, ("cast_charge_up", (match.players[ally.pid], origin, 30.0)))
            if guest is not enemy:
                expected.append(("ab_wave", (match.players[guest.pid], beam.pos, 50.0)))
            assert all(e.t == cast_time for e in batch if e not in waves)
            assert played == expected


def test_recon_flight_and_impact_reach_connected_guest(session: HostSession, monkeypatch) -> None:
    from client.common import Sound, UiState
    from client.events import EventsMixin
    from gameplay.geometry import Vec
    from gameplay.net import events_from_json
    from gameplay.world import WorldMap

    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    match = session.match
    match.world = WorldMap("test", "Test", 120, 120, spawns={0: [Vec(50, 50)], 1: [Vec(100, 100)]})
    caster = match.add_player("Sova host", 0, "sova")
    client = EventsMixin()
    client.match = Match(match.world, match.cfg, agent_roster=match.agents)
    client.ui, client.sound = UiState(), Sound()
    address = f"127.0.0.1:{session.net.port}"
    guest = NetClient(address, "Near enemy", "omen")
    distant = None
    try:
        distant = NetClient(address, "Distant enemy", "sage")
        client.me = guest.pid
        assert session.net.choose_team(guest.pid, 1 - caster.team)
        assert session.net.choose_team(distant.pid, 1 - caster.team)
        assert session.start(team_size=2)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match.phase, match.phase_until = "live", match.time + 60
        match.players[guest.pid].pos = caster.pos + Vec(6, 8)
        far_position = Vec(100, 100)
        match.players[distant.pid].pos = far_position
        session.step(1 / 64, {caster.pid: Command(ability="E", facing=0, cursor_depth=16)})
        [arrow] = [e for e in match.effects if e.props.get("sprite") == "sova_recon_bolt"]
        impacts = []

        def read_guest() -> None:
            for message in guest.take():
                if message["type"] == "state":
                    apply_snapshot(client.match, message["snap"], guest.pid)
                elif message["type"] == "events":
                    impacts.extend(e for e in events_from_json(message["events"])
                                   if e.kind == "sound_fx" and e.data.get("key") == "cast_place_trap")
            if listener := client.match.players.get(guest.pid):
                client.update_recon_audio(listener)

        def flying() -> bool:
            read_guest()
            return bool(client.ui.recon_sounds)

        _wait(flying, session)
        [channel] = client.ui.recon_sounds.values()
        assert channel.get_busy() and not impacts

        def landed() -> bool:
            read_guest()
            return bool(impacts) and client.match.time >= arrow.until

        _wait(landed, session)
        assert not client.ui.recon_sounds and not channel.get_busy()
        [impact] = impacts
        assert Vec(*impact.data["pos"]) == arrow.pos
        assert impact.t == pytest.approx(arrow.until, abs=1 / 64)
        assert any(e.kind == "sensor" and e.pos == arrow.pos for e in client.match.effects)
        assert (far_position - arrow.pos).length() > impact.data["radius"]

        def distant_has_landed_state() -> bool:
            messages = distant.take()
            assert not any(e.kind == "sound_fx" and e.data.get("key") == "cast_place_trap"
                           for msg in messages if msg["type"] == "events"
                           for e in events_from_json(msg["events"]))
            return any(msg["snap"]["time"] > impact.t
                       and any(e["kind"] == "sensor" and e["sprite"] == "sova_recon_bolt"
                               for e in msg["snap"]["effects"])
                       for msg in messages if msg["type"] == "state")

        _wait(distant_has_landed_state, session)
        played = []
        monkeypatch.setattr(client.sound, "play", lambda key, listener, pos, radius, **kw: played.append((key, pos)))
        client.handle_events(impacts)
        assert played == [("cast_place_trap", arrow.pos)]
    finally:
        client.update_recon_audio(None)
        if distant is not None:
            distant.close()
        guest.close()


def test_omen_guest_arrives_as_shade_and_returns_on_cancel(session: HostSession) -> None:
    from gameplay.geometry import Vec
    from gameplay.kit.builtins import can_land

    client = NetClient(f"127.0.0.1:{session.net.port}", "Omen Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        match = session.match
        match.phase_until = match.time
        session.step(1 / 64)
        guest = match.players[client.pid]
        opponent = next(p for p in match.players.values() if p.team != guest.team)
        origin = guest.pos
        target = next(origin + delta for delta in (Vec(4, 0), Vec(-4, 0), Vec(0, 4), Vec(0, -4))
                      if can_land(match, guest, origin + delta))
        guest.ult_points = 7
        client.send(Command(ability="X", points=[(target.x, target.y)]))
        _wait(lambda: match.snapshot(opponent.pid)["minimap_obscured"], session)
        _wait(lambda: guest.pos == target and "omen_shade" in guest.status, session)
        snapshots = []

        def received_shade() -> bool:
            snapshots.extend(msg["snap"] for msg in client.take() if msg["type"] == "state"
                             and any(e.get("sprite") == "omen_from_the_shadows" for e in msg["snap"]["effects"]))
            return bool(snapshots)

        _wait(received_shade, session)
        shadow = Match(match.world, agent_roster=match.agents)
        apply_snapshot(shadow, snapshots[-1], client.pid)
        shade = next(e for e in shadow.effects if e.props.get("sprite") == "omen_from_the_shadows")
        radius = shadow.sight_range(shadow.players[client.pid])
        assert radius is not None and radius < 8
        shadow.time = (shade.start + shade.until) / 2
        assert shadow.sight_range(shadow.players[client.pid]) > radius
        client.send(Command(ability="X"))
        _wait(lambda: guest.pos == origin and "omen_shade" not in guest.status, session)
        assert guest.ult_points == 0
        assert not match.snapshot(opponent.pid)["minimap_obscured"]
    finally:
        client.close()


def test_kayo_host_interrupts_guest_omen_windup(session: HostSession) -> None:
    from gameplay.geometry import Vec
    from gameplay.world import WorldMap

    host = session.match.add_player("Host", 0, "kayo")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Omen Guest", "omen")
    try:
        match = session.match
        match.world = WorldMap("workyard", "Test", 100, 100, spawns={0: [Vec(10, 16)], 1: [Vec(10, 10)]})
        _wait(lambda: client.pid in match.players, session)
        session.start(team_size=1)
        match.phase_until = match.time
        session.step(1 / 64)
        omen = match.players[client.pid]
        host.pos, omen.pos = Vec(10, 16), Vec(10, 10)
        origin = omen.pos
        omen.ult_points = 7
        session.step(1 / 64, {host.pid: Command(ability="E", facing=180, cursor_depth=6)})
        client.send(Command(ability="X", points=[(30, 20)]))
        _wait(lambda: match.minimap_obscured(host), session)
        _wait(lambda: omen.status.get("suppress", 0) > match.time, session)
        assert omen.pos == origin and omen.channel_until == 0 and omen.ult_points == 0
        assert not match.minimap_obscured(host)
    finally:
        client.close()


def test_dark_cover_guest_cast_preserves_intermediate_height(session: HostSession) -> None:
    client = NetClient(f"127.0.0.1:{session.net.port}", "Omen Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        match = session.match
        guest = match.players[client.pid]
        point = guest.pos
        client.send(Command(ability="E", target_lift=1.25, points=[(point.x, point.y)]))
        _wait(lambda: any(e.kind == "smoke" and e.owner == client.pid for e in match.effects), session)
        [smoke] = [e for e in match.effects if e.kind == "smoke" and e.owner == client.pid]
        assert smoke.pos == point
        assert smoke.fall_offset(smoke.start) == pytest.approx(1.25)
        snapshots: list = []

        def received_smoke() -> bool:
            snapshots.extend(message["snap"] for message in client.take()
                             if message["type"] == "state" and any(
                                 e["kind"] == "smoke" and e["owner"] == client.pid for e in message["snap"]["effects"]
                             ))
            return bool(snapshots)

        _wait(received_smoke, session)
        shadow = Match(match.world, agent_roster=match.agents)
        apply_snapshot(shadow, snapshots[-1], client.pid)
        [copy] = [e for e in shadow.effects if e.kind == "smoke" and e.owner == client.pid]
        assert copy.fall_offset(copy.start) == pytest.approx(1.25)
    finally:
        client.close()


@pytest.mark.parametrize(("key", "index"), [("icebox", 0), ("icebox", 1), ("icebox", 4), ("breeze", 0)])
def test_guest_zipline_mount_and_release_over_localhost(key: str, index: int) -> None:
    from gameplay.world import load_playable_map

    world = load_playable_map(key)
    session = HostSession(Match(world), "Host", _free_port())
    client = None
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        match = session.match
        match.phase_until = match.time
        session.step(1 / 64)
        player = match.players[client.pid]
        cable = world.ziplines[index]
        player.pos = cable.start
        player.ground = world.ground_height(player.pos)
        player.level = world.floor_level(player.pos)
        shadow = Match(world)
        positions = {}

        def guest_has_zipline(expected: int | None) -> bool:
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], client.pid, predict_own=True, server_pos=positions)
            rider = shadow.players.get(client.pid)
            return rider is not None and rider.zipline == expected

        client.send(Command(interact=True))
        _wait(lambda: guest_has_zipline(index), session)
        assert shadow.players[client.pid].ground == (cable.level if cable.lower is None else cable.lower)
        client.send(Command(move_y=1, facing=90))
        if cable.lower is None:
            _wait(lambda: player.pos.x > cable.start.x + 1, session)
        else:
            _wait(lambda: guest_has_zipline(index) and shadow.players[client.pid].ground > cable.lower + 0.5, session)
        client.send(Command(jump=True))
        _wait(lambda: guest_has_zipline(None), session)
        assert player.zipline is None and shadow.players[client.pid].pos == positions[client.pid]
    finally:
        if client is not None:
            client.close()
        session.close()


def test_held_input_continues_between_client_messages(session: HostSession) -> None:
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        session.match.phase_until = session.match.time
        session.step(1 / 64)
        client.send(Command(move_y=1.0, facing=session.match.players[client.pid].facing, buy=["phantom"]))
        _wait(lambda: client.pid in session.last, session)
        before = session.match.players[client.pid].pos
        for _ in range(20):  # no new messages: the last held command keeps applying
            session.step(1 / 64)
        assert (session.match.players[client.pid].pos - before).length() > 0.3
        assert session.last[client.pid].buy == []
    finally:
        client.close()


def test_guest_spike_equipment_and_refund_reach_host(session: HostSession) -> None:
    from gameplay.geometry import Rect, Vec
    from gameplay.match import Effect
    from gameplay.world import Wall

    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.match.players[client.pid].team = 0
        session.start(team_size=2)
        match = session.match
        guest = match.players[client.pid]
        host.credits = 5000
        for _ in range(2):
            client.send(Command(request_clicks=["vandal"]))
        _wait(lambda: len(session.net.pending.get(guest.pid, Command()).request_clicks) == 2)
        session.step(1 / 64)
        assert guest.request == "" and guest.request_revision == 2
        session.step(1 / 64)
        assert guest.request_revision == 2

        def fulfill(key: str) -> None:
            client.send(Command(request=key))
            _wait(lambda: guest.request == key, session)
            session.step(1 / 64, {host.pid: Command(buy=[guest.gift_action()])})

        client.send(Command(request="vandal"))
        _wait(lambda: guest.request == "vandal", session)
        stale_gift = guest.gift_action()
        client.send(Command(request=""))
        _wait(lambda: guest.pid in session.net.pending, timeout=5)
        session.step(1 / 64, {host.pid: Command(buy=[stale_gift])})
        assert guest.request == "" and host.credits == 5000 and "primary" not in guest.weapons
        client.send(Command(request="vandal"))
        _wait(lambda: guest.request == "vandal", session)
        session.step(1 / 64, {host.pid: Command(buy=[stale_gift])})
        assert host.credits == 5000 and "primary" not in guest.weapons
        session.step(1 / 64, {host.pid: Command(buy=[guest.gift_action()])})
        assert host.credits == 2100

        client.send(Command(buy=["sell:vandal", "sell:vandal"]))
        _wait(lambda: "primary" not in guest.weapons, session)
        assert host.credits == 5000 and guest.credits == 800

        guest.credits = 5000
        client.send(Command(request="vandal"))
        _wait(lambda: guest.request == "vandal", session)
        client.send(Command(buy=["buy:vandal"]))
        _wait(lambda: guest.pid in session.net.pending)
        session.step(1 / 64, {host.pid: Command(buy=[guest.gift_action()])})
        assert guest.credits == 2100 and host.credits == 5000 and guest.request == ""
        revision = guest.request_revision
        client.send(Command(request="vandal"))
        _wait(lambda: guest.pid in session.net.pending)
        session.step(1 / 64)
        assert guest.request == "" and guest.request_revision == revision
        guest.weapon.mag -= 1
        client.send(Command(reload=True))
        _wait(lambda: guest.reload_until > session.match.time, session)
        fulfill("phantom")
        assert host.credits == 2100 and guest.reload_until == 0
        client.send(Command(buy=["sell:phantom", "sell:phantom"]))
        _wait(lambda: guest.weapon.key == "vandal", session)
        assert (host.credits, guest.credits) == (5000, 2100)
        guest.weapon.mag -= 1
        client.send(Command(reload=True))
        _wait(lambda: guest.reload_until > session.match.time, session)
        client.send(Command(buy=["sell:vandal", "sell:vandal"]))
        _wait(lambda: "primary" not in guest.weapons, session)
        assert (host.credits, guest.credits, guest.reload_until) == (5000, 5000, 0)

        fulfill("vandal")
        assert host.credits == 2100
        client.send(Command(drop=True))
        _wait(lambda: "primary" not in guest.weapons, session)
        client.send(Command(request="vandal"))
        _wait(lambda: guest.request == "vandal", session)
        picked_up_gift = guest.gift_action()
        guest.pos = next(drop.pos for drop in session.match.drops if drop.key == "vandal")
        client.send(Command(interact=True))
        _wait(lambda: "primary" in guest.weapons, session)
        assert guest.request == ""
        assert not match.buy(host, picked_up_gift)
        client.send(Command(buy=["sell:vandal", "sell:vandal"], request="phantom"))
        _wait(lambda: guest.request == "phantom", session)
        assert not session.match.sellable(guest, "vandal")
        assert (host.credits, guest.credits) == (2100, 5000)

        match.spike_carrier = guest.pid
        client.send(Command(slot="spike"))
        shadow = Match(match.world)

        def equipped_on_guest() -> bool:
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], client.pid)
            return client.pid in shadow.players and shadow.players[client.pid].spike_equipped

        _wait(equipped_on_guest, session)
        assert guest.spike_equipped
        guest.pos, guest.ground, guest.level = Vec(24, 5), 0, 0
        rect = Rect(24.5, 4.5, 24.6, 5.5)
        match.effects.append(Effect("wall", guest.pid, guest.team, rect.center, match.time + 10,
                                    props={"barrier": Wall(rect, 3, blocks_sight=False)}))
        client.send(Command(drop=True, facing=90))
        _wait(lambda: match.spike_carrier != guest.pid, session)
        assert match.spike_pos == Vec(24, 5)
        assert not guest.spike_equipped and guest.weapon is not None
        assert guest.equip_until > match.time
    finally:
        client.close()


@pytest.mark.parametrize("guest_picks_up", [False, True], ids=["host", "guest"])
def test_weapon_swap_at_round_start_cancels_previous_reload(session: HostSession, guest_picks_up: bool) -> None:
    from gameplay.match import Drop

    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        if guest_picks_up:
            client.choose_team(0)
            _wait(lambda: session.match.players[client.pid].team == 0, session)
        session.start(team_size=2 if guest_picks_up else 1)
        match = session.match
        guest = match.players[client.pid]
        picker = guest if guest_picks_up else host
        match.spike_carrier = picker.pid
        assert match.world.site_at(picker.pos, picker.level) is None
        picker.weapons["primary"] = match._new_weapon("phantom")
        picker.slot = "primary"
        picker.weapon.mag -= 1

        def input_for_picker(cmd: Command, applied: Callable[[], bool]) -> None:
            if guest_picks_up:
                client.send(cmd)
                _wait(applied, session)
            else:
                session.step(1 / 64, {host.pid: cmd})
                assert applied()

        input_for_picker(Command(reload=True), lambda: picker.reload_until > match.time)
        previous_reload = picker.reload_until
        match.drops.append(Drop("vandal", 7, 30, picker.pos))
        match.phase_until = match.time
        input_for_picker(Command(interact=True), lambda: picker.weapon.key == "vandal")
        assert match.phase == "live"
        assert match.spike_carrier == picker.pid and picker.plant_progress == 0
        assert picker.reload_until == 0
        assert any(drop.key == "phantom" for drop in match.drops)
        while match.time <= previous_reload:
            session.step(1 / 64)

        shadow = Match(match.world)

        def guest_sees_swap() -> bool:
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], client.pid)
            return (shadow.phase == "live" and any(drop.key == "phantom" for drop in shadow.drops)
                    and (not guest_picks_up or shadow.players[client.pid].weapon.mag == 7))

        _wait(guest_sees_swap, session)
        assert (picker.weapon.mag, picker.weapon.reserve) == (7, 30)
    finally:
        client.close()


@pytest.mark.parametrize("actions,dropped,held", [
    (["sidearm", "drop"], "classic", "vandal"),
    (["drop", "sidearm"], "vandal", "classic"),
    (["sidearm", "drop", "melee"], "classic", "tactical_knife"),
])
def test_guest_weapon_switch_and_drop_keep_input_order(session: HostSession, actions, dropped, held) -> None:
    session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        match = session.match
        guest = match.players[client.pid]
        guest.credits = 5000
        client.send(Command(buy=["buy:vandal"]))
        _wait(lambda: guest.slot == "primary", session)
        for action in actions:
            client.send(Command(equipment_actions=[action]))
        _wait(lambda: (cmd := session.net.pending.get(guest.pid)) is not None and cmd.equipment_actions == actions)
        session.step(1 / 64)
        assert [drop.key for drop in match.drops] == [dropped]
        assert guest.weapon.key == held
    finally:
        client.close()


@pytest.mark.parametrize("offset", [-1, 0, 1], ids=["before", "at", "after"])
def test_guest_purchase_and_slot_selection_at_buy_deadline(session: HostSession, offset: int) -> None:
    session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        match = session.match
        guest = match.players[client.pid]
        guest.credits = 5000
        guest.slot = "melee"
        match.phase_until = match.time + (4 - offset) / 256
        client.send(Command(buy=["buy:vandal"], slot="sidearm"))
        _wait(lambda: guest.pid in session.net.pending)
        session.step(1 / 64)
        assert guest.slot == "sidearm"
        assert match.phase == ("buy" if offset < 0 else "live")
        assert guest.credits == (2100 if offset < 0 else 5000)
        assert ("primary" in guest.weapons) == (offset < 0)
    finally:
        client.close()


@pytest.mark.parametrize("refund", [False, True])
def test_guest_refund_one_tick_before_buy_deadline_updates_thrifty(session: HostSession, refund: bool) -> None:
    from gameplay.net import events_from_json

    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        assert session.start(team_size=1)
        match = session.match
        guest = match.players[client.pid]
        assert guest.team != host.team
        host.credits = 2000
        session.step(1 / 64, {host.pid: Command(buy=["buy:spectre", "buy:light_armor"])})
        assert host.weapons["primary"].key == "spectre" and host.armor == 25
        credits, classic = guest.credits, guest.weapons["sidearm"]
        pistol_loadout_value = sum(match.weapons[weapon.key].price for weapon in guest.weapons.values())
        client.send(Command(buy=["buy:ghost"]))
        _wait(lambda: match.sellable(guest, "ghost"), session)
        assert guest.credits == credits - match.weapons["ghost"].price
        client.send(Command(buy=["sell:ghost"] if refund else []))
        _wait(lambda: guest.pid in session.net.pending)

        tick = 1 / 64
        deadline = match.time + 2 * tick
        match.phase_until = deadline
        session.step(tick)
        assert match.phase == "buy" and match.time == deadline - tick
        expected_credits = credits if refund else credits - match.weapons["ghost"].price
        expected_sidearm = classic if refund else guest.weapons["sidearm"]
        assert guest.credits == expected_credits
        assert guest.weapons["sidearm"] == expected_sidearm
        session.step(tick)
        assert match.phase == "live" and match.time == deadline
        assert match.loadout_value[host.team] == pistol_loadout_value + 2000
        assert match.loadout_value[guest.team] == pistol_loadout_value + (0 if refund else match.weapons["ghost"].price)

        shadow = Match(match.world)
        titles = []

        def update_guest_view() -> None:
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], client.pid)
                elif message["type"] == "events":
                    titles.extend(e.data for e in events_from_json(message["events"])
                                  if e.kind == "round_title" and e.data["title"] == "Thrifty")

        def guest_sees_live_round() -> bool:
            update_guest_view()
            return shadow.phase == "live" and shadow.time >= deadline

        _wait(guest_sees_live_round, session)
        remote = shadow.players[guest.pid]
        assert remote.credits == guest.credits == expected_credits
        assert remote.weapons["sidearm"] == guest.weapons["sidearm"] == expected_sidearm
        starting_loadout_values = match.loadout_value.copy()
        match.drops.append(match._ground_weapon(guest, match._new_weapon("vandal"), guest.pos))
        client.send(Command(interact=True))
        _wait(lambda: guest.pid in session.net.pending)

        def guest_sees_vandal_pickup() -> bool:
            update_guest_view()
            weapon = shadow.players[guest.pid].weapons.get("primary")
            return weapon is not None and weapon.key == "vandal"

        _wait(guest_sees_vandal_pickup, session)
        assert guest.weapons["primary"].key == "vandal"
        assert match.loadout_value == starting_loadout_values
        match._kill(guest, host, "vandal", "body")
        events = session.step(tick)
        expected_titles = [{"title": "Thrifty", "team": guest.team}] if refund else []
        assert [e.data for e in events if e.kind == "round_title" and e.data["title"] == "Thrifty"] == expected_titles

        def guest_sees_round_end() -> bool:
            update_guest_view()
            return shadow.phase == "end"

        _wait(guest_sees_round_end, session)
        assert shadow.round_winner == guest.team
        assert titles == expected_titles
    finally:
        client.close()


def test_guest_reload_targets_weapon_selected_at_keypress(session: HostSession) -> None:
    session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        match = session.match
        guest = match.players[client.pid]
        guest.credits = 5000
        client.send(Command(buy=["buy:vandal"]))
        _wait(lambda: guest.slot == "primary", session)
        guest.weapons["primary"].mag -= 1
        guest.weapons["sidearm"].mag -= 1
        actions = ["sidearm", "reload", "primary"]
        for action in actions:
            client.send(Command(equipment_actions=[action]))
        _wait(lambda: (cmd := session.net.pending.get(guest.pid)) is not None and cmd.equipment_actions == actions)
        events = session.step(1 / 64)
        assert [event.data["weapon"] for event in events if event.kind == "reload"] == ["classic"]
        assert guest.slot == "primary" and guest.reload_until == 0
    finally:
        client.close()


@pytest.mark.parametrize("obstacle", ["none", "barrier", "map-edge", "death-drop"])
def test_guest_equips_primary_after_dropping_sidearm(session: HostSession, obstacle: str) -> None:
    from gameplay.geometry import Rect, Vec
    from gameplay.match import Effect
    from gameplay.world import Wall

    session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "jett")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        match = session.match
        guest = match.players[client.pid]
        guest.credits = 5000
        client.send(Command(buy=["buy:vandal"], slot="sidearm"))
        _wait(lambda: "primary" in guest.weapons and guest.slot == "sidearm", session)
        guest.ult_points = match.ultimate_cost(guest)
        client.send(Command(ability="X"))
        _wait(lambda: guest.blades_equipped, session)
        client.send(Command(drop=True))
        _wait(lambda: guest.pid in session.net.pending)
        session.step(1 / 64)
        assert guest.blades_equipped and "sidearm" in guest.weapons and not match.drops
        client.send(Command(slot="sidearm"))
        _wait(lambda: not guest.blades_equipped, session)
        guest.pos, guest.ground, guest.level = Vec(24, 35), 0, 0
        if obstacle == "map-edge":
            match.phase_until = match.time
            session.step(1 / 64)
            guest.pos = Vec(match.world.width - 0.5, 35)
        origin = guest.pos
        if obstacle == "barrier":
            rect = Rect(24.5, 34.5, 24.6, 35.5)
            match.effects.append(Effect("wall", guest.pid, guest.team, rect.center, match.time + 10,
                                        props={"barrier": Wall(rect, 3, blocks_sight=False)}))
        elif obstacle == "death-drop":
            match.world.drop_zones.append((Rect(24.75, 34.5, 25.25, 35.5), origin))
        client.send(Command(drop=True, facing=90))
        _wait(lambda: guest.pid in session.net.pending)
        _wait(lambda: "sidearm" not in guest.weapons, session)
        assert guest.slot == "primary" and guest.equip_until > match.time
        if obstacle == "death-drop":
            assert not match.drops
        else:
            assert match.drops[0].pos == (origin + Vec(1, 0) if obstacle == "none" else origin)
    finally:
        client.close()


def test_guest_sage_does_not_spend_ultimate_on_ally_in_death_drop(session: HostSession) -> None:
    from gameplay.geometry import Rect, Vec

    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "sage")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(0)
        _wait(lambda: session.match.players[client.pid].team == 0, session)
        session.start(team_size=2)
        match = session.match
        sage = match.players[client.pid]
        match.phase_until = match.time
        session.step(1 / 64)
        sage.pos, host.pos = Vec(24, 5), Vec(24, 6.2)
        match.world.drop_zones.append((Rect(23, 6, 25, 7), sage.pos))
        match._kill(None, host, "fall", "legs")
        sage.ult_points = match.ultimate_cost(sage)
        cast = Command(ability="X", facing=0, cursor_depth=1.2)
        client.send(cast)
        _wait(lambda: sage.pid in session.net.pending)
        session.step(1 / 64)
        assert sage.ult_points == match.ultimate_cost(sage)
        assert not any(e.props.get("revive_pid") == host.pid for e in match.effects)
        assert not host.alive
    finally:
        client.close()


@pytest.mark.parametrize(("round_end", "timer_ticks_after_revive", "interrupt_defuse", "fuse_expires"), [
    (reason, offset, False, reason == "detonation")
    for reason in ("timer", "detonation", "early_defuse", "wingman_defuse", "elimination", "live_elimination")
    for offset in (1, 0, -1)
] + [
    (reason, 0, True, fuse_expires)
    for reason in ("early_defuse", "wingman_defuse")
    for fuse_expires in (False, True)
] + [
    (reason, offset, False, False)
    for reason in ("attackers_eliminated", "planted_sage_eliminated")
    for offset in (1, 0, -1)
])
def test_guest_sage_resurrection_at_round_deadline(
    session: HostSession, timer_ticks_after_revive: int, round_end: str,
    interrupt_defuse: bool, fuse_expires: bool, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gameplay.geometry import Vec

    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "sage")
    gekko_client = None
    try:
        match = session.match
        _wait(lambda: client.pid in match.players, session)
        client.choose_team(0)
        _wait(lambda: match.players[client.pid].team == 0, session)
        if round_end == "wingman_defuse":
            gekko_client = NetClient(f"127.0.0.1:{session.net.port}", "Defender", "gekko")
            _wait(lambda: gekko_client.pid in match.players, session)
            gekko_client.choose_team(1)
            _wait(lambda: match.players[gekko_client.pid].team == 1, session)
        session.start(team_size=2)
        sage = match.players[client.pid]
        host.credits = 5000
        session.step(1 / 64, {host.pid: Command(buy=["buy:vandal"])})
        match.phase_until = match.time
        session.step(1 / 64)
        sage.pos, host.pos = Vec(24, 5), Vec(24, 6.5)
        match._kill(None, host, "vandal", "body")
        sage.ult_points = match.ultimate_cost(sage)
        client.send(Command(ability="X", facing=0, cursor_depth=1.5))
        _wait(lambda: sage.pid in session.net.pending)
        session.step(1 / 64)
        marker, = [e for e in match.effects if e.props.get("revive_pid") == host.pid]

        deadline = marker.until + timer_ticks_after_revive / 64
        if round_end not in ("timer", "live_elimination", "attackers_eliminated"):
            # Keep the revived player outside the blast so the inventory outcome is observable.
            match._plant(sage, "A", point=Vec(48, 50))
            match.spike_planted_at = deadline - float(match._spike["fuse_time"])
        elif round_end == "timer":
            match.phase_until = deadline
        if round_end == "wingman_defuse":
            if not fuse_expires:
                match.spike_planted_at += 10
            defender = match.players[gekko_client.pid]
            defender.pos = match.spike_pos
            defender.ground = match.spike_ground
            defender.level = match.world.floor_level(defender.pos)
            defender.charges["Q"] = 1
            gekko_client.send(Command(ability="Q", ability_alt=True, cursor_depth=0))
            _wait(lambda: any(e.data.get("defusing") for e in match.effects), session)
            device = next(e for e in match.effects if e.data.get("defusing"))
            while match.time < deadline - 1 / 64:
                session.step(1 / 64)
            device.data["progress"] = float(match._spike["defuse_time"]) - 1 / 64
            if interrupt_defuse:
                from gameplay.kit.engine import remove_device

                tick_effects = match._tick_effects

                def destroy_wingman(dt: float) -> None:
                    remove_device(match, device, "destroy")
                    tick_effects(dt)

                with monkeypatch.context() as patch:
                    patch.setattr(match, "_tick_effects", destroy_wingman)
                    events = session.step(1 / 64)
                assert device.props.get("ended")
            else:
                events = session.step(1 / 64)
                assert any(e.kind == "defuse" and e.data["pid"] == defender.pid for e in events)
        elif round_end == "early_defuse":
            if not fuse_expires:
                match.spike_planted_at += 10
            defender = next(p for p in match.players.values() if p.team != host.team)
            defender.pos = match.spike_pos
            defender.is_bot = False
            while match.time < deadline - 1 / 64:
                session.step(1 / 64)
            defender.defusing = True
            defender.defuse_progress = float(match._spike["defuse_time"]) - 1 / 64
            events = session.step(1 / 64, {defender.pid: Command(use_spike=not interrupt_defuse)})
            if interrupt_defuse:
                assert any(e.kind == "defuse_stop" and e.data["pid"] == defender.pid for e in events)
        elif round_end in ("elimination", "live_elimination"):
            if round_end == "elimination":
                match.spike_planted_at += 10
            while match.time < deadline - 1 / 64:
                session.step(1 / 64)
            tick_effects = match._tick_effects

            def eliminate_defenders(dt: float) -> None:
                for defender in match.players.values():
                    if defender.team != host.team and defender.alive:
                        match._kill(sage, defender, "vandal", "body")
                tick_effects(dt)

            with monkeypatch.context() as patch:
                patch.setattr(match, "_tick_effects", eliminate_defenders)
                events = session.step(1 / 64)
            assert not any(e.kind == "revive" for e in events)
        elif round_end in ("attackers_eliminated", "planted_sage_eliminated"):
            if round_end == "planted_sage_eliminated":
                match.spike_planted_at += 10
            while match.time < deadline - 1 / 64:
                session.step(1 / 64)
            tick_effects = match._tick_effects

            def eliminate_sage(dt: float) -> None:
                match._kill(None, sage, "vandal", "body")
                tick_effects(dt)

            with monkeypatch.context() as patch:
                patch.setattr(match, "_tick_effects", eliminate_sage)
                events = session.step(1 / 64)
            assert not sage.alive
            if round_end == "planted_sage_eliminated":
                assert match.phase == "planted"
                assert host.alive == (timer_ticks_after_revive >= 0)
                assert any(e.kind == "revive" and e.data["pid"] == host.pid for e in events) == (
                    timer_ticks_after_revive == 0
                )
                _wait(lambda: match.time >= marker.until, session)
                assert match.phase == "planted" and host.alive and host.weapon.key == "vandal"
                assert not any(drop.key == "vandal" for drop in match.drops)
                shadow = Match(match.world)

                def guest_sees_revived_ally() -> bool:
                    for message in client.take():
                        if message["type"] == "state":
                            apply_snapshot(shadow, message["snap"], client.pid)
                    ally = shadow.players.get(host.pid)
                    return shadow.phase == "planted" and ally is not None and ally.alive

                _wait(guest_sees_revived_ally, session)
                return
            assert not any(e.kind == "revive" for e in events)
            if timer_ticks_after_revive == 1:
                assert match.phase == "live"
                assert host.alive and host.weapon.key == "vandal"
                return
            assert match.round_winner == 1 - host.team
        if interrupt_defuse:
            assert match.time == marker.until
            relevant = {e.kind for e in events} & {"revive", "defuse", "explode", "round_end"}
            if not fuse_expires:
                assert match.phase == "planted"
                assert host.alive and host.weapon.key == "vandal"
                assert relevant == {"revive"}
                return
            assert relevant == {"explode", "round_end"}
        _wait(lambda: match.time > marker.until, session)
        revived = timer_ticks_after_revive == 1
        assert match.phase == "end"
        expected_reason = {
            "timer": "Time ran out",
            "elimination": "Defenders eliminated",
            "live_elimination": "Defenders eliminated",
            "attackers_eliminated": "Attackers eliminated",
        }.get(round_end, "Bomb detonated" if fuse_expires else "Bomb defused")
        assert match.round_reason == expected_reason
        assert host.alive == revived and marker not in match.effects
        assert any(drop.key == "vandal" for drop in match.drops) != revived
        shadow = Match(match.world)

        def guest_sees_round_end() -> bool:
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], client.pid)
            return shadow.phase == "end"

        _wait(guest_sees_round_end, session)
        assert shadow.players[host.pid].alive == revived

        round_no = match.round_no
        match.phase_until = match.time
        session.step(1 / 64)
        assert match.round_no == round_no + 1 and match.phase == "buy"
        assert host.alive and host.weapon.key == ("vandal" if revived else "classic") and not match.drops
    finally:
        if gekko_client is not None:
            gekko_client.close()
        client.close()


@pytest.mark.parametrize("slot,key", [("primary", "vandal"), ("sidearm", "sheriff")])
@pytest.mark.parametrize("picked_up", [False, True])
def test_guest_sage_restores_only_an_unclaimed_death_drop(
    session: HostSession, slot: str, key: str, picked_up: bool,
) -> None:
    from gameplay.geometry import Vec

    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "sage")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(0)
        _wait(lambda: session.match.players[client.pid].team == 0, session)
        session.start(team_size=2)
        match = session.match
        sage = match.players[client.pid]
        host.credits = 5000
        session.step(1 / 64, {host.pid: Command(buy=[f"buy:{key}", "buy:regen_shield"])})
        assert host.armor_key == "regen_shield" and host.armor_reserve > 0
        host.weapons[slot].mag, host.weapons[slot].reserve = 2, 9
        match.phase_until = match.time
        session.step(1 / 64)
        sage.pos, host.pos = Vec(24, 5), Vec(24, 6.5)
        host.armor = 10
        host.armor_regen_at = match.time + 3.0
        host.reload_until = match.time + 3.0
        match._kill(None, host, "vandal", "body")
        [death_drop] = match.drops
        assert slot not in host.weapons
        sage.ult_points = match.ultimate_cost(sage)
        client.send(Command(ability="X", facing=0, cursor_depth=1.5))
        _wait(lambda: sage.pid in session.net.pending)
        session.step(1 / 64)
        assert sage.ult_points == 0 and not host.alive
        match._damage(None, host, 10, "body", "test")
        assert host.hp == 0

        if picked_up:
            sage.pos = host.pos
            client.send(Command(interact=True))
            _wait(lambda: sage.weapons.get(slot) is not None and sage.weapons[slot].key == key, session)
            sage.pos = Vec(24, 5)
        _wait(lambda: host.alive, session)
        assert (host.hp, host.armor, host.armor_key, host.armor_reserve, host.armor_regen_at) == (100, 0, "", 0, None)
        shadow = Match(match.world)

        def guest_sees_revived_host() -> bool:
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], client.pid)
            remote_host = shadow.players.get(host.pid)
            return remote_host is not None and remote_host.alive and remote_host.hp == 100

        _wait(guest_sees_revived_host, session)
        remote_host = shadow.players[host.pid]
        assert (remote_host.armor, remote_host.armor_key, remote_host.armor_reserve) == (0, "", 0)
        assert remote_host.channel_until == pytest.approx(host.channel_until)
        assert host.channel_until > match.time
        assert all(drop is not death_drop for drop in match.drops)
        if picked_up:
            assert (sage.weapons[slot].mag, sage.weapons[slot].reserve) == (2, 9)
            assert host.weapon.key == "classic"
            assert all(weapon.key != key for weapon in host.weapons.values())
        else:
            restored = host.weapons[slot]
            assert (restored.key, restored.mag, restored.reserve) == (key, 2, 9)

        match._damage(None, host, 10, "body", "test")
        assert host.hp == 90
        pos, mag = host.pos, host.weapon.mag
        active_slot = host.slot
        assert host.reload_until == 0
        session.step(1 / 64, {host.pid: Command(slot="melee", reload=True, equipment_actions=["reload", "melee"])})
        assert host.slot == active_slot and host.reload_until == 0
        move_and_fire = Command(move_y=1, facing=180, fire=True)
        session.step(1 / 64, {host.pid: move_and_fire})
        assert host.pos == pos and host.weapon.mag == mag

        ground_weapon = match._ground_weapon(host, match._new_weapon("ghost"), pos)
        sage.pos = Vec(24, 3)
        match.drops.insert(0, ground_weapon)
        assert match.side(host.team) == "attack"
        match.spike_carrier, match.spike_pos = None, pos
        match.spike_ground = match.world.ground_height(pos, host.level)
        match.orbs = [pos]
        session.step(1 / 64, {host.pid: Command(interact=True)})
        assert ground_weapon in match.drops and match.spike_pos == pos
        assert host.orb_progress == 0

        _wait(lambda: match.time > host.channel_until, session)
        assert match.spike_carrier == host.pid
        session.step(1 / 64, {host.pid: move_and_fire})
        assert host.pos != pos and host.weapon.mag == mag - 1
        session.step(1 / 64, {host.pid: Command(interact=True)})
        assert host.weapons["sidearm"].key == "ghost" and host.orb_progress > 0
        session.step(1 / 64, {host.pid: Command(slot="melee")})
        assert host.slot == "melee"
        session.step(1 / 64, {host.pid: Command(slot="sidearm")})
        host.weapon.mag -= 1
        session.step(1 / 64, {host.pid: Command(reload=True)})
        assert host.reload_until > match.time
    finally:
        client.close()


def test_dropped_weapon_carries_with_new_owner_until_side_switch(session: HostSession) -> None:
    from gameplay.geometry import heading

    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(0)
        _wait(lambda: session.match.players[client.pid].team == 0, session)
        session.start(team_size=2)
        match = session.match
        guest = match.players[client.pid]
        host.credits = 5000
        session.step(1 / 64, {host.pid: Command(buy=["buy:vandal"])})
        host.weapon.mag, host.weapon.reserve = 7, 30
        match.phase_until = match.time
        session.step(1 / 64, {host.pid: Command(drop=True)})
        guest.pos = match.drops[0].pos
        client.send(Command(interact=True))
        _wait(lambda: "primary" in guest.weapons, session)
        assert "primary" not in host.weapons
        assert (guest.weapon.key, guest.weapon.mag, guest.weapon.reserve) == ("vandal", 7, 30)

        shadow = Match(match.world)

        def guest_sees_round(number: int) -> bool:
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], client.pid)
            return shadow.round_no == number and shadow.phase == "buy"

        def next_round() -> None:
            match._end_round(host.team, "Time ran out")
            match.phase_until = match.time
            session.step(1 / 64)
            _wait(lambda: guest_sees_round(match.round_no), session)

        next_round()
        vandal = match.weapons["vandal"]
        assert (guest.weapon.key, guest.weapon.mag, guest.weapon.reserve) == ("vandal", vandal.mag, vandal.reserve)
        remote_weapon = shadow.players[guest.pid].weapon
        assert (remote_weapon.key, remote_weapon.mag, remote_weapon.reserve) == ("vandal", vandal.mag, vandal.reserve)
        assert "primary" not in host.weapons and not match.drops

        match.round_no = int(match._r["half_after"])
        match.phase_until = match.time
        session.step(1 / 64, {host.pid: Command(drop=True)})
        assert match.drops and match.drops[0].pos == host.pos + heading(host.facing)
        next_round()
        assert match.side(guest.team) == "defense"
        assert match.spike_carrier is None and match.spike_pos is not None
        assert shadow.spike_carrier is None and shadow.spike_pos == match.spike_pos
        assert guest.weapon.key == shadow.players[guest.pid].weapon.key == "classic"
        assert "primary" not in guest.weapons and not match.drops and not shadow.drops
        _wait(lambda: match.spike_carrier is not None, session)
        bot = match.players[match.spike_carrier]
        assert bot.is_bot and match.side(bot.team) == "attack"
    finally:
        client.close()


@pytest.mark.parametrize("guest_drops", [False, True], ids=["host", "guest"])
def test_melee_only_player_gets_classic_when_buy_ends(session: HostSession, guest_drops: bool) -> None:
    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        match = session.match
        player = match.players[client.pid] if guest_drops else host
        if guest_drops:
            client.send(Command(drop=True))
            _wait(lambda: set(player.weapons) == {"melee"}, session)
        else:
            session.step(1 / 64, {host.pid: Command(drop=True)})
            assert set(player.weapons) == {"melee"}

        match.phase_until = match.time
        session.step(1 / 64)
        assert match.phase == "live" and player.weapon.key == "classic"
        assert player.weapon.mag == match.weapons["classic"].mag
    finally:
        client.close()


@pytest.mark.parametrize("guest_recovers", [False, True], ids=["host", "guest"])
@pytest.mark.parametrize("obstacle", ["door", "ability-wall"])
def test_attacker_can_interact_to_recover_spike_after_carrier_dies(session: HostSession, guest_recovers: bool, obstacle: str) -> None:
    from gameplay.geometry import Rect, Vec
    from gameplay.match import Effect, INTERACT_RANGE, PICKUP_RANGE
    from gameplay.world import Wall

    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(0)
        _wait(lambda: session.match.players[client.pid].team == 0, session)
        session.start(team_size=2)
        match = session.match
        guest = match.players[client.pid]
        receiver, carrier = (guest, host) if guest_recovers else (host, guest)
        match.phase_until = match.time
        session.step(1 / 64)
        carrier.pos, carrier.ground, carrier.level = Vec(24, 5), 0, 0
        receiver.ground, receiver.level = 0, 0
        receiver.pos = carrier.pos + Vec((PICKUP_RANGE + INTERACT_RANGE) / 2, 0)
        match.spike_carrier = carrier.pid
        match._kill(None, carrier, "test", "body")
        session.step(1 / 64)
        assert match.spike_carrier is None and match.spike_pos == carrier.pos

        x, y = carrier.pos.x, carrier.pos.y
        rect = Rect(x + 0.5, y - 0.5, x + 0.6, y + 0.5)
        smoke = Effect("smoke", carrier.pid, carrier.team, rect.center, match.time + 10, radius=0.3)
        match.effects.append(smoke)
        if obstacle == "door":
            match.world.walls.append(Wall(rect, 3, door=True, reopenable=False))
        else:
            barrier = Effect("wall", carrier.pid, carrier.team, rect.center, match.time + 10,
                             props={"barrier": Wall(rect, 3, blocks_sight=False)})
            match.effects.append(barrier)
        if guest_recovers:
            client.send(Command(interact=True))
            _wait(lambda: guest.pid in session.net.pending)
            session.step(1 / 64)
        else:
            session.step(1 / 64, {host.pid: Command(interact=True)})
        assert match.spike_carrier is None
        if obstacle == "door":
            match.open_doors.add(rect)
        else:
            match.effects.remove(barrier)
        if not guest_recovers:
            session.step(1 / 64, {host.pid: Command(interact=True)})
        _wait(lambda: match.spike_carrier == receiver.pid, session)
        assert match.spike_pos is None
    finally:
        client.close()


@pytest.mark.parametrize("killed", [False, True], ids=["release", "death"])
def test_only_selected_defuser_stops_moving_in_start_tick(session: HostSession, killed: bool, monkeypatch) -> None:
    from gameplay.geometry import Vec

    host = session.match.add_player("Host", 1, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(1)
        _wait(lambda: session.match.players[client.pid].team == 1, session)
        session.start(team_size=2)
        match = session.match
        guest = match.players[client.pid]
        attacker = next(p for p in match.players.values() if p.team == 0)
        attacker.pos, host.pos, guest.pos = Vec(24, 5), Vec(24, 4), Vec(24, 6)
        match._plant(attacker, "A")
        start = guest.pos
        hold = Command(use_spike=True, move_y=1, facing=0)
        client.send(hold)
        _wait(lambda: guest.pid in session.net.pending)
        session.step(1 / 64, {host.pid: hold})
        assert host.defusing and not guest.defusing and guest.pos.y > start.y
        if killed:
            host.defuse_progress = 3.5
            match.spike_half_defused = True
            tick_effects = match._tick_effects

            def kill_before_spike_tick(dt: float) -> None:
                tick_effects(dt)
                match._kill(attacker, host, "vandal", "body")

            monkeypatch.setattr(match, "_tick_effects", kill_before_spike_tick)
        session.step(1 / 64, {host.pid: hold if killed else Command()})
        assert not host.defusing and guest.defusing and guest.vel.length() == 0
        if killed:
            assert not host.alive and guest.defuse_progress == 3.5
    finally:
        client.close()


@pytest.mark.parametrize("after_half", [False, True], ids=["before-half", "after-half"])
@pytest.mark.parametrize("interruption", ["door", "release", "barrier"])
def test_guest_defuse_stops_with_checkpoint_and_reequip(session: HostSession, after_half: bool, interruption: str) -> None:
    from gameplay.geometry import Rect, Vec
    from gameplay.match import Effect
    from gameplay.world import Wall

    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        match = session.match
        guest = match.players[client.pid]
        match.phase_until = match.time
        session.step(1 / 64)
        host.pos, guest.pos = Vec(24, 5), Vec(24, 6.2)
        door = Wall(Rect(23.5, 5.55, 24.5, 5.65), 3, door=True)
        release = interruption == "release"
        barrier = Effect("wall", host.pid, host.team, door.rect.center, match.time + 10,
                         props={"barrier": Wall(door.rect, 3, blocks_sight=False)})
        match.effects.append(Effect("smoke", host.pid, host.team, door.rect.center, match.time + 10, radius=0.3))
        match.world.walls.append(door)
        match.open_doors.add(door.rect)
        match._plant(host, "A")
        guest.weapon.mag -= 1
        starting_magazine = guest.weapon.mag
        if after_half:
            client.send(Command(reload=True))
            _wait(lambda: guest.reload_until > match.time, session)
            guest.reload_until = match.time + 1 / 64
        start = guest.pos
        client.send(Command(interact=True, reload=True, fire=True, move_y=1, jump=True))
        _wait(lambda: guest.pid in session.net.pending)
        guest.vel = Vec(0, 4)
        _wait(lambda: guest.defusing, session)
        assert guest.pos == start and guest.z == 0 and guest.vel.length() == 0
        assert guest.reload_until == 0 and guest.weapon.mag == starting_magazine
        while guest.defuse_progress < (3.6 if after_half else 1.0):
            session.step(1 / 64)
        client.send(Command(use_spike=True, equipment_actions=["sidearm", "drop"]))
        _wait(lambda: guest.pid in session.net.pending)
        session.step(1 / 64)
        assert guest.defusing and "sidearm" in guest.weapons and not match.drops
        magazine = guest.weapon.mag
        if release:
            client.send(Command(fire=True))
            _wait(lambda: guest.pid in session.net.pending)
        elif interruption == "barrier":
            match.effects.append(barrier)
        else:
            match.open_doors.remove(door.rect)
        session.step(1 / 64)
        checkpoint = 3.5 if after_half else 0.0
        assert not guest.defusing and guest.defuse_progress == checkpoint
        assert guest.equip_until > match.time and guest.weapon.mag == magazine
        if release:
            client.send(Command(use_spike=True))
            _wait(lambda: guest.pid in session.net.pending)
        elif interruption == "barrier":
            match.effects.remove(barrier)
        else:
            match.open_doors.add(door.rect)
        session.step(1 / 64)
        assert guest.defusing and guest.defuse_progress == pytest.approx(checkpoint + 1 / 64)
    finally:
        client.close()


@pytest.mark.parametrize("cancel", [False, True], ids=["complete", "cancel"])
def test_guest_cannot_fire_during_weapon_reequip_after_plant(session: HostSession, cancel: bool) -> None:
    session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(0)
        _wait(lambda: session.match.players[client.pid].team == 0, session)
        session.start(team_size=2)
        match = session.match
        guest = match.players[client.pid]
        guest.credits = 5000
        client.send(Command(buy=["buy:vandal"]))
        _wait(lambda: guest.slot == "primary", session)
        match.phase_until = match.time
        session.step(1 / 64)
        site = match.world.sites[0]
        guest.pos = site.rect.center
        guest.ground = match.world.ground_height(guest.pos)
        guest.level = match.world.floor_level(guest.pos)
        match.spike_carrier, match.spike_pos = guest.pid, None
        client.send(Command(use_spike=True))
        _wait(lambda: guest.plant_progress > 0, session)
        magazine = guest.weapon.mag
        if not cancel:
            guest.plant_progress = 4 - 1 / 128
            session.step(1 / 64)
            assert match.phase == "planted" and guest.equip_until > match.time
        client.send(Command(fire=True))
        _wait(lambda: guest.pid in session.net.pending)
        session.step(1 / 64)
        if cancel:
            assert match.phase == "live" and match.spike_carrier == guest.pid
            assert guest.plant_progress == 0 and guest.equip_until > match.time
        assert guest.weapon.mag == magazine
        _wait(lambda: guest.weapon.mag < magazine, session)
    finally:
        client.close()


@pytest.mark.parametrize("offset", [-1, 0, 1], ids=["before", "tie", "after"])
@pytest.mark.parametrize("wingman", [False, True], ids=["player", "wingman"])
def test_guest_defuse_and_detonation_in_same_tick(session: HostSession, offset: int, wingman: bool) -> None:
    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "gekko" if wingman else "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        match = session.match
        defender = match.players[client.pid]
        match._plant(host, "A")
        defender.pos = host.pos
        defender.level, defender.ground = host.level, host.ground
        if wingman:
            assert defender.agent == "gekko"
            defender.charges["Q"] = 1
            client.send(Command(ability="Q", ability_alt=True, cursor_depth=0))
            _wait(lambda: any(e.data.get("defusing") for e in match.effects), session)
            device = next(e for e in match.effects if e.data.get("defusing"))
            device.data["progress"] = 7 - (2 + offset) / 256
        else:
            client.send(Command(use_spike=True))
            _wait(lambda: defender.defusing, session)
            defender.defuse_progress = 7 - (2 + offset) / 256
        match.spike_planted_at = match.time - 45 + 2 / 256
        events = session.step(1 / 64)
        assert match.round_winner == (defender.team if offset <= 0 else host.team)
        assert {e.kind for e in events} & {"defuse", "explode"} == ({"defuse"} if offset <= 0 else {"explode"})
    finally:
        client.close()


@pytest.mark.parametrize("teammate_survives", [False, True])
def test_wingman_defuse_survives_gekko_only_with_live_teammate(session: HostSession, teammate_survives: bool) -> None:
    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "gekko")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=2 if teammate_survives else 1)
        match = session.match
        gekko = match.players[client.pid]
        match._plant(host, "A")
        gekko.pos, gekko.level, gekko.ground = host.pos, host.level, host.ground
        gekko.charges["Q"] = 1
        client.send(Command(ability="Q", ability_alt=True, cursor_depth=0))
        _wait(lambda: any(e.data.get("defusing") for e in match.effects), session)
        wingman = next(e for e in match.effects if e.data.get("defusing"))
        wingman.data["progress"] = 7 - 1 / 128
        match._kill(host, gekko, "vandal", "body")
        session.step(1 / 64)
        assert wingman.props.get("ended")
        assert match.round_winner == (gekko.team if teammate_survives else host.team)
        assert gekko.defuses == int(teammate_survives)
    finally:
        client.close()


@pytest.mark.parametrize("mid_tick", [False, True], ids=["between-ticks", "during-tick"])
def test_two_wingmen_defuse_exclusively_and_preserve_checkpoint(session: HostSession, mid_tick: bool, monkeypatch) -> None:
    from unittest.mock import Mock

    from client.events import EventsMixin
    from gameplay.geometry import Vec
    from gameplay.kit.engine import remove_device
    from gameplay.net import events_from_json

    attacker = session.match.add_player("Attacker", 0, "omen")
    host = session.match.add_player("Host", 1, "gekko")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "gekko")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(1)
        _wait(lambda: session.match.players[client.pid].team == 1, session)
        session.start(team_size=2)
        match = session.match
        guest = match.players[client.pid]
        match._plant(attacker, "A")
        for player in (host, guest):
            player.pos, player.ground, player.level = attacker.pos, attacker.ground, attacker.level
            player.charges["Q"] = 1
        cast = Command(ability="Q", ability_alt=True, cursor_depth=0)
        client.send(cast)
        _wait(lambda: guest.pid in session.net.pending)
        session.step(1 / 64, {host.pid: cast})
        first, second = [e for e in match.effects if e.props.get("gekko_objective")]
        first.data["path"].clear()
        second.data["path"].clear()
        session.step(1 / 64)
        assert first.data.get("defusing") and not second.data.get("defusing")
        assert second.data["progress"] == 0
        checkpoint = float(match._spike["defuse_checkpoint"])
        first.data["progress"] = checkpoint - 1 / 64
        match.players[first.owner].pos = match.spike_pos + Vec(6, 0)
        session.step(1 / 64)
        received = []

        def receive_half():
            for message in client.take():
                if message["type"] == "events":
                    received.extend(event for event in events_from_json(message["events"])
                                    if event.kind == "defuse_half")
            return bool(received)

        _wait(receive_half, session)
        [cue] = received
        assert Vec(*cue.data["pos"]) == match.spike_pos
        assert match.spike_pos != match.players[cue.data["pid"]].pos
        audio = EventsMixin()
        audio.me, audio.match, audio.sound = client.pid, match, Mock()
        audio.handle_events([cue])
        audio.sound.play.assert_called_once_with("spike_defuse_half", guest, match.spike_pos, 35,
                                                 occluded=audio.occluded(guest, match.spike_pos))
        first.data["progress"] = checkpoint
        if mid_tick:
            tick_effects = match._tick_effects

            def destroy_then_tick(dt: float) -> None:
                remove_device(match, first, "destroy")
                tick_effects(dt)

            with monkeypatch.context() as patch:
                patch.setattr(match, "_tick_effects", destroy_then_tick)
                session.step(1 / 64)
            assert second.data.get("defusing") and second.data["progress"] == 3.5
        else:
            remove_device(match, first, "destroy")
        session.step(1 / 64)
        assert second.data.get("defusing") and second.data["progress"] == 3.5 + 1 / 64
    finally:
        client.close()


@pytest.mark.parametrize("interruption", ["release", "death", "out-of-range", "door"])
def test_player_defuse_reservation_matches_wingman_progress(session: HostSession, interruption: str, monkeypatch) -> None:
    from gameplay.geometry import Rect, Vec
    from gameplay.world import Wall
    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "gekko")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=2 if interruption == "death" else 1)
        match = session.match
        guest = match.players[client.pid]
        match._plant(host, "A")
        guest.pos, guest.level, guest.ground = host.pos, host.level, host.ground
        guest.charges["Q"] = 1
        client.send(Command(ability="Q", ability_alt=True, cursor_depth=0))
        _wait(lambda: any(e.props.get("gekko_objective") for e in match.effects), session)
        wingman = next(e for e in match.effects if e.props.get("gekko_objective"))
        wingman.data["path"].clear()
        door = None
        if interruption == "door":
            point = match.spike_pos
            guest.pos = point + Vec(0, 1.2)
            door = Wall(Rect(point.x - 0.5, point.y + 0.55, point.x + 0.5, point.y + 0.65), 3, door=True)
            match.world.walls.append(door)
            match.open_doors.add(door.rect)
        client.send(Command(use_spike=True))
        _wait(lambda: guest.pid in session.net.pending)
        session.step(1 / 64)
        assert guest.defusing and not wingman.data.get("defusing")
        assert guest.defuse_progress == 1 / 64 and wingman.data["progress"] == 0

        if interruption != "release":
            match.spike_half_defused = True
            guest.defuse_progress = 3.5
            tick_effects = match._tick_effects

            def interrupt_then_tick(dt: float) -> None:
                if interruption == "death":
                    match._kill(host, guest, "vandal", "body")
                elif door is not None:
                    match.open_doors.remove(door.rect)
                else:
                    guest.pos = guest.pos + Vec(0, 3)
                tick_effects(dt)

            with monkeypatch.context() as patch:
                patch.setattr(match, "_tick_effects", interrupt_then_tick)
                session.step(1 / 64)
            assert wingman.data["progress"] == 3.5
        else:
            client.send(Command())
            _wait(lambda: guest.pid in session.net.pending)
            session.step(1 / 64)
            assert wingman.data["progress"] == 1 / 64
        assert not guest.defusing and wingman.data.get("defusing")
    finally:
        client.close()


@pytest.mark.parametrize("checkpoint", [0.0, 3.5], ids=["before-half", "at-half"])
def test_guest_takes_over_defuse_in_tick_wingman_is_destroyed(session: HostSession, checkpoint: float, monkeypatch) -> None:
    from gameplay.kit.engine import remove_device

    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "gekko")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        match = session.match
        guest = match.players[client.pid]
        match._plant(host, "A")
        guest.pos, guest.level, guest.ground = host.pos, host.level, host.ground
        guest.charges["Q"] = 1
        client.send(Command(ability="Q", ability_alt=True, cursor_depth=0))
        _wait(lambda: any(e.data.get("defusing") for e in match.effects), session)
        wingman = next(e for e in match.effects if e.data.get("defusing"))
        wingman.data["progress"] = checkpoint or 3.0
        match.spike_half_defused = bool(checkpoint)
        client.send(Command(use_spike=True))
        _wait(lambda: guest.pid in session.net.pending)
        session.step(1 / 64)
        assert not guest.defusing

        tick_effects = match._tick_effects

        def destroy_during_tick(dt: float) -> None:
            remove_device(match, wingman, "destroy")
            tick_effects(dt)

        with monkeypatch.context() as patch:
            patch.setattr(match, "_tick_effects", destroy_during_tick)
            events = session.step(1 / 64)
        assert guest.defusing and guest.defuse_progress == checkpoint
        assert any(e.kind == "defuse_start" and e.data["resumed"] == bool(checkpoint) for e in events)
        session.step(1 / 64)
        assert guest.defuse_progress == checkpoint + 1 / 64
    finally:
        client.close()


@pytest.mark.parametrize("with_door,with_gun,aim_at_switch", [
    (True, False, True), (False, True, False), (True, True, False), (True, True, True),
])
def test_guest_interact_selects_aimed_door_or_ground_weapon(
    session: HostSession, with_door: bool, with_gun: bool, aim_at_switch: bool,
) -> None:
    from gameplay.geometry import Rect, Vec
    from gameplay.match import Drop
    from gameplay.world import Wall

    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        match = session.match
        guest = match.players[client.pid]
        guest.pos = Vec(24, 35)
        switch = Vec(24, 36)
        door = Wall(Rect(23.5, 36.5, 24.5, 36.6), 3, door=True, switch=switch)
        if with_door:
            match.world.walls.append(door)
        guest.weapons["primary"] = match._new_weapon("phantom")
        if with_gun:
            match.drops.append(Drop("vandal", 7, 30, Vec(25, 35)))
        match.phase_until = match.time
        session.step(1 / 64, {host.pid: Command()})
        client.send(Command(interact=True, facing=0 if aim_at_switch else 90, cursor_depth=1))
        _wait(lambda: guest.prev_interact, session)
        assert (door.rect in match.open_doors) == aim_at_switch
        assert guest.weapons["primary"].key == ("phantom" if aim_at_switch else "vandal")
        assert any(d.key == "vandal" for d in match.drops) == (with_gun and aim_at_switch)
    finally:
        client.close()


@pytest.mark.parametrize("obstacle", ["none", "smoke", "wall", "transparent-barrier"])
def test_guest_selects_reachable_weapon_at_equal_distance(session: HostSession, obstacle: str) -> None:
    from gameplay.geometry import Rect, Vec
    from gameplay.match import Drop, Effect
    from gameplay.world import Wall

    session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        match = session.match
        guest = match.players[client.pid]
        guest.pos = Vec(24, 35)
        guest.weapons["primary"] = match._new_weapon("bulldog")
        match.drops.extend([Drop("phantom", 10, 20, Vec(24, 36)), Drop("vandal", 7, 30, Vec(25, 35))])
        rect = Rect(24.6, 34.8, 24.7, 35.2)
        if obstacle == "wall":
            match.world.walls.append(Wall(rect, 3))
        elif obstacle == "transparent-barrier":
            match.effects.append(Effect("wall", guest.pid, guest.team, rect.center, match.time + 10,
                                        props={"barrier": Wall(rect, 3, blocks_sight=False)}))
        elif obstacle == "smoke":
            match.effects.append(Effect("smoke", guest.pid, guest.team, rect.center, match.time + 10, radius=0.3))
        match.phase_until = match.time
        session.step(1 / 64)
        client.send(Command(interact=True, facing=90, cursor_depth=1))
        _wait(lambda: guest.prev_interact, session)
        assert guest.weapons["primary"].key == ("phantom" if obstacle in ("wall", "transparent-barrier") else "vandal")
    finally:
        client.close()


def test_guest_receives_drop_height_and_can_pick_up_after_climbing_ramp(session: HostSession) -> None:
    from gameplay.geometry import Rect, Vec
    from gameplay.world import Deck, WorldMap

    world = WorldMap("height", "Height test", 30, 20,
                     spawns={0: [Vec(12, 5)], 1: [Vec(6, 5)]},
                     decks=[Deck(Rect(10, 2, 16, 8), 2, 0)],
                     ramps=[Rect(6, 4, 10.2, 6)], ramp_spans={0: ("x", False, 0, 2)})
    session.match.world = world
    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        match = session.match
        guest = match.players[client.pid]
        host.weapons["primary"] = match._new_weapon("vandal")
        host.slot = "primary"
        guest.weapons["primary"] = match._new_weapon("phantom")
        match.phase_until = match.time
        session.step(1 / 64, {host.pid: Command(drop=True, facing=270)})
        dropped = match.drops[0]
        assert dropped.ground == 2
        shadow = Match(world)

        def receive() -> bool:
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], client.pid)
            return any(d.key == "vandal" and d.ground == 2 and d.pos == dropped.pos for d in shadow.drops)

        _wait(receive, session)
        guest.pos, guest.ground, guest.level = dropped.pos, 0.0, 0
        client.send(Command(interact=True))
        _wait(lambda: guest.prev_interact, session)
        assert dropped in match.drops and guest.weapons["primary"].key == "phantom"
        guest.pos = Vec(6, 5)
        client.send(Command(move_y=1, facing=90))
        _wait(lambda: guest.ground > 0.5, session)
        _wait(lambda: guest.ground >= 1.85 and not guest.prev_interact, session)
        client.send(Command(interact=True))
        _wait(lambda: guest.weapons["primary"].key == "vandal", session)
        assert dropped not in match.drops
        guest.team = host.team
        host.pos, host.ground, host.level = Vec(15.5, 5), 2, 2
        guest.pos, guest.ground, guest.level = Vec(15.5, 5.5), 2, 2
        match.spike_carrier, match.spike_pos = host.pid, None
        session.step(1 / 64, {host.pid: Command(slot="spike", drop=True, facing=90)})
        assert match.spike_carrier is None and match.spike_ground == 0
        guest.pos, guest.ground, guest.level = Vec(16.6, 5.5), 0, 0
        _wait(lambda: match.spike_carrier == guest.pid, session)

        guest.team = 1 - host.team
        host.pos, host.ground, host.level = Vec(10.1, 5), 2, 2
        match._plant(host, "A")
        guest.pos, guest.ground, guest.level = Vec(10.1, 5), 0, 0
        client.send(Command(use_spike=True))
        _wait(lambda: guest.pid in session.net.pending)
        session.step(1 / 64)
        assert not guest.defusing
        guest.pos = Vec(9.4, 5)
        guest.ground = world.ground_height(guest.pos)
        guest.level = world.floor_level(guest.pos)
        _wait(lambda: guest.defusing, session)
        assert guest.defuse_progress > 0
    finally:
        client.close()


def test_host_and_guest_can_confirm_same_weapon_request_in_one_tick(session: HostSession) -> None:
    host = session.match.add_player("Host", 0, "omen")
    recipient = session.match.add_player("Recipient", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(0)
        _wait(lambda: session.match.players[client.pid].team == 0, session)
        session.start(team_size=3)
        guest = session.match.players[client.pid]
        host.credits = guest.credits = 5000
        session.step(1 / 64, {recipient.pid: Command(request="vandal")})
        action = recipient.gift_action()
        client.send(Command(buy=[action]))
        _wait(lambda: guest.pid in session.net.pending)
        session.step(1 / 64, {host.pid: Command(buy=[action])})
        assert sorted((host.credits, guest.credits)) == [2100, 5000]
        assert recipient.weapon.key == "vandal" and len(recipient.purchases) == 1
        session.step(1 / 64, {recipient.pid: Command(buy=["sell:vandal"])})
        assert host.credits == guest.credits == 5000
    finally:
        client.close()


def test_team_purchase_obeys_same_buy_zone_as_self_purchase(session: HostSession) -> None:
    from gameplay.geometry import Vec

    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(0)
        _wait(lambda: session.match.players[client.pid].team == 0, session)
        session.match.world.lock_spawn_during_buy = True
        session.start(team_size=2)
        match = session.match
        guest = match.players[client.pid]
        guest.credits = 5000
        session.step(1 / 64, {host.pid: Command(request="vandal")})
        zone = match.buy_spawn_zone(guest)
        assert zone is not None
        shadow = Match(match.world)
        for pos in (Vec(zone.x1 + 0.01, zone.center.y), Vec(zone.x1 - 0.01, zone.center.y)):
            guest.pos = pos
            expected = None if zone.contains(pos) else "zone"
            assert match.purchase_block_reason(guest) == expected
            apply_snapshot(shadow, match.snapshot(guest.pid), guest.pid)
            assert shadow.purchase_block_reason(shadow.players[guest.pid]) == expected
            client.send(Command(buy=["buy:ghost", host.gift_action()]))
            _wait(lambda: guest.pid in session.net.pending)
            session.step(0)
            if not zone.contains(pos):
                assert guest.credits == 5000 and host.request == "vandal" and "primary" not in host.weapons
                assert guest.weapons["sidearm"].key == "classic"
        assert guest.credits == 1600 and guest.weapons["sidearm"].key == "ghost"
        assert host.request == "" and host.weapons["primary"].key == "vandal"
        for pos, allowed in ((Vec(zone.x1 + 0.01, zone.center.y), False),
                             (Vec(zone.x1 - 0.01, zone.center.y), True)):
            guest.pos = pos
            apply_snapshot(shadow, match.snapshot(guest.pid), guest.pid)
            assert ("ghost" in shadow.players[guest.pid].remote_sellable) == allowed
            assert match.sellable(guest, "ghost") == allowed
            client.send(Command(buy=["sell:ghost"]))
            _wait(lambda: guest.pid in session.net.pending)
            session.step(0)
            assert guest.credits == (2100 if allowed else 1600)
    finally:
        client.close()


def test_weapon_request_disappears_for_guest_when_teammate_dies(session: HostSession) -> None:
    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(0)
        _wait(lambda: session.match.players[client.pid].team == 0, session)
        session.start(team_size=2)
        match = session.match
        buyer = match.players[client.pid]
        buyer.credits = 5000
        session.step(1 / 64, {host.pid: Command(request="vandal")})
        shadow = Match(match.world)

        def sees_request(request: str) -> bool:
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], client.pid)
            return host.pid in shadow.players and shadow.players[host.pid].request == request

        _wait(lambda: sees_request("vandal"), session)
        action = shadow.players[host.pid].gift_action()
        match._kill(None, host, "test", "body")
        assert host.request == ""
        client.send(Command(buy=[action], request="phantom"))
        _wait(lambda: buyer.request == "phantom", session)
        _wait(lambda: sees_request(""), session)
        assert not shadow.players[host.pid].alive and buyer.credits == 5000
    finally:
        client.close()


def test_disconnected_player_becomes_bot(session: HostSession) -> None:
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    _wait(lambda: client.pid in session.match.players, session)
    session.start(team_size=1)
    client.close()
    _wait(lambda: session.match.players[client.pid].is_bot, session)
    assert session.match.players[client.pid].name.endswith("(Bot)")


@pytest.mark.parametrize("rejoin", ["never", "before_revive", "during_recovery"])
def test_sage_resurrection_survives_target_disconnect(session: HostSession, rejoin: str) -> None:
    from gameplay.geometry import Vec

    sage = session.match.add_player("Host", 0, "sage")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        match = session.match
        _wait(lambda: client.pid in match.players, session)
        client.choose_team(0)
        _wait(lambda: match.players[client.pid].team == 0, session)
        session.start(team_size=2)
        target = match.players[client.pid]
        target.weapons["primary"] = match._new_weapon("vandal")
        target.weapons["primary"].mag -= 1
        target.slot = "primary"
        match.phase_until = match.time
        session.step(1 / 64)
        sage.pos, target.pos = Vec(24, 5), Vec(24, 6.5)
        match._kill(None, target, "vandal", "body")
        sage.ult_points = match.ultimate_cost(sage)
        session.step(1 / 64, {sage.pid: Command(ability="X", facing=0, cursor_depth=1.5)})
        marker, = [e for e in match.effects if e.props.get("revive_pid") == target.pid]
    finally:
        client.close()

    _wait(lambda: match.players[target.pid].is_bot, session)
    assert match.players[target.pid] is target and not target.alive
    back = None
    try:
        if rejoin == "before_revive":
            back = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen", token=client.token)
            assert back.rejoined and back.pid == target.pid
            assert match.players[back.pid] is target and not target.is_bot and not target.alive
            assert marker in match.effects and match.time < marker.until

        _wait(lambda: target.alive, session)
        assert target.weapons["primary"].key == "vandal" and not match.drops
        assert sum(e.kind == "revive" and e.data["pid"] == target.pid for e in match.events) == 1
        session.step(1 / 64)
        assert marker not in match.effects

        if rejoin == "during_recovery":
            back = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen", token=client.token)
            assert back.rejoined and back.pid == target.pid
            assert match.players[back.pid] is target and not target.is_bot
            assert match.time < target.channel_until

        if back is not None:
            shadow = Match(match.world)

            def guest_sees_restored_inventory() -> bool:
                for message in back.take():
                    if message["type"] == "state":
                        apply_snapshot(shadow, message["snap"], back.pid)
                player = shadow.players.get(back.pid)
                return player is not None and player.alive and "primary" in player.weapons

            _wait(guest_sees_restored_inventory, session)
            assert shadow.players[back.pid].weapons["primary"].key == "vandal"
            if rejoin == "during_recovery":
                assert shadow.players[back.pid].channel_until == pytest.approx(target.channel_until)
                pos, mag = target.pos, target.weapon.mag
                sage.pos = Vec(24, 3)
                assert match.side(target.team) == "attack"
                match.spike_carrier, match.spike_pos = None, pos
                match.spike_ground = match.world.ground_height(pos, target.level)
                slot = target.slot
                assert slot == "primary" and mag == match.weapons["vandal"].mag - 1
                switch_weapon = Command(slot="melee", equipment_actions=["melee"])
                reload_weapon = Command(reload=True)
                drop_weapon = Command(drop=True, equipment_actions=["drop"])
                back.send(drop_weapon)
                _wait(lambda: target.pid in session.net.pending)
                session.step(1 / 64)
                assert match.time < target.channel_until
                assert target.weapon.key == "vandal" and not match.drops
                back.send(reload_weapon)
                _wait(lambda: target.pid in session.net.pending)
                session.step(1 / 64)
                assert match.time < target.channel_until and target.reload_until == 0
                back.send(switch_weapon)
                _wait(lambda: target.pid in session.net.pending)
                session.step(1 / 64)
                assert match.time < target.channel_until and target.slot == slot
                smoke = Command(ability="E", points=[(24, 10)])
                charges = target.charges["E"]
                back.send(Command(move_y=1, facing=180, fire=True, ability=smoke.ability, points=smoke.points))
                _wait(lambda: target.pid in session.net.pending)
                session.step(1 / 64)
                assert match.time < target.channel_until
                assert target.pos == pos and target.weapon.mag == mag
                assert target.charges["E"] == charges
                from gameplay.match import INTERACT_RANGE, PICKUP_RANGE

                manual_spike_pos = pos + Vec((PICKUP_RANGE + INTERACT_RANGE) / 2, 0)
                match.spike_pos = manual_spike_pos
                match.orbs = [pos]
                ult_points = target.ult_points
                ground_weapon = match._ground_weapon(target, match._new_weapon("phantom"), pos)
                match.drops.append(ground_weapon)
                back.send(Command(interact=True, fire=True, alt_fire=True, facing=180))
                _wait(lambda: target.pid in session.net.pending)
                while match.time + 1 / 64 < target.channel_until:
                    session.step(1 / 64)
                    assert match.spike_carrier is None and match.spike_pos == manual_spike_pos
                session.step(1 / 64)
                assert match.spike_carrier is None and match.spike_pos == manual_spike_pos
                assert target.weapon.key == "vandal" and ground_weapon in match.drops
                for _ in range(64):
                    session.step(1 / 64)
                assert target.weapon.mag == mag
                assert target.zoom_level == 0 and not target.zoomed
                assert match.orbs == [pos] and target.orb_progress == 0 and target.ult_points == ult_points
                back.send(Command())
                _wait(lambda: target.pid in session.net.pending)
                session.step(1 / 64)
                assert match.spike_carrier is None
                match.drops.remove(ground_weapon)
                back.send(Command(interact=True))
                _wait(lambda: target.pid in session.net.pending)
                session.step(1 / 64)
                assert match.spike_carrier == target.pid and match.spike_pos is None
                assert target.orb_progress > 0
                _wait(lambda: pos not in match.orbs, session)
                assert target.ult_points == ult_points + 1
                assert target.slot == slot
                assert target.reload_until == 0 and target.weapon.mag == mag
                assert target.weapon.key == "vandal" and not match.drops
                back.send(Command(move_y=1, facing=180, fire=True, alt_fire=True))
                _wait(lambda: target.pid in session.net.pending)
                session.step(1 / 64)
                assert target.pos != pos and target.weapon.mag == mag - 1
                assert target.zoom_level == 1 and target.zoomed
                assert target.charges["E"] == charges
                back.send(reload_weapon)
                _wait(lambda: target.pid in session.net.pending)
                session.step(1 / 64)
                assert target.reload_until > match.time
                _wait(lambda: target.reload_until == 0, session)
                assert target.weapon.mag == match.weapons["vandal"].mag
                back.send(smoke)
                _wait(lambda: target.pid in session.net.pending)
                session.step(1 / 64)
                assert target.charges["E"] == charges - 1
                assert any(e.kind == "smoke" and e.owner == target.pid for e in match.effects)
                back.send(switch_weapon)
                _wait(lambda: target.pid in session.net.pending)
                session.step(1 / 64)
                assert target.slot == "melee"
                back.send(Command(slot="primary", drop=True, equipment_actions=["primary", "drop"]))
                _wait(lambda: target.pid in session.net.pending)
                session.step(1 / 64)
                assert "primary" not in target.weapons
                dropped, = match.drops
                assert dropped.key == "vandal" and dropped.mag == match.weapons["vandal"].mag
                back.send(Command(interact=True))
                _wait(lambda: target.pid in session.net.pending)
                session.step(1 / 64)
                assert target.weapons["primary"].key == "vandal"
    finally:
        if back is not None:
            back.close()


@pytest.mark.parametrize(("input_name", "planting"), [
    ("interact", False), ("use_spike", False),
    ("interact", True), ("use_spike", True), ("fire", True),
])
def test_guest_spike_use_requires_new_input_after_sage_recovery(
    session: HostSession, input_name: str, planting: bool,
) -> None:
    from gameplay.geometry import Vec

    team = 0 if planting else 1
    sage = session.match.add_player("Host", team, "sage")
    with_guest = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        match = session.match
        _wait(lambda: with_guest.pid in match.players, session)
        with_guest.choose_team(team)
        _wait(lambda: match.players[with_guest.pid].team == team, session)
        session.start(team_size=2)
        target = match.players[with_guest.pid]
        for player in match.players.values():
            player.is_bot = False
        match.phase_until = match.time
        session.step(1 / 64)
        sage.pos, target.pos = Vec(24, 5), Vec(24, 6.5)
        for player in (sage, target):
            player.level, player.ground = 0, 0.0
        match._kill(None, target, "vandal", "body")
        if not planting:
            planter = next(p for p in match.players.values() if p.team != target.team)
            match._plant(planter, "A", point=target.pos, level=target.level)
        sage.ult_points = match.ultimate_cost(sage)
        session.step(1 / 64, {sage.pid: Command(ability="X", facing=0, cursor_depth=1.5)})
        assert any(e.props.get("revive_pid") == target.pid for e in match.effects)
        phase = "live" if planting else "planted"
        _wait(lambda: target.alive or match.phase != phase, session)
        assert target.alive and match.phase == phase, match.round_reason
        if planting:
            target.pos = match.world.sites[0].rect.center
            target.ground = match.world.ground_height(target.pos)
            target.level = match.world.floor_level(target.pos)
            match.spike_carrier, match.spike_pos = target.pid, None

        spike_use = Command(**{input_name: True})
        with_guest.send(spike_use)
        _wait(lambda: target.pid in session.net.pending)
        session.step(1 / 64)
        assert match.time < target.channel_until
        assert target.plant_progress == target.defuse_progress == 0
        _wait(lambda: match.time > target.channel_until, session)
        if input_name == "fire":
            site_pos = target.pos
            target.pos = Vec(24, 6.5)
            assert match.world.site_at(target.pos, target.level) is None
            with_guest.send(Command(slot="spike", fire=True))
            _wait(lambda: target.pid in session.net.pending)
            session.step(1 / 64)
            assert target.spike_equipped
            target.pos = site_pos
        session.step(1 / 64)
        assert target.plant_progress == target.defuse_progress == 0

        with_guest.send(Command())
        _wait(lambda: target.pid in session.net.pending)
        session.step(1 / 64)
        with_guest.send(spike_use)
        _wait(lambda: target.pid in session.net.pending)
        session.step(1 / 64)
        assert (target.plant_progress if planting else target.defuse_progress) > 0
    finally:
        with_guest.close()


@pytest.mark.parametrize(("enemy_has_sight", "lethal", "last_defender", "halftime_result"), [
    (False, False, False, None), (True, False, False, None), (True, True, False, None),
    (True, True, True, None), (True, True, True, "defuse"), (True, True, True, "detonation"),
])
def test_guest_classic_alt_fire_and_jump_require_new_input_after_sage_recovery(
    session: HostSession, enemy_has_sight: bool, lethal: bool, last_defender: bool, halftime_result: str | None,
) -> None:
    from gameplay.geometry import Vec
    from gameplay.net import events_from_json
    halftime = halftime_result is not None

    match = session.match
    sage = match.add_player("Host", 0, "sage")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    teammate = None
    enemy_client = None
    try:
        _wait(lambda: client.pid in match.players, session)
        client.choose_team(0)
        _wait(lambda: match.players[client.pid].team == 0, session)
        teammate = NetClient(f"127.0.0.1:{session.net.port}", "Teammate", "omen")
        _wait(lambda: teammate.pid in match.players, session)
        teammate.choose_team(0)
        _wait(lambda: match.players[teammate.pid].team == 0, session)
        enemy_client = NetClient(f"127.0.0.1:{session.net.port}", "Opponent", "omen")
        _wait(lambda: enemy_client.pid in match.players, session)
        enemy_client.choose_team(1)
        _wait(lambda: match.players[enemy_client.pid].team == 1, session)
        assert session.start(team_size=3)
        target = match.players[client.pid]
        enemy = match.players[enemy_client.pid]
        for player in match.players.values():
            player.is_bot = False
        match.phase_until = match.time
        session.step(1 / 64)
        sage.pos, target.pos = Vec(24, 5), Vec(24, 6.5)
        match._kill(None, target, "vandal", "body")
        target.crouching = True
        spectator = match.players[teammate.pid]
        match._kill(None, spectator, "vandal", "body")
        sage.ult_points = match.ultimate_cost(sage)
        session.step(1 / 64, {sage.pid: Command(ability="X", facing=0, cursor_depth=1.5)})
        _wait(lambda: target.alive, session)
        assert target.weapon.key == "classic"
        assert not target.crouching
        magazine = target.weapon.mag

        fire_and_jump = Command(alt_fire=True, jump=True, facing=90)
        target.facing = 0
        client.send(Command(alt_fire=True, jump=True, crouch=True, facing=90))
        _wait(lambda: target.pid in session.net.pending)
        session.step(1 / 64)
        assert match.time < target.channel_until
        assert target.facing == 90
        assert target.z == target.vz == 0 and target.weapon.mag == magazine
        shadow = Match(match.world)

        landing_times = []
        jump_events = []
        shot_events = []

        def update_teammate_view() -> None:
            for message in teammate.take():
                if message["type"] == "state":
                    previous = shadow.players.get(target.pid)
                    was_airborne = previous is not None and previous.z > 0
                    apply_snapshot(shadow, message["snap"], teammate.pid)
                    if was_airborne and shadow.players[target.pid].z == 0:
                        landing_times.append(shadow.time)
                elif message["type"] == "events":
                    for event in events_from_json(message["events"]):
                        if event.data.get("pid") == target.pid:
                            if event.kind == "jump":
                                jump_events.append(event)
                            elif event.kind == "shot":
                                shot_events.append(event)

        def teammate_sees_new_facing() -> bool:
            update_teammate_view()
            ally = shadow.players.get(target.pid)
            return ally is not None and ally.alive and ally.facing == 90

        _wait(teammate_sees_new_facing, session)
        assert match.time < target.channel_until
        assert not shadow.players[teammate.pid].alive
        assert shadow.time < shadow.players[target.pid].channel_until
        assert shadow.players[target.pid].channel_until == pytest.approx(target.channel_until)
        while match.time <= target.channel_until:
            session.step(1 / 64)
            assert target.weapon.mag == magazine
            assert target.z == target.vz == 0
            if match.time < target.channel_until:
                assert not target.crouching
        session.step(1 / 64)
        assert target.weapon.mag == magazine
        assert target.z == target.vz == 0
        assert target.crouching

        client.send(Command())
        _wait(lambda: target.pid in session.net.pending)
        session.step(1 / 64)
        client.send(fire_and_jump)
        _wait(lambda: target.pid in session.net.pending)
        enemy.pos = target.pos + (Vec(1.5, 0) if enemy_has_sight else Vec(0, -2.5))
        enemy.level, enemy.ground = target.level, target.ground
        enemy.facing = 270 if enemy_has_sight else 0
        if not enemy_has_sight:
            enemy.blind_until = match.time + 5
        assert match.can_see(enemy, target) == enemy_has_sight
        if lethal:
            enemy.hp = 1
        if last_defender:
            for defender in match.players.values():
                if defender.team == enemy.team and defender is not enemy:
                    match._kill(None, defender, "classic", "body")
        if halftime:
            match.round_no = int(match._r["half_after"])
            match.score[:] = [7, match.round_no - 8]
            enemy.credits = 3000
            enemy.weapons["primary"] = match._new_weapon("vandal")
            enemy.weapons["sidearm"] = match._new_weapon("ghost")
        score_before = match.score.copy()
        enemy_hp = enemy.hp
        kills_before, deaths_before = target.kills, enemy.deaths
        events = session.step(1 / 64)
        assert target.weapon.mag == magazine - 1
        jump, = [e for e in events if e.kind == "jump" and e.data["pid"] == target.pid]
        assert target.z > 0

        def teammate_sees_jump() -> bool:
            update_teammate_view()
            return shadow.players[target.pid].z > 0

        _wait(teammate_sees_jump, session)
        assert shadow.players[target.pid].alive and not shadow.players[teammate.pid].alive
        assert shadow.time >= shadow.players[target.pid].channel_until
        airborne_at = shadow.time
        client.send(Command())
        _wait(lambda: target.pid in session.net.pending)

        def teammate_sees_landing() -> bool:
            update_teammate_view()
            return shadow.time > airborne_at and shadow.players[target.pid].z == 0

        _wait(teammate_sees_landing, session)
        landed_at = shadow.time

        def teammate_has_later_snapshot() -> bool:
            update_teammate_view()
            return shadow.time > landed_at

        _wait(teammate_has_later_snapshot, session)
        assert landing_times == [landed_at]
        received_jump, = jump_events
        assert received_jump.t == pytest.approx(jump.t)
        shots = [e for e in events if e.kind == "shot" and e.data["pid"] == target.pid]
        assert len(shots) == len(shot_events) == 3  # One Classic volley, one event per pellet.
        for received, original in zip(shot_events, shots):
            assert received.t == pytest.approx(original.t)
            assert received.data["weapon"] == original.data["weapon"] == "classic"
            assert received.data["to"] == pytest.approx(original.data["to"])
        enemy_shadow = Match(match.world)
        enemy_shots = []
        enemy_hits = []
        enemy_kills = []
        enemy_round_ends = []

        def update_enemy_view() -> None:
            for message in enemy_client.take():
                if message["type"] == "state":
                    apply_snapshot(enemy_shadow, message["snap"], enemy_client.pid)
                elif message["type"] == "events":
                    for event in events_from_json(message["events"]):
                        if event.kind == "shot" and event.data.get("pid") == target.pid:
                            enemy_shots.append(event)
                        elif event.kind == "hit" and event.data.get("by") == target.pid and event.data.get("pid") == enemy.pid:
                            enemy_hits.append(event)
                        elif event.kind == "kill" and event.data.get("by") == target.pid and event.data.get("pid") == enemy.pid:
                            enemy_kills.append(event)
                        elif event.kind == "round_end":
                            enemy_round_ends.append(event)

        def enemy_has_later_snapshot() -> bool:
            update_enemy_view()
            return enemy_shadow.time > landed_at

        _wait(enemy_has_later_snapshot, session)
        # The host filters tracer and hit events at broadcast time, when a lethal victim has lost sight.
        assert len(enemy_shots) == (3 if enemy_has_sight and not lethal else 0)
        hits = [e for e in events if e.kind == "hit" and e.data.get("by") == target.pid and e.data["pid"] == enemy.pid]
        assert len(hits) == (1 if lethal else 3 if enemy_has_sight else 0)
        assert len(enemy_hits) == (0 if lethal else len(hits))
        for received, original in zip(enemy_hits, hits):
            assert received.t == pytest.approx(original.t)
            assert received.data == original.data
        assert enemy_shadow.players[enemy.pid].hp == enemy.hp == max(0, enemy_hp - sum(e.data["dmg"] for e in hits))
        kills = [e for e in events if e.kind == "kill" and e.data.get("by") == target.pid and e.data["pid"] == enemy.pid]
        assert len(kills) == len(enemy_kills) == int(lethal)
        round_ends = [e for e in events if e.kind == "round_end"]
        assert len(round_ends) == len(enemy_round_ends) == int(last_defender)
        if last_defender:
            assert enemy_round_ends[0].data == round_ends[0].data
            assert enemy_round_ends[0].t == pytest.approx(round_ends[0].t)
            assert enemy_shadow.phase == match.phase == "end"
            assert enemy_shadow.round_winner == match.round_winner == target.team
            assert enemy_shadow.round_reason == match.round_reason == "Defenders eliminated"
            score_before[target.team] += 1
        assert enemy_shadow.score == match.score == score_before
        if lethal:
            assert enemy_kills[0].t == pytest.approx(kills[0].t)
            assert enemy_kills[0].data == kills[0].data
            assert not enemy.alive and not enemy_shadow.players[enemy.pid].alive
            assert target.kills == kills_before + 1 and enemy.deaths == deaths_before + 1
        for received, original in zip(enemy_shots, shots):
            assert received.t == pytest.approx(original.t)
            assert received.data["weapon"] == original.data["weapon"] == "classic"
            assert received.data["to"] == pytest.approx(original.data["to"])
        assert target.z == target.vz == 0
        assert shadow.players[target.pid].alive and not shadow.players[teammate.pid].alive
        assert target.weapon.mag == magazine - 1
        if last_defender:
            next_round = match.round_no + 1
            next_attacking_team = enemy.team if halftime else target.team
            match.phase_until = match.time
            session.step(1 / 64)

            def enemy_sees_next_buy_phase() -> bool:
                update_enemy_view()
                return enemy_shadow.round_no == next_round and enemy_shadow.phase == "buy"

            _wait(enemy_sees_next_buy_phase, session)
            assert match.round_no == next_round and match.phase == "buy"
            assert enemy_shadow.score == match.score == score_before
            assert enemy_shadow.attacking_team == match.attacking_team == next_attacking_team
            assert enemy_shadow.players[enemy.pid].alive and enemy.alive
            assert len(enemy_round_ends) == 1
            if halftime:
                guest_state = enemy_shadow.players[enemy.pid]
                assert enemy.credits == guest_state.credits == match._eco["start"]
                expected_weapons = {"sidearm": "classic", "melee": "tactical_knife"}
                for player in (enemy, guest_state):
                    assert {slot: weapon.key for slot, weapon in player.weapons.items()} == expected_weapons
                    assert player.slot == "sidearm" and player.armor == player.armor_reserve == 0

                spike_pos = match.spike_pos
                assert spike_pos is not None and enemy_shadow.spike_pos == spike_pos
                assert enemy_shadow.spike_carrier is match.spike_carrier is None
                enemy.pos = spike_pos

                def enemy_sees_spike_pickup() -> bool:
                    update_enemy_view()
                    return enemy_shadow.spike_carrier == enemy.pid

                _wait(enemy_sees_spike_pickup, session)
                assert match.phase == enemy_shadow.phase == "buy"
                assert match.spike_carrier == enemy.pid
                assert match.spike_pos is enemy_shadow.spike_pos is None

                match.phase_until = match.time
                session.step(1 / 64)

                def enemy_sees_live_round() -> bool:
                    update_enemy_view()
                    return enemy_shadow.round_no == next_round and enemy_shadow.phase == "live"

                _wait(enemy_sees_live_round, session)
                assert match.round_no == next_round and match.phase == "live"
                assert match.spike_carrier == enemy_shadow.spike_carrier == enemy.pid
                assert match.spike_pos is enemy_shadow.spike_pos is None

                site = match.world.sites[0]
                enemy.pos = site.rect.center
                enemy.level = match.world.floor_level(enemy.pos)
                enemy.ground = match.world.ground_height(enemy.pos)
                enemy_client.send(Command(use_spike=True))
                _wait(lambda: enemy.pid in session.net.pending)

                def enemy_sees_planted_spike() -> bool:
                    update_enemy_view()
                    return enemy_shadow.round_no == next_round and enemy_shadow.phase == "planted"

                _wait(enemy_sees_planted_spike, session)
                assert match.phase == "planted"
                assert match.spike_site == enemy_shadow.spike_site == site.name
                assert match.spike_pos == enemy_shadow.spike_pos == enemy.pos
                assert match.spike_carrier is enemy_shadow.spike_carrier is None
                assert enemy_shadow._spike_detonation_at() == pytest.approx(match._spike_detonation_at())

                if halftime_result == "defuse":
                    target.pos = match.spike_pos
                    target.level, target.ground = enemy.level, enemy.ground
                    client.send(Command(use_spike=True))
                    _wait(lambda: target.pid in session.net.pending)
                    _wait(lambda: target.defusing, session)
                    target.defuse_progress = float(match._spike["defuse_time"]) - 1 / 64
                    events = session.step(1 / 64)
                    defuse, = [event for event in events if event.kind == "defuse"]
                    assert defuse.data["pid"] == target.pid
                    winner, reason = target.team, "Bomb defused"
                else:
                    match.spike_planted_at = match.time + 1 / 64 - float(match._spike["fuse_time"])
                    events = session.step(1 / 64)
                    explosion, = [event for event in events if event.kind == "explode"]
                    assert Vec(*explosion.data["pos"]) == match.spike_pos
                    winner, reason = enemy.team, "Bomb detonated"
                round_end, = [event for event in events if event.kind == "round_end"]

                def enemy_sees_round_result() -> bool:
                    update_enemy_view()
                    return (enemy_shadow.round_no == next_round and enemy_shadow.phase == "end"
                            and len(enemy_round_ends) >= 2)

                _wait(enemy_sees_round_result, session)
                assert len(enemy_round_ends) == 2 and enemy_round_ends[-1].data == round_end.data
                assert match.round_winner == enemy_shadow.round_winner == winner
                assert match.round_reason == enemy_shadow.round_reason == reason
                score_before[winner] += 1
                assert match.score == enemy_shadow.score == score_before
                if halftime_result == "detonation":
                    token = enemy_client.token
                    enemy_client.close()
                    _wait(lambda: enemy.is_bot, session)
                    enemy_client = NetClient(f"127.0.0.1:{session.net.port}", "Opponent", "omen", token=token)
                    assert enemy_client.rejoined and enemy_client.pid == enemy.pid
                    assert match.players[enemy.pid] is enemy and not enemy.is_bot
                    enemy_shadow = Match(match.world)

                    def rejoined_guest_sees_round_result() -> bool:
                        update_enemy_view()
                        return enemy_shadow.round_no == next_round and enemy_shadow.phase == "end"

                    _wait(rejoined_guest_sees_round_result, session)
                    assert enemy_shadow.round_winner == winner and enemy_shadow.round_reason == reason
                    assert enemy_shadow.score == score_before

                    token = enemy_client.token
                    enemy_client.close()
                    _wait(lambda: enemy.is_bot, session)
                    match.phase_until = match.time
                    session.step(1 / 64)
                    assert match.round_no == next_round + 1 and match.phase == "buy"

                    enemy_client = NetClient(f"127.0.0.1:{session.net.port}", "Opponent", "omen", token=token)
                    assert enemy_client.rejoined and enemy_client.pid == enemy.pid
                    enemy_shadow = Match(match.world)

                    def rejoined_guest_sees_buy_phase() -> bool:
                        update_enemy_view()
                        return enemy_shadow.round_no == next_round + 1 and enemy_shadow.phase == "buy"

                    _wait(rejoined_guest_sees_buy_phase, session)
                    assert enemy_shadow.score == match.score == score_before
                    assert enemy_shadow.attacking_team == match.attacking_team == enemy.team
                    assert enemy_shadow.players[enemy.pid].alive and enemy.alive and not enemy.is_bot
                    credits_before_purchase = enemy.credits
                    assert enemy_shadow.players[enemy.pid].credits == credits_before_purchase
                    assert enemy.weapons["sidearm"].key == "classic"
                    original_sidearm = enemy.weapons["sidearm"]
                    enemy_client.send(Command(buy=["buy:ghost"]))
                    _wait(lambda: enemy.pid in session.net.pending)

                    def rejoined_guest_sees_purchase() -> bool:
                        update_enemy_view()
                        return enemy_shadow.players[enemy.pid].weapons["sidearm"].key == "ghost"

                    _wait(rejoined_guest_sees_purchase, session)
                    purchased_state = enemy_shadow.players[enemy.pid]
                    assert enemy.weapons["sidearm"] == purchased_state.weapons["sidearm"]
                    assert enemy.credits == purchased_state.credits == credits_before_purchase - match.weapons["ghost"].price
                    assert match.phase == enemy_shadow.phase == "buy"

                    token = enemy_client.token
                    enemy_client.close()
                    _wait(lambda: enemy.is_bot, session)
                    enemy_client = NetClient(f"127.0.0.1:{session.net.port}", "Opponent", "omen", token=token)
                    assert enemy_client.rejoined and enemy_client.pid == enemy.pid
                    assert match.players[enemy.pid] is enemy and not enemy.is_bot
                    enemy_shadow = Match(match.world)
                    _wait(rejoined_guest_sees_buy_phase, session)
                    guest_after_rejoin = enemy_shadow.players[enemy.pid]
                    assert guest_after_rejoin.weapons["sidearm"] == purchased_state.weapons["sidearm"]
                    assert guest_after_rejoin.credits == purchased_state.credits
                    assert "ghost" in guest_after_rejoin.remote_sellable

                    enemy_client.send(Command(buy=["sell:ghost"]))
                    _wait(lambda: enemy.pid in session.net.pending)

                    def rejoined_guest_sees_refund() -> bool:
                        update_enemy_view()
                        player = enemy_shadow.players[enemy.pid]
                        return player.weapons["sidearm"].key == "classic" and player.credits == credits_before_purchase

                    _wait(rejoined_guest_sees_refund, session)
                    refunded_state = enemy_shadow.players[enemy.pid]
                    assert enemy.weapons["sidearm"] == refunded_state.weapons["sidearm"] == original_sidearm
                    assert enemy.credits == refunded_state.credits == credits_before_purchase
                    assert match.phase == enemy_shadow.phase == "buy"

                    enemy_client.send(Command(buy=["buy:ghost"]))
                    _wait(lambda: enemy.pid in session.net.pending)
                    _wait(rejoined_guest_sees_purchase, session)
                    credits_after_purchase = enemy.credits
                    sidearm_after_purchase = enemy.weapons["sidearm"]
                    assert match.sellable(enemy, "ghost")
                    enemy_client.send(Command(buy=["sell:ghost"]))
                    _wait(lambda: enemy.pid in session.net.pending)
                    buy_deadline = match.time + 1 / 64
                    match.phase_until = buy_deadline
                    session.step(1 / 64)
                    assert match.time == buy_deadline and match.phase == "live"
                    assert enemy.weapons["sidearm"] == sidearm_after_purchase and enemy.credits == credits_after_purchase

                    def rejoined_guest_sees_live_phase() -> bool:
                        update_enemy_view()
                        return enemy_shadow.round_no == next_round + 1 and enemy_shadow.phase == "live"

                    _wait(rejoined_guest_sees_live_phase, session)
                    guest_state = enemy_shadow.players[enemy.pid]
                    assert guest_state.weapons["sidearm"] == sidearm_after_purchase
                    assert guest_state.credits == credits_after_purchase and "ghost" not in guest_state.remote_sellable

                    token = enemy_client.token
                    enemy_client.close()
                    _wait(lambda: enemy.is_bot, session)
                    assert match.phase == "live"

                    enemy_client = NetClient(f"127.0.0.1:{session.net.port}", "Opponent", "omen", token=token)
                    assert enemy_client.rejoined and enemy_client.pid == enemy.pid
                    enemy_shadow = Match(match.world)

                    _wait(rejoined_guest_sees_live_phase, session)
                    assert "ghost" not in enemy_shadow.players[enemy.pid].remote_sellable
                    credits_after_purchase = enemy.credits
                    sidearm_after_purchase = enemy.weapons["sidearm"]
                    assert sidearm_after_purchase.key == "ghost"
                    enemy_client.send(Command(buy=["sell:ghost"]))
                    _wait(lambda: enemy.pid in session.net.pending)
                    session.step(1 / 64)
                    processed_at = match.time
                    _wait(lambda: rejoined_guest_sees_live_phase() and enemy_shadow.time >= processed_at, session)
                    guest_state = enemy_shadow.players[enemy.pid]
                    assert enemy.weapons["sidearm"] == guest_state.weapons["sidearm"] == sidearm_after_purchase
                    assert enemy.credits == guest_state.credits == credits_after_purchase
    finally:
        if enemy_client is not None:
            enemy_client.close()
        if teammate is not None:
            teammate.close()
        client.close()


def test_deathmatch_iso_disconnect_allows_duel_victim_to_respawn(session: HostSession) -> None:
    victim = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "iso")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(1)
        _wait(lambda: session.match.players[client.pid].team == 1, session)
        assert session.configure_lobby(mode="deathmatch")
        assert session.start(team_size=1)
        m = session.match
        iso = m.players[client.pid]
        m.time = m.phase_until
        session.step(0)
        iso.duel_id = victim.duel_id = iso.pid
        iso.passive_state["iso_contract"] = (victim.pid, m.time + 15)
        m._kill(iso, victim, "classic", "body")
        session.step(0)
        client.close()
        _wait(lambda: iso.is_bot, session)

        m.time = victim.died_at + 1.6
        session.step(0)
        assert not victim.alive and victim.duel_id == iso.pid
        m.time = victim.died_at + 2
        session.step(0)
        assert victim.alive and victim.duel_id == 0
        assert m.deathmatch_spawn_protected(victim)
        assert m.score == [0, 1]
    finally:
        client.close()


def test_ip_party_reopens_in_place_and_syncs_a_second_match(session: HostSession) -> None:
    host = session.match.add_player("Host", 0, "reyna")
    target = f"127.0.0.1:{session.net.port}"
    client = NetClient(target, "Guest", "sage")
    extra = None
    try:
        pid, token = client.pid, client.token
        client.choose_team(0)
        _wait(lambda: session.match.players[pid].team == 0, session)
        assert session.configure_lobby(map_key="bind", mode="quick")
        assert session.match.win_rounds == 5
        assert session.configure_lobby(mode="standard")
        assert session.match.win_rounds == session.match.cfg.lobby.win_rounds
        assert session.start(team_size=1)
        assert session.team_counts() == [2, 2]
        assert not session.configure_lobby(map_key="haven")
        assert not session.return_to_lobby()
        session.match.players[pid].kills = 3
        session.match.phase = "over"
        assert session.return_to_lobby()
        assert session.match.players.keys() == {host.pid, pid}
        assert session.match.players[pid].kills == 0
        assert session.match.players[pid].agent == "sage" and session.match.players[pid].team == 0
        assert session.net.join_code.endswith(f":{session.net.port}") and session.net.tokens[token] == pid
        assert session.configure_lobby(map_key="haven", mode="deathmatch")

        snapshots = []
        def receive(wanted_phase):
            snapshots.extend(m for m in client.take() if m["type"] == "state")
            return bool(snapshots and snapshots[-1]["game"] == 1 and snapshots[-1]["snap"]["phase"] == wanted_phase)

        _wait(lambda: receive("lobby"), session)
        assert client.connected and client.map_key == "haven" and snapshots[-1]["snap"]["mode"] == "deathmatch"
        extra = NetClient(target, "New guest", "omen")
        assert extra.pid != pid
        extra.close()
        _wait(lambda: extra.pid not in session.match.players, session)
        assert session.start(team_size=2)
        _wait(lambda: receive("buy"), session)
        client.send(Command(buy=["tdm1:ghost", "tdm4:vandal"]))
        shadow = Match(session.match.world)

        def receive_loadout() -> bool:
            if not receive("buy"):
                return False
            apply_snapshot(shadow, snapshots[-1]["snap"], pid)
            return shadow.players[pid].dm_loadout[-1] == "vandal"

        _wait(receive_loadout, session)
        assert shadow.dm_stage == 1 and shadow.players[pid].weapon.key == "ghost"
        session.match.time = session.match.phase_until
        _wait(lambda: receive("live"), session)
        assert snapshots[-1]["snap"]["round"] == 1
        assert any(p["pid"] == pid and not p["bot"] for p in snapshots[-1]["snap"]["roster"])

        match = session.match
        guest = match.players[pid]
        station = match.drops[0]
        guest.pos, guest.ground = station.pos, match.world.ground_height(station.pos)
        apply_snapshot(shadow, snapshots[-1]["snap"], pid)
        assert any(drop.pos == station.pos for drop in shadow.drops)
        client.send(Command(interact=True))

        def receive_station_weapon(expected: bool) -> bool:
            if not receive("live"):
                return False
            apply_snapshot(shadow, snapshots[-1]["snap"], pid)
            return shadow.players[pid].weapon.from_station == expected

        _wait(lambda: receive_station_weapon(True), session)
        assert guest.weapon.from_station and station not in match.drops
        assert all(drop.pos != station.pos for drop in shadow.drops)
        guest_view = shadow.players[pid].weapon
        assert (guest_view.key, guest_view.mag, guest_view.reserve) == (station.key, station.mag, station.reserve)
        client.send(Command(drop=True))
        _wait(lambda: receive_station_weapon(False), session)
        assert guest.weapon.key == shadow.players[pid].weapon.key == "ghost" and station not in match.drops

        orb = match.recovery_orbs[0]
        assert orb in shadow.recovery_orbs
        guest.hp = 40
        guest.pos, guest.ground = orb, match.world.ground_height(orb)

        def receive_recovery() -> bool:
            if not receive("live"):
                return False
            apply_snapshot(shadow, snapshots[-1]["snap"], pid)
            return orb not in shadow.recovery_orbs and shadow.players[pid].hp > 40

        _wait(receive_recovery, session)
        assert any(zone.kind == "tdm_recovery" and zone.owner == pid for zone in shadow.effects)
        host_player = match.players[host.pid]
        host_player.hp = 50
        host_player.pos, host_player.ground = orb, match.world.ground_height(orb)

        def receive_ally_heal() -> bool:
            return receive_recovery() and shadow.players[host.pid].hp > 50

        _wait(receive_ally_heal, session)
        guest.pos, host_player.pos = match.world.spawns[0][:2]
        match.time = match.dm_next_ultimate_wave

        def receive_ultimate_wave() -> bool:
            if not receive("live"):
                return False
            apply_snapshot(shadow, snapshots[-1]["snap"], pid)
            return len(shadow.orbs) == 2

        _wait(receive_ultimate_wave, session)
        point = match.orbs[0]
        guest_before, host_before = guest.ult_points, host_player.ult_points
        guest.pos, guest.ground = point, match.world.ground_height(point)

        def receive_ultimate_points(player_id: int, points: int) -> bool:
            if not receive("live"):
                return False
            apply_snapshot(shadow, snapshots[-1]["snap"], pid)
            return point not in shadow.orbs and shadow.players[player_id].ult_points == points

        _wait(lambda: receive_ultimate_points(pid, guest_before + 10), session)
        assert any(zone.kind == "tdm_ultimate" and zone.owner == pid for zone in shadow.effects)
        host_player.pos, host_player.ground = point, match.world.ground_height(point)
        _wait(lambda: receive_ultimate_points(host_player.pid, host_before + 10), session)
        assert (guest.ult_points, host_player.ult_points) == (guest_before + 10, host_before + 10)
        point = match.orbs[0]
        host_player.pos, host_player.ground = point, match.world.ground_height(point)
        _wait(lambda: receive_ultimate_points(host_player.pid, host_before + 20), session)
        assert any(zone.kind == "tdm_ultimate" and zone.owner == host_player.pid for zone in shadow.effects)
        guest.pos, guest.ground = point, match.world.ground_height(point)
        _wait(lambda: receive_ultimate_points(pid, guest_before + 20), session)
        match.time = match.phase_until

        def receive_stage_weapon(player_id: int, weapon: str) -> bool:
            if not receive("live"):
                return False
            apply_snapshot(shadow, snapshots[-1]["snap"], pid)
            player = shadow.players.get(player_id)
            return shadow.dm_stage == 2 and player is not None and player.weapon is not None and player.weapon.key == weapon

        _wait(lambda: receive_stage_weapon(pid, "ghost"), session)
        assert shadow.deathmatch_stage_equip_left(shadow.players[pid]) > 0
        client.send(Command(buy=["tdm:equip:2"]))
        _wait(lambda: receive_stage_weapon(pid, "sheriff"), session)
        assert not shadow.deathmatch_stage_equip_left(shadow.players[pid])
        assert host_player.weapon.key == "classic"
        match.time = host_player.dm_stage_equip_until
        _wait(lambda: receive_stage_weapon(host_player.pid, "sheriff"), session)
    finally:
        if extra is not None and extra.connected:
            extra.close()
        client.close()


@pytest.mark.parametrize(("mode", "seconds"), [("deathmatch", 5), ("standard", 20), ("quick", 20)])
def test_device_recall_timing_for_host_and_guest(session: HostSession, mode: str, seconds: int) -> None:
    from gameplay.geometry import Vec

    host = session.match.add_player("Host", 0, "killjoy")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "killjoy")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(1)
        _wait(lambda: session.match.players[client.pid].team == 1, session)
        assert session.configure_lobby(mode=mode)
        assert session.start(team_size=1)
        m = session.match
        guest = m.players[client.pid]
        m.time = m.phase_until
        session.step(0.05)
        host.pos, guest.pos = Vec(17, 8), Vec(23, 8)
        client.send(Command(ability="E", facing=0, cursor_depth=2))
        session.step(0.05, {host.pid: Command(ability="E", facing=0, cursor_depth=2)})
        _wait(lambda: host.charges["E"] == guest.charges["E"] == 0, session)
        assert len([e for e in m.effects if e.props.get("key") == "E"]) == 2
        client.send(Command(interact=True, facing=0, cursor_depth=0))
        session.step(0.05, {host.pid: Command(interact=True, facing=0, cursor_depth=0)})

        def deadline(player):
            if mode == "deathmatch":
                return next(iter(player.dm_device_recalls.get("E", ())), 0)
            return player.ability_ready_at.get("E", 0)

        _wait(lambda: bool(deadline(host) and deadline(guest)), session)
        assert deadline(guest) == pytest.approx(m.time + seconds, abs=0.1)
        assert deadline(host) == pytest.approx(m.time + seconds, abs=0.2)
        m.time = min(deadline(host), deadline(guest)) - 0.01
        session.step(0)
        assert host.charges["E"] == guest.charges["E"] == 0
        m.time = max(deadline(host), deadline(guest))
        shadow = Match(m.world)

        def synced():
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], guest.pid)
            return guest.pid in shadow.players and shadow.players[guest.pid].charges.get("E") == 1

        _wait(synced, session)
        assert host.charges["E"] == guest.charges["E"] == 1
        assert not any(e.props.get("key") == "E" for e in m.effects)
    finally:
        client.close()


def test_deathmatch_ghost_syncs_for_guest(session: HostSession) -> None:
    from gameplay.geometry import Vec

    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        m = session.match
        assert session.configure_lobby(mode="deathmatch") and m.set_rules(allow_cheats=True)
        assert session.start(team_size=1) and session.end_deathmatch_phase()
        session.step(0.05)
        shadow = Match(m.world)
        positions = {}

        def synced(active):
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], client.pid, predict_own=True, server_pos=positions)
            player = shadow.players.get(client.pid)
            return player is not None and player.dm_ghost == active and (player.z > 0 if active else player.z == 0)

        _wait(lambda: synced(False), session)
        predicted = shadow.players[client.pid]
        for active in (True, False):
            predicted.pos += Vec(1, 0)
            predicted.vel, predicted.vz = Vec(3, 0), 2.0
            client.send(Command(buy=["tdm:toggle_ghost"], jump=active))
            _wait(lambda: synced(active), session)
            assert predicted.pos == positions[client.pid]
            assert predicted.vel == Vec(0, 0) and predicted.vz == 0
        assert not m.players[client.pid].dm_ghost
        client.send(Command(buy=["tdm:toggle_ghost"], jump=True))
        _wait(lambda: synced(True), session)
        player = m.players[client.pid]
        client.close()
        _wait(lambda: player.is_bot, session)
        assert not player.dm_ghost
    finally:
        client.close()


def test_deathmatch_host_can_end_phase_and_guest_receives_result(session: HostSession) -> None:
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        m = session.match
        assert session.configure_lobby(mode="deathmatch")
        assert m.set_rules(allow_cheats=True)
        assert session.start(team_size=1)
        shadow = Match(m.world)

        def sync(phase, stage):
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], client.pid)
            return shadow.phase == phase and shadow.dm_stage == stage

        _wait(lambda: sync("buy", 1), session)
        assert session.toggle_deathmatch_timer()
        _wait(lambda: sync("buy", 1) and shadow.dm_timer_paused, session)
        paused_left = shadow.phase_time_left()
        paused_at = shadow.time
        _wait(lambda: sync("buy", 1) and shadow.time > paused_at, session)
        assert shadow.phase_time_left() == pytest.approx(paused_left)
        assert session.toggle_deathmatch_timer()
        _wait(lambda: sync("buy", 1) and not shadow.dm_timer_paused and shadow.phase_time_left() < paused_left, session)
        client.send(Command(buy=["end_dm_phase"]))
        session.step(0.05)
        assert m.phase == "buy"
        for stage in range(1, 5):
            assert session.end_deathmatch_phase()
            _wait(lambda: sync("live", stage), session)
        m.score = [3, 4]
        assert session.end_deathmatch_phase()
        _wait(lambda: sync("over", 4), session)
        assert shadow.score == [3, 4] and shadow.match_winner == 1
    finally:
        client.close()


def test_deathmatch_guest_receives_surrender_result(session: HostSession) -> None:
    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "jett")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        assert session.configure_lobby(mode="deathmatch") and session.start(team_size=1)
        assert session.surrender(host.team)
        assert not session.surrender(host.team)
        results = []
        snapshots = []

        def received():
            for message in client.take():
                if message["type"] == "state" and message["snap"]["phase"] == "over":
                    snapshots.append(message["snap"])
                elif message["type"] == "events":
                    results.extend(e["data"] for e in message["events"] if e["kind"] == "round_end")
            return bool(snapshots and results)

        _wait(received)
        assert snapshots[-1]["winner"] == 1 and snapshots[-1]["dm_left"] == 0
        assert results == [{"winner": 1, "reason": "Surrendered", "score": [0, 0]}]
    finally:
        client.close()


@pytest.mark.parametrize("arrival", ["together", "in_lobby", "next_match"])
def test_deathmatch_guest_routes_result_across_lobby_transition(session: HostSession, arrival: str) -> None:
    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "jett")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        assert session.configure_lobby(mode="deathmatch") and session.start(team_size=1)
        generation = session.net.generation
        _wait(lambda: any(msg["type"] == "state" and msg["game"] == generation
                          for msg in client.take()), session)
        assert session.surrender(host.team) and session.return_to_lobby()
        session.step(0)

        def buffered():
            client.inbox.extend(event.message for event in client.lobby.poll()
                                if event.kind == "message" and event.message)
            return (any(msg.get("t") == "events" and msg.get("game") == generation for msg in client.inbox)
                    and any(msg.get("t") == "state" and msg["snap"]["phase"] == "lobby" for msg in client.inbox))

        _wait(buffered)
        if arrival != "together":
            results = [msg for msg in client.inbox if msg.get("t") == "events"]
            client.inbox = [msg for msg in client.inbox if msg.get("t") != "events"]
            assert client.take()[-1]["snap"]["phase"] == "lobby"
            if arrival == "next_match":
                assert session.start(team_size=1)
                _wait(lambda: any(msg["type"] == "state" and msg["snap"]["phase"] == "buy"
                                  for msg in client.take()), session)
            client.inbox.extend(results)
        messages = client.take()
        if arrival == "together":
            assert messages[-1]["snap"]["phase"] == "lobby"
        expected = [] if arrival == "next_match" else [
            {"winner": 1, "reason": "Surrendered", "score": [0, 0]},
        ]
        assert [e["data"] for msg in messages if msg["type"] == "events" for e in msg["events"]
                if e["kind"] == "round_end"] == expected
    finally:
        client.close()


def test_deathmatch_guest_receives_draw_at_time_limit(session: HostSession) -> None:
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        assert session.configure_lobby(mode="deathmatch") and session.start(team_size=1)
        m = session.match
        for _ in range(4):
            m.time = m.phase_until
            session.step(0)
        assert m.dm_stage == 4
        m.score = [12, 12]
        m.time = m.dm_ends_at
        session.step(0.1)
        shadow = Match(m.world)
        results = []

        def received():
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], client.pid)
                elif message["type"] == "events":
                    results.extend(e["data"] for e in message["events"] if e["kind"] == "round_end")
            return shadow.phase == "over" and bool(results)

        _wait(received)
        assert shadow.score == [12, 12] and shadow.match_winner is None
        assert shadow.dm_ends_at == shadow.time and shadow.round_reason == "Time limit"
        assert results == [{"winner": None, "reason": "Time limit", "score": [12, 12]}]
    finally:
        client.close()


def test_deathmatch_guest_receives_only_one_result_at_kill_limit(session: HostSession) -> None:
    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        m = session.match
        assert session.configure_lobby(mode="deathmatch") and session.start(team_size=2)
        m.time = m.phase_until
        session.step(0.05)
        first, second = [p for p in m.players.values() if p.team == 1]
        m.score = [99, 99]
        m.events = []
        m._kill(host, first, "classic", "body")
        m._kill(host, second, "classic", "body")
        session.net.broadcast(m.events)
        results = []
        messages = []

        def received():
            for message in client.take():
                if message["type"] == "state" and message["snap"]["phase"] == "over":
                    results.append(message["snap"])
                elif message["type"] == "events":
                    messages.extend(message["events"])
            return bool(results and any(event["kind"] == "round_end" for event in messages))

        _wait(received)
        assert results[-1]["winner"] == 0 and results[-1]["score"] == [100, 99]
        assert results[-1]["dm_left"] == 0
        assert [event["kind"] for event in messages].count("round_end") == 1
    finally:
        client.close()


@pytest.mark.parametrize("healing", [False, True])
def test_deathmatch_assist_syncs_to_guest(session: HostSession, healing: bool) -> None:
    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        m = session.match
        client.choose_team(0)
        _wait(lambda: m.players[client.pid].team == 0, session)
        assert session.configure_lobby(mode="deathmatch") and session.start(team_size=2)
        guest = m.players[client.pid]
        victim = next(p for p in m.players.values() if p.team == 1)
        m.time = m.phase_until
        session.step(0.05)
        if healing:
            from gameplay.kit.statuses import _heal_whole

            host.hp = 50
            _heal_whole(m, host, 25, healer=guest.pid)
        else:
            m._damage(guest, victim, 11, "body", "classic")
        m._damage(host, victim, 200, "body", "classic")
        assert guest.assists == 1 and host.kills == 1
        shadow = Match(m.world)

        def synced():
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], guest.pid)
            return guest.pid in shadow.players and shadow.players[guest.pid].assists == 1

        _wait(synced, session)
    finally:
        client.close()


def test_deathmatch_invincibility_shot_passes_through_guest(session: HostSession) -> None:
    from gameplay.geometry import Vec, heading

    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(1)
        m = session.match
        _wait(lambda: m.players[client.pid].team == 1, session)
        assert session.configure_lobby(mode="deathmatch") and m.set_rules(allow_cheats=True, invincibility=True)
        assert session.start(team_size=2) and session.end_deathmatch_phase()
        session.step(0.05)
        guest = m.players[client.pid]
        bot = next(p for p in m.players.values() if p.is_bot and p.team == 1)
        host.pos, guest.pos, bot.pos = Vec(17, 15), Vec(17, 19), Vec(17, 23)
        host.cursor_depth = 8
        direction = heading(0)
        m._trace(host, m.weapons["classic"], direction, direction)
        assert guest.hp == 100 and guest.armor == 25
        assert bot.hp < 100 or bot.armor < 25
        shadow = Match(m.world)

        def synced():
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], guest.pid)
            remote = shadow.players.get(guest.pid)
            return remote is not None and shadow.cheat("invincibility") and remote.hp == 100 and remote.armor == 25

        _wait(synced, session)
    finally:
        client.close()


def test_deathmatch_infinite_magazines_syncs_for_guest(session: HostSession) -> None:
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        m = session.match
        assert session.configure_lobby(mode="deathmatch")
        assert m.set_rules(allow_cheats=True, infinite_magazines=True)
        assert session.start(team_size=1)
        guest = m.players[client.pid]
        m.time = m.phase_until
        session.step(0.05)
        station = m.drops[0]
        guest.pos, guest.ground = station.pos, m.world.ground_height(station.pos)
        client.send(Command(interact=True))
        _wait(lambda: guest.weapon.from_station, session)
        guest.weapon.mag = guest.weapon.reserve = 0
        client.send(Command(reload=True))
        _wait(lambda: guest.reload_until > m.time, session)
        m.time = guest.reload_until
        shadow = Match(m.world)

        def reloaded():
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], guest.pid)
            player = shadow.players.get(guest.pid)
            return player is not None and player.weapon.from_station and player.weapon.reserve == 0 and player.weapon.mag > 0

        _wait(reloaded, session)
        assert shadow.cheat("infinite_magazines") and not shadow.cheat("infinite_ammo")
        assert shadow.has_infinite_reserve(shadow.players[guest.pid].weapon)
    finally:
        client.close()


@pytest.mark.parametrize(("host_agent", "guest_agent", "seconds", "host_cost", "guest_cost"), [
    ("waylay", "chamber", 4.5, 60, 70),
    ("skye", "kayo", 22, 70, 70),
    ("skye", "viper", 22, 70, 90),
    ("skye", "neon", 24, 70, 60),
    ("skye", "yoru", 22, 70, 60),
    ("harbor", "fade", 24, 70, 80),
    ("harbor", "vyse", 29, 70, 80),
    ("harbor", "iso", 31, 70, 60),
    ("harbor", "clove", 22, 70, 70),
])
def test_deathmatch_new_agent_cooldowns_sync_for_host_and_guest(
    session: HostSession, host_agent: str, guest_agent: str, seconds: float, host_cost: int, guest_cost: int,
) -> None:
    host = session.match.add_player("Host", 0, host_agent)
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", guest_agent)
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(0)
        _wait(lambda: session.match.players[client.pid].team == 0, session)
        assert session.configure_lobby(mode="deathmatch") and session.start(team_size=2)
        m = session.match
        guest = m.players[client.pid]
        m.time = m.phase_until
        session.step(0)
        for _ in range(round(seconds * 10) + 1):
            session.step(0.1)
        shadow = Match(m.world)

        def synced():
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], guest.pid)
            return guest.pid in shadow.players and shadow.players[guest.pid].charges.get("Q") == 1

        _wait(synced, session)
        assert guest.charges["Q"] == 1 and host.charges["Q"] == shadow.players[host.pid].charges["Q"] == 0
        assert shadow.ultimate_cost(shadow.players[guest.pid]) == guest_cost
        assert shadow.ultimate_cost(shadow.players[host.pid]) == host_cost
    finally:
        client.close()


def test_deathmatch_astra_stars_sync_for_guest(session: HostSession) -> None:
    session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "astra")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(1)
        _wait(lambda: session.match.players[client.pid].team == 1, session)
        assert session.configure_lobby(mode="deathmatch") and session.start(team_size=1)
        m = session.match
        guest = m.players[client.pid]
        shadow = Match(m.world)

        def synced(charges: int) -> bool:
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], guest.pid)
            remote = shadow.players.get(guest.pid)
            return remote is not None and remote.charges.get("E") == charges

        m.time = m.phase_until
        session.step(0)
        _wait(lambda: synced(2), session)
        assert shadow.ultimate_cost(shadow.players[guest.pid]) == 90
        guest.pos = m._deathmatch_station_anchors[0]
        points = [(guest.pos.x, guest.pos.y)]
        client.send(Command(ability="X", points=points))
        _wait(lambda: synced(1), session)
        star = next(e for e in m.effects if e.owner == guest.pid and e.props.get("sprite") == "astra_star")
        m.time = star.start
        client.send(Command())
        _wait(lambda: guest.prev_ability is None, session)
        client.send(Command(ability="X", ability_alt=True, points=points))
        _wait(lambda: bool(guest.dm_device_recalls.get("E")), session)
        deadline = guest.dm_device_recalls["E"][0]
        assert deadline - m.time == pytest.approx(20, abs=0.1)
        m.time = deadline - 0.125
        session.step(0)
        assert guest.charges["E"] == 1
        m.time = deadline
        session.step(0)
        _wait(lambda: synced(2), session)
        guest.recharge_timers["E"] = 35.875
        session.step(0.0625)
        assert guest.charges["E"] == 2
        session.step(0.0625)
        _wait(lambda: synced(3), session)
    finally:
        client.close()


@pytest.mark.parametrize(("agent", "cooldowns", "cost"),
                         [("veto", (40, 24, 40), 60), ("hush", (51, 44, 46), 70)])
def test_deathmatch_signature_and_basic_cooldowns_sync_for_host_and_guest(
    session: HostSession, agent: str, cooldowns: tuple[int, int, int], cost: int,
) -> None:
    host = session.match.add_player("Host", 0, agent)
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", agent)
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(0)
        _wait(lambda: session.match.players[client.pid].team == 0, session)
        assert session.configure_lobby(mode="deathmatch") and session.start(team_size=2)
        m = session.match
        guest = m.players[client.pid]
        for player in (host, guest):
            assert player.agent == agent
            assert player.recharge_timers == {key: seconds / 2 for key, seconds in zip("CQE", cooldowns)}
            assert m.ultimate_cost(player) == cost
            player.charges.update(C=0, Q=0, E=0)
            player.recharge_timers.update({key: seconds - 0.125 for key, seconds in zip("CQE", cooldowns)})
        m.time = m.phase_until
        session.step(0.0625)
        assert all(not any(p.charges[k] for k in "CQE") for p in (host, guest))
        session.step(0.0625)
        shadow = Match(m.world)

        def synced():
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], guest.pid)
            return all(pid in shadow.players and all(shadow.players[pid].charges.get(k) == 1 for k in "CQE")
                       for pid in (host.pid, guest.pid))

        _wait(synced, session)
        assert all(all(p.charges[k] == 1 for k in "CQE") for p in (host, guest))
        assert all(shadow.ultimate_cost(shadow.players[pid]) == cost for pid in (host.pid, guest.pid))
    finally:
        client.close()


def test_deathmatch_phoenix_return_resets_guest_prediction(session: HostSession) -> None:
    from gameplay.geometry import Vec

    session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "phoenix")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        assert session.configure_lobby(mode="deathmatch") and session.start(team_size=1)
        m = session.match
        guest = m.players[client.pid]
        m.time = m.phase_until
        session.step(0)
        guest.pos = m._deathmatch_station_anchors[0]
        guest.ult_points = m.ultimate_cost(guest)
        client.send(Command(ability="X"))
        _wait(lambda: any("return_armor" in e.data for e in m.effects), session)
        marker = next(e for e in m.effects if "return_armor" in e.data)
        shadow = Match(m.world)
        positions = {}
        apply_snapshot(shadow, m.snapshot(guest.pid), guest.pid, predict_own=True, server_pos=positions)
        predicted = shadow.players[guest.pid]
        guest.pos = predicted.pos = marker.pos + Vec(1, 0)
        predicted.vel, predicted.vz = Vec(3, 0), 2.0
        m.time = marker.until
        session.step(0)
        assert guest.ability_return_at == marker.until
        session.step(0.1)

        def synced():
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], guest.pid, predict_own=True, server_pos=positions)
            return predicted.ability_return_at == marker.until

        _wait(synced)
        assert predicted.pos == marker.pos
        assert predicted.vel == Vec(0, 0) and predicted.vz == 0.0
    finally:
        client.close()


@pytest.mark.parametrize("receive_death_snapshot", [True, False])
def test_team_deathmatch_respawn_resets_client_prediction(receive_death_snapshot: bool) -> None:
    from gameplay.geometry import Vec
    from gameplay.world import load_playable_map

    host = Match(load_playable_map("haven"))
    player = host.add_player("Guest", 1, "jett")
    host.set_mode("deathmatch")
    host.start()
    host.time = host.phase_until
    host.tick(0.0, {})
    shadow = Match(host.world)
    positions = {}
    apply_snapshot(shadow, host.snapshot(player.pid), player.pid, predict_own=True, server_pos=positions)

    host._kill(None, player, "spawn", "body")
    if receive_death_snapshot:
        apply_snapshot(shadow, host.snapshot(player.pid), player.pid, predict_own=True, server_pos=positions)
    host.time += host.deathmatch_rules["respawn"]
    host.tick(0.01, {})
    assert player.alive and player.deaths == 1

    predicted = shadow.players[player.pid]
    predicted.pos = player.pos + Vec(1, 0)
    predicted.vel, predicted.vz = Vec(4, 0), 2.0
    apply_snapshot(shadow, host.snapshot(player.pid), player.pid, predict_own=True, server_pos=positions)
    assert predicted.pos == positions[player.pid]
    assert predicted.vel == Vec(0, 0) and predicted.vz == 0.0

    predicted.pos += Vec(1, 0)
    predicted.vel = Vec(4, 0)
    apply_snapshot(shadow, host.snapshot(player.pid), player.pid, predict_own=True, server_pos=positions)
    assert predicted.pos == positions[player.pid] + Vec(1, 0)
    assert predicted.vel == Vec(4, 0)


def test_deathmatch_recovery_orb_shares_healing_with_guest(session: HostSession) -> None:
    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "jett")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(0)
        _wait(lambda: session.match.players[client.pid].team == 0, session)
        assert session.configure_lobby(mode="deathmatch") and session.start(team_size=2)
        m = session.match
        guest = m.players[client.pid]
        m.time = m.phase_until
        session.step(0)
        point = m.recovery_orbs[0]
        host.pos, host.ground, host.hp = point, m.world.ground_height(point), 50
        session.step(0)
        assert point not in m.recovery_orbs and guest.dm_recovery_until == 0
        guest.pos, guest.ground, guest.hp = point, host.ground, 50
        session.step(0)
        assert guest.dm_recovery_until == host.dm_recovery_until > m.time
        session.step(0.1)
        assert guest.hp > 50

        shadow = Match(m.world)

        def synced():
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], guest.pid)
            remote = shadow.players.get(guest.pid)
            return (remote is not None and remote.hp == guest.hp and point not in shadow.recovery_orbs
                    and any(e.kind == "tdm_recovery" and e.owner == host.pid for e in shadow.effects))

        _wait(synced)
    finally:
        client.close()


def test_deathmatch_contested_ultimate_orb_syncs_to_guest(session: HostSession) -> None:
    from gameplay.geometry import Vec

    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "jett")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(1)
        _wait(lambda: session.match.players[client.pid].team == 1, session)
        assert session.configure_lobby(mode="deathmatch") and session.start(team_size=1)
        m = session.match
        guest = m.players[client.pid]
        m.time = m.phase_until
        session.step(0)
        m.time = m.dm_next_ultimate_wave
        session.step(0)
        point = m.orbs[0]
        guest.pos, host.pos = point, point + Vec(0.5, 0)
        guest.ground = host.ground = m.world.ground_height(point)
        session.step(0.1)
        assert guest.ult_points == 10 and host.ult_points == 0

        shadow = Match(m.world)

        def synced():
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], guest.pid)
            remote = shadow.players.get(guest.pid)
            return remote is not None and remote.ult_points == 10 and point not in shadow.orbs

        _wait(synced)
    finally:
        client.close()


def test_team_deathmatch_spawn_damage_syncs_for_host_and_guest(session: HostSession) -> None:
    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "jett")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_team(1)
        _wait(lambda: session.match.players[client.pid].team == 1, session)
        assert session.configure_lobby(map_key="haven", mode="deathmatch")
        assert session.start(team_size=1)
        m = session.match
        guest = m.players[client.pid]
        m.time = m.phase_until
        session.step(0.05)
        m._kill(host, guest, "classic", "body")
        m._kill(None, host, "classic", "body")
        m.time += 1.5
        session.step(0.05)
        shadow = Match(m.world)
        messages = []

        def sync(predicate):
            for message in client.take():
                if message["type"] == "state":
                    apply_snapshot(shadow, message["snap"], guest.pid)
                elif message["type"] == "events":
                    messages.extend(message.get("events", []))
            return guest.pid in shadow.players and predicate(shadow.players[guest.pid])

        _wait(lambda: sync(shadow.deathmatch_spawn_protected), session)
        assert m.deathmatch_spawn_protected(host) and m.deathmatch_spawn_protected(guest)
        for attacker, target in ((host, guest), (guest, host)):
            m._damage(attacker, target, 60, "body", "classic")
            assert target.hp == 100 and target.armor == 25
        m.time = guest.dm_spawn_protected_until
        host_events = session.step(0.05)
        assert {e.data["pid"] for e in host_events if e.kind == "hit" and e.data.get("source") == "spawn"} == {
            host.pid, guest.pid,
        }
        def guest_hit_received() -> bool:
            return any(e["kind"] == "hit" and e["data"]["pid"] == guest.pid and e["data"].get("source") == "spawn"
                       for e in messages)

        _wait(lambda: sync(lambda p: p.hp == 90 and not shadow.deathmatch_spawn_protected(p)) and guest_hit_received(),
              session)
        assert shadow.players[guest.pid].armor == 25 and host.hp == 90
        client.send(Command(ability="E"))
        _wait(lambda: guest.prev_ability == "E", session)
        assert guest.charges["E"] == 1 and guest.dash_armed_until == 0
        guest.pos = m.drops[0].pos
        guest.ground = m.world.ground_height(guest.pos)
        client.send(Command())
        _wait(lambda: guest.prev_ability is None, session)
        client.send(Command(ability="E"))
        _wait(lambda: sync(lambda p: p.charges.get("E") == 0 and p.dash_armed_until > shadow.time), session)
    finally:
        client.close()


@pytest.mark.parametrize(("action", "checkpoint", "wingman"), [
    ("plant", False, False), ("defuse", False, False), ("defuse", True, False), ("defuse", True, True),
])
def test_rejoin_restores_running_spike_audio(tmp_path, monkeypatch, action, checkpoint, wingman) -> None:
    from unittest.mock import Mock

    from client.game import Game
    from gameplay.geometry import Vec
    from gameplay.kit.engine import remove_device
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    host = Game(args(host=True, port=_free_port(), agent="gekko" if wingman else "omen"))
    guest = None
    dt = 1 / 64
    try:
        guest = Game(args(join=f"127.0.0.1:{host.session.net.port}", name="Listener"))
        actor = host.match.players[host.me]
        assert host.session.start(team_size=2)
        monkeypatch.setattr(host.session.bots, "commands", lambda dt: {})
        match = host.match
        site = match.world.sites[0]
        actor.pos = site.rect.center
        actor.level = match.world.floor_level(actor.pos, 0)
        actor.ground = match.world.ground_height(actor.pos, actor.level)
        match.phase, match.phase_until = "live", match.time + 60
        if action == "plant":
            match.spike_carrier = actor.pid
        else:
            match._plant(actor, site.name)
            actor.team = next(team for team in (0, 1) if match.side(team) == "defense")
            match.spike_half_defused = checkpoint
            if not wingman:
                actor.pos = match.spike_pos + Vec(0.5, 0)
        if wingman:
            actor.charges["Q"] = 1
            host.step(dt, Command(ability="Q", ability_alt=True, cursor_depth=0))
            device = next(effect for effect in match.effects if effect.props.get("gekko_objective"))
        held = Command(use_spike=not wingman)
        started = []
        for _ in range(65):
            started.extend(event for event in host.step(dt, held)
                           if event.kind == f"{action}_start")
        [active] = match.snapshot(guest.me)["spike_audio"]
        if action == "defuse":
            [event] = started
            assert Vec(*event.data["pos"]) == Vec(*active["pos"]) == match.spike_pos
        audio_id = active.get("audio_id", actor.pid)
        assert audio_id == (-actor.pid if wingman else actor.pid)
        assert active["key"] == ("spike_defuse_half" if checkpoint else f"spike_{action}")
        if checkpoint:
            live_play = Mock(wraps=host.sound.play)
            with monkeypatch.context() as patch:
                patch.setattr(host.sound, "play", live_play)
                host.handle_events(started)
            assert [call.args[0] for call in live_play.call_args_list] == ["spike_defuse_half", "spike_defuse"]
            cue, work = live_play.call_args_list
            assert cue.args[2] == match.spike_pos
            if not wingman:
                assert work.args[2] == match.spike_pos != actor.pos
                [event] = started
                assert Vec(*event.data["spike_pos"]) == match.spike_pos
            host.stop_spike_sound(audio_id)
        def receive_initial_audio():
            host.step(dt, held)
            guest.handle_events(guest.step(dt, Command()))
            return bool(guest.ui.spike_sounds.get(audio_id, (None, []))[1])

        _wait(receive_initial_audio)
        _, previous_tracks = guest.ui.spike_sounds[audio_id]
        listener = guest.match.players[guest.me]
        assert all(channel.get_sound() == sample for channel, sample, _ in previous_tracks)
        old = guest.client
        old.close()
        guest.update_spike_audio(listener)
        assert not guest.ui.spike_sounds and not guest.ui.spike_sound_sources
        assert all(channel.get_sound() != sample for channel, sample, _ in previous_tracks)
        guest.rejoin()
        assert guest.client is not old and guest.client.rejoined
        guest.update_spike_audio(listener)
        assert not guest.ui.spike_sounds
        # A start delivered alongside the first state must not replay the beginning.
        guest.client.inbox.append({"t": "events", "game": guest.client.generation, "events": [{
            "kind": f"{action}_start", "t": active["started"], "data": active,
        }]})
        play = Mock(wraps=guest.sound.play)
        monkeypatch.setattr(guest.sound, "play", play)
        events = []

        def receive(command):
            host.step(dt, command)
            batch = guest.step(dt, Command())
            events.extend(batch)
            guest.handle_events(batch)

        _wait(lambda: receive(held) or audio_id in guest.ui.spike_sounds)
        [restored] = [event for event in events if event.kind == "spike_audio_restore"]
        assert not any(event.kind == f"{action}_start" for event in events)
        [call] = [call for call in play.call_args_list if call.args[0] == f"spike_{action}"]
        if action == "defuse":
            assert call.args[2] == match.spike_pos
        tail = call.kwargs["sample_override"]
        original = guest.sound.sounds[f"spike_{action}"]
        offset = guest.match.time - restored.t
        if checkpoint:
            offset += float(match._spike["defuse_checkpoint"])
            assert all(call.args[0] != "spike_defuse_half" for call in play.call_args_list)
        assert tail.get_length() == pytest.approx(original.get_length() - offset, abs=0.001)
        _, tracks = guest.ui.spike_sounds[audio_id]
        if wingman:
            tick_effects = match._tick_effects

            def destroy_on_tick(dt):
                remove_device(match, device, "destroy")
                tick_effects(dt)

            with monkeypatch.context() as patch:
                patch.setattr(match, "_tick_effects", destroy_on_tick)
                host.step(dt, Command())
        _wait(lambda: receive(Command()) or audio_id not in guest.ui.spike_sounds)
        assert not match.snapshot(guest.me)["spike_audio"]
        assert all(channel.get_sound() != sample for channel, sample, _ in tracks)
    finally:
        if guest is not None:
            guest.client.close()
        host.session.close()


def test_party_lobby_buttons_and_map_render_after_rematch(tmp_path, monkeypatch, archived_agents) -> None:
    from client.game import Game
    from gameplay.world import PLAYABLE_MAP_KEYS
    from test_client import args
    import user_settings

    monkeypatch.setattr(user_settings, "SETTINGS_PATH", tmp_path / "settings.json")
    host = Game(args(host=True, port=_free_port()))
    target = f"localhost:{host.session.net.port}"
    guest = None
    try:
        guest = Game(args(join=target, name="Guest"))
        assert user_settings.load()["last_join"] == target

        def sync(phase, map_key):
            host.step(1 / 30, Command())
            guest.step(1 / 30, Command())
            return (
                guest.match.phase == phase and guest.match.world.key == map_key
                and guest.net_generation == host.session.net.generation
                and roster(guest) == roster(host)
                and guest.me in guest.match.players
            )

        def roster(game):
            return {pid: (p.agent, p.is_bot) for pid, p in game.match.players.items()}

        def check_content():
            assert guest.match.agents.keys() == host.match.agents.keys()
            assert "kestrel" not in host.match.agents
            assert all(agent in host.match.agents for agent, _ in roster(host).values())

        _wait(lambda: sync("lobby", "ascent"))
        check_content()
        assert not host.session.configure_lobby(map_key="workyard")
        assert not host.session.configure_lobby(map_key="_ascent")
        assert "kestrel" in archived_agents and "kestrel" not in host.match.agents
        guest.client.choose_agent("kestrel")
        guest.client.choose_team(0)
        _wait(lambda: host.match.players[guest.me].team == 0)
        assert host.match.players[guest.me].agent == "omen"
        guest.client.choose_team(1)
        _wait(lambda: host.match.players[guest.me].team == 1)
        host.start_from_lobby()
        _wait(lambda: sync("buy", "ascent"))
        check_content()
        assert any(bot for _, bot in roster(host).values())
        host.match.phase = "over"
        _wait(lambda: sync("over", "ascent"))
        host.draw()
        party = next(h for h in host.kit.hits if h.action == "party")
        assert host.screen_button(party.rect.center) == "party"
        host.return_party()
        _wait(lambda: sync("lobby", "ascent"))
        check_content()
        assert all(not bot for _, bot in roster(host).values())
        host.draw()
        map_button = next(h for h in host.kit.hits if h.action == "choose_map")
        host.pick_agent_at(map_button.rect.center)
        assert host.party_map_picker.keys == PLAYABLE_MAP_KEYS
        host.party_map_action("map_pick:_ascent")
        assert host.match.world.key == "ascent"
        host.party_map_action("choose_map")
        host.party_map_action("map_pick:bind")
        _wait(lambda: sync("lobby", "bind"))
        check_content()
        for step, key in ((-1, "ascent"), (-1, PLAYABLE_MAP_KEYS[-1]), (2, "bind")):
            host.change_party_setting("map", step)
            _wait(lambda: sync("lobby", key))
            check_content()

        old = guest.client
        old.close()
        _wait(lambda: guest.me not in host.match.players)
        assert host.session.configure_lobby(map_key="haven")
        guest.rejoin()
        assert guest.client is not old and not guest.client.rejoined
        _wait(lambda: sync("lobby", "haven"))
        check_content()
        guest.client.choose_agent("sage")
        _wait(lambda: host.match.players[guest.me].agent == "sage")
        guest.client.choose_agent("kestrel")
        guest.client.choose_team(0)
        _wait(lambda: host.match.players[guest.me].team == 0)
        assert host.match.players[guest.me].agent == "sage"
        guest.client.choose_team(1)
        _wait(lambda: host.match.players[guest.me].team == 1)
        guest.draw()
        assert not any(h.action.startswith("setting:") for h in guest.kit.hits)
        assert guest.client.connected and guest.map_cache and guest.match.round_no == 0
        host.start_from_lobby()
        _wait(lambda: sync("buy", "haven"))
        check_content()
        assert any(bot for _, bot in roster(host).values())

        pid, old = guest.me, guest.client
        old.close()
        _wait(lambda: roster(host).get(pid) == ("sage", True))
        guest.join_agent = "kestrel"
        guest.rejoin()
        assert guest.client is not old and guest.client.rejoined and guest.me == pid
        _wait(lambda: sync("buy", "haven"))
        check_content()
        assert roster(host)[pid] == ("sage", False)
    finally:
        if guest:
            guest.client.close()
        host.session.close()


def test_join_rejected_after_start(session: HostSession) -> None:
    session.start(team_size=1)
    with pytest.raises(ConnectionError):
        NetClient(f"127.0.0.1:{session.net.port}", "Late", "omen")


def test_oversized_message_is_refused() -> None:
    a, b = socket.socketpair()
    try:
        a.sendall((10_000_000).to_bytes(4, "big"))
        with pytest.raises(ValueError):
            recv_msg(b)
        with pytest.raises(ValueError):
            send_msg(a, {"x": "y" * 600_000})
    finally:
        a.close()
        b.close()


def test_fill_bots_balances_teams(session: HostSession) -> None:
    session.match.add_player("Host", 0, "omen")
    session.start(team_size=3)
    assert session.team_counts() == [3, 3]
    assert session.match.phase == "buy"


def test_client_picks_agent_in_lobby_only(session: HostSession) -> None:
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        client.choose_agent("sage")
        _wait(lambda: session.match.players[client.pid].agent == "sage", session)
        client.choose_agent("not-an-agent")
        session.start(team_size=1)
        client.choose_agent("jett")
        for _ in range(20):
            session.step(1 / 64)
        assert session.match.players[client.pid].agent == "sage"
    finally:
        client.close()


def test_dropped_player_rejoins_their_slot(session: HostSession) -> None:
    host = session.match.add_player("Host", 0, "omen")
    client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
    pid, token = client.pid, client.token
    _wait(lambda: pid in session.match.players, session)
    client.choose_team(0)
    _wait(lambda: session.match.players[pid].team == 0, session)
    session.start(team_size=1)
    match = session.match
    assert match.spike_carrier is None and match.spike_pos is not None
    match.players[pid].pos = match.spike_pos
    session.step(1 / 64)
    assert match.spike_carrier == pid
    host.credits = 5000
    client.send(Command(request="vandal"))
    _wait(lambda: match.players[pid].request == "vandal", session)
    old_purchase = match.players[pid].gift_action()
    client.close()
    _wait(lambda: match.players[pid].is_bot, session)
    assert match.players[pid].request == ""
    session.step(1 / 64, {host.pid: Command(buy=[old_purchase])})
    assert host.credits == 5000
    assert match.spike_carrier == pid
    back = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen", token=token)
    try:
        assert back.pid == pid and back.rejoined
        assert not session.match.players[pid].is_bot and session.match.players[pid].name == "Guest"
        assert pid not in session.bots.commands(1 / 64)
        assert match.players[pid].request == ""
        back.send(Command(request="vandal"))
        _wait(lambda: match.players[pid].request == "vandal", session)
        session.step(1 / 64, {host.pid: Command(buy=[old_purchase])})
        assert host.credits == 5000
        session.step(1 / 64, {host.pid: Command(buy=[match.players[pid].gift_action()])})
        assert host.credits == 2100
        assert match.spike_carrier == pid
    finally:
        back.close()


@pytest.mark.parametrize(("slot", "sprite"), [("Q", "sova_shock_bolt"), ("E", "sova_recon_bolt")])
def test_sova_bolt_guest_path_stays_continuous_after_first_bounce(session, monkeypatch, slot, sprite):
    from gameplay.geometry import Rect, Vec
    from gameplay.world import Wall, WorldMap

    match = session.match
    match.world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(90, 90)]})
    match.world.walls.append(Wall(Rect(4, 14, 16, 15), 3))
    guest = NetClient(f"127.0.0.1:{session.net.port}", "Sova guest", "sova")
    try:
        assert session.net.choose_team(guest.pid, 0)
        assert session.start(team_size=1)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match.phase, match.phase_until = "live", match.time + 60
        match.players[guest.pid].charges[slot] = 1
        guest.send(Command(ability=slot, facing=0, cursor_depth=16, bounces=2))
        replica = Match(match.world)

        def receive_bolt(after):
            for message in guest.take():
                if message["type"] == "state":
                    apply_snapshot(replica, message["snap"], guest.pid)
                    if any(e.props.get("sprite") == sprite and e.start > after for e in replica.effects):
                        return True
            return False

        _wait(lambda: receive_bolt(-1), session)
        original = next(e for e in replica.effects if e.props.get("sprite") == sprite)
        while match.time < original.start + 0.25:
            session.step(1 / 64)
        transition = match.time
        match.world.walls.append(Wall(Rect(4, 7, 16, 8), 3))
        _wait(lambda: receive_bolt(original.start), session)
        updated = next(e for e in replica.effects if e.props.get("sprite") == sprite)
        travel = 16 * (transition - original.start) / (original.until - original.start)
        assert travel > 4
        assert updated.start == pytest.approx(transition)
        assert updated.a.y == pytest.approx(14 - (travel - 4))
        assert updated.pos.y == pytest.approx(13.7)
        assert len(updated.props["bolt_path"]) == 3
        assert updated.until < original.until
        remaining_distance = (updated.a.y - 8) + (updated.pos.y - 8)
        assert remaining_distance / (updated.until - updated.start) == pytest.approx(
            16 / (original.until - original.start))
    finally:
        guest.close()


@pytest.mark.parametrize("bounces", [0, 1])
@pytest.mark.parametrize(("slot", "remove_cover", "rejoin"), [
    (slot, remove_cover, rejoin)
    for slot in ("Q", "E")
    for remove_cover, rejoin in ((True, None), (False, None), (True, "flight"), (True, "impact"))
] + [
    pytest.param("E", True, "expired", id="recon-expired"),
    pytest.param("E", True, "destroyed", id="recon-destroyed"),
    pytest.param("E", True, "destroyed_active", id="recon-destroyed-active"),
])
def test_sova_bolt_guest_receives_updated_impact(session, monkeypatch, slot, bounces, remove_cover, rejoin):
    from gameplay.geometry import Rect, Vec
    from gameplay.world import Wall, WorldMap

    match = session.match
    victim_y = (6 if bounces else 26) if remove_cover else (11 if bounces else 17)
    match.world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(10, victim_y)]})
    cover = Wall(Rect(4, 7, 16, 8) if bounces else Rect(4, 18, 16, 19), 3)
    if bounces:
        match.world.walls.append(Wall(Rect(4, 14, 16, 15), 3))
    if remove_cover:
        match.world.walls.append(cover)
    victim = match.add_player("Target host", 1, "omen")
    guest = NetClient(f"127.0.0.1:{session.net.port}", "Sova guest", "sova")
    try:
        assert session.net.choose_team(guest.pid, 0)
        assert session.start(team_size=1)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match.phase, match.phase_until = "live", match.time + 60
        match.players[guest.pid].charges[slot] = 1
        health = victim.hp
        guest.send(Command(ability=slot, facing=0, cursor_depth=16, bounces=bounces))
        _wait(lambda: any(e.props.get("bolt_path") for e in match.effects), session)
        bolt = next(e for e in match.effects if e.props.get("bolt_path"))
        old_impact = bolt.until
        dt = 1 / 64
        if remove_cover:
            while match.time + dt < old_impact:
                session.step(dt)
            match.broken_cover.add(cover.rect)
        else:
            while match.time < bolt.start + 0.2:
                session.step(dt)
            match.world.walls.append(cover)
        if slot == "Q" and bounces and remove_cover:
            guest.send(Command(facing=180))
        session.step(dt)
        assert (bolt.until > old_impact) if remove_cover else (bolt.until < old_impact)
        new_impact = bolt.until
        recon_ended = rejoin in ("expired", "destroyed", "destroyed_active")
        recon_destroyed = rejoin in ("destroyed", "destroyed_active")
        if rejoin:
            pid, token = guest.pid, guest.token
            guest.close()
            _wait(lambda: match.players[pid].is_bot, session)
            if rejoin == "impact" or recon_ended:
                while bolt in match.effects:
                    session.step(dt)
            if recon_ended:
                [sensor] = [effect for effect in match.effects if effect.kind == "sensor"]
                _wait(lambda: victim.revealed_until > match.time, session)
                reveal_expires = victim.revealed_until
                if recon_destroyed:
                    victim.pos = sensor.pos + Vec(1, 0)
                    weapon = match._weapon_def(victim)
                    assert weapon is not None
                    direction = Vec(-1, 0)
                    match._trace(victim, weapon, direction, direction)
                    assert sensor not in match.effects or sensor.props.get("ended")
                    assert match.time < sensor.start + 2.27
                _wait(lambda: sensor not in match.effects
                      and (rejoin == "destroyed_active" or victim.revealed_until <= match.time), session)
            guest = NetClient(f"127.0.0.1:{session.net.port}", "Sova guest", "sova", token=token)
            assert guest.pid == pid and guest.rejoined
            assert (match.time >= new_impact) == (rejoin != "flight")
            if slot == "Q" and bounces:
                guest.send(Command(facing=180))
        replica = Match(match.world)
        received_path = received_sensor = False
        first_state = True

        def receive_impact():
            nonlocal received_path, received_sensor, first_state
            for message in guest.take():
                if message["type"] != "state":
                    continue
                apply_snapshot(replica, message["snap"], guest.pid)
                if recon_ended:
                    assert not any(effect.props.get("sprite") == "sova_recon_bolt" for effect in replica.effects)
                    target = replica.players.get(victim.pid)
                    if rejoin == "destroyed_active" and first_state:
                        assert replica.time < reveal_expires
                    first_state = False
                    if rejoin == "destroyed_active" and replica.time < reveal_expires:
                        assert target is not None
                        assert target.revealed_until == pytest.approx(reveal_expires)
                    else:
                        assert target is None or target.revealed_until <= replica.time
                    if recon_destroyed:
                        return replica.time > sensor.start + 2.4
                    return True
                if rejoin == "flight" and first_state:
                    [in_flight] = [effect for effect in replica.effects if effect.props.get("bolt_path")]
                    assert replica.time < new_impact
                    assert in_flight.start == pytest.approx(bolt.start)
                    assert in_flight.until == pytest.approx(new_impact)
                    assert in_flight.props["bolt_path"] == [list(point) for point in bolt.props["bolt_path"]]
                if rejoin == "impact":
                    assert not any(effect.props.get("bolt_path") for effect in replica.effects)
                    if first_state and slot == "E":
                        assert any(effect.kind == "sensor" and effect.pos == bolt.pos for effect in replica.effects)
                first_state = False
                for effect in replica.effects:
                    if effect.props.get("bolt_path") and effect.until == pytest.approx(new_impact):
                        received_path = True
                    if effect.kind == "sensor" and effect.props.get("sprite") == "sova_recon_bolt":
                        assert new_impact <= effect.start < new_impact + dt
                        assert effect.pos == bolt.pos
                        received_sensor = True
                target = replica.players.get(victim.pid)
                if slot == "Q" and target is not None and target.hp < health:
                    assert new_impact <= replica.time < new_impact + 0.12
                    assert target.hp == victim.hp
                    assert not any(e.props.get("bolt_path") for e in replica.effects)
                    return True
                if target is not None and target.revealed_until > replica.time:
                    assert replica.time >= new_impact + 0.67
                    assert replica.time < new_impact + 0.8
                    return True
            return False

        _wait(receive_impact, session)
        if recon_ended:
            return
        assert received_path == (rejoin != "impact")
        if slot == "E":
            assert received_sensor
    finally:
        guest.close()


@pytest.mark.parametrize(("in_front", "repeat"), [
    (False, None), (True, None), (True, "hit"), (True, "miss"), (True, "rejoin"),
    (True, "rejoin_expired"),
])
def test_hunters_fury_guest_only_takes_hit_in_front_of_sova(session, monkeypatch, in_front, repeat):
    from gameplay.geometry import Vec
    from gameplay.world import WorldMap

    match = session.match
    target_pos = Vec(10, 10.5 if in_front else 9.5)
    match.world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [target_pos]})
    sova = match.add_player("Sova host", 0, "sova")
    guest = NetClient(f"127.0.0.1:{session.net.port}", "Target guest", "omen")
    try:
        assert session.net.choose_team(guest.pid, 1)
        assert session.start(team_size=1)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match.phase, match.phase_until = "live", match.time + 60
        sova.ult_points = 8
        target = match.players[guest.pid]
        target.dummy = True
        if repeat:
            target.hp = 200
        health = target.hp
        expected_hp = health
        dt = 1 / 64
        session.step(dt, {sova.pid: Command(ability="X", facing=0)})
        [beam] = [e for e in match.effects if e.props.get("sprite") == "sova_hunters_fury"]
        replica = Match(match.world)

        def received_impact():
            for message in guest.take():
                if message["type"] != "state":
                    continue
                apply_snapshot(replica, message["snap"], guest.pid)
                if not beam.start <= replica.time < beam.until:
                    continue
                victim = replica.players[guest.pid]
                assert victim.hp == expected_hp
                assert (victim.revealed_until > replica.time) is in_front
                return True
            return False

        while match.time < beam.start:
            session.step(dt)
        expected_hp = target.hp
        assert expected_hp == health - (80 if in_front else 0)
        _wait(received_impact, session)
        if in_front:
            expires = target.revealed_until
            assert replica.players[guest.pid].revealed_until == pytest.approx(expires)
            assert beam.start + 1 <= expires < beam.start + 1 + dt
            if repeat:
                second_hit = repeat != "miss"
                while match.time + dt < sova.repeat_next:
                    session.step(dt)
                session.step(dt, {sova.pid: Command(ability="X", facing=0 if second_hit else 180)})
                beam = max((e for e in match.effects if e.props.get("sprite") == "sova_hunters_fury"),
                           key=lambda e: e.start)
                while match.time < beam.start:
                    session.step(dt)
                previous_hp = expected_hp
                expected_hp = target.hp
                assert expected_hp == previous_hp - (80 if second_hit else 0)
                assert match.time < expires
                if second_hit:
                    assert expires < target.revealed_until
                    expires = target.revealed_until
                    assert beam.start + 1 <= expires < beam.start + 1 + dt
                else:
                    assert target.revealed_until == pytest.approx(expires)
                _wait(received_impact, session)
                assert replica.players[guest.pid].revealed_until == pytest.approx(expires)

            if repeat in ("rejoin", "rejoin_expired"):
                pid, token = guest.pid, guest.token
                guest.close()
                _wait(lambda: target.is_bot, session)
                if repeat == "rejoin_expired":
                    while match.time < expires:
                        session.step(dt)
                guest = NetClient(f"127.0.0.1:{session.net.port}", "Target guest", "omen", token=token)
                assert guest.pid == pid and guest.rejoined
                replica = Match(match.world)

                def received_first_state():
                    for message in guest.take():
                        if message["type"] == "state":
                            apply_snapshot(replica, message["snap"], pid)
                            if repeat == "rejoin_expired":
                                assert replica.time >= expires
                                assert replica.players[pid].revealed_until == 0
                            else:
                                assert replica.time < expires
                                assert replica.players[pid].revealed_until == pytest.approx(expires)
                            assert replica.players[pid].hp == expected_hp
                            return True
                    return False

                _wait(received_first_state, session)

            def received_expiry():
                for message in guest.take():
                    if message["type"] != "state":
                        continue
                    apply_snapshot(replica, message["snap"], guest.pid)
                    victim = replica.players[guest.pid]
                    assert victim.hp == expected_hp
                    if replica.time < expires:
                        assert victim.revealed_until == pytest.approx(expires)
                        continue
                    assert victim.revealed_until <= replica.time < expires + 0.12
                    return True
                return False

            _wait(received_expiry, session)
    finally:
        guest.close()


@pytest.mark.parametrize("use_all_shots", [False, True])
def test_hunters_fury_guest_hud_stops_when_recast_ends(session, monkeypatch, use_all_shots):
    from client.game import Game
    from test_client import args

    match = session.match
    guest = NetClient(f"127.0.0.1:{session.net.port}", "Sova guest", "sova")
    try:
        assert session.net.choose_team(guest.pid, 0)
        assert session.start(team_size=1)
        monkeypatch.setattr(session.bots, "commands", lambda dt: {})
        match.phase, match.phase_until = "live", match.time + 60
        sova = match.players[guest.pid]
        sova.ult_points = 8
        game = Game(args(agent="sova"))
        replica = Match(match.world)
        game.match, game.me = replica, guest.pid
        hints = []
        monkeypatch.setattr(game, "ability_hint", lambda label, color: hints.append(label))
        guest.send(Command(ability="X", facing=0))
        _wait(lambda: sova.repeat_shots == 2, session)
        deadline = sova.repeat_until
        saw_ready = False

        def received_deadline():
            nonlocal saw_ready
            for message in guest.take():
                if message["type"] != "state":
                    continue
                apply_snapshot(replica, message["snap"], guest.pid)
                pilot = replica.players[guest.pid]
                if pilot.repeat_until != deadline:
                    continue
                hints.clear()
                game.draw_aim_preview(pilot, "X")
                if pilot.repeat_shots and pilot.repeat_next <= replica.time < deadline:
                    assert game.ability_ready(pilot, "X")
                    assert hints and f"{pilot.repeat_shots} left" in hints[-1] and "Left click fires" in hints[-1]
                    saw_ready = True
                elif not pilot.repeat_shots or replica.time >= deadline:
                    assert saw_ready
                    assert (replica.time < deadline) is use_all_shots
                    assert not game.ability_ready(pilot, "X") and not hints
                    return True
            return False

        if use_all_shots:
            dt = 1 / 64
            def received_ready():
                received_deadline()
                return saw_ready

            _wait(received_ready, session)
            for remaining in (1, 0):
                _wait(lambda: match.time + dt >= sova.repeat_next and sova.prev_ability is None, session)
                session.step(dt, {sova.pid: Command(ability="X", facing=180)})
                assert sova.repeat_shots == remaining
        _wait(received_deadline, session)
    finally:
        guest.close()


def test_rejoin_by_name_after_restart(session: HostSession) -> None:
    client = NetClient(f"127.0.0.1:{session.net.port}", "Restarter", "omen")
    pid = client.pid
    _wait(lambda: pid in session.match.players, session)
    session.start(team_size=1)
    client.close()
    _wait(lambda: session.match.players[pid].is_bot, session)
    back = NetClient(f"127.0.0.1:{session.net.port}", "Restarter", "omen")
    try:
        assert back.pid == pid
    finally:
        back.close()
