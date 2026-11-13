"""Yoru's moving decoys, tether and rift."""
from dataclasses import replace

from gameplay.geometry import Rect, Vec, angle_diff, angle_of
from gameplay.kit import statuses
from gameplay.kit.builtins import game_event, select
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place
from gameplay.kit.registry import COMMAND_FILTERS, effect

DRIFT = "yoru_drift"


def _sound(ctx, key, point, radius):
    game_event(ctx.m, "sound_fx", {"key": key, "pos": (point.x, point.y), "radius": radius})


def _advance(ctx, speed):
    match, obj = ctx.m, ctx.obj
    level = obj.props["source_level"]
    walls = [w.rect for w in match.combat_walls() if w.top > level and match.wall_active(w)
             and (not w.on_deck or w.base <= level)]
    obj.pos = match._move_against_walls(obj.pos, obj.pos + ctx.aim * speed * ctx.dt, 0.39, walls, None)
    obj.pos = Vec(max(0.4, min(match.world.width - 0.4, obj.pos.x)),
                  max(0.4, min(match.world.height - 0.4, obj.pos.y)))


@effect("yoru_clone", per_player=False)
def clone(ctx, _target, spec):
    if statuses.has(ctx.m, ctx.owner, DRIFT):
        return False
    if spec.get("marker"):
        place(ctx, thing("sensor", lasts=3600, radius=0.35, sprite="yoru_marker", hidden="enemies",
                         detect_range=0, manual="Fakeout", triggers=[on("activate", [step("yoru_launch_clone")])]),
              ctx.source)
    else:
        launch_clone(ctx, None, {})


@effect("yoru_launch_clone", per_player=False)
def launch_clone(ctx, _target, _spec):
    clone = place(ctx, thing("sensor", lasts=10, radius=0.45, hp=150, hit_radius=0.42, sprite="yoru_clone",
                             triggers=[on("tick", [step("yoru_clone_walk")])]), ctx.point)
    clone.props["on_remove"] = "yoru_clone_flash"
    clone.props["clone_facing"] = angle_of(ctx.aim)


@effect("yoru_clone_walk", per_player=False)
def clone_walk(ctx, _target, _spec):
    _advance(ctx, 5.4)
    if int(ctx.m.time * 3) != int((ctx.m.time - ctx.dt) * 3):
        game_event(ctx.m, "sound", {"pid": ctx.obj.owner, "pos": (ctx.obj.pos.x, ctx.obj.pos.y),
                                   "kind": "step", "radius": 22, "decoy": True})


@effect("yoru_clone_flash", per_player=False)
def clone_flash(ctx, _target, spec):
    if spec["reason"] != "destroy":
        return
    shooter = ctx.m.players.get(ctx.obj.data.get("last_attacker"))
    direction = (shooter.pos - ctx.point).normalized() if shooter else ctx.aim
    place(replace(ctx, aim=direction), thing("zone", delay=0.6, lasts=0.15, radius=28,
         sprite="yoru_flash", warning_sprite="yoru_flash",
         triggers=[on("start", [step("yoru_pop", duration=2, cone=110)])]), ctx.point)


@effect("yoru_pop", per_player=False)
def pop(ctx, _target, spec):
    for player in select(ctx, {"who": "everyone", "radius": ctx.obj.radius, "sight": "all"}):
        if statuses.flag(ctx.m, player, "intangible"):
            continue
        if spec.get("cone") and abs(angle_diff(angle_of(player.pos - ctx.point), angle_of(ctx.aim))) > spec["cone"] / 2:
            continue
        angle = abs(angle_diff(player.facing, angle_of(ctx.point - player.pos)))
        statuses.apply_status(ctx.m, player, "blind", max(0.2, spec["duration"] * (1 - angle / 200)))
    game_event(ctx.m, "flash", {"pos": (ctx.point.x, ctx.point.y), "radius": ctx.obj.radius, "pid": ctx.obj.owner})


@effect("yoru_blindside", per_player=False)
def blindside(ctx, _target, _spec):
    if statuses.has(ctx.m, ctx.owner, DRIFT):
        return False
    limit = min(34, max(2, ctx.owner.cursor_depth))
    candidates = [w.rect for w in ctx.m.combat_walls() if w.top > ctx.owner.level and ctx.m.wall_active(w)]
    bounds = Rect(0, 0, ctx.m.world.width, ctx.m.world.height)
    impact = [(hit[0], rect) for rect in candidates
              if (hit := rect.ray_interval(ctx.source, ctx.aim)) and 0 <= hit[0] <= limit]
    if (edge := bounds.ray_interval(ctx.source, ctx.aim)) and edge[1] <= limit:
        impact.append((edge[1], bounds))
    if not impact:
        return
    distance, wall = min(impact, key=lambda pair: pair[0])
    point = ctx.source + ctx.aim * distance
    x = min(abs(point.x - wall.x0), abs(point.x - wall.x1))
    y = min(abs(point.y - wall.y0), abs(point.y - wall.y1))
    reflected = Vec(-ctx.aim.x, ctx.aim.y) if x <= y else Vec(ctx.aim.x, -ctx.aim.y)
    bounce = point + reflected * 0.08
    destination = ctx.m._clip_to_walls(bounce, bounce + reflected * 3, ctx.owner.level)
    place(replace(ctx, source=bounce), thing("flash", delay=distance / 24, lasts=0.6, thrown=True,
          radius=35, sprite="yoru_flash", triggers=[on("expire", [step("yoru_pop", duration=1.5)])]), destination)


def _gate(ctx):
    return next((e for e in ctx.m.effects if e.owner == ctx.owner.pid and e.props.get("sprite") == "yoru_gate"
                 and not e.props.get("ended") and ctx.m.time < e.until), None)


@effect("yoru_gate", per_player=False)
def gate(ctx, _target, spec):
    owner, match = ctx.owner, ctx.m
    if active := _gate(ctx):
        if statuses.has(match, owner, DRIFT):
            return False
        active.props["ended"] = True
        owner.status.pop("yoru_gate", None)
        arrival = place(ctx, thing("none", delay=0.5, lasts=0.15, hidden="all",
                                    triggers=[on("start", [step("yoru_arrive")], consume=True)]), active.pos)
        arrival.data.update(level=active.props["source_level"], cast_at=match.time)
        owner.channel_until = owner.equip_until = match.time + 1.2
        owner.vel = Vec(0, 0)
        _sound(ctx, "ab_teleport", owner.pos, 42.5)
        return
    gate = place(ctx, thing("sensor", lasts=20, radius=0.45, hp=20, hit_radius=0.45, sprite="yoru_gate",
                            hidden="enemies", detect_range=4, manual="Fake teleport",
                            triggers=[on("tick", [step("yoru_gate_move", stationary=spec.get("stationary", False))]),
                                      on("activate", [step("yoru_fake_gate")]), on("expire", [step("yoru_gate_end")])]),
                 ctx.source)
    gate.props["on_remove"] = "yoru_gate_end"
    statuses.apply_status(match, owner, "yoru_gate", 20)


@effect("yoru_gate_move", per_player=False)
def gate_move(ctx, _target, spec):
    if not spec.get("stationary"):
        _advance(ctx, 6)


@effect("yoru_gate_end", per_player=False)
def gate_end(ctx, _target, _spec):
    if ctx.owner is not None:
        ctx.owner.status.pop("yoru_gate", None)


@effect("yoru_fake_gate", per_player=False)
def fake_gate(ctx, _target, _spec):
    gate_end(ctx, None, {})
    if ctx.owner is not None:
        _sound(ctx, "ab_teleport", ctx.owner.pos, 42.5)
    _sound(ctx, "ab_teleport", ctx.point, 42.5)
    place(ctx, thing("zone", lasts=30, radius=0.5, sprite="yoru_marker"), ctx.point)


@effect("yoru_arrive", per_player=False)
def arrive(ctx, _target, _spec):
    owner, match = ctx.owner, ctx.m
    if (owner is None or not owner.alive or owner.dm_ghost or owner.duel_id
            or owner.died_at >= ctx.obj.data["cast_at"]):
        return
    level = ctx.obj.data["level"]
    if (statuses.flag(match, owner, "no_abilities") or not match.buy_phase_allows_landing(owner, ctx.point)
            or any(w.top > level and (not w.on_deck or w.base <= level) and match.wall_active(w)
                   and w.rect.circle_push(ctx.point, 0.38) for w in match.combat_walls())):
        return
    owner.pos = owner.last_pos = ctx.point
    owner.ground = match.world.ground_height(ctx.point, level) * float(match._mv["level_height"])
    owner.level = level
    owner.z = owner.vz = 0
    _sound(ctx, "ab_teleport", ctx.point, 42.5)


@effect("yoru_drift", per_player=False)
def drift(ctx, _target, _spec):
    if statuses.has(ctx.m, ctx.owner, DRIFT):
        exit_drift(ctx, None, {})
        return
    place(ctx, thing("none", delay=0.4, lasts=0.16, hidden="all",
                     triggers=[on("start", [step("yoru_enter")], consume=True)]), ctx.source)
    ctx.owner.channel_until = ctx.m.time + 0.4


@effect("yoru_enter", per_player=False)
def enter(ctx, _target, _spec):
    if ctx.owner is None or not ctx.owner.alive or statuses.flag(ctx.m, ctx.owner, "no_abilities"):
        return
    statuses.apply_status(ctx.m, ctx.owner, DRIFT, 10)
    place(ctx, thing("none", lasts=10, hidden="all", triggers=[on("expire", [step("yoru_exit")])]), ctx.owner.pos)


@effect("yoru_exit", per_player=False)
def exit_drift(ctx, _target, _spec):
    if ctx.owner is None or DRIFT not in ctx.owner.status:
        return
    ctx.owner.status.pop(DRIFT)
    ctx.owner.equip_until = ctx.m.time + 0.8
    _sound(ctx, "ab_teleport", ctx.owner.pos, 35)


def filter_command(match, player, cmd, _dt):
    if not statuses.has(match, player, DRIFT):
        return cmd
    ability = cmd.ability
    if ability in ("C", "Q") or (ability == "E" and statuses.has(match, player, "yoru_gate")):
        ability = None
    return replace(cmd, ability=ability, fire=False, alt_fire=False, reload=False, slot=None, use_spike=False, drop=False)


COMMAND_FILTERS["yoru"] = filter_command
