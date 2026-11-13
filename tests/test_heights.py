"""Continuous ground height: ramps rise evenly, ledges are fallen from the current height, platforms block walking."""
from __future__ import annotations

from gameplay.geometry import Rect, Vec
from gameplay.match import Command, Match
from gameplay.world import Deck, Platform, WorldMap
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


def test_weapon_pickup_uses_drop_floor_at_shared_coordinates_and_edges() -> None:
    world = ramp_world()
    world.decks = [Deck(Rect(10, 2, 16, 8), 2, 0)]
    match = Match(world)
    p = match.add_player("A", 0, "omen")
    match.start()
    for origin, floor, facing, receiver, receiver_floor, allowed in (
        (Vec(12, 4), 2, 0, Vec(12, 5), 0, False),
        (Vec(12, 4), 0, 0, Vec(12, 5), 2, False),
        (Vec(12, 4), 0, 0, Vec(12, 5), 0, True),
        (Vec(15.5, 5), 2, 90, Vec(16.6, 5), 0, True),
        (Vec(3.5, 1), 0.875, 90, Vec(3.7, 1), 0.925, True),
    ):
        match.drops.clear()
        p.pos, p.ground, p.level, p.facing = origin, floor, int(floor + 0.5), facing
        p.slot = "primary"
        p.weapons["primary"] = match._new_weapon("vandal")
        match.tick(0, {p.pid: Command(drop=True)})
        assert len(match.drops) == 1
        p.pos, p.ground, p.level = receiver, receiver_floor, int(receiver_floor + 0.5)
        match.tick(0, {p.pid: Command(interact=True)})
        assert ("primary" in p.weapons) == allowed


def test_spike_dropped_over_deck_edge_must_be_collected_below() -> None:
    world = ramp_world()
    world.decks = [Deck(Rect(10, 2, 16, 8), 2, 0)]
    match = Match(world)
    carrier = match.add_player("Carrier", 0, "omen")
    receiver = match.add_player("Receiver", 0, "omen")
    match.start()
    carrier.pos, carrier.ground, carrier.level = Vec(15.5, 5), 2, 2
    receiver.pos, receiver.ground, receiver.level = Vec(15.5, 5.5), 2, 2
    match.spike_carrier, match.spike_pos = carrier.pid, None
    match.tick(1 / 64, {carrier.pid: Command(slot="spike", drop=True, facing=90),
                        receiver.pid: Command(interact=True)})
    assert match.spike_carrier is None and match.spike_pos == Vec(16.5, 5)
    assert match.spike_ground == 0
    receiver.pos, receiver.ground, receiver.level = Vec(16.6, 5.5), 0, 0
    match.tick(1 / 64, {receiver.pid: Command(interact=True)})
    assert match.spike_carrier == receiver.pid


def test_defuse_reaches_platform_from_ramp_but_not_from_below_ledge() -> None:
    match = Match(ramp_world())
    attacker = match.add_player("Attacker", 0, "omen")
    defender = match.add_player("Defender", 1, "omen")
    match.start()
    attacker.pos, attacker.ground, attacker.level = Vec(4.2, 1), 1, 1
    match._plant(attacker, "A")
    defender.pos, defender.ground, defender.level = Vec(4.2, 2.5), 0, 0
    match.tick(1 / 64, {defender.pid: Command(use_spike=True)})
    assert not defender.defusing
    defender.pos = Vec(3.5, 1)
    defender.ground = match.world.ground_height(defender.pos)
    defender.level = match.world.floor_level(defender.pos)
    match.tick(1 / 64, {defender.pid: Command(use_spike=True)})
    assert defender.defusing and defender.defuse_progress == 1 / 64


def test_spike_and_weapon_drops_stay_inside_outer_map_edge() -> None:
    match = Match(ramp_world())
    player = match.add_player("Attacker", 0, "omen")
    match.start()
    player.pos = Vec(match.world.width - 0.5, 5)
    match.spike_carrier, match.spike_pos = player.pid, None
    match.tick(1 / 64, {player.pid: Command(equipment_actions=["spike", "drop", "drop"], facing=90)})
    assert match.spike_pos == player.pos
    assert match.drops[0].pos == player.pos and match.drops[0].key == "classic"


def test_platform_side_blocks_without_ramp() -> None:
    m, pid = setup()
    p = m.players[pid]
    p.pos, p.z, p.vz, p.ground = Vec(5.0, 31.5), 0.0, 0.0, 0.0  # north of the platform, on the ground
    walk(m, pid, 0.0, 1.0)  # south (+y) into the platform side
    assert p.ground == 0.0 and p.pos.y < 33.0
