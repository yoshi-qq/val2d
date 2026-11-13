"""Icebox upper plant areas through the regular match and snapshot paths."""

import pytest

from gameplay.geometry import Vec, angle_of
from gameplay.match import Command, Match
from gameplay.nav import NavGrid
from gameplay.net import apply_snapshot
from gameplay.world import load_playable_map


def test_icebox_a_belt_ramp_connects_both_platforms_without_jumping() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    runner = match.add_player("Runner", 0, "omen")
    match.add_player("Defender", 1, "jett")
    match.start()
    match.phase_until = match.time
    match.tick(0.1, {})

    lower, upper = Vec(49, 5), Vec(49, 13)
    assert world.ground_height(Vec(49, 9)) == pytest.approx(0.8)
    nav = NavGrid(world)
    buy, areas = match._buy_areas
    for point in (lower, upper):
        assert buy.cell(point) not in areas[0] | areas[1]
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], upper, start_ground=0, goal_ground=1.4)

    for start, end in ((lower, upper), (upper, lower)):
        start_height, end_height = world.ground_height(start), world.ground_height(end)
        assert nav.line_free(start, end, start_height, end_height)
        runner.pos, runner.ground, runner.level = start, start_height, world.floor_level(start)
        runner.vel = Vec(0, 0)
        command = Command(move_y=1, facing=angle_of(end - start))
        for _ in range(120):
            match.tick(1 / 64, {runner.pid: command})
            assert runner.z == 0
            if (runner.pos - end).length() < 0.25:
                break
        assert (runner.pos - end).length() < 0.25
        assert runner.ground == pytest.approx(end_height)


def test_icebox_a_nest_gate_blocks_ground_movement_but_preserves_sight() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    runner = match.add_player("Runner", 0, "omen")
    match.add_player("Defender", 1, "jett")
    match.start()
    match.phase_until = match.time
    match.tick(0.1, {})

    approach, under_nest = Vec(63.5, 11.5), Vec(66, 11.5)
    nav = NavGrid(world)
    assert match._line_clear(approach, under_nest, 0)
    assert not nav.line_free(approach, under_nest, 0, 0)
    assert nav.path(approach, under_nest, start_ground=0, goal_ground=0)
    assert nav.line_free(Vec(64.7, 11.5), under_nest, 2, 2)

    runner.pos, runner.ground, runner.level = approach, 0, 0
    command = Command(move_y=1, facing=angle_of(under_nest - approach))
    for _ in range(64):
        match.tick(1 / 64, {runner.pid: command})
    assert approach.x < runner.pos.x < 64.5


@pytest.mark.parametrize("reverse", [False, True])
def test_icebox_zipline_rides_in_both_directions(reverse: bool) -> None:
    match = Match(load_playable_map("icebox"))
    rider = match.add_player("Rider", int(reverse), "omen")
    match.add_player("Other", 1 - rider.team, "jett")
    match.start()
    cable = match.world.ziplines[0]
    start, end = (cable.end, cable.start) if reverse else (cable.start, cable.end)
    nav = NavGrid(match.world)
    for spawns in match.world.spawns.values():
        assert nav.path(spawns[2], start, start_ground=0, goal_ground=match.world.ground_height(start))
    rider.pos = start
    rider.ground = match.world.ground_height(start)
    rider.level = int(rider.ground)
    match.tick(1 / 64, {rider.pid: Command(interact=True)})
    assert rider.zipline is None
    match.phase_until = match.time
    match.tick(1 / 64, {})
    rider.pos, rider.ground, rider.level = start, match.world.ground_height(start), match.world.floor_level(start)
    match.tick(1 / 64, {rider.pid: Command(interact=True)})
    assert rider.zipline == 0 and rider.ground == cable.level
    match.tick(1 / 64, {})
    assert rider.pos == start
    command = Command(move_y=1, facing=angle_of(end - start))
    for _ in range(400):
        match.tick(1 / 64, {rider.pid: command})
        if rider.zipline is None:
            break
    assert rider.pos == end
    assert rider.zipline is None and rider.ground == match.world.ground_height(end)


def test_icebox_zipline_height_gate_and_midair_release() -> None:
    match = Match(load_playable_map("icebox"))
    rider = match.add_player("Rider", 1, "omen")
    match.add_player("Other", 0, "jett")
    match.start()
    match.phase_until = match.time
    match.tick(1 / 64, {})
    cable = match.world.ziplines[0]
    rider.pos, rider.ground, rider.level = cable.end, 0, 0
    match.tick(1 / 64, {rider.pid: Command(interact=True)})
    assert rider.zipline is None
    match.tick(1 / 64, {})
    rider.ground, rider.level = cable.level, int(cable.level)
    match.tick(1 / 64, {rider.pid: Command(interact=True)})
    assert rider.zipline == 0
    for _ in range(100):
        match.tick(1 / 64, {rider.pid: Command(move_y=1, facing=270)})
    match.tick(1 / 64, {rider.pid: Command(jump=True)})
    assert rider.zipline is None and rider.z > 0
    for _ in range(75):
        match.tick(1 / 64, {})
    assert rider.ground == rider.z == 0


@pytest.mark.parametrize("index", [1, 2, 3, 4])
def test_icebox_ascenders_climb_descend_and_land(index: int) -> None:
    match = Match(load_playable_map("icebox"))
    rider = match.add_player("Rider", 0, "omen")
    match.add_player("Defender", 1, "jett")
    match.start()
    cable = match.world.ziplines[index]
    nav = NavGrid(match.world)
    for spawns in match.world.spawns.values():
        for point, level in ((cable.start, cable.lower), (cable.end, cable.level)):
            assert match.world.ground_height(point) == level
            assert nav.path(spawns[2], point, start_ground=0, goal_ground=level)
    rider.pos = cable.start
    match.tick(1 / 64, {rider.pid: Command(interact=True, move_y=1)})
    assert rider.zipline is None
    match.phase_until = match.time
    match.tick(1 / 64, {})
    rider.pos = cable.start
    match.tick(1 / 64, {rider.pid: Command(interact=True)})
    assert rider.zipline == index
    for _ in range(96):
        match.tick(1 / 64, {rider.pid: Command(move_y=1, facing=180)})
        if rider.zipline is None:
            break
    assert rider.zipline is None and rider.pos == cable.end and rider.ground == cable.level
    match.tick(1 / 64, {rider.pid: Command(interact=True)})
    assert rider.zipline == index
    for _ in range(96):
        match.tick(1 / 64, {rider.pid: Command(move_y=-1, facing=90)})
        if rider.zipline is None:
            break
    assert rider.zipline is None and rider.pos == cable.start and rider.ground == cable.lower
    match.tick(1 / 64, {rider.pid: Command(interact=True)})
    for _ in range(22):
        match.tick(1 / 64, {rider.pid: Command(move_y=1)})
    match.tick(1 / 64, {rider.pid: Command(jump=True)})
    assert rider.zipline is None and rider.z > 0
    for _ in range(65):
        match.tick(1 / 64, {})
    assert rider.ground == cable.lower and rider.z == 0


@pytest.mark.parametrize(("start", "waypoints", "height"), [
    (Vec(93.5, 36), (Vec(93.5, 15.5),), 3),
    (Vec(78.5, 85), (Vec(78.5, 95), Vec(82.5, 95)), 2),
    (Vec(95.5, 52), (Vec(86, 52),), 1.5),
])
def test_icebox_upper_approaches_are_walkable(start: Vec, waypoints: tuple[Vec, ...], height: float) -> None:
    match = Match(load_playable_map("icebox"))
    runner = match.add_player("Attacker", 0, "omen")
    match.add_player("Defender", 1, "jett")
    match.start()
    match.phase_until = match.time
    match.tick(0.1, {})
    runner.pos = start
    for point in waypoints:
        for _ in range(320):
            if (runner.pos - point).length() < 0.25:
                break
            match.tick(1 / 64, {runner.pid: Command(move_y=1, facing=angle_of(point - runner.pos))})
        assert (runner.pos - point).length() < 0.25
    assert runner.ground == height


def test_icebox_b_green_cubby_door_is_a_separate_live_route() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    nav = NavGrid(world)
    approach, garage = Vec(35.5, 64), Vec(35.5, 72)
    assert nav.line_free(approach, garage)
    assert not nav.line_free(Vec(37, 66), Vec(37, 70))
    buy, areas = match._buy_areas
    assert buy.cell(Vec(35.5, 62)) in areas[0]
    assert buy.cell(approach) not in areas[0]
    assert buy.cell(garage) not in areas[0]
    assert nav.line_free(Vec(50, 65), Vec(50, 75))
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], garage)


def test_icebox_buy_barriers_leave_green_and_orange_neutral() -> None:
    match = Match(load_playable_map("icebox"))
    buy, areas = match._buy_areas
    assert areas[0].isdisjoint(areas[1])
    for point in (Vec(57, 85), Vec(72, 71)):
        assert buy.cell(point) not in areas[0] | areas[1]
    for point in (Vec(57, 89), Vec(72, 75), Vec(72, 100), Vec(76, 105)):
        assert buy.cell(point) in areas[1]
    nav = NavGrid(match.world)
    assert nav.line_free(Vec(57, 85), Vec(57, 89))
    assert nav.line_free(Vec(72, 71), Vec(72, 75))


def test_icebox_defender_buy_line_leaves_the_mid_and_a_approaches_neutral() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    buy, areas = match._buy_areas
    nav = NavGrid(world)
    for neutral, held in (
        (Vec(80, 40), Vec(84, 40)),
        (Vec(80, 52), Vec(86, 52)),
        (Vec(79, 14), Vec(88, 14)),
    ):
        assert buy.cell(neutral) not in areas[0] | areas[1]
        assert buy.cell(held) in areas[1]
        assert not buy.line_free(neutral, held)
        assert nav.path(neutral, held)
    assert buy.cell(Vec(97, 9)) in areas[1]


def test_icebox_attacker_buy_line_closes_a_belt_and_mid_blue() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    buy, areas = match._buy_areas
    nav = NavGrid(world)
    for y in (9, 26, 40):
        held, neutral = Vec(42.5, y), Vec(45, y)
        assert buy.cell(held) in areas[0]
        assert buy.cell(neutral) not in areas[0] | areas[1]
        assert not buy.line_free(held, neutral)
        assert nav.line_free(held, neutral)


def test_icebox_spawn_container_screens_tube_and_leaves_both_passages_open() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    nav = NavGrid(world)
    tube_approach = Vec(73, 63)
    assert all(not match._line_clear(spawn, tube_approach, 0) for spawn in world.spawns[0])
    for x in (32.5, 43):
        assert nav.line_free(Vec(x, 43), Vec(x, 47))
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], tube_approach)


def test_icebox_tube_window_opens_sight_without_opening_a_walkway() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    nav = NavGrid(world)
    tube, boiler, defender_side = Vec(89, 58.5), Vec(89, 52), Vec(101, 48)
    assert match._line_clear(tube, boiler, 0)
    assert match._line_clear(tube, defender_side, 0)
    assert not match._line_clear(tube, Vec(86, 52), 0)
    assert not nav.line_free(tube, boiler)
    assert nav.path(tube, boiler)
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], tube)


def test_icebox_tube_crates_leave_a_clear_passage_to_the_window() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    nav = NavGrid(world)
    before, after = Vec(87.3, 57.5), Vec(87.3, 60.5)
    assert not match._line_clear(before, after, 0)
    assert not nav.line_free(before, after)
    before, after = Vec(89.1, 57.5), Vec(89.1, 60.5)
    assert nav.line_free(before, after)
    assert match._line_clear(before, after, 0)
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], before)


@pytest.mark.parametrize("walk", [True, False])
def test_icebox_snow_pile_drop_and_orange_route(walk: bool) -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    player = match.add_player("Runner", 0, "omen")
    match.add_player("Defender", 1, "jett")
    match.start()
    match.phase_until = match.time
    match.tick(1 / 64, {})
    nav = NavGrid(world)
    assert not nav.line_free(Vec(86.5, 72), Vec(86.5, 76))
    assert nav.line_free(Vec(75.25, 82), Vec(75.25, 87))
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], Vec(84, 66.5), start_ground=0, goal_ground=0.8)

    player.pos, player.ground, player.level = Vec(83.2, 66.5), 0.8, 1
    for _ in range(70):
        match.tick(1 / 64, {player.pid: Command(move_y=1, facing=270, walk=walk)})
        if player.ground == player.z == 0:
            break
    assert player.ground == player.z == 0
    assert (player.quiet_landing_at == match.time) == walk
    guest = Match(world)
    apply_snapshot(guest, match.snapshot(player.pid), player.pid)
    assert guest.players[player.pid].quiet_landing_at == player.quiet_landing_at


def test_icebox_kitchen_back_wall_opens_the_corner_without_opening_the_room() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    nav = NavGrid(world)
    inside, outside = Vec(92, 56.5), Vec(97, 56.5)
    assert match._line_clear(inside, outside, 0)
    assert nav.line_free(inside, outside)
    assert not match._line_clear(Vec(92, 58), Vec(97, 58), 0)
    assert not nav.line_free(Vec(92, 58), Vec(97, 58))
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], inside)


def test_icebox_screens_lintel_preserves_the_doorway_and_blocks_the_high_angle() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    shooter = match.add_player("Shooter", 0, "omen")
    target = match.add_player("Target", 1, "jett")
    match.start()
    match.phase_until = match.time
    match.tick(0.1, {})
    outside, inside = Vec(87.5, 40), Vec(87.5, 34)
    shooter.pos, target.pos = outside, inside
    assert NavGrid(world).line_free(outside, inside)
    assert match.line_of_fire(shooter, target)
    target.ground, target.level = 2, 2
    assert not match.line_of_fire(shooter, target)
    assert not match.line_of_fire(target, shooter)
    assert not world.deck_blocks(outside, 1.6, inside, 1.6)
    assert world.deck_blocks(outside, 2.5, inside, 2.5)


def test_icebox_pipes_blocks_the_corner_angle_and_leaves_the_aisle_open() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    nav = NavGrid(world)
    pipes, aisle = Vec(70, 21), Vec(76, 21)
    assert not match._line_clear(Vec(71, 22.5), Vec(75, 22.5), 2)
    assert match._line_clear(pipes, aisle, 0)
    assert nav.line_free(pipes, aisle)
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], pipes)


def test_icebox_boiler_cannot_shoot_through_the_a_pipes_frame() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    shooter = match.add_player("Boiler", 0, "omen")
    target = match.add_player("Pipes", 1, "jett")
    match.start()
    match.phase_until = match.time
    match.tick(0.1, {})
    for x in (85.5, 86, 88.5, 89):
        shooter.pos = Vec(x, 51)
        shooter.ground = world.ground_height(shooter.pos)
        shooter.level = world.floor_level(shooter.pos)
        for point in (Vec(71, 19), Vec(73, 19), Vec(75, 20), Vec(76.5, 21)):
            target.pos = point
            target.ground = world.ground_height(point)
            target.level = world.floor_level(point)
            assert not match.line_of_fire(shooter, target), (shooter.pos, point)


def test_icebox_boiler_ramp_reaches_the_mid_peek() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    nav = NavGrid(world)
    foot, landing = Vec(95.5, 52), Vec(86, 52)
    assert nav.line_free(foot, landing, start_ground=0, goal_ground=1.5)
    assert world.ground_height(Vec(92, 52)) == pytest.approx(0.75)
    assert world.ground_height(Vec(92, 49.5)) == 0
    assert match._line_clear(landing, Vec(52, 55), 2)
    assert not match._line_clear(landing, Vec(52, 54), 2)
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], landing, start_ground=0, goal_ground=1.5)


@pytest.mark.parametrize("attacking_team", [0, 1])
@pytest.mark.parametrize(("site_name", "point"), [
    ("A", Vec(93.5, 15.5)),
    ("B", Vec(77.5, 92.0)),
    ("B", Vec(82.5, 95.0)),
])
def test_icebox_upper_plant_and_defuse(attacking_team: int, site_name: str, point: Vec) -> None:
    world = load_playable_map("icebox")
    deck = world.deck_at(point)
    assert deck is not None
    assert world.site_at(point, deck.level).name == site_name
    nav = NavGrid(world)
    assert nav.free(nav.cell(point, deck.level))
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], point, start_ground=0, goal_ground=deck.level)

    match = Match(world)
    players = [match.add_player("Alpha", 0, "omen"), match.add_player("Bravo", 1, "jett")]
    match.start()
    if attacking_team:
        match.round_no = int(match._r["half_after"])
        match._start_round()
    attacker, defender = players[attacking_team], players[1 - attacking_team]
    assert match.spike_pos is not None
    attacker.pos = match.spike_pos
    match.tick(0, {})
    assert match.spike_carrier == attacker.pid
    assert not match.buy_phase_allows_landing(attacker, point)
    match.phase_until = match.time
    match.tick(0.1, {})

    attacker.pos, attacker.ground, attacker.level = point, deck.level, int(deck.level)
    for _ in range(45):
        match.tick(0.1, {attacker.pid: Command(use_spike=True)})
    assert match.phase == "planted" and match.spike_site == site_name
    assert match.spike_ground == deck.level

    guest = Match(load_playable_map("icebox"))
    apply_snapshot(guest, match.snapshot(defender.pid), defender.pid)
    assert guest.spike_pos == point and guest.spike_ground == deck.level

    attacker.pos = world.spawns[0][0]
    lower_point = Vec(80.1, point.y) if deck.closed_below else point
    defender.pos, defender.ground, defender.level = lower_point, deck.lower, int(deck.lower)
    for _ in range(10):
        match.tick(0.1, {defender.pid: Command(interact=True)})
    assert defender.defuse_progress == 0

    defender.pos, defender.ground, defender.level = point, deck.level, int(deck.level)
    for _ in range(75):
        match.tick(0.1, {defender.pid: Command(interact=True)})
    assert match.round_winner == defender.team


@pytest.mark.parametrize(("point", "level", "plantable"), [
    (Vec(79.45, 95), 2, True),
    (Vec(79.55, 95), 2, True),
    (Vec(81, 93.8), 2, True),
    (Vec(81, 93.7), 2, False),
    (Vec(81, 96.45), 2, True),
    (Vec(81, 96.55), 2, False),
    (Vec(84.95, 95), 2, True),
    (Vec(85.05, 95), 2, False),
    (Vec(77.5, 95), 0, False),
    (Vec(82.5, 95), 0, True),
])
def test_icebox_b_plant_outline(point: Vec, level: int, plantable: bool) -> None:
    world = load_playable_map("icebox")
    site = world.site_at(point, level)
    assert (site is not None and site.name == "B") == plantable


def test_icebox_a_ground_plant_outline_and_approaches() -> None:
    world = load_playable_map("icebox")
    nav = NavGrid(world)
    buy, areas = Match(world)._buy_areas
    for point in (Vec(87.5, 4.5), Vec(88.5, 25.5), Vec(98.5, 26.5)):
        site = world.site_at(point, 0)
        assert site is not None and site.name == "A"
        cell = buy.cell(point)
        assert cell in areas[1] and cell not in areas[0]
        for spawns in world.spawns.values():
            assert nav.path(spawns[2], point, start_ground=0, goal_ground=0)
    for point in (Vec(85.5, 15.5), Vec(88.5, 28.5), Vec(100.5, 24.5)):
        assert world.site_at(point, 0) is None


def test_icebox_a_site_wall_bevel_preserves_the_passage_along_its_edge() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    nav = NavGrid(world)
    corner, opening = Vec(79.5, 2.5), Vec(77, 9.5)
    assert match._line_clear(corner, opening, 0)
    assert nav.line_free(corner, opening, 0, 0)
    assert not match._line_clear(Vec(76.75, 8), Vec(76.75, 7), 0)


def test_icebox_back_a_low_crate_preserves_sight_and_the_plant_approach() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    nav = NavGrid(world)
    assert world.ground_height(Vec(92, 6.5)) == 1
    assert match._line_clear(Vec(92, 4), Vec(92, 9), 0)
    assert not nav.line_free(Vec(92, 4), Vec(92, 9), 0, 0)
    approach, plant = Vec(94.5, 4), Vec(94.5, 9)
    assert match._line_clear(approach, plant, 0)
    assert nav.line_free(approach, plant)
    site = world.site_at(plant, 0)
    assert site is not None and site.name == "A"
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], plant, start_ground=0, goal_ground=0)


def test_icebox_lower_b_container_blocks_movement_and_sight() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    rider = match.add_player("Attacker", 0, "omen")
    match.add_player("Defender", 1, "jett")
    match.start()
    match.phase_until = match.time
    match.tick(0.1, {})
    near, far = Vec(77.5, 90), Vec(77.5, 104)
    middle = Vec(77.5, 95)
    nav = NavGrid(world)
    assert not nav.free(nav.cell(middle, 0))
    assert nav.free(nav.cell(middle, 2))
    assert not match._line_clear(near, far, 0)
    assert match._line_clear(Vec(77.5, 95), Vec(82.5, 95), 2)

    rider.pos = far
    for _ in range(64):
        match.tick(1 / 64, {rider.pid: Command(move_y=1, facing=180)})
    assert rider.pos.y > 103 and rider.ground == 0

    under_bridge = Vec(82.5, 95)
    assert nav.free(nav.cell(under_bridge, 0))
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], under_bridge, start_ground=0, goal_ground=0)


def test_icebox_upper_b_container_opens_toward_green_and_the_bridge() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    inside = Vec(77.5, 94)
    assert match._line_clear(inside, Vec(74, 83), 2)
    assert not match._line_clear(inside, Vec(74, 97.5), 2)
    assert match._line_clear(inside, Vec(82.5, 95), 2)
    assert not match._line_clear(inside, Vec(82.5, 89), 2)
    nav = NavGrid(world)
    assert nav.line_free(inside, Vec(82.5, 95), start_ground=2, goal_ground=2)


def test_icebox_b_green_cubby_is_a_ground_level_dead_end() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    runner = match.add_player("Attacker", 0, "omen")
    match.add_player("Defender", 1, "jett")
    match.start()
    match.phase_until = match.time
    match.tick(0.1, {})
    entrance, inside = Vec(76.5, 90), Vec(76.5, 92)
    nav = NavGrid(world)
    assert nav.line_free(entrance, inside, start_ground=0, goal_ground=0)
    assert match._line_clear(entrance, inside, 0)
    assert not match._line_clear(inside, Vec(76.5, 95), 0)
    assert world.site_at(inside, 0) is None
    assert world.site_at(inside, 2).name == "B"
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], inside, start_ground=0, goal_ground=0)
    runner.pos = entrance
    for _ in range(64):
        match.tick(1 / 64, {runner.pid: Command(move_y=1, facing=0)})
    assert 92 < runner.pos.y < 93.2 and runner.ground == 0


def test_icebox_yellow_pocket_opens_the_site_angle_and_stays_enclosed() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    nav = NavGrid(world)
    mouth, pocket = Vec(46, 99), Vec(44.25, 99)
    assert nav.line_free(mouth, pocket)
    assert match._line_clear(pocket, Vec(82, 104), 0)
    assert not nav.free(nav.cell(Vec(42.8, 99)))
    assert not match._line_clear(pocket, Vec(42.8, 99), 0)
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], pocket)
    buy, areas = match._buy_areas
    assert buy.cell(pocket) not in areas[0]


def test_icebox_back_b_building_is_closed_and_fence_remains_open() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    nav = NavGrid(world)
    assert not nav.free(nav.cell(Vec(104, 93)))
    assert not match._line_clear(Vec(104, 89), Vec(104, 97), 0)
    fence, back = Vec(100, 88), Vec(100, 93)
    assert world.callout_at(fence) == "B Fence"
    assert world.callout_at(back) == "B Back"
    assert nav.line_free(fence, Vec(100, 98))
    assert match._line_clear(fence, Vec(100, 98), 0)
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], back)


def test_icebox_snowman_choke_preserves_the_site_rotation() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    nav = NavGrid(world)
    site, snowman = Vec(82, 104), Vec(100, 104)
    assert nav.line_free(site, snowman)
    assert match._line_clear(site, snowman, 0)
    for y in (101, 106.5):
        assert not nav.line_free(Vec(82, y), Vec(100, y))
        assert not match._line_clear(Vec(82, y), Vec(100, y), 0)
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], snowman)


def test_icebox_yellow_roof_can_be_checked_from_two_angles() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    nav = NavGrid(world)
    assert world.ground_height(Vec(58, 107)) == 2
    for before, after in (
        (Vec(53, 107), Vec(66, 107)),
        (Vec(58, 104), Vec(58, 111)),
    ):
        assert not match._line_clear(before, after, 0)
        assert not match._line_clear(before, after, 1)
        assert match._line_clear(before, after, 2)
        assert not nav.line_free(before, after, 0, 0)


def test_icebox_yellow_stack_blocks_sight_and_leaves_the_passage_open() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    nav = NavGrid(world)
    before, after = Vec(60, 104.8), Vec(66, 104.8)
    assert not match._line_clear(before, after, 0)
    assert not nav.line_free(before, after)
    before, after = Vec(60, 103), Vec(66, 103)
    assert match._line_clear(before, after, 0)
    assert nav.line_free(before, after)
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], after)


def test_icebox_green_container_leaves_the_floor_beneath_it_open() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    nav = NavGrid(world)
    entrance, exit_point = Vec(54.5, 78), Vec(54.5, 86.5)
    below = Vec(54.5, 83)
    assert world.ground_height(below, 0) == 0
    assert world.ground_height(below) == 0
    deck = world.deck_at(below)
    assert deck is not None and not deck.walkable
    assert world.deck_blocks(below, 1.6, below, 5.5)
    assert nav.line_free(entrance, exit_point, start_ground=0, goal_ground=0)
    assert match._line_clear(entrance, exit_point, 0)
    assert not match._line_clear(exit_point, Vec(54.5, 92), 0)
    assert nav.line_free(Vec(57, 86), Vec(57, 92))
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], below, start_ground=0, goal_ground=0)


def test_icebox_orange_crates_break_the_tube_to_danger_sightline() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    nav = NavGrid(world)
    tube, danger = Vec(72, 65), Vec(72, 86)
    assert not match._line_clear(tube, danger, 0)
    assert not nav.line_free(tube, danger)
    assert nav.line_free(Vec(74.5, 76), Vec(74.5, 84))
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], danger)


@pytest.mark.parametrize(("point", "upper_floor"), [
    (Vec(82.5, 95), True),
    (Vec(72, 100), False),
    (Vec(76, 105), False),
])
def test_icebox_b_ground_plant_and_defuse(point: Vec, upper_floor: bool) -> None:
    match = Match(load_playable_map("icebox"))
    attacker = match.add_player("Attacker", 0, "omen")
    defender = match.add_player("Defender", 1, "jett")
    match.start()
    assert match.spike_pos is not None
    attacker.pos = match.spike_pos
    match.tick(0, {})
    match.phase_until = match.time
    match.tick(0.1, {})

    attacker.pos, attacker.ground, attacker.level = Vec(85.5, 95), 2, 2
    for _ in range(45):
        match.tick(0.1, {attacker.pid: Command(use_spike=True)})
    assert match.phase == "live" and attacker.plant_progress == 0

    for spawns in match.world.spawns.values():
        assert NavGrid(match.world).path(spawns[2], point, start_ground=0, goal_ground=0)
    attacker.pos, attacker.ground, attacker.level = point, 0, 0
    for _ in range(45):
        match.tick(0.1, {attacker.pid: Command(use_spike=True)})
    assert match.phase == "planted" and match.spike_site == "B" and match.spike_ground == 0

    attacker.pos = match.world.spawns[0][0]
    if upper_floor:
        defender.pos, defender.ground, defender.level = point, 2, 2
        for _ in range(10):
            match.tick(0.1, {defender.pid: Command(interact=True)})
        assert defender.defuse_progress == 0

    defender.pos, defender.ground, defender.level = point, 0, 0
    for _ in range(75):
        match.tick(0.1, {defender.pid: Command(interact=True)})
    assert match.round_winner == defender.team


def test_icebox_shifted_default_cover_blocks_the_danger_to_tube_angle() -> None:
    world = load_playable_map("icebox")
    match = Match(world)
    cover = next(wall for wall in world.walls if wall.rect.contains(Vec(73, 88)) and wall.full)
    danger, tube = Vec(74, 104), Vec(73, 64)
    assert not match._line_clear(danger, tube, 0)
    assert match._line_clear(danger, tube, 0, ignore_wall=cover)
    assert world.site_at(Vec(72, 97.9), 0) is None
    assert world.site_at(Vec(76, 106.1), 0) is None
