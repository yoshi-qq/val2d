import pytest

from gameplay.geometry import Rect, Vec
from gameplay.match import Command
from gameplay.netgame import NetClient
from gameplay.session import HostSession
from gameplay.world import Wall
from test_chamber import DT, advance, arena
from test_net import _free_port, _wait


@pytest.mark.parametrize("finish", ["timeout", "shot"])
def test_kayo_downed_death_sound_reaches_nearby_guest(finish):
    from client.common import Sound, pygame
    from client.events import EventsMixin
    from gameplay.net import events_from_json

    match = arena()
    host = match.add_player("KAY/O", 0, "kayo")
    session = HostSession(match, "Host", _free_port())
    try:
        guest = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
        try:
            assert session.net.choose_team(guest.pid, 1)
            assert session.start(team_size=2)
            for player in match.players.values():
                player.is_bot = False
            match.phase, match.phase_until = "live", 100
            enemy = match.players[guest.pid]
            host.pos, enemy.pos, enemy.facing = Vec(20, 20), Vec(20, 26), 180
            host.ult_points = match.ultimate_cost(host)
            session.step(DT, {host.pid: Command(ability="X")})
            match._damage(enemy, host, 200, "body", "vandal")
            deadline = host.passive_state["kayo_downed"][0]
            assert host.alive
            if finish == "shot":
                match._damage(enemy, host, 849, "body", "vandal")
                enemy.weapons["primary"] = match._new_weapon("operator")
                enemy.slot, enemy.equip_until, enemy.zoom_level = "primary", 0, 1
                session.step(DT, {enemy.pid: Command(fire=True, facing=180, cursor_depth=6)})
                assert not host.alive and match.time < deadline
            received = []
            state_time = 0

            def collect():
                nonlocal state_time
                for message in guest.take():
                    if message["type"] == "state":
                        state_time = message["snap"]["time"]
                    elif message["type"] == "events":
                        received.extend(e for e in events_from_json(message["events"])
                                        if e.kind == "sound_fx" and e.data.get("key") == "cast_electric")
                return state_time > deadline + 0.2 and bool(received)

            while match.time < deadline:
                session.step(DT)
            _wait(collect, session)
            assert not host.alive and host.deaths == 1
            [cue] = received
            assert cue.t == host.died_at
            if finish == "timeout":
                assert deadline <= cue.t <= deadline + DT
            else:
                assert cue.t < deadline
            assert Vec(*cue.data["pos"]) == host.pos
            audio = EventsMixin()
            audio.match, audio.me, audio.sound = match, guest.pid, Sound()
            pygame.mixer.stop()
            audio.handle_events([cue])
            assert pygame.mixer.get_busy()
            pygame.mixer.stop()
            enemy.pos = host.pos + Vec(0, 20)
            audio.handle_events([cue])
            assert not pygame.mixer.get_busy()
        finally:
            guest.close()
    finally:
        session.close()


def test_kayo_offline_selection_and_suppression_through_cover(tmp_path, monkeypatch):
    from client.game import Game
    from test_client import args

    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")
    game = Game(args(agent="kayo"))
    assert game.match.players[game.me].agent == "kayo"
    game.match.start()
    game.draw()
    match = arena()
    kayo = match.add_player("KAY/O", 0, "kayo")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    kayo.pos, enemy.pos = Vec(20, 20), Vec(20, 30)
    match.world.walls.append(Wall(Rect(17, 24, 23, 25), 3))
    match.tick(DT, {kayo.pid: Command(ability="E", facing=0, cursor_depth=10)})
    advance(match, 1.6)
    assert enemy.status["suppress"] > match.time + 7
    assert kayo.charges["E"] == 0
    advance(match, 49)
    assert kayo.charges["E"] == 1


def test_frag_and_underhand_flash():
    match = arena()
    kayo = match.add_player("KAY/O", 0, "kayo")
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", 100
    kayo.pos, enemy.pos = Vec(20, 20), Vec(20, 30)
    kayo.charges.update(C=1, Q=1)
    match.tick(DT, {kayo.pid: Command(ability="Q", ability_alt=True, facing=0, cursor_depth=14),
                    enemy.pid: Command(facing=180)})
    for _ in range(70):
        match.tick(DT, {enemy.pid: Command(facing=180)})
    assert enemy.blind_until > match.time + 2
    match.tick(DT, {kayo.pid: Command(ability="C", facing=0, cursor_depth=12.5)})
    advance(match, 1.1)
    assert enemy.hp == 40


def test_guest_stabilizes_downed_host():
    from unittest.mock import Mock

    from client.common import Sound, UiState, pygame
    from client.events import EventsMixin
    from gameplay.match import Match
    from gameplay.net import apply_snapshot, events_from_json

    match = arena()
    session = HostSession(match, "Host", _free_port())
    host = match.add_player("Host", 0, "kayo")
    try:
        client = NetClient(f"127.0.0.1:{session.net.port}", "Guest", "omen")
        opponent = None
        try:
            _wait(lambda: client.pid in match.players, session)
            client.choose_team(host.team)
            _wait(lambda: match.players[client.pid].team == host.team, session)
            opponent = NetClient(f"127.0.0.1:{session.net.port}", "Opponent", "omen")
            assert session.net.choose_team(opponent.pid, 1 - host.team)
            assert session.start(team_size=2)
            guest = match.players[client.pid]
            enemy = match.players[opponent.pid]
            for player in match.players.values():
                player.is_bot = False
            match.phase, match.phase_until = "live", 100
            host.pos, guest.pos, enemy.pos = Vec(20, 20), Vec(21, 20), Vec(20, 26)
            host.ult_points = 8
            session.step(DT, {host.pid: Command(ability="X")})
            enemy.weapons["primary"] = match._new_weapon("operator")
            enemy.slot, enemy.equip_until, enemy.zoom_level = "primary", 0, 1
            session.step(DT, {enemy.pid: Command(fire=True, facing=180, cursor_depth=6)})
            assert host.hp == 850 and host.alive and "kayo_downed" in host.status
            own_audio = EventsMixin()
            own_audio.match, own_audio.me, own_audio.sound = Match(match.world), host.pid, Sound()
            deadline = host.passive_state["kayo_downed"][0]
            assert "kayo_downed_until" not in next(
                row for row in match.snapshot(client.pid)["players"] if row["pid"] == host.pid
            )

            def own_gain():
                apply_snapshot(own_audio.match, match.snapshot(host.pid), host.pid)
                own_audio.update_audio_perspective(own_audio.match.players[host.pid])
                return own_audio.sound.perspective_gain

            assert own_gain() == 1.0
            while match.time < deadline - 2.5:
                session.step(DT)
            assert own_gain() == pytest.approx(0.625)
            pygame.mixer.stop()
            channel = own_audio.sound.play("cast_sonic")
            assert channel is not None and channel.get_busy()
            pygame.mixer.stop()
            ally_audio = EventsMixin()
            ally_audio.match, ally_audio.me = Match(match.world), client.pid
            ally_audio.ui, ally_audio.sound = UiState(), Sound()
            assert ally_audio.sound.ok
            cues = {client.pid: [], opponent.pid: []}
            announcements = {client.pid: [], opponent.pid: []}

            def collect():
                for guest in (client, opponent):
                    for message in guest.take():
                        if message["type"] == "events":
                            for event in events_from_json(message["events"]):
                                if event.kind == "sound_fx" and event.data.get("key") == "ab_revive":
                                    cues[guest.pid].append(event)
                                elif event.kind == "kayo_announcement":
                                    announcements[guest.pid].append(event)
                        elif message["type"] == "state":
                            snapshot = message["snap"]
                            if guest is client:
                                apply_snapshot(ally_audio.match, snapshot, client.pid)
                            else:
                                assert all(effect["kind"] != "kayo_stabilize" for effect in snapshot["effects"])
                listener = ally_audio.match.players.get(client.pid)
                ally_audio.update_kayo_stabilize_audio(listener)
                return bool(ally_audio.ui.kayo_stabilize_sounds)

            pygame.mixer.stop()
            client.send(Command(interact=True))
            _wait(lambda: collect() and all(cues.values()), session)
            paused_gain = own_gain()
            for _ in range(16):
                session.step(DT)
            assert own_gain() == pytest.approx(paused_gain)
            [channel] = ally_audio.ui.kayo_stabilize_sounds.values()
            assert channel.get_busy()
            client.send(Command())
            _wait(lambda: not collect(), session)
            assert not channel.get_busy()
            assert host.hp == 850
            client.send(Command(interact=True))
            _wait(collect, session)
            [channel] = ally_audio.ui.kayo_stabilize_sounds.values()
            _wait(lambda: host.hp == 100 and "kayo_downed" not in host.status, session)
            _wait(lambda: not collect() and all(len(events) == 2 for events in announcements.values()), session)
            assert all(len(events) == 2 for events in cues.values())
            assert not channel.get_busy()
            assert host.alive and host.channel_until > match.time
            assert "kayo_overload" not in host.status
            assert own_gain() == 1.0
            for recipient, keys in [(guest, ["cast_dark", "cast_buff"]), (enemy, ["cast_burst", "cast_beam"])]:
                audio = EventsMixin()
                audio.match, audio.me = match, recipient.pid
                audio.sound = Mock(wraps=ally_audio.sound)
                for event in announcements[recipient.pid]:
                    pygame.mixer.stop()
                    audio.handle_events([event])
                    assert pygame.mixer.get_busy()
                assert [call.args[0] for call in audio.sound.play.call_args_list] == keys
            pygame.mixer.stop()
        finally:
            if opponent is not None:
                opponent.close()
            client.close()
    finally:
        session.close()
