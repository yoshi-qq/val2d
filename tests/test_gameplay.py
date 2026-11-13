"""Tests for the game core (without pygame)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gameplay.bots import BotDirector
from gameplay.data import HitZoneConfig, load_weapons
from gameplay.geometry import Vec, heading
from gameplay.hitzones import resolve_zone
from gameplay.match import Command, Match
from map_fixtures import load_archived_map

CFG = HitZoneConfig()
UP = heading(0)


def zone(target: Vec, cursor_depth: float, same_level: bool = True, cursor_level: bool = True) -> str | None:
    return resolve_zone(Vec(0, 0), UP, UP, cursor_depth, target, same_level, cursor_level, CFG).zone


def test_hitzone_head_when_cursor_on_target() -> None:
    assert zone(Vec(0, 10), 10) == "head"


def test_hitzone_head_missed_sideways_gives_body() -> None:
    assert zone(Vec(0.3, 10), 10) == "body"


def test_hitzone_depth_off_gives_body_then_legs() -> None:
    assert zone(Vec(0, 10), 8) == "body"
    assert zone(Vec(0, 10), 2) == "legs"


def test_hitzone_at_least_legs_far_sideways_within_body() -> None:
    assert zone(Vec(0.35, 10), 1) == "legs"


def test_hitzone_miss_outside_body_and_other_level() -> None:
    assert zone(Vec(0.5, 10), 10) is None
    assert zone(Vec(0, 10), 10, same_level=False) is None
    assert zone(Vec(0, 10), 10, cursor_level=False) is None


def duel(seed: int = 1, agents: tuple[str, str] = ("jett", "omen")) -> tuple[Match, int, int]:
    m = Match(load_archived_map("workyard"), seed=seed)
    a = m.add_player("A", 0, agents[0]).pid
    b = m.add_player("B", 1, agents[1]).pid
    m.start()
    return m, a, b


def run(m: Match, seconds: float, cmds: dict[int, Command] | None = None, dt: float = 1 / 64) -> None:
    for _ in range(int(seconds / dt)):
        m.tick(dt, cmds or {})


def test_buy_phase_then_live() -> None:
    m, a, _ = duel()
    assert m.phase == "buy"
    assert m.buy(m.players[a], "frenzy")
    assert m.players[a].credits == 800 - m.weapons["frenzy"].price
    run(m, 31)
    assert m.phase == "live"


def test_first_shot_standing_is_exact_and_kills_with_headshots() -> None:
    m, a, b = duel()
    pa, pb = m.players[a], m.players[b]
    run(m, 31)
    pa.pos, pb.pos = Vec(24, 16), Vec(24, 24)  # mid, clear sight? the pillar at 22-26/18-22 blocks
    pa.pos, pb.pos = Vec(17, 15), Vec(17, 25)
    pa.facing = 0.0
    d = m.weapons["classic"]
    assert m.current_spread(pa, d) == 0.0
    shots = 0
    while pb.alive and shots < 10:
        m.tick(1 / 64, {a: Command(facing=0.0, cursor_depth=10.0, fire=True)})
        m.tick(0.2, {a: Command(facing=0.0, cursor_depth=10.0, fire=False)})
        shots += 1
    assert not pb.alive
    assert m.phase == "end" and m.round_winner == 0


def test_armor_absorbs_damage() -> None:
    m, a, b = duel()
    pa, pb = m.players[a], m.players[b]
    pb.armor = 50
    m._damage(pa, pb, 40, "body", "test")
    assert pb.hp == 100 - (40 - 26) and pb.armor == 50 - 26


def test_wall_penetration_by_level() -> None:
    m, a, b = duel()
    pa, pb = m.players[a], m.players[b]
    run(m, 31)
    pa.pos, pb.pos = Vec(12, 20), Vec(17, 20)
    # target behind a thin wall (x 14..15, 1 m thick): the sidearm (level 0) penetrates level 0
    m.tick(1 / 64, {a: Command(facing=90.0, cursor_depth=5.0, fire=True)})
    assert pb.hp < 100
    hp = pb.hp
    # thick pillar (level 3) stops everything
    pa.pos, pb.pos = Vec(20, 20), Vec(28, 20)
    m.tick(0.5, {a: Command(facing=90.0, cursor_depth=8.0)})
    m.tick(1 / 64, {a: Command(facing=90.0, cursor_depth=8.0, fire=True)})
    assert pb.hp == hp


def test_plant_and_explode_gives_attackers_round() -> None:
    m, a, b = duel()
    m.players[a].pos = m.spike_pos
    run(m, 31)
    pa = m.players[a]
    assert m.spike_carrier == a
    pa.pos = Vec(8, 30)
    run(m, 4.2, {a: Command(interact=True)})
    assert m.phase == "planted"
    credits = pa.credits
    m.players[b].pos = Vec(40, 2)
    run(m, 46)
    assert m.round_winner == 0
    assert pa.credits > credits


def test_defuse_with_checkpoint() -> None:
    m, a, b = duel()
    m.players[a].pos = m.spike_pos
    run(m, 31)
    pa, pb = m.players[a], m.players[b]
    pa.pos = Vec(8, 30)
    run(m, 4.2, {a: Command(interact=True)})
    pb.pos = Vec(8.5, 30)
    run(m, 4.0, {b: Command(interact=True)})
    run(m, 0.5)
    assert pb.defuse_progress == 3.5
    run(m, 3.7, {b: Command(interact=True)})
    assert m.round_winner == 1


def test_loss_streak_economy() -> None:
    m, a, b = duel()
    for expected in (1900, 2400, 2900, 2900):  # Valorant loss streak
        before = m.players[b].credits
        m._end_round(0, "test")
        assert m.players[b].credits - before == expected or m.players[b].credits == 9000
        m.phase = "live"


def test_side_switch_and_overtime_win_by_two() -> None:
    m, _, _ = duel()
    m.overtime = True
    m.score = [12, 12]
    m.round_no = 24
    m.phase = "live"
    m._end_round(0, "test")
    assert m.match_winner is None
    m.phase = "live"
    m._end_round(0, "test")
    assert m.match_winner == 0


def test_abilities_smoke_blocks_sight_and_dash_moves(archived_agents) -> None:
    m, a, b = duel(agents=("kestrel", "marrow"))
    run(m, 31)
    pa, pb = m.players[a], m.players[b]
    pa.pos, pb.pos = Vec(17, 15), Vec(17, 25)
    pa.facing = pb.facing = 0.0
    pb.facing = 180.0
    assert m.can_see(pb, pa)
    m.tick(1 / 64, {b: Command(facing=180.0, cursor_depth=5.0, ability="E")})
    assert any(e.kind == "smoke" for e in m.effects)
    assert not m.can_see(pb, pa)
    start = pa.pos
    m.tick(1 / 64, {a: Command(facing=90.0, ability="E")})
    run(m, 0.3)
    assert (pa.pos - start).length() > 4.0


def test_flash_blinds_viewer(archived_agents) -> None:
    m, a, b = duel(agents=("kestrel", "marrow"))
    run(m, 31)
    pa, pb = m.players[a], m.players[b]
    pa.pos, pb.pos = Vec(17, 15), Vec(17, 25)
    pa.charges["C"] = 1
    pb.facing = 180.0
    m.tick(1 / 64, {a: Command(facing=0.0, cursor_depth=6.0, ability="C")})
    run(m, 0.6, {b: Command(facing=180.0)})
    assert pb.blind_until > m.time


def test_weapons_complete() -> None:
    w = load_weapons()
    assert len([k for k, d in w.items() if d.slot == "primary"]) >= 12
    assert len([k for k, d in w.items() if d.slot == "sidearm"]) >= 4


def test_bot_match_runs_to_end() -> None:
    m = Match(load_archived_map("workyard"), seed=3)
    for i in range(5):
        m.add_player(f"Bot A{i}", 0, "jett" if i % 2 else "omen", is_bot=True)
        m.add_player(f"Bot B{i}", 1, "omen" if i % 2 else "jett", is_bot=True)
    m.win_rounds = 3
    m.overtime = False
    director = BotDirector(m, seed=3)
    m.start()
    dt = 1 / 32
    for _ in range(int(60 * 60 / dt)):
        m.tick(dt, director.commands(dt))
        if m.phase == "over":
            break
    assert m.phase == "over"
    assert max(m.score) == 3


def test_weapons_come_from_python_config() -> None:
    weapons = load_weapons()
    assert len([w for w in weapons.values() if w.slot != "melee"]) == 20
    assert weapons["warden"].mag == 18 and weapons["warden"].price == 2900
    assert weapons["odin"].rate_ramp is not None


def test_rate_ramp_speeds_up_held_fire() -> None:
    m, a, _ = duel()
    run(m, 31)
    p = m.players[a]
    p.weapons["primary"] = m._new_weapon("odin")
    p.slot = "primary"
    p.equip_until = 0.0
    shots_early = shots_late = 0
    for i in range(int(3.0 * 64)):
        events = m.tick(1 / 64, {a: Command(facing=180.0, fire=True)})
        fired = sum(1 for e in events if e.kind == "shot")
        if i < 32:
            shots_early += fired
        elif i >= 128:
            shots_late += fired
    assert shots_late > shots_early * 1.2


def test_map_materials_set_wall_properties() -> None:
    m = load_archived_map("alley")
    glass = [w for w in m.walls if w.material == "glass"]
    assert glass and not glass[0].blocks_sight and glass[0].height == 2 and glass[0].penetration == 0
    assert m.floor == "concrete" and any(mat == "tiles" for mat, _ in m.floors)


def test_map_objects_block_and_spawn_barrier_only_in_buy_phase() -> None:
    m = load_archived_map("alley")
    keys = {o.key for o in m.objects}
    assert {"door", "barrel", "spawn_barrier", "bench"} <= keys and m.decals
    barrier_walls = [w for w in m.walls if w.buy_phase_only]
    assert barrier_walls
    match = Match(m, seed=1)
    a = match.add_player("A", 0, "jett").pid
    match.add_player("B", 1, "jett")
    match.start()
    p = match.players[a]
    p.pos = Vec(12, 4.0)
    for _ in range(64):
        match.tick(1 / 64, {a: Command(facing=0.0, move_y=1.0)})
    assert p.pos.y < 4.7  # held back by the barrier during the buy phase
    match.phase, match.phase_until = "live", match.time + 90
    for _ in range(64):
        match.tick(1 / 64, {a: Command(facing=0.0, move_y=1.0)})
    assert p.pos.y > 5.5


def _armed(key: str) -> tuple[Match, int, int]:
    m, a, b = duel()
    run(m, 31)
    p = m.players[a]
    p.weapons["primary"] = m._new_weapon(key)
    p.slot, p.equip_until = "primary", 0.0
    return m, a, b


def test_alt_burst_fires_a_burst_per_press() -> None:
    m, a, _ = _armed("bulldog")
    shots = 0
    for i in range(40):
        events = m.tick(1 / 64, {a: Command(facing=180.0, alt_fire=i < 2)})
        shots += sum(1 for e in events if e.kind == "shot")
    assert shots == 3


def test_alt_zoom_reduces_spread_and_speed() -> None:
    m, a, _ = _armed("marshal")
    p = m.players[a]
    d = m.weapons["marshal"]
    p.vel = Vec(3.0, 0.0)
    plain_spread, plain_speed = m.current_spread(p, d), m._max_speed(p)
    m.tick(1 / 64, {a: Command(facing=180.0, alt_fire=True)})
    p.vel = Vec(3.0, 0.0)
    assert p.zoomed
    assert m.current_spread(p, d) < plain_spread and m._max_speed(p) < plain_speed


def test_alt_spread_shot_fires_three_pellets_for_one_round() -> None:
    m, a, _ = duel()
    run(m, 31)
    p = m.players[a]
    p.equip_until = 0.0
    mag = p.weapon.mag
    events = m.tick(1 / 64, {a: Command(facing=180.0, alt_fire=True)})
    assert sum(1 for e in events if e.kind == "shot") == 3 and p.weapon.mag == mag - 1


def test_alt_spin_fires_at_top_rate_immediately() -> None:
    m, a, _ = _armed("odin")
    shots = 0
    for _ in range(64):
        shots += sum(1 for e in m.tick(1 / 64, {a: Command(facing=180.0, alt_fire=True)}) if e.kind == "shot")
    assert shots >= 15


def test_door_opens_with_f_and_lets_players_through() -> None:
    m = Match(load_archived_map("alley"), seed=1)
    a = m.add_player("A", 0, "jett").pid
    m.add_player("B", 1, "jett")
    m.start()
    m.phase, m.phase_until = "live", m.time + 90
    door = next(w for w in m.world.walls if w.door)
    p = m.players[a]
    c = door.rect.center
    p.pos = Vec(c.x, door.rect.y0 - 0.6)
    assert m.wall_active(door)
    m.tick(1 / 64, {a: Command(facing=0.0, interact=True)})
    assert door.rect in m.open_doors and not m.wall_active(door)
    m.tick(1 / 64, {a: Command(facing=0.0)})
    m.tick(1 / 64, {a: Command(facing=0.0, interact=True)})
    assert door.rect not in m.open_doors
    m._start_round()
    assert not m.open_doors


def test_spray_pattern_first_bullets_on_target_then_drift_to_one_side() -> None:
    from gameplay.match import spray_offset
    d = load_weapons()["phantom"]
    offsets = [spray_offset(d, i) for i in range(20)]
    assert offsets[0] == offsets[1] == 0.0
    later = offsets[6:16]
    assert all(abs(o) <= d.spray_max for o in offsets)
    assert sum(1 for o in later if o > 0) in (0, 1, 9, 10) or abs(sum(later)) > 0.5 * sum(abs(o) for o in later)
    assert spray_offset(load_weapons()["guardian"], 8) == 0.0  # semi-automatic: no pattern


def test_drop_bomb_and_weapon_with_g() -> None:
    m, a, _ = duel()
    run(m, 31)
    p = m.players[a]
    m.spike_carrier = a
    p.weapons["primary"] = m._new_weapon("vandal")
    p.slot = "primary"
    m.tick(1 / 64, {a: Command(facing=0.0, drop=True)})
    assert "primary" not in p.weapons and any(d.key == "vandal" for d in m.drops) and p.slot == "sidearm"
    assert m.spike_carrier == a
    m.tick(1 / 64, {a: Command(slot="spike")})
    m.tick(1 / 64, {a: Command(facing=0.0, drop=True)})
    assert m.spike_carrier is None and m.spike_pos is not None
    m.tick(1 / 64, {a: Command(facing=0.0)})
    assert "primary" not in p.weapons  # not picked up again right away


def test_dropping_sidearm_equips_remaining_primary() -> None:
    m, a, _ = duel()
    p = m.players[a]
    p.weapons["primary"] = m._new_weapon("vandal")
    assert p.slot == "sidearm"
    m.tick(1 / 64, {a: Command(drop=True)})
    assert p.slot == "primary" and p.weapon.key == "vandal"
    assert p.equip_until > m.time
    assert any(drop.key == "classic" for drop in m.drops)


def test_nav_path_goes_around_walls() -> None:
    from gameplay.nav import grid_for
    world = load_archived_map("workyard")
    grid = grid_for(world)
    goal = grid.center(grid.nearest_free(grid.cell(Vec(8, 33.5))))  # site A, next to the platform
    path = grid.path(Vec(24, 3), goal)
    assert path and (path[-1] - goal).length() < 0.01
    points = [Vec(24, 3)] + path
    assert all(grid.line_free(a, b) for a, b in zip(points, points[1:]))


def test_practice_range_buys_anywhere_and_targets_respawn() -> None:
    m = Match(load_archived_map("range"), seed=1)
    a = m.add_player("A", 0, "jett").pid
    targets = []
    for pos, _ in m.world.practice_targets:
        d = m.add_player("T", 1, "jett", is_bot=True)
        d.dummy, d.home = True, pos
        targets.append(d)
    m.start_practice()
    p = m.players[a]
    p.pos = Vec(30, 20)
    assert m.buy(p, "operator") and m.phase == "live"
    m._kill(p, targets[0], "test", "head")
    run(m, 2.5)
    assert targets[0].alive and (targets[0].pos - targets[0].home).length() < 0.01
    run(m, 200)
    assert m.phase == "live" and m.round_no == 1


def test_fall_damage_only_above_safe_speed() -> None:
    m, a, _ = duel()
    run(m, 31)
    p = m.players[a]
    p.vz = 4.2  # an ordinary jump
    p.z = 0.01
    run(m, 1.0)
    assert p.hp == 100
    p.z, p.vz = 3.5, 0.0  # dropping from 3.5 m
    run(m, 1.5)
    assert 40 <= p.hp < 100


def test_damage_report_history_and_combat_score() -> None:
    m, a, b = duel()
    run(m, 31)
    pa, pb = m.players[a], m.players[b]
    m._damage(pa, pb, 30, "body", "test")
    m._damage(pb, pa, 20, "head", "test")
    report = m.damage_report(a)
    assert report[0]["dealt"] == 30 and report[0]["taken"] > 0 and report[0]["dealt_hits"] == 1
    m._kill(pa, pb, "test", "head")
    run(m, 0.1)
    assert m.history and m.history[-1][0] == pa.team
    assert m.combat_score(pa) >= 150 + 30 and pa.first_kills == 1


def test_team_buy_request_and_gift() -> None:
    m = Match(load_archived_map("workyard"), seed=1)
    a = m.add_player("A", 0, "jett").pid
    b = m.add_player("B", 0, "omen").pid
    m.add_player("E", 1, "jett")
    m.start()
    pa, pb = m.players[a], m.players[b]
    pa.credits = 5000
    m.tick(1 / 64, {b: Command(request="vandal")})
    assert pb.request == "vandal"
    gift = Command(buy=[pb.gift_action()])
    m.tick(1 / 64, {a: gift, b: Command(request="")})
    assert pb.request == "" and pa.credits == 5000 and "primary" not in pb.weapons
    m.tick(1 / 64, {a: gift, b: Command(request="phantom")})
    assert pb.request == "phantom" and pa.credits == 5000 and "primary" not in pb.weapons
    m.tick(1 / 64, {b: Command(request="vandal")})
    m.tick(1 / 64, {a: gift})
    assert pb.request == "vandal" and pa.credits == 5000 and "primary" not in pb.weapons
    m.tick(1 / 64, {a: Command(buy=[pb.gift_action()])})
    assert pb.weapons["primary"].key == "vandal" and pa.credits == 5000 - m.weapons["vandal"].price
    assert pb.request == ""
    enemy = m.players[3]
    m.tick(1 / 64, {enemy.pid: Command(request="vandal")})
    assert not m.buy(pa, enemy.gift_action())
    m.tick(1 / 64, {b: Command(request="phantom", buy=["buy:phantom"])})
    assert pb.request == "phantom"  # insufficient credits
    pb.credits = 5000
    m.tick(1 / 64, {b: Command(buy=["buy:phantom"])})
    assert pb.request == "" and pb.weapons["primary"].key == "phantom"
    m.tick(1 / 64, {b: Command(request="phantom")})
    assert pb.request == ""
    m.tick(1 / 64, {b: Command(request="vandal")})
    revision = pb.request_revision
    m.tick(1 / 64, {b: Command(request="phantom")})
    assert pb.request == "vandal" and pb.request_revision == revision


def test_same_tick_team_purchase_follows_self_purchase_in_either_player_order() -> None:
    for recipient_first in (False, True):
        m = Match(load_archived_map("workyard"), seed=1)
        first = m.add_player("First", 0, "jett")
        second = m.add_player("Second", 0, "omen")
        m.add_player("Defender", 1, "jett")
        recipient, buyer = (first, second) if recipient_first else (second, first)
        m.start()
        buyer.credits = recipient.credits = 5000
        m.tick(1 / 64, {recipient.pid: Command(request="vandal")})
        commands = {recipient.pid: Command(buy=["buy:vandal"]),
                    buyer.pid: Command(buy=[recipient.gift_action()])}
        m.tick(1 / 64, commands)
        assert buyer.credits == 5000 and recipient.credits == 2100
        assert recipient.weapons["primary"].key == "vandal" and recipient.request == ""

        m.tick(1 / 64, {recipient.pid: Command(request="phantom")})
        commands[recipient.pid] = Command(buy=["buy:phantom"])
        commands[buyer.pid] = Command(buy=[recipient.gift_action()])
        m.tick(1 / 64, commands)
        assert buyer.credits == 2100 and recipient.credits == 2100
        assert recipient.weapons["primary"].key == "phantom" and recipient.request == ""


def test_two_same_tick_team_purchases_charge_one_buyer() -> None:
    m = Match(load_archived_map("workyard"), seed=1)
    recipient, first, second = [m.add_player(name, 0, "omen") for name in ("Recipient", "First", "Second")]
    m.add_player("Defender", 1, "jett")
    m.start()
    first.credits = second.credits = 5000
    m.tick(1 / 64, {recipient.pid: Command(request="vandal")})
    purchase = Command(buy=[recipient.gift_action()])
    events = m.tick(1 / 64, {first.pid: purchase, second.pid: purchase})
    assert sorted((first.credits, second.credits)) == [2100, 5000]
    assert sum(event.kind == "buy" for event in events) == 1
    assert len(recipient.purchases) == 1 and not m.drops
    assert m.sell(recipient, "vandal")
    assert first.credits == second.credits == 5000


def test_refund_clears_request_for_restored_weapon() -> None:
    m = Match(load_archived_map("workyard"), seed=1)
    p = m.add_player("Buyer", 0, "omen")
    m.start()
    p.credits = 9000
    m.tick(1 / 64, {p.pid: Command(buy=["buy:vandal", "buy:phantom"])})
    m.tick(1 / 64, {p.pid: Command(request="vandal")})
    assert p.request == "vandal"
    m.tick(1 / 64, {p.pid: Command(buy=["sell:phantom"])})
    assert p.weapon.key == "vandal" and p.request == ""


def test_quick_mode_short_match() -> None:
    from gameplay.world import load_map

    m = Match(load_map("ascent"), seed=1)
    a = m.add_player("A", 0, "omen")
    b = m.add_player("B", 1, "killjoy")
    m.set_mode("quick")
    m.start()
    assert m.win_rounds == 5 and not m.overtime and int(m._r["half_after"]) == 4
    assert (a.ult_points, b.ult_points) == (2, 3)
    a.credits = b.credits = 0
    m._end_round(0, "test")
    assert (a.credits, b.credits) == (3000, 2400)
    m.round_no, m.score = 8, [4, 4]
    m.attacking_team = 1
    m._start_round()
    assert (a.credits, b.credits) == (5000, 5000) and m.attacking_team == 1
    m._end_round(0, "test")
    assert m.match_winner == 0


def test_deathmatch_respawns_and_kill_limit() -> None:
    from gameplay.world import load_playable_map

    m = Match(load_playable_map("ascent"), seed=1)
    a = m.add_player("A", 0, "jett").pid
    b = m.add_player("B", 1, "jett").pid
    m.set_mode("deathmatch")
    m.start()
    pa, pb = m.players[a], m.players[b]
    assert m.phase == "buy" and m.phase_time_left() == 20 and m.spike_carrier is None
    assert (pa.weapon.key, pa.armor_key, pa.armor_reserve) == ("classic", "regen_shield", 50)
    assert not m.buy(pa, "vandal")
    m.tick(0.05, {a: Command(buy=["tdm1:bandit", "tdm2:stinger", "tdm3:guardian", "tdm4:vandal"])})
    assert (pa.weapon.key, pa.armor, pa.credits) == ("bandit", 0, 0)
    m.time = m.phase_until
    m.tick(0.0, {})
    assert (m.phase, m.dm_stage, m.phase_time_left()) == ("live", 1, 75)
    pa.pos = Vec(m.world.width / 2, m.world.height / 2)
    assert not m.buy(pa, "tdm1:ghost")
    m.time = m.phase_until - 1
    stations = list(m.drops)
    pb.status_drain = 0.75
    pb.quiet_drop, pb.quiet_landing_at = True, m.time
    m._kill(pa, pb, "test", "head")
    assert m.drops == stations
    assert pa.ult_points == 3 and pb.ult_points == 0 and m.ultimate_cost(pa) == 70
    run(m, 1.4)
    assert not pb.alive and m.score[pa.team] == 1
    run(m, 0.2)
    assert pb.alive and (pb.weapon.key, pb.armor) == ("sheriff", 25)
    assert pb.status_drain == 0 and not pb.quiet_drop and pb.quiet_landing_at < 0
    assert not m.deathmatch_stage_equip_left(pb)
    assert pa.weapon.key == "bandit" and m.deathmatch_stage_equip_left(pa) > 0
    assert not m.buy(pa, "tdm:equip:3")
    m.tick(0, {a: Command(buy=["tdm:equip:2"])})
    assert (pa.weapon.key, pa.weapons["sidearm"].key, pa.armor) == ("stinger", "bandit", 50)
    pa.weapon.mag = 0
    reserve = pa.weapon.reserve
    m.tick(0.05, {a: Command(reload=True)})
    m.time = pa.reload_until
    m.tick(0.0, {})
    assert pa.weapon.mag == m.weapons["stinger"].mag and pa.weapon.reserve == reserve
    for stage, seconds, weapon, shield in ((3, 75, "guardian", 25), (4, 345, "vandal", 50)):
        m.time = m.phase_until
        m.tick(0.0, {})
        assert (m.dm_stage, m.phase_time_left(), m.deathmatch_stage_equip_left(pa)) == (stage, seconds, 5)
        m.time = pa.dm_stage_equip_until - 0.01
        m.tick(0, {})
        assert pa.weapon.key != weapon
        m.tick(0.01, {})
        assert (pa.weapon.key, pa.armor) == (weapon, shield)
    m.score[pa.team] = 99
    m._kill(pa, pb, "test", "head")
    assert m.phase == "over" and m.match_winner == pa.team


def test_deathmatch_respawn_ignores_ghosts_and_duelists_when_choosing_spawn() -> None:
    from gameplay.world import WorldMap

    near, far = Vec(5, 5), Vec(15, 5)
    world = WorldMap("test", "Test", 30, 30, spawns={0: [near, far], 1: [Vec(25, 25)]})
    m = Match(world)
    m.set_mode("deathmatch")
    player = m.add_player("Player", 0, "omen")
    enemy = m.add_player("Enemy", 1, "omen")
    ghost = m.add_player("Ghost", 1, "omen")
    duelist = m.add_player("Duelist", 1, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    enemy.pos = near
    ghost.pos, ghost.dm_ghost = far, True
    duelist.pos, duelist.duel_id = far, duelist.pid
    m._kill(enemy, player, "classic", "body")
    m.time += m.deathmatch_rules["respawn"]
    m.tick(0, {})
    assert player.alive and player.pos == far
    ally = m.add_player("Ally", 0, "omen")
    ally.pos = far
    enemy.pos = Vec(2, 5)
    m._kill(enemy, player, "classic", "body")
    m.time += m.deathmatch_rules["respawn"]
    m.tick(0, {})
    assert player.alive and player.pos == near


def test_deathmatch_sage_resurrection_takes_priority_over_respawn() -> None:
    from gameplay.world import load_playable_map

    m = Match(load_playable_map("haven"))
    m.set_mode("deathmatch")
    sage = m.add_player("Sage", 0, "sage")
    ally = m.add_player("Ally", 0, "clove")
    enemy = m.add_player("Enemy", 1, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    point = m._deathmatch_station_anchors[0]
    sage.pos = ally.pos = point
    sage.ground = ally.ground = m.world.ground_height(point)
    sage.ult_points = m.ultimate_cost(sage)
    ally.ult_points = m.ultimate_cost(ally)
    m._kill(enemy, ally, "classic", "body")
    assert m.can_cast_dead(ally, "X")
    m.tick(0, {sage.pid: Command(ability="X", cursor_depth=0)})
    assert not m.can_cast_dead(ally, "X")
    marker = next(e for e in m.effects if e.props.get("revive_pid") == ally.pid)
    m.time = ally.died_at + 1.6
    m.tick(0, {})
    assert not ally.alive
    m.time = marker.until
    m.tick(0, {})
    assert ally.alive and ally.pos == point and sage.ult_points == 0


def test_deathmatch_clove_ultimate_takes_priority_over_respawn() -> None:
    from gameplay.world import load_playable_map

    m = Match(load_playable_map("haven"))
    m.set_mode("deathmatch")
    clove = m.add_player("Clove", 0, "clove")
    sage = m.add_player("Sage", 0, "sage")
    enemy = m.add_player("Enemy", 1, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    death_pos = m._deathmatch_station_anchors[0]
    clove.pos = death_pos
    sage.pos = death_pos
    sage.ground = clove.ground = m.world.ground_height(death_pos)
    sage.ult_points = m.ultimate_cost(sage)
    clove.ult_points = m.ultimate_cost(clove)
    m.time = m.phase_until - 1
    m._kill(enemy, clove, "classic", "body")
    m.time = clove.died_at + 1
    clove.recharge_timers["E"] = 64.9375
    m.tick(0, {clove.pid: Command(ability="X")})
    m.tick(0.0625, {})
    assert clove.charges["E"] == 1
    assert clove.recharge_timers["E"] == 65
    m.tick(0, {sage.pid: Command(ability="X", cursor_depth=0)})
    assert sage.ult_points == m.ultimate_cost(sage)
    assert not any(e.props.get("revive_pid") == clove.pid for e in m.effects)
    m.time = clove.died_at + 1.6
    m.tick(0, {})
    assert not clove.alive
    m.time = clove.channel_until
    m.tick(0, {})
    assert clove.alive and clove.pos == death_pos and clove.ult_points == 0
    assert clove.status["clove_phase"] > m.time
    m.tick(0, {})
    assert clove.charges["E"] == 2
    assert m.dm_stage == 2 and m.deathmatch_stage_equip_left(clove) > 0
    m.time = clove.dm_stage_equip_until
    m.tick(0, {})
    assert clove.weapon.key == "sheriff"


def test_deathmatch_stage_upgrade_waits_for_ghost_exit() -> None:
    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    assert m.set_rules(allow_cheats=True)
    p = m.add_player("Player", 0, "omen")
    m.start()
    toggle = Command(buy=["tdm:toggle_ghost"])
    m.time = m.phase_until
    m.tick(0, {p.pid: toggle})
    assert p.dm_ghost
    m.time = m.phase_until
    m.tick(0, {})
    m.time = p.dm_stage_equip_until
    m.tick(0, {})
    assert p.weapon.key == "classic"
    m.tick(0, {p.pid: toggle})
    assert not p.dm_ghost and p.weapon.key == "sheriff"
    assert p.dm_stage_equip_until == 0


def test_deathmatch_stage_upgrade_waits_for_iso_duel_cleanup() -> None:
    from gameplay.world import load_playable_map

    m = Match(load_playable_map("haven"))
    m.set_mode("deathmatch")
    p = m.add_player("Iso", 0, "iso")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    p.duel_id = p.pid
    m.time = m.phase_until
    m.tick(0, {p.pid: Command(buy=["tdm:equip:2"])})
    assert m.dm_stage == 2 and p.weapon.key == "classic"
    station_weapon = m._new_weapon("shorty")
    station_weapon.from_station = True
    p.weapons["primary"] = station_weapon
    p.slot = "primary"
    m.tick(0, {p.pid: Command(drop=True)})
    assert p.weapon.key == "classic" and p.dm_stage_equip_until > m.time
    m.time = p.dm_stage_equip_until
    m.tick(0, {})
    assert p.weapon.key == "classic"
    p.duel_id = 0
    m.tick(0, {})
    assert p.weapon.key == "sheriff" and p.dm_stage_equip_until == 0


def test_deathmatch_respawn_waits_for_iso_duel_cleanup() -> None:
    from gameplay.world import load_playable_map

    m = Match(load_playable_map("haven"))
    m.set_mode("deathmatch")
    iso = m.add_player("Iso", 0, "iso")
    victim = m.add_player("Victim", 1, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    iso.duel_id = victim.duel_id = iso.pid
    iso.passive_state["iso_contract"] = (victim.pid, m.time + 15)
    assert not m.in_deathmatch_spawn(victim)
    assert not m.buy(victim, "tdm1:ghost")
    m._kill(iso, victim, "classic", "body")
    m.tick(0, {})

    m.time = victim.died_at + 1.6
    m.tick(0, {})
    assert not victim.alive and victim.duel_id == iso.pid
    m.time = victim.died_at + 2
    m.tick(0, {})
    assert victim.alive and victim.duel_id == 0
    assert m.deathmatch_spawn_protected(victim)
    assert m.score == [1, 0]


def test_deathmatch_ignores_extra_eliminations_after_winning_kill() -> None:
    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    killer = m.add_player("Killer", 0, "omen")
    first = m.add_player("First", 1, "omen")
    second = m.add_player("Second", 1, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    m.score = [99, 99]
    m._kill(killer, first, "classic", "body")
    m._kill(killer, second, "classic", "body")
    m._kill(second, killer, "classic", "body")
    assert m.phase == "over" and m.match_winner == 0
    assert m.score == [100, 99] and killer.alive and second.alive
    assert [event.kind for event in m.events] == ["kill", "round_end"]


def test_deathmatch_phoenix_return_keeps_new_stage_armor() -> None:
    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    phoenix = m.add_player("Phoenix", 0, "phoenix")
    m.start()
    assert m.buy(phoenix, "tdm2:stinger")
    m.time = m.phase_until
    m.tick(0, {})
    phoenix.pos = m._deathmatch_station_anchors[0]
    phoenix.ult_points = m.ultimate_cost(phoenix)
    m.time = m.phase_until - 1
    m.tick(0, {phoenix.pid: Command(ability="X")})
    marker = next(e for e in m.effects if "return_armor" in e.data)
    m.time = m.phase_until
    m.tick(0, {phoenix.pid: Command(buy=["tdm:equip:2"])})
    assert phoenix.armor_key == "heavy_armor"
    phoenix.hp_frac, phoenix.decay_pool, phoenix.status_drain = 0.5, 20, 0.75
    m.time = marker.until
    events = m.tick(0, {})
    assert any(e.kind == "ability_return" for e in events)
    assert phoenix.weapon.key == "stinger" and phoenix.armor_key == "heavy_armor"
    assert (phoenix.hp_frac, phoenix.decay_pool, phoenix.status_drain) == (0, 0, 0)


def test_deathmatch_phoenix_return_keeps_armor_after_same_stage_loadout_change() -> None:
    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    phoenix = m.add_player("Phoenix", 0, "phoenix")
    m.start()
    spawn = phoenix.pos
    m.time = m.phase_until
    m.tick(0, {})
    phoenix.pos = m._deathmatch_station_anchors[0]
    phoenix.ult_points = m.ultimate_cost(phoenix)
    m.tick(0, {phoenix.pid: Command(ability="X")})
    marker = next(e for e in m.effects if "return_armor" in e.data)
    phoenix.pos = spawn
    assert m.buy(phoenix, "tdm1:ghost")
    m.time = marker.until
    m.tick(0, {})
    assert phoenix.pos == marker.pos
    assert phoenix.weapon.key == "ghost" and phoenix.armor_key == "" and phoenix.armor_reserve == 0


def test_deathmatch_phoenix_return_stays_outside_duel() -> None:
    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    phoenix = m.add_player("Phoenix", 0, "phoenix")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    phoenix.pos = m._deathmatch_station_anchors[0]
    phoenix.ult_points = m.ultimate_cost(phoenix)
    m.tick(0, {phoenix.pid: Command(ability="X")})
    marker = next(e for e in m.effects if "return_armor" in e.data)
    phoenix.duel_id = phoenix.pid
    phoenix.pos = marker.pos + Vec(2, 0)
    m.time = marker.until
    events = m.tick(0, {})
    assert phoenix.pos != marker.pos and phoenix.duel_id == phoenix.pid
    assert not any(e.kind == "ability_return" for e in events)


def test_deathmatch_winning_ability_stops_remaining_effects() -> None:
    from gameplay.kit.dsl import on, step
    from gameplay.match import Effect
    from gameplay.world import WorldMap

    m = Match(WorldMap("test", "Test", 30, 30, spawns={0: [Vec(5, 10)], 1: [Vec(20, 10)]}))
    m.set_mode("deathmatch")
    owner = m.add_player("Owner", 0, "omen")
    victim = m.add_player("Victim", 1, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    victim.hp, victim.armor = 1, 0
    m.score = [99, 0]
    lethal = Effect("blast", owner.pid, owner.team, victim.pos, m.time, 2,
                    props={"triggers": [on("expire", [step("damage", amount=100)], who="enemies")]})
    pending = Effect("blast", owner.pid, owner.team, victim.pos, m.time, 2)
    m.effects.extend([lethal, pending])

    m.tick(0, {})

    assert m.phase == "over" and m.score == [100, 0]
    assert pending in m.effects


def test_deathmatch_winning_shot_stops_pellets_and_pickup() -> None:
    from gameplay.match import Drop
    from gameplay.world import WorldMap

    world = WorldMap("test", "Test", 30, 30, spawns={0: [Vec(5, 10)], 1: [Vec(20, 10)]})
    m = Match(world, seed=1)
    m.set_mode("deathmatch")
    shooter = m.add_player("Shooter", 0, "omen")
    victim = m.add_player("Victim", 1, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    victim.pos, victim.hp, victim.armor = Vec(6, 10), 1, 0
    shooter.weapons["primary"] = m._new_weapon("judge")
    shooter.slot = "primary"
    station = Drop("shorty", 2, 6, shooter.pos)
    m.drops = [station]
    m.score = [99, 0]

    events = m.tick(0, {shooter.pid: Command(facing=90, fire=True, interact=True)})
    assert m.phase == "over" and m.score == [100, 0]
    assert sum(event.kind == "shot" for event in events) == 1
    assert m.drops == [station] and shooter.weapon.key == "judge"


def test_deathmatch_healing_assist_waits_for_effect_end_and_expires() -> None:
    from gameplay.kit.builtins import e_heal
    from gameplay.kit.registry import Ctx

    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    healer = m.add_player("Sage", 0, "sage")
    killer = m.add_player("Ally", 0, "omen")
    enemy = m.add_player("Enemy", 1, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    killer.hp = 50
    ctx = Ctx(m, healer, healer.team, killer.pos, healer.pos, heading(0))
    e_heal(ctx, killer, {"amount": 50, "over": 5})
    run(m, 1)
    m._kill(killer, enemy, "classic", "body")
    assert healer.assists == 0
    run(m, 4)
    m._damage(healer, enemy, 50, "body", "classic")
    m._kill(killer, enemy, "classic", "body")
    assert healer.assists == 1
    run(m, 11)
    m._kill(killer, enemy, "classic", "body")
    assert healer.assists == 1


def test_deathmatch_damage_assist_threshold_and_window() -> None:
    for hits, death_at, expected in [
        ([(0, 10)], 0, 0), ([(0, 5), (2, 6)], 2, 1), ([(0, 11), (4, 1)], 5, 0), ([(0, 50)], 5, 1),
    ]:
        m = Match(load_archived_map("workyard"))
        m.set_mode("deathmatch")
        helper = m.add_player("Helper", 0, "omen")
        killer = m.add_player("Killer", 0, "omen")
        victim = m.add_player("Victim", 1, "omen")
        m.start()
        m.time = m.phase_until
        m.tick(0, {})
        start = m.time
        for seconds, amount in hits:
            m.time = start + seconds
            m._damage(helper, victim, amount, "body", "classic")
        m.time = start + death_at
        m._kill(killer, victim, "classic", "body")
        assert helper.assists == expected
        run(m, 1.6)
        m._kill(killer, victim, "classic", "body")
        assert helper.assists == expected


def test_deathmatch_kill_streak_resets_on_death_but_survives_stage_change() -> None:
    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    player = m.add_player("Player", 0, "omen")
    enemy = m.add_player("Enemy", 1, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    m._kill(player, enemy, "classic", "body")
    assert m.events[-1].data["streak"] == 1
    m.time = m.phase_until
    m.tick(0, {})
    m._kill(player, enemy, "classic", "body")
    assert m.events[-1].data["streak"] == 2
    m._kill(enemy, player, "classic", "body")
    run(m, 1.6)
    m._kill(player, enemy, "classic", "body")
    assert m.events[-1].data["streak"] == 1
    assert player.kills == 3 and m.score == [3, 1]


def test_deathmatch_spawn_blocks_combat_before_and_after_protection() -> None:
    from gameplay.world import load_playable_map

    m = Match(load_playable_map("haven"))
    m.set_mode("deathmatch")
    p = m.add_player("Jett", 0, "jett")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    mag = p.weapon.mag
    m.tick(0.02, {p.pid: Command(ability="E", fire=True)})
    assert p.charges["E"] == 1 and p.dash_armed_until == 0
    assert p.weapon.mag == mag
    m._kill(None, p, "test", "body")
    run(m, 1.6)
    m.tick(0.5, {})
    assert m.deathmatch_spawn_protected(p)
    mag = p.weapon.mag
    m.tick(0.02, {p.pid: Command(fire=True)})
    assert p.weapon.mag == mag
    m.time = p.dm_spawn_protected_until
    m.tick(0, {})
    assert not m.deathmatch_spawn_protected(p)
    m.tick(0.02, {p.pid: Command(ability="E", fire=True)})
    assert p.charges["E"] == 1 and p.dash_armed_until == 0
    assert p.weapon.mag == mag
    p.pos = m._deathmatch_station_anchors[0]
    m.tick(0, {})
    m.tick(0.02, {p.pid: Command(fire=True)})
    assert p.weapon.mag == mag - 1
    m.tick(0.02, {p.pid: Command(ability="E")})
    assert p.charges["E"] == 0 and p.dash_armed_until > m.time


def test_deathmatch_spawn_cancels_pending_weapon_burst() -> None:
    from gameplay.world import load_playable_map

    m = Match(load_playable_map("haven"))
    m.set_mode("deathmatch")
    p = m.add_player("Player", 0, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    home = p.pos
    outside = m._deathmatch_station_anchors[0]
    p.pos = outside
    p.weapons["primary"] = m._new_weapon("bulldog")
    p.slot, p.equip_until = "primary", 0.0
    assert any(e.kind == "shot" for e in m.tick(0.02, {p.pid: Command(alt_fire=True)}))
    assert p.burst_left == 2
    mag = p.weapon.mag

    p.pos = home
    assert not any(e.kind == "shot" for e in m.tick(0.1, {}))
    p.pos = outside
    assert not any(e.kind == "shot" for e in m.tick(0.1, {}))
    assert p.weapon.mag == mag


def test_deathmatch_spawn_blocks_harbor_tide_controls() -> None:
    from gameplay.match import Effect
    from gameplay.world import load_playable_map

    m = Match(load_playable_map("haven"))
    m.set_mode("deathmatch")
    p = m.add_player("Harbor", 0, "harbor")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    direction = heading(0)
    tide = Effect("marker", p.pid, p.team, p.pos, m.time + 10, 0,
                  props={"sprite": "harbor_current"}, data={"direction": direction})
    m.effects.append(tide)

    m.tick(0.1, {p.pid: Command(fire=True, facing=90)})
    m.tick(0.1, {p.pid: Command(alt_fire=True)})
    assert tide.data["direction"] == direction and not tide.data.get("stop")

    p.pos = m._deathmatch_station_anchors[0]
    p.ground = m.world.ground_height(p.pos)
    m.tick(0.1, {p.pid: Command(fire=True, facing=90)})
    assert tide.data["direction"] != direction
    m.tick(0.1, {p.pid: Command(alt_fire=True)})
    assert tide.data["stop"]


def test_deathmatch_spawn_blocks_manual_device_activation() -> None:
    from gameplay.match import Effect
    from gameplay.world import load_playable_map

    m = Match(load_playable_map("haven"))
    m.set_mode("deathmatch")
    p = m.add_player("Cypher", 0, "cypher")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    device = Effect("cage", p.pid, p.team, p.pos, m.time + 10, 1, props={"manual": True})
    m.effects.append(device)

    m.tick(0, {p.pid: Command(interact=True, cursor_depth=0)})
    assert device in m.effects and not device.props.get("ended")
    m.tick(0, {})
    p.pos = device.pos = m._deathmatch_station_anchors[0]
    p.ground = m.world.ground_height(p.pos)
    m.tick(0, {p.pid: Command(interact=True, cursor_depth=0)})
    assert device.props.get("ended")


def test_deathmatch_spawn_protection_does_not_consume_one_time_effect() -> None:
    from gameplay.kit.dsl import on, step
    from gameplay.match import Effect
    from gameplay.world import load_playable_map

    m = Match(load_playable_map("haven"))
    m.set_mode("deathmatch")
    owner = m.add_player("Owner", 0, "omen")
    target = m.add_player("Target", 1, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    target.dm_spawn_protected_until = m.time + 15
    trigger = on("tick", [step("damage", amount=10)], who="enemies", once_per_player=True)
    m.effects.append(Effect("blast", owner.pid, owner.team, target.pos, m.time + 20, 2,
                            props={"triggers": [trigger]}))
    target.armor = 0
    m.tick(0, {})
    assert target.hp == 100
    m.time = target.dm_spawn_protected_until
    m.tick(0, {})
    assert target.hp == 90
    m.tick(0, {})
    assert target.hp == 90


def test_deathmatch_alarmbot_drops_an_unreachable_target() -> None:
    from gameplay.kit.builtins import tr_chase
    from gameplay.kit.registry import Ctx
    from gameplay.match import Effect

    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    owner = m.add_player("Killjoy", 0, "killjoy")
    target = m.add_player("Target", 1, "omen")
    m.start()
    point = target.pos
    alarmbot = Effect("sensor", owner.pid, owner.team, point, m.time + 10, 3,
                      data={"chase_pid": target.pid})
    ctx = Ctx(m, owner, owner.team, point, owner.pos, heading(0), obj=alarmbot)
    spec = {"speed": 7.5, "blast_radius": 3, "first": True}

    target.dm_ghost = True
    assert tr_chase(ctx, spec) is None
    assert "chase_pid" not in alarmbot.data
    target.dm_ghost = False
    target.duel_id = target.pid
    alarmbot.data["chase_pid"] = target.pid
    assert tr_chase(ctx, spec) is None
    assert "chase_pid" not in alarmbot.data
    target.duel_id = 0
    assert tr_chase(ctx, spec) == [target]


def test_deathmatch_bot_device_activation_respects_ability_restrictions() -> None:
    from gameplay.match import Effect
    from gameplay.world import load_playable_map

    m = Match(load_playable_map("haven"))
    m.set_mode("deathmatch")
    bot = m.add_player("Cypher", 0, "cypher", is_bot=True)
    enemy = m.add_player("Enemy", 1, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    point = m._deathmatch_station_anchors[0]
    enemy.pos = point
    device = Effect("cage", bot.pid, bot.team, point, m.time + 10, 1,
                    props={"manual": True, "bot_trigger_radius": 3.5})
    m.effects.append(device)
    m.tick(0, {})
    assert not device.props.get("ended")
    bot.pos = point
    enemy.dm_ghost = True
    m.tick(0, {})
    assert not device.props.get("ended")
    enemy.dm_ghost = False
    enemy.pos = device.pos = m.world.spawns[1][0]
    enemy.dm_spawn_protected_until = m.time + 15
    m.tick(0, {})
    assert not device.props.get("ended")
    enemy.pos = device.pos = point
    bot.status["suppress"] = m.time + 1
    m.tick(0, {})
    assert not device.props.get("ended")
    m.time = bot.status["suppress"]
    enemy.duel_id = enemy.pid
    m.tick(0, {})
    assert not device.props.get("ended")
    enemy.duel_id = 0
    bot.duel_id = bot.pid
    m.tick(0, {})
    assert not device.props.get("ended")
    bot.duel_id = 0
    m.tick(0, {})
    assert device.props.get("ended")


def test_deathmatch_spawn_protection_on_both_sides() -> None:
    from gameplay.kit.statuses import apply_status
    from gameplay.world import load_playable_map

    m = Match(load_playable_map("haven"), seed=1)
    m.set_mode("deathmatch")
    a = m.add_player("A", 0, "omen")
    b = m.add_player("B", 1, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    for p in (a, b):
        assert not m.deathmatch_spawn_protected(p)
        m._kill(None, p, "test", "body")
    run(m, 1.6)
    for p, enemy in ((a, b), (b, a)):
        assert m.deathmatch_spawn_protected(p)
        m._damage(enemy, p, 50, "body", "classic")
        apply_status(m, p, "blind", 2)
        assert (p.hp, p.armor, p.blind_until) == (100, 25, 0)
    home = a.pos
    a.pos = m._deathmatch_station_anchors[0]
    m.tick(0, {})
    a.pos = home
    m.tick(0, {})
    assert not m.deathmatch_spawn_protected(a)
    m._damage(b, a, 50, "body", "classic")
    assert a.hp == 75
    deadline = b.dm_spawn_protected_until
    m.time = deadline - 0.01
    m.tick(0, {})
    assert b.hp == 100
    m.time = deadline + 0.05
    events = m.tick(0, {})
    assert (b.hp, b.armor, b.armor_reserve) == (90, 25, 50)
    assert b.dm_next_spawn_damage == deadline + 1
    assert any(e.kind == "hit" and e.data.get("source") == "spawn" for e in events)
    b.hp = 5
    m.time = b.dm_next_spawn_damage
    m.tick(0, {})
    assert not b.alive and m.score == [0, 0]


def test_deathmatch_bot_leaves_spawn_before_fighting() -> None:
    from gameplay.bots import BotBrain
    from gameplay.geometry import Rect
    from gameplay.world import WorldMap

    world = WorldMap("test", "Test", 30, 30, spawns={0: [Vec(5, 10)], 1: [Vec(20, 10)]},
                     spawn_zones={0: Rect(2, 6, 8, 14), 1: Rect(17, 6, 23, 14)})
    m = Match(world)
    m.set_mode("deathmatch")
    bot = m.add_player("Bot", 0, "omen", is_bot=True)
    enemy = m.add_player("Enemy", 1, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    bot.facing = 90
    brain = BotBrain(bot.pid, reaction=0)
    assert brain._visible_enemy(m, bot) is enemy
    cmd = brain.think(m, 0.1)
    assert cmd.move_y == 1 and not cmd.fire and cmd.ability is None

    bot.pos = Vec(10, 10)
    enemy.dm_spawn_protected_until = m.time + 15
    assert brain._visible_enemy(m, bot) is None
    enemy.pos = Vec(15, 10)
    assert brain.think(m, 0.1).fire
    enemy.dm_ghost = True
    cmd = brain.think(m, 0.1)
    assert not cmd.fire and not cmd.move_y and brain.goal is None
    enemy.dm_ghost = False
    assert brain.think(m, 0.1).fire
    enemy.duel_id = enemy.pid
    assert not brain.think(m, 0.1).move_y and brain.goal is None
    bot.duel_id = enemy.duel_id
    assert brain.think(m, 0.1).fire


def test_deathmatch_ghost_crosses_walls_and_cannot_fight() -> None:
    from gameplay.geometry import Rect
    from gameplay.world import Wall, WorldMap

    world = WorldMap("test", "Test", 30, 30, walls=[Wall(Rect(8, 1, 9, 29), 3)],
                     spawns={0: [Vec(5, 10)], 1: [Vec(20, 10)]})
    m = Match(world)
    m.set_mode("deathmatch")
    p = m.add_player("Player", 0, "omen")
    enemy = m.add_player("Enemy", 1, "omen")
    assert m.set_rules(allow_cheats=True)
    m.start()
    assert not m.can_toggle_deathmatch_ghost(p)
    assert m.end_deathmatch_phase()
    p.duel_id = enemy.pid
    m.tick(0, {p.pid: Command(buy=["tdm:toggle_ghost"])})
    assert not p.dm_ghost
    p.duel_id = 0
    m.tick(0, {p.pid: Command(buy=["tdm:toggle_ghost"])})
    assert p.dm_ghost
    mag = p.weapon.mag
    run(m, 1, {p.pid: Command(facing=0, move_x=1, jump=True, fire=True)})
    assert p.pos.x > 9 and p.z > 0 and p.weapon.mag == mag
    m._damage(enemy, p, 100, "body", "classic")
    assert p.hp == 100
    p.pos = Vec(8.5, 10)
    m.tick(0, {p.pid: Command(buy=["tdm:toggle_ghost"])})
    assert not p.dm_ghost and p.pos == Vec(5, 10) and p.z == 0
    m._damage(enemy, p, 30, "body", "classic")
    assert p.hp < 100


def test_deathmatch_custom_timer_pauses_without_stopping_respawns() -> None:
    m = Match(load_archived_map("workyard"), seed=1)
    m.set_mode("deathmatch")
    player = m.add_player("Player", 0, "omen")
    assert m.set_rules(allow_cheats=True)
    m.start()
    assert m.toggle_deathmatch_timer()
    run(m, 1)
    assert abs(m.phase_time_left() - 20) < 1e-6
    assert not m.recovery_orbs and m.dm_next_ultimate_wave == m.phase_until + 60
    assert m.end_deathmatch_phase() and not m.dm_timer_paused
    m.tick(0, {})
    assert m.toggle_deathmatch_timer()
    left = m.phase_time_left()
    m._kill(None, player, "test", "body")
    run(m, 1.6)
    assert player.alive and m.phase_time_left() == left
    assert m.toggle_deathmatch_timer()
    run(m, 1)
    assert m.phase_time_left() == left - 1


def test_deathmatch_custom_end_phase_reuses_stage_transitions() -> None:
    m = Match(load_archived_map("workyard"), seed=1)
    m.set_mode("deathmatch")
    player = m.add_player("Player", 0, "omen")
    assert not m.end_deathmatch_phase()
    assert m.set_rules(allow_cheats=True)
    m.start()
    assert m.end_deathmatch_phase()
    assert not m.end_deathmatch_phase()
    m.tick(0, {})
    assert m.phase == "live" and m.dm_stage == 1 and m.phase_time_left() == 75
    assert m.recovery_orbs and m.dm_next_ultimate_wave == m.time + 60
    assert m.dm_ends_at == m.time + 570
    for stage in (2, 3, 4):
        assert m.end_deathmatch_phase()
        m.tick(0, {})
        assert m.dm_stage == stage and m.deathmatch_stage_equip_left(player) > 0
    m.score = [3, 2]
    assert m.end_deathmatch_phase()
    events = m.tick(0, {})
    assert m.phase == "over" and m.match_winner == 0
    assert sum(e.kind == "round_end" for e in events) == 1
    assert not m.end_deathmatch_phase()


def test_deathmatch_surrender_finalizes_paused_timer() -> None:
    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    assert m.set_rules(allow_cheats=True)
    m.start()
    assert m.toggle_deathmatch_timer()
    assert m.surrender(0)
    assert not m.surrender(0)
    snap = m.snapshot()
    assert snap["phase"] == "over" and snap["winner"] == snap["round_winner"] == 1
    assert snap["dm_left"] == 0 and not m.dm_timer_paused
    assert snap["round_reason"] == "Surrendered"
    assert [event.kind for event in m.events].count("round_end") == 1


def test_deathmatch_time_limit_allows_draw() -> None:
    m = Match(load_archived_map("workyard"), seed=1)
    m.set_mode("deathmatch")
    m.start()
    for _ in range(4):
        m.time = m.phase_until
        m.tick(0.0, {})
    assert m.phase_until == m.dm_ends_at
    m.phase_until = m.dm_ends_at + 0.01
    m.time = m.dm_ends_at
    events = m.tick(0.0, {})
    assert m.phase == "over" and m.match_winner is None and m.score == [0, 0]
    assert events[-1].data["winner"] is None


def test_deathmatch_astra_stars_and_dissipate_recharge_separately() -> None:
    from gameplay.kit.engine import remove_device
    from gameplay.world import load_playable_map

    m = Match(load_playable_map("haven"))
    m.set_mode("deathmatch")
    p = m.add_player("Astra", 0, "astra")
    m.start()
    assert p.charges["E"] == 2 and m.ultimate_cost(p) == 90
    m.time = m.phase_until
    m.tick(0, {})
    p.pos = m._deathmatch_station_anchors[0]
    m.tick(0, {p.pid: Command(ability="X", points=[(p.pos.x, p.pos.y)])})
    assert p.charges["E"] == 1
    star = next(e for e in m.effects if e.props.get("sprite") == "astra_star")
    remove_device(m, star, "recall")
    m.time += 19
    m.tick(0, {})
    assert p.charges["E"] == 1
    m.time += 1
    m.tick(0, {})
    assert p.charges["E"] == 2
    p.recharge_timers["E"] = 35.875
    m.tick(0.0625, {})
    assert p.charges["E"] == 2
    m.tick(0.0625, {})
    assert p.charges["E"] == 3


def test_deathmatch_cooldowns_cover_the_playable_roster() -> None:
    from gameplay.match import playable_agents

    roster = playable_agents()
    m = Match(load_archived_map("workyard"), agent_roster=roster)
    rules = m.deathmatch_rules
    assert roster.keys() <= rules["ability_cooldowns"].keys()
    assert roster.keys() <= rules["ultimate_costs"].keys()
    chamber = m.add_player("Chamber", 0, "chamber")
    waylay = m.add_player("Waylay", 1, "waylay")
    regular_costs = [m.ultimate_cost(player) for player in (chamber, waylay)]
    m.set_mode("deathmatch")
    m.start()
    assert chamber.recharge_timers == {"C": 23, "Q": 4.5, "E": 25.5}
    assert waylay.recharge_timers == {"C": 27, "Q": 29, "E": 25.5}
    assert [m.ultimate_cost(player) for player in (chamber, waylay)] == [70, 60]
    m.time = m.phase_until
    m.tick(0, {})
    run(m, 4.5)
    assert chamber.charges["Q"] == 1 and waylay.charges["Q"] == 0
    run(m, 24.5)
    assert waylay.charges["C"] == waylay.charges["Q"] == 1
    assert chamber.charges["Q"] == 3
    m.set_mode("standard")
    assert [m.ultimate_cost(player) for player in (chamber, waylay)] == regular_costs


def test_deathmatch_skye_kayo_and_viper_recharge_on_their_mode_timers() -> None:
    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    skye = m.add_player("Skye", 0, "skye")
    kayo = m.add_player("KAY/O", 1, "kayo")
    viper = m.add_player("Viper", 1, "viper")
    assert skye.agent == "skye" and kayo.agent == "kayo"
    m.start()
    assert skye.recharge_timers == {"C": 32.5, "Q": 25.5, "E": 22}
    assert kayo.recharge_timers == {"C": 27, "Q": 22, "E": 29}
    assert viper.recharge_timers == {"C": 27, "Q": 22, "E": 40}
    assert [m.ultimate_cost(p) for p in (skye, kayo, viper)] == [70, 70, 90]
    m.time = m.phase_until
    m.tick(0, {})
    run(m, 22)
    assert skye.charges["Q"] == 0 and kayo.charges["Q"] == 1
    assert viper.charges["Q"] == 1 and viper.charges["C"] == 0
    run(m, 10.5)
    assert skye.charges["C"] == skye.charges["Q"] == kayo.charges["C"] == 1
    assert viper.charges["C"] == 1


def test_deathmatch_yoru_recharges_gatecrash_with_time() -> None:
    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    p = m.add_player("Yoru", 0, "yoru")
    enemy = m.add_player("Enemy", 1, "omen")
    assert p.agent == "yoru"
    m.start()
    assert p.recharge_timers == {"C": 29, "Q": 22, "E": 25.5}
    assert m.ultimate_cost(p) == 60
    m.time = m.phase_until
    m.tick(0, {})
    for _ in range(2):
        m._kill(p, enemy, "classic", "body")
        run(m, 1.6)
    assert p.charges["E"] == 1
    run(m, 22.4)
    assert p.charges["E"] == 2 and p.credits == 0


def test_deathmatch_neon_recharges_without_credits() -> None:
    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    p = m.add_player("Neon", 0, "neon")
    assert p.agent == "neon"
    m.start()
    assert p.recharge_timers == {"C": 22, "Q": 24, "E": 18}
    assert m.ultimate_cost(p) == 60
    m.time = m.phase_until
    m.tick(0, {})
    run(m, 22)
    assert p.charges["C"] == 1 and p.charges["Q"] == 0
    run(m, 2)
    assert p.charges["Q"] == 1 and p.credits == 0


def test_deathmatch_abilities_recharge_without_buying() -> None:
    m = Match(load_archived_map("workyard"), seed=1)
    m.set_mode("deathmatch")
    p = m.add_player("Omen", 0, "omen")
    m.start()
    assert (p.charges["C"], p.charges["Q"], p.charges["E"]) == (0, 0, 1)
    m.time = m.phase_until
    m.tick(0.0, {})
    run(m, 16.6)
    assert p.charges["C"] == 1 and p.charges["Q"] == 0
    run(m, 16.0)
    assert p.charges["E"] == 2


def test_recall_uses_mode_delay_and_does_not_restore_the_charge_early() -> None:
    for mode, delay in (("deathmatch", 5), ("standard", 20), ("quick", 20)):
        m = Match(load_archived_map("workyard"), seed=1)
        m.set_mode(mode)
        player = m.add_player("Killjoy", 0, "killjoy")
        m.start()
        m.time = m.phase_until
        m.tick(0, {})
        player.pos = Vec(17, 8)
        m.tick(0, {player.pid: Command(ability="E", facing=0, cursor_depth=2)})
        turret = next(e for e in m.effects if e.props.get("key") == "E")
        assert player.charges["E"] == 0
        if mode == "deathmatch":
            player.recharge_timers["E"] = 35.99
        m.tick(0.05, {player.pid: Command(interact=True, facing=0, cursor_depth=0)})
        assert turret not in m.effects
        ready = m.time + delay
        m.time = ready - 0.01
        m.tick(0, {})
        assert player.charges["E"] == 0
        m.time = ready
        m.tick(0, {})
        assert player.charges["E"] == 1
        m.tick(0.1, {})
        assert player.charges["E"] == 1


def test_deathmatch_orb_zones_only_credit_players_while_active() -> None:
    from gameplay.match import Effect
    from gameplay.world import WorldMap

    m = Match(WorldMap("test", "Test", 30, 30))
    m.set_mode("deathmatch")
    p = m.add_player("Player", 0, "omen")
    p.pos = Vec(10, 10)
    m.time = 20
    m.dm_next_ultimate_wave = 60
    m.effects = [
        Effect("tdm_ultimate", p.pid, p.team, p.pos, 26, 2, start=21),
        Effect("tdm_ultimate", p.pid, p.team, p.pos, 20, 2, start=15),
        Effect("tdm_ultimate", p.pid, p.team, p.pos, 26, 2, props={"ended": True}),
    ]
    m._tick_deathmatch_orbs(0)
    assert p.ult_points == 0
    m.time = 21
    m._tick_deathmatch_orbs(0)
    assert p.ult_points == 10


def test_deathmatch_ultimate_orbs_spawn_together_and_credit_allies_once() -> None:
    from gameplay.world import load_playable_map

    m = Match(load_playable_map("haven"), seed=1)
    m.set_mode("deathmatch")
    collector = m.add_player("Collector", 0, "omen")
    teammate = m.add_player("Teammate", 0, "sage")
    enemy = m.add_player("Enemy", 1, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    first_wave = m.dm_next_ultimate_wave
    m.time = first_wave - 0.01
    m.tick(0, {})
    assert not m.orbs
    m.time = first_wave
    m.tick(0, {})
    assert len(m.orbs) == 2
    point = m.orbs[0]
    collector_home = collector.pos
    teammate_home = teammate.pos

    def touch(player):
        player.pos, player.ground = point, m.world.ground_height(point)

    touch(collector)
    touch(enemy)
    collector.duel_id = enemy.duel_id = enemy.pid
    m.tick(0, {})
    assert point in m.orbs and collector.ult_points == enemy.ult_points == 0
    collector.duel_id = enemy.duel_id = 0
    collector.pos = point + Vec(0.5, 0)
    m.tick(0, {})
    assert point not in m.orbs and enemy.ult_points == 10 and collector.ult_points == 0
    m.orbs.append(point)
    touch(collector)
    enemy.pos = point + Vec(0.5, 0)
    m.tick(0, {})
    assert point not in m.orbs and collector.ult_points == 10 and enemy.ult_points == 10
    collector.pos = collector_home
    teammate.ult_points = m.ultimate_cost(teammate) - 3
    touch(teammate)
    m.tick(0.1, {})
    assert teammate.ult_points == m.ultimate_cost(teammate)
    teammate.pos = teammate_home
    m.tick(0.1, {})
    teammate.ult_points = 0
    touch(teammate)
    m.tick(0.1, {})
    assert teammate.ult_points == 0
    m.time = first_wave + m.deathmatch_rules["ultimate_orbs"]["duration"]
    m.tick(0, {})
    assert not any(zone.kind == "tdm_ultimate" for zone in m.effects)

    enemy.pos = m.world.spawns[1][0]
    teammate.pos = teammate_home
    m.time = m.phase_until
    m.tick(0, {})
    assert len(m.orbs) == 1
    m.time = m.dm_next_ultimate_wave
    m.tick(0, {})
    assert len(m.orbs) == 2 and point in m.orbs


def test_deathmatch_recovery_orb_discards_fraction_at_full_health_and_armor() -> None:
    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    player = m.add_player("Player", 0, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    player.hp, player.armor = 99, 24
    player.dm_recovery_armor_frac = 0.75
    player.dm_recovery_until = m.time + 6
    m.tick(0.1, {})
    assert (player.hp, player.armor) == (100, 25)
    assert player.dm_recovery_hp_frac == player.dm_recovery_armor_frac == 0

    # Another effect can fill health while orb recovery is paused by damage.
    player.hp, player.armor = 100, 24
    player.dm_recovery_hp_frac = player.dm_recovery_armor_frac = 0.5
    player.dm_recovery_paused_until = m.time + 1
    m.tick(0.1, {})
    assert player.dm_recovery_hp_frac == 0
    assert player.dm_recovery_armor_frac == 0.5


def test_deathmatch_recovery_orb_shares_remaining_time_and_respawns() -> None:
    from gameplay.world import load_playable_map

    m = Match(load_playable_map("haven"), seed=1)
    m.set_mode("deathmatch")
    collector = m.add_player("Collector", 0, "omen")
    teammate = m.add_player("Teammate", 0, "omen")
    enemy = m.add_player("Enemy", 1, "omen")
    m.start()
    assert not m.recovery_orbs
    m.time = m.phase_until
    m.tick(0, {})
    point = m.recovery_orbs[0]
    collector_home, teammate_home, enemy_home = collector.pos, teammate.pos, enemy.pos

    def touch(player):
        player.pos = point
        player.ground = m.world.ground_height(point)

    touch(collector)
    m.tick(0, {})
    assert point in m.recovery_orbs
    collector.hp, collector.armor, collector.armor_reserve = 10, 0, 7
    m.tick(0, {})
    expiry = m.time + 6
    assert point not in m.recovery_orbs and collector.dm_recovery_until == expiry
    assert collector.hp == 10 and collector.armor == 0
    collector.pos = collector_home
    touch(enemy)
    enemy.hp = 50
    run(m, 2)
    assert collector.hp > 10 and collector.armor > 0 and enemy.hp == 50
    teammate.hp = 5
    touch(teammate)
    m.tick(0, {})
    assert teammate.dm_recovery_until == expiry
    m._damage(enemy, teammate, 5, "body", "test")
    before = teammate.hp
    run(m, 1)
    assert teammate.hp == before
    run(m, 3)
    assert (collector.hp, collector.armor, collector.armor_reserve) == (100, 25, 7)
    assert before < teammate.hp < 100 and enemy.hp == 50
    assert all(effect.kind != "tdm_recovery" for effect in m.effects)
    teammate.pos = teammate_home
    enemy.pos = enemy_home
    ready_at = m.dm_recovery_orbs[point]
    m.time = ready_at - 0.01
    m.tick(0, {})
    assert point not in m.recovery_orbs
    m.tick(0.02, {})
    assert point in m.recovery_orbs

    m.time = m.phase_until - 1
    touch(collector)
    collector.armor = 10
    m.tick(0, {})
    assert point not in m.recovery_orbs
    ready_at = m.dm_recovery_orbs[point]
    m.time = m.phase_until
    m.tick(0, {})
    assert m.dm_stage == 2 and m.dm_recovery_orbs[point] == ready_at


def test_deathmatch_reserve_does_not_refill_chamber_ability_weapons() -> None:
    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    p = m.add_player("Chamber", 0, "chamber")
    assert m.set_rules(allow_cheats=True, infinite_magazines=True)
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    p.pos = m.drops[0].pos
    p.charges["Q"] = 2
    p.ult_points = m.ultimate_cost(p)
    for slot in ("Q", "X"):
        assert m._use_ability(p, slot)
        weapon = p.weapon
        assert weapon.key in m.ability_weapons
        weapon.mag -= 1
        remaining = weapon.mag
        m.tick(0.05, {p.pid: Command(reload=True)})
        assert p.reload_until == 0 and weapon.mag == remaining and weapon.reserve == 0


def test_deathmatch_stage_upgrade_preserves_equipped_ability_weapons() -> None:
    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    chamber = m.add_player("Chamber", 0, "chamber")
    jett = m.add_player("Jett", 1, "jett")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    for player in (chamber, jett):
        player.pos = m.drops[0].pos
        player.ult_points = m.ultimate_cost(player)
        assert m._use_ability(player, "X")
    weapon = chamber.weapon
    blades = jett.blade_count
    m.time = m.phase_until
    m.tick(0, {})
    m.time = chamber.dm_stage_equip_until
    chamber.hp = 99
    chamber.dm_recovery_armor_frac = 0.75
    chamber.dm_recovery_hp_frac = 0.5
    chamber.dm_recovery_until = m.time + 1
    m.tick(0, {})
    assert chamber.slot == "ability" and chamber.weapon is weapon
    assert chamber.dm_recovery_armor_frac == 0 and chamber.dm_recovery_hp_frac == 0.5
    assert jett.blades_equipped and jett.blade_count == blades
    assert all(p.weapons["primary"].key == "sheriff" for p in (chamber, jett))
    m._holster_ability_weapon(chamber)
    assert chamber.weapon.key == "sheriff"


def test_deathmatch_holsters_headhunter_to_sidearm_while_primary_is_jammed() -> None:
    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    p = m.add_player("Chamber", 0, "chamber")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    p.pos = m.drops[0].pos
    p.ground = m.world.ground_height(p.pos)
    m.tick(0, {p.pid: Command(interact=True)})
    primary = p.weapon
    assert primary.from_station
    p.charges["Q"] = 1
    m.tick(0, {p.pid: Command(ability="Q")})
    assert p.slot == "ability"
    m.time = p.equip_until
    p.status["vyse_jammed"] = m.time + 1
    m.tick(0, {p.pid: Command(fire=True)})
    assert p.slot == "sidearm" and p.weapons["primary"] is primary
    assert p.charges["Q"] == 0


def test_deathmatch_infinite_magazines_keeps_station_weapon_and_requires_reload() -> None:
    m = Match(load_archived_map("workyard"), seed=1)
    m.set_mode("deathmatch")
    assert m.set_rules(allow_cheats=True, infinite_magazines=True)
    player = m.add_player("Player", 0, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    station = m.drops[0]
    player.pos, player.ground = station.pos, m.world.ground_height(station.pos)
    m.tick(0, {player.pid: Command(interact=True)})
    weapon = player.weapon
    assert weapon is not None and weapon.from_station
    weapon.mag, weapon.reserve = 1, 0
    m.time = player.equip_until
    m.tick(0, {player.pid: Command(fire=True)})
    assert player.weapon is weapon and weapon.mag == 0
    m.tick(0, {player.pid: Command(reload=True)})
    assert player.reload_until > m.time
    m.time = player.reload_until
    m.tick(0, {})
    assert weapon.mag == m.weapons[weapon.key].mag and weapon.reserve == 0


def test_deathmatch_station_respects_full_wall_with_raised_base() -> None:
    from gameplay.geometry import Rect
    from gameplay.match import Drop
    from gameplay.world import Wall, WorldMap

    wall = Wall(Rect(10.4, 9, 10.6, 11), 3, base=1, blocks_sight=False)
    world = WorldMap("test", "Test", 30, 30, walls=[wall])
    m = Match(world)
    m.set_mode("deathmatch")
    p = m.add_player("Player", 0, "omen")
    m.phase = "live"
    p.pos = Vec(10, 10)
    station = Drop("shorty", 2, 6, Vec(11, 10))
    m.drops = [station]
    assert m._deathmatch_station_in_reach(p) is None
    assert not m._deathmatch_orb_in_reach(p, station.pos, 1.2)
    world.walls[0] = Wall(wall.rect, 3, base=1, blocks_sight=False, on_deck=True)
    assert m._deathmatch_station_in_reach(p) is station
    assert m._deathmatch_orb_in_reach(p, station.pos, 1.2)
    p.pos = station.pos
    assert m._deathmatch_station_in_reach(p) is station
    assert m._deathmatch_orb_in_reach(p, station.pos, 1.2)


def test_deathmatch_pickups_respect_platforms() -> None:
    from gameplay.geometry import Rect
    from gameplay.match import Drop
    from gameplay.world import Deck, WorldMap

    point = Vec(10, 10)
    world = WorldMap("test", "Test", 30, 30, decks=[Deck(Rect(9, 9, 12, 12), 1, 0)])
    m = Match(world)
    m.set_mode("deathmatch")
    p = m.add_player("Player", 0, "omen")
    m.phase = "live"
    station = Drop("shorty", 2, 6, point)
    m.drops = [station]
    p.pos, p.ground, p.z = point, 0, 0.5
    assert m._deathmatch_station_in_reach(p) is None
    assert not m._deathmatch_orb_in_reach(p, point, 1.2)

    p.ground, p.z, p.level = 1, 0, 1
    farther = Drop("sheriff", 6, 12, point + Vec(1, 0))
    m.drops = [farther, station]
    assert m._deathmatch_station_in_reach(p) is station
    assert m._deathmatch_orb_in_reach(p, point, 1.2)
    p.dm_ghost = True
    assert m._deathmatch_station_in_reach(p) is None
    p.dm_ghost = False
    p.duel_id = p.pid
    assert m._deathmatch_station_in_reach(p) is None


def test_deathmatch_stage_upgrade_keeps_sidearm_while_primary_is_jammed() -> None:
    m = Match(load_archived_map("workyard"))
    m.set_mode("deathmatch")
    p = m.add_player("Player", 0, "omen")
    m.start()
    m.time = m.phase_until
    m.tick(0, {})
    m.time = m.phase_until
    m.tick(0, {})
    m.time = p.dm_stage_equip_until
    p.status["vyse_jammed"] = m.time + 1
    m.tick(0, {})
    assert p.weapons["primary"].key == "sheriff" and p.slot == "sidearm"
    m.time += 1
    m.tick(0, {p.pid: Command(slot="primary")})
    assert p.slot == "primary"
    loadout = p.weapon
    station = m._new_weapon("shorty")
    station.from_station = True
    p.dm_stowed_primary = loadout
    p.weapons["primary"] = station
    p.status["vyse_jammed"] = m.time + 1
    m.tick(0, {p.pid: Command(drop=True)})
    assert p.weapons["primary"] is loadout and p.slot == "sidearm"
    station_point = m.drops[0].pos
    p.pos, p.ground = station_point, m.world.ground_height(station_point)
    p.weapon.mag = 1
    m.tick(0, {p.pid: Command(reload=True)})
    reload_until = p.reload_until
    assert reload_until > m.time
    m.tick(0, {p.pid: Command(interact=True)})
    assert p.weapons["primary"].from_station and p.slot == "sidearm"
    assert p.reload_until == reload_until


def test_deathmatch_weapon_station_ammo_and_lifecycle() -> None:
    from gameplay.world import load_playable_map

    m = Match(load_playable_map("haven"), seed=1)
    m.set_mode("deathmatch")
    a = m.add_player("A", 0, "omen")
    b = m.add_player("B", 1, "omen")
    m.start()
    assert not m.drops
    m.time = m.phase_until
    m.tick(0.0, {})
    assert {drop.key for drop in m.drops} == {"shorty", "sheriff", "stinger"}
    station = m.drops[0]
    a.pos = b.pos = station.pos
    a.ground = b.ground = m.world.ground_height(station.pos)
    m.tick(0.0, {})
    assert station in m.drops and a.weapon.key == "classic"
    m.tick(0.0, {a.pid: Command(interact=True), b.pid: Command(interact=True)})
    temporary = a.weapon
    assert station not in m.drops and temporary.from_station and b.weapon.key == "classic"
    assert (temporary.mag, temporary.reserve) == (station.mag, station.reserve)
    temporary.mag = 0
    m.tick(0.0, {a.pid: Command(reload=True)})
    m.time = a.reload_until
    m.tick(0.0, {})
    assert (temporary.mag, temporary.reserve) == (station.mag, station.reserve - station.mag)

    m.time = m.phase_until
    m.tick(0.0, {})
    assert a.weapon is temporary and m.dm_stage == 2 and len(m.drops) == 3
    assert {drop.key for drop in m.drops} <= {"bucky", "spectre", "bulldog", "marshal"}
    m.time = a.dm_stage_equip_until
    m.tick(0.0, {})
    assert a.weapon is temporary and not m.deathmatch_stage_equip_left(a)
    temporary.mag, temporary.reserve = 1, 0
    m.tick(0.0, {a.pid: Command(fire=True)})
    assert a.weapon.key == "sheriff" and not a.weapon.from_station
    a.weapon.mag = 2
    next_station = m.drops[0]
    a.pos, a.ground = next_station.pos, m.world.ground_height(next_station.pos)
    m.tick(0.0, {a.pid: Command(interact=True)})
    assert a.weapon.from_station
    m.tick(0.0, {a.pid: Command(drop=True)})
    assert a.weapon.key == "sheriff" and a.weapon.mag == 2 and next_station not in m.drops
    a.pos = m.drops[0].pos
    a.ground = m.world.ground_height(a.pos)
    m.tick(0.0, {a.pid: Command(interact=True)})
    assert a.weapon.from_station
    remaining = list(m.drops)
    m._kill(b, a, "test", "body")
    assert not a.weapon.from_station and m.drops == remaining
    run(m, 1.6)
    assert a.alive and a.weapon.key == "sheriff" and not a.weapon.from_station
    assert not a.prev_interact

    next_station = m.drops[0]
    a.pos, a.ground = next_station.pos, m.world.ground_height(next_station.pos)
    m.tick(0, {a.pid: Command(interact=True)})
    assert a.weapon.from_station
    m.time = m.phase_until
    m.tick(0, {a.pid: Command(buy=["tdm:equip:3"])})
    assert a.weapon.key == "spectre" and not a.weapon.from_station
