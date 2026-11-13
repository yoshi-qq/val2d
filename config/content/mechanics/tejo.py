"""Tejo's controlled drone and area strikes."""
from collections import deque

from gameplay.geometry import Vec
from gameplay.kit import statuses
from gameplay.kit.builtins import damage_map_cover, e_sound, select
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place, remove_device
from gameplay.kit.registry import COMMAND_FILTERS, effect
from gameplay.nav import grid_for


@effect("tejo_drone", per_player=False)
def launch_drone(ctx, _player, _spec):
    start = ctx.m._clip_to_walls(ctx.source, ctx.source + ctx.aim * 4, ctx.owner.level)
    drone = place(ctx, thing("sensor", delay=0.3, lasts=6, radius=0.45, hp=42, hit_radius=0.45, device_vision=True,
                             sprite="tejo_drone", hidden="enemies", detect_range=4,
                             cancel_channel=True, on_remove="tejo_drone_end",
                             triggers=[on("tick", [step("tejo_drone_tick")]),
                                       on("expire", [step("tejo_drone_end")])]), start)
    drone.data.update(movement=Vec(0, 0), health=ctx.owner.hp + ctx.owner.armor + ctx.owner.overheal)
    ctx.owner.channel_until = drone.until
    ctx.owner.vel = Vec(0, 0)


@effect("tejo_drone_end", per_player=False)
def end_drone(ctx, _player, _spec):
    if ctx.owner is not None:
        ctx.owner.channel_until = 0
        ctx.owner.equip_until = ctx.m.time + 0.5


@effect("tejo_drone_tick", per_player=False)
def move_drone(ctx, _player, _spec):
    obj, owner, match = ctx.obj, ctx.owner, ctx.m
    health = owner.hp + owner.armor + owner.overheal if owner is not None else 0
    if owner is None or not owner.alive or health < obj.data["health"]:
        remove_device(match, obj, "cancel")
        return
    obj.data["health"] = health
    if "pulse_at" in obj.data:
        if match.time >= obj.data["pulse_at"]:
            place(ctx, thing("zone", lasts=0.75, radius=0.1, sprite="tejo_pulse",
                             triggers=[on("tick", [step("tejo_scan")])]), obj.pos)
            remove_device(match, obj, "complete")
        return
    movement = obj.data["movement"]
    level = obj.props["source_level"]
    walls = [w.rect for w in match.combat_walls() if w.top > level and match.wall_active(w)
             and (not w.on_deck or w.base <= level)]
    obj.pos = match._move_against_walls(obj.pos, obj.pos + movement * (7 * ctx.dt), 0.4, walls, None)
    obj.props["source_level"] = match.world.floor_level(obj.pos, level + 0.5)


@effect("tejo_scan", per_player=False)
def scan(ctx, _player, _spec):
    pulse = ctx.obj
    pulse.radius = min(16, 16 * (ctx.m.time - pulse.start) / 0.7)
    seen = pulse.data.setdefault("seen", set())
    for player in select(ctx, {"sight": "walls"}):
        if (player.pid not in seen and abs(player.level - pulse.props["source_level"]) <= 2
                and player.immune_until <= ctx.m.time
                and not statuses.flag(ctx.m, player, "intangible")):
            seen.add(player.pid)
            statuses.apply_status(ctx.m, player, "suppress", 8)
            player.revealed_until = max(player.revealed_until, ctx.m.time + 1.5)


def control_drone(match, player, cmd, _dt):
    drone = next((obj for obj in match.effects if obj.owner == player.pid and obj.props.get("sprite") == "tejo_drone"
                  and not obj.props.get("ended") and match.time < obj.until), None)
    if drone is None:
        return cmd
    if statuses.flag(match, player, "no_abilities") or (cmd.ability == "C" and player.prev_ability != "C"):
        remove_device(match, drone, "cancel")
        return None
    if match.time >= drone.start and "pulse_at" not in drone.data:
        if cmd.facing is not None:
            player.facing = cmd.facing % 360
        wish = Vec(cmd.move_x, cmd.move_y).rotated(player.facing)
        drone.data["movement"] = wish.normalized() if wish.length() > 1 else wish
        if cmd.fire or cmd.jump:
            drone.data["pulse_at"] = match.time + 0.4
            drone.props["hidden"] = None
            drone.until = max(drone.until, drone.data["pulse_at"] + 0.05)
            player.channel_until = drone.until
    return None


def _first_surface(match, origin, direction, limit, level):
    best = None
    for wall in match.active_sight_walls(level):
        iv = wall.rect.ray_interval(origin, direction)
        if iv and iv[0] <= limit and (best is None or iv[0] < best[0]):
            best = iv[0], wall.rect
    return best


@effect("tejo_grenade", per_player=False)
def grenade(ctx, _player, _spec):
    missile = place(ctx, thing("sensor", lasts=3, radius=0.35, sprite="tejo_grenade",
                               triggers=[on("tick", [step("tejo_grenade_tick")])]), ctx.source)
    missile.data.update(direction=ctx.aim, remaining=max(2, min(28, ctx.owner.cursor_depth)),
                        bounce=bool(ctx.ability.get("bounce")))


@effect("tejo_grenade_tick", per_player=False)
def move_grenade(ctx, _player, _spec):
    obj = ctx.obj
    direction = obj.data["direction"]
    travel = min(obj.data["remaining"], 24 * ctx.dt)
    hit = _first_surface(ctx.m, obj.pos, direction, travel, obj.props["source_level"])
    if hit:
        distance, rect = hit
        point = obj.pos + direction * distance
        if obj.data.pop("bounce", False):
            side = min(abs(point.x - rect.x0), abs(point.x - rect.x1)) < 1e-5
            reflected = Vec(-direction.x, direction.y) if side else Vec(direction.x, -direction.y)
            obj.pos = point + reflected * 0.05
            obj.data.update(direction=reflected, remaining=max(6, obj.data["remaining"] - distance))
            return
        obj.pos += direction * max(0, distance - 0.05)
    else:
        obj.pos += direction * travel
        obj.data["remaining"] -= travel
        if obj.data["remaining"] > 0:
            return
    place(ctx, thing("zone", delay=0.9, lasts=0.25, radius=5.25, sprite="tejo_blast", warning_sprite="tejo_blast",
                     triggers=[on("start", [step("tejo_explosion", inner=1.25, maximum=35, minimum=20, concuss=2.5)])]),
          obj.pos)
    obj.props["ended"] = True


@effect("tejo_salvo", per_player=False)
def salvo(ctx, _player, _spec):
    match = ctx.m
    level = ctx.owner.level
    if match._line_clear(ctx.source, ctx.point, level, ignore_effects=True, solid_only=True):
        route = [ctx.point]
    else:
        grid = grid_for(match.world, frozenset(match.open_doors | match.broken_cover), tuple(match.ability_walls()))
        route = grid.path(ctx.source, ctx.point, start_ground=level, goal_ground=match.world.floor_level(ctx.point))
        if not route:
            return False
    missile = place(ctx, thing("sensor", lasts=20, radius=0.35, sprite="tejo_missile",
                               triggers=[on("tick", [step("tejo_salvo_move")])]), ctx.source)
    missile.data["route"] = deque(route)


@effect("tejo_salvo_move", per_player=False)
def salvo_move(ctx, _player, _spec):
    missile = ctx.obj
    route = missile.data["route"]
    travel = 22 * ctx.dt
    while route and travel > 0:
        delta = route[0] - missile.pos
        distance = delta.length()
        if distance > travel:
            missile.pos += delta * (travel / distance)
            return
        missile.pos = route.popleft()
        travel -= distance
    if not route:
        ctx.point = missile.pos
        missile.props["source_level"] = ctx.m.world.floor_level(missile.pos)
        salvo_land(ctx, None, {})
        missile.props["ended"] = True


def salvo_land(ctx, _player, _spec):
    for index in range(3):
        place(ctx, thing("zone", delay=1.25 + index * 0.8, lasts=0.25, radius=4.5, sprite="tejo_blast",
                         warning_sprite="tejo_blast" if index == 0 else None,
                         triggers=[on("start", [step("tejo_explosion", inner=2.5, maximum=65, minimum=50)])]), ctx.point)


@effect("tejo_explosion", per_player=False)
def explode(ctx, _player, spec):
    obj = ctx.obj
    for player in select(ctx, {"who": "everyone"}):
        if statuses.flag(ctx.m, player, "intangible"):
            continue
        distance = (player.pos - ctx.point).length()
        fraction = max(0, min(1, (distance - spec["inner"]) / (obj.radius - spec["inner"])))
        damage = round(spec["maximum"] + (spec["minimum"] - spec["maximum"]) * fraction)
        ctx.m._damage(ctx.owner, player, damage, "body", f"ability:{ctx.ability['name']}")
        if player.alive and spec.get("concuss"):
            statuses.apply_status(ctx.m, player, "concuss", spec["concuss"])
    damage_map_cover(ctx, {"do": "damage", "amount": spec["maximum"], "cover_mult": 0.5})
    for device in list(ctx.m.effects):
        if (device.data.get("hp", 0) > 0 and not device.props.get("ended")
                and device.props.get("duel_id", 0) == obj.props.get("duel_id", 0)
                and abs(device.props.get("source_level", 0) - obj.props["source_level"]) <= 1
                and (device.pos - obj.pos).length() <= obj.radius):
            device.data["hp"] -= round(spec["maximum"] * 0.5)
            if device.data["hp"] <= 0:
                remove_device(ctx.m, device, "destroy")
    e_sound(ctx, None, {"key": "ab_blast", "radius": 24, "range_filtered": True})


@effect("tejo_armageddon", per_player=False)
def armageddon(ctx, _player, _spec):
    axis = ctx.aim
    for index in range(16):
        a = ctx.point + axis * (2 * index)
        b = a + axis * 2
        segment = place(ctx, thing("zone", delay=3.08 + index * 0.25, lasts=1, radius=6,
                                   sprite="tejo_strike", blocks_sight=False,
                                   triggers=[on("tick", [step("tejo_strike_tick")])]), (a + b) * 0.5)
        segment.a, segment.b = a, b


@effect("tejo_strike_tick", per_player=False)
def strike_tick(ctx, _player, _spec):
    pulse = min(3, int((ctx.m.time - ctx.obj.start) / 0.25))
    if ctx.obj.data.get("pulse") == pulse:
        return
    ctx.obj.data["pulse"] = pulse
    for player in select(ctx, {"who": "everyone", "area": "strip", "width": 12}):
        ctx.m._damage(ctx.owner, player, 60, "body", "ability:Armageddon")
    damage_map_cover(ctx, {"do": "damage", "amount": 60, "cover_mult": 0.5, "area": "line", "width": 12})
    e_sound(ctx, None, {"key": "ab_blast", "radius": 22, "range_filtered": True})


COMMAND_FILTERS["tejo"] = control_drone
