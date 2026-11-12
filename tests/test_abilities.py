"""Tests for the ability presets and statuses (config/content/agents/, config/content/statuses.py)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gameplay import abilities
from gameplay.geometry import Vec
from gameplay.match import Command, Match, load_agents
from map_fixtures import load_archived_map

KINDS = {"smoke", "wall", "flash", "zone", "blast", "wave", "sensor", "alarm", "tripwire", "dash", "hop", "teleport",
         "anchor", "heal", "stim", "shield", "revive", "reveal_all", "overdrive", "immunity", "decoy"}


def setup(agent_a: str = "omen", agent_b: str = "omen") -> tuple[Match, int, int]:
    m = Match(load_archived_map("workyard"), seed=2)
    a = m.add_player("A", 0, agent_a).pid
    b = m.add_player("B", 1, agent_b).pid
    m.start()
    m.phase, m.phase_until = "live", m.time + 100
    pa, pb = m.players[a], m.players[b]
    pa.pos, pb.pos = Vec(17, 15), Vec(17, 23)
    pa.facing, pb.facing = 0.0, 180.0
    return m, a, b


def cast(m: Match, pid: int, agent: str, key: str, depth: float = 8.0) -> None:
    p = m.players[pid]
    p.agent = agent
    p.charges[key] = 5
    p.ult_points = 20
    p.prev_ability = None
    m.tick(1 / 64, {pid: Command(facing=p.facing, cursor_depth=depth, ability=key)})


def run(m: Match, seconds: float) -> None:
    for _ in range(int(seconds * 64)):
        m.tick(1 / 64, {})


def test_all_agents_use_known_blocks() -> None:
    agents = load_agents()
    assert set(agents) == {"brimstone", "omen", "jett", "sova", "sage", "cypher", "phoenix", "killjoy"}
    for key, agent in agents.items():
        for slot, ab in agent["abilities"].items():
            assert ab["kind"] in KINDS or ab["kind"] == "custom", (key, slot, ab["kind"])  # custom: composed with the kit


def test_every_ability_of_every_agent_runs_without_error() -> None:
    for agent, data in load_agents().items():
        for key in ("C", "Q", "E", "X"):
            m, a, _ = setup(agent)
            cast(m, a, agent, key)
            run(m, 3)


def test_blast_applies_status_and_damage(archived_agents) -> None:
    m, a, b = setup()
    cast(m, a, "okoro", "E")  # concussing blast at the cursor (8 m ahead = on B)
    run(m, 1.0)
    assert abilities.has(m, m.players[b], "concuss")
    hp = m.players[b].hp
    cast(m, a, "rook", "X")
    run(m, 1.0)
    assert m.players[b].hp < hp


def test_concuss_and_slow_reduce_speed() -> None:
    m, a, b = setup()
    pb = m.players[b]
    base = m._max_speed(pb)
    abilities.apply_status(m, pb, "slow", 2)
    assert m._max_speed(pb) < base
    abilities.apply_status(m, pb, "detain", 2)
    assert m._max_speed(pb) == 0


def test_suppress_blocks_abilities() -> None:
    m, a, _ = setup()
    abilities.apply_status(m, m.players[a], "suppress", 3)
    before = len(m.effects)
    cast(m, a, "omen", "E")
    assert len(m.effects) == before


def test_vulnerable_increases_damage() -> None:
    m, a, b = setup()
    pb = m.players[b]
    m._damage(m.players[a], pb, 20, "body", "test")
    plain = 100 - pb.hp
    pb.hp = 100
    abilities.apply_status(m, pb, "vulnerable", 3)
    m._damage(m.players[a], pb, 20, "body", "test")
    assert 100 - pb.hp > plain


def test_decay_never_kills_and_regenerates() -> None:
    m, a, b = setup()
    pb = m.players[b]
    abilities.apply_status(m, pb, "decay", 10)
    run(m, 9)
    assert pb.alive and pb.hp >= 1 and pb.hp < 100
    low = pb.hp
    run(m, 4)
    assert pb.hp > low


def test_nearsight_hides_far_enemies() -> None:
    m, a, b = setup()
    assert m.can_see(m.players[a], m.players[b])
    abilities.apply_status(m, m.players[a], "nearsight", 3)
    assert not m.can_see(m.players[a], m.players[b])


def test_tripwire_detains_crossing_enemy(archived_agents) -> None:
    m, a, b = setup()
    cast(m, a, "harrow", "C", depth=3.0)
    wire = next(e for e in m.effects if e.kind == "tripwire")
    pb = m.players[b]
    pb.pos = wire.pos + Vec(0, 0.6)
    pb.last_pos = pb.pos
    m.tick(1 / 64, {})
    pb.pos = wire.pos - Vec(0, 0.6)
    m.tick(1 / 64, {})
    assert abilities.has(m, pb, "detain")


def test_revive_brings_back_fallen_ally(archived_agents) -> None:
    m = Match(load_archived_map("workyard"), seed=1)
    a = m.add_player("A", 0, "harrow").pid
    c = m.add_player("C", 0, "omen").pid
    m.add_player("B", 1, "omen")
    m.start()
    m.phase, m.phase_until = "live", m.time + 100
    pa, pc = m.players[a], m.players[c]
    pa.pos, pc.pos, pa.facing = Vec(17, 15), Vec(17, 19), 0.0
    m._kill(None, pc, "test", "body")
    cast(m, a, "harrow", "X", depth=4.0)
    assert pc.alive and pc.hp == 100


def test_anchor_returns_to_set_point(archived_agents) -> None:
    m, a, _ = setup()
    start = m.players[a].pos
    cast(m, a, "sable", "C")
    m.players[a].pos = Vec(30, 20)
    cast(m, a, "sable", "C")
    assert (m.players[a].pos - start).length() < 0.01


def test_heal_restores_health_over_time(archived_agents) -> None:
    m, a, _ = setup()
    pa = m.players[a]
    pa.hp = 30
    cast(m, a, "sable", "E", depth=0.5)
    run(m, 5)
    assert pa.hp >= 85


def test_bot_uses_offensive_ability_on_close_enemy(archived_agents) -> None:
    from gameplay.bots import BotBrain
    m, a, b = setup("okoro")
    m.players[a].is_bot = True
    m.players[a].charges["E"] = 1
    brain = BotBrain(a, reaction=0.0)
    cmd = brain.think(m, 1 / 64)
    assert cmd.ability == "E"


def test_bot_buys_abilities_with_spare_credits(archived_agents) -> None:
    from gameplay.bots import BotBrain
    m, a, _ = setup("tamsin")
    m.phase = "buy"
    p = m.players[a]
    p.credits, p.charges = 9000, {}
    wants = BotBrain(a).think(m, 1 / 64).buy
    assert "C" in wants and "Q" in wants
