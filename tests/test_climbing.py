"""No boosting: full walls are never climbed, crates only by a full jump, no popping up onto an edge."""
from __future__ import annotations

from gameplay.geometry import Vec
from gameplay.match import Command, Match
from gameplay.world import parse_map

RAW = {"name": "Test", "width": 20, "height": 10, "walls": [{"rect": [8, 0, 8.5, 10], "mat": "concrete"}],
       "crates": [[6, 4, 8, 6]], "sites": [{"name": "A", "rect": [14, 2, 18, 8]}],
       "spawns": {"0": [[2, 5]], "1": [[16, 5]]}, "spawn_zones": {"0": [0, 0, 3, 10], "1": [15, 0, 20, 10]}}


def setup() -> tuple[Match, int]:
    m = Match(parse_map("test", RAW), seed=1)
    pid = m.add_player("A", 0, "kestrel").pid
    m.add_player("B", 1, "kestrel")
    m.start()
    m.phase, m.phase_until = "live", m.time + 100
    return m, pid


def run(m: Match, pid: int, seconds: float, facing: float, jump_at: float | None = None) -> None:
    for i in range(int(seconds * 64)):
        jump = jump_at is not None and abs(i / 64 - jump_at) < 0.5 / 64
        m.tick(1 / 64, {pid: Command(move_y=1.0, facing=facing, jump=jump)})


def place(m: Match, pid: int, pos: Vec, ground: float) -> None:
    p = m.players[pid]
    p.pos, p.vel, p.z, p.vz, p.ground, p.level = pos, Vec(0, 0), 0.0, 0.0, ground, int(ground + 0.5)


def test_walking_into_a_crate_is_blocked() -> None:
    m, pid = setup()
    place(m, pid, Vec(4.5, 5), 0.0)
    run(m, pid, 1.0, 90.0)
    p = m.players[pid]
    assert p.ground == 0.0 and p.pos.x < 6.0


def test_a_full_jump_lands_on_the_crate() -> None:
    m, pid = setup()
    place(m, pid, Vec(4.6, 5), 0.0)
    run(m, pid, 0.6, 90.0, jump_at=0.0)
    p = m.players[pid]
    assert p.ground == 1.0 and 6.0 < p.pos.x < 8.0


def test_jumping_from_the_crate_never_crosses_a_full_wall() -> None:
    m, pid = setup()
    place(m, pid, Vec(7.0, 5), 1.0)
    for start in (0.0, 0.1, 0.3):
        run(m, pid, 0.8, 90.0, jump_at=start)
        assert m.players[pid].pos.x < 8.0


def test_jumping_late_into_the_crate_side_does_not_pop_up() -> None:
    m, pid = setup()
    place(m, pid, Vec(5.3, 5), 0.0)
    p = m.players[pid]
    heights = []
    for i in range(40):
        m.tick(1 / 64, {pid: Command(move_y=1.0, facing=90.0, jump=i == 0)})
        heights.append(p.ground + p.z)
    rises = [b - a for a, b in zip(heights, heights[1:])]
    assert max(rises) < 0.2, "no sudden jump in height"
