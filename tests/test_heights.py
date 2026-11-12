"""Continuous ground height: ramps rise evenly, ledges are fallen from the current height, platforms block walking."""
from __future__ import annotations

from gameplay.geometry import Rect, Vec
from gameplay.match import Command, Match
from gameplay.world import Platform, WorldMap
from map_fixtures import load_archived_map


def ramp_world() -> WorldMap:
    return WorldMap("t", "t", 20.0, 10.0, platforms=[Platform(Rect(4.0, 0.0, 8.0, 2.0), 1)], ramps=[Rect(0.0, 0.0, 4.0, 2.0)])


def test_ramp_rises_toward_platform() -> None:
    w = ramp_world()
    assert w.ground_height(Vec(0.2, 1.0)) < 0.1      # low end stays low
    assert 0.45 < w.ground_height(Vec(2.0, 1.0)) < 0.55
    assert w.ground_height(Vec(3.9, 1.0)) > 0.95
    assert w.ground_height(Vec(6.0, 1.0)) == 1.0
    assert w.floor_level(Vec(0.2, 1.0)) == 0 and w.floor_level(Vec(6.0, 1.0)) == 1


def walk(m: Match, pid: int, facing: float, seconds: float) -> list[float]:
    heights = []
    for _ in range(int(seconds * 64)):
        m.tick(1 / 64, {pid: Command(move_y=1.0, facing=facing)})
        p = m.players[pid]
        heights.append(p.ground + p.z)
    return heights


def setup() -> tuple[Match, int]:
    m = Match(load_archived_map("workyard"), seed=1)
    pid = m.add_player("A", 0, "omen").pid
    m.start()
    for _ in range(31 * 64):
        m.tick(1 / 64, {})
    return m, pid


def test_walking_up_the_ramp_is_smooth_and_off_the_ledge_never_rises() -> None:
    m, pid = setup()
    p = m.players[pid]
    p.pos, p.z, p.vz, p.ground = Vec(11.5, 35.5), 0.0, 0.0, 0.0  # in front of the low end of the Workyard ramp
    up = walk(m, pid, 270.0, 0.9)  # west; compass angles: 0 is +y, 270 is -x
    assert 3.0 < p.pos.x < 8.0, "reached the platform"
    assert max(b - a for a, b in zip(up, up[1:])) < 0.15, "no jump while walking up"
    assert abs(up[-1] - 1.0) < 1e-6
    off = walk(m, pid, 180.0, 1.0)  # north (-y) over the platform edge
    assert p.pos.y < 33.0 and p.ground == 0.0 and p.z == 0.0, "fell down and landed"
    assert all(b <= a + 1e-9 for a, b in zip(off, off[1:])), "height only goes down when stepping off"


def test_platform_side_blocks_without_ramp() -> None:
    m, pid = setup()
    p = m.players[pid]
    p.pos, p.z, p.vz, p.ground = Vec(5.0, 31.5), 0.0, 0.0, 0.0  # north of the platform, on the ground
    walk(m, pid, 0.0, 1.0)  # south (+y) into the platform side
    assert p.ground == 0.0 and p.pos.y < 33.0
