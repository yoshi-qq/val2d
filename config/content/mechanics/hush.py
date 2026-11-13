"""Hush's telekinetic projectiles and anchor."""
from dataclasses import replace

from gameplay.geometry import Vec, heading
from gameplay.kit import statuses
from gameplay.kit.builtins import e_pull, e_sound, select
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place, remove_device
from gameplay.kit.registry import COMMAND_FILTERS, effect


@effect("hush_flow", per_player=False)
def flow(ctx, _player, _spec):
    if (ctx.point - ctx.source).length() < 0.5:
        return False
    anchor = place(ctx, thing("zone", delay=0.45, lasts=0.32, radius=0.6, sprite="hush_anchor",
                     warning_sprite="hush_anchor", triggers=[on("start", [step("hush_dash")]), on("expire", [step("hush_brake")])]), ctx.point)
    anchor.data["owner_died_at"] = ctx.owner.died_at
    if ctx.owner.z > 0:
        statuses.apply_status(ctx.m, ctx.owner, "hush_hover", 0.45)


@effect("hush_dash", per_player=False)
def dash(ctx, _player, _spec):
    p = ctx.owner
    if p is None or not p.alive or statuses.flag(ctx.m, p, "no_abilities"):
        return
    if p.dm_ghost or p.duel_id or ctx.m.in_deathmatch_spawn(p) or p.died_at != ctx.obj.data["owner_died_at"]:
        return
    delta = ctx.point - p.pos
    p.dash_until = ctx.m.time + 0.3
    p.dash_vel = delta.normalized() * min(32, delta.length() / 0.3)
    ctx.obj.data["dash_started"] = True


@effect("hush_brake", per_player=False)
def brake(ctx, _player, _spec):
    p = ctx.owner
    if (p and p.alive and ctx.obj.data.get("dash_started") and p.died_at == ctx.obj.data["owner_died_at"]
            and not p.dm_ghost and not p.duel_id and not ctx.m.in_deathmatch_spawn(p) and p.dash_until <= ctx.m.time):
        p.vel = Vec(0, 0)


def _orb(match, player, mode):
    return next((e for e in match.effects if e.owner == player.pid and e.props.get("sprite") == f"hush_{mode}"
                 and not e.props.get("ended") and match.time < e.until), None)


def _launch(ctx, obj, direction):
    obj.data.update(direction=direction, launched=True)
    obj.until = ctx.time + (3 if obj.data["mode"] == "ult" else 1.1)


@effect("hush_projectile", per_player=False)
def projectile(ctx, _player, spec):
    mode = spec["mode"]
    if obj := _orb(ctx.m, ctx.owner, mode):
        if mode == "ult":
            if not obj.data.get("launched"):
                return False
            obj.data["burst"] = True
        else:
            _launch(ctx.m, obj, ctx.aim)
            ctx.owner.status.pop(f"hush_{mode}", None)
            obj.data["redirected"] = True
        return
    prepared = mode == "ult" or ctx.ability.get("prepare")
    obj = place(ctx, thing("sensor", lasts=6, radius=0.4, sprite=f"hush_{mode}", hp=20, hit_radius=0.4,
                            on_remove="hush_clear_orb",
                            triggers=[on("tick", [step("hush_move")]), on("expire", [step("hush_expire")])]), ctx.source)
    obj.data["mode"] = mode
    statuses.apply_status(ctx.m, ctx.owner, f"hush_{mode}", 6)
    if not prepared:
        _launch(ctx.m, obj, ctx.aim)


@effect("hush_clear_orb", per_player=False)
def clear(ctx, _player, _spec):
    if ctx.owner is not None:
        ctx.owner.status.pop(f"hush_{ctx.obj.data['mode']}", None)


@effect("hush_expire", per_player=False)
def expire(ctx, _player, _spec):
    if ctx.obj.data.get("launched"):
        _burst(ctx)
    clear(ctx, None, {})


@effect("hush_move", per_player=False)
def move(ctx, _player, _spec):
    obj, match = ctx.obj, ctx.m
    if not ctx.owner or not ctx.owner.alive:
        remove_device(match, obj, "cancel")
        return
    if not obj.data.get("launched"):
        obj.pos = ctx.owner.pos + heading(ctx.owner.facing) * 1.2
        obj.props["source_level"] = ctx.owner.level
        return
    end = obj.pos + obj.data["direction"] * (18 * ctx.dt)
    clipped = match._clip_to_walls(obj.pos, end, obj.props["source_level"], thrown=True)
    obj.pos = ctx.point = clipped
    if obj.data.get("burst") or clipped != end:
        _burst(ctx)
        remove_device(match, obj, "complete")


def _burst(ctx):
    mode = ctx.obj.data["mode"]
    radius = {"flash": 20, "pull": 6, "ult": 8}[mode]
    if mode != "flash":
        field = place(ctx, thing("zone", lasts=0.5, radius=radius, sprite=f"hush_{mode}_field"), ctx.point)
        field.props["source_level"] = ctx.obj.props["source_level"]
    spec = {"who": "everyone", "radius": radius, "sight": "walls"}
    if mode == "flash":
        spec.update(facing="view", sight="all")
    for p in select(ctx, spec):
        if p.immune_until > ctx.m.time or statuses.flag(ctx.m, p, "intangible"):
            continue
        if mode == "flash":
            statuses.apply_status(ctx.m, p, "blind", 2)
        elif mode == "ult":
            statuses.apply_status(ctx.m, p, "hush_suspended", 2.5)
            p.dash_until = 0
            if p.zipline is not None:
                ctx.m._leave_zipline(p)
            p.vel, p.vz = Vec(0, 0), 0
        else:
            origin = p.pos
            intended = min(3.5, (ctx.point - origin).length())
            e_pull(ctx, p, {"strength": intended})
            collided = (p.pos - origin).length() + 0.05 < intended
            for other in ctx.m.players.values():
                if (other.pid != p.pid and other.alive and other.level == p.level
                        and (other.pos - p.pos).length() < 0.8):
                    collided = True
                    p.pos = origin
                    break
            if collided:
                statuses.apply_status(ctx.m, p, "concuss", 2)
    e_sound(ctx, None, {"key": "cast_arcane", "radius": 25, "range_filtered": True})


def control(match, player, cmd, _dt):
    orb = _orb(match, player, "ult")
    if orb is None or statuses.flag(match, player, "no_abilities"):
        return cmd
    aim = heading(player.facing if cmd.facing is None else cmd.facing)
    if orb.data.get("launched"):
        orb.data["direction"] = aim
        if cmd.fire and not player.prev_fire:
            orb.data["burst"] = True
    elif cmd.fire and match.phase in ("live", "planted"):
        _launch(match, orb, aim)
    return replace(cmd, fire=False, alt_fire=False)


COMMAND_FILTERS["hush"] = control
