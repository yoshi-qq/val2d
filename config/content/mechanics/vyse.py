"""Vyse's surface traps, movement damage and primary-weapon jam."""
from gameplay.geometry import Rect, Vec
from gameplay.kit import statuses
from gameplay.kit.builtins import e_sound, select
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place, remove_device
from gameplay.kit.registry import effect
from gameplay.world import Wall


def _surface(ctx):
    reach = ctx.ability["range"]
    hit = None
    for wall in ctx.m.active_sight_walls(ctx.owner.level):
        interval = wall.rect.ray_interval(ctx.source, ctx.aim)
        if interval and interval[0] <= reach and (hit is None or interval[0] < hit[0]):
            hit = (*interval, wall.rect)
    if hit is None or abs((ctx.point - ctx.source).length() - hit[0]) > 1.25:
        return None
    entry, exit, rect = hit
    contact = ctx.source + ctx.aim * entry
    if min(abs(contact.x - rect.x0), abs(contact.x - rect.x1)) < 1e-5:
        normal = Vec(-1 if ctx.aim.x > 0 else 1, 0)
    else:
        normal = Vec(0, -1 if ctx.aim.y > 0 else 1)
    if ctx.ability.get("through_surface"):
        return (ctx.source + ctx.aim * (exit + 0.3), normal * -1) if exit - entry <= 10 else None
    return contact + normal * 0.3, normal


def _eligible(ctx, player):
    return player.immune_until <= ctx.m.time and not statuses.flag(ctx.m, player, "intangible")


@effect("vyse_nest", per_player=False)
def nest(ctx, _player, _spec):
    place(ctx, thing("sensor", delay=0.75, lasts=3600, radius=0.35, hp=20, hit_radius=0.35,
                     sprite="vyse_nest", hidden="enemies", detect_range=3.5, owner_range=float("inf"),
                     manual=True, bot_trigger_radius=6.25,
                     triggers=[on("activate", [step("vyse_vines")])]), ctx.point)


@effect("vyse_vines", per_player=False)
def vines(ctx, _player, _spec):
    place(ctx, thing("zone", delay=0.2, lasts=5.8, radius=6.25, sprite="vyse_vines", warning_sprite="vyse_vines",
                     triggers=[on("tick", [step("vyse_vine_contact")])]), ctx.point)


@effect("vyse_vine_contact", per_player=False)
def vine_contact(ctx, _player, _spec):
    for player in select(ctx, {"who": "everyone"}):
        if not _eligible(ctx, player) or abs(player.level - ctx.obj.props["source_level"]) > 1:
            continue
        if player.passive_state.get("vyse_vine_frame") == ctx.m.time:
            continue
        previous = player.passive_state.get("vyse_vine_frame", -1)
        player.passive_state["vyse_vine_frame"] = ctx.m.time
        statuses.apply_status(ctx.m, player, "vyse_vine_slow", 0.08)
        distance = player.passive_state.get("vyse_vine_distance", 0) if ctx.m.time - previous <= ctx.dt * 1.5 else 0
        distance += player.vel.length() * ctx.dt
        ticks = int(distance / 1.25)
        player.passive_state["vyse_vine_distance"] = distance - ticks * 1.25
        if ticks:
            ctx.m._damage(ctx.owner, player, ticks * 10, "legs", "ability:Razorvine")


@effect("vyse_shear", per_player=False)
def shear(ctx, _player, _spec):
    surface = _surface(ctx)
    if surface is None:
        return False
    point, direction = surface
    end = ctx.m._clip_to_walls(point, point + direction * 12, ctx.owner.level)
    if (end - point).length() < 1:
        return False
    trap = place(ctx, thing("zone", delay=2, lasts=3600, radius=0.35, sprite="vyse_shear_trap", hidden="enemies",
                            owner_range=float("inf"), blocks_sight=False,
                            triggers=[on("tick", [step("vyse_shear_watch")])]), (point + end) * 0.5)
    trap.a, trap.b = point, end


@effect("vyse_shear_watch", per_player=False)
def shear_watch(ctx, _player, _spec):
    trap = ctx.obj
    occupants = {p.pid for p in select(ctx, {"area": "strip", "width": 1})
                 if _eligible(ctx, p) and p.level == trap.props["source_level"]}
    previous = trap.data.get("occupants", set())
    if previous - occupants:
        wall = place(ctx, thing("wall", lasts=6, sprite="vyse_shear_wall"), trap.pos)
        wall.a, wall.b = trap.a, trap.b
        wall.props["barrier"] = Wall(Rect(min(wall.a.x, wall.b.x) - 0.35, min(wall.a.y, wall.b.y) - 0.35,
                                         max(wall.a.x, wall.b.x) + 0.35, max(wall.a.y, wall.b.y) + 0.35),
                                     3, base=trap.props["source_level"], on_deck=trap.props["source_level"] > 0)
        e_sound(ctx, None, {"key": "cast_shield_up", "radius": 24, "range_filtered": True})
        trap.props["ended"] = True
    elif occupants - previous:
        e_sound(ctx, None, {"key": "cast_tech", "radius": 15, "range_filtered": True, "team": 1 - ctx.team})
    trap.data["occupants"] = occupants


@effect("vyse_rose", per_player=False)
def rose(ctx, _player, _spec):
    if statuses.has(ctx.m, ctx.owner, "vyse_rose_ready"):
        obj = next((e for e in ctx.m.effects if e.owner == ctx.owner.pid and e.props.get("sprite") == "vyse_rose"
                    and not e.props.get("ended")), None)
        if obj is None or ctx.m.time < obj.start or obj.data.get("flash_at") is not None:
            return False
        obj.data["flash_at"] = ctx.m.time + 0.5
        obj.props["hidden"] = None
        obj.props.pop("recall_recharge", None)
        obj.props.pop("owner_range", None)
        e_sound(ctx, None, {"key": "cast_charge_up", "radius": 20, "range_filtered": True})
        return
    surface = _surface(ctx)
    if surface is None:
        return False
    point, _ = surface
    if not (0 <= point.x <= ctx.m.world.width and 0 <= point.y <= ctx.m.world.height):
        return False
    obj = place(ctx, thing("sensor", delay=0.8, lasts=3600, radius=0.4, hp=20, hit_radius=0.4,
                           sprite="vyse_rose", hidden="enemies", detect_range=10, owner_range=float("inf"),
                           recall_recharge=20, destroy_recharge=60, on_remove="vyse_rose_removed",
                           triggers=[on("tick", [step("vyse_rose_tick")])]), point)
    obj.props["recall_range"] = 32.5
    statuses.apply_status(ctx.m, ctx.owner, "vyse_rose_ready", 3600)


@effect("vyse_rose_removed", per_player=False)
def rose_removed(ctx, _player, _spec):
    if ctx.owner is not None:
        ctx.owner.status.pop("vyse_rose_ready", None)


@effect("vyse_rose_tick", per_player=False)
def rose_tick(ctx, _player, _spec):
    if ctx.m.time < ctx.obj.data.get("flash_at", float("inf")):
        return
    for player in select(ctx, {"who": "everyone", "radius": 40, "facing": "view", "sight": "all"}):
        if _eligible(ctx, player):
            statuses.apply_status(ctx.m, player, "blind", 2)
    e_sound(ctx, None, {"key": "cast_burst", "radius": 30, "range_filtered": True})
    ctx.obj.props["recall_recharge"] = 20
    remove_device(ctx.m, ctx.obj, "recall")


@effect("vyse_jam")
def jam(ctx, player, _spec):
    if _eligible(ctx, player):
        statuses.apply_status(ctx.m, player, "vyse_jammed", 8)
        if player.slot == "primary":
            ctx.m._select_equipment(player, "sidearm" if "sidearm" in player.weapons else "melee")
