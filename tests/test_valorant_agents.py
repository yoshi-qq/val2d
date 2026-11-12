"""Regression coverage for the eight playable VALORANT kits."""
from __future__ import annotations

import pytest

from gameplay.geometry import Rect, Vec
from gameplay.kit.engine import expand, resolve_target
from gameplay.match import Command, Match, PLAYABLE_AGENT_KEYS, playable_agents
from gameplay.net import apply_snapshot, command_from_json, merge_commands
from gameplay.world import Wall, WorldMap


def match_for(agent: str) -> tuple[Match, int, int]:
    world = WorldMap("test", "Test", 100, 100, spawns={0: [Vec(10, 10)], 1: [Vec(90, 90)]})
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


def test_omen_teleport_rejects_a_wall_and_only_moves_after_channel() -> None:
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
    advance(match, 2.6)
    assert player.pos == Vec(30, 20)


def test_paranoia_travels_through_walls_and_hits_allies() -> None:
    from gameplay.abilities import has

    match, pid, enemy_id = match_for("omen")
    player, enemy = match.players[pid], match.players[enemy_id]
    ally = match.add_player("Ally", player.team, "sage")
    ally.pos, enemy.pos = Vec(10, 17), Vec(10, 27)
    match.world.walls.append(Wall(Rect(8, 21, 12, 22), 3))
    player.charges["Q"] = 1
    match.tick(1 / 64, {pid: Command(ability="Q", facing=0)})
    assert not has(match, ally, "nearsight") and not has(match, enemy, "nearsight")
    advance(match, 0.5)
    assert has(match, ally, "nearsight") and not has(match, enemy, "nearsight")
    advance(match, 0.45)
    assert has(match, enemy, "nearsight") and not has(match, player, "nearsight")


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


def test_omen_ultimate_can_be_cancelled_without_refunding_points() -> None:
    match, pid, _ = match_for("omen")
    player = match.players[pid]
    origin = player.pos
    player.ult_points = 7
    match.tick(1 / 64, {pid: Command(ability="X", points=[(97, 97)])})
    assert player.ult_points == 0 and player.channel_until > match.time
    assert match.effects[0].pos == Vec(97, 97)
    advance(match, 0.1)
    match.tick(1 / 64, {pid: Command(ability="X")})
    advance(match, 3)
    assert player.pos == origin and player.ult_points == 0
