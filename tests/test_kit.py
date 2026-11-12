"""Ability kit: composed abilities, chained objects, triggers, passives, data statuses, plugin mechanics."""
from __future__ import annotations

import runpy
from pathlib import Path

from gameplay import abilities
from gameplay.geometry import Vec
from gameplay.kit import EFFECTS, TRIGGERS, check_ability, tick
from gameplay.kit.dsl import ability, agent, damage, heal, on, preset, push, spawn, status, step, thing
from gameplay.match import Command, Match
from gameplay.world import load_map

ROOT = Path(__file__).resolve().parent.parent


def setup(spec: dict) -> tuple[Match, int, int]:
    m = Match(load_map("werkhof"), seed=2)
    m.agents = {**m.agents, "test": spec}
    a = m.add_player("A", 0, "test").pid
    b = m.add_player("B", 1, "kestrel").pid
    m.start()
    m.phase, m.phase_until = "live", m.time + 100
    pa, pb = m.players[a], m.players[b]
    pa.pos, pb.pos, pa.facing, pb.facing = Vec(17, 15), Vec(17, 23), 0.0, 180.0
    return m, a, b


def cast(m: Match, pid: int, key: str, depth: float = 8.0) -> None:
    p = m.players[pid]
    p.charges[key], p.ult_points, p.prev_ability = 5, 20, None
    m.tick(1 / 64, {pid: Command(facing=p.facing, cursor_depth=depth, ability=key)})


def run(m: Match, seconds: float) -> None:
    for _ in range(int(seconds * 64)):
        m.tick(1 / 64, {})


def filler() -> dict:
    return {"Q": preset("hop", "Hop", velocity=5.0), "E": preset("hop", "Hop", velocity=5.0),
            "X": preset("overdrive", "Od", cost=7, duration=5.0)}


def test_template_agent_is_valid_and_its_firebomb_chains_into_a_burning_zone() -> None:
    template = runpy.run_path(str(ROOT / "config" / "content" / "agents" / "_template.py"))["AGENT"]
    assert all(not check_ability(ab) for ab in template["abilities"].values())
    m, a, b = setup(template)
    pb = m.players[b]
    cast(m, a, "C")
    run(m, 1.0)
    assert pb.hp < 100, "the burst hit"
    assert any(e.kind == "zone" for e in m.effects), "the burst left a zone"
    hp = pb.hp
    run(m, 1.0)
    assert pb.hp < hp and abilities.has(m, pb, "burn")


def test_ultimate_reveals_and_hastes_team_and_passive_heals_on_kill() -> None:
    template = runpy.run_path(str(ROOT / "config" / "content" / "agents" / "_template.py"))["AGENT"]
    m, a, b = setup(template)
    pa, pb = m.players[a], m.players[b]
    base = m._max_speed(pa)
    cast(m, a, "X")
    assert pb.revealed_until > m.time and abilities.has(m, pa, "haste") and m._max_speed(pa) > base
    pa.hp = 40
    m._kill(pa, pb, "test", "body")
    tick(m, 1 / 64)  # kills normally happen inside a match tick; the kit reads this tick's events
    run(m, 2.5)
    assert pa.hp >= 60


def test_enter_trigger_fires_once_per_stay_and_push_moves_out() -> None:
    trap = ability("Spring", target="aim", place=thing("zone", lasts=10, radius=2.0, triggers=[
        on("enter", who="enemies", do=[damage(10), push(3.0)])]))
    m, a, b = setup(agent("T", C=trap, **filler()))
    pb = m.players[b]
    cast(m, a, "C", depth=8.0)
    run(m, 0.2)
    assert pb.hp == 90 and (pb.pos - Vec(17, 23)).length() > 1.0


def test_status_from_data_and_plugin_mechanic() -> None:
    assert "swap" in EFFECTS and "low_light" in TRIGGERS
    swap = ability("Switch", target="self", do=[step("swap", who="enemies", first=True), status("fortify", 3, who="self")])
    m, a, b = setup(agent("T", C=swap, **filler()))
    pa, pb = m.players[a], m.players[b]
    cast(m, a, "C")
    assert pa.pos == Vec(17, 23) and pb.pos == Vec(17, 15)
    m._damage(pb, pa, 20, "body", "test")
    assert pa.hp == 100 - 14  # fortify: 0.7 damage taken


def test_check_ability_names_unknown_parts() -> None:
    bad = ability("Bad", do=[step("explode_universe")], place=thing("zone", triggers=[on("sometimes", do=[heal(5)])]))
    problems = " ".join(check_ability(bad))
    assert "explode_universe" in problems and "sometimes" in problems
    assert check_ability(preset("nonsense", "X"))


def test_python_map_template_builds_rooms_ramps_and_spawns() -> None:
    from gameplay.world import parse_map
    raw = runpy.run_path(str(ROOT / "gameplay" / "data" / "maps" / "_template.py"))["MAP"]
    w = parse_map("yard", raw)
    assert len(w.sites) == 2 and len(w.spawns[0]) == 5 and len(w.ramps) == 1
    assert 0.3 < w.ground_height(w.ramps[0].center) < 0.7 and w.ground_height(w.platforms[0].rect.center) == 1.0
    doorway = Vec(4 + 6 + 1, 23.5)  # gap in the south wall of room A
    assert not any(wl.rect.contains(doorway) and wl.height == 2 and not wl.material.startswith("obj:") for wl in w.walls)
