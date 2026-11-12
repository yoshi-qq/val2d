"""Smaller Valorant rules: selling, old gun drops on a new buy, low props, cover and crouching, tagging, assists,
orbs, survivor credits, round titles, surrender, body blocking."""
from __future__ import annotations

from gameplay.geometry import Vec
from gameplay.match import Command, Match
from gameplay.world import parse_map

RAW = {"name": "Test", "width": 30, "height": 20,
       "walls": [], "crates": [[14, 9, 16, 11]], "objects": [{"key": "barrel", "pos": [15, 4]}],
       "sites": [{"name": "A", "rect": [24, 2, 28, 6]}, {"name": "B", "rect": [24, 14, 28, 18]}],
       "spawns": {"0": [[2, 10]], "1": [[28, 10]]}, "spawn_zones": {"0": [0, 0, 5, 20], "1": [25, 0, 30, 20]}}


def setup(buy_phase: bool = False) -> tuple[Match, int, int]:
    m = Match(parse_map("test", RAW), seed=1)
    a = m.add_player("A", 0, "kestrel").pid
    b = m.add_player("B", 1, "kestrel", is_bot=True).pid
    m.start()
    if not buy_phase:
        m.phase, m.phase_until = "live", m.time + 100
    return m, a, b


def test_selling_a_gun_bought_this_buy_phase_refunds_it() -> None:
    m, a, _ = setup(buy_phase=True)
    p = m.players[a]
    p.credits = 5000
    assert m.buy(p, "assault_rifle") and p.credits == 2100
    assert m.buy(p, "assault_rifle") and p.credits == 5000 and "primary" not in p.weapons  # second click sells


def test_a_new_gun_drops_the_old_one_and_selling_brings_it_back() -> None:
    m, a, _ = setup(buy_phase=True)
    p = m.players[a]
    p.credits = 9000
    m.buy(p, "burst_rifle")
    first = p.weapons["primary"]
    m.purchases_done = True
    p.purchases.clear()  # as if bought last round: no longer sellable
    m.buy(p, "assault_rifle")
    assert any(d.key == "burst_rifle" for d in m.drops)
    m.sell(p, "assault_rifle")
    assert p.weapons["primary"] is first and not any(d.key == "burst_rifle" for d in m.drops)


def test_dropped_guns_cannot_be_sold() -> None:
    m, a, _ = setup(buy_phase=True)
    p = m.players[a]
    p.credits = 3000
    m.buy(p, "assault_rifle")
    m.spike_carrier = None  # G would drop the bomb first
    m._drop(p)
    assert not m.sellable(p, "assault_rifle")


def test_low_props_do_not_block_sight_but_crouching_behind_a_crate_hides() -> None:
    m, a, b = setup()
    pa, pb = m.players[a], m.players[b]
    pa.pos, pb.pos, pa.facing = Vec(15, 1), Vec(15, 6), 0.0  # barrel at 15,4 between them
    assert m.can_see(pa, pb)
    pa.pos, pb.pos = Vec(15, 2), Vec(15, 11.6)  # crate 14-16 / 9-11 between, B right behind it
    assert m.can_see(pa, pb)
    pb.crouching = True
    assert not m.can_see(pa, pb)


def test_tagging_slows_after_a_hit() -> None:
    m, a, b = setup()
    pa, pb = m.players[a], m.players[b]
    pa.pos, pb.pos, pa.facing = Vec(10, 15), Vec(10, 20 - 1.5), 0.0
    base = m._max_speed(pb)
    pa.next_shot = 0.0
    m.tick(1 / 64, {a: Command(facing=0.0, cursor_depth=3.5, fire=True)})
    assert pb.hp < 100 and m._max_speed(pb) < base * 0.5


def test_assists_count_teammates_who_damaged_the_victim() -> None:
    m = Match(parse_map("test", RAW), seed=1)
    a = m.add_player("A", 0, "kestrel").pid
    c = m.add_player("C", 0, "kestrel", is_bot=True).pid
    b = m.add_player("B", 1, "kestrel", is_bot=True).pid
    m.start()
    m.phase = "live"
    m._damage(m.players[c], m.players[b], 30, "body", "test")
    m._damage(m.players[a], m.players[b], 90, "body", "test")
    assert m.players[a].kills == 1 and m.players[c].assists == 1


def test_orb_gives_an_ultimate_point() -> None:
    m, a, _ = setup()
    p = m.players[a]
    assert m.orbs
    p.pos, before = m.orbs[0], p.ult_points
    for _ in range(70):
        m.tick(1 / 64, {a: Command(interact=True)})
    assert p.ult_points == before + 1 and len(m.orbs) == 1


def test_survivors_of_a_lost_round_without_plant_get_1000() -> None:
    m, a, b = setup()
    attackers = [p for p in m.players.values() if m.side(p.team) == "attack"]
    p = attackers[0]
    before = p.credits
    m._end_round(1 - p.team, "Time ran out")
    assert p.credits - before == 1000


def test_flawless_and_surrender() -> None:
    m, a, b = setup()
    m._kill(m.players[a], m.players[b], "test", "body")
    assert m.surrender(m.players[b].team) and m.phase == "over" and m.match_winner == m.players[a].team


def test_players_do_not_walk_through_each_other() -> None:
    m, a, b = setup()
    pa, pb = m.players[a], m.players[b]
    pa.pos, pb.pos = Vec(10, 15), Vec(10, 16)
    for _ in range(64):
        m.tick(1 / 64, {a: Command(move_y=1.0, facing=0.0), b: Command(facing=180.0)})
    assert (pa.pos - pb.pos).length() >= 0.75
