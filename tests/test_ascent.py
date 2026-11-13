"""Ascent's floor levels: stairs, Heaven too high to jump onto, B Main windows, cover on raised floors, bot paths."""
from __future__ import annotations

from gameplay.geometry import Vec
from gameplay.match import Command, Match
from gameplay.nav import grid_for
from gameplay.world import load_map


def setup() -> tuple[Match, int]:
    m = Match(load_map("ascent"), seed=1)
    pid = m.add_player("A", 0, "omen").pid
    m.start()
    m.phase_until = m.time
    m.tick(1 / 64, {})
    return m, pid


def place(m: Match, pid: int, x: float, top: float, reach: float = float("inf")) -> None:
    p = m.players[pid]
    p.pos, p.z, p.vz = Vec(x, m.world.height - top), 0.0, 0.0
    p.ground = m.world.ground_height(p.pos, reach)
    p.level = m.world.floor_level(p.pos, reach)
    p.vel = Vec(0, 0)


def walk(m: Match, pid: int, facing: float, seconds: float, jump: bool = False) -> None:
    for i in range(int(seconds * 64)):
        m.tick(1 / 64, {pid: Command(move_y=1.0, facing=facing, jump=jump and i % 20 == 0)})


def test_levels_of_the_main_areas() -> None:
    w = load_map("ascent")
    at = lambda x, top: w.ground_height(Vec(x, w.height - top))  # noqa: E731
    assert at(110, 52) == 2.0 and at(110, 40) == 3.0 and at(110, 31) == 6.0  # A front, raised plant floor, Heaven
    assert at(92, 52) == 2.0 and at(95, 37) == 3.0                           # A Tree below the Garden landing
    assert at(64, 65) == 1.0 and at(64, 55) == 2.0 and at(76, 75) == 2.0     # courtyard, Mid Bottom, Catwalk
    assert at(20, 35) == 0.0 and at(30, 47) == 1.0 and at(55, 38) == 2.0     # B site below B Lane, Market


def test_buy_phase_allows_leaving_spawn_and_opens_barriers_at_round_start() -> None:
    m = Match(load_map("ascent"))
    player = m.add_player("A", 0, "omen")
    m.start()
    place(m, player.pid, 97, 81)  # A Lobby, just outside the A Main barrier
    assert not m.world.spawn_zones[0].contains(player.pos)
    walk(m, player.pid, 0, 1.0)
    assert 78.0 <= m.world.height - player.pos.y <= 79.0
    assert m.buy(player, "frenzy")

    m.phase_until = m.time
    walk(m, player.pid, 0, 1.0)
    assert m.phase == "live"
    assert m.world.height - player.pos.y < 77.25


def test_buy_barriers_separate_the_teams_and_neutral_lanes_for_teleports() -> None:
    from gameplay.kit.builtins import can_land

    m = Match(load_map("ascent"))
    attacker = m.add_player("A", 0, "omen")
    defender = m.add_player("B", 1, "omen")
    m.start()

    def point(x: float, top: float) -> Vec:
        return Vec(x, m.world.height - top)

    assert sum(w.buy_phase_only for w in m.world.walls) == 10
    for p in (point(31, 75), point(97, 80), point(84, 90)):
        assert can_land(m, attacker, p)
        assert not can_land(m, defender, p)
    for p in (point(115, 46), point(34, 46), point(88, 56)):
        assert can_land(m, defender, p)
        assert not can_land(m, attacker, p)
    for p in (point(27, 60), point(65, 53), point(113, 65), point(49, 70)):
        assert not can_land(m, attacker, p) and not can_land(m, defender, p)


def test_stairs_climb_and_heaven_needs_its_stairs() -> None:
    m, pid = setup()
    p = m.players[pid]
    place(m, pid, 110, 52)
    walk(m, pid, 0.0, 1.5)  # north up the A site stairs
    assert p.ground == 3.0 and m.world.callout_at(p.pos) == "A Site"
    walk(m, pid, 180.0, 1.5)  # and back down
    assert p.ground == 2.0
    place(m, pid, 115, 36)
    walk(m, pid, 0.0, 1.5, jump=True)  # runs under the Heaven deck without jumping onto it
    assert p.ground == 3.0 and m.world.deck_at(p.pos) is not None
    place(m, pid, 101.5, 19)
    walk(m, pid, 180.0, 2.0)  # south up the Heaven stairs
    assert p.ground == 6.0


def test_b_main_high_windows_do_not_open_a_route_or_sightline_at_floor_height() -> None:
    m, pid = setup()
    p = m.players[pid]
    place(m, pid, 26.5, 52)
    walk(m, pid, 0.0, 1.5, jump=True)  # north into the west window
    assert m.world.height - p.pos.y > 50.0 and m.world.callout_at(p.pos) == "B Main"
    for x in (26.5, 32.5):
        assert not m._line_clear(Vec(x, m.world.height - 52), Vec(x, m.world.height - 47), 1)
    place(m, pid, 41, 52)
    walk(m, pid, 0.0, 0.8)
    assert m.world.height - p.pos.y < 49


def test_deck_separates_players_and_allows_drop_to_site() -> None:
    m, pid = setup()
    upper = m.players[pid]
    lower = m.add_player("B", 1, "jett")
    place(m, pid, 114, 32)
    place(m, lower.pid, 114, 32, reach=3)
    assert (upper.ground, lower.ground) == (6, 3)
    assert m.world.callout_at(upper.pos, upper.level) == "A Rafters"
    assert m.world.callout_at(lower.pos, lower.level) == "A Hell"
    assert not m.can_see(upper, lower) and not m.line_of_fire(lower, upper)
    m.spike_pos, m.spike_ground = lower.pos, lower.ground
    assert m.near_spike(lower, 1) and not m.near_spike(upper, 1)
    m.spike_pos = None
    lower.z, lower.vz = 1, 14
    for _ in range(12):
        m.tick(1 / 64, {})
    assert lower.ground == 3 and lower.z <= 1.4
    walk(m, pid, 180, 1.2)
    assert upper.ground == 3 and m.world.height - upper.pos.y > 34


def test_bot_paths_reach_both_deck_surfaces() -> None:
    world = load_map("ascent")
    grid = grid_for(world)
    target = Vec(114, world.height - 32)
    assert grid.cell(target, 3) != grid.cell(target, 6)
    assert grid.path(world.spawns[0][2], target, goal_ground=3)
    assert grid.path(world.spawns[1][2], target, goal_ground=6)
    assert not grid.line_free(target, target, 3, 6)


def test_lobby_approaches_are_walkable_in_both_directions() -> None:
    m, pid = setup()
    p = m.players[pid]
    for x, top, start, end in ((97, 74, 1, 2), (27, 67, 0.5, 1)):
        place(m, pid, x, top)
        assert p.ground == start
        walk(m, pid, 0, 1.15)
        assert p.ground == end
        walk(m, pid, 180, 1.15)
        assert p.ground == start


def test_ability_damage_hits_closed_door_and_mid_panel_without_player_targets() -> None:
    from gameplay.kit.engine import use

    m, pid = setup()
    p = m.players[pid]
    door = next(w for w in m.world.walls if w.switch and w.rect.center.x > 90)
    panel = next(w for w in m.world.walls if w.material == "obj:ascent_mid_panel")
    place(m, pid, 99, 52.5)
    p.facing = 90
    fury = m.agents["sova"]["abilities"]["X"]
    use(m, p, "X", fury)
    for _ in range(60):
        m.tick(1 / 64, {})
    assert m.cover_health[door.rect] == door.hp  # open doors cannot take damage
    m.effects.clear()
    m.open_doors.remove(door.rect)
    use(m, p, "X", fury)
    for _ in range(60):
        m.tick(1 / 64, {})
    assert m.cover_health[door.rect] == door.hp - 80
    m.effects.clear()
    strike = m.agents["brimstone"]["abilities"]["X"]
    use(m, p, "X", strike, point=panel.rect.center)
    for _ in range(2 * 64):
        m.tick(1 / 64, {})
    assert 0 < m.cover_health[panel.rect] < panel.hp


def test_thrown_projectile_breaks_a_window_in_flight() -> None:
    from gameplay.kit.engine import use

    m, pid = setup()
    p = m.players[pid]
    glass = next(w for w in m.world.walls if w.material == "obj:ascent_glass")
    place(m, pid, 94.5, 35.5)
    bolt = m.agents["sova"]["abilities"]["E"]
    use(m, p, "E", bolt, point=Vec(94.5, m.world.height - 32.5))
    assert m.wall_active(glass)
    for _ in range(24):
        m.tick(1 / 64, {})
    assert not m.wall_active(glass)


def test_crate_on_a_raised_floor_is_still_cover() -> None:
    w = load_map("ascent")
    site = w.site_at
    dice = [wl for wl in w.walls if wl.material == "obj:ascent_radianite_crate" and site(wl.rect.center)
            and site(wl.rect.center).name == "A"]
    assert dice and all(wl.top == 4.0 for wl in dice)  # one level above the A site floor
    assert w.ground_height(dice[0].rect.center) == 4.0


def test_bots_reach_every_area() -> None:
    w = load_map("ascent")
    grid = grid_for(w)
    for x, top in ((110, 40), (112, 31), (20, 35), (64, 55), (76, 75), (125, 63), (95, 37)):
        assert grid.path(w.spawns[0][2], Vec(x, w.height - top)), (x, top)


def test_every_stair_rises_without_steps() -> None:
    w = load_map("ascent")
    for rect, axis, high_at_min, top, low in w.ramp_profiles():
        c = rect.center
        span = (rect.x1 - rect.x0) if axis == "x" else (rect.y1 - rect.y0)
        start = (rect.x0 if axis == "x" else rect.y0) - 0.3
        heights = []
        for i in range(int((span + 0.6) / 0.25) + 1):
            v = start + i * 0.25
            point = Vec(v, c.y) if axis == "x" else Vec(c.x, v)
            if not any(wl.full and wl.rect.contains(point) for wl in w.walls):  # floor only, not inside walls
                heights.append(w.ground_height(point))
        steps = [abs(b - a) for a, b in zip(heights, heights[1:])]
        assert max(steps) < 0.3, (rect, heights)

def test_ascent_switch_door_and_breakables_reset_each_round() -> None:
    from gameplay.match import heading
    from gameplay.geometry import angle_of

    m, pid = setup()
    player = m.players[pid]
    door = next(w for w in m.world.walls if w.switch and w.rect.center.x > 90)
    assert not m.wall_active(door)
    player.pos = door.rect.center
    assert not m._toggle_door(player)
    player.pos = door.switch
    assert m._toggle_door(player) and m.wall_active(door)
    assert not m._toggle_door(player) and m.wall_active(door)

    # Fire directly into the closed door from A Tree.
    place(m, pid, 99, 52.5)
    weapon = m.weapons[player.weapon.key]
    direction = heading(angle_of(door.rect.center - player.pos))
    for _ in range(50):
        m._trace(player, weapon, direction, direction)
        if not m.wall_active(door):
            break
    assert door.rect in m.broken_cover
    player.pos = door.switch
    assert not m._toggle_door(player)

    glass = next(w for w in m.world.walls if w.material == "obj:ascent_glass")
    place(m, pid, 94.5, 35.5)
    direction = heading(0)
    assert m.wall_active(glass) and not glass.blocks_sight
    m._trace(player, weapon, direction, direction)
    assert not m.wall_active(glass)
    assert list((glass.rect.x0, glass.rect.y0, glass.rect.x1, glass.rect.y1)) in m.snapshot()["cover_broken"]

    m._start_round()
    assert not m.wall_active(door) and m.wall_active(glass)
    assert m.cover_health[door.rect] == 500


def test_mid_panels_stop_bullets_until_destroyed_and_keep_sills() -> None:
    m, pid = setup()
    for panel in (w for w in m.world.walls if w.material == "obj:ascent_mid_panel"):
        assert panel.hp == 400 and panel.penetration == 3 and panel.blocks_sight
        m._damage_cover(panel, 399)
        assert m.wall_active(panel, for_sight=True)
        m._damage_cover(panel, 1)
        assert not m.wall_active(panel)
        sill = next(w for w in m.world.walls if w.low and w.rect.contains(panel.rect.center))
        assert m.wall_active(sill) and not sill.blocks_sight
