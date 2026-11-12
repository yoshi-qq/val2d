"""Lobby rules: set only in the lobby, play out all rounds, cheats only while cheats are allowed, sent to clients."""
from __future__ import annotations

from gameplay.geometry import Vec
from gameplay.match import Command, Match
from gameplay.net import apply_snapshot
from map_fixtures import load_archived_map


def lobby() -> tuple[Match, int, int]:
    m = Match(load_archived_map("workyard"), seed=5)
    a = m.add_player("A", 0, "omen").pid
    b = m.add_player("B", 1, "omen", is_bot=True).pid
    return m, a, b


def test_rules_change_only_in_the_lobby() -> None:
    m, _, _ = lobby()
    assert m.set_rules(play_all_rounds=True, win_rounds=5)
    assert m.cfg.lobby.play_all_rounds and m.win_rounds == 5
    m.start()
    assert not m.set_rules(allow_cheats=True) and not m.cfg.lobby.allow_cheats


def test_cheats_need_allow_cheats() -> None:
    m, a, _ = lobby()
    m.set_rules(infinite_ammo=True)
    assert not m.cheat("infinite_ammo")
    m.set_rules(allow_cheats=True)
    assert m.cheat("infinite_ammo")


def test_infinite_ammo_abilities_and_invincibility() -> None:
    m, a, b = lobby()
    m.set_rules(allow_cheats=True, infinite_ammo=True, infinite_abilities=True, invincibility=True)
    m.start()
    m.phase, m.phase_until = "live", m.time + 100
    pa, pb = m.players[a], m.players[b]
    pa.pos, pb.pos, pa.facing = Vec(17, 15), Vec(17, 23), 0.0
    mag = pa.weapon.mag
    for _ in range(20):
        pa.next_shot = 0.0
        pa.prev_fire = False
        m.tick(1 / 64, {a: Command(facing=180.0, cursor_depth=8.0, fire=True)})  # away from B: the round goes on
    assert pa.weapon.mag == mag
    pa.charges["C"] = 0
    pa.prev_ability = None
    before = len(m.effects)
    m.tick(1 / 64, {a: Command(facing=0.0, cursor_depth=6.0, ability="C")})
    assert len(m.effects) > before or m.events  # the flash went out without a charge
    m._damage(pb, pa, 80, "body", "test")
    assert pa.hp == 100
    m._damage(pa, pb, 80, "body", "test")
    assert pb.hp < 100  # bots are not invincible


def test_play_out_all_rounds() -> None:
    m, _, _ = lobby()
    m.set_rules(play_all_rounds=True, win_rounds=5, overtime=True)
    m.start()
    m.score = [4, 0]
    assert not m._match_decided()  # first to 5 would be decided at 5:0; all rounds means 8 regulation rounds
    m.score = [5, 3]
    assert m._match_decided()
    m.score = [4, 4]
    assert not m._match_decided()  # tie after regulation: overtime


def test_rules_reach_the_client() -> None:
    host, _, _ = lobby()
    host.set_rules(allow_cheats=True, bullet_tracers=True, all_around_sight=True)
    host.start()
    client = Match(load_archived_map("workyard"))
    apply_snapshot(client, host.snapshot(), own_pid=1)
    assert client.cheat("bullet_tracers") and client.cfg.lobby.all_around_sight


def test_planting_stopped_early_sends_a_stop_for_the_sound() -> None:
    m, a, _ = lobby()
    m.start()
    m.phase, m.phase_until = "live", m.time + 100
    p = m.players[a]
    m.spike_carrier = a
    site = m.world.sites[0]
    p.pos = site.rect.center
    m.tick(1 / 64, {a: Command(interact=True)})
    assert p.plant_progress > 0
    events = m.tick(1 / 64, {a: Command(interact=False)})
    assert any(e.kind == "plant_stop" for e in events)


def test_agent_built_from_the_ability_library() -> None:
    from gameplay.kit import check_ability
    from gameplay.kit.dsl import agent, library
    built = agent("Lib", C=library("firebomb", price=300), Q=library("cloak_step"), E=library("haste_aura"),
                  X=library("healing_rain"))
    assert built["abilities"]["C"]["price"] == 300
    assert all(not check_ability(ab) for ab in built["abilities"].values())
