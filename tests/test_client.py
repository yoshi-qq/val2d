"""Headless smoke tests of the game client: menu, a local match drawn frame by frame, overlays."""
from __future__ import annotations

import argparse
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from client.game import Game  # noqa: E402
from gameplay.match import Command  # noqa: E402


def args(**over: object) -> argparse.Namespace:
    base = dict(agent="omen", team_size=2, rounds=13, map="ascent", all_around=False, sound_rings=False, name="Tester",
                host=False, host_online=False, join=None, find=False, port=9009, no_menu=True, practice=False,
                mode="standard", online=False)
    base.update(over)
    return argparse.Namespace(**base)


@pytest.fixture(autouse=True)
def settings_path(monkeypatch, tmp_path):
    monkeypatch.setattr("user_settings.SETTINGS_PATH", tmp_path / "settings.json")


def frames(game: Game, n: int) -> None:
    for _ in range(n):
        events = game.step(1 / 60, Command())
        game.handle_events(events)
        game.draw()


@pytest.mark.parametrize("action", ["plant", "defuse"])
def test_running_spike_sound_follows_listener_gain(action, monkeypatch) -> None:
    from types import SimpleNamespace
    from unittest.mock import Mock

    from client.common import Sound, UiState
    from client.events import EventsMixin
    from gameplay.geometry import Vec
    from gameplay.match import GameEvent

    listener = SimpleNamespace(alive=True, pos=Vec(0, -40), facing=0,
                               status={"kayo_downed": float("inf")},
                               passive_state={"kayo_downed_until": 15.0})
    audio = EventsMixin()
    audio.me, audio.ui, audio.sound = 1, UiState(), Sound()
    audio.match = SimpleNamespace(time=9.0, players={1: listener})
    monkeypatch.setattr(audio, "occluded", lambda *_: False)
    assert audio.sound.spatial_mix(listener, Vec(0, 5), 35, False, 1.0)[:2] == (0, 0)
    play = audio.sound.play
    monkeypatch.setattr(audio.sound, "play", Mock(side_effect=lambda *args, **kwargs: Mock(wraps=play(*args, **kwargs))))
    find_channel = pygame.mixer.find_channel
    monkeypatch.setattr(pygame.mixer, "find_channel", lambda: Mock(wraps=find_channel()))
    pygame.mixer.stop()
    audio.update_audio_perspective(listener)
    audio.handle_events([GameEvent(f"{action}_start", 9, {"pid": 2, "pos": (0, 5)})])
    pos, tracks = audio.ui.spike_sounds[2]
    (channel, sample, _), (filtered, filtered_sample, _) = tracks
    assert channel.get_sound() == sample
    audio.update_spike_audio(listener)
    assert channel.set_volume.call_args.args == (0, 0)
    listener.pos = Vec(0, 0)
    full_left, full_right, _ = audio.sound.spatial_mix(listener, pos, 35, False, 1.0)
    audio.match.time = 12.5
    audio.update_audio_perspective(listener)
    audio.update_spike_audio(listener)
    assert channel.set_volume.call_args.args == pytest.approx((full_left * 0.625, full_right * 0.625))
    assert channel.get_sound() == sample
    assert audio.sound.play.call_count == 1
    monkeypatch.setattr(audio, "occluded", lambda *_: True)
    audio.update_spike_audio(listener)
    assert channel.set_volume.call_args.args == (0, 0)
    left, right, _ = audio.sound.spatial_mix(listener, pos, 35, True, 1.0)
    assert filtered.set_volume.call_args.args == pytest.approx((left, right))
    monkeypatch.setattr(audio, "occluded", lambda *_: False)
    audio.update_spike_audio(listener)
    assert filtered.set_volume.call_args.args == (0, 0)
    assert channel.set_volume.call_args.args == pytest.approx((full_left * 0.625, full_right * 0.625))
    assert filtered.get_sound() == filtered_sample
    filtered.play.assert_called_once_with(filtered_sample)
    assert audio.sound.play.call_count == 1
    listener.pos = Vec(0, -40)
    audio.update_spike_audio(listener)
    assert channel.set_volume.call_args.args == (0, 0)
    listener.pos = Vec(0, 0)
    audio.update_spike_audio(listener)
    assert channel.set_volume.call_args.args == pytest.approx((full_left * 0.625, full_right * 0.625))
    assert audio.sound.play.call_count == 1
    audio.handle_events([GameEvent(f"{action}_stop", 12.5, {"pid": 2})])
    channel.stop.assert_called_once()
    filtered.stop.assert_called_once()
    assert not audio.ui.spike_sounds


def test_defuse_checkpoint_cues_follow_spectated_teammate(monkeypatch) -> None:
    from unittest.mock import Mock

    from gameplay.geometry import Vec
    from gameplay.match import GameEvent

    game = Game(args(team_size=3))
    game.match.start()
    game.match.phase = "planted"
    me = game.match.players[game.me]
    me.alive = False
    spike = Vec(20, 20)
    game.match.spike_pos = spike
    play = Mock()
    monkeypatch.setattr(game.sound, "play", play)
    first = game.view_player(me)
    game.spectate_index += 1
    second = game.view_player(me)
    assert first.pid != second.pid
    monkeypatch.setattr(game, "occluded", lambda player, pos: player.pid == second.pid)
    game.handle_events([GameEvent("defuse_half", 0, {"pid": me.pid, "pos": (20, 20)})],
                       spike_listener=first)
    game.handle_events([GameEvent("defuse_start", 0, {"pid": me.pid, "pos": (20, 20), "resumed": True})],
                       spike_listener=second)
    calls = [call for call in play.call_args_list if call.args[0] == "spike_defuse_half"]
    assert [(call.args[1], call.args[2], call.kwargs["occluded"]) for call in calls] == [
        (first, spike, False), (second, spike, True),
    ]


def test_spike_countdown_plays_grouped_spatial_beeps(monkeypatch) -> None:
    from gameplay.geometry import Vec

    game = Game(args(team_size=3))
    match = game.match
    match.start()
    me = match.players[game.me]
    near, far = sorted((p for p in match.players.values() if p.team == me.team and p is not me),
                       key=lambda p: p.pid)
    match.phase = "planted"
    match.spike_planted_at = 0
    match.spike_pos = Vec(8, 30)
    near.pos, far.pos = Vec(8, 25), Vec(8, 100)
    beeps = []
    listeners = {}
    monkeypatch.setattr(game, "occluded", lambda listener, _: listener.pid == far.pid)

    def play(key, listener=None, pos=None, radius=40, **kwargs):
        if key == "bomb_beep":
            assert pos == match.spike_pos and radius == 60
            assert kwargs["occluded"] == (listener.pid == far.pid)
            beeps.append(match.time)
            listeners[match.time] = listener.pid

    monkeypatch.setattr(game.sound, "play", play)
    for tick in range(2400, 4601):
        match.time = tick / 100
        if tick == 2500:
            me.alive = False
        if tick == 2510:
            game.spectate_index += 1
        game.audio_tick(me, spike_listener=game.view_player(me))
    assert beeps[:5] == [24.0, 25.0, 25.2, 26.0, 26.2]
    assert beeps[19:25] == [34.0, 34.2, 35.0, 35.2, 35.4, 36.0]
    assert beeps[-3:] == [44.0, 44.2, 44.4]
    assert [listeners[t] for t in (24.0, 25.0, 25.2)] == [me.pid, near.pid, far.pid]


@pytest.mark.parametrize("weapon", ["phantom", "spectre", "ghost", "vandal"])
def test_gunshot_audibility_in_local_match(monkeypatch, weapon) -> None:
    from types import SimpleNamespace

    from gameplay.geometry import Vec
    from gameplay.net import event_to_json, events_from_json
    from gameplay.netgame import NetHost

    game = Game(args(sound_rings=True))
    match = game.match
    match.start()
    match.phase, match.phase_until = "live", match.time + 60
    monkeypatch.setattr(game.bots, "commands", lambda dt: {})
    shooter = match.players[game.me]
    listener = next(p for p in match.players.values() if p.team != shooter.team)
    definition = match.weapons[weapon]
    shooter.pos = Vec(45, 45)
    shooter.slot = definition.slot
    shooter.weapons[definition.slot] = match._new_weapon(weapon, shooter)
    shooter.equip_until = 0
    events = game.step(1 / 64, Command(fire=True, facing=90))
    [shot] = [event for event in events if event.kind == "sound" and event.data.get("kind") == "shot"]
    [shot] = events_from_json([event_to_json(shot)])
    game.me = listener.pid
    origin = Vec(*shot.data["pos"])
    monkeypatch.setattr(game, "occluded", lambda player, pos: False)
    host = SimpleNamespace(match=match)
    for offset, expected in [
        (Vec(0, 20), True), (Vec(40, 0), True),
        (Vec(0, 40), not definition.silenced), (Vec(55, 0), definition.silenced),
        (Vec(50, 20), definition.silenced), (Vec(50, 30), False),
        (Vec(-55, 0), False), (Vec(0, 55), False), (Vec(81, 0), False),
    ]:
        listener.pos = origin + offset
        listener.facing = 270
        game.ui.rings.clear()
        pygame.mixer.stop()
        game.handle_events([shot])
        assert pygame.mixer.get_busy() == expected, offset
        if definition.silenced:
            assert NetHost._event_visible(host, listener, shot) == expected, offset
            assert bool(game.ui.rings) == expected, offset


@pytest.mark.parametrize("empowered,recast", [(True, False), (True, True), (False, False)])
def test_reyna_dismiss_exit_audio(monkeypatch, empowered, recast) -> None:
    from types import SimpleNamespace

    from gameplay.geometry import Vec
    from gameplay.net import event_to_json, events_from_json
    from gameplay.netgame import NetHost
    from gameplay.world import WorldMap

    game = Game(args(agent="reyna", team_size=3))
    match = game.match
    match.world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(90, 90)]})
    match.start()
    match.phase, match.phase_until = "live", match.time + 60
    reyna = match.players[game.me]
    ally = next(p for p in match.players.values() if p.team == reyna.team and p is not reyna)
    victim, enemy, distant = [p for p in match.players.values() if p.team != reyna.team]
    ally.pos, victim.pos, enemy.pos, distant.pos = Vec(20, 13), Vec(10, 16), Vec(25, 13), Vec(90, 90)
    if empowered:
        reyna.ult_points = match.ultimate_cost(reyna)
        match.tick(1 / 64, {reyna.pid: Command(ability="X")})
    victim.hp, reyna.equip_until = 1, 0
    match.tick(1 / 64, {reyna.pid: Command(fire=True, facing=0, cursor_depth=6)})
    started = match.tick(1 / 64, {reyna.pid: Command(ability="E")})
    assert reyna.status["dismiss"] > match.time
    assert not any(e.kind == "sound_fx" for e in started)
    exit_pos = Vec(20, 10)
    reyna.pos = exit_pos
    deadline = reyna.status["dismiss"]
    exit_events = []
    while match.time < deadline + 0.1:
        command = {reyna.pid: Command(ability="E")} if recast and match.time >= deadline - 1 else {}
        exit_events.extend(e for e in match.tick(1 / 64, command) if e.kind == "sound_fx")
        if command:
            recast = False
            deadline = match.time
    if not empowered:
        assert exit_events == []
        return
    [cue] = exit_events
    assert cue.t == pytest.approx(deadline, abs=1 / 64)
    assert cue.data["key"] == "cast_sonic" and Vec(*cue.data["pos"]) == exit_pos
    assert "cast_sonic" in game.sound.sounds
    host = SimpleNamespace(match=match)
    played = []
    monkeypatch.setattr(game.sound, "play", lambda key, *args, **kw: played.append((key, args)))
    for player in (reyna, ally, enemy, distant):
        game.me = player.pid
        received = events_from_json([event_to_json(cue)] if NetHost._event_visible(host, player, cue) else [])
        assert bool(received) == (player is not distant)
        for events in ([cue], received):
            game.handle_events(events)
            args_played = () if player is reyna else (player, exit_pos, 20.0)
            assert played == ([] if player is distant else [("cast_sonic", args_played)])
            played.clear()


def test_breach_flashpoint_warns_at_wall_exit_before_burst(monkeypatch) -> None:
    from types import SimpleNamespace

    from gameplay.geometry import Rect, Vec
    from gameplay.net import event_to_json, events_from_json
    from gameplay.netgame import NetHost
    from gameplay.world import Wall, WorldMap

    game = Game(args(agent="breach", team_size=3))
    match = game.match
    match.world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(90, 90)]})
    match.world.walls.append(Wall(Rect(5, 20, 15, 22), 3))
    match.start()
    match.phase, match.phase_until = "live", match.time + 60
    breach = match.players[game.me]
    breach.charges["Q"] = 1
    ally = next(p for p in match.players.values() if p.team == breach.team and p is not breach)
    enemy, distant, *_ = [p for p in match.players.values() if p.team != breach.team]
    ally.pos, enemy.pos, distant.pos = Vec(15, 25), Vec(10, 25), Vec(90, 90)
    cast = match.tick(1 / 64, {breach.pid: Command(ability="Q", facing=0)})
    [charge] = [e for e in match.effects if e.kind == "flash"]
    assert not any(e.kind == "sound_fx" for e in cast)
    events = []
    while match.time < charge.until + 0.1:
        events.extend(e for e in match.tick(1 / 64, {}) if e.kind in ("sound_fx", "flash"))
    warning, burst = events
    assert warning.kind == "sound_fx" and burst.kind == "flash"
    assert warning.t == pytest.approx(charge.start, abs=1 / 64)
    assert burst.t - warning.t == pytest.approx(0.5, abs=1 / 64)
    assert Vec(*warning.data["pos"]) == Vec(*burst.data["pos"]) == Vec(10, 22.05)
    host = SimpleNamespace(match=match)
    played = []
    monkeypatch.setattr(game.sound, "play", lambda key, *args, **kw: played.append(key))
    for player in (breach, ally, enemy, distant):
        game.me = player.pid
        received = events_from_json([event_to_json(warning)] if NetHost._event_visible(host, player, warning) else [])
        assert bool(received) == (player is not distant)
        for batch in ([warning], received):
            game.handle_events(batch)
            assert played == ([] if player is distant else ["cast_charge_up"])
            played.clear()


@pytest.mark.parametrize(("agent", "ally_key", "enemy_key"), [
    ("reyna", "ab_power", "cast_dark"),
    ("brimstone", "cast_tech", "cast_beam"),
    ("sage", "ab_revive", "cast_shield_up"),
    ("phoenix", "cast_fire", "cast_burst"),
    ("sova", "cast_sonic", "cast_electric"),
    ("jett", "cast_wind", "cast_ice"),
    ("omen", "cast_arcane", "cast_dark"),
    ("cypher", "ab_reveal", "cast_place_trap"),
    ("killjoy", "cast_tech", "ab_alarm"),
    ("waylay", "cast_buff", "cast_beam"),
    ("neon", "cast_electric", "cast_burst"),
    ("kayo", "cast_tech", "cast_electric"),
])
def test_ultimate_announcement_differs_by_team(monkeypatch, agent, ally_key, enemy_key) -> None:
    from types import SimpleNamespace

    from gameplay.geometry import Vec
    from gameplay.net import event_to_json, events_from_json
    from gameplay.netgame import NetHost
    from gameplay.world import WorldMap

    game = Game(args(agent=agent))
    match = game.match
    match.world = WorldMap("test", "Test", 120, 120, spawns={0: [Vec(10, 10)], 1: [Vec(110, 110)]})
    match.start()
    match.phase, match.phase_until = "live", match.time + 60
    caster = match.players[game.me]
    ally = next(p for p in match.players.values() if p.team == caster.team and p is not caster)
    enemy = next(p for p in match.players.values() if p.team != caster.team)
    ally.pos = enemy.pos = caster.pos + Vec(80, 0)
    caster.ult_points = match.ultimate_cost(caster)
    target = caster.pos + Vec(0, 8)
    command = Command(ability="X", points=[(target.x, target.y)]) if agent in ("brimstone", "omen") else Command(ability="X")
    if agent == "sage":
        fallen = match.add_player("Fallen", caster.team, "omen")
        fallen.pos, fallen.alive, fallen.hp = caster.pos + Vec(0, 4), False, 0
        command = Command(ability="X", facing=0, cursor_depth=4)
    elif agent == "cypher":
        corpse = match.add_player("Fallen enemy", enemy.team, "omen")
        corpse.pos, corpse.alive, corpse.hp = caster.pos + Vec(0, 4), False, 0
        command = Command(ability="X", facing=0, cursor_depth=4)
    events = match.tick(1 / 64, {caster.pid: command})
    [cast] = [e for e in events if e.kind == "ability"]
    assert cast.t == match.time and caster.ult_points == 0
    if agent == "brimstone":
        [strike] = [e for e in match.effects if e.props.get("sprite") == "brimstone_orbital_strike_beam"]
        assert strike.pos == target and strike.start > cast.t
    elif agent == "sage":
        [marker] = [e for e in match.effects if e.props.get("revive_pid") == fallen.pid]
        assert not fallen.alive and marker.until > cast.t
    elif agent == "phoenix":
        [marker] = [e for e in match.effects if e.props.get("sprite") == "phoenix_run_it_back_marker"]
        assert marker.pos == caster.pos and marker.start == cast.t
    elif agent == "sova":
        assert caster.repeat_shots == 2
    elif agent == "jett":
        assert caster.blades_equipped and caster.blade_count == 5
    elif agent == "omen":
        assert caster.channel_until > cast.t and caster.pos != target
    elif agent == "cypher":
        [hat] = [e for e in match.effects if e.props.get("sprite") == "cypher_neural_theft"]
        assert hat.pos == corpse.pos and hat.start == cast.t
    elif agent == "killjoy":
        [device] = [e for e in match.effects if e.props.get("sprite") == "killjoy_lockdown_pulse"]
        assert device.pos == caster.pos and device.start > cast.t
    elif agent == "neon":
        assert caster.overdrive_until > cast.t
    elif agent == "kayo":
        assert caster.status["kayo_overload"] > cast.t
        [windup] = [e for e in events if e.kind == "sound_fx"]
        assert windup.t == cast.t and windup.data["key"] == "cast_charge_up"
        assert Vec(*windup.data["pos"]) == caster.pos
    elif agent == "waylay":
        [windup] = [e for e in events if e.kind == "sound_fx"]
        assert windup.t == cast.t and windup.data["key"] == "cast_charge_up"
        assert Vec(*windup.data["pos"]) == caster.pos
    else:
        assert caster.status["empress"] > cast.t
    assert {ally_key, enemy_key} <= game.sound.sounds.keys()

    host = SimpleNamespace(match=match)
    played = []
    monkeypatch.setattr(game.sound, "play", lambda key, *args, **kw: played.append((key, args)))
    for viewer, key in [(caster, ally_key), (ally, ally_key), (enemy, enemy_key)]:
        game.me = viewer.pid
        assert NetHost._event_visible(host, viewer, cast)
        if agent in ("waylay", "kayo"):
            assert NetHost._event_visible(host, viewer, windup) == (viewer is caster)
        for batch in ([cast], events_from_json([event_to_json(cast)])):
            game.handle_events(batch)
            assert played == [(key, ())]
            played.clear()
    assert not any(e.kind == "ability" for e in match.tick(1 / 64, {}))
    if agent == "jett":
        for equipped in (False, True):
            events = match.tick(1 / 64, {caster.pid: command})
            assert caster.blades_equipped == equipped
            assert not any(e.data.get("cast_announcement") for e in events)
            match.tick(1 / 64, {})
    if agent == "sova":
        game.me = caster.pid
        for _ in range(2):
            while match.time < caster.repeat_next:
                match.tick(1 / 64, {})
            [shot] = [e for e in match.tick(1 / 64, {caster.pid: command}) if e.kind == "ability"]
            assert "cast_announcement" not in shot.data
            game.handle_events(events_from_json([event_to_json(shot)]))
            assert len(played) == 1 and played[0][1][0] is caster
            played.clear()
        assert caster.repeat_shots == 0


def test_omen_ultimate_arrival_audio_is_spatial(monkeypatch) -> None:
    from types import SimpleNamespace

    from gameplay.geometry import Vec
    from gameplay.net import event_to_json, events_from_json
    from gameplay.netgame import NetHost
    from gameplay.world import WorldMap

    game = Game(args(agent="omen"))
    match = game.match
    match.world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(90, 90)]})
    match.start()
    match.phase, match.phase_until = "live", match.time + 60
    omen = match.players[game.me]
    omen.ult_points = match.ultimate_cost(omen)
    ally = next(p for p in match.players.values() if p.team == omen.team and p is not omen)
    enemy, distant = [p for p in match.players.values() if p.team != omen.team]
    ally.pos, enemy.pos, distant.pos = Vec(56, 50), Vec(50, 56), Vec(73, 50)
    target = Vec(50, 50)
    cast = match.tick(1 / 64, {omen.pid: Command(ability="X", points=[(target.x, target.y)])})
    assert any(e.data.get("cast_announcement") for e in cast)
    assert not any(e.kind == "sound_fx" for e in cast)
    for _ in range(95):
        assert not any(e.kind == "sound_fx" for e in match.tick(1 / 64, {}))
    [cue] = [e for e in match.tick(1 / 64, {}) if e.kind == "sound_fx"]
    assert omen.pos == target and omen.status["omen_shade"] > cue.t
    assert Vec(*cue.data["pos"]) == target and cue.data["radius"] == 22.5

    host = SimpleNamespace(match=match)
    played = []
    monkeypatch.setattr(game.sound, "play", lambda key, *args, **kw: played.append((key, args)))
    for viewer in (omen, ally, enemy, distant):
        game.me = viewer.pid
        received = events_from_json([event_to_json(cue)] if NetHost._event_visible(host, viewer, cue) else [])
        assert bool(received) == (viewer is not distant)
        for batch in ([cue], received):
            game.handle_events(batch)
            args_played = () if viewer is omen else (viewer, target, 22.5)
            assert played == ([] if viewer is distant else [("ab_teleport", args_played)])
            played.clear()
    for _ in range(161):
        assert not any(e.kind == "sound_fx" for e in match.tick(1 / 64, {}))


def test_orbital_strike_spatial_cues_follow_target_and_activation(monkeypatch) -> None:
    from types import SimpleNamespace

    from gameplay.geometry import Vec
    from gameplay.net import event_to_json, events_from_json
    from gameplay.netgame import NetHost
    from gameplay.world import WorldMap

    game = Game(args(agent="brimstone", team_size=3))
    match = game.match
    match.world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(90, 90)]})
    match.start()
    match.phase, match.phase_until = "live", match.time + 60
    caster = match.players[game.me]
    caster.ult_points = match.ultimate_cost(caster)
    ally = next(p for p in match.players.values() if p.team == caster.team and p is not caster)
    enemy, far_enemy, *_ = [p for p in match.players.values() if p.team != caster.team]
    target = Vec(50, 10)
    ally.pos, enemy.pos, far_enemy.pos = Vec(55, 10), Vec(46, 10), Vec(90, 90)
    initial = match.tick(1 / 64, {caster.pid: Command(ability="X", points=[(target.x, target.y)])})
    [windup] = [e for e in initial if e.kind == "sound_fx"]
    [announcement] = [e for e in initial if e.kind == "ability"]
    [strike] = match.effects
    assert windup.t == announcement.t < strike.start
    cues = []
    while match.time < strike.start + 0.1:
        cues.extend(e for e in match.tick(1 / 64, {}) if e.kind == "sound_fx")
    [activation] = cues
    assert activation.t == pytest.approx(strike.start, abs=1 / 64)

    host = SimpleNamespace(match=match)
    played = []
    monkeypatch.setattr(game.sound, "play", lambda key, *args, **kw: played.append((key, args)))
    for cue, key in [(windup, "cast_charge_up"), (activation, "ab_blast")]:
        assert cue.data["key"] == key and Vec(*cue.data["pos"]) == target
        for viewer in (caster, ally, enemy, far_enemy):
            game.me = viewer.pid
            audible = viewer in (ally, enemy)
            received = events_from_json([event_to_json(cue)] if NetHost._event_visible(host, viewer, cue) else [])
            assert bool(received) == audible
            for batch in ([cue], received):
                game.handle_events(batch)
                assert played == ([(key, (viewer, target, 28.0))] if audible else [])
                played.clear()


def test_rolling_thunder_announcement_precedes_quake_and_differs_by_team(monkeypatch) -> None:
    from types import SimpleNamespace

    from gameplay.geometry import Vec
    from gameplay.net import event_to_json, events_from_json
    from gameplay.netgame import NetHost
    from gameplay.world import WorldMap

    game = Game(args(agent="breach", team_size=3))
    match = game.match
    match.world = WorldMap("test", "Test", 150, 150, spawns={0: [Vec(10, 10)], 1: [Vec(140, 140)]})
    match.start()
    match.phase, match.phase_until = "live", match.time + 60
    breach = match.players[game.me]
    breach.pos = Vec(10, 10)
    breach.ult_points = match.ultimate_cost(breach)
    ally = next(p for p in match.players.values() if p.team == breach.team and p is not breach)
    ally.pos = Vec(130, 130)
    victim, far_enemy, *_ = [p for p in match.players.values() if p.team != breach.team]
    victim.pos, far_enemy.pos = Vec(10, 20), Vec(140, 140)

    events = match.tick(1 / 64, {breach.pid: Command(ability="X", facing=0)})
    [cast] = [e for e in events if e.kind == "ability"]
    assert cast.t == match.time
    assert not victim.status.get("concuss")
    assert {"ult_cast", "cast_earth"} <= game.sound.sounds.keys()
    host = SimpleNamespace(match=match)
    played = []
    monkeypatch.setattr(game.sound, "play", lambda key, *args, **kw: played.append((key, args)))
    for viewer, key in [(breach, "ult_cast"), (ally, "ult_cast"),
                        (victim, "cast_earth"), (far_enemy, "cast_earth")]:
        game.me = viewer.pid
        assert NetHost._event_visible(host, viewer, cast)
        for batch in ([cast], events_from_json([event_to_json(cast)])):
            game.handle_events(batch)
            assert played == [(key, ())]
            played.clear()
    for _ in range(78):
        tick_events = match.tick(1 / 64, {})
        assert not any(e.data.get("cast_announcement") for e in tick_events)
    assert victim.status["concuss"] > match.time


@pytest.mark.parametrize(("agent", "pool_sprite"), [
    ("brimstone", "brimstone_incendiary_burning"),
    ("phoenix", "phoenix_hot_hands_pool"),
])
def test_fire_pool_audio_follows_each_field_in_team_snapshots(agent, pool_sprite) -> None:
    from gameplay.geometry import Vec
    from gameplay.match import Effect
    from gameplay.net import apply_snapshot
    from gameplay.world import WorldMap

    game = Game(args(agent=agent, team_size=3))
    host = game.match
    host.world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(90, 90)]})
    host.start()
    host.phase, host.phase_until = "live", host.time + 60
    caster = host.players[game.me]
    ally = next(p for p in host.players.values() if p.team == caster.team and p is not caster)
    enemy, distant, *_ = [p for p in host.players.values() if p.team != caster.team]
    ally.pos, enemy.pos, distant.pos = Vec(15, 17), Vec(16, 16), Vec(90, 90)
    caster.charges["Q"] = 2
    host.tick(1 / 64, {caster.pid: Command(ability="Q", facing=0, cursor_depth=6)})
    game.update_incendiary_audio(ally)
    assert not game.ui.fire_sounds
    for _ in range(64):
        host.tick(1 / 64, {})
    host.tick(1 / 64, {caster.pid: Command(ability="Q", facing=90, cursor_depth=6)})
    fields = lambda: sorted((e for e in host.effects if e.props.get("sprite") == pool_sprite),
                            key=lambda e: e.until)
    [first] = fields()
    host.effects.append(Effect("smoke", caster.pid, caster.team, first.pos, host.time + 10, radius=4))
    assert not game.occluded(ally, first.pos)
    replica = type(host)(host.world, host.cfg, agent_roster=host.agents)
    game.match = replica

    def check(viewer, expected):
        apply_snapshot(replica, host.snapshot(viewer.pid), viewer.pid)
        game.update_incendiary_audio(replica.players[viewer.pid])
        assert len(game.ui.fire_sounds) == expected
        assert all(ch.get_busy() for ch in game.ui.fire_sounds.values())

    for viewer, expected in [(ally, 1), (enemy, 1), (distant, 0)]:
        check(viewer, expected)
        game.update_incendiary_audio(None)
    while len(fields()) < 2:
        host.tick(1 / 64, {})
    check(ally, 2)
    channels = dict(game.ui.fire_sounds)
    check(ally, 2)
    assert game.ui.fire_sounds == channels
    while host.time < first.until:
        host.tick(1 / 64, {})
    check(ally, 1)
    assert not next(ch for identity, ch in channels.items() if identity[1] == first.pos).get_busy()
    while fields():
        host.tick(1 / 64, {})
    check(ally, 0)


@pytest.mark.parametrize(("agent", "slot"), [("sova", "C"), ("reyna", "C")])
def test_device_hit_audio_is_private_to_shooter(monkeypatch, agent, slot) -> None:
    from types import SimpleNamespace

    from gameplay.geometry import Vec
    from gameplay.net import event_to_json, events_from_json
    from gameplay.netgame import NetHost
    from gameplay.world import WorldMap

    game = Game(args(agent=agent))
    match = game.match
    match.world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(90, 90)]})
    match.start()
    match.phase, match.phase_until = "live", match.time + 60
    owner = match.players[game.me]
    shooter = next(p for p in match.players.values() if p.team != owner.team)
    owner.charges[slot] = 1
    match.tick(1 / 64, {owner.pid: Command(ability=slot, facing=0)})
    for _ in range(35):
        match.tick(1 / 64, {})
    [device] = [e for e in match.effects if e.props.get("hit_sound")]
    shooter.pos, shooter.equip_until = device.pos - Vec(5, 0), 0
    hp = device.data["hp"]
    miss = match.tick(1 / 64, {shooter.pid: Command(fire=True, facing=270)})
    assert not any(e.kind == "device_hit_audio" for e in miss)
    match.tick(1 / 64, {})
    shooter.next_shot = 0
    hit = match.tick(1 / 64, {shooter.pid: Command(fire=True, facing=90)})
    [cue] = [e for e in hit if e.kind == "device_hit_audio"]
    assert device.data["hp"] < hp and cue.t == match.time
    host = SimpleNamespace(match=match)
    played = []
    monkeypatch.setattr(game.sound, "play", lambda key, *args, **kw: played.append((key, args)))
    for viewer in match.players.values():
        game.me = viewer.pid
        received = events_from_json([event_to_json(cue)] if NetHost._event_visible(host, viewer, cue) else [])
        assert bool(received) == (viewer is shooter)
        for batch in ([cue], received):
            game.handle_events(batch)
            assert played == ([("hit_body", ())] if viewer is shooter else [])
            played.clear()


@pytest.mark.parametrize(("destroyed", "expected_count"), [(True, 0), (False, 0), (False, 1), (False, 2)])
def test_lockdown_warning_tracks_enemy_range_and_windup(destroyed, expected_count, monkeypatch) -> None:
    from types import SimpleNamespace
    from gameplay.geometry import Vec
    from gameplay.kit.engine import remove_device
    from gameplay.net import apply_snapshot, event_to_json, events_from_json
    from gameplay.netgame import NetHost
    from gameplay.world import WorldMap

    game = Game(args(agent="killjoy"))
    host = game.match
    host.world = WorldMap("test", "Test", 120, 120, spawns={0: [Vec(50, 50)], 1: [Vec(100, 100)]})
    host.start()
    host.phase, host.phase_until = "live", host.time + 60
    caster = host.players[game.me]
    ally = next(p for p in host.players.values() if p.team == caster.team and p is not caster)
    enemy, other_enemy = [p for p in host.players.values() if p.team != caster.team]
    caster.ult_points = host.ultimate_cost(caster)
    host.tick(1 / 64, {caster.pid: Command(ability="X")})
    [device] = [e for e in host.effects if e.props.get("sprite") == "killjoy_lockdown_pulse"]
    ally.pos = device.pos + Vec(0, 4)
    enemy.pos = device.pos + Vec(device.radius + 1, 0)
    game.match = type(host)(host.world, host.cfg, agent_roster=host.agents)

    def update(viewer):
        apply_snapshot(game.match, host.snapshot(viewer.pid), viewer.pid)
        game.update_lockdown_audio(game.match.players[viewer.pid])

    for viewer in (caster, ally, enemy):
        update(viewer)
        assert not game.ui.lockdown_sounds
    enemy.pos = device.pos + Vec(device.radius - 0.1, 0)
    update(enemy)
    [channel] = game.ui.lockdown_sounds.values()
    assert channel.get_busy()
    enemy.pos = device.pos + Vec(device.radius + 1, 0)
    update(enemy)
    assert not game.ui.lockdown_sounds and not channel.get_busy()
    enemy.pos = device.pos + Vec(3, 0)
    update(enemy)
    [channel] = game.ui.lockdown_sounds.values()
    if destroyed:
        remove_device(host, device, "destroy")
    else:
        if expected_count == 0:
            enemy.pos = device.pos + Vec(device.radius + 1, 0)
        if expected_count == 2:
            other_enemy.pos = device.pos + Vec(0, 5)
        while host.time < device.start:
            host.tick(1 / 64, {})
        assert device in host.effects
    update(enemy)
    assert not game.ui.lockdown_sounds and not channel.get_busy()

    if destroyed:
        remove_device(host, device, "destroy")
        [cue] = [e for e in host.events if e.kind == "lockdown_destroyed"]
        played = []
        monkeypatch.setattr(game.sound, "play", lambda key: played.append(key))
        for viewer in (caster, ally, enemy):
            game.me = viewer.pid
            apply_snapshot(game.match, host.snapshot(viewer.pid), viewer.pid)
            allowed = NetHost._event_visible(SimpleNamespace(match=host), viewer, cue)
            assert allowed == (viewer is not enemy)
            for batch in ([cue], events_from_json([event_to_json(cue)] if allowed else [])):
                game.handle_events(batch)
                assert played == ([] if viewer is enemy else ["cast_burst"])
                played.clear()
    else:
        assert not any(e.kind == "lockdown_destroyed" for e in host.events)
        [cue] = [e for e in host.events if e.kind == "lockdown_result"]
        assert cue.data["count"] == expected_count
        assert sum(p.status.get("detain", 0) > host.time for p in (enemy, other_enemy)) == expected_count
        played = []
        monkeypatch.setattr(game.sound, "play", lambda key: played.append(key))
        for viewer in (caster, ally, enemy):
            game.me = viewer.pid
            apply_snapshot(game.match, host.snapshot(viewer.pid), viewer.pid)
            allowed = NetHost._event_visible(SimpleNamespace(match=host), viewer, cue)
            assert allowed == (viewer is not enemy)
            game.handle_events(events_from_json([event_to_json(cue)] if allowed else []))
            expected = "ui_click" if expected_count == 0 else f"kill_{expected_count}"
            assert played == ([] if viewer is enemy else [expected])
            played.clear()


def test_owl_rotor_follows_drone_until_destroyed(monkeypatch) -> None:
    from gameplay.geometry import Vec
    from gameplay.net import apply_snapshot
    from gameplay.world import WorldMap

    game = Game(args(agent="sova"))
    host = game.match
    host.world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(90, 90)]})
    host.start()
    host.phase, host.phase_until = "live", host.time + 60
    caster = host.players[game.me]
    ally = next(p for p in host.players.values() if p.team == caster.team and p is not caster)
    enemy, distant = [p for p in host.players.values() if p.team != caster.team]
    ally.pos, enemy.pos, distant.pos = Vec(10, 18), Vec(10, 20), Vec(90, 90)
    caster.charges["C"] = 1
    host.tick(1 / 64, {caster.pid: Command(ability="C", facing=0)})
    [drone] = [e for e in host.effects if e.props.get("sprite") == "sova_owl_drone"]
    game.match = type(host)(host.world, host.cfg, agent_roster=host.agents)
    positions = []
    original = game.sound.spatial_mix

    def mix(listener, pos, radius, occluded, gain, **kwargs):
        positions.append(pos)
        return original(listener, pos, radius, occluded, gain, **kwargs)

    monkeypatch.setattr(game.sound, "spatial_mix", mix)

    def update(viewer):
        apply_snapshot(game.match, host.snapshot(viewer.pid), viewer.pid)
        game.update_rotor_audio(game.match.players[viewer.pid])

    update(ally)
    assert not game.ui.rotor_sounds
    for _ in range(16):
        host.tick(1 / 64, {})
    for viewer, expected in [(enemy, 1), (distant, 0), (ally, 1)]:
        update(viewer)
        assert len(game.ui.rotor_sounds) == expected
        assert positions[-1] == drone.pos
    [channel] = game.ui.rotor_sounds.values()
    origin = drone.pos
    for _ in range(16):
        host.tick(1 / 64, {caster.pid: Command(move_y=1, facing=0)})
    update(ally)
    assert drone.pos != origin and positions[-1] == drone.pos
    assert list(game.ui.rotor_sounds.values()) == [channel]

    enemy.pos, enemy.equip_until = drone.pos - Vec(5, 0), 0
    drone.data["hp"] = 1
    host.tick(1 / 64, {enemy.pid: Command(fire=True, facing=90)})
    assert drone.props.get("ended")
    update(ally)
    assert not game.ui.rotor_sounds and not channel.get_busy()


def test_owl_drone_warning_follows_only_spotted_guest() -> None:
    from gameplay.geometry import Vec
    from gameplay.net import apply_snapshot
    from gameplay.world import WorldMap

    game = Game(args(agent="sova", team_size=3))
    host = game.match
    host.world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(90, 90)]})
    host.start()
    host.phase, host.phase_until = "live", host.time + 60
    caster = host.players[game.me]
    ally = next(p for p in host.players.values() if p.team == caster.team and p is not caster)
    spotted, distant, *_ = [p for p in host.players.values() if p.team != caster.team]
    ally.pos, spotted.pos, distant.pos = Vec(11, 14), Vec(10, 15), Vec(90, 90)
    caster.charges["C"] = 1
    host.tick(1 / 64, {caster.pid: Command(ability="C", facing=0)})
    for _ in range(16):
        host.tick(1 / 64, {})
    host.tick(1 / 64, {caster.pid: Command(fire=True, facing=0)})
    assert spotted.status["owl_drone_spotted"] > host.time
    assert spotted.passive_state["owl_drone_spotted_at"] == host.time
    game.match = type(host)(host.world, host.cfg, agent_roster=host.agents)
    for viewer in (caster, ally, distant, spotted):
        apply_snapshot(game.match, host.snapshot(viewer.pid), viewer.pid)
        game.update_drone_warning(game.match.players[viewer.pid])
        assert (game.ui.drone_warning is not None) == (viewer is spotted)
    channel = game.ui.drone_warning
    assert channel.get_busy()
    spotted.pos = Vec(80, 80)
    for _ in range(270):
        host.tick(1 / 64, {})
    apply_snapshot(game.match, host.snapshot(spotted.pid), spotted.pid)
    game.update_drone_warning(game.match.players[spotted.pid])
    assert game.ui.drone_warning is None and not channel.get_busy()


def test_recon_flight_audio_follows_each_arrow_in_team_snapshots(monkeypatch) -> None:
    from types import SimpleNamespace

    from gameplay.geometry import Vec
    from gameplay.net import apply_snapshot, event_to_json, events_from_json
    from gameplay.netgame import NetHost
    from gameplay.world import WorldMap

    game = Game(args(agent="sova", team_size=3))
    host = game.match
    host.world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(90, 90)]})
    host.start()
    host.phase, host.phase_until = "live", host.time + 60
    caster = host.players[game.me]
    second = host.add_player("Second Sova", caster.team, "sova")
    second.pos, second.charges["E"] = Vec(12, 10), 1
    ally, *_ = [p for p in host.players.values() if p.team == caster.team and p is not caster]
    enemy, distant, *_ = [p for p in host.players.values() if p.team != caster.team]
    ally.pos, enemy.pos, distant.pos = Vec(16, 16), Vec(17, 16), Vec(90, 90)
    commands = {caster.pid: Command(ability="E", facing=0, cursor_depth=16),
                second.pid: Command(ability="E", facing=0, cursor_depth=16)}
    host.tick(1 / 64, commands)
    assert len([e for e in host.effects if e.kind == "blast"]) == 2
    replica = type(host)(host.world, host.cfg, agent_roster=host.agents)
    game.match = replica
    positions = []
    original = game.sound.spatial_mix

    def mix(listener, pos, radius, occluded, gain, **kwargs):
        positions.append(pos)
        return original(listener, pos, radius, occluded, gain, **kwargs)

    monkeypatch.setattr(game.sound, "spatial_mix", mix)
    for viewer, expected in [(ally, 2), (enemy, 2), (distant, 0)]:
        apply_snapshot(replica, host.snapshot(viewer.pid), viewer.pid)
        game.update_recon_audio(replica.players[viewer.pid])
        assert len(game.ui.recon_sounds) == expected
        game.update_recon_audio(None)
    assert Vec(10, 10) in positions and Vec(12, 10) in positions
    for _ in range(12):
        host.tick(1 / 64, {})
    positions.clear()
    apply_snapshot(replica, host.snapshot(ally.pid), ally.pid)
    game.update_recon_audio(replica.players[ally.pid])
    assert {p.x for p in positions} == {10, 12}
    assert all(p.y > 10 for p in positions)
    channels = list(game.ui.recon_sounds.values())
    arrival = max(e.until for e in host.effects if e.kind == "blast")
    destinations = {e.pos for e in host.effects if e.kind == "blast"}
    impacts = []
    while host.time < arrival:
        impacts.extend(e for e in host.tick(1 / 64, {}) if e.kind == "sound_fx")
    assert len(impacts) == 2
    assert {Vec(*e.data["pos"]) for e in impacts} == destinations
    assert all(e.t == pytest.approx(arrival, abs=1 / 64) for e in impacts)
    assert sum(e.kind == "sensor" for e in host.effects) == 2
    apply_snapshot(replica, host.snapshot(ally.pid), ally.pid)
    game.update_recon_audio(replica.players[ally.pid])
    assert not game.ui.recon_sounds and not any(ch.get_busy() for ch in channels)
    played = []
    monkeypatch.setattr(game.sound, "play", lambda key, *args, **kwargs: played.append((key, args[1])))
    net = SimpleNamespace(match=host)
    for viewer, audible in [(ally, True), (enemy, True), (distant, False)]:
        game.me = viewer.pid
        apply_snapshot(replica, host.snapshot(viewer.pid), viewer.pid)
        received = events_from_json([event_to_json(e) for e in impacts if NetHost._event_visible(net, viewer, e)])
        assert len(received) == (2 if audible else 0)
        for batch in (impacts, received):
            game.handle_events(batch)
            assert played == ([("cast_place_trap", Vec(*e.data["pos"])) for e in impacts] if audible else [])
            played.clear()


def test_sky_smoke_warns_once_per_cloud_at_its_own_expiry(monkeypatch) -> None:
    from types import SimpleNamespace

    from gameplay.geometry import Vec
    from gameplay.net import event_to_json, events_from_json
    from gameplay.netgame import NetHost
    from gameplay.world import WorldMap

    game = Game(args(agent="brimstone", team_size=3))
    match = game.match
    match.world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(90, 90)]})
    match.start()
    match.phase, match.phase_until = "live", match.time + 60
    caster = match.players[game.me]
    caster.charges["E"] = 3
    ally = next(p for p in match.players.values() if p.team == caster.team and p is not caster)
    enemy, distant, *_ = [p for p in match.players.values() if p.team != caster.team]
    centers = (Vec(25, 10), Vec(25, 30), Vec(45, 10))
    match.tick(1 / 64, {caster.pid: Command(ability="E", points=[(p.x, p.y) for p in centers[:2]])})
    for _ in range(64):
        match.tick(1 / 64, {})
    match.tick(1 / 64, {caster.pid: Command(ability="E", points=[(45, 10)])})
    expiries = {e.pos: e.until for e in match.effects if e.kind == "smoke"}
    assert set(expiries) == set(centers) and len(set(expiries.values())) == 2
    cues = []
    while match.time < max(expiries.values()) + 0.1:
        cues.extend(e for e in match.tick(1 / 64, {}) if e.kind == "sound_fx")
    assert len(cues) == 3
    assert {Vec(*cue.data["pos"]) for cue in cues} == set(centers)

    host = SimpleNamespace(match=match)
    played = []
    monkeypatch.setattr(game.sound, "play", lambda key, *args, **kw: played.append((key, args)))
    for cue in cues:
        center = Vec(*cue.data["pos"])
        assert expiries[center] - cue.t == pytest.approx(1.5, abs=1 / 64)
        ally.pos, enemy.pos, distant.pos = center + Vec(5, 0), center + Vec(0, 5), Vec(90, 90)
        for player in (ally, enemy, distant):
            game.me = player.pid
            received = events_from_json([event_to_json(cue)] if NetHost._event_visible(host, player, cue) else [])
            assert bool(received) == (player is not distant)
            for events in ([cue], received):
                game.handle_events(events)
                assert played == ([] if player is distant else [("cast_whoosh", (player, center, 12.5))])
                played.clear()


def test_dark_cover_audio_routes_cast_and_fade_separately(monkeypatch) -> None:
    from types import SimpleNamespace

    from gameplay.geometry import Vec
    from gameplay.net import event_to_json, events_from_json
    from gameplay.netgame import NetHost
    from gameplay.world import WorldMap

    game = Game(args(team_size=3))
    match = game.match
    match.world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(90, 90)]})
    match.start()
    match.phase, match.phase_until = "live", match.time + 60
    omen = match.players[game.me]
    omen.pos = Vec(30, 50)
    ally, far_ally = [p for p in match.players.values() if p.team == omen.team and p is not omen]
    enemy, near_smoke, far_enemy = [p for p in match.players.values() if p.team != omen.team]
    ally.pos, far_ally.pos = Vec(35, 50), Vec(65, 50)
    enemy.pos, near_smoke.pos, far_enemy.pos = Vec(35, 55), Vec(65, 55), Vec(90, 50)
    origin, target = omen.pos, Vec(65, 52)
    cast = match.tick(1 / 64, {omen.pid: Command(ability="E", points=[(target.x, target.y)])})
    [smoke] = [e for e in match.effects if e.kind == "smoke"]
    assert smoke.pos == target
    fade = []
    while match.time < smoke.until:
        fade.extend(e for e in match.tick(1 / 64, {}) if e.kind == "sound_fx")
    [warning] = fade
    assert smoke.until - warning.t == pytest.approx(1.5, abs=1 / 64)

    host = SimpleNamespace(match=match)
    played = []
    monkeypatch.setattr(game.sound, "play", lambda key, *args, **kw: played.append((key, args)))
    for batch, key, point, audience in [
        (cast, "cast_deploy", origin, (omen, ally)),
        (fade, "cast_whoosh", target, (far_ally, near_smoke)),
    ]:
        relevant = [e for e in batch if e.kind in ("ability", "sound_fx")]
        [cue] = [e for e in relevant if e.kind == "sound_fx"]
        assert Vec(*cue.data["pos"]) == point
        for player in match.players.values():
            game.me = player.pid
            received = events_from_json([event_to_json(e) for e in relevant if NetHost._event_visible(host, player, e)])
            assert any(e.kind == "sound_fx" for e in received) == (player in audience)
            for events in (relevant, received):
                game.handle_events(events)
                args_played = () if player is omen else (player, point, 12.5)
                assert played == ([(key, args_played)] if player in audience else [])
                played.clear()


def test_shrouded_step_audio_at_departure_and_arrival(monkeypatch) -> None:
    from types import SimpleNamespace

    from gameplay.geometry import Vec
    from gameplay.net import event_to_json, events_from_json
    from gameplay.netgame import NetHost
    from gameplay.world import WorldMap

    game = Game(args())
    match = game.match
    match.world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(35, 50)], 1: [Vec(90, 90)]})
    match.start()
    match.phase, match.phase_until = "live", match.time + 60
    omen = match.players[game.me]
    omen.pos = Vec(35, 50)
    omen.charges["C"] = 1
    ally = next(p for p in match.players.values() if p.team == omen.team and p is not omen)
    enemy, distant = [p for p in match.players.values() if p.team != omen.team]
    ally.pos, enemy.pos, distant.pos = Vec(47, 55), Vec(47, 45), Vec(85, 85)
    host = SimpleNamespace(match=match)
    played = []
    monkeypatch.setattr(game.sound, "play", lambda key, *args, **kw: played.append((key, args)))
    cast = match.tick(1 / 64, {omen.pid: Command(ability="C", facing=90, cursor_depth=12)})
    assert omen.pos == Vec(35, 50)
    arrival = []
    for _ in range(50):
        arrival.extend(match.tick(1 / 64, {}))
    assert omen.pos == Vec(47, 50)

    for events, key, point in [(cast, "cast_arcane", Vec(35, 50)), (arrival, "ab_teleport", Vec(47, 50))]:
        relevant = [e for e in events if e.kind in ("ability", "sound_fx")]
        [cue] = [e for e in relevant if e.kind == "sound_fx"]
        assert Vec(*cue.data["pos"]) == point
        for player in (omen, ally, enemy, distant):
            game.me = player.pid
            received = events_from_json([event_to_json(e) for e in relevant if NetHost._event_visible(host, player, e)])
            assert any(e.kind == "sound_fx" for e in received) == (player is not distant)
            for batch in (relevant, received):
                game.handle_events(batch)
                expected = [] if player is distant else [(key, () if player is omen else (player, point, cue.data["radius"]))]
                assert played == expected
                played.clear()


def test_assist_audio_goes_only_to_credited_helper(monkeypatch) -> None:
    from types import SimpleNamespace

    from gameplay.net import event_to_json, events_from_json
    from gameplay.netgame import NetHost

    game = Game(args(team_size=3))
    match = game.match
    match.start()
    match.phase = "live"
    killer = match.players[game.me]
    helper, ally = [p for p in match.players.values() if p.team == killer.team and p != killer]
    victim, enemy, *_ = [p for p in match.players.values() if p.team != killer.team]
    match.events.clear()
    match._damage(helper, victim, 55, "body", "vandal")
    assert not any(e.kind == "assist" for e in match.events)
    match._damage(killer, victim, 160, "head", "vandal")
    assert helper.assists == 1
    events = [e for e in match.events if e.kind in ("assist", "kill")]
    host = SimpleNamespace(match=match)
    assert "assist" in game.sound.sounds
    played = []
    monkeypatch.setattr(game.sound, "play", lambda key, *args, **kwargs: played.append(key))
    for player, expected in [(helper, ["assist"]), (killer, ["kill_1"]), (victim, ["death"]),
                             (ally, []), (enemy, [])]:
        game.me = player.pid
        received = events_from_json([event_to_json(e) for e in events if NetHost._event_visible(host, player, e)])
        assert sum(e.kind == "assist" for e in received) == (player == helper)
        game.handle_events(received)
        assert played == expected
        played.clear()
        game.handle_events(events)
        assert played == expected
        played.clear()


def test_menu_opens_and_lists_maps(archived_agents) -> None:
    from gameplay.match import PLAYABLE_AGENT_KEYS
    from gameplay.world import PLAYABLE_MAP_KEYS
    from menu import MainMenu
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    font = pygame.font.Font(None, 22)
    menu = MainMenu(screen, font, font, args(map="workyard", agent="kestrel"))
    assert menu.maps == list(PLAYABLE_MAP_KEYS)
    assert {"workyard", "range", "_ascent"}.isdisjoint(menu.maps)
    assert set(menu.agents()) == set(archived_agents).intersection(PLAYABLE_AGENT_KEYS)
    assert (menu.args.map, menu.args.agent) == ("ascent", "omen")
    assert "kestrel" in archived_agents and "kestrel" not in menu.agents()
    menu.activate("agent:kestrel")
    menu.activate("pick_agent")
    assert (menu.agent_view, menu.args.agent) == ("omen", "omen")
    for expected in (*PLAYABLE_MAP_KEYS[1:], PLAYABLE_MAP_KEYS[0]):
        menu.activate("map_next")
        assert menu.args.map == expected
    menu.draw()


def test_local_match_draws_buy_and_live_frames() -> None:
    game = Game(args())
    game.match.start()
    frames(game, 30)
    game.match.phase_until = game.match.time  # skip the buy phase
    frames(game, 60)
    assert game.match.phase in ("live", "planted", "end")


def test_team_deathmatch_end_phase_from_pause_menu() -> None:
    game = Game(args(mode="deathmatch"))
    assert game.match.set_rules(allow_cheats=True)
    game.start_from_lobby()
    game.open_overlay("pause")
    game.draw_overlay()
    pause = next(hit for hit in game.kit.hits if hit.action == "toggle_dm_timer")
    for event in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        game.overlay_event(pygame.event.Event(event, button=1, pos=pause.rect.center))
    assert game.match.dm_timer_paused
    game.open_overlay("pause")
    game.draw_overlay()
    action = next(hit for hit in game.kit.hits if hit.action == "end_dm_phase")
    for event in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        game.overlay_event(pygame.event.Event(event, button=1, pos=action.rect.center))
    frames(game, 1)
    assert game.match.phase == "live" and game.match.dm_stage == 1
    assert not game.match.dm_timer_paused
    game.open_overlay("pause")
    game.draw_overlay()
    ghost = next(hit for hit in game.kit.hits if hit.action == "toggle_dm_ghost")
    for event in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        game.overlay_event(pygame.event.Event(event, button=1, pos=ghost.rect.center))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    game.run()
    assert game.match.players[game.me].dm_ghost


def test_team_deathmatch_loadouts_from_play_menu() -> None:
    from gameplay.match import Command
    from menu import MainMenu

    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    font = pygame.font.Font(None, 22)
    menu = MainMenu(screen, font, font, args())
    menu.activate("mode:deathmatch")
    selected = menu.activate("start")
    assert isinstance(selected, argparse.Namespace)
    game = Game(selected)
    game.start_from_lobby()
    me = game.match.players[game.me]
    assert game.match.can_select_deathmatch_loadout(me)
    game.ui.buy_open = True
    game.draw()
    cards = game.buy_layout()
    assert len(cards) == 13
    card = next(rect for rect, item, _ in cards if item == "tdm4:vandal")
    item = game.buy_item_at(card.center)
    assert item == "tdm4:vandal"
    action = game.buy_action_at(me, item, card.center)
    assert action is not None
    game.step(1 / 60, Command(buy=[action]))
    assert me.dm_loadout[-1] == "vandal"
    game.ui.buy_open = False
    game.match.time = game.match.phase_until
    frames(game, 2)
    assert game.match.phase == "live"
    station = game.match.drops[0]
    me.pos, me.ground = station.pos, game.match.world.ground_height(station.pos)
    game.handle_events(game.step(1 / 60, Command(interact=True)))
    game.draw()
    assert me.weapon.from_station and me.weapon.reserve == station.reserve
    game.step(1 / 60, Command(drop=True))
    assert me.weapon.key == "classic" and station not in game.match.drops
    orb = game.match.recovery_orbs[0]
    me.hp = 40
    me.pos, me.ground = orb, game.match.world.ground_height(orb)
    frames(game, 8)
    assert orb not in game.match.recovery_orbs and me.hp > 40
    game.match.time = game.match.dm_next_ultimate_wave
    frames(game, 1)
    point = game.match.orbs[0]
    me.pos, me.ground = point, game.match.world.ground_height(point)
    points = me.ult_points
    frames(game, 1)
    assert point not in game.match.orbs and me.ult_points == points + 10
    game.match.time = game.match.phase_until
    frames(game, 1)
    assert game.match.deathmatch_stage_equip_left(me) and me.weapon.key == "classic"
    pygame.event.clear()
    _post_key(game.keys["buy"])
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    game.run()
    assert me.weapon.key == "sheriff" and not game.match.deathmatch_stage_equip_left(me)


@pytest.mark.parametrize(("key", "sites"), [("bind", "AB"), ("haven", "ABC")])
def test_additional_maps_open_from_the_play_menu(key, sites, archived_agents) -> None:
    from gameplay.world import PLAYABLE_MAP_KEYS
    from menu import MainMenu

    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    font = pygame.font.Font(None, 22)
    menu = MainMenu(screen, font, font, args())
    menu.activate("choose_map")
    assert menu.map_picker.keys == PLAYABLE_MAP_KEYS
    menu.activate("map_pick:range")
    assert menu.args.map == "ascent"
    menu.activate(f"map_pick:{key}")
    chosen = menu.activate("start")
    assert isinstance(chosen, argparse.Namespace)
    game = Game(chosen)
    assert game.match.world.key == key
    assert {site.name for site in game.match.world.sites} == set(sites)
    assert "kestrel" in archived_agents and "kestrel" not in game.match.agents
    game.draw()
    assert {agent for _, agent in game.agent_cards} == set(menu.agents())
    game.agent_cards.append((pygame.Rect(0, 0, 6, 6), "kestrel"))
    game.pick_agent_at((1, 1))
    assert game.match.players[game.me].agent == "omen"
    game.start_from_lobby()
    assert all(player.agent in menu.agents() for player in game.match.players.values())
    frames(game, 2)
    game.match.phase_until = game.match.time
    frames(game, 2)
    assert game.match.phase == "live"


@pytest.mark.parametrize("options", [{"map": "workyard"}, {"map": "harbour", "host": True}, {"practice": True}])
def test_custom_maps_are_disabled(options) -> None:
    with pytest.raises(OSError, match="disabled"):
        Game(args(**options))


def test_party_rejects_disabled_content_before_switching_matches(archived_agents) -> None:
    from types import SimpleNamespace

    from gameplay.match import Match
    from gameplay.netgame import NetClient
    from gameplay.world import load_playable_map

    game = Game(args())
    previous = game.match
    assert "kestrel" in archived_agents and "kestrel" not in previous.agents
    assert all(player.agent in previous.agents for player in previous.players.values())
    game.mode = "client"
    client = NetClient.__new__(NetClient)
    client.connected, client.map_key, client.generation, client.state_sequence = False, "ascent", 0, -1
    client.inbox = []
    client.lobby = SimpleNamespace(poll=lambda: ())
    game.client = client
    game.net_generation = 0
    host = Match(load_playable_map("bind"), agent_roster=previous.agents)
    player = host.add_player("Host", 0, "omen")
    host.start()

    for section in ("roster", "players"):
        snap = host.snapshot(player.pid)
        snap[section][0]["agent"] = "kestrel"
        client.inbox.append({"t": "state", "game": 1, "seq": 2, "map": "bind", "snap": snap})
        with pytest.warns(UserWarning, match="unavailable agent 'kestrel'"):
            game.step(1 / 30, Command())
        assert game.match is previous and game.net_generation == 0
        assert (client.generation, client.state_sequence, client.map_key) == (0, -1, "ascent")

    valid = {"t": "state", "game": 1, "seq": 1, "map": "bind", "snap": host.snapshot(player.pid)}
    client.inbox.append({**valid, "seq": 3, "map": "workyard"})
    with pytest.warns(UserWarning, match="Map 'workyard' is disabled"):
        game.step(1 / 30, Command())
    assert game.match is previous and game.net_generation == 0
    assert (client.generation, client.state_sequence, client.map_key) == (0, -1, "ascent")

    client.inbox.append(valid)
    game.step(1 / 30, Command())
    assert game.match.world.key == "bind" and game.net_generation == 1
    assert game.match.players[player.pid].agent == "omen"


def test_menu_start_path_local() -> None:
    """The real path: main menu builds the arguments, the game starts from them and draws."""
    from menu import MainMenu
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    font = pygame.font.Font(None, 22)
    menu = MainMenu(screen, font, font, args(no_menu=False))
    chosen = menu.activate("start")
    assert isinstance(chosen, argparse.Namespace)
    game = Game(chosen)
    assert game.match.world.key == "ascent"
    assert all(p.agent in menu.agents() for p in game.match.players.values())
    game.reload_content()
    assert set(game.match.agents) == set(menu.agents())
    game.match.start()
    frames(game, 10)


def test_custom_menu_prefills_last_ip_and_accepts_paste(monkeypatch) -> None:
    from menu import MainMenu
    import user_settings

    user_settings.save({**user_settings.defaults(), "last_join": "192.168.1.2:9009"})
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    font = pygame.font.Font(None, 22)
    menu = MainMenu(screen, font, font, args())
    assert menu.address == "192.168.1.2:9009"
    monkeypatch.setattr(pygame.scrap, "get_text", lambda: " 192.168.1.3:9010\n")
    menu.typing = True
    menu.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v, mod=pygame.KMOD_CTRL, unicode=""))
    chosen = menu.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode=""))
    assert chosen.join == "192.168.1.3:9010"


def test_escape_pauses_and_double_alt_f4_quits() -> None:
    game = Game(args())
    game.match.start()
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=41))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    game.run()  # returns once the second Alt+F4 arrives
    assert game.quit_program


def test_escape_opens_pause_and_closes_it_again() -> None:
    game = Game(args())
    game.match.start()
    game.open_overlay("pause")
    game.draw()
    game.draw_overlay()
    assert game.overlay == "pause" and any(h.action == "resume" for h in game.kit.hits)
    game.overlay_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=41))
    assert game.overlay == ""


def test_menu_escape_never_quits_and_alt_f4_asks_first() -> None:
    from menu import MainMenu
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    menu = MainMenu(screen, pygame.font.Font(None, 22), pygame.font.Font(None, 22), args(no_menu=False))
    menu.tab, menu.view = "agents", "settings"
    esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=41)
    assert menu.handle(esc) is None and menu.view == "main"
    assert menu.handle(esc) is None and menu.tab == "play"
    assert menu.handle(esc) is None
    assert menu.handle(pygame.event.Event(pygame.QUIT)) is None and menu.dialog == "quit"
    assert menu.handle(pygame.event.Event(pygame.QUIT)) is False


def test_crosshair_is_symmetric_for_any_size_and_gap() -> None:
    from client.crosshair import shape
    for size in (0.5, 0.73, 1.0, 1.37, 2.5):
        for gap in (0.0, 2.4, 4.0, 7.6, 12.0):
            for center in ((100, 100), (100.5, 99.5), (101.3, 100.7)):
                right, left, down, up, dot = shape(center, size, gap, True)
                cx2 = dot.x * 2 + dot.w  # twice the centre, exact in whole pixels
                cy2 = dot.y * 2 + dot.h
                assert right.x + left.right == cx2 and down.y + up.bottom == cy2
                assert right.size == left.size and down.size == up.size and right.w == down.h


@pytest.mark.parametrize("zoom,scoped", [(0, False), (1, False), (1, True)])
def test_cursor_stops_at_the_view_edge_and_reverses_immediately(zoom, scoped) -> None:
    from gameplay.geometry import heading

    game = Game(args())
    me = game.match.players[game.me]
    game.zoom_level, game.scoped = zoom, scoped
    game.scale *= 1.5 if zoom else 1.0
    game.move_cursor(me, -100_000)
    _, y = game.to_screen(me.pos + heading(me.facing) * game.cursor_depth, me)
    assert y == pytest.approx(game.h / 2 if scoped else 1)
    limit = game.cursor_depth
    game.move_cursor(me, -100_000)
    assert game.cursor_depth == limit
    game.move_cursor(me, 1)
    assert game.cursor_depth == pytest.approx(limit - 0.03)


@pytest.mark.parametrize("level", [1, 2])
def test_scoped_map_rotates_with_world_positions(level) -> None:
    from client.common import VIEW_METERS
    from gameplay.geometry import Vec
    from gameplay.match import WeaponState

    game = Game(args())
    me = game.match.players[game.me]
    me.pos = Vec(10, game.match.world.height - 20)
    me.weapons["primary"] = WeaponState("operator", 5, 10)
    me.slot, me.zoom_level = "primary", level
    game.cursor_depth = 5.0
    game.apply_zoom(me, holding_alt=False)
    assert game.scoped
    base = game.w / VIEW_METERS
    game.map_surface = pygame.Surface((round(25 * base), round(25 * base)))
    marker = Vec(13, me.pos.y + 5)
    color = (240, 40, 140)
    pygame.draw.circle(game.map_surface, color,
                       (round(marker.x * base), round((game.match.world.height - marker.y) * base)), 10)
    previous_x = game.w
    for facing in (25.0, 35.0):
        me.facing = facing
        game.screen.fill((0, 0, 0))
        game.draw_map_texture(me)
        x, y = map(round, game.to_screen(marker, me))
        assert x < previous_x
        assert game.screen.get_at((x, y))[:3] == color
        previous_x = x


def test_paranoia_warning_draws_a_border_without_blinding_the_view() -> None:
    game = Game(args())
    me = game.match.players[game.me]
    game.screen.fill((0, 0, 0))
    game.match.remote_paranoia_warning = True
    game.draw_flash(me)
    assert game.screen.get_at((0, 0))[:3] != (0, 0, 0)
    assert game.screen.get_at((game.w // 2, game.h // 2))[:3] == (0, 0, 0)
    game.screen.fill((0, 0, 0))
    game.match.remote_paranoia_warning = False
    game.draw_flash(me)
    assert game.screen.get_at((0, 0))[:3] == (0, 0, 0)


def test_obscured_minimap_skips_drawing_contacts(monkeypatch) -> None:
    game = Game(args())
    me = game.match.players[game.me]
    calls = []
    monkeypatch.setattr(game, "_mini_icon", lambda *_args: calls.append("icon"))
    monkeypatch.setattr(game.kit, "text", lambda label, *_args, **_kwargs: calls.append(label))
    game.match.remote_minimap_obscured = True
    game.draw_minimap(me, [], None)
    assert calls == ["MINIMAP OBSCURED"]
    game.match.remote_minimap_obscured = False
    game.draw_minimap(me, [], None)
    assert "icon" in calls


@pytest.mark.parametrize("mode", ["local", "client"])
def test_minimap_contacts_require_the_players_own_view(mode) -> None:
    from gameplay.geometry import Rect, Vec
    from gameplay.world import Wall

    game = Game(args())
    game.mode = mode
    match = game.match
    me = match.players[game.me]
    ally = next(p for p in match.players.values() if p.team == me.team and p is not me)
    enemy = next(p for p in match.players.values() if p.team != me.team)
    me.pos, me.facing = Vec(15, 10), 0
    ally.pos, ally.facing = Vec(15, 16), 0
    enemy.visible = True
    match.world.walls = [Wall(Rect(14, 14, 16, 15), 3)]
    enemy.pos = Vec(15, 17)
    assert match.can_see(ally, enemy)
    assert not game.minimap_sees_enemy(me, enemy)
    enemy.pos = Vec(15, 12)
    assert game.minimap_sees_enemy(me, enemy)
    match.world.walls = []
    enemy.pos = Vec(15, 32)
    assert match.can_see(me, enemy)
    assert not game.minimap_sees_enemy(me, enemy)


def test_weapon_wheel_skips_empty_slots_and_hud_shows_the_actual_keys(monkeypatch) -> None:
    from gameplay.match import Command

    game = Game(args(keys={"sidearm": "8"}))
    game.match.start()
    me = game.match.players[game.me]
    assert me.slot == "sidearm" and "primary" not in me.weapons
    cmd = Command()
    game.scroll_weapons(me, cmd, -1)
    assert cmd.slot == "melee"
    game.scroll_weapons(me, cmd, -1)
    assert cmd.slot == "sidearm"

    labels = []
    monkeypatch.setattr(game.kit, "text", lambda label, *args, **kwargs: labels.append(label))
    game.draw_weapon_box(me)
    assert "8" in labels and "3" in labels and "1" not in labels


def test_main_menu_inventory_scrolls_between_pages(monkeypatch) -> None:
    from menu import MainMenu

    monkeypatch.setattr("client.inventory.WEAPONS_PER_PAGE", 2)
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    font = pygame.font.Font(None, 22)
    menu = MainMenu(screen, font, font, args())
    menu.activate("tab:inventory")
    menu.inventory.page = 0
    menu.handle(pygame.event.Event(pygame.MOUSEWHEEL, y=-1))
    assert menu.inventory.page == 1
    menu.handle(pygame.event.Event(pygame.MOUSEWHEEL, y=5))
    assert menu.inventory.page == 0


def _post_key(key: int) -> None:
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0))


@pytest.fixture
def legacy_wall_agent(monkeypatch, archived_agents):
    from gameplay.match import playable_agents
    roster = playable_agents()
    roster["marrow"] = archived_agents["marrow"]
    monkeypatch.setattr("client.game.playable_agents", lambda: roster)


def test_ability_is_taken_in_hand_cast_with_left_click_and_put_away_with_its_key() -> None:
    game = Game(args(agent="phoenix"))
    game.match.start()
    key_e = game.keys["ability_e"]
    before = len(game.match.effects)
    pygame.event.clear()
    _post_key(key_e)          # in hand
    _post_key(game.keys["drop"])
    _post_key(key_e)          # same key: put away again
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    game.run()
    assert game.aiming is None and len(game.match.effects) == before
    assert game.match.players[game.me].weapons["sidearm"].key == "classic"
    game2 = Game(args(agent="phoenix"))
    game2.match.start()
    before = len(game2.match.effects)
    pygame.event.clear()
    _post_key(key_e)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 360)))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    game2.run()
    assert len(game2.match.effects) == before + 1 and game2.aiming is None


def test_right_click_casts_the_alternative_wall_along_the_aim(legacy_wall_agent) -> None:
    from gameplay.match import Command
    game = Game(args(agent="marrow"))
    game.match.start()
    me = game.match.players[game.me]
    me.charges["Q"], me.facing = 1, 0.0
    assert me.agent == "marrow"
    game.match.tick(1 / 64, {game.me: Command(facing=0.0, cursor_depth=6.0, ability="Q", ability_alt=True)})
    wall = next(e for e in game.match.effects if e.kind == "wall")
    assert abs(wall.a.x - wall.b.x) < 1e-6 and abs(wall.a.y - wall.b.y) > 1.0  # along the aim (aim = +y)


def test_escape_menu_opens_full_settings_and_applies_them() -> None:
    import user_settings
    game = Game(args())
    game.match.start()
    saved = user_settings.load()
    try:
        game.open_overlay("pause")
        game.draw()
        game.draw_overlay()
        settings = next(h for h in game.kit.hits if h.action == "settings")
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            game.overlay_event(pygame.event.Event(kind, button=1, pos=settings.rect.center))
        assert game.overlay == "settings"
        game.settings_panel.settings["sensitivity"] = 0.6
        game.draw_overlay()
        game.overlay_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=41))
        assert game.overlay == "pause" and abs(game.sens - 0.6) < 1e-9
    finally:
        user_settings.save(saved)


def test_match_over_has_a_back_to_menu_button() -> None:
    game = Game(args())
    game.match.start()
    game.match.phase = "over"
    game.draw()
    assert any(h.action == "to_menu" for h in game.kit.hits)


@pytest.mark.parametrize("action", ["plant", "defuse"])
@pytest.mark.parametrize("restore", [False, True])
def test_running_spike_sound_follows_spectated_teammate(action, restore, monkeypatch) -> None:
    from unittest.mock import Mock

    from gameplay.geometry import Vec
    from gameplay.match import GameEvent

    game = Game(args(team_size=3))
    match = game.match
    match.start()
    match.phase, match.phase_until = "live", match.time + 100
    me = match.players[game.me]
    near, far = sorted((p for p in match.players.values() if p.team == me.team and p is not me),
                       key=lambda p: p.pid)
    me.alive = False
    me.pos = far.pos = Vec(0, 0)
    near.pos, near.facing = Vec(45, 40), 0
    monkeypatch.setattr(game, "occluded", lambda listener, _: listener.pid == near.pid)
    play = game.sound.play
    monkeypatch.setattr(game.sound, "play", Mock(side_effect=lambda *args, **kw: Mock(wraps=play(*args, **kw))))
    pygame.mixer.stop()
    event = GameEvent("spike_audio_restore" if restore else f"{action}_start",
                      match.time - 1 if restore else match.time,
                      {"pid": near.pid, "pos": (45, 45), "key": f"spike_{action}"})
    spectator = game.view_player(me)
    game.handle_events([event], spike_listener=spectator)
    pos, tracks = game.ui.spike_sounds[near.pid]
    channel, sample, filtered = tracks[0]
    assert filtered
    assert game.sound.play.call_args.args[1] is spectator
    assert game.sound.play.call_args.kwargs["occluded"]
    if restore:
        assert sample.get_length() == pytest.approx(game.sound.muffled[f"spike_{action}"].get_length() - 1, abs=0.001)
    game.audio_tick(me, spike_listener=game.view_player(me))
    expected = game.sound.spatial_mix(near, pos, 35, True, 1.0)[:2]
    assert channel.set_volume.call_args.args == pytest.approx(expected)
    game.spectate_index += 1
    game.audio_tick(me, spike_listener=game.view_player(me))
    assert channel.set_volume.call_args.args == (0, 0)
    game.spectate_index += 1
    game.audio_tick(me, spike_listener=game.view_player(me))
    assert channel.set_volume.call_args.args == pytest.approx(expected)
    assert channel.get_sound() == sample
    assert game.sound.play.call_count == 1
    game.stop_spike_sound(near.pid)


def test_spatial_ability_cues_preserve_recipients_while_spectating() -> None:
    from types import SimpleNamespace
    from unittest.mock import Mock

    from client.events import EventsMixin
    from gameplay.geometry import Vec
    from gameplay.match import GameEvent
    from gameplay.netgame import NetHost
    from test_chamber import arena

    match = arena()
    me = match.add_player("Spectator", 0, "omen")
    watched = match.add_player("Watched", 0, "sage")
    match.phase = "live"
    me.alive, me.pos, watched.pos = False, Vec(70, 70), Vec(10, 10)
    audio = EventsMixin()
    audio.match, audio.me, audio.sound = match, me.pid, Mock()
    audio.occluded = lambda *_: False
    host = SimpleNamespace(match=match)
    spatial = GameEvent("sound_fx", 0, {"key": "cast_sonic", "pos": (12, 10), "radius": 15,
                                      "range_filtered": True})
    assert NetHost._event_visible(host, me, spatial)
    enemy_only = GameEvent("sound_fx", 0, {**spatial.data, "team": 1})
    assert not NetHost._event_visible(host, me, enemy_only)
    audio.handle_events([spatial, enemy_only,
                         GameEvent("assist", 0, {"pid": watched.pid}),
                         GameEvent("assist", 0, {"pid": me.pid}),
                         GameEvent("kayo_announcement", 0, {"team": me.team, "ally": "cast_dark",
                                                            "enemy": "cast_burst"})], spike_listener=watched)
    calls = audio.sound.play.call_args_list
    assert [call.args for call in calls] == [
        ("cast_sonic", watched, Vec(12, 10), 15), ("assist",), ("cast_dark",),
    ]


@pytest.mark.parametrize("kind", ["door", "orb", "explode"])
def test_spatial_map_sound_follows_spectated_teammate(kind) -> None:
    from gameplay.geometry import Vec
    from gameplay.match import GameEvent

    game = Game(args(team_size=3))
    match = game.match
    match.start()
    match.phase = "live"
    me = match.players[game.me]
    me.alive, me.pos = False, Vec(140, 140)
    near, far = sorted((p for p in match.players.values() if p.team == me.team and p is not me),
                       key=lambda p: p.pid)
    near.pos, near.facing, far.pos = Vec(10, 10), 0, me.pos
    assert game.sound.ok
    try:
        for index, (opened, expected) in enumerate(((True, True), (False, False))):
            pygame.mixer.stop()
            game.spectate_index = index
            event = GameEvent(kind, match.time, {"pos": (10, 14), "open": opened})
            game.handle_events([event], spike_listener=game.view_player(me))
            assert pygame.mixer.get_busy() == expected
    finally:
        pygame.mixer.stop()


def test_reload_cues_follow_spectator_switch(monkeypatch) -> None:
    from unittest.mock import Mock

    from gameplay.geometry import Vec
    from gameplay.match import GameEvent

    game = Game(args(team_size=3))
    match = game.match
    match.start()
    match.phase, match.time = "live", 2
    me = match.players[game.me]
    me.alive = False
    reloader = next(p for p in match.players.values() if p.team != me.team)
    reloader.pos = Vec(20, 21)
    first = game.view_player(me)
    play = Mock()
    monkeypatch.setattr(game.sound, "play", play)
    monkeypatch.setattr(game, "occluded", lambda listener, _: listener.pid == first.pid)
    game.handle_events([GameEvent("reload", 2, {"pid": reloader.pid, "pos": (20, 20), "seconds": 1.5})],
                       spike_listener=first)
    game.spectate_index += 1
    second = game.view_player(me)
    assert first.pid != second.pid
    match.time = 3
    game.audio_tick(me, spike_listener=second)
    assert len([call for call in play.call_args_list if call.args[0].startswith("reload_")]) == 1
    match.time = 3.2
    game.audio_tick(me, spike_listener=second)
    cues = [call for call in play.call_args_list if call.args[0].startswith("reload_")]
    assert [call.args for call in cues] == [
        ("reload_out", first, Vec(20, 20), 14), ("reload_in", second, reloader.pos, 14),
    ]
    assert [call.kwargs for call in cues] == [{"occluded": True, "gain": 0.5}, {"occluded": False, "gain": 0.5}]


def test_jump_and_landing_follow_spectated_teammate(monkeypatch) -> None:
    from unittest.mock import Mock

    from gameplay.geometry import Vec
    from gameplay.match import GameEvent

    game = Game(args(team_size=2))
    match = game.match
    match.start()
    match.phase, match.time = "live", 2
    me = match.players[game.me]
    me.alive, me.pos = False, Vec(70, 70)
    watched = game.view_player(me)
    jumper, quiet = [p for p in match.players.values() if p.team != me.team]
    jumper.pos, quiet.pos = Vec(12, 10), Vec(15, 10)
    from gameplay.geometry import Rect

    match.world.quiet_landings = [Rect(14, 9, 16, 11)]
    quiet.quiet_drop = quiet.walking = True
    match._landing(jumper, 1)
    match._landing(quiet, 1)
    play = Mock()
    monkeypatch.setattr(game.sound, "play", play)
    monkeypatch.setattr(game, "occluded", lambda listener, _: listener is watched)
    game.handle_events([GameEvent("jump", 1.9, {"pid": jumper.pid, "pos": (10, 10)})]
                       + [event for event in match.events if event.kind == "land"], spike_listener=watched)
    game.audio_tick(me, spike_listener=watched)
    calls = [call for call in play.call_args_list if call.args[0] in ("jump", "land")]
    assert [call.args for call in calls] == [
        ("jump", watched, Vec(10, 10), 12), ("land", watched, jumper.pos, 18),
    ]
    assert all(call.kwargs["occluded"] for call in calls)
    assert game.ui.landed_at[quiet.pid] == match.time


def test_footstep_uses_spectated_teammate_for_mixing_and_noise_ring() -> None:
    from dataclasses import replace
    from unittest.mock import Mock

    from client.common import UiState
    from client.events import EventsMixin
    from gameplay.geometry import Vec
    from gameplay.match import GameEvent
    from test_chamber import arena

    match = arena()
    match.cfg = replace(match.cfg, lobby=replace(match.cfg.lobby, sound_rings=True))
    me = match.add_player("Spectator", 0, "omen")
    watched = match.add_player("Watched", 0, "sage")
    enemy = match.add_player("Enemy", 1, "omen")
    me.alive, me.pos, watched.pos = False, Vec(70, 70), Vec(10, 10)
    origin = Vec(12, 10)
    audio = EventsMixin()
    audio.match, audio.me, audio.sound, audio.ui = match, me.pid, Mock(), UiState()
    audio.occluded = lambda listener, _: listener is watched
    event = GameEvent("sound", 0, {"pid": enemy.pid, "kind": "step", "pos": (12, 10), "radius": 15})
    audio.handle_events([event], spike_listener=watched)
    assert audio.sound.play.call_args.args == (audio.sound_key(event.data, origin), watched, origin, 15)
    assert audio.sound.play.call_args.kwargs["occluded"]
    assert len(audio.ui.rings) == 1
    watched.pos = Vec(60, 60)
    audio.handle_events([event], spike_listener=watched)
    assert len(audio.ui.rings) == 1


def test_master_volume_updates_playing_one_shots() -> None:
    from unittest.mock import Mock

    from client.common import Sound

    sound = Sound()
    sound.volume = 0.8
    sound.set_perspective_gain(0.25)
    for channel_id, key in enumerate(("cast_sonic", "ui_click", "round_win")):
        sample = Mock()
        sample.play.return_value.id = channel_id
        sample.play.return_value.get_sound.return_value = sample
        sound.sounds[key] = sample
        sound.play(key, apply_perspective=key != "round_win")
    for volume in (0.0, 0.4):
        sound.volume = volume
        for key in ("cast_sonic", "ui_click", "round_win"):
            sample = sound.sounds[key]
            expected = 0.5 * volume * (0.25 if key == "cast_sonic" else 1)
            assert sample.play.return_value.set_volume.call_args.args == (expected, expected)
            sample.play.assert_called_once()


def test_kayo_countdown_updates_playing_one_shots() -> None:
    from unittest.mock import Mock

    from client.common import Sound

    sound = Sound()
    sound.volume = 0.8
    sample = Mock()
    channel = sample.play.return_value
    channel.id = 0
    channel.get_sound.return_value = sample
    sound.sounds["cast_sonic"] = sample
    assert sound.play("cast_sonic") is channel
    sound.set_perspective_gain(0.25)
    sound.set_perspective_gain(1.0)
    assert [call.args for call in channel.set_volume.call_args_list] == [(0.4, 0.4), (0.1, 0.1), (0.4, 0.4)]
    sample.play.assert_called_once()

    # The same sample can be reused on the same channel for an undamped announcement.
    sound.play("cast_sonic", apply_perspective=False)
    channel.set_volume.reset_mock()
    sound.set_perspective_gain(0.25)
    channel.set_volume.assert_not_called()

    sound.play("cast_sonic")
    channel.get_sound.return_value = None
    channel.set_volume.reset_mock()
    sound.set_perspective_gain(1.0)
    channel.set_volume.assert_not_called()


def test_kayo_countdown_keeps_announcements_at_user_volume() -> None:
    from types import SimpleNamespace
    from unittest.mock import Mock

    from client.common import Sound, UiState
    from client.events import EventsMixin
    from gameplay.match import GameEvent

    audio = EventsMixin()
    audio.me, audio.aiming, audio.ui, audio.sound = 1, None, UiState(), Sound()
    audio.match = SimpleNamespace(time=1, players={1: SimpleNamespace(team=0)})
    audio.sound.volume = 0.6
    audio.sound.perspective_gain = 0.25
    for key in ("round_win", "cast_sonic"):
        audio.sound.sounds[key] = Mock()
    audio.handle_events([
        GameEvent("round_end", 1, {"winner": 0, "reason": "Test", "score": [1, 0]}),
        GameEvent("ability", 1, {"pid": 2, "pos": (0, 0), "team": 1,
                                "cast_announcement": {"ally": "cast_dark", "enemy": "cast_sonic"}}),
    ])
    for key in ("round_win", "cast_sonic"):
        audio.sound.sounds[key].play.return_value.set_volume.assert_called_once_with(0.3, 0.3)
    sample = audio.sound.sounds["cast_sonic"]
    sample.reset_mock()
    audio.sound.play("cast_sonic")
    sample.play.return_value.set_volume.assert_called_once_with(0.075, 0.075)


def test_kayo_countdown_keeps_ui_feedback_at_user_volume() -> None:
    from unittest.mock import Mock

    from client.common import Sound

    sound = Sound()
    sound.volume = 0.6
    sound.perspective_gain = 0.25
    for key, expected in (("ui_click", 0.3), ("ui_buy", 0.3), ("cast_sonic", 0.075)):
        sample = Mock()
        sound.sounds[key] = sample
        sound.play(key)
        sample.play.return_value.set_volume.assert_called_once_with(expected, expected)
    sound.volume = 0
    assert sound.play("ui_click") is None


def test_kayo_countdown_gain_follows_spectated_teammate() -> None:
    from gameplay.net import apply_snapshot

    game = Game(args(team_size=3))
    host = game.match
    host.start()
    host.phase, host.time = "live", 10
    me = host.players[game.me]
    me.alive = False
    kayo, other = sorted((p for p in host.players.values() if p.team == me.team and p is not me),
                         key=lambda p: p.pid)
    kayo.agent = "kayo"
    kayo.status["kayo_downed"] = float("inf")
    kayo.passive_state["kayo_downed"] = (12.5, None, "test", "body")
    replica = type(host)(host.world, host.cfg, agent_roster=host.agents)
    apply_snapshot(replica, host.snapshot(me.pid), me.pid)
    game.match = replica
    me = replica.players[me.pid]
    game.update_audio_perspective(game.view_player(me))
    assert game.sound.perspective_gain == pytest.approx(0.625)
    game.spectate_index += 1
    assert game.view_player(me).pid == other.pid
    game.update_audio_perspective(game.view_player(me))
    assert game.sound.perspective_gain == 1
    game.spectate_index -= 1
    kayo.status.pop("kayo_downed")
    apply_snapshot(replica, host.snapshot(me.pid), me.pid)
    game.update_audio_perspective(game.view_player(me))
    assert game.sound.perspective_gain == 1


@pytest.mark.parametrize("clear_mark", [False, True])
@pytest.mark.parametrize("muted", [False, True])
def test_drone_warning_waits_until_audible(monkeypatch, clear_mark, muted) -> None:
    import numpy as np

    from client import events

    game = Game(args())
    listener = game.match.players[game.me]
    listener.status["owl_drone_spotted"] = game.match.time + 2
    now = 1_000_000_000
    monkeypatch.setattr(events, "monotonic_ns", lambda: now)
    count = pygame.mixer.get_num_channels()
    pygame.mixer.stop()
    pygame.mixer.set_num_channels(1)
    try:
        if muted:
            game.sound.volume = 0
        else:
            blocker = game.sound.play("round_win")
            assert blocker is not None
        game.update_drone_warning(listener)
        assert game.ui.drone_warning is None and game.ui.drone_warning_waiting
        now += 125_000_000
        if muted:
            assert not pygame.mixer.get_busy()
            game.sound.volume = 0.8
        else:
            blocker.stop()
        if clear_mark:
            listener.status.pop("owl_drone_spotted")
        game.update_drone_warning(listener)
        assert game.ui.drone_warning_waiting is None
        if clear_mark:
            assert game.ui.drone_warning is None and not pygame.mixer.get_busy()
        else:
            warning = game.ui.drone_warning
            original = pygame.sndarray.array(game.sound.sounds["ab_alarm"])
            frames = round(0.125 * pygame.mixer.get_init()[0])
            assert np.array_equal(pygame.sndarray.array(warning.get_sound()), np.roll(original, -frames, axis=0))
            game.update_drone_warning(listener)
            assert game.ui.drone_warning is warning and warning.get_busy()
    finally:
        game.update_drone_warning(None)
        pygame.mixer.stop()
        pygame.mixer.set_num_channels(count)


def test_drone_warning_follows_spectated_teammate() -> None:
    import numpy as np

    from gameplay.net import apply_snapshot

    game = Game(args(team_size=3))
    host = game.match
    host.start()
    host.phase = "live"
    me = host.players[game.me]
    me.alive = False
    marked, other = sorted((p for p in host.players.values() if p.team == me.team and p is not me),
                           key=lambda p: p.pid)
    marked.status["owl_drone_spotted"] = host.time + 2
    marked.passive_state["owl_drone_spotted_at"] = host.time
    host.time += 0.125
    replica = type(host)(host.world, host.cfg, agent_roster=host.agents)
    apply_snapshot(replica, host.snapshot(me.pid), me.pid)
    game.match = replica
    me = replica.players[me.pid]
    assert game.view_player(me).pid == marked.pid
    game.audio_tick(me, spike_listener=game.view_player(me))
    warning = game.ui.drone_warning
    assert warning is not None and warning.get_busy()
    original = pygame.sndarray.array(game.sound.sounds["ab_alarm"])
    frames = round(0.125 * pygame.mixer.get_init()[0])
    assert np.array_equal(pygame.sndarray.array(warning.get_sound()), np.roll(original, -frames, axis=0))
    for volume in (0, 0.4):
        game.sound.volume = volume
        game.audio_tick(me, spike_listener=game.view_player(me))
        assert game.ui.drone_warning is warning and warning.get_busy()
    game.spectate_index += 1
    assert game.view_player(me).pid == other.pid
    game.audio_tick(me, spike_listener=game.view_player(me))
    assert game.ui.drone_warning is None and not warning.get_busy()
    game.spectate_index -= 1
    game.audio_tick(me, spike_listener=game.view_player(me))
    assert game.ui.drone_warning is not None and game.ui.drone_warning.get_busy()
    marked.status.pop("owl_drone_spotted")
    apply_snapshot(replica, host.snapshot(me.pid), me.pid)
    game.audio_tick(me, spike_listener=game.view_player(me))
    assert game.ui.drone_warning is None


@pytest.mark.parametrize("action", ["plant", "defuse"])
@pytest.mark.parametrize("blocked", [False, True])
def test_audible_cue_preempts_silent_spike_track(monkeypatch, action, blocked) -> None:
    from gameplay.geometry import Vec
    from gameplay.match import GameEvent

    game = Game(args())
    listener = game.match.players[game.me]
    listener.pos, listener.facing = Vec(10, 10), 0
    occluded = False
    monkeypatch.setattr(game, "occluded", lambda *_: occluded)
    count = pygame.mixer.get_num_channels()
    pygame.mixer.stop()
    pygame.mixer.set_num_channels(2)
    try:
        game.handle_events([GameEvent(f"{action}_start", 0, {"pid": 2, "pos": (10, 15)})])
        _, tracks = game.ui.spike_sounds[2]
        occluded = blocked
        game.update_spike_audio(listener)
        audible, audible_sample, _ = next(track for track in tracks if track[2] == blocked)
        silent, _, _ = next(track for track in tracks if track[2] != blocked)
        cue = game.sound.play("ui_click")
        assert cue is not None and cue.id == silent.id
        game.update_spike_audio(listener)
        assert audible.get_sound() == audible_sample
        assert cue.get_sound() == game.sound.sounds["ui_click"]
        cue.stop()
        game.update_spike_audio(listener)
        assert len(tracks) == 2 and audible.get_sound() == audible_sample
        game.handle_events([GameEvent(f"{action}_stop", 0, {"pid": 2})])
        assert not any(channel.get_busy() for channel, _, _ in tracks)
        assert not game.sound.silent_alternates
    finally:
        game.stop_spike_sound(2)
        pygame.mixer.stop()
        pygame.mixer.set_num_channels(count)


@pytest.mark.parametrize("action", ["plant", "defuse"])
@pytest.mark.parametrize("abort", [False, True])
def test_spike_audio_waits_for_free_channel(monkeypatch, action, abort) -> None:
    from client import events
    from gameplay.geometry import Vec
    from gameplay.match import GameEvent

    game = Game(args())
    listener = game.match.players[game.me]
    listener.pos, listener.facing = Vec(10, 10), 0
    monkeypatch.setattr(game, "occluded", lambda *_: False)
    now = 1_000_000_000
    monkeypatch.setattr(events, "monotonic_ns", lambda: now)
    count = pygame.mixer.get_num_channels()
    pygame.mixer.stop()
    pygame.mixer.set_num_channels(1)
    try:
        original = game.sound.sounds[f"spike_{action}"]
        blocker = game.sound.play("round_win")
        assert blocker is not None
        game.handle_events([GameEvent(f"{action}_start", 0, {"pid": 2, "pos": (10, 15)})])
        assert game.ui.spike_sounds[2][1] == []
        game.update_spike_audio(listener)
        assert blocker.get_sound() == game.sound.sounds["round_win"]
        if abort:
            game.handle_events([GameEvent(f"{action}_stop", 0, {"pid": 2})])
        now += 1_000_000_000
        blocker.stop()
        game.update_spike_audio(listener)
        if abort:
            assert not game.ui.spike_sounds and not pygame.mixer.get_busy()
        else:
            [(channel, sample, _)] = game.ui.spike_sounds[2][1]
            assert channel.get_sound() == sample
            assert sample.get_length() == pytest.approx(original.get_length() - 1, abs=0.001)
    finally:
        game.stop_spike_sound(2)
        pygame.mixer.stop()
        pygame.mixer.set_num_channels(count)


@pytest.mark.parametrize("preempt_primary", [False, True])
def test_audible_cue_preempts_silent_ability_track(monkeypatch, preempt_primary) -> None:
    from gameplay.geometry import Vec
    from gameplay.match import Effect

    game = Game(args())
    listener = game.match.players[game.me]
    listener.pos, listener.facing = Vec(10, 10), 0
    game.match.effects.append(Effect("zone", listener.pid, listener.team, Vec(10, 15),
                                     game.match.time + 5, 2, props={"sprite": "brimstone_incendiary_burning"}))
    blocked = False
    monkeypatch.setattr(game, "occluded", lambda *_: blocked)
    count = pygame.mixer.get_num_channels()
    pygame.mixer.stop()
    pygame.mixer.set_num_channels(2)
    try:
        game.update_incendiary_audio(listener)
        [main] = game.ui.fire_sounds.values()
        [(alternate, _)] = game.ui.effect_sound_alternates.values()
        blocked = preempt_primary
        game.update_incendiary_audio(listener)
        audible, silent = (alternate, main) if preempt_primary else (main, alternate)
        cue = game.sound.play("ui_click")
        assert cue is not None and cue.id == silent.id
        assert audible.get_busy()
        game.update_incendiary_audio(listener)
        assert cue.get_sound() == game.sound.sounds["ui_click"]
        cue.stop()
        game.update_incendiary_audio(listener)
        assert game.ui.effect_sound_alternates
        assert next(iter(game.ui.fire_sounds.values())) is audible
    finally:
        game.update_incendiary_audio(None)
        pygame.mixer.stop()
        pygame.mixer.set_num_channels(count)


@pytest.mark.parametrize("expires", [False, True])
@pytest.mark.parametrize("delay", ["busy", "muted", "out_of_range"])
def test_ability_loop_waits_until_audible(monkeypatch, expires, delay) -> None:
    import numpy as np

    from client import events
    from gameplay.geometry import Vec
    from gameplay.match import Effect

    game = Game(args())
    listener = game.match.players[game.me]
    listener.pos, listener.facing = Vec(10, 10), 0
    monkeypatch.setattr(game, "occluded", lambda *_: False)
    now = 1_000_000_000
    monkeypatch.setattr(events, "monotonic_ns", lambda: now)
    effect = Effect("zone", listener.pid, listener.team, Vec(10, 15), game.match.time + 5, 2, start=game.match.time,
                    props={"sprite": "brimstone_incendiary_burning"})
    game.match.effects.append(effect)
    count = pygame.mixer.get_num_channels()
    pygame.mixer.stop()
    pygame.mixer.set_num_channels(1)
    try:
        if delay == "muted":
            game.sound.volume = 0
        elif delay == "out_of_range":
            listener.pos = Vec(70, 70)
        else:
            blocker = game.sound.play("round_win")
            assert blocker is not None
        game.update_incendiary_audio(listener)
        assert not game.ui.fire_sounds
        assert bool(game.ui.effect_sound_waiting) == (delay != "out_of_range")
        now += 125_000_000
        game.match.time += 0.125
        if delay == "muted":
            assert not pygame.mixer.get_busy()
            game.sound.volume = 0.8
        elif delay == "out_of_range":
            listener.pos = Vec(10, 10)
        else:
            blocker.stop()
        if expires:
            game.match.time = effect.until
        game.update_incendiary_audio(listener)
        assert not game.ui.effect_sound_waiting
        if expires:
            assert not game.ui.fire_sounds and not pygame.mixer.get_busy()
        else:
            [channel] = game.ui.fire_sounds.values()
            original = pygame.sndarray.array(game.sound.sounds["incendiary_fire"])
            frames = round(0.125 * pygame.mixer.get_init()[0])
            assert np.array_equal(pygame.sndarray.array(channel.get_sound()), np.roll(original, -frames, axis=0))
    finally:
        game.update_incendiary_audio(None)
        pygame.mixer.stop()
        pygame.mixer.set_num_channels(count)


@pytest.mark.parametrize("channel_pressure", [False, True])
def test_spatial_ability_loop_keeps_both_tracks_on_occlusion_change(monkeypatch, channel_pressure) -> None:
    from unittest.mock import Mock

    from gameplay.geometry import Vec
    from gameplay.match import Effect

    game = Game(args())
    listener = game.match.players[game.me]
    listener.pos, listener.facing = Vec(10, 10), 0
    pos = Vec(10, 15)
    game.match.effects.append(Effect("zone", listener.pid, listener.team, pos, game.match.time + 5, 2,
                                     props={"sprite": "brimstone_incendiary_burning"}))
    blocked = False
    monkeypatch.setattr(game, "occluded", lambda *_: blocked)
    play, find = game.sound.play, pygame.mixer.find_channel
    from client import events
    now = 1_000_000_000
    monkeypatch.setattr(events, "monotonic_ns", lambda: now)
    monkeypatch.setattr(game.sound, "play", Mock(side_effect=lambda *a, **kw: Mock(wraps=play(*a, **kw))))
    monkeypatch.setattr(pygame.mixer, "find_channel", lambda: None if channel_pressure else Mock(wraps=find()))
    game.update_incendiary_audio(listener)
    [clear] = game.ui.fire_sounds.values()
    if channel_pressure:
        assert not game.ui.effect_sound_alternates
        now += 125_000_000
        monkeypatch.setattr(pygame.mixer, "find_channel", lambda: Mock(wraps=find()))
        game.update_incendiary_audio(listener)
    [(filtered, sample)] = game.ui.effect_sound_alternates.values()
    if channel_pressure:
        import numpy as np

        original = pygame.sndarray.array(game.sound.muffled["incendiary_fire"])
        frames = round(0.125 * pygame.mixer.get_init()[0])
        assert np.array_equal(pygame.sndarray.array(sample), np.roll(original, -frames, axis=0))
    try:
        for blocked in (True, False):
            game.update_incendiary_audio(listener)
            left, right, _ = game.sound.spatial_mix(listener, pos, 22, blocked, 0.75)
            audible, silent = (filtered, clear) if blocked else (clear, filtered)
            assert audible.set_volume.call_args.args == pytest.approx((left, right))
            assert silent.set_volume.call_args.args == (0, 0)
            assert clear.get_busy() and filtered.get_busy()
        game.sound.play.assert_called_once()
        filtered.play.assert_called_once()
    finally:
        game.update_incendiary_audio(None)
    assert not clear.get_busy() and not filtered.get_busy()
    assert not game.ui.effect_sound_alternates


def test_spatial_ability_loops_follow_spectated_teammate() -> None:
    from gameplay.geometry import Vec
    from gameplay.match import Effect
    from gameplay.net import apply_snapshot
    from gameplay.world import WorldMap

    game = Game(args(team_size=3))
    host = game.match
    host.world = WorldMap("test", "Test", 150, 150)
    host.start()
    host.phase, host.phase_until = "live", host.time + 60
    me = host.players[game.me]
    near, far = sorted((p for p in host.players.values() if p.team == me.team and p is not me),
                       key=lambda p: p.pid)
    me.alive = False
    me.pos = far.pos = Vec(100, 100)
    near.pos, near.facing = Vec(15, 10), 0
    for sprite in ("brimstone_incendiary_burning", "sova_owl_drone"):
        host.effects.append(Effect("zone", near.pid, near.team, Vec(15, 15), host.time + 5, 2,
                                   props={"sprite": sprite}))
    replica = type(host)(host.world, host.cfg, agent_roster=host.agents)
    apply_snapshot(replica, host.snapshot(me.pid), me.pid)
    game.match = replica
    me = replica.players[me.pid]
    game.audio_tick(me, spike_listener=game.view_player(me))
    [fire] = game.ui.fire_sounds.values()
    [rotor] = game.ui.rotor_sounds.values()
    assert fire.get_busy() and rotor.get_busy()
    for volume in (0, 0.4):
        game.sound.volume = volume
        game.audio_tick(me, spike_listener=game.view_player(me))
        assert next(iter(game.ui.fire_sounds.values())) is fire and fire.get_busy()
        assert next(iter(game.ui.rotor_sounds.values())) is rotor and rotor.get_busy()
    game.spectate_index += 1
    game.audio_tick(me, spike_listener=game.view_player(me))
    assert not game.ui.fire_sounds and not game.ui.rotor_sounds
    assert not fire.get_busy() and not rotor.get_busy()


def test_spectator_camera_turns_smoothly() -> None:
    game = Game(args(team_size=3))
    game.match.start()
    game.match.phase, game.match.phase_until = "live", game.match.time + 100
    me = game.match.players[game.me]
    game.match._kill(None, me, "test", "body")
    first = game.view_player(me)
    mate = game.match.players[first.pid]
    mate.facing = (first.facing + 170.0) % 360.0  # the teammate snaps round
    game.match.time += 1 / 60
    cam = game.view_player(me)
    turned = abs((cam.facing - first.facing + 540) % 360 - 180)
    assert 0 < turned < 60, "the camera follows, but not in one jump"


@pytest.mark.parametrize(("agent", "slot"), [("phoenix", "Q"), ("brimstone", "C")])
def test_throwable_in_hand_draws_its_aim_preview(agent, slot) -> None:
    game = Game(args(agent=agent))
    game.match.start()
    me = game.match.players[game.me]
    ab = game.match.agents[me.agent]["abilities"][slot]
    assert game.is_throwable(ab) and game.needs_aim(me, slot)
    game.aiming = slot
    game.draw()


def test_buy_menu_sells_with_a_second_click_and_surrender_ends_the_match() -> None:
    game = Game(args())
    game.match.start()
    me = game.match.players[game.me]
    me.credits = 5000
    game.match.buy(me, "vandal")
    assert game.item_sellable(me, "vandal")
    game.ui.buy_open = True
    game.draw()
    vandal = next(rect for rect, key, _ in game.buy_layout() if key == "vandal")
    action = game.buy_action_at(me, game.buy_item_at(vandal.center), vandal.center)
    assert action == "sell:vandal"
    game.step(1 / 64, Command(buy=[action, action]))
    assert me.credits == 5000 and "primary" not in me.weapons
    game.ui.buy_open = False
    game.open_overlay("pause")
    game.draw_overlay()
    assert any(h.action == "surrender" for h in game.kit.hits)
    game.overlay = "surrender"
    game.draw_overlay()
    yes = next(h for h in game.kit.hits if h.action == "surrender_yes")
    for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        game.overlay_event(pygame.event.Event(kind, button=1, pos=yes.rect.center))
    assert game.match.phase == "over"


def test_multi_placement_marks_with_left_and_confirms_with_right_click() -> None:
    from gameplay.geometry import Vec

    game = Game(args(agent="brimstone"))
    game.match.start()
    me = game.match.players[game.me]
    assert me.agent == "brimstone"
    me.charges["E"] = 3
    rect, scale = game.tactical_layout()
    origin = (round(rect.left + me.pos.x * scale), round(rect.top + (game.match.world.height - me.pos.y) * scale))
    clicks = [(origin[0] - 8, origin[1]), (origin[0] + 8, origin[1])]
    targets = [Vec((x - rect.left) / scale, game.match.world.height - (y - rect.top) / scale) for x, y in clicks]
    pygame.event.clear()
    _post_key(game.keys["ability_e"])
    for click in clicks:
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=click))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=clicks[-1]))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    game.run()
    assert [effect.pos for effect in game.match.effects if effect.kind == "smoke"] == targets
    assert me.charges["E"] == 1 and game.aiming is None


@pytest.mark.parametrize("release", [False, True])
def test_breach_fault_line_casts_on_primary_release(release: bool) -> None:
    game = Game(args(agent="breach"))
    game.match.start()
    me = game.match.players[game.me]

    pygame.event.clear()
    _post_key(game.keys["ability_e"])
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 360)))
    if release:
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(640, 360)))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    game.run()

    waves = [e for e in game.match.effects if e.kind == "zone" and e.owner == me.pid]
    assert me.charges["E"] == (0 if release else 1)
    if release:
        [wave] = waves
        assert (wave.a - me.pos).length() == pytest.approx(8)
        assert (wave.b - wave.a).length() == pytest.approx(8, abs=0.06)
    else:
        assert not waves


@pytest.mark.parametrize(("agent", "slot", "button", "elapsed", "re_equip", "charges_left"), [
    ("omen", "Q", None, 1100, False, 1),
    ("omen", "Q", 3, 1100, False, 1),
    ("omen", "Q", 1, 1099, False, 1),
    ("omen", "Q", 1, 1100, False, 0),
    ("omen", "Q", 1, 1099, True, 1),
    ("omen", "Q", 1, 1100, True, 0),
    ("omen", "C", 1, 499, False, 1),
    ("omen", "C", 1, 500, False, 0),
    ("sova", "C", None, 900, False, 1),
    ("sova", "C", 3, 900, False, 1),
    ("sova", "C", 1, 899, False, 1),
    ("sova", "C", 1, 900, False, 0),
    ("sova", "C", 1, 899, True, 1),
    ("sova", "C", 1, 900, True, 0),
])
def test_timed_abilities_cast_after_equipping(
    monkeypatch, agent: str, slot: str, button: int | None, elapsed: int, re_equip: bool, charges_left: int
) -> None:
    from gameplay.geometry import Vec
    from gameplay.world import WorldMap

    game = Game(args(agent=agent))
    game.match.world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(25, 25)], 1: [Vec(75, 75)]})
    game.match.start()
    game.seen_round = game.match.round_no
    me = game.match.players[game.me]
    me.charges[slot] = 1

    equip = pygame.event.Event(pygame.KEYDOWN, key=game.keys[f"ability_{slot.lower()}"])
    frames = [(0, [equip])]
    if re_equip:
        frames.extend([(500, [equip]), (700, [equip])])
    last_equip = frames[-1][0]
    clicks = []
    if button is not None:
        clicks.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button, pos=(640, 360)))
    clicks.extend([pygame.event.Event(pygame.QUIT), pygame.event.Event(pygame.QUIT)])
    frames.append((last_equip + elapsed, clicks))
    pending = iter(frames)
    now = 0

    def next_events():
        nonlocal now
        now, events = next(pending)
        return events

    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now)
    monkeypatch.setattr(pygame.event, "get", next_events)
    game.run()
    assert me.charges[slot] == charges_left
    kind = "sensor" if agent == "sova" else "zone"
    assert any(e.kind == kind and e.owner == me.pid for e in game.match.effects) == (charges_left == 0)


@pytest.mark.parametrize(("elapsed", "confirm", "cast", "depth", "distance"), [
    (599, "ability", False, 24, 24),
    (600, "click", False, 24, 24),
    (600, "cancel", False, 24, 24),
    (600, "ability", True, 24, 24),
    (600, "ability", True, 80, 80),
    (600, "ability", True, 80.01, 80),
])
def test_omen_dark_cover_uses_the_shadow_camera_and_the_ability_key(
    monkeypatch, elapsed: int, confirm: str, cast: bool, depth: float, distance: float
) -> None:
    from gameplay.geometry import Vec, heading
    from gameplay.world import WorldMap

    world = WorldMap("test", "Test", 110, 110, spawns={0: [Vec(20, 20)], 1: [Vec(100, 100)]})
    monkeypatch.setattr("client.game.load_playable_map", lambda _key: world)
    game = Game(args(agent="omen"))
    game.match.start()
    game.seen_round = game.match.round_no
    me = game.match.players[game.me]
    me.facing = game.local_facing = 9
    game.cursor_depth = depth
    target = me.pos + heading(me.facing) * distance
    hints = []
    markers = []
    monkeypatch.setattr(game, "ability_hint", lambda text, _color: hints.append(text))
    monkeypatch.setattr(game, "radius_ring", lambda point, radius, *_: markers.append((point, radius)))
    now = 0
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now)

    equip = pygame.event.Event(pygame.KEYDOWN, key=game.keys["ability_e"])
    inputs = [pygame.event.Event(pygame.KEYDOWN, key=game.keys["reload"])]
    if confirm == "click":
        inputs.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 360)))
    else:
        inputs.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE if confirm == "cancel" else equip.key))
    inputs.extend([pygame.event.Event(pygame.QUIT), pygame.event.Event(pygame.QUIT)])
    first_frame = True

    def next_events():
        nonlocal first_frame, now
        if first_frame:
            first_frame = False
            return [equip]
        assert game.aiming == "E" and game.tactical_ability(me) is None
        assert game.camera(me)[0] == target
        assert any(hint.startswith(f"Dark Cover · {distance:.1f} m") for hint in hints)
        assert (target, 4.1) in markers
        now = elapsed
        return inputs

    monkeypatch.setattr(pygame.event, "get", next_events)
    game.run()
    assert not game.shadow_view and game.aiming is None
    assert me.charges["E"] == (0 if cast else 1)
    smokes = [e for e in game.match.effects if e.kind == "smoke" and e.owner == me.pid]
    assert bool(smokes) == cast
    if cast:
        [smoke] = smokes
        assert (smoke.pos - target).length() == pytest.approx(0)


@pytest.mark.parametrize(("wheel", "ground", "height_steps", "lift"), [
    ((-1,), 0, (), 0.0),
    ((-1, 1), 3, (), 0.0),
    ((-1,), 0, (12,), 2.8),
    ((-1, 1), 3, (15, -2), 2.5),
    ((-1, 1), 3, (3, -1), 0.5),
    ((-1, 1), 3, (1, -2), 0.0),
])
def test_dark_cover_scroll_selects_and_displays_the_deck_floor(
    monkeypatch, wheel: tuple[int, ...], ground: int, height_steps: tuple[int, ...], lift: float
) -> None:
    from gameplay.geometry import Rect, Vec
    from gameplay.world import Deck, WorldMap

    target = Vec(20, 44)
    deck = Deck(Rect(16, 40, 24, 48), 3, 0)
    world = WorldMap("test", "Test", 100, 100, decks=[deck], spawns={0: [Vec(20, 20)], 1: [Vec(90, 90)]})
    monkeypatch.setattr("client.game.load_playable_map", lambda _key: world)
    game = Game(args(agent="omen"))
    game.match.start()
    game.seen_round = game.match.round_no
    game.cursor_depth = 24
    hints, cutaways = [], []
    monkeypatch.setattr(game, "ability_hint", lambda text, _color: hints.append(text))
    monkeypatch.setattr(game, "draw_deck_cutaways", lambda _me, floors: cutaways.append(floors))
    equip = pygame.event.Event(pygame.KEYDOWN, key=game.keys["ability_e"])
    frames = iter([(0, [equip]), (200, [pygame.event.Event(pygame.MOUSEWHEEL, y=y) for y in wheel]),
                   (400, [pygame.event.Event(pygame.MOUSEWHEEL, y=y) for y in height_steps]),
                   (600, [equip, pygame.event.Event(pygame.QUIT), pygame.event.Event(pygame.QUIT)])])
    now = 0

    def next_events():
        nonlocal now
        now, events = next(frames)
        if now == 600:
            assert f"· Floor {ground} ·" in hints[-1]
            assert (f"Drop {lift:g} m" in hints[-1]) if lift else ("Drop" not in hints[-1])
            assert cutaways[-1][deck] == (ground == 3)
        return events

    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now)
    monkeypatch.setattr(pygame.key, "get_mods", lambda: pygame.KMOD_CTRL if now == 400 else 0)
    monkeypatch.setattr(pygame.event, "get", next_events)
    game.run()
    [smoke] = [effect for effect in game.match.effects if effect.kind == "smoke"]
    assert smoke.pos == target and smoke.props["settled_ground"] == ground
    assert smoke.fall_offset(smoke.start) == pytest.approx(lift)
    if lift:
        assert smoke.fall_offset(smoke.start + 0.2) == pytest.approx(max(0, lift - 1))
        assert smoke.fall_offset(smoke.start + 1) == 0


def test_dark_cover_client_rejects_raised_target_at_horizontal_limit(monkeypatch) -> None:
    from gameplay.geometry import Vec
    from gameplay.world import WorldMap

    world = WorldMap("test", "Test", 110, 110, spawns={0: [Vec(20, 20)], 1: [Vec(100, 100)]})
    monkeypatch.setattr("client.game.load_playable_map", lambda _key: world)
    game = Game(args(agent="omen"))
    game.match.start()
    game.seen_round = game.match.round_no
    game.cursor_depth = 80
    hints = []
    monkeypatch.setattr(game, "ability_hint", lambda text, _color: hints.append(text))
    equip = pygame.event.Event(pygame.KEYDOWN, key=game.keys["ability_e"])
    frames = iter([(0, [equip]), (200, [pygame.event.Event(pygame.MOUSEWHEEL, y=12)]),
                   (600, [equip, pygame.event.Event(pygame.QUIT), pygame.event.Event(pygame.QUIT)])])
    now = 0

    def next_events():
        nonlocal now
        now, events = next(frames)
        return events

    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now)
    monkeypatch.setattr(pygame.key, "get_mods", lambda: pygame.KMOD_CTRL)
    monkeypatch.setattr(pygame.event, "get", next_events)
    game.run()
    assert any("Dark Cover · 80.1 m" in hint and "Out of range" in hint for hint in hints)
    assert game.match.players[game.me].charges["E"] == 1
    assert not any(e.kind == "smoke" for e in game.match.effects)


def test_ascent_deck_prefers_an_on_screen_enemy_then_the_own_floor() -> None:
    from gameplay.geometry import Vec

    game = Game(args())
    m = game.match
    m.start()
    m.phase = "live"
    me = m.players[game.me]
    enemy = next(p for p in m.players.values() if p.team != me.team)
    [deck] = m.world.decks
    me.pos, me.facing, me.ground, me.level = Vec(116, m.world.height - 39), 0, deck.lower, int(deck.lower)
    enemy.pos = Vec(116, m.world.height - 33)
    enemy.ground = enemy.level = deck.level
    assert m.can_see(me, enemy)
    assert game.deck_view_upper(deck, me)
    game.draw()
    me.pos = Vec(116, m.world.height - 51)
    assert not game.deck_view_upper(deck, me)
