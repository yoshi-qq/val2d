"""Waylay's movement, return beacon and expanding ultimate."""
from collections import deque

from gameplay.geometry import Vec
from gameplay.kit import statuses
from gameplay.kit.builtins import select
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place
from gameplay.kit.registry import effect, trigger
from gameplay.nav import NavGrid, grid_for

READY = "waylay_refract_ready"
TRANSIT = "waylay_refract_transit"
BEACON_READY = 1.0
BEACON_LIFETIME = 9.0


@effect("waylay_equip_lock", per_player=False)
def equip_lock(ctx, _player, spec):
    ctx.owner.equip_until = max(ctx.owner.equip_until, ctx.m.time + spec["seconds"])


@effect("waylay_hinder")
def hinder(ctx, player, spec):
    if not statuses.flag(ctx.m, player, "intangible"):
        statuses.apply_status(ctx.m, player, "waylay_hinder", spec["seconds"])


@effect("waylay_lightspeed", per_player=False)
def lightspeed(ctx, _player, spec):
    player = ctx.owner
    duration = 0.45 * spec["count"]
    player.dash_vel = ctx.aim * 20
    player.dash_until = player.channel_until = ctx.m.time + duration
    player.vel = player.dash_vel * statuses.mult(ctx.m, player, "dash_speed")
    equip_lock(ctx, None, {"seconds": duration})
    if player.vz > 0:
        player.vz = float(ctx.m._mv["gravity"]) * 0.45
    statuses.apply_status(ctx.m, player, "waylay_lightstep", duration)
    player.passive_state["waylay_protected_landing"] = True
    place(ctx, thing("none", lasts=duration, hidden="all",
                     triggers=[on("expire", [step("waylay_dash_end")])]), player.pos)


@effect("waylay_dash_end", per_player=False)
def dash_end(ctx, _player, _spec):
    player = ctx.owner
    if player is not None and player.dash_until == ctx.obj.until:
        player.vel = Vec(0, 0)
        if player.z <= 0.001:
            player.passive_state.pop("waylay_protected_landing", None)


def _return_path(match, player, beacon):
    inactive = frozenset(match.open_doors | match.broken_cover)
    extra = tuple(match.ability_walls())
    grid = (NavGrid(match.world, inactive, extra, buy_phase=True) if match.phase == "buy"
            else grid_for(match.world, inactive, extra))
    level_height = float(match._mv["level_height"])
    start = player.ground / level_height
    goal = beacon.data["ground"] / level_height
    if grid.line_free(player.pos, beacon.pos, start, goal):
        return [beacon.pos]
    return grid.path(player.pos, beacon.pos, start_ground=start, goal_ground=goal)


@effect("waylay_refract", per_player=False)
def refract(ctx, _player, _spec):
    player, match = ctx.owner, ctx.m
    beacon = next((e for e in match.effects if e.owner == player.pid and e.data.get("waylay_beacon")
                   and not e.props.get("ended") and player.died_at < e.start - BEACON_READY
                   and e.until > match.time), None)
    if beacon is None:
        beacon = place(ctx, thing("zone", delay=BEACON_READY, lasts=BEACON_LIFETIME - BEACON_READY,
                                  radius=0.55, sprite="waylay_beacon", warning_sprite="waylay_beacon",
                                  triggers=[on("start", [step("waylay_ready")])]), player.pos)
        beacon.data.update(waylay_beacon=True, ground=player.ground)
        return
    if not statuses.has(match, player, READY) or not match.buy_phase_allows_landing(player, beacon.pos):
        return False
    path = _return_path(match, player, beacon)
    if not path:
        return False
    distance = sum((b - a).length() for a, b in zip([player.pos, *path], path))
    duration = max(0.35, min(2.0, 0.35 + (distance - 2.5) * (1.65 / 47.5)))
    transit = place(ctx, thing("none", delay=0.05, lasts=duration + 0.2, hidden="all",
                               triggers=[on("start", [step("waylay_begin_return")]),
                                         on("tick", [step("waylay_travel")])]), player.pos)
    transit.data.update(path=deque(path), speed=distance / duration, finish=transit.start + duration,
                        cast_at=match.time)
    beacon.props["ended"] = True
    player.status.pop(READY, None)
    player.channel_until = transit.data["finish"]
    player.equip_until = max(player.equip_until, player.channel_until + 0.8)
    player.reload_until = player.dash_until = 0
    player.passive_state.pop("waylay_protected_landing", None)
    player.vel = Vec(0, 0)


@effect("waylay_ready", per_player=False)
def ready(ctx, _player, _spec):
    if ctx.owner is not None and ctx.owner.died_at < ctx.obj.start - BEACON_READY:
        statuses.apply_status(ctx.m, ctx.owner, READY, ctx.obj.until - ctx.m.time)


@effect("waylay_begin_return", per_player=False)
def begin_return(ctx, _player, _spec):
    if ctx.owner is not None:
        statuses.apply_status(ctx.m, ctx.owner, TRANSIT, ctx.obj.data["finish"] - ctx.m.time)


@effect("waylay_travel", per_player=False)
def travel(ctx, _player, _spec):
    obj, player, match = ctx.obj, ctx.owner, ctx.m
    if player is None or not player.alive or player.died_at >= obj.data["cast_at"]:
        obj.props["ended"] = True
        return
    path = obj.data["path"]
    finish = obj.data["finish"]
    available = max(0.0, min(match.time, finish) - max(obj.start, match.time - ctx.dt))
    distance = obj.data["speed"] * available
    level_height = float(match._mv["level_height"])
    radius = float(match._mv["radius"])
    while path:
        offset = path[0] - player.pos
        length = offset.length()
        if length > distance + 1e-7:
            point = player.pos + offset * (distance / length)
        else:
            point = path.popleft()
        reach = (player.ground + float(match._mv["step_up"])) / level_height
        walls = [w.rect for w in match.combat_walls() if (w.full or w.top > reach)
                 and (not w.on_deck or w.base <= reach) and match.wall_active(w)]
        safe = match._move_against_walls(player.pos, point, radius, walls, match.buy_spawn_zone(player))
        player.pos = safe
        player.ground = match.world.ground_height(safe, reach) * level_height
        player.level = int(player.ground / level_height + 0.5)
        player.z = player.vz = 0
        if (safe - point).length() > 1e-5:
            path.clear()
        if length > distance + 1e-7:
            break
        distance = max(0, distance - length)
    if match.time >= finish or not path:
        obj.props["ended"] = True
        player.channel_until = match.time
        player.status.pop(TRANSIT, None)
        statuses.apply_status(match, player, "blind", 0.2)


@effect("waylay_convergent_paths", per_player=False)
def convergent_paths(ctx, _player, _spec):
    ctx.owner.channel_until = ctx.m.time + 0.6
    equip_lock(ctx, None, {"seconds": 1.1})


@trigger("waylay_expanding_strip")
def expanding_strip(ctx, _spec):
    elapsed = ctx.m.time - ctx.obj.start
    tick = min(3, int(elapsed / 0.125))
    if tick == ctx.obj.data.get("beam_tick"):
        return None
    ctx.obj.data["beam_tick"] = tick
    width = ctx.obj.radius * (tick + 1) / 2
    return select(ctx, {"who": "others", "area": "strip", "width": width})
