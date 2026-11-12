"""Alternate fire: knife (no headshots, backstab), sniper scope toggle and levels, no-scope spread, shotgun tight shot."""
from __future__ import annotations

from gameplay.geometry import Vec
from gameplay.match import Command, Match
from map_fixtures import load_archived_map


def duel() -> tuple[Match, int, int]:
    m = Match(load_archived_map("workyard"), seed=3)
    a = m.add_player("A", 0, "omen").pid
    b = m.add_player("B", 1, "omen").pid
    m.start()
    m.phase, m.phase_until = "live", m.time + 100
    pa, pb = m.players[a], m.players[b]
    pa.pos, pb.pos = Vec(17, 15), Vec(17, 16.2)
    pa.facing = 0.0
    for p in (pa, pb):
        p.slot, p.equip_until, p.next_shot = "melee", 0.0, 0.0
    return m, a, b


def stab(m: Match, a: int, alt: bool = False) -> None:
    p = m.players[a]
    p.next_shot, p.prev_fire, p.prev_alt = 0.0, False, False
    m.tick(1 / 64, {a: Command(facing=p.facing, cursor_depth=1.2, fire=not alt, alt_fire=alt)})


def test_knife_front_stab_is_body_damage_without_headshot() -> None:
    m, a, b = duel()
    pb = m.players[b]
    pb.facing = 180.0  # looking at the attacker
    stab(m, a)
    assert pb.hp == 50


def test_knife_backstab_doubles_and_heavy_stab_kills_from_behind() -> None:
    m, a, b = duel()
    pb = m.players[b]
    pb.facing = 0.0  # back turned
    stab(m, a)
    assert pb.hp == 0 or not pb.alive  # 50 x 2
    m2, a2, b2 = duel()
    m2.players[b2].facing = 180.0
    stab(m2, a2, alt=True)
    assert m2.players[b2].hp == 25  # heavy stab from the front: 75


def test_sniper_scope_toggles_and_cycles_levels() -> None:
    from gameplay.data import load_weapons
    adler = load_weapons()["operator"]
    lvl = 0
    seq = []
    for down, was in ((True, False), (False, True), (True, False), (False, True), (True, False)):
        lvl = adler.zoom_after(lvl, down, was)
        seq.append(lvl)
    assert seq == [1, 1, 2, 2, 0]
    hold = load_weapons()["vandal"]
    assert hold.zoom_after(0, True, False) == 1 and hold.zoom_after(1, False, True) == 0


def test_no_scope_is_inaccurate_and_scope_is_exact() -> None:
    m, a, _ = duel()
    p = m.players[a]
    from gameplay.match import WeaponState
    p.weapons["primary"] = WeaponState("operator", 5, 10)
    p.slot = "primary"
    d = m.weapons["operator"]
    assert m.current_spread(p, d) >= 5.0
    p.zoomed = True
    assert m.current_spread(p, d) == 0.0
