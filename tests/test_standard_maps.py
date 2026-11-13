"""Spike routes, buy barriers and objective interactions on the selectable maps."""

import pytest

from gameplay.geometry import Vec, angle_of
from gameplay.match import Command, Match
from gameplay.nav import NavGrid
from gameplay.world import PLAYABLE_MAP_KEYS, load_playable_map


@pytest.mark.parametrize("key", PLAYABLE_MAP_KEYS)
def test_standard_map_routes_and_spike_on_both_sides(key: str) -> None:
    world = load_playable_map(key)
    open_doors = frozenset(w.rect for w in world.walls if w.door and w.switch is not None)
    open_doors |= frozenset(world.drop_wall_links.values())
    navigation = NavGrid(world, open_doors)
    buy = NavGrid(world, frozenset(w.rect for w in world.walls if w.door), buy_phase=True)
    attackers, defenders = world.spawns[0], world.spawns[1]
    attack_area = buy.connected_cells(attackers[2])
    defense_area = buy.connected_cells(defenders[2])
    assert attack_area.isdisjoint(defense_area)
    assert len(attackers) == len(defenders) == 5
    assert all(buy.free(buy.cell(point)) for point in attackers + defenders)
    assert {site.name for site in world.sites} == set("ABC" if key in ("haven", "lotus") else "AB")
    assert len(world.orbs) == (4 if key == "fracture" else 2)
    assert all(navigation.free(navigation.cell(point)) for point in world.orbs)

    for site in world.sites:
        plant_cell = navigation.nearest_free(navigation.cell(site.rect.center))
        plant = navigation.center(plant_cell)
        assert site.rect.contains(plant)
        assert buy.cell(plant) in defense_area
        assert buy.cell(plant) not in attack_area
        assert navigation.path(attackers[2], plant)
        assert navigation.path(defenders[2], plant)

        for attacking_team in (0, 1):
            match = Match(world)
            players = [match.add_player("Alpha", 0, "omen"), match.add_player("Bravo", 1, "jett")]
            match.start()
            if attacking_team:
                match.round_no = int(match._r["half_after"])
                match._start_round()
            attacker, defender = players[attacking_team], players[1 - attacking_team]
            assert match.spike_carrier is None and match.spike_pos is not None
            assert attacker.pos in attackers and defender.pos in defenders
            assert buy.cell(match.spike_pos) in attack_area
            attacker.pos = match.spike_pos
            match.tick(0, {})
            assert match.spike_carrier == attacker.pid

            match.phase_until = match.time
            match.tick(0.1, {})
            assert match.phase == "live"
            attacker.pos = plant
            attacker.ground = navigation.height_at(plant_cell)
            attacker.level = world.floor_level(plant, attacker.ground)
            for _ in range(50):
                match.tick(0.1, {attacker.pid: Command(use_spike=True)})
            assert match.phase == "planted" and match.spike_site == site.name

            attacker.pos = attackers[2]
            defender.pos = plant
            defender.ground = navigation.height_at(plant_cell)
            defender.level = world.floor_level(plant, defender.ground)
            for _ in range(75):
                match.tick(0.1, {defender.pid: Command(interact=True)})
            assert match.round_winner == defender.team


def test_corrode_attacker_buy_line_closes_the_lobby_and_mid_passages() -> None:
    world = load_playable_map("corrode")
    buy, areas = Match(world)._buy_areas
    nav = NavGrid(world)
    for attacker_side, neutral in (
        (Vec(108, 78), Vec(100, 78)),
        (Vec(102, 48), Vec(102, 53)),
        (Vec(108, 44), Vec(99, 44)),
    ):
        assert buy.cell(attacker_side) in areas[0]
        assert buy.cell(neutral) not in areas[0] | areas[1]
        assert not buy.line_free(attacker_side, neutral)
        assert nav.line_free(attacker_side, neutral, 0, 0)


def test_corrode_mid_window_ramp_joins_the_platform() -> None:
    world = load_playable_map("corrode")
    buy, areas = Match(world)._buy_areas
    foot, platform = Vec(42, 60), Vec(42, 68)
    assert world.ground_height(platform) == 1.5
    assert buy.line_free(foot, platform, start_ground=0, goal_ground=1.5)
    assert buy.line_free(platform, foot, start_ground=1.5, goal_ground=0)
    assert all(buy.cell(point) in areas[1] for point in (foot, platform))
    assert buy.path(world.spawns[1][2], platform, start_ground=0, goal_ground=1.5)


def test_corrode_defender_buy_line_keeps_mid_top_neutral() -> None:
    world = load_playable_map("corrode")
    match = Match(world)
    buy, areas = match._buy_areas
    nav = NavGrid(world)
    window, mid = Vec(43, 60), Vec(50, 60)
    assert buy.cell(window) in areas[1]
    assert buy.cell(mid) not in areas[0] | areas[1]
    assert not buy.line_free(window, mid)
    assert not nav.line_free(window, mid, 0, 0)
    assert nav.path(window, mid, start_ground=0, goal_ground=0)
    assert not match._line_clear(window, mid, 0)
    assert match._line_clear(window, mid, 2)
    for held, neutral in (
        (Vec(54, 46), Vec(54, 51)),  # B Link
        (Vec(65, 76), Vec(70, 76)),  # A Link
    ):
        assert buy.cell(held) in areas[1]
        assert buy.cell(neutral) not in areas[0] | areas[1]
        assert not buy.line_free(held, neutral)
        assert nav.line_free(held, neutral, 0, 0)


def test_corrode_b_buy_line_leaves_the_site_and_approach_separate() -> None:
    world = load_playable_map("corrode")
    buy, areas = Match(world)._buy_areas
    held, neutral = Vec(62, 19), Vec(68, 19)
    assert buy.cell(held) in areas[1]
    assert buy.cell(neutral) not in areas[0] | areas[1]
    assert not buy.line_free(held, neutral)
    assert NavGrid(world).line_free(held, neutral, 0, 0)


def test_corrode_a_crane_callout_is_on_the_defender_rotation() -> None:
    world = load_playable_map("corrode")
    buy, areas = Match(world)._buy_areas
    crane = next(rect.center for name, rect in world.callouts if name == "A Crane")
    plant = Vec(54, 107)
    assert world.callout_at(crane) == "A Crane"
    assert buy.cell(crane) in areas[1] and buy.cell(crane) not in areas[0]
    assert buy.path(world.spawns[1][2], crane)
    assert buy.path(crane, plant)


def test_corrode_b_arch_rotation_reaches_the_tower_landing() -> None:
    world = load_playable_map("corrode")
    buy, areas = Match(world)._buy_areas
    nav = NavGrid(world)
    foot, tower = Vec(38, 15.5), Vec(38, 28)
    assert buy.line_free(foot, tower, start_ground=0, goal_ground=2.5)
    assert buy.line_free(tower, foot, start_ground=2.5, goal_ground=0)
    assert all(buy.cell(point) in areas[1] for point in (foot, tower))
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], tower, start_ground=0, goal_ground=2.5)
    arch = next(rect.center for name, rect in world.callouts if name == "B Arch")
    assert world.callout_at(arch) == "B Arch"
    assert buy.cell(arch) in areas[1] and buy.cell(arch) not in areas[0]
    assert buy.path(world.spawns[1][2], arch, start_ground=0, goal_ground=0)
    assert buy.path(arch, tower, start_ground=0, goal_ground=2.5)


@pytest.mark.parametrize(("key", "site", "team", "plant"), [
    ("breeze", "A", 0, Vec(116.5, 70.5)), ("breeze", "A", 1, Vec(128.5, 68.5)),
    ("breeze", "B", 0, Vec(12.5, 94.5)), ("breeze", "B", 1, Vec(21.5, 91.5)),
    ("corrode", "A", 0, Vec(48.5, 109.5)), ("corrode", "A", 1, Vec(55.5, 98.5)),
    ("corrode", "B", 0, Vec(49, 19)), ("corrode", "B", 1, Vec(49, 29)),
    ("corrode", "B", 0, Vec(57.5, 19)), ("corrode", "B", 1, Vec(59.25, 29)),
])
def test_extended_ground_plant_and_defuse(key: str, site: str, team: int, plant: Vec) -> None:
    world = load_playable_map(key)
    match = Match(world)
    players = [match.add_player("Alpha", 0, "omen"), match.add_player("Bravo", 1, "jett")]
    match.start()
    if team:
        match.round_no = int(match._r["half_after"])
        match._start_round()
    attacker, defender = players[team], players[1 - team]
    buy, areas = match._buy_areas
    assert buy.cell(plant) in areas[1] and buy.cell(plant) not in areas[0]
    nav = NavGrid(world)
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], plant, start_ground=0, goal_ground=0)
    outside_points = ((Vec(116.5, 66.5), Vec(115.5, 77.5), Vec(21.5, 89.5), Vec(23.5, 94.5))
                      if key == "breeze" else (Vec(55.5, 97.5), Vec(55.5, 112.5), Vec(54, 29), Vec(57.5, 17.5)))
    for outside in outside_points:
        assert world.site_at(outside, 0) is None

    assert match.spike_pos is not None
    attacker.pos = match.spike_pos
    match.tick(0, {})
    match.phase_until = match.time
    match.tick(0.1, {})
    attacker.pos = plant
    for _ in range(50):
        match.tick(0.1, {attacker.pid: Command(use_spike=True)})
    assert match.phase == "planted" and match.spike_site == site and match.spike_ground == 0
    attacker.pos = world.spawns[0][2]
    defender.pos = plant
    for _ in range(75):
        match.tick(0.1, {defender.pid: Command(interact=True)})
    assert match.round_winner == defender.team


def test_breeze_a_bridge_ascender_connects_site_and_bridge_after_buy() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    rider = match.add_player("Rider", 1, "omen")
    match.add_player("Attacker", 0, "jett")
    match.start()
    [rope] = world.ziplines
    nav = NavGrid(world)
    buy, areas = match._buy_areas
    for point, level in ((rope.start, 0), (rope.end, 2)):
        assert world.ground_height(point) == level
        assert buy.cell(point) in areas[1] and buy.cell(point) not in areas[0]
        for spawns in world.spawns.values():
            assert nav.path(spawns[2], point, start_ground=0, goal_ground=level)

    offset = Vec(-0.6, 0)
    rider.pos = rope.start + offset
    match.tick(1 / 64, {rider.pid: Command(interact=True)})
    assert rider.zipline is None
    match.phase_until = match.time
    match.tick(1 / 64, {})

    for start, end, direction in ((rope.start, rope.end, 1), (rope.end, rope.start, -1)):
        rider.pos = start + offset
        match.tick(1 / 64, {rider.pid: Command(interact=True)})
        assert rider.zipline == 0 and rider.pos == start
        for _ in range(96):
            match.tick(1 / 64, {rider.pid: Command(move_y=direction)})
            if rider.zipline is None:
                break
        assert rider.zipline is None and rider.pos == end
        assert rider.ground == world.ground_height(end)


def test_breeze_a_bridge_cover_leaves_the_defender_passage_open() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    buy, areas = match._buy_areas
    nav = NavGrid(world)
    assert world.ground_height(Vec(73, 108)) == 1
    assert not nav.line_free(Vec(70.5, 108), Vec(76, 108), 0, 0)
    assert match._line_clear(Vec(70.5, 108), Vec(76, 108), 0)
    passage = Vec(70.5, 105.5), Vec(76, 105.5)
    assert buy.line_free(*passage)
    assert all(buy.cell(point) in areas[1] for point in passage)
    rope = world.ziplines[0]
    assert nav.path(passage[1], rope.end, start_ground=0, goal_ground=rope.level)


def test_breeze_mid_nest_cover_preserves_the_buy_threshold() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    buy, areas = match._buy_areas
    nav = NavGrid(world)
    assert world.ground_height(Vec(60, 98.5)) == 1
    assert match._line_clear(Vec(57.5, 98.5), Vec(62.5, 98.5), 0)
    assert not nav.line_free(Vec(57.5, 98.5), Vec(62.5, 98.5), 0, 0)
    held, nest = Vec(66, 106), Vec(59, 106)
    assert buy.cell(held) in areas[1]
    assert buy.cell(nest) not in areas[0] | areas[1]
    assert not buy.line_free(held, nest)
    assert nav.line_free(held, nest, start_ground=0.2, goal_ground=0.8)
    landing, mid = Vec(57, 105), Vec(57, 98.5)
    assert world.ground_height(landing) == pytest.approx(0.8)
    assert nav.line_free(landing, mid, start_ground=0.8, goal_ground=0)
    assert nav.line_free(mid, landing, start_ground=0, goal_ground=0.8)


def test_breeze_mid_top_east_cover_leaves_the_west_passage_open() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    buy, areas = match._buy_areas
    nav = NavGrid(world)
    assert world.ground_height(Vec(65.5, 83.5)) == 1
    assert match._line_clear(Vec(65.5, 81), Vec(65.5, 86), 0)
    assert not nav.line_free(Vec(65.5, 81), Vec(65.5, 86), 0, 0)
    passage = Vec(62.5, 80.5), Vec(62.5, 88.5)
    assert nav.line_free(*passage, 0, 0)
    assert all(buy.cell(point) not in areas[0] | areas[1] for point in passage)


def test_breeze_mid_top_cover_leaves_the_b_tunnel_route_open_after_buy() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    buy, areas = match._buy_areas
    nav = NavGrid(world)
    assert world.ground_height(Vec(58, 92)) == 1
    assert match._line_clear(Vec(54, 92), Vec(62, 92), 0)
    assert not nav.line_free(Vec(54, 92), Vec(62, 92), 0, 0)
    tunnel, mid = Vec(48, 95), Vec(63, 95)
    assert buy.cell(tunnel) in areas[1]
    assert buy.cell(mid) not in areas[0] | areas[1]
    assert not buy.line_free(tunnel, mid)
    assert nav.line_free(tunnel, mid, 0, 0)


@pytest.mark.parametrize(("y", "landing_x"), [(77.5, 62), (79, 56.2)])
def test_breeze_b_elbow_window_passes_utility_through_the_opening(y: float, landing_x: float) -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    thrower = match.add_player("KAY/O", 0, "kayo")
    match.add_player("Defender", 1, "jett")
    match.start()
    match.phase_until = match.time
    match.tick(0.1, {})
    thrower.pos = Vec(54, y)
    target = Vec(62, y)
    nav = NavGrid(world)
    assert not nav.line_free(thrower.pos, target, 0, 0)
    assert nav.path(thrower.pos, target, start_ground=0, goal_ground=0)
    match.tick(1 / 64, {thrower.pid: Command(ability="E", facing=angle_of(target - thrower.pos),
                                            cursor_depth=10)})
    knife = next(effect for effect in match.effects if effect.props.get("thrown"))
    assert knife.pos.x == pytest.approx(landing_x)


def test_breeze_b_elbow_cover_leaves_the_turn_open() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    buy, areas = match._buy_areas
    nav = NavGrid(world)
    assert world.ground_height(Vec(49.5, 82)) == 1
    assert match._line_clear(Vec(47, 82), Vec(51, 82), 0)
    assert not nav.line_free(Vec(47, 82), Vec(51, 82), 0, 0)
    turn = Vec(34, 77), Vec(51, 79)
    assert nav.line_free(*turn, 0, 0)
    assert all(buy.cell(point) not in areas[0] | areas[1] for point in turn)
    foot, elbow = Vec(33, 68), Vec(33, 78.5)
    assert world.ground_height(Vec(33, 73)) == pytest.approx(0.5)
    assert nav.path(Vec(17, 69), foot, start_ground=0, goal_ground=0)
    assert nav.line_free(foot, elbow, 0, 0)
    assert nav.line_free(elbow, foot, 0, 0)
    assert all(buy.cell(point) not in areas[0] | areas[1] for point in (foot, elbow))


def test_breeze_b_tunnel_cover_leaves_sight_and_the_south_passage_open() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    nav = NavGrid(world)
    assert world.ground_height(Vec(44, 98)) == 1
    assert match._line_clear(Vec(41, 98), Vec(47, 98), 0)
    assert not nav.line_free(Vec(41, 98), Vec(47, 98), 0, 0)
    assert nav.line_free(Vec(41, 95), Vec(47, 95), 0, 0)
    site, tunnel = Vec(32.5, 95), Vec(48, 95)
    assert world.ground_height(Vec(38, 95)) == pytest.approx(0.5)
    assert nav.line_free(site, tunnel, 0, 0)
    assert nav.line_free(tunnel, site, 0, 0)
    buy, areas = match._buy_areas
    assert all(buy.cell(point) in areas[1] for point in (site, tunnel))
    assert buy.line_free(site, tunnel, 0, 0)
    assert not buy.line_free(tunnel, Vec(53, 95), 0, 0)


def test_breeze_b_wall_screens_the_cubby_and_leaves_the_south_passage_open() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    nav = NavGrid(world)
    assert not match._line_clear(Vec(28, 101), Vec(34, 101), 0)
    assert not nav.line_free(Vec(28, 101), Vec(34, 101), 0, 0)
    approach, plant = Vec(34, 97.5), Vec(21.5, 97)
    assert nav.line_free(approach, plant, 0, 0)
    assert match._line_clear(approach, plant, 0)


def test_breeze_b_cubby_cover_leaves_the_plant_approach_open() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    nav = NavGrid(world)
    assert not match._line_clear(Vec(27, 105.5), Vec(33, 105.5), 0)
    assert not nav.line_free(Vec(27, 105.5), Vec(33, 105.5), 0, 0)
    assert nav.path(Vec(33, 103), Vec(27, 103), start_ground=0, goal_ground=0)
    assert nav.line_free(Vec(27, 103), Vec(21.5, 97), 0, 0)


def test_breeze_b_back_low_cover_leaves_the_west_lane_open() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    nav = NavGrid(world)
    buy, areas = match._buy_areas
    assert world.ground_height(Vec(6.5, 95)) == 1
    assert match._line_clear(Vec(6.5, 92), Vec(6.5, 97.5), 0)
    assert not nav.line_free(Vec(6.5, 92), Vec(6.5, 97.5), 0, 0)
    back, corner, site = Vec(4.5, 92), Vec(4.5, 108), Vec(12.5, 108)
    assert all(buy.cell(point) in areas[1] for point in (back, corner, site))
    assert nav.line_free(back, corner, 0, 0)
    assert nav.line_free(corner, site, 0, 0)
    assert world.ground_height(Vec(9.5, 102)) == 1
    assert match._line_clear(Vec(9.5, 100.5), Vec(9.5, 102), 0)
    assert not nav.line_free(Vec(9.5, 100.5), Vec(9.5, 102), 0, 0)
    assert nav.line_free(Vec(11.5, 100.5), Vec(11.5, 103.5), 0, 0)


def test_breeze_b_back_wall_screens_the_site_and_leaves_a_route_around() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    nav = NavGrid(world)
    back, site = Vec(5.5, 96), Vec(12.5, 96)
    assert not match._line_clear(back, site, 0)
    assert not nav.line_free(back, site, 0, 0)
    assert not match._line_clear(Vec(5.5, 105), Vec(12.5, 105), 0)
    assert not nav.line_free(Vec(5.5, 105), Vec(12.5, 105), 0, 0)
    assert nav.line_free(Vec(5.5, 108), Vec(12.5, 108), 0, 0)
    assert nav.path(back, site, start_ground=0, goal_ground=0)
    assert not match._line_clear(Vec(15, 103), Vec(15, 107), 0)
    assert not nav.line_free(Vec(15, 103), Vec(15, 107), 0, 0)
    assert nav.line_free(Vec(19, 107), Vec(21.5, 97), 0, 0)


def test_breeze_b_main_west_cover_keeps_the_neutral_lane_open() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    buy, areas = match._buy_areas
    nav = NavGrid(world)
    assert world.ground_height(Vec(12, 65)) == 1
    assert match._line_clear(Vec(12, 62), Vec(12, 68), 0)
    assert not nav.line_free(Vec(12, 62), Vec(12, 68), 0, 0)
    approach, threshold = Vec(17, 61), Vec(17, 76)
    assert buy.line_free(approach, threshold)
    assert all(buy.cell(point) not in areas[0] | areas[1] for point in (approach, threshold))
    assert not buy.line_free(threshold, Vec(17, 83))
    assert nav.line_free(approach, Vec(17, 83), 0, 0)


def test_breeze_b_main_cover_leaves_the_site_entrance_open_after_buy() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    buy, _ = match._buy_areas
    nav = NavGrid(world)
    assert not match._line_clear(Vec(5, 86), Vec(12, 86), 0)
    assert not nav.line_free(Vec(5, 86), Vec(12, 86), 0, 0)
    approach, entry = Vec(17, 76), Vec(17, 83)
    assert not buy.line_free(approach, entry)
    assert nav.line_free(approach, entry, 0, 0)
    assert nav.line_free(entry, Vec(12.5, 94.5), 0, 0)
    assert world.ground_height(Vec(17, 77.5)) == pytest.approx(0.8)
    main, site = Vec(17, 69), Vec(17, 86)
    assert not buy.line_free(main, site, 0, 0)
    assert nav.line_free(main, site, 0, 0)
    assert nav.line_free(site, main, 0, 0)


@pytest.mark.parametrize("updraft", [False, True])
def test_breeze_mid_jump_requires_a_vertical_ability(updraft: bool) -> None:
    match = Match(load_playable_map("breeze"))
    player = match.add_player("Jett", 0, "jett")
    match.add_player("Defender", 1, "omen")
    match.start()
    match.phase_until = match.time
    match.tick(1 / 64, {})
    player.pos = Vec(60.5, 62.5)
    player.charges["Q"] = 1
    north = angle_of(Vec(0, 1))
    match.tick(1 / 64, {player.pid: Command(move_y=1, facing=north, jump=not updraft,
                                           ability="Q" if updraft else None)})
    for _ in range(40):
        if player.ground == 2:
            break
        match.tick(1 / 64, {player.pid: Command(move_y=1, facing=north)})
    for _ in range(64):
        match.tick(1 / 64, {})
    assert player.ground == (2 if updraft else 0) and player.z == 0


def test_breeze_mid_pillar_keeps_a_ground_route_around_mid_jump() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    buy, areas = match._buy_areas
    nav = NavGrid(world)
    assert world.ground_height(Vec(68.5, 68)) == 1
    assert world.ground_height(Vec(60.5, 65)) == 2
    assert match._line_clear(Vec(68.75, 65.5), Vec(68.75, 70), 0)
    assert not nav.line_free(Vec(68.75, 65.5), Vec(68.75, 70), 0, 0)
    assert not nav.line_free(Vec(60.5, 63), Vec(60.5, 73), 0, 0)
    assert nav.path(Vec(60.5, 63), Vec(60.5, 73), start_ground=0, goal_ground=0)
    start, end = Vec(71.5, 63), Vec(71.5, 73)
    assert nav.line_free(start, end, 0, 0)
    assert all(buy.cell(point) not in areas[0] | areas[1] for point in (start, end))


def test_breeze_mid_hall_cover_leaves_the_attacker_passage_open_after_buy() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    buy, areas = match._buy_areas
    nav = NavGrid(world)
    assert world.ground_height(Vec(93, 44)) == 1
    assert match._line_clear(Vec(90, 44), Vec(94, 44), 0)
    assert not nav.line_free(Vec(90, 44), Vec(94, 44), 0, 0)
    held, hall = Vec(88, 43), Vec(88, 49)
    assert buy.cell(held) in areas[0]
    assert buy.cell(hall) not in areas[0] | areas[1]
    assert not buy.line_free(held, hall)
    assert nav.line_free(held, hall, 0, 0)


def test_breeze_mid_nest_rotation_cover_preserves_the_defender_passage() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    buy, areas = match._buy_areas
    assert world.ground_height(Vec(61, 114)) == 1
    assert match._line_clear(Vec(58.5, 114), Vec(64, 114), 0)
    assert not buy.line_free(Vec(58.5, 114), Vec(64, 114), 0, 0)
    west, east = Vec(58.5, 116), Vec(68.5, 116)
    assert buy.line_free(west, east, 0, 0)
    assert all(buy.cell(point) in areas[1] for point in (west, east))


def test_breeze_defender_spawn_cover_leaves_the_rotation_open() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    buy, areas = match._buy_areas
    assert world.ground_height(Vec(60.5, 125)) == 1
    assert match._line_clear(Vec(58, 125), Vec(63, 125), 0)
    assert not buy.line_free(Vec(58, 125), Vec(63, 125), 0, 0)
    west, east = Vec(58, 123), Vec(63, 123)
    assert buy.line_free(west, east, 0, 0)
    assert all(buy.cell(point) in areas[1] for point in (west, east))
    for spawn in world.spawns[1]:
        assert buy.path(spawn, west)


def test_breeze_defender_arches_cover_leaves_the_north_passage_open() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    buy, areas = match._buy_areas
    west, east = Vec(36.5, 118.1), Vec(40.5, 118.1)
    assert not match._line_clear(west, east, 0)
    assert not buy.line_free(west, east, 0, 0)
    passage = Vec(36.5, 119.2), Vec(42, 119.2)
    assert buy.line_free(*passage, 0, 0)
    assert all(buy.cell(point) in areas[1] for point in passage)


def test_breeze_attacker_spawn_posts_leave_the_lobby_route_open() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    buy, areas = match._buy_areas
    for x in (58.875, 64.875):
        before, after = Vec(x, 17), Vec(x, 21)
        assert not match._line_clear(before, after, 0)
        assert not buy.line_free(before, after, 0, 0)
    assert buy.line_free(Vec(61.5, 17), Vec(61.5, 21), 0, 0)
    lobby = Vec(99, 37.5)
    assert buy.cell(lobby) in areas[0]
    for spawn in world.spawns[0]:
        assert buy.path(spawn, lobby)


def test_breeze_a_shop_cover_leaves_the_lobby_route_open_after_buy() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    buy, areas = match._buy_areas
    nav = NavGrid(world)
    assert world.ground_height(Vec(109, 43)) == 1
    assert match._line_clear(Vec(106, 43), Vec(112, 43), 0)
    assert not nav.line_free(Vec(106, 43), Vec(112, 43), 0, 0)
    lobby, approach, shop = Vec(99, 37.5), Vec(104, 37.5), Vec(106, 49)
    assert buy.cell(lobby) in areas[0]
    assert all(buy.cell(point) not in areas[0] | areas[1] for point in (approach, shop))
    assert not buy.line_free(lobby, approach)
    assert nav.line_free(lobby, approach, 0, 0)
    assert nav.line_free(approach, shop, 0, 0)


def test_breeze_a_main_cover_blocks_turret_targeting() -> None:
    match = Match(load_playable_map("breeze"))
    owner = match.add_player("Killjoy", 0, "killjoy")
    target = match.add_player("Defender", 1, "jett")
    match.start()
    match.phase_until = match.time
    match.tick(0.1, {})
    owner.pos, target.pos = Vec(104, 64), Vec(111, 62)
    match.tick(1 / 64, {owner.pid: Command(ability="E", facing=angle_of(Vec(1, 0)), cursor_depth=1)})
    turret = next(effect for effect in match.effects if effect.props.get("sprite") == "killjoy_turret")
    assert turret.pos == Vec(105, 64)
    initial_hp = target.hp
    for _ in range(90):
        match.tick(1 / 64, {})
    assert target.hp == initial_hp

    target.pos = Vec(111, 65)
    for _ in range(90):
        match.tick(1 / 64, {})
    assert target.hp < initial_hp


def test_breeze_a_main_cover_leaves_the_site_entrance_open_after_buy() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    buy, areas = match._buy_areas
    nav = NavGrid(world)
    assert not match._line_clear(Vec(104, 62), Vec(111, 62), 0)
    assert not nav.line_free(Vec(104, 62), Vec(111, 62), 0, 0)
    approach, entry = Vec(112, 57), Vec(112, 65)
    assert buy.cell(approach) not in areas[0] | areas[1]
    assert buy.cell(entry) in areas[1]
    assert not buy.line_free(approach, entry)
    assert nav.line_free(approach, entry, 0, 0)
    assert nav.path(entry, Vec(116.5, 70.5), start_ground=0, goal_ground=0)
    shop, main = Vec(112, 55), Vec(112, 66)
    assert world.ground_height(Vec(112, 60)) == pytest.approx(0.5)
    assert not buy.line_free(shop, main, 0, 0)
    assert nav.line_free(shop, main, 0, 0)
    assert nav.line_free(main, shop, 0, 0)


def test_breeze_a_back_site_cover_leaves_a_route_to_plant() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    nav = NavGrid(world)
    assert not match._line_clear(Vec(119, 82), Vec(125, 82), 0)
    assert not nav.line_free(Vec(119, 82), Vec(125, 82), 0, 0)
    assert nav.line_free(Vec(119, 79.5), Vec(126, 79.5), 0, 0)
    plant = Vec(130, 74)
    assert nav.line_free(Vec(126, 79.5), plant, 0, 0)
    assert world.site_at(plant, 0).name == "A"


def test_breeze_a_yellow_screens_back_site_and_keeps_the_side_route_open() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    nav = NavGrid(world)
    across_cover = Vec(102, 86.75), Vec(111, 86.75)
    beside_cover = Vec(102, 80.5), Vec(111, 80.5)
    assert not match._line_clear(*across_cover, 0)
    assert not nav.line_free(*across_cover, 0, 0)
    assert match._line_clear(*beside_cover, 0)
    assert nav.line_free(*beside_cover, 0, 0)
    for spawns in world.spawns.values():
        assert nav.path(spawns[2], beside_cover[1], start_ground=0, goal_ground=0)


def test_breeze_b_window_keeps_sight_and_blocks_the_direct_shortcut() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    window, main = Vec(17, 47), Vec(17, 52)
    nav = NavGrid(world)
    assert match._line_clear(window, main, 0)
    assert not nav.line_free(window, main, 0, 0)
    assert nav.path(window, main, start_ground=0, goal_ground=0)
    assert world.ground_height(Vec(29, 49.5)) == 1
    assert match._line_clear(Vec(29, 47.75), Vec(29, 51.5), 0)
    assert not nav.line_free(Vec(29, 47.75), Vec(29, 51.5), 0, 0)
    assert nav.line_free(Vec(31.5, 48), Vec(31.5, 52), 0, 0)


def test_breeze_mid_wood_doors_slit_only_passes_rays_at_window_height() -> None:
    world = load_playable_map("breeze")
    mid, site = Vec(92, 74.5), Vec(100, 74.5)
    assert Match(world)._line_clear(mid, site, 0)
    assert world.deck_blocks(mid, 1, site, 1)
    assert not world.deck_blocks(mid, 1.6, site, 1.6)
    assert world.deck_blocks(mid, 2.2, site, 2.2)
    nav = NavGrid(world)
    assert not nav.line_free(mid, site, 0, 0)
    assert nav.path(mid, site, start_ground=0, goal_ground=0)


def test_breeze_mid_wood_doors_cover_leaves_two_lines_through_the_opening() -> None:
    world = load_playable_map("breeze")
    match = Match(world)
    buy, _ = match._buy_areas
    nav = NavGrid(world)
    assert not match._line_clear(Vec(83, 72.75), Vec(88, 72.75), 0)
    assert not nav.line_free(Vec(83, 72.75), Vec(88, 72.75), 0, 0)
    for y in (69.5, 71):
        mid, site = Vec(88, y), Vec(98, y)
        assert not buy.line_free(mid, site)
        assert nav.line_free(mid, site, 0, 0)


def test_breeze_buy_lines_leave_neutral_approaches() -> None:
    world = load_playable_map("breeze")
    buy, areas = Match(world)._buy_areas
    live = NavGrid(world)
    for team, held, neutral in (
        (0, Vec(32, 44), Vec(26, 44)),  # B Window
        (0, Vec(31, 58), Vec(31, 63)),  # B Elbow approach
        (0, Vec(65, 43), Vec(65, 49)),  # Mid Bottom
        (0, Vec(88, 43), Vec(88, 49)),  # Mid Hall approach
        (0, Vec(99, 37.5), Vec(104, 37.5)),  # A Lobby
        (1, Vec(17, 83), Vec(17, 75)),  # B Main
        (1, Vec(48, 95), Vec(53, 95)),  # B Tunnel
        (1, Vec(66, 106), Vec(59, 106)),  # Mid Nest
        (1, Vec(88, 98), Vec(88, 93)),  # A Bridge
        (1, Vec(98, 70.5), Vec(91, 70.5)),  # Mid Wood Doors
        (1, Vec(111, 62), Vec(111, 56)),  # A Shop approach
    ):
        assert buy.cell(held) in areas[team]
        assert buy.cell(neutral) not in areas[0] | areas[1]
        assert not buy.line_free(held, neutral)
        assert live.line_free(held, neutral)

    # Val2D's lower A Ramp also connects directly to the defender side.
    held, neutral = Vec(96, 87), Vec(88, 87)
    assert buy.cell(held) in areas[1]
    assert buy.cell(neutral) not in areas[0] | areas[1]
    assert world.ground_height(neutral) == pytest.approx(0.55)
    assert not buy.line_free(held, neutral, start_ground=0, goal_ground=0.55)
    assert live.line_free(held, neutral, start_ground=0, goal_ground=0.55)
    assert live.line_free(neutral, held, start_ground=0.55, goal_ground=0)
    lower_hall = Vec(88, 94.5)
    assert buy.line_free(lower_hall, neutral, start_ground=0, goal_ground=0.55)
    assert buy.cell(lower_hall) not in areas[0] | areas[1]
    # The former A Link shortcut stays blocked after the barriers drop.
    hall, back_site = Vec(88, 92.5), Vec(97.5, 92.5)
    assert not Match(world)._line_clear(hall, back_site, 0)
    assert not live.line_free(hall, back_site, 0, 0)
    assert live.path(hall, back_site, start_ground=0, goal_ground=0)


@pytest.mark.parametrize("jump", [False, True])
def test_abyss_mid_gap_can_be_jumped_but_kills_and_returns_the_spike_on_a_fall(jump: bool) -> None:
    match = Match(load_playable_map("abyss"))
    runner = match.add_player("Runner", 0, "omen")
    match.add_player("Defender", 1, "jett")
    match.start()
    runner.pos = match.spike_pos
    match.tick(0, {})
    match.phase_until = match.time
    match.tick(1 / 64, {})
    gap, recovery = match.world.drop_zones[0]
    runner.weapons["primary"] = match._new_weapon("vandal")
    runner.pos = Vec(62.25, gap.y0 - 0.9)
    assert match.world.ground_height(runner.pos) == 0
    for i in range(65):
        match.tick(1 / 64, {runner.pid: Command(move_y=1, facing=0, jump=jump and i == 0)})
    if jump:
        assert runner.alive and runner.pos.y > gap.y1
        assert match.spike_carrier == runner.pid
    else:
        assert not runner.alive
        assert match.spike_pos == recovery
        assert not match.drops


def test_sage_cannot_resurrect_teammate_lost_in_abyss():
    from gameplay.kit.engine import resolve_target

    match = Match(load_playable_map("abyss"))
    sage = match.add_player("Sage", 0, "sage")
    teammate = match.add_player("Teammate", 0, "omen")
    match.add_player("Defender", 1, "jett")
    match.start()
    match.phase_until = match.time
    match.tick(1 / 64, {})
    gap, _ = match.world.drop_zones[0]
    sage.pos = Vec(62.25, gap.y0 - 1)
    sage.facing, sage.cursor_depth = 0, 1.2
    teammate.pos = sage.pos + Vec(0, 1.2)
    match._kill(None, teammate, "fall", "legs")
    ability = match.agents[sage.agent]["abilities"]["X"]
    assert match.world.drop_recovery(teammate.pos) is not None
    assert resolve_target(match, sage, ability) is None
    teammate.pos = sage.pos + Vec(0, 0.5)
    sage.cursor_depth = 0.5
    assert resolve_target(match, sage, ability) == teammate.pos


def test_summit_switches_close_linked_paths_until_the_next_round() -> None:
    match = Match(load_playable_map("summit"))
    match.add_player("Attacker", 0, "omen")
    match.add_player("Defender", 1, "jett")
    match.start()
    match.phase_until = match.time
    match.tick(1 / 64, {})
    links = match.world.drop_wall_links
    assert len(links) == 3 and set(links.values()) <= match.open_doors
    for switch, wall in links.items():
        target = next(w for w in match.world.walls if w.rect == switch)
        barrier = next(w for w in match.world.walls if w.rect == wall)
        assert not match.wall_active(barrier)
        match._damage_cover(target, 124)
        assert wall in match.open_doors
        match._damage_cover(target, 1)
        assert not match.wall_active(target) and match.wall_active(barrier)
    navigation = NavGrid(match.world, frozenset(match.broken_cover))
    assert all(navigation.path(spawns[2], site.rect.center)
               for spawns in match.world.spawns.values() for site in match.world.sites)
    match._start_round()
    assert not match.broken_cover and set(links.values()) <= match.open_doors


def test_fracture_attacker_transport_connects_both_buy_areas() -> None:
    match = Match(load_playable_map("fracture"))
    attacker = match.add_player("Attacker", 0, "omen")
    match.add_player("Defender", 1, "jett")
    match.start()
    grid, areas = match._buy_areas
    assert areas[0].isdisjoint(areas[1])
    for entry, exit_point in match.world.teleporters:
        assert grid.cell(entry.center) in areas[0]
        assert grid.cell(exit_point) in areas[0]
        attacker.pos = entry.center
        events = match.tick(1 / 64, {})
        assert attacker.pos == exit_point
        assert not any(event.kind == "sound_fx" for event in events)


@pytest.mark.parametrize("key", ["breeze", "fracture"])
def test_proximity_door_opens_and_closes(key: str) -> None:
    match = Match(load_playable_map(key))
    player = match.add_player("Attacker", 0, "omen")
    match.add_player("Defender", 1, "jett")
    match.start()
    match.phase_until = match.time
    match.tick(1 / 64, {})
    [(wall, trigger)] = match.world.automatic_doors.items()
    assert wall not in match.open_doors
    if key == "breeze":
        west, east = Vec(76, 56.75), Vec(84, 56.75)
        assert all(match.world.ground_height(point) == 0 for point in (west, wall.center, east))
        assert NavGrid(match.world).line_free(west, east, 0, 0)
    player.pos = trigger.center
    assert any(event.kind == "door" for event in match.tick(1 / 64, {}))
    assert wall in match.open_doors
    player.pos = match.world.spawns[0][0]
    match.tick(1 / 64, {})
    assert wall not in match.open_doors


@pytest.mark.parametrize(("x", "y", "opens"), [
    (76, 56.75, True), (84, 56.75, True), (76, 53.5, False),
])
def test_breeze_proximity_door_reacts_to_thrown_utility(x: float, y: float, opens: bool) -> None:
    match = Match(load_playable_map("breeze"))
    thrower = match.add_player("Attacker", 0, "kayo")
    match.add_player("Defender", 1, "jett")
    match.start()
    match.phase_until = match.time
    match.tick(1 / 64, {})
    [(wall, trigger)] = match.world.automatic_doors.items()
    thrower.pos = Vec(x, y)
    facing = angle_of(Vec(1 if x < wall.center.x else -1, 0))
    match.tick(1 / 64, {thrower.pid: Command(ability="E", facing=facing, cursor_depth=11)})
    assert wall not in match.open_doors
    knife = next(effect for effect in match.effects if effect.props.get("thrown"))
    if opens:
        assert (knife.pos.x - wall.center.x) * (x - wall.center.x) < 0
    events = []
    for _ in range(50):
        events.extend(event.data["open"] for event in match.tick(1 / 64, {}) if event.kind == "door")
    assert events == ([True, False] if opens else [])
    assert wall not in match.open_doors
    assert not trigger.contains(thrower.pos)


def test_lotus_doors_close_at_the_end_of_their_cycle() -> None:
    match = Match(load_playable_map("lotus"))
    player = match.add_player("Attacker", 0, "omen")
    match.add_player("Defender", 1, "jett")
    match.start()
    match.phase_until = match.time
    match.tick(1 / 64, {})
    assert len(match.world.timed_doors) == 2
    for wall, duration in match.world.timed_doors.items():
        player.pos = wall.center
        assert match._toggle_door(player)
        assert wall in match.open_doors and not match._toggle_door(player)
        player.pos = match.world.spawns[0][0]
        match.time += duration - 0.5
        match.tick(0.1, {})
        assert wall in match.open_doors
        match.time += 0.5
        assert any(event.kind == "door" for event in match.tick(0.1, {}))
        assert wall not in match.open_doors
