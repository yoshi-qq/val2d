"""Deadlock's mesh, noise detection and nanowire capture."""
from dataclasses import replace

from gameplay.geometry import Rect, Vec, heading
from gameplay.kit import statuses
from gameplay.kit.builtins import e_sound, reequip_weapon, select
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place, remove_device
from gameplay.kit.registry import COMMAND_FILTERS, Ctx, MATCH_TICKS, effect
from gameplay.world import Wall


def _vulnerable(match, player):
    return (player.immune_until <= match.time and not statuses.flag(match, player, "intangible")
            and not match.deathmatch_spawn_protected(player))


@effect("deadlock_net_land", per_player=False)
def net_land(ctx, _player, _spec):
    place(ctx, thing("zone", delay=0.4, lasts=0.3, radius=6.5, sprite="deadlock_net",
                     warning_sprite="deadlock_net",
                     triggers=[on("start", [step("deadlock_net_player")], who="everyone")]), ctx.point)


@effect("deadlock_net_player")
def net_player(ctx, player, _spec):
    if _vulnerable(ctx.m, player):
        statuses.apply_status(ctx.m, player, "deadlock_netted", float("inf"))
        player.dash_until = 0
        if player.zipline is not None:
            ctx.m._leave_zipline(player)
        player.crouching = True


def remove_nets(match, commands, dt):
    for player in match.players.values():
        cmd = commands.get(player.pid)
        if (not player.alive or not statuses.has(match, player, "deadlock_netted")
                or statuses.flag(match, player, "no_interact") or not (cmd and cmd.interact)):
            player.passive_state.pop("deadlock_remove_net", None)
            continue
        progress = player.passive_state.get("deadlock_remove_net", 0) + dt
        if progress >= 1.5:
            from gameplay.match import GameEvent
            player.status.pop("deadlock_netted", None)
            player.passive_state.pop("deadlock_remove_net", None)
            match.events.append(GameEvent("sound_fx", match.time, {
                "key": "cast_tech", "radius": 16, "pos": (player.pos.x, player.pos.y), "range_filtered": True,
            }))
        else:
            player.passive_state["deadlock_remove_net"] = progress


@effect("deadlock_sensor", per_player=False)
def sensor(ctx, _player, _spec):
    # Place a little in front of the wall so a shot can reach the device.
    direction = (ctx.point - ctx.source).normalized()
    if direction.length() == 0:
        return False
    surface = ctx.m._clip_to_walls(ctx.source, ctx.source + direction * 14.2, ctx.owner.level)
    if (surface - ctx.point).length() > 1.25 or (surface - ctx.source).length() >= 14:
        return False
    obj = place(ctx, thing("sensor", delay=1.75, lasts=3600, radius=0.35, hp=20, hit_radius=0.35,
                           hidden="enemies", detect_range=4, owner_range=float("inf"), recall_recharge=0,
                           sprite="deadlock_sensor", on_remove="deadlock_sensor_removed",
                           triggers=[on("tick", [step("deadlock_listen")])]), surface)
    obj.props["recall_range"] = 27
    obj.data["normal"] = direction * -1


@effect("deadlock_sensor_removed", per_player=False)
def sensor_removed(ctx, _player, spec):
    if spec["reason"] == "destroy":
        e_sound(ctx, None, {"key": "cast_tech", "radius": 200, "team_only": True})


def _in_sensor(ctx, player):
    offset = player.pos - ctx.obj.pos
    normal = ctx.obj.data["normal"]
    return (0 <= offset.dot(normal) <= 9 and abs(offset.cross(normal)) <= 4
            and abs(player.level - ctx.obj.props["source_level"]) <= 1
            and ctx.m._line_clear(ctx.obj.pos, player.pos, player.level, ignore_effects=True))


@effect("deadlock_listen", per_player=False)
def listen(ctx, _player, _spec):
    obj, match = ctx.obj, ctx.m
    if "trigger_at" not in obj.data:
        noisy = {event.data["pid"] for event in match.events if event.kind == "jump" or (
            event.kind == "sound" and event.data.get("kind") in ("shot", "step", "knife"))}
        for player in select(ctx, {"who": "enemies", "area": "everywhere"}):
            if ((player.pid in noisy or 0 < player.plant_progress <= ctx.dt or player.defusing)
                    and _vulnerable(match, player) and _in_sensor(ctx, player)):
                obj.data["trigger_at"] = match.time + 0.5
                obj.props["hidden"] = None
                obj.props.pop("recall_recharge", None)
                e_sound(ctx, None, {"key": "cast_sonic", "radius": 18, "range_filtered": True})
                break
    elif match.time >= obj.data["trigger_at"]:
        for player in select(ctx, {"who": "everyone", "area": "everywhere"}):
            if _in_sensor(ctx, player) and _vulnerable(match, player):
                statuses.apply_status(match, player, "concuss", 2.5)
        obj.props["ended"] = True


@effect("deadlock_mesh", per_player=False)
def mesh(ctx, _player, _spec):
    if ctx.m.world.drop_recovery(ctx.point) is not None:
        return
    level = ctx.m.world.floor_level(ctx.point)
    core = _mesh_node(ctx, ctx.point, level, 680, 1200)
    for direction in (Vec(1, 0), Vec(-1, 0), Vec(0, 1), Vec(0, -1)):
        end = ctx.m._clip_to_walls(ctx.point, ctx.point + direction * 10, level)
        if ((end - ctx.point).length() < 0.5 or not (0 <= end.x <= ctx.m.world.width and 0 <= end.y <= ctx.m.world.height)
                or ctx.m.world.drop_recovery(end) is not None):
            continue
        node = _mesh_node(ctx, end, level, 320, 480)
        arm = place(ctx, thing("wall", delay=1, lasts=29, sprite="deadlock_mesh",
                               blocks_sight=False, triggers=[on("tick", [step("deadlock_mesh_arm")])]),
                    (ctx.point + end) * 0.5)
        arm.a, arm.b = ctx.point, end
        arm.data.update(core=core, node=node)
        core.data.setdefault("arms", []).append(arm)
        node.data["arms"] = [arm]


def _mesh_node(ctx, point, level, hp, fortified):
    node = place(ctx, thing("sensor", delay=1, lasts=29, radius=0.55, hp=hp, friendly_fire=True,
                            sprite="deadlock_node", hit_sound="cast_tech", on_remove="deadlock_mesh_node_broken",
                            triggers=[on("tick", [step("deadlock_mesh_decay")])]), point)
    node.props["source_level"] = level
    node.data.update(fortify_at=ctx.m.time + 3, fortify_hp=fortified - hp)
    return node


@effect("deadlock_mesh_decay", per_player=False)
def mesh_decay(ctx, _player, _spec):
    node = ctx.obj
    elapsed = max(0, ctx.m.time - (node.until - 5))
    if elapsed:
        maximum = node.data.setdefault("decay_hp", node.data["hp"])
        cap = round(maximum * max(0, 1 - elapsed / 5))
        node.data["hp"] = min(node.data["hp"], cap)
        if node.data["hp"] <= 0:
            remove_device(ctx.m, node, "decay")


@effect("deadlock_mesh_node_broken", per_player=False)
def mesh_node_broken(ctx, _player, _spec):
    for arm in ctx.obj.data.get("arms", ()):
        arm.props["ended"] = True


@effect("deadlock_mesh_arm", per_player=False)
def mesh_arm(ctx, _player, _spec):
    arm = ctx.obj
    core, node = arm.data["core"], arm.data["node"]
    if core.props.get("ended") or node.props.get("ended"):
        arm.props["ended"] = True
        return
    for orb in (core, node):
        orb.props["hit_radius"] = orb.radius
    if "barrier" not in arm.props:
        a, b = arm.a, arm.b
        rect = Rect(min(a.x, b.x) - 0.10, min(a.y, b.y) - 0.10,
                    max(a.x, b.x) + 0.10, max(a.y, b.y) + 0.10)
        level = core.props["source_level"]
        arm.props["source_level"] = level
        arm.props["barrier"] = Wall(rect, 0, blocks_sight=False, base=level, on_deck=level > 0,
                                    ceiling=level + 2, movement_only=True)


@effect("deadlock_accelerator", per_player=False)
def accelerator(ctx, _player, _spec):
    match, owner = ctx.m, ctx.owner
    if statuses.has(match, owner, "deadlock_accelerator_equipped"):
        owner.status.pop("deadlock_accelerator_equipped", None)
        reequip_weapon(match, owner)
        return
    ready = statuses.has(match, owner, "deadlock_accelerator_ready")
    if not ready:
        statuses.apply_status(match, owner, "deadlock_accelerator_ready", 10)
    remaining = owner.status.get("deadlock_accelerator_ready", match.time) - match.time
    statuses.apply_status(match, owner, "deadlock_accelerator_equipped", remaining)
    owner.equip_until = match.time + (0.7 if ready else 1.1)
    owner.reload_until = owner.burst_left = 0


def accelerator_command(match, player, cmd, _dt):
    if not statuses.has(match, player, "deadlock_accelerator_equipped"):
        if player.status.pop("deadlock_accelerator_equipped", None) is not None:
            reequip_weapon(match, player)
        deadline = player.status.get("deadlock_accelerator_ready")
        if deadline is not None and deadline <= match.time:
            player.status.pop("deadlock_accelerator_ready")
        return cmd
    if (cmd.slot or any(slot in ("primary", "sidearm", "melee", "spike") for slot in cmd.equipment_actions)
            or (cmd.ability and cmd.ability != "X") or statuses.flag(match, player, "no_abilities")):
        player.status.pop("deadlock_accelerator_equipped", None)
        reequip_weapon(match, player)
        return replace(cmd, fire=False, alt_fire=False)
    if ((cmd.fire or player.is_bot) and cmd.ability != "X"
            and match.time >= max(player.equip_until, player.channel_until)
            and match.phase in ("live", "planted") and not statuses.flag(match, player, "no_fire")
            and not match.in_deathmatch_spawn(player) and not player.spike_equipped):
        aim = heading(player.facing if cmd.facing is None else cmd.facing)
        ctx = Ctx(match, player, player.team, player.pos, player.pos, aim, key="X")
        launch_pulse(ctx)
        player.status.pop("deadlock_accelerator_equipped", None)
        player.status.pop("deadlock_accelerator_ready", None)
        player.equip_until = match.time + 0.5
        player.dash_until, player.dash_vel = match.time + 0.15, aim * -10
        e_sound(ctx, None, {"key": "cast_beam", "radius": 40, "range_filtered": True})
    return replace(cmd, fire=False, alt_fire=False, reload=False)


def launch_pulse(ctx):
    pulse = place(ctx, thing("zone", delay=0.5, lasts=0.6, radius=0.7, sprite="deadlock_pulse",
                             triggers=[on("tick", [step("deadlock_pulse_tick")])]), ctx.source)
    pulse.data.update(direction=ctx.aim, remaining=40.0, path=[ctx.source], bounced=False)


def _wall_hit(match, origin, direction, distance, level):
    hit = None
    for wall in match.active_sight_walls(level):
        iv = wall.rect.ray_interval(origin, direction)
        if iv and 0 <= iv[0] <= distance and (hit is None or iv[0] < hit[0]):
            hit = iv[0], wall.rect
    return hit


def reflected_heading(point, direction, rect):
    at_side = min(abs(point.x - rect.x0), abs(point.x - rect.x1)) < 1e-5
    return Vec(-direction.x, direction.y) if at_side else Vec(direction.x, -direction.y)


def pulse_preview(match, player):
    direction = heading(player.facing)
    origin = player.pos
    hit = _wall_hit(match, origin, direction, 40, player.level)
    if not hit:
        return origin, origin + direction * 40
    length, rect = hit
    corner = origin + direction * length
    direction = reflected_heading(corner, direction, rect)
    reflected_origin = corner + direction * 0.01
    second = _wall_hit(match, reflected_origin, direction, 40 - length, player.level)
    return origin, corner, reflected_origin + direction * (second[0] if second else 40 - length)


def _capture(ctx, a, direction, length, radius):
    candidates = []
    for player in select(ctx, {"who": "enemies", "area": "everywhere"}):
        offset = player.pos - a
        along = min(length, max(0, offset.dot(direction)))
        closest = a + direction * along
        if ((player.pos - closest).length() <= radius and _vulnerable(ctx.m, player)
                and not statuses.has(ctx.m, player, "deadlock_cocooned")
                and ctx.m._line_clear(closest, player.pos, player.level, ignore_effects=True)):
            candidates.append((along, player.pid, player))
    return min(candidates)[2] if candidates else None


@effect("deadlock_pulse_tick", per_player=False)
def pulse_tick(ctx, _player, _spec):
    pulse, match = ctx.obj, ctx.m
    budget = min(pulse.data["remaining"], 82.5 * min(ctx.dt, match.time - pulse.start))
    while budget > 1e-6:
        direction = pulse.data["direction"]
        hit = _wall_hit(match, pulse.pos, direction, budget, pulse.props["source_level"])
        length = hit[0] if hit else budget
        if player := _capture(ctx, pulse.pos, direction, length, 3):
            along = min(length, max(0, (player.pos - pulse.pos).dot(direction)))
            _cocoon(ctx, player, pulse.pos + direction * along)
            return
        pulse.pos += direction * length
        budget -= length
        pulse.data["remaining"] -= length
        if hit and not pulse.data["bounced"]:
            reflected = reflected_heading(pulse.pos, direction, hit[1])
            pulse.pos += reflected * 0.01
            pulse.data.update(direction=reflected, bounced=True)
            pulse.data["path"].append(pulse.pos)
        elif hit or pulse.data["remaining"] <= 1e-6:
            if player := _capture(ctx, pulse.pos, direction, 0, 6.5):
                _cocoon(ctx, player, pulse.pos)
            pulse.props["ended"] = True
            return


def _cocoon(ctx, player, contact):
    pulse = ctx.obj
    cocoon = place(ctx, thing("sensor", lasts=7, radius=0.8, hp=600, hit_radius=0.8,
                              friendly_fire=True, sprite="deadlock_cocoon",
                              on_remove="deadlock_release",
                              triggers=[on("tick", [step("deadlock_pull")]), on("expire", [step("deadlock_execute")])]),
                   player.pos)
    cocoon.props["source_level"] = player.level
    cocoon.data.update(victim=player.pid, path=[*pulse.data["path"], contact])
    route = [*cocoon.data["path"], player.pos]
    cocoon.data["speed"] = sum((b - a).length() for a, b in zip(route, route[1:])) / 7
    pulse.props["ended"] = True
    player.dash_until = 0
    if player.zipline is not None:
        ctx.m._leave_zipline(player)
    player.vel, player.vz = Vec(0, 0), 0
    statuses.apply_status(ctx.m, player, "deadlock_cocooned", 7)


@effect("deadlock_pull", per_player=False)
def pull(ctx, _player, _spec):
    obj, match = ctx.obj, ctx.m
    player = match.players.get(obj.data["victim"])
    if player is None or not player.alive or not statuses.has(match, player, "deadlock_cocooned"):
        obj.props["ended"] = True
        return
    path = obj.data["path"]
    budget = obj.data["speed"] * ctx.dt
    while path and budget > 0:
        offset = path[-1] - player.pos
        distance = offset.length()
        if distance <= budget:
            player.pos = path.pop()
            budget -= distance
        else:
            player.pos += offset.normalized() * budget
            break
    obj.pos = player.pos
    obj.props["source_level"] = player.level


@effect("deadlock_release", per_player=False)
def release(ctx, _player, _spec):
    player = ctx.m.players.get(ctx.obj.data["victim"])
    if player is not None:
        player.status.pop("deadlock_cocooned", None)


@effect("deadlock_execute", per_player=False)
def execute(ctx, _player, _spec):
    player = ctx.m.players.get(ctx.obj.data["victim"])
    release(ctx, None, {})
    if player is not None and player.alive:
        ctx.m._damage(ctx.owner, player, 10000, "body", "deadlock_annihilation")


MATCH_TICKS["deadlock"] = remove_nets
COMMAND_FILTERS["deadlock"] = accelerator_command
