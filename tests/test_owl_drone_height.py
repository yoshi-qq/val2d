import pytest

from gameplay.geometry import Rect, Vec
from gameplay.match import Command
from gameplay.world import Deck, Platform, Wall
from test_valorant_agents import advance, match_for


@pytest.mark.parametrize(("slot", "maximum"), [("Q", 28), ("E", 30)])
def test_sova_bolt_charge_controls_landing_distance(monkeypatch, slot, maximum):
    import pygame
    from dataclasses import replace

    from client.game import Game
    from gameplay.kit.engine import resolve_target
    from test_client import args

    game = Game(args(agent="sova", team_size=1))
    match, pid, _ = match_for("sova")
    game.match, game.me = match, pid
    sova = match.players[pid]
    sova.charges[slot] = 1
    sova.facing = 0
    spec = match.agents["sova"]["abilities"][slot]
    now = 1000
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now)
    game.set_aim(slot)
    cmd = Command()
    for expected in (1, 2, 0):
        game.aim_click(sova, cmd, 3, (0, 0))
        assert game.bounces == expected and cmd.ability is None
    game.aim_click(sova, cmd, 1, (0, 0))
    assert cmd.ability is None and game.charge_started == now
    for elapsed, distance in [(0, 6), (500, (6 + maximum) / 2), (1200, maximum)]:
        now = 1000 + elapsed
        shooter = replace(sova, cursor_depth=game.charged_depth(spec))
        assert resolve_target(match, shooter, spec) == sova.pos + Vec(0, distance)
    match.tick(1 / 64, {pid: Command(ability=slot, facing=0, cursor_depth=game.charged_depth(spec))})
    assert sova.charges[slot] == 0
    assert match.effects[0].pos == sova.pos + Vec(0, maximum)


@pytest.mark.parametrize("slot", ["Q", "E"])
@pytest.mark.parametrize(("bounces", "expected"), [(0, 14.7), (1, 5.3), (2, 10)])
def test_sova_bolt_reflects_off_walls(slot, bounces, expected):
    from gameplay.net import apply_snapshot, command_from_json

    match, pid, _ = match_for("sova")
    match.players[pid].charges[slot] = 1
    match.world.walls.extend([Wall(Rect(4, 15, 16, 16), 3), Wall(Rect(4, 4, 16, 5), 3)])
    cmd = command_from_json(dict(ability=slot, facing=0, cursor_depth=20, bounces=bounces))
    match.tick(1 / 64, {pid: cmd})
    [bolt] = match.effects
    assert bolt.pos.y == pytest.approx(expected)
    if bounces:
        assert len(bolt.props["bolt_path"]) == bounces + 2
        replica = type(match)(match.world)
        apply_snapshot(replica, match.snapshot(pid), pid)
        assert replica.effects[0].props["bolt_path"] == bolt.props["bolt_path"]


@pytest.mark.parametrize("slot", ["Q", "E"])
@pytest.mark.parametrize("wall_removed", [True, False])
@pytest.mark.parametrize("bounces", [0, 1])
def test_sova_bolt_updates_path_when_cover_changes(slot, wall_removed, bounces):
    match, pid, _ = match_for("sova")
    match.players[pid].charges[slot] = 1
    wall = Wall(Rect(4, 18, 16, 19), 3)
    if wall_removed:
        match.world.walls.append(wall)
    dt = 1 / 64
    match.tick(dt, {pid: Command(ability=slot, facing=0, cursor_depth=20, bounces=bounces)})
    [bolt] = match.effects
    advance(match, 0.0625)
    if wall_removed:
        match.broken_cover.add(wall.rect)
    else:
        match.world.walls.append(wall)
    match.tick(dt, {})
    assert 10 < bolt.a.y < 18
    assert bolt.pos.y == pytest.approx(30 if wall_removed else (6 if bounces else 17.7))
    assert len(bolt.props["bolt_path"]) == (3 if bounces and not wall_removed else 2)


@pytest.mark.parametrize("slot", ["Q", "E"])
@pytest.mark.parametrize(("bounces", "landing"), [(1, 8.3), (2, 13.7)])
def test_sova_bolt_keeps_spent_bounce_after_cover_changes(slot, bounces, landing):
    match, pid, _ = match_for("sova")
    match.players[pid].charges[slot] = 1
    match.world.walls.append(Wall(Rect(4, 14, 16, 15), 3))
    dt = 1 / 64
    match.tick(dt, {pid: Command(ability=slot, facing=0, cursor_depth=16, bounces=bounces)})
    [bolt] = match.effects
    advance(match, 0.25)
    match.world.walls.append(Wall(Rect(4, 7, 16, 8), 3))
    match.tick(dt, {})
    assert 8 < bolt.a.y < 14
    # With two selected bounces, the reflection meets the original wall again.
    assert bolt.pos.y == pytest.approx(landing)
    assert len(bolt.props["bolt_path"]) == bounces + 1


@pytest.mark.parametrize("slot", ["Q", "E"])
@pytest.mark.parametrize("remove_cover", [False, True])
def test_sova_bolt_applies_effect_at_recomputed_impact(slot, remove_cover):
    match, pid, enemy_id = match_for("sova")
    enemy = match.players[enemy_id]
    enemy.pos = Vec(10, 6 if remove_cover else 11)
    health = enemy.hp
    match.players[pid].charges[slot] = 1
    match.world.walls.append(Wall(Rect(4, 14, 16, 15), 3))
    cover = Wall(Rect(4, 7, 16, 8), 3)
    if remove_cover:
        match.world.walls.append(cover)
    dt = 1 / 64
    match.tick(dt, {pid: Command(ability=slot, facing=0, cursor_depth=16, bounces=1)})
    [bolt] = match.effects
    original_impact = bolt.until
    if remove_cover:
        while match.time + dt < original_impact:
            match.tick(dt, {})
        match.broken_cover.add(cover.rect)
    else:
        advance(match, 0.25)
        match.world.walls.append(cover)
    match.tick(dt, {})
    assert (bolt.until > original_impact) if remove_cover else (bolt.until < original_impact)
    if remove_cover:
        assert bolt in match.effects and match.time >= original_impact
        assert enemy.hp == health and enemy.revealed_until <= match.time
        assert len(match.effects) == 1
    while match.time + dt < bolt.until:
        match.tick(dt, {})
    assert bolt in match.effects
    assert enemy.hp == health and enemy.revealed_until <= match.time
    match.tick(dt, {})
    assert bolt not in match.effects
    if slot == "Q":
        assert enemy.hp < health
    else:
        [sensor] = match.effects
        assert sensor.pos == bolt.pos
        assert sensor.start == match.time
        while match.time + dt < sensor.start + 0.67:
            match.tick(dt, {})
        assert enemy.revealed_until <= match.time
        match.tick(dt, {})
        assert enemy.revealed_until == pytest.approx(match.time + 0.75)
        while match.time + dt < sensor.start + 2.27:
            match.tick(dt, {})
        assert enemy.revealed_until <= match.time
        match.tick(dt, {})
        assert enemy.revealed_until == pytest.approx(match.time + 0.75)


def test_owl_drone_equips_before_primary_fire_deploys(monkeypatch):
    import pygame

    from client.game import Game
    from test_client import args

    game = Game(args(agent="sova", team_size=1))
    match, pid, _ = match_for("sova")
    game.match, game.me = match, pid
    sova = match.players[pid]
    sova.charges["C"] = 1
    now = 1000
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now)
    assert game.needs_aim(sova, "C")
    game.set_aim("C")
    assert game.aim_ready_at == 1900
    assert not match.effects and sova.charges["C"] == 1

    cmd = Command()
    now = 1899
    game.aim_click(sova, cmd, 1, (0, 0))
    assert cmd.ability is None and game.aiming == "C"
    now = 1900
    game.aim_click(sova, cmd, 3, (0, 0))
    assert cmd.ability is None and game.aiming == "C"
    wall = Rect(8, 10.5, 12, 10.6)
    from gameplay.world import Wall
    match.world.walls.append(Wall(wall, 3))
    game.aim_click(sova, cmd, 1, (0, 0))
    assert cmd.ability is None and game.aiming == "C"
    match.world.walls.clear()
    game.aim_click(sova, cmd, 1, (0, 0))
    assert cmd.ability == "C" and game.aiming is None
    match.tick(1 / 64, {pid: cmd})
    [drone] = match.effects
    assert sova.charges["C"] == 0 and drone.start - match.time == pytest.approx(0.25)


@pytest.mark.parametrize(("ticks", "marks", "takes_damage"), [
    (8, True, True),
    (28, True, False),
    (56, False, False),
])
def test_flight_height_controls_dart_and_bullet_hits(ticks, marks, takes_damage):
    match, pid, enemy_id = match_for("sova")
    sova, enemy = match.players[pid], match.players[enemy_id]
    sova.charges["C"] = 1
    enemy.pos = Vec(10, 16)
    match.tick(1 / 64, {pid: Command(ability="C", facing=0)})
    [drone] = match.effects
    advance(match, 0.25)
    for _ in range(ticks):
        match.tick(1 / 64, {pid: Command(jump=True)})

    match.tick(1 / 64, {pid: Command(fire=True, facing=0)})
    assert ("owl_drone_spotted" in enemy.status) is marks
    hp = drone.data["hp"]
    weapon = match._weapon_def(enemy)
    assert weapon is not None
    match._trace(enemy, weapon, Vec(0, -1), Vec(0, -1))
    assert (drone.data["hp"] < hp) is takes_damage


@pytest.mark.parametrize(("pitch", "deck", "marks"), [(0, False, False), (20, False, True), (20, True, False)])
def test_owl_drone_aims_at_a_raised_target(pitch, deck, marks):
    match, pid, enemy_id = match_for("sova")
    sova, enemy = match.players[pid], match.players[enemy_id]
    sova.charges["C"] = 1
    enemy.pos = Vec(10, 17)
    match.world.platforms.append(Platform(Rect(9, 16.8, 11, 19), 2))
    if deck:
        match.world.decks.append(Deck(Rect(9, 13, 11, 16), 1, 0))
    advance(match, 1 / 64)
    enemy.ground, enemy.level = 2, 2
    match.tick(1 / 64, {pid: Command(ability="C", facing=0)})
    advance(match, 0.25)

    match.tick(1 / 64, {pid: Command(fire=True, facing=0, drone_pitch=pitch)})
    assert ("owl_drone_spotted" in enemy.status) is marks


def test_sova_bot_pilots_owl_drone_and_marks_with_a_dart():
    from gameplay.bots import BotDirector

    match, pid, enemy_id = match_for("sova")
    bot, enemy = match.players[pid], match.players[enemy_id]
    bot.is_bot = True
    bot.charges["C"], bot.charges["E"], bot.charges["Q"] = 1, 0, 0
    enemy.pos = Vec(10, 16)
    wall = Wall(Rect(8, 13, 12, 13.2), 3)
    match.world.walls.append(wall)
    director = BotDirector(match)
    director.sync()
    brain = director.brains[pid]
    brain.goal = Vec(10, 20)
    brain.rng.seed(31)  # first placement roll is below 2%
    dt = 1 / 64

    match.tick(dt, director.commands(dt))
    [drone] = match.effects
    body, launch = bot.pos, drone.pos
    for _ in range(28):
        match.tick(dt, director.commands(dt))
    assert bot.pos == body and drone.pos.y > launch.y
    assert "dart_ready" not in drone.data and "owl_drone_spotted" not in enemy.status

    match.world.walls.remove(wall)
    events = match.tick(dt, director.commands(dt))
    assert drone.data["dart_ready"] == pytest.approx(match.time + 5)
    assert [e.data["pid"] for e in events if e.kind == "owl_dart_hit"] == [pid, enemy_id]
    assert "owl_drone_spotted" in enemy.status and enemy.revealed_until <= match.time
    ready = drone.data["dart_ready"]
    for _ in range(104):
        match.tick(dt, director.commands(dt))
    assert drone.data["dart_ready"] == ready and enemy.revealed_until > match.time


@pytest.mark.parametrize(("wall_height", "deck_height", "second_wall"), [
    (1, None, False), (1, 1.25, False), (2, None, False), (2, None, True),
])
def test_owl_drone_bot_flies_over_or_around_cover(wall_height, deck_height, second_wall):
    from gameplay.bots import BotDirector

    match, pid, enemy_id = match_for("sova")
    bot = match.players[pid]
    bot.is_bot = True
    bot.charges["C"], bot.charges["E"], bot.charges["Q"] = 1, 0, 0
    match.players[enemy_id].pos = Vec(90, 90)
    match.world.walls.append(Wall(Rect(8, 13, 12, 13.2), 3, height=wall_height))
    if second_wall:
        match.world.walls.append(Wall(Rect(9, 14, 16, 15), 3))
    if deck_height is not None:
        match.world.decks.append(Deck(Rect(8, 9, 12, 18), deck_height, 0))
    director = BotDirector(match)
    director.sync()
    brain = director.brains[pid]
    brain.goal = Vec(10, 20)
    dt = 1 / 64
    match.tick(dt, {pid: Command(ability="C", facing=0)})
    [drone] = match.effects

    heights = []
    for _ in range(300):
        match.tick(dt, director.commands(dt))
        heights.append(drone.props.get("flight_height", 0))
    if deck_height is None and wall_height == 1:
        assert max(heights) >= 1 and drone.pos.y > 13.2
        assert heights[-1] < 0.1
    else:
        assert max(heights) < 1 and drone.pos.y > 15
        assert abs(drone.pos.x - 10) < 0.4


@pytest.mark.parametrize("ascending", [True, False])
@pytest.mark.parametrize("blocked_edge", [None, "approach", "return", "all_returns", "all_approaches"])
def test_owl_drone_bot_changes_deck_sides_at_the_edge(ascending, blocked_edge):
    from gameplay.bots import BotDirector

    match, pid, _ = match_for("sova")
    bot = match.players[pid]
    bot.is_bot = True
    bot.charges["C"] = 1
    deck = Deck(Rect(8, 8, 12, 18), 2, 0)
    match.world.decks.append(deck)
    if blocked_edge == "approach":
        match.world.walls.append(Wall(Rect(7, 9, 8.2, 17), 3))
    start_height, goal_height = (0, 2) if ascending else (2, 0)
    if blocked_edge == "return":
        match.world.walls.append(Wall(Rect(8.1, 12, 9.2, 14.5), 3, height=1, base=goal_height))
    if blocked_edge == "all_returns":
        match.world.walls.extend([
            Wall(Rect(8, 17.5, 12, 18.5), 3),
            Wall(Rect(5, 13.8, 12, 14.2), 3, base=goal_height),
        ])
    if blocked_edge == "all_approaches":
        match.world.walls.extend([
            Wall(Rect(7, 9, 8.2, 17), 3),
            Wall(Rect(11.8, 9, 13, 17), 3),
            Wall(Rect(8, 7, 12, 8.2), 3),
            Wall(Rect(9.5, 13.8, 10.5, 14.2), 3, height=1, base=start_height),
        ])
    bot.ground = bot.level = start_height
    match.spike_pos, match.spike_ground = Vec(10, 15), goal_height
    director = BotDirector(match)
    director.sync()
    director.brains[pid].goal = match.spike_pos
    dt = 1 / 64
    match.tick(dt, {pid: Command(ability="C", facing=0)})
    [drone] = match.effects

    left_deck = False
    for _ in range(380):
        before = drone.pos
        height = drone.props.get("flight_height", start_height)
        match.tick(dt, director.commands(dt))
        after = drone.props.get("flight_height", start_height)
        left_deck |= not deck.rect.contains(drone.pos)
        if (height >= deck.level) != (after >= deck.level):
            assert not deck.rect.contains(before)
            if blocked_edge == "all_approaches":
                assert before.y > deck.rect.y1
            elif blocked_edge:
                assert before.x > deck.rect.x1
    assert left_deck
    assert (drone.pos - match.spike_pos).length() <= 0.4
    assert drone.props["flight_height"] == pytest.approx(goal_height, abs=0.05)


@pytest.mark.parametrize("ascending", [True, False])
@pytest.mark.parametrize(("on_return", "remaining", "reaches_goal"), [
    (False, None, True), (True, None, True), (True, 2.5, True), (True, 1.25, False),
])
def test_owl_drone_bot_replans_when_spike_changes_level(ascending, on_return, remaining, reaches_goal):
    from gameplay.bots import BotDirector

    match, pid, enemy_id = match_for("sova")
    bot = match.players[pid]
    bot.is_bot = True
    bot.charges["C"] = 1
    match.world.decks.append(Deck(Rect(8, 8, 12, 18), 2, 0))
    start_height, goal_height = (0, 2) if ascending else (2, 0)
    bot.ground = bot.level = start_height
    match.spike_pos, match.spike_ground = Vec(10, 15), goal_height
    director = BotDirector(match)
    director.sync()
    director.brains[pid].goal = match.spike_pos
    dt = 1 / 64
    match.tick(dt, {pid: Command(ability="C", facing=0)})
    [drone] = match.effects
    for _ in range(150):
        match.tick(dt, director.commands(dt))
        if on_return and drone.data.get("bot_return_goal") == match.spike_pos and match.world.deck_at(drone.pos):
            break
        if (not on_return and match.world.deck_at(drone.pos) is None
                and abs(drone.props.get("flight_height", start_height) - start_height) >= 0.5):
            break
    else:
        pytest.fail("Drone never reached the requested flight phase")
    pos, height = drone.pos, drone.props["flight_height"]
    if remaining is not None:
        drone.until = match.time + remaining
    match.spike_ground = start_height
    if not on_return:
        match.tick(dt, director.commands(dt))
        assert drone.pos == pos
        assert abs(drone.props["flight_height"] - start_height) < abs(height - start_height)
    exited = not on_return
    if not reaches_goal:
        # Let the bot hold for one tick before a target comes into dart range.
        match.tick(dt, director.commands(dt))
        assert drone.pos == pos
        enemy = match.players[enemy_id]
        enemy.pos = Vec(10, 15)
        enemy.ground = enemy.level = goal_height
    dart_hits = []
    while match.time + dt < drone.until:
        before = drone.pos
        before_height = drone.props["flight_height"]
        events = match.tick(dt, director.commands(dt))
        dart_hits.extend(e.data["pid"] for e in events if e.kind == "owl_dart_hit")
        exited |= match.world.deck_at(drone.pos) is None
        if (before_height >= 2) != (drone.props["flight_height"] >= 2):
            assert match.world.deck_at(before) is None
    assert exited == reaches_goal
    if not reaches_goal:
        assert drone.pos == pos
        assert (drone.props["flight_height"] >= 2) == (height >= 2)
        assert dart_hits == [pid, enemy_id]
        assert enemy.status["owl_drone_spotted"] > match.time
        impact = drone.data["dart_ready"] - 5
        assert enemy.revealed_until <= match.time
        match.tick(dt, {})
        assert drone not in match.effects
        for delay in (1.6, 3.4):
            while match.time + dt < impact + delay:
                match.tick(dt, {})
            assert enemy.revealed_until <= match.time
            match.tick(dt, {})
            assert enemy.revealed_until == pytest.approx(match.time + 0.6)
        return
    assert (drone.pos - match.spike_pos).length() <= 0.4
    assert drone.props["flight_height"] == pytest.approx(start_height, abs=0.05)


@pytest.mark.parametrize(("flight_time", "reaches_goal"), [(2.5, False), (4, True)])
def test_owl_drone_bot_reserves_time_to_change_height(flight_time, reaches_goal):
    from gameplay.bots import BotDirector

    match, pid, _ = match_for("sova")
    bot = match.players[pid]
    bot.is_bot = True
    bot.charges["C"] = 1
    match.world.decks.append(Deck(Rect(8, 8, 12, 18), 2, 0))
    match.spike_pos, match.spike_ground = Vec(10, 15), 2
    director = BotDirector(match)
    director.sync()
    director.brains[pid].goal = match.spike_pos
    dt = 1 / 64
    match.tick(dt, {pid: Command(ability="C", facing=0)})
    [drone] = match.effects
    launch = drone.pos
    drone.until = drone.start + flight_time
    while match.time + dt < drone.until:
        match.tick(dt, director.commands(dt))
    if reaches_goal:
        assert (drone.pos - match.spike_pos).length() <= 0.4
        assert drone.props["flight_height"] == pytest.approx(2)
    else:
        assert drone.pos == launch
        assert drone.props["flight_height"] == 0


@pytest.mark.parametrize("phase", ["climb", "return", "shaft", "descending_shaft"])
@pytest.mark.parametrize("enough_time", [True, False])
def test_owl_drone_bot_replans_return_after_barrier_appears(phase, enough_time):
    from gameplay.bots import BotDirector
    from gameplay.match import Effect

    match, pid, enemy_id = match_for("sova")
    bot = match.players[pid]
    bot.is_bot = True
    bot.charges["C"] = 1
    match.world.decks.append(Deck(Rect(8, 8, 12, 18), 2, 0))
    descending = phase.startswith("descending")
    bot.ground = bot.level = 2 if descending else 0
    goal_height = 0 if descending else 2
    match.spike_pos, match.spike_ground = Vec(10, 15), goal_height
    director = BotDirector(match)
    director.sync()
    director.brains[pid].goal = match.spike_pos
    dt = 1 / 64
    match.tick(dt, {pid: Command(ability="C", facing=0)})
    [drone] = match.effects
    for _ in range(200):
        match.tick(dt, director.commands(dt))
        if descending and 1.5 < drone.props.get("flight_height", 2) < 1.85:
            break
        if phase in ("climb", "shaft") and 0 < drone.props.get("flight_height", 0) < 2:
            break
        if phase == "return" and drone.data.get("bot_return_goal") == match.spike_pos:
            break
    else:
        pytest.fail("Drone never began the requested phase")
    pos = drone.pos
    height = drone.props["flight_height"]
    if not enough_time:
        drone.until = match.time + abs(goal_height - height) / 2 + 0.3
    rect = Rect(8.5, 12, 9.1, 15.3)
    if phase in ("shaft", "descending_shaft"):
        rect = Rect(pos.x - 0.2, pos.y - 0.2, pos.x + 0.2, pos.y + 0.2)
    match.effects.append(Effect("wall", enemy_id, 1, rect.center, drone.until,
                                props={"barrier": Wall(rect, 3, base=goal_height, ceiling=1.5 if descending else None)}))
    if descending:
        assert drone.data.get("bot_deck_edge") is not None
        assert rect.contains(drone.pos)
    while match.time + dt < drone.until:
        match.tick(dt, director.commands(dt))
    if enough_time:
        assert (drone.pos - match.spike_pos).length() <= 0.4
        assert drone.props["flight_height"] == pytest.approx(goal_height, abs=0.05)
    else:
        assert drone.pos == pos
        assert drone.props["flight_height"] == height


@pytest.mark.parametrize(("ascending", "detour_ticks", "remaining", "reaches_goal"), [
    (False, 0, None, True), (False, 4, None, True), (False, 8, None, True),
    (False, 8, 2.4, True), (False, 8, 1.4, False),
    (True, 4, 2.4, True), (True, 4, 1.2, False),
])
def test_owl_drone_bot_resumes_height_change_after_barrier_breaks(ascending, detour_ticks, remaining, reaches_goal):
    from gameplay.bots import BotDirector
    from gameplay.match import Effect

    match, pid, enemy_id = match_for("sova")
    bot = match.players[pid]
    bot.is_bot = True
    bot.charges["C"] = 1
    bot.ground = bot.level = 0 if ascending else 2
    goal_height = 2 if ascending else 0
    match.world.decks.append(Deck(Rect(8, 8, 12, 18), 2, 0))
    match.spike_pos, match.spike_ground = Vec(10, 15), goal_height
    director = BotDirector(match)
    director.sync()
    director.brains[pid].goal = match.spike_pos
    dt = 1 / 64
    match.tick(dt, {pid: Command(ability="C", facing=0)})
    [drone] = match.effects
    for _ in range(120):
        match.tick(dt, director.commands(dt))
        height = drone.props.get("flight_height", bot.level)
        if (0 < height < 0.2) if ascending else (1.5 < height < 1.85):
            break
    else:
        pytest.fail("Drone never began descending")
    pos, height = drone.pos, drone.props["flight_height"]
    if not detour_ticks:
        drone.until = match.time + height / 2 + 1.25
    rect = Rect(pos.x - 0.2, pos.y - 0.2, pos.x + 0.2, pos.y + 0.2)
    wall = Wall(rect, 3, base=2 if ascending else 0, ceiling=None if ascending else 1.5, hp=100)
    match.effects.append(Effect("wall", enemy_id, 1, pos, drone.until, data={"hp": 100},
                                props={"barrier": wall}))
    if detour_ticks:
        for _ in range(detour_ticks):
            match.tick(dt, director.commands(dt))
        assert (drone.pos - pos).length() > 0.2
    else:
        match.tick(dt, director.commands(dt))
        assert drone.pos == pos and drone.props["flight_height"] == height
    pos, height = drone.pos, drone.props["flight_height"]
    inside_deck = match.world.deck_at(pos) is not None
    assert inside_deck == (detour_ticks == 8)
    if remaining is not None:
        drone.until = match.time + remaining
    match._damage_cover(wall, 100)
    if not inside_deck and reaches_goal:
        match.tick(dt, director.commands(dt))
        assert drone.pos == pos
        assert (drone.props["flight_height"] - height) * (1 if ascending else -1) > 0
    exited_deck = not inside_deck
    while match.time + dt < drone.until:
        match.tick(dt, director.commands(dt))
        exited_deck |= match.world.deck_at(drone.pos) is None
        if not exited_deck:
            assert drone.props["flight_height"] >= 1.4
    if not reaches_goal:
        assert match.world.deck_at(drone.pos) is match.world.deck_at(pos)
        assert drone.pos == pos
        return
    assert exited_deck
    assert (drone.pos - match.spike_pos).length() <= 0.4
    assert drone.props["flight_height"] == pytest.approx(goal_height, abs=0.05)


@pytest.mark.parametrize("flight_time", [3, 5])
def test_owl_drone_bot_replans_deck_transition_when_barrier_appears(flight_time):
    from gameplay.bots import BotDirector
    from gameplay.match import Effect

    match, pid, enemy_id = match_for("sova")
    bot = match.players[pid]
    bot.is_bot = True
    bot.charges["C"] = 1
    match.world.decks.append(Deck(Rect(8, 8, 12, 18), 2, 0))
    match.spike_pos, match.spike_ground = Vec(10, 15), 2
    director = BotDirector(match)
    director.sync()
    director.brains[pid].goal = match.spike_pos
    dt = 1 / 64
    match.tick(dt, {pid: Command(ability="C", facing=0)})
    [drone] = match.effects
    drone.until = drone.start + flight_time
    while drone.pos.x > 9:
        match.tick(dt, director.commands(dt))
        assert match.time < drone.start + 1
    assert drone.data["bot_deck_edge"].x < 8
    blocked_at = drone.pos
    rect = Rect(7, 9, 8.2, 17)
    match.effects.append(Effect("wall", enemy_id, 1, rect.center, drone.until,
                                props={"barrier": Wall(rect, 3)}))
    while match.time + dt < drone.until:
        match.tick(dt, director.commands(dt))
    if flight_time == 3:
        assert drone.pos == blocked_at
        assert drone.props["flight_height"] == 0
    else:
        assert (drone.pos - match.spike_pos).length() <= 0.4
        assert drone.props["flight_height"] == pytest.approx(2)
