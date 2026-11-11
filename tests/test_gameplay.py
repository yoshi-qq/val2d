"""Tests for the game core (without pygame)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gameplay.bots import BotDirector
from gameplay.data import HitZoneConfig, load_weapons
from gameplay.geometry import Vec, heading
from gameplay.hitzones import resolve_zone
from gameplay.match import Command, Match
from gameplay.world import load_map

CFG = HitZoneConfig()
UP = heading(0)


def zone(target: Vec, cursor_depth: float, same_level: bool = True, cursor_level: bool = True) -> str | None:
    return resolve_zone(Vec(0, 0), UP, UP, cursor_depth, target, same_level, cursor_level, CFG).zone


def test_hitzone_head_when_cursor_on_target() -> None:
    assert zone(Vec(0, 10), 10) == "head"


def test_hitzone_head_missed_sideways_gives_body() -> None:
    assert zone(Vec(0.3, 10), 10) == "body"


def test_hitzone_depth_off_gives_body_then_legs() -> None:
    assert zone(Vec(0, 10), 8) == "body"
    assert zone(Vec(0, 10), 2) == "legs"


def test_hitzone_at_least_legs_far_sideways_within_body() -> None:
    assert zone(Vec(0.35, 10), 1) == "legs"


def test_hitzone_miss_outside_body_and_other_level() -> None:
    assert zone(Vec(0.5, 10), 10) is None
    assert zone(Vec(0, 10), 10, same_level=False) is None
    assert zone(Vec(0, 10), 10, cursor_level=False) is None


def duel(seed: int = 1) -> tuple[Match, int, int]:
    m = Match(load_map("werkhof"), seed=seed)
    a = m.add_player("A", 0, "kestrel").pid
    b = m.add_player("B", 1, "marrow").pid
    m.start()
    return m, a, b


def run(m: Match, seconds: float, cmds: dict[int, Command] | None = None, dt: float = 1 / 64) -> None:
    for _ in range(int(seconds / dt)):
        m.tick(dt, cmds or {})


def test_buy_phase_then_live() -> None:
    m, a, _ = duel()
    assert m.phase == "buy"
    assert m.buy(m.players[a], "hornisse")
    assert m.players[a].credits == 800 - m.weapons["hornisse"].price
    run(m, 31)
    assert m.phase == "live"


def test_first_shot_standing_is_exact_and_kills_with_headshots() -> None:
    m, a, b = duel()
    pa, pb = m.players[a], m.players[b]
    run(m, 31)
    pa.pos, pb.pos = Vec(24, 16), Vec(24, 24)  # mid, clear sight? the pillar at 22-26/18-22 blocks
    pa.pos, pb.pos = Vec(17, 15), Vec(17, 25)
    pa.facing = 0.0
    d = m.weapons["spatz"]
    assert m.current_spread(pa, d) == 0.0
    shots = 0
    while pb.alive and shots < 10:
        m.tick(1 / 64, {a: Command(facing=0.0, cursor_depth=10.0, fire=True)})
        m.tick(0.2, {a: Command(facing=0.0, cursor_depth=10.0, fire=False)})
        shots += 1
    assert not pb.alive
    assert m.phase == "end" and m.round_winner == 0


def test_armor_absorbs_damage() -> None:
    m, a, b = duel()
    pa, pb = m.players[a], m.players[b]
    pb.armor = 50
    m._damage(pa, pb, 40, "body", "test")
    assert pb.hp == 100 - (40 - 26) and pb.armor == 50 - 26


def test_wall_penetration_by_level() -> None:
    m, a, b = duel()
    pa, pb = m.players[a], m.players[b]
    run(m, 31)
    pa.pos, pb.pos = Vec(12, 20), Vec(17, 20)
    # target behind a thin wall (x 14..15, 1 m thick): the sidearm (level 0) penetrates level 0
    m.tick(1 / 64, {a: Command(facing=90.0, cursor_depth=5.0, fire=True)})
    assert pb.hp < 100
    hp = pb.hp
    # thick pillar (level 3) stops everything
    pa.pos, pb.pos = Vec(20, 20), Vec(28, 20)
    m.tick(0.5, {a: Command(facing=90.0, cursor_depth=8.0)})
    m.tick(1 / 64, {a: Command(facing=90.0, cursor_depth=8.0, fire=True)})
    assert pb.hp == hp


def test_plant_and_explode_gives_attackers_round() -> None:
    m, a, b = duel()
    run(m, 31)
    pa = m.players[a]
    assert m.spike_carrier == a
    pa.pos = Vec(8, 30)
    run(m, 4.2, {a: Command(interact=True)})
    assert m.phase == "planted"
    credits = pa.credits
    m.players[b].pos = Vec(40, 2)
    run(m, 46)
    assert m.round_winner == 0
    assert pa.credits > credits


def test_defuse_with_checkpoint() -> None:
    m, a, b = duel()
    run(m, 31)
    pa, pb = m.players[a], m.players[b]
    pa.pos = Vec(8, 30)
    run(m, 4.2, {a: Command(interact=True)})
    pb.pos = Vec(8.5, 30)
    run(m, 4.0, {b: Command(interact=True)})
    run(m, 0.5)
    assert pb.defuse_progress == 3.5
    run(m, 3.7, {b: Command(interact=True)})
    assert m.round_winner == 1


def test_loss_streak_economy() -> None:
    m, a, b = duel()
    for expected in (1800, 2300, 2800, 2800):
        before = m.players[b].credits
        m._end_round(0, "test")
        assert m.players[b].credits - before == expected or m.players[b].credits == 9000
        m.phase = "live"


def test_side_switch_and_overtime_win_by_two() -> None:
    m, _, _ = duel()
    m.score = [12, 12]
    m.round_no = 24
    m.phase = "live"
    m._end_round(0, "test")
    assert m.match_winner is None
    m.phase = "live"
    m._end_round(0, "test")
    assert m.match_winner == 0


def test_abilities_smoke_blocks_sight_and_dash_moves() -> None:
    m, a, b = duel()
    run(m, 31)
    pa, pb = m.players[a], m.players[b]
    pa.pos, pb.pos = Vec(17, 15), Vec(17, 25)
    pa.facing = pb.facing = 0.0
    pb.facing = 180.0
    assert m.can_see(pb, pa)
    m.tick(1 / 64, {b: Command(facing=180.0, cursor_depth=5.0, ability="E")})
    assert any(e.kind == "smoke" for e in m.effects)
    assert not m.can_see(pb, pa)
    start = pa.pos
    m.tick(1 / 64, {a: Command(facing=90.0, ability="E")})
    run(m, 0.3)
    assert (pa.pos - start).length() > 4.0


def test_flash_blinds_viewer() -> None:
    m, a, b = duel()
    run(m, 31)
    pa, pb = m.players[a], m.players[b]
    pa.pos, pb.pos = Vec(17, 15), Vec(17, 25)
    pa.charges["C"] = 1
    pb.facing = 180.0
    m.tick(1 / 64, {a: Command(facing=0.0, cursor_depth=6.0, ability="C")})
    run(m, 0.6, {b: Command(facing=180.0)})
    assert pb.blind_until > m.time


def test_weapons_complete() -> None:
    w = load_weapons()
    assert len([k for k, d in w.items() if d.slot == "primary"]) >= 12
    assert len([k for k, d in w.items() if d.slot == "sidearm"]) >= 4


def test_bot_match_runs_to_end() -> None:
    m = Match(load_map("werkhof"), seed=3)
    for i in range(5):
        m.add_player(f"Bot A{i}", 0, "kestrel" if i % 2 else "marrow", is_bot=True)
        m.add_player(f"Bot B{i}", 1, "marrow" if i % 2 else "kestrel", is_bot=True)
    m.win_rounds = 3
    m.overtime = False
    director = BotDirector(m, seed=3)
    m.start()
    dt = 1 / 32
    for _ in range(int(60 * 60 / dt)):
        m.tick(dt, director.commands(dt))
        if m.phase == "over":
            break
    assert m.phase == "over"
    assert max(m.score) == 3


def test_weapons_come_from_python_config() -> None:
    weapons = load_weapons()
    assert len([w for w in weapons.values() if w.slot != "melee"]) == 20
    assert weapons["heron"].mag == 18 and weapons["heron"].price == 2900
    assert weapons["walze"].rate_ramp is not None


def test_rate_ramp_speeds_up_held_fire() -> None:
    m, a, _ = duel()
    run(m, 31)
    p = m.players[a]
    p.weapons["primary"] = m._new_weapon("walze")
    p.slot = "primary"
    p.equip_until = 0.0
    shots_early = shots_late = 0
    for i in range(int(3.0 * 64)):
        events = m.tick(1 / 64, {a: Command(facing=180.0, fire=True)})
        fired = sum(1 for e in events if e.kind == "shot")
        if i < 32:
            shots_early += fired
        elif i >= 128:
            shots_late += fired
    assert shots_late > shots_early * 1.2


def test_map_materials_set_wall_properties() -> None:
    m = load_map("gasse")
    glass = [w for w in m.walls if w.material == "glass"]
    assert glass and not glass[0].blocks_sight and glass[0].height == 2 and glass[0].penetration == 0
    assert m.floor == "concrete" and any(mat == "tiles" for mat, _ in m.floors)


def test_map_objects_block_and_spawn_barrier_only_in_buy_phase() -> None:
    m = load_map("gasse")
    keys = {o.key for o in m.objects}
    assert {"door", "barrel", "spawn_barrier", "bench"} <= keys and m.decals
    barrier_walls = [w for w in m.walls if w.buy_phase_only]
    assert barrier_walls
    match = Match(m, seed=1)
    a = match.add_player("A", 0, "kestrel").pid
    match.add_player("B", 1, "kestrel")
    match.start()
    p = match.players[a]
    p.pos = Vec(12, 4.0)
    for _ in range(64):
        match.tick(1 / 64, {a: Command(facing=0.0, move_y=1.0)})
    assert p.pos.y < 4.7  # held back by the barrier during the buy phase
    match.phase, match.phase_until = "live", match.time + 90
    for _ in range(64):
        match.tick(1 / 64, {a: Command(facing=0.0, move_y=1.0)})
    assert p.pos.y > 5.5
