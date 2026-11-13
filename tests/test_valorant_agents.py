"""Regression coverage for the playable VALORANT kits."""
from __future__ import annotations

import pytest

from gameplay.geometry import Rect, Vec
from gameplay.kit.engine import expand, resolve_target
from gameplay.match import Command, Match, PLAYABLE_AGENT_KEYS, playable_agents
from gameplay.net import apply_snapshot, command_from_json, merge_commands
from gameplay.world import Wall, WorldMap


def match_for(agent: str, world: WorldMap | None = None) -> tuple[Match, int, int]:
    world = world or WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(90, 90)]})
    match = Match(world, agent_roster=playable_agents())
    player = match.add_player("Player", 0, agent)
    enemy = match.add_player("Enemy", 1, "omen")
    match.start()
    match.phase, match.phase_until = "live", match.time + 100
    return match, player.pid, enemy.pid


def advance(match: Match, seconds: float) -> None:
    for _ in range(round(seconds * 64)):
        match.tick(1 / 64, {})


def test_every_configured_valorant_agent_is_selectable() -> None:
    assert tuple(playable_agents()) == PLAYABLE_AGENT_KEYS


def test_reyna_shares_soul_charges_and_devour_survives_a_snapshot() -> None:
    match, pid, enemy_id = match_for("reyna")
    player, enemy = match.players[pid], match.players[enemy_id]
    observer = match.add_player("Observer", 1, "omen")
    observer.pos = Vec(25, 25)
    match.phase = "buy"
    player.credits = 400
    assert match.buy(player, "Q") and player.charges["E"] == 2
    assert match.sell(player, "E") and player.charges["E"] == 1
    match.phase = "live"
    player.hp, player.equip_until = 75, 0
    enemy.pos, enemy.hp = Vec(10, 16), 1
    match.tick(1 / 64, {pid: Command(fire=True, facing=0, cursor_depth=6)})
    assert not enemy.alive
    assert not any(row["soul_orb"] for row in match.snapshot(observer.pid)["effects"])
    shadow = Match(match.world, agent_roster=playable_agents())
    apply_snapshot(shadow, match.snapshot(pid), pid)
    spec = shadow.agents["reyna"]["abilities"]["Q"]
    assert resolve_target(shadow, shadow.players[pid], spec) == enemy.pos
    match.tick(1 / 64, {pid: Command(ability="Q")})
    assert player.charges["E"] == 0
    advance(match, 3.1)
    assert (player.hp, player.overheal) == (100, 25)
    apply_snapshot(shadow, match.snapshot(pid), pid)
    assert shadow.players[pid].overheal == 25
    match._damage(observer, player, 10, "body", "classic")
    assert (player.hp, player.overheal) == (100, 15)
    advance(match, 10.1)
    assert player.overheal == 0


def test_reyna_empress_autoheals_and_grants_invisible_dismiss() -> None:
    match, pid, enemy_id = match_for("reyna")
    player, enemy = match.players[pid], match.players[enemy_id]
    observer = match.add_player("Observer", 1, "omen")
    observer.pos, observer.facing = Vec(10, 24), 180
    player.hp, player.ult_points, player.charges["E"] = 60, 7, 0
    match.tick(1 / 64, {pid: Command(ability="X")})
    assert player.ult_points == 0
    enemy.pos, enemy.hp = Vec(10, 16), 1
    player.equip_until = 0
    match.tick(1 / 64, {pid: Command(fire=True, facing=0, cursor_depth=6)})
    match.tick(1 / 64, {pid: Command(ability="E")})
    assert player.status["dismiss"] > match.time and player.charges["E"] == 0
    assert not match.can_see(observer, player)
    hp = player.hp
    match._damage(observer, player, 100, "head", "classic")
    assert player.hp == hp
    match.tick(1 / 64, {})
    match.tick(1 / 64, {pid: Command(ability="E")})
    assert "dismiss" not in player.status and match.can_see(observer, player)
    advance(match, 2.6)
    assert (player.hp, player.overheal) == (100, 10)
    advance(match, 10.1)
    assert player.overheal == 10


def test_reyna_empress_does_not_autoheal_from_a_kill_while_suppressed() -> None:
    from gameplay.abilities import apply_status

    match, pid, enemy_id = match_for("reyna")
    player, enemy = match.players[pid], match.players[enemy_id]
    survivor = match.add_player("Survivor", enemy.team, "omen")
    survivor.pos = Vec(30, 30)
    player.hp, player.ult_points = 60, 7
    match.tick(1 / 64, {pid: Command(ability="X")})
    apply_status(match, player, "suppress", 1.0)
    enemy.pos, enemy.hp = Vec(10, 16), 1
    player.equip_until = 0
    match.tick(1 / 64, {pid: Command(fire=True, facing=0, cursor_depth=6)})
    assert not enemy.alive
    advance(match, 2.7)
    assert (player.hp, player.overheal) == (60, 0)


def test_reyna_leer_crosses_walls_and_nearsights_only_visible_eye() -> None:
    match, pid, enemy_id = match_for("reyna")
    player, enemy = match.players[pid], match.players[enemy_id]
    match.world.walls.append(Wall(Rect(6, 12, 14, 13), 3))
    player.charges["C"] = 1
    enemy.pos, enemy.facing = Vec(10, 24), 180
    match.tick(1 / 64, {pid: Command(ability="C", facing=0, cursor_depth=6)})
    advance(match, 1.0)
    eye = match.effects[0]
    assert eye.pos == Vec(10, 20) and eye.data["hp"] == 60
    assert enemy.status["leer"] > match.time and "leer" not in player.status
    enemy.facing = 110
    advance(match, 0.2)
    assert enemy.status.get("leer", 0) <= match.time
    enemy.pos, enemy.facing = Vec(10, 10), 0
    advance(match, 0.6)
    assert enemy.status.get("leer", 0) <= match.time


def test_breach_wall_charges_require_a_wall_and_trigger_on_the_far_side() -> None:
    match, pid, enemy_id = match_for("breach")
    player, enemy = match.players[pid], match.players[enemy_id]
    player.charges.update(C=1, Q=2)
    enemy.pos, enemy.facing = Vec(10, 16), 180
    match.tick(1 / 64, {pid: Command(ability="Q", facing=0)})
    assert player.charges["Q"] == 2 and not match.effects
    match.world.walls.append(Wall(Rect(6, 13, 14, 14), 3))
    advance(match, 0.1)
    match.tick(1 / 64, {pid: Command(ability="Q", facing=0)})
    assert player.charges["Q"] == 1 and match.effects[0].pos.y > 14
    advance(match, 0.8)
    assert player.blind_until <= match.time < enemy.blind_until

    match.tick(1 / 64, {pid: Command(ability="C", facing=0)})
    advance(match, 2.4)
    assert enemy.hp == 20 and player.hp == 100
    advance(match, 0.6)
    assert not enemy.alive


@pytest.mark.parametrize(("facing", "duration"), [(180, 2.25), (225, 1.25), (0, 0.25)])
def test_breach_flashpoint_uses_the_targets_facing_at_detonation(facing: int, duration: float) -> None:
    match, pid, enemy_id = match_for("breach")
    player, enemy = match.players[pid], match.players[enemy_id]
    player.charges["Q"] = 2
    match.world.walls.append(Wall(Rect(6, 13, 14, 14), 3))
    enemy.pos, enemy.facing = Vec(10, 19), 180
    match.tick(1 / 64, {pid: Command(ability="Q", facing=0)})
    assert player.charges["Q"] == 1
    [flash] = match.effects
    advance(match, 0.25)
    assert enemy.blind_until <= match.time
    while match.time < flash.until:
        match.tick(1 / 64, {enemy_id: Command(facing=facing)})
    assert enemy.blind_until - match.time == pytest.approx(duration)
    assert player.blind_until <= match.time


def test_breach_seismic_abilities_delay_and_rolling_thunder_knocks_once() -> None:
    match, pid, enemy_id = match_for("breach")
    player, enemy = match.players[pid], match.players[enemy_id]
    enemy.pos = Vec(10, 26)
    match.world.walls.append(Wall(Rect(6, 13, 14, 14), 3))
    match.tick(1 / 64, {pid: Command(ability="E", facing=0, cursor_depth=22)})
    advance(match, 0.9)
    assert enemy.status.get("concuss", 0) <= match.time
    advance(match, 0.3)
    assert enemy.status["concuss"] > match.time

    player.ult_points = 8
    enemy.pos = Vec(10, 20)
    match.tick(1 / 64, {pid: Command(ability="X", facing=0)})
    assert player.ult_points == 0
    advance(match, 2.8)
    assert enemy.pos == Vec(10, 27)
    assert enemy.status["concuss"] > match.time


@pytest.mark.parametrize(("depth", "inside", "outside"), [(0, 15.9, 16.1), (100, 63.9, 64.1)])
def test_breach_fault_line_uses_the_charged_length_after_the_spawn_offset(
    depth: float, inside: float, outside: float
) -> None:
    match, pid, enemy_id = match_for("breach")
    player, enemy = match.players[pid], match.players[enemy_id]
    enemy.pos = player.pos + Vec(0, inside)
    beyond = match.add_player("Beyond", enemy.team, "omen")
    beyond.pos = player.pos + Vec(2, outside)
    match.tick(1 / 64, {pid: Command(ability="E", facing=0, cursor_depth=depth)})
    advance(match, 1.2)
    assert enemy.status["concuss"] > match.time
    assert beyond.status.get("concuss", 0) <= match.time


def test_breach_rolling_thunder_ends_after_eight_four_meter_sections() -> None:
    match, pid, enemy_id = match_for("breach")
    player, enemy = match.players[pid], match.players[enemy_id]
    enemy.pos = player.pos + Vec(0, 39.9)
    beyond = match.add_player("Beyond", enemy.team, "omen")
    beyond.pos = player.pos + Vec(5, 40.1)
    player.ult_points = 8
    match.tick(1 / 64, {pid: Command(ability="X", facing=0)})
    assert len(match.effects) == 8
    advance(match, 2.9)
    assert enemy.status.get("concuss", 0) <= match.time
    advance(match, 0.2)
    assert enemy.status["concuss"] > match.time
    assert beyond.status.get("concuss", 0) <= match.time

def test_breach_aftershock_covers_ten_meters_from_the_far_face() -> None:
    match, pid, enemy_id = match_for("breach")
    player, enemy = match.players[pid], match.players[enemy_id]
    match.world.walls.append(Wall(Rect(6, 13, 14, 14), 3))
    enemy.pos = Vec(12.95, 23.9)
    beyond = match.add_player("Beyond", enemy.team, "omen")
    beyond.pos = Vec(10, 24.2)
    player.charges["C"] = 1
    match.tick(1 / 64, {pid: Command(ability="C", facing=0)})
    advance(match, 2.1)
    assert enemy.hp == 100
    advance(match, 0.2)
    assert enemy.hp == 20 and beyond.hp == 100
    advance(match, 0.6)
    assert not enemy.alive and beyond.hp == 100


def test_sky_smoke_only_spends_charges_on_valid_confirmation() -> None:
    match, pid, _ = match_for("brimstone")
    player = match.players[pid]
    player.charges["E"] = 3
    for points in ([], [(20, 20), (90, 90)]):
        match.tick(1 / 64, {pid: Command(ability="E", points=points)})
        assert player.charges["E"] == 3 and not match.effects
        match.tick(1 / 64, {})
    chosen = [(20, 20), (30, 20), (40, 20)]
    match.tick(1 / 64, {pid: Command(ability="E", points=chosen + [(50, 20)])})
    assert player.charges["E"] == 0
    assert [e.pos for e in match.effects] == [Vec(*point) for point in chosen]
    radius = expand(match.agents["brimstone"]["abilities"]["E"])["place"]["radius"]
    assert radius == 4.15
    assert all(e.kind == "smoke" and e.radius == radius and e.start - match.time == pytest.approx(1)
               for e in match.effects)
    client = Match(match.world)
    apply_snapshot(client, match.snapshot(pid), pid)
    assert client.effects[0].props["sprite"] == "brimstone_sky_smoke"


@pytest.mark.parametrize("slot, field", [("C", "brimstone_stim_field"), ("Q", "brimstone_incendiary_burning")])
def test_brimstone_throw_lands_at_the_preview_even_against_a_wall(slot: str, field: str) -> None:
    match, pid, _ = match_for("brimstone")
    player = match.players[pid]
    player.charges[slot] = 1
    match.world.walls.append(Wall(Rect(9, 14, 11, 15), 3))
    player.facing, player.cursor_depth = 0, 22
    ab = match.agents[player.agent]["abilities"][slot]
    assert ab["landing_preview"]
    landing = resolve_target(match, player, expand(ab))
    assert landing == Vec(10, 13.7)
    match.tick(1 / 64, {pid: Command(ability=slot, facing=0, cursor_depth=22)})
    assert match.effects[0].pos == landing and match.effects[0].a == player.pos
    advance(match, 1)
    assert any(e.pos == landing and e.props["sprite"] == field for e in match.effects)


def test_ability_command_keeps_its_cursor_when_the_host_merges_input() -> None:
    cast = command_from_json({"ability": "E", "points": [[20, 20], [1], "12", [float("inf"), 1]],
                              "facing": 25, "cursor_depth": 12})
    cmd = merge_commands(cast, Command(facing=90, cursor_depth=3))
    assert (cmd.ability, cmd.facing, cmd.cursor_depth, cmd.points) == ("E", 25, 12, [(20, 20)])


@pytest.mark.parametrize("lethal", [False, True])
def test_run_it_back_returns_with_health_and_starting_armor(lethal: bool) -> None:
    match, pid, enemy = match_for("phoenix")
    player = match.players[pid]
    start = player.pos
    player.armor, player.ult_points = 25, 7
    match.tick(1 / 64, {pid: Command(ability="X")})
    player.pos, player.hp, player.armor = Vec(24, 15), 50, 0
    if lethal:
        match._damage(match.players[enemy], player, 100, "body", "classic")
    else:
        advance(match, 10.1)
    assert player.alive and player.deaths == 0
    assert (player.pos, player.hp, player.armor, player.ult_points) == (start, 100, 25, 0)


@pytest.mark.parametrize("agent, slot, active", [("cypher", "Q", "smoke"), ("killjoy", "C", "zone")])
def test_remote_utility_waits_for_its_owner(agent: str, slot: str, active: str) -> None:
    match, pid, _ = match_for(agent)
    player = match.players[pid]
    player.charges[slot] = 1
    match.tick(1 / 64, {pid: Command(ability=slot, facing=0, cursor_depth=10)})
    advance(match, 2)
    [device] = match.effects
    assert device.props["manual"] and device.kind == "alarm"
    match.tick(1 / 64, {pid: Command(facing=0, cursor_depth=8, interact=True)})
    assert [e.kind for e in match.effects] == [active]


def test_tailwind_and_blade_storm_have_separate_equip_and_fire_steps() -> None:
    match, pid, _ = match_for("jett")
    player = match.players[pid]
    match.tick(1 / 64, {pid: Command(ability="E")})
    assert player.charges["E"] == 0 and not player.dash_until
    advance(match, 1.1)
    match.tick(1 / 64, {pid: Command(ability="E")})
    assert player.dash_until > match.time and not player.dash_armed_until
    player.ult_points = 8
    match.tick(1 / 64, {pid: Command(ability="X")})
    assert player.blades_equipped and player.blade_count == 5 and player.ult_points == 0
    advance(match, 0.5)
    match.tick(1 / 64, {pid: Command(fire=True)})
    assert player.blade_count == 4
    advance(match, 0.4)
    events = match.tick(1 / 64, {pid: Command(alt_fire=True)})
    assert sum(e.kind == "shot" for e in events) == 4
    assert not player.blades_equipped and player.blade_count == 0


def test_tactical_map_marks_three_points_before_confirming() -> None:
    from client.game import Game
    from test_client import args

    game = Game(args(agent="brimstone"))
    game.match.start()
    me = game.match.players[game.me]
    me.charges["E"] = 3
    rect, scale = game.tactical_layout()
    x = round(rect.left + me.pos.x * scale)
    y = round(rect.top + (game.match.world.height - me.pos.y) * scale)
    game.set_aim("E")
    game.aim_click(me, Command(), 3, (x, y))
    assert game.aiming == "E"
    for dx in (0, 15, 30, 45):
        mark = Command()
        game.aim_click(me, mark, 1, (x + dx, y))
        assert mark.ability is None and not game.match.effects
    assert len(game.multi_points) == 3
    game.draw()
    confirm = Command()
    game.aim_click(me, confirm, 3, (x, y))
    assert confirm.ability == "E" and len(confirm.points) == 3 and game.aiming is None
    game.match.tick(1 / 64, {me.pid: confirm})
    assert me.charges["E"] == 0 and len(game.match.effects) == 3
    game.draw()


def test_barrier_has_independently_destructible_solid_blocks() -> None:
    match, pid, _ = match_for("sage")
    player = match.players[pid]
    player.charges["C"] = 1
    match.tick(1 / 64, {pid: Command(ability="C", facing=0, cursor_depth=5)})
    walls = match.ability_walls()
    assert len(walls) == 4
    a, b = Vec(10, 13), Vec(10, 17)
    assert not match._line_clear(a, b, 0)
    client = Match(match.world)
    apply_snapshot(client, match.snapshot(pid), pid)
    assert not client._line_clear(a, b, 0)
    match._damage_cover(walls[0], walls[0].hp)
    assert len(match.ability_walls()) == 3
    assert player.charges["C"] == 0


def test_hunters_fury_pays_once_and_can_reaim_each_beam() -> None:
    match, pid, _ = match_for("sova")
    player = match.players[pid]
    player.ult_points = 8
    for i, direction in enumerate((0, 90, 180)):
        match.tick(1 / 64, {pid: Command(ability="X", facing=direction)})
        assert player.ult_points == 0 and player.repeat_shots == 2 - i
        [beam] = match.effects
        assert beam.a == player.pos and (beam.b - beam.a).length() == pytest.approx(45)
        advance(match, 1.0)
    assert not match.effects


def test_hunters_fury_reveals_for_one_second_through_cover() -> None:
    match, pid, enemy_id = match_for("sova")
    match.players[pid].ult_points = 8
    enemy = match.players[enemy_id]
    enemy.pos = Vec(10, 20)
    health = enemy.hp
    match.world.walls.append(Wall(Rect(8, 14, 12, 15), 3))
    dt = 1 / 64
    match.tick(dt, {pid: Command(ability="X", facing=0)})
    [beam] = match.effects
    while match.time + dt < beam.start:
        match.tick(dt, {})
    assert enemy.hp == health and enemy.revealed_until <= match.time
    match.tick(dt, {})
    assert enemy.hp == health - 80
    assert enemy.revealed_until == pytest.approx(match.time + 1)
    advance(match, 1 - dt)
    assert enemy.revealed_until > match.time
    match.tick(dt, {})
    assert enemy.revealed_until <= match.time


@pytest.mark.parametrize(("offset", "hit"), [(-0.1, False), (0, False), (0.1, True)])
def test_hunters_fury_hits_only_in_front_of_sova(offset, hit) -> None:
    match, pid, enemy_id = match_for("sova")
    sova, enemy = match.players[pid], match.players[enemy_id]
    sova.ult_points = 8
    enemy.dummy = True  # Keep the target at the beam boundary through the windup.
    enemy.pos = sova.pos + Vec(0, offset)
    health = enemy.hp
    dt = 1 / 64
    match.tick(dt, {pid: Command(ability="X", facing=0)})
    [beam] = match.effects
    while match.time < beam.start:
        match.tick(dt, {})
    assert enemy.hp == health - (80 if hit else 0)
    assert (enemy.revealed_until > match.time) is hit


@pytest.mark.parametrize("before_expiry", [True, False])
def test_hunters_fury_recast_window_is_six_seconds(before_expiry) -> None:
    match, pid, _ = match_for("sova")
    sova = match.players[pid]
    sova.ult_points = 8
    dt = 1 / 64
    match.tick(dt, {pid: Command(ability="X", facing=0)})
    assert sova.repeat_until == pytest.approx(match.time + 6)
    advance(match, 6 - (2 if before_expiry else 1) * dt)
    match.tick(dt, {pid: Command(ability="X", facing=90)})
    assert bool(match.effects) is before_expiry
    assert sova.ult_points == 0


@pytest.mark.parametrize("use_all_shots", [True, False])
def test_hunters_fury_end_requires_weapon_recovery(use_all_shots) -> None:
    match, pid, _ = match_for("sova")
    sova = match.players[pid]
    sova.ult_points = 8
    dt = 1 / 64
    match.tick(dt, {pid: Command(ability="X", facing=0)})
    if use_all_shots:
        advance(match, 1)
        match.tick(dt, {pid: Command(ability="X", facing=0)})
        advance(match, 1)
    else:
        advance(match, 6 - dt)
    weapon = sova.weapon
    assert weapon is not None
    ammo = weapon.mag
    match.tick(dt, {pid: Command(ability="X" if use_all_shots else None, facing=0, fire=True)})
    assert not sova.repeat_shots and weapon.mag == ammo
    assert sova.equip_until == pytest.approx(match.time + 1)
    advance(match, 1 - 2 * dt)
    match.tick(dt, {pid: Command(fire=True)})
    assert weapon.mag == ammo
    match.tick(dt, {})
    match.tick(dt, {pid: Command(fire=True)})
    assert weapon.mag == ammo - 1


def test_hunters_fury_blocks_weapon_fire_between_beams() -> None:
    match, pid, _ = match_for("sova")
    sova = match.players[pid]
    sova.ult_points = 8
    weapon = sova.weapon
    assert weapon is not None
    ammo = weapon.mag
    dt = 1 / 64
    match.tick(dt, {pid: Command(ability="X", facing=0, fire=True)})
    assert sova.repeat_shots == 2 and weapon.mag == ammo
    advance(match, 1)
    match.tick(dt, {pid: Command(fire=True)})
    assert weapon.mag == ammo
    match.tick(dt, {pid: Command(ability="X", facing=0, fire=True)})
    assert sova.repeat_shots == 1 and weapon.mag == ammo


def test_hunters_fury_weapon_switch_discards_remaining_shots() -> None:
    match, pid, _ = match_for("sova")
    sova = match.players[pid]
    sova.ult_points = 8
    dt = 1 / 64
    match.tick(dt, {pid: Command(ability="X", facing=0)})
    advance(match, 1)
    sidearm = sova.weapons["sidearm"]
    ammo = sidearm.mag
    match.tick(dt, {pid: Command(slot="sidearm", ability="X", fire=True)})
    assert sova.slot == "sidearm" and sova.repeat_shots == 0
    assert not match.effects and sidearm.mag == ammo
    assert sova.equip_until == pytest.approx(match.time + 1)
    advance(match, 1 - 2 * dt)
    match.tick(dt, {pid: Command(fire=True)})
    assert sidearm.mag == ammo
    match.tick(dt, {})
    match.tick(dt, {pid: Command(fire=True)})
    assert sidearm.mag == ammo - 1


def test_omen_teleport_rejects_a_wall_and_arrives_as_a_shade() -> None:
    match, pid, _ = match_for("omen")
    player = match.players[pid]
    player.ult_points = 7
    start = player.pos
    match.world.walls.append(Wall(Rect(20, 20, 25, 25), 3))
    match.tick(1 / 64, {pid: Command(ability="X", points=[(21, 21)])})
    assert player.ult_points == 7 and player.pos == start
    advance(match, 0.1)
    match.tick(1 / 64, {pid: Command(ability="X", points=[(30, 20)])})
    assert player.ult_points == 0 and player.pos == start
    advance(match, 95 / 64)
    assert player.pos == start
    advance(match, 1 / 64)
    assert player.pos == Vec(30, 20)
    assert player.status["omen_shade"] > match.time
    advance(match, 2.5)
    assert "omen_shade" not in player.status
    weapon = player.weapon
    assert weapon is not None
    assert player.equip_until - match.time == pytest.approx(match.weapons[weapon.key].equip)
    magazine = weapon.mag
    match.tick(1 / 64, {pid: Command(fire=True)})
    assert weapon.mag == magazine
    advance(match, match.weapons[weapon.key].equip)
    match.tick(1 / 64, {pid: Command(fire=True)})
    assert weapon.mag == magazine - 1


def test_shrouded_step_separates_windup_arrival_and_weapon_recovery() -> None:
    match, pid, _ = match_for("omen")
    player = match.players[pid]
    player.charges["C"] = 1
    player.equip_until = 0
    weapon = player.weapon
    assert weapon is not None
    magazine = weapon.mag
    origin, destination = player.pos, player.pos + Vec(0, 10)
    cast = match.tick(1 / 64, {pid: Command(ability="C", facing=0, cursor_depth=10)})
    cast_at = match.time
    [departure] = [e for e in cast if e.kind == "sound_fx"]
    assert departure.t == cast_at and departure.data["pos"] == (origin.x, origin.y)
    advance(match, 44 / 64)
    assert player.pos == origin
    assert all(e.props.get("sprite") != "omen_shrouded_step_arrival" for e in match.effects)

    arrival_tick = match.tick(1 / 64, {pid: Command(fire=True)})
    landed_at = match.time
    [arrival] = [e for e in arrival_tick if e.kind == "sound_fx"]
    assert arrival.t == landed_at and arrival.data["pos"] == (destination.x, destination.y)
    assert landed_at - cast_at == pytest.approx(0.7, abs=1 / 64)
    assert player.pos == destination and weapon.mag == magazine
    [animation] = [e for e in match.effects if e.props.get("sprite") == "omen_shrouded_step_arrival"]
    assert animation.pos == destination and animation.start == landed_at
    assert animation.until - landed_at == pytest.approx(0.5)

    advance(match, 31 / 64)
    assert animation in match.effects
    advance(match, 1 / 64)
    assert animation not in match.effects
    advance(match, 11 / 64)
    match.tick(1 / 64, {pid: Command(fire=True)})
    assert weapon.mag == magazine
    advance(match, 1 / 64)
    match.tick(1 / 64, {pid: Command(fire=True)})
    assert weapon.mag == magazine - 1


def test_paranoia_travels_through_walls_and_hits_allies() -> None:
    from gameplay.abilities import has

    match, pid, enemy_id = match_for("omen")
    player, enemy = match.players[pid], match.players[enemy_id]
    ally = match.add_player("Ally", player.team, "sage")
    ally.pos, enemy.pos = Vec(10, 21), Vec(10, 32)
    match.world.walls.append(Wall(Rect(8, 24, 12, 25), 3))
    player.charges["Q"] = 1
    match.tick(1 / 64, {pid: Command(ability="Q", facing=0)})
    assert not has(match, ally, "paranoia") and not has(match, enemy, "paranoia")
    assert match.paranoia_warning(ally) and match.paranoia_warning(enemy)
    assert not match.paranoia_warning(player)
    guest = Match(match.world, agent_roster=playable_agents())
    apply_snapshot(guest, match.snapshot(enemy_id), enemy_id)
    assert guest.paranoia_warning(guest.players[enemy_id])
    advance(match, 0.5)
    assert has(match, ally, "paranoia") and not has(match, enemy, "paranoia")
    assert not match.paranoia_warning(ally) and match.paranoia_warning(enemy)
    enemy.pos = Vec(15, 32)
    assert not match.paranoia_warning(enemy)
    enemy.pos = Vec(10, 32)
    advance(match, 0.45)
    assert has(match, enemy, "paranoia") and not has(match, player, "paranoia")
    apply_snapshot(guest, match.snapshot(enemy_id), enemy_id)
    assert not guest.paranoia_warning(guest.players[enemy_id])


@pytest.mark.parametrize(("agent", "sprite"), [("cypher", "cypher_spycam"), ("killjoy", "killjoy_turret")])
def test_paranoia_temporarily_limits_device_vision(agent: str, sprite: str) -> None:
    match, pid, _ = match_for("omen")
    omen = match.players[pid]
    sentinel = match.add_player("Sentinel", 1, agent)
    sentinel.charges["E"] = 1
    target = match.add_player("Target", omen.team, "sage")
    sentinel.pos, target.pos = Vec(10, 17), Vec(10, 35)
    match.tick(1 / 64, {sentinel.pid: Command(ability="E", facing=0, cursor_depth=7)})
    [device] = [e for e in match.effects if e.props.get("sprite") == sprite]
    omen.charges["Q"] = 1
    match.tick(1 / 64, {pid: Command(ability="Q", facing=0)})
    omen.pos = Vec(40, 10)
    advance(match, 0.6)
    expires = device.data["nearsighted_until"]
    assert expires > match.time
    assert device.data["nearsighted_range"] == 7.5
    from gameplay.kit.engine import _ctx_for
    from gameplay.kit.builtins import select

    trigger = device.props["triggers"][0]
    assert target not in select(_ctx_for(match, device, 0), trigger)
    target.pos = device.pos + Vec(0, 7)
    assert target in select(_ctx_for(match, device, 0), trigger)
    target.pos = device.pos + Vec(0, 9)
    advance(match, 2)
    assert device.data["nearsighted_until"] == expires
    assert target in select(_ctx_for(match, device, 0), trigger)


@pytest.mark.parametrize("distance", [7.25, 7.75])
def test_paranoia_limits_owl_drone_darts_until_it_wears_off(distance: float) -> None:
    match, pid, _ = match_for("omen")
    omen = match.players[pid]
    sova = match.add_player("Sova", 1, "sova")
    target = match.add_player("Target", omen.team, "sage")
    sova.pos, target.pos = Vec(10, 20), Vec(40, 40)
    sova.charges["C"] = omen.charges["Q"] = 1
    match.tick(1 / 64, {sova.pid: Command(ability="C", facing=0), pid: Command(ability="Q", facing=0)})
    [drone] = [e for e in match.effects if e.props.get("sprite") == "sova_owl_drone"]
    omen.pos = Vec(40, 10)
    advance(match, 88 / 64)
    assert drone.data.get("nearsighted_until", 0) > match.time
    target.pos = drone.pos + Vec(distance, 0)
    match.tick(1 / 64, {sova.pid: Command(fire=True, facing=90)})
    assert (target.status.get("owl_drone_spotted", 0) > match.time) == (distance < 7.5)

    target.pos = Vec(40, 40)
    advance(match, 5)
    assert drone.data["nearsighted_until"] <= match.time
    target.pos = drone.pos + Vec(7.75, 0)
    match.tick(1 / 64, {sova.pid: Command(fire=True, facing=90)})
    assert target.status["owl_drone_spotted"] == pytest.approx(match.time + 4)


def test_owl_drone_dart_marks_only_on_fire_and_reveals_twice() -> None:
    match, pid, enemy_id = match_for("sova")
    sova, enemy = match.players[pid], match.players[enemy_id]
    enemy.pos = Vec(10, 15)
    sova.charges["C"] = 1
    match.tick(1 / 64, {pid: Command(ability="C", facing=0)})
    advance(match, 1.5)
    assert "owl_drone_spotted" not in enemy.status
    match.tick(1 / 64, {pid: Command(fire=True, facing=0)})
    impact = match.time
    assert enemy.status["owl_drone_spotted"] == impact + 4
    advance(match, 1)
    match.tick(1 / 64, {pid: Command(fire=True, facing=0)})
    assert enemy.status["owl_drone_spotted"] == impact + 4
    assert enemy.revealed_until <= match.time
    advance(match, 0.65)
    assert enemy.revealed_until > match.time
    advance(match, 1)
    assert enemy.revealed_until <= match.time
    advance(match, 0.8)
    assert enemy.revealed_until > match.time
    advance(match, 0.7)
    assert enemy.revealed_until <= match.time


@pytest.mark.parametrize("lethal", [False, True])
def test_owl_drone_ends_when_sova_takes_damage(lethal: bool) -> None:
    match, pid, enemy_id = match_for("sova")
    sova, enemy = match.players[pid], match.players[enemy_id]
    enemy.pos, enemy.equip_until = Vec(10, 14), 0
    sova.charges["C"] = 1
    if lethal:
        sova.hp = 1
    match.tick(1 / 64, {pid: Command(ability="C")})
    [drone] = match.effects
    for _ in range(24):
        match.tick(1 / 64, {pid: Command(move_y=1, facing=90)})
    assert drone.pos.x > sova.pos.x
    hp = sova.hp
    match.tick(1 / 64, {enemy_id: Command(fire=True, facing=180, cursor_depth=4)})
    assert sova.hp < hp and sova.alive != lethal
    assert drone.props.get("ended") and sova.channel_until == 0
    assert sova.charges["C"] == 0
    if not lethal:
        assert sova.equip_until - match.time == pytest.approx(0.7)


def test_sova_steers_owl_drone_and_can_return_to_his_body() -> None:
    match, pid, _ = match_for("sova")
    sova = match.players[pid]
    origin = sova.pos
    sova.charges["C"] = 1
    match.tick(1 / 64, {pid: Command(ability="C", facing=0)})
    [drone] = match.effects
    start = drone.pos
    assert drone.start - match.time == pytest.approx(0.25)
    assert drone.until - drone.start == pytest.approx(7)
    assert sova.channel_until == drone.until
    for _ in range(15):
        match.tick(1 / 64, {pid: Command(move_y=1, fire=True, facing=90)})
    assert drone.pos == start
    assert "dart_ready" not in drone.data
    advance(match, 1 / 64)
    for _ in range(16):
        match.tick(1 / 64, {pid: Command(move_y=1, facing=90)})
    assert drone.pos.x == pytest.approx(start.x + 1)
    assert sova.pos == origin and sova.channel_until > match.time
    match.tick(1 / 64, {pid: Command(ability="C")})
    assert drone not in match.effects and sova.channel_until == 0
    assert sova.equip_until - match.time == pytest.approx(0.7)
    weapon = sova.weapon
    assert weapon is not None
    magazine = weapon.mag
    advance(match, 43 / 64)
    match.tick(1 / 64, {pid: Command(fire=True)})
    assert weapon.mag == magazine
    advance(match, 1 / 64)
    match.tick(1 / 64, {pid: Command(fire=True)})
    assert weapon.mag == magazine - 1


@pytest.mark.parametrize(("wall_y", "launch_y"), [(None, 11.25), (11, 10.68), (10.55, None)])
def test_owl_drone_launches_ahead_and_stays_on_near_side_of_wall(wall_y, launch_y) -> None:
    match, pid, _ = match_for("sova")
    sova = match.players[pid]
    sova.charges["C"] = 1
    if wall_y is not None:
        match.world.walls.append(Wall(Rect(8, wall_y, 12, wall_y + 0.1), 3))
    match.tick(1 / 64, {pid: Command(ability="C", facing=0)})
    if launch_y is None:
        assert not match.effects and sova.charges["C"] == 1 and sova.channel_until == 0
    else:
        [drone] = match.effects
        assert drone.pos.y == pytest.approx(launch_y)
        assert drone.pos.x == pytest.approx(10)
        assert sova.charges["C"] == 0


def test_owl_drone_climbs_over_low_walls_but_stays_below_a_deck() -> None:
    from gameplay.world import Deck

    match, pid, _ = match_for("sova")
    sova = match.players[pid]
    sova.charges["C"] = 1
    match.world.walls.append(Wall(Rect(8, 13, 12, 13.2), 3, height=1))
    match.world.decks.append(Deck(Rect(8, 9, 12, 18), 3, 0))
    match.tick(1 / 64, {pid: Command(ability="C", facing=0)})
    [drone] = match.effects
    advance(match, 0.25)
    for _ in range(48):
        match.tick(1 / 64, {pid: Command(move_y=1, facing=0)})
    assert drone.pos.y < 13
    for _ in range(64):
        match.tick(1 / 64, {pid: Command(move_y=1, jump=True, facing=0)})
    assert drone.pos.y > 13.2
    for _ in range(32):
        match.tick(1 / 64, {pid: Command(jump=True)})
    assert drone.props["flight_height"] == pytest.approx(2.48)
    shadow = Match(match.world, agent_roster=playable_agents())
    apply_snapshot(shadow, match.snapshot(pid), pid)
    assert shadow.effects[0].props["flight_height"] == pytest.approx(2.48)
    for _ in range(32):
        match.tick(1 / 64, {pid: Command(crouch=True)})
    assert drone.props["flight_height"] == pytest.approx(1.48)


def test_owl_drone_expiry_starts_fixed_weapon_recovery() -> None:
    match, pid, _ = match_for("sova")
    sova = match.players[pid]
    sova.charges["C"] = 1
    match.tick(1 / 64, {pid: Command(ability="C")})
    [drone] = match.effects
    advance(match, 7.25)
    assert drone not in match.effects and sova.channel_until == 0
    assert sova.equip_until - match.time == pytest.approx(0.7)


def test_paranoia_uses_pc_radius_without_hitting_players_beside_omen() -> None:
    from gameplay.abilities import has

    match, pid, enemy_id = match_for("omen")
    player, enemy = match.players[pid], match.players[enemy_id]
    enemy.pos = Vec(14.29, 22)
    outside = match.add_player("Outside", enemy.team, "sage")
    outside.pos = Vec(5.69, 22)
    adjacent = match.add_player("Adjacent", player.team, "sage")
    adjacent.pos = Vec(11, 10)
    player.charges["Q"] = 1
    match.tick(1 / 64, {pid: Command(ability="Q", facing=0)})
    advance(match, 1.25)
    assert has(match, enemy, "paranoia")
    assert not has(match, outside, "paranoia") and not has(match, adjacent, "paranoia")


def test_paranoia_limits_sight_and_deafens_for_two_seconds_from_impact() -> None:
    from gameplay.abilities import flag

    match, pid, enemy_id = match_for("omen")
    player, enemy = match.players[pid], match.players[enemy_id]
    enemy.pos, enemy.facing = Vec(10, 17), 180
    player.charges["Q"] = 1
    match.tick(1 / 64, {pid: Command(ability="Q", facing=0)})
    while not flag(match, enemy, "deaf") and match.time < 1.25:
        advance(match, 1 / 64)
    assert flag(match, enemy, "deaf")
    player.pos = Vec(10, 9.5)
    assert match.can_see(enemy, player)  # 7.5 m
    player.pos = Vec(10, 9.4)
    assert not match.can_see(enemy, player)  # 7.6 m

    advance(match, 127 / 64)
    assert flag(match, enemy, "deaf") and not match.can_see(enemy, player)
    advance(match, 1 / 64)
    assert not flag(match, enemy, "deaf") and match.can_see(enemy, player)


def test_omen_paranoia_delays_return_to_weapon_for_seven_tenths() -> None:
    match, pid, _ = match_for("omen")
    player = match.players[pid]
    player.charges["Q"] = 1
    player.equip_until = 0
    weapon = player.weapon
    assert weapon is not None
    magazine = weapon.mag
    match.tick(1 / 64, {pid: Command(ability="Q", fire=True)})
    assert player.charges["Q"] == 0 and weapon.mag == magazine

    advance(match, 43 / 64)
    match.tick(1 / 64, {pid: Command(fire=True)})
    assert weapon.mag == magazine
    advance(match, 1 / 64)
    match.tick(1 / 64, {pid: Command(fire=True)})
    assert weapon.mag == magazine - 1


def test_barrier_fortifies_without_healing_earlier_damage() -> None:
    match, pid, _ = match_for("sage")
    player = match.players[pid]
    player.charges["C"] = 1
    match.tick(1 / 64, {pid: Command(ability="C", facing=0, cursor_depth=12)})
    assert len(match.effects) == 4
    first = match.effects[0]
    assert first.data["hp"] == 400
    match._damage_cover(first.props["barrier"], 100)
    advance(match, 2.0)
    assert first.data["hp"] == 500 and match.effects[1].data["hp"] == 600


def test_destroying_spycam_starts_45_second_cooldown() -> None:
    from gameplay.geometry import heading

    match, pid, enemy_id = match_for("cypher")
    player, enemy = match.players[pid], match.players[enemy_id]
    match.tick(1 / 64, {pid: Command(ability="E", facing=0, cursor_depth=6)})
    cam = match.effects[0]
    enemy.pos = Vec(10, 20)
    enemy.cursor_depth = 4
    match._trace(enemy, match.weapons["classic"], heading(180), heading(180))
    assert cam.props["ended"] and player.charges["E"] == 0
    ready = player.ability_ready_at["E"]
    assert ready - match.time == pytest.approx(45)
    match.time = ready - 0.02
    match.tick(0.01, {})
    assert player.charges["E"] == 0
    match.tick(0.02, {})
    assert player.charges["E"] == 1


def test_buy_multiple_signature_charges_and_sell_only_unused_charges() -> None:
    match, pid, _ = match_for("brimstone")
    player = match.players[pid]
    match.phase = "buy"
    credits = player.credits
    assert match.buy(player, "E") and match.buy(player, "E")
    assert player.charges["E"] == 3 and player.credits == credits - 200
    match.tick(1 / 64, {pid: Command(ability="E", points=[(20, 20)])})
    assert match.buy(player, "sell:E")
    assert player.charges["E"] == 1 and player.credits == credits - 100
    assert not match.buy(player, "sell:E")


def test_neural_theft_marks_positions_twice_without_live_reveal() -> None:
    match, pid, enemy_id = match_for("cypher")
    player, enemy = match.players[pid], match.players[enemy_id]
    corpse = match.add_player("Corpse", enemy.team, "omen")
    corpse.alive, corpse.pos = False, Vec(10, 18)
    player.ult_points = 7
    match.tick(1 / 64, {pid: Command(ability="X", facing=0, cursor_depth=8)})
    advance(match, 2)
    first, = [effect for effect in match.effects if effect.kind == "snapshot"]
    assert first.pos == enemy.pos and enemy.revealed_until <= match.time
    assert not any(effect["kind"] == "snapshot" for effect in match.snapshot(enemy_id)["effects"])
    enemy.pos = Vec(85, 85)
    advance(match, 0.5)
    assert first.pos != enemy.pos
    advance(match, 3.5)
    second, = [effect for effect in match.effects if effect.kind == "snapshot"]
    assert second.pos == enemy.pos


def test_sage_revive_finishes_on_the_original_target_after_windup() -> None:
    match, pid, _ = match_for("sage")
    player = match.players[pid]
    fallen = match.add_player("Fallen", player.team, "omen")
    fallen.alive, fallen.pos, fallen.hp = False, Vec(10, 20), 0
    player.ult_points = 7
    match.tick(1 / 64, {pid: Command(ability="X", facing=0, cursor_depth=10)})
    assert player.ult_points == 0 and not fallen.alive
    match.tick(1 / 64, {pid: Command(facing=180)})
    advance(match, 2)
    assert fallen.alive and fallen.hp == 100


@pytest.mark.parametrize("timer_ticks_after_revive", [1, 0, -1])
@pytest.mark.parametrize("round_end", ["timer", "detonation", "defuse", "early_defuse"])
def test_sage_resurrection_at_round_deadline(timer_ticks_after_revive: int, round_end: str) -> None:
    match, pid, enemy_id = match_for("sage")
    sage = match.players[pid]
    fallen = match.add_player("Fallen", sage.team, "omen")
    fallen.pos = Vec(10, 20)
    match._kill(None, fallen, "vandal", "body")
    sage.ult_points = match.ultimate_cost(sage)
    match.tick(1 / 64, {pid: Command(ability="X", facing=0, cursor_depth=10)})
    marker, = [e for e in match.effects if e.props.get("revive_pid") == fallen.pid]
    deadline = marker.until + timer_ticks_after_revive / 64
    if round_end == "timer":
        match.phase_until = deadline
        reason = "Time ran out"
    else:
        defender = match.players[enemy_id]
        match._plant(sage, "A", point=defender.pos)
        match.spike_planted_at = deadline - float(match._spike["fuse_time"])
        reason = "Bomb detonated"
        if round_end in ("defuse", "early_defuse"):
            reason = "Bomb defused"
        if round_end == "early_defuse":
            match.spike_planted_at += 10
    while match.time < marker.until + 1 / 64:
        commands = {}
        if reason == "Bomb defused" and match.time == deadline - 1 / 64:
            defender.defusing = True
            defender.defuse_progress = float(match._spike["defuse_time"]) - 1 / 64
            commands[enemy_id] = Command(use_spike=True)
        match.tick(1 / 64, commands)
        assert fallen.alive == (timer_ticks_after_revive == 1 and match.time >= marker.until)
    assert match.phase == "end" and match.round_reason == reason


def test_dark_cover_uses_spatial_range_and_travel_time() -> None:
    from math import sqrt

    match, pid, _ = match_for("omen")
    player = match.players[pid]
    distance = sqrt(80 ** 2 - 3 ** 2)
    match.tick(1 / 64, {pid: Command(ability="E", points=[(10, 10 + distance + 0.01)], target_lift=3)})
    assert player.charges["E"] == 1 and not match.effects
    advance(match, 1 / 64)
    match.tick(1 / 64, {pid: Command(ability="E", points=[(10, 10 + distance)], target_lift=3)})
    [smoke] = match.effects
    assert player.charges["E"] == 0
    assert smoke.start - match.time == pytest.approx(80 / 64)


def test_dark_cover_rejects_targets_beyond_eighty_meters() -> None:
    match, pid, _ = match_for("omen")
    player = match.players[pid]
    match.tick(1 / 64, {pid: Command(ability="E", points=[(10, 90.01)])})
    assert player.charges["E"] == 1 and not match.effects
    advance(match, 1 / 64)
    match.tick(1 / 64, {pid: Command(ability="E", points=[(10, 90)])})
    [smoke] = match.effects
    assert player.charges["E"] == 0 and smoke.pos == Vec(10, 90)
    assert smoke.radius == pytest.approx(4.1)
    assert smoke.start - match.time == pytest.approx(80 / 64)
    advance(match, 80 / 64)
    through_edge = (Vec(14.05, 85), Vec(14.05, 95))
    assert not match._line_clear(*through_edge, player.level)
    assert match._line_clear(Vec(14.15, 85), Vec(14.15, 95), player.level)
    advance(match, 15)
    assert match._line_clear(*through_edge, player.level)


@pytest.mark.parametrize(("point", "under_deck", "ground"), [
    ((10, 20), False, 0),
    ((20, 20), False, 2),
    ((15, 20), False, 1),
    ((30, 20), False, 3),
    ((30, 20), True, 0),
])
def test_dark_cover_settles_on_selected_floor_and_keeps_its_sound_positions(
    point: tuple[int, int], under_deck: bool, ground: int
) -> None:
    from gameplay.world import Deck, Platform

    world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(90, 90)]},
                     platforms=[Platform(Rect(18, 17, 22, 23), 2)], ramps=[Rect(12, 17, 18, 23)],
                     ramp_spans={0: ("x", False, 0, 2)}, decks=[Deck(Rect(25, 15, 35, 25), 3, 0)])
    match, pid, _ = match_for("omen", world)
    cmd = command_from_json({"ability": "E", "ability_alt": under_deck, "points": [point]})
    cast = match.tick(1 / 64, {pid: cmd})
    [cue] = [e for e in cast if e.kind == "sound_fx"]
    assert cue.data["pos"] == (10, 10) and cue.data["key"] == "cast_deploy"
    [smoke] = match.effects
    assert smoke.pos == Vec(*point) and smoke.props["settled_ground"] == ground
    client = Match(match.world, agent_roster=playable_agents())
    apply_snapshot(client, match.snapshot(pid), pid)
    assert client.effects[0].props["settled_ground"] == ground
    advance(match, smoke.start - match.time + 1 / 64)
    if point == (30, 20):
        assert match._line_clear(Vec(25, 20), Vec(35, 20), 0) == (ground == 3)
        assert match._line_clear(Vec(25, 20), Vec(35, 20), 3) == (ground == 0)
    fade = []
    while match.time < smoke.until:
        fade.extend(e for e in match.tick(1 / 64, {}) if e.kind == "sound_fx")
    [warning] = fade
    assert warning.data["pos"] == point and warning.data["key"] == "cast_whoosh"
    assert smoke.until - warning.t == pytest.approx(1.5, abs=1 / 64)


def test_raised_dark_cover_falls_and_expands_its_sight_footprint() -> None:
    from gameplay.world import Deck

    world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(90, 90)]},
                     decks=[Deck(Rect(15, 15, 25, 25), 3, 0)])
    match, pid, _ = match_for("omen", world)
    cmd = command_from_json({"ability": "E", "ability_alt": True, "target_lift": 2.5, "points": [[20, 20]]})
    cmd = merge_commands(cmd, Command())
    cast = match.tick(1 / 64, {pid: cmd})
    assert [e.data["pos"] for e in cast if e.kind == "sound_fx"] == [(10, 10)]
    [smoke] = match.effects
    assert smoke.props["settled_ground"] == 0
    assert smoke.fall_offset(smoke.start) == pytest.approx(2.5)
    ray = (Vec(15, 23.8), Vec(25, 23.8))
    while match.time < smoke.start:
        assert not any(e.kind == "sound_fx" for e in match.tick(1 / 64, {}))
    assert match._line_clear(*ray, 0)
    assert not match._line_clear(Vec(15, 20), Vec(25, 20), 0)
    client = Match(world, agent_roster=playable_agents())
    apply_snapshot(client, match.snapshot(pid), pid)
    assert client.effects[0].fall_offset(client.time) == pytest.approx(smoke.fall_offset(match.time))
    while smoke.fall_offset(match.time) > 0:
        assert not any(e.kind == "sound_fx" for e in match.tick(1 / 64, {}))
    assert not match._line_clear(*ray, 0)
    assert match._line_clear(*ray, 3)
    fade = []
    while match.time < smoke.until:
        fade.extend(e for e in match.tick(1 / 64, {}) if e.kind == "sound_fx")
    [warning] = fade
    assert warning.data["pos"] == (20, 20) and warning.data["key"] == "cast_whoosh"
    assert smoke.until - warning.t == pytest.approx(1.5, abs=1 / 64)


def test_dark_cover_rejects_a_drop_without_a_walkable_floor() -> None:
    match, pid, _ = match_for("omen")
    player = match.players[pid]
    match.world.drop_zones.append((Rect(8, 18, 12, 22), Vec(10, 17)))
    events = match.tick(1 / 64, {pid: Command(ability="E", points=[(10, 20)])})
    assert player.charges["E"] == 1 and not match.effects
    assert not any(e.kind == "sound_fx" for e in events)


def test_dark_cover_recharges_one_charge_at_a_time_and_locks_weapon_fire() -> None:
    match, pid, _ = match_for("omen")
    player = match.players[pid]
    match.phase = "buy"
    assert match.buy(player, "E") and player.charges["E"] == 2
    match.phase = "live"
    player.equip_until = 0
    weapon = player.weapon
    assert weapon is not None
    magazine = weapon.mag

    match.tick(1 / 64, {pid: Command(ability="E", points=[(10, 20)], fire=True)})
    first_cast_at = match.time
    assert player.charges["E"] == 1 and weapon.mag == magazine
    advance(match, 1 / 64)
    match.tick(1 / 64, {pid: Command(ability="E", points=[(20, 20)])})
    assert player.charges["E"] == 0
    advance(match, 43 / 64)
    match.tick(1 / 64, {pid: Command(fire=True)})
    assert weapon.mag == magazine
    advance(match, 1 / 64)
    match.tick(1 / 64, {pid: Command(fire=True)})
    assert weapon.mag == magazine - 1

    # The recharge timer includes the tick that spends the first charge.
    advance(match, first_cast_at + 40 - 2 / 64 - match.time)
    assert player.charges["E"] == 0
    advance(match, 1 / 64)
    assert player.charges["E"] == 1
    advance(match, 40 - 1 / 64)
    assert player.charges["E"] == 1
    advance(match, 1 / 64)
    assert player.charges["E"] == 2


def test_omen_ultimate_shade_can_only_be_shot_after_windup() -> None:
    match, pid, enemy_id = match_for("omen")
    player, enemy = match.players[pid], match.players[enemy_id]
    origin = player.pos
    enemy.pos = Vec(30, 14)
    enemy.equip_until = 0
    player.ult_points = 7
    match.tick(1 / 64, {pid: Command(ability="X", points=[(30, 20)])})
    [shade] = match.effects
    match.tick(1 / 64, {enemy_id: Command(fire=True, facing=0)})
    assert not shade.props.get("ended")
    advance(match, 1.5)
    match.tick(1 / 64, {enemy_id: Command(fire=True, facing=0)})
    assert shade not in match.effects
    assert player.pos == origin and player.channel_until == 0 and player.ult_points == 0


@pytest.mark.parametrize("cancel", [False, True])
def test_omen_ultimate_obscures_only_enemy_minimaps_until_it_ends(cancel: bool) -> None:
    match, pid, enemy_id = match_for("omen")
    player, enemy = match.players[pid], match.players[enemy_id]
    ally = match.add_player("Ally", player.team, "sage")
    player.ult_points = 7
    match.tick(1 / 64, {pid: Command(ability="X", points=[(30, 20)])})
    [shade] = match.effects
    assert match.time < shade.start
    assert not match.minimap_obscured(player) and not match.minimap_obscured(ally)
    guest = Match(match.world, agent_roster=playable_agents())
    snap = match.snapshot(enemy_id)
    assert not snap["effects"]
    apply_snapshot(guest, snap, enemy_id)
    assert guest.minimap_obscured(guest.players[enemy_id])
    advance(match, 1.5)
    assert match.minimap_obscured(enemy)
    if cancel:
        match.tick(1 / 64, {pid: Command(ability="X")})
    else:
        advance(match, 2.5)
    assert not match.minimap_obscured(enemy)
    apply_snapshot(guest, match.snapshot(enemy_id), enemy_id)
    assert not guest.minimap_obscured(guest.players[enemy_id])


@pytest.mark.parametrize("slot", ["C", "X"])
def test_kayo_zero_point_cancels_omen_on_teleport_tick(slot: str) -> None:
    match, pid, _ = match_for("omen")
    omen = match.players[pid]
    kayo = match.add_player("KAY/O", 1, "kayo")
    origin = omen.pos
    kayo.pos, kayo.charges["E"] = Vec(10, 16), 1
    omen.charges["C"], omen.ult_points = 1, 7
    teleport = Command(ability="X", points=[(30, 20)]) if slot == "X" else Command(ability="C", facing=90, cursor_depth=10)
    knife = Command(ability="E", facing=180, cursor_depth=6)
    if slot == "X":
        match.tick(1 / 64, {pid: teleport})
        advance(match, 2 / 64)
        match.tick(1 / 64, {kayo.pid: knife})
    else:
        match.tick(1 / 64, {kayo.pid: knife})
        advance(match, 47 / 64)
        match.tick(1 / 64, {pid: teleport})

    [marker] = [e for e in match.effects if e.props.get("interruptible_teleport")]
    boundary = marker.start if slot == "X" else marker.until
    while match.time + 1 / 64 < boundary:
        advance(match, 1 / 64)
    assert "suppress" not in omen.status and marker in match.effects
    advance(match, 1 / 64)
    assert omen.status.get("suppress", 0) > match.time
    assert omen.pos == origin and omen.channel_until == 0 and marker not in match.effects


@pytest.mark.parametrize("slot", ["C", "X"])
def test_omen_teleport_suppression_interrupts_windup(slot: str) -> None:
    from gameplay.abilities import apply_status

    match, pid, enemy_id = match_for("omen")
    player = match.players[pid]
    origin = player.pos
    player.charges["C"], player.ult_points = 1, 7
    cmd = Command(ability="X", points=[(30, 20)]) if slot == "X" else Command(ability="C", cursor_depth=10)
    match.tick(1 / 64, {pid: cmd})
    [marker] = match.effects
    apply_status(match, player, "suppress", 0.1)
    advance(match, 1 / 64)
    assert player.channel_until == 0 and marker not in match.effects
    assert not match.minimap_obscured(match.players[enemy_id])
    assert "weapon_recovery" not in player.status
    advance(match, 4)
    assert player.pos == origin
    assert (player.charges["C"], player.ult_points) == ((1, 0) if slot == "X" else (0, 7))


def test_omen_ultimate_can_be_cancelled_without_refunding_points() -> None:
    from gameplay.abilities import apply_status

    match, pid, _ = match_for("omen")
    player = match.players[pid]
    origin = player.pos
    player.ult_points = 7
    match.tick(1 / 64, {pid: Command(ability="X", points=[(97, 97)])})
    assert player.ult_points == 0 and player.channel_until > match.time
    assert match.effects[0].pos == Vec(97, 97)
    [shade] = match.effects
    assert shade.start - match.time == pytest.approx(1.5)
    assert shade.until - shade.start == pytest.approx(2.5)
    advance(match, 0.1)
    match.tick(1 / 64, {pid: Command(ability="X")})
    assert not shade.props.get("ended")
    advance(match, 1.5)
    assert player.pos == shade.pos
    apply_status(match, player, "suppress", 2)
    advance(match, 0.2)
    assert player.pos == shade.pos and shade in match.effects
    match.tick(1 / 64, {pid: Command(ability="X")})
    assert shade.props.get("ended")
    advance(match, 3)
    assert player.pos == origin and player.ult_points == 0


def test_omen_shade_can_collect_spike_and_carry_it_back_on_cancel() -> None:
    match, pid, enemy_id = match_for("omen")
    player, enemy = match.players[pid], match.players[enemy_id]
    origin, destination = player.pos, Vec(30, 20)
    enemy.pos = Vec(30, 32)
    match.spike_carrier, match.spike_pos = None, destination
    player.ult_points = 7
    match.tick(1 / 64, {pid: Command(ability="X", points=[(destination.x, destination.y)])})
    advance(match, 1.5)
    assert player.pos == destination and match.spike_carrier == pid
    assert match.sight_range(player) == pytest.approx(0)
    enemy.revealed_until = match.time + 2
    assert not match.can_see(player, enemy)
    shadow = Match(match.world, agent_roster=playable_agents())
    apply_snapshot(shadow, match.snapshot(pid), pid)
    assert shadow.players[pid].pos == destination
    assert "omen_shade" in shadow.players[pid].status
    assert shadow.sight_range(shadow.players[pid]) == pytest.approx(0)
    advance(match, 0.5)
    early = match.sight_range(player)
    assert 0 < early < 12
    assert not match.can_see(player, enemy)
    advance(match, 0.5)
    assert match.sight_range(player) > 2 * early
    assert match.can_see(player, enemy)
    match.tick(1 / 64, {pid: Command(ability="X")})
    assert player.pos == origin and match.spike_carrier == pid
    assert "omen_shade" not in player.status
    assert match.sight_range(player) is None
