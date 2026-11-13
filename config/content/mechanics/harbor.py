"""Harbor's water smoke, guided screen and crowd control."""
from dataclasses import replace

from gameplay.geometry import Vec, angle_diff, angle_of, heading
from gameplay.kit import statuses
from gameplay.kit.builtins import e_sound, select
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place
from gameplay.kit.registry import COMMAND_FILTERS, effect


def _active(ctx, sprite):
    return next((e for e in reversed(ctx.m.effects) if e.owner == ctx.owner.pid
                 and e.props.get("sprite") == sprite and not e.props.get("ended")
                 and e.until > ctx.m.time), None)


@effect("harbor_storm_land", per_player=False)
def storm_land(ctx, _target, _spec):
    place(ctx, thing("zone", delay=0.6, lasts=0.4, radius=6, sprite="harbor_storm",
                     warning_sprite="harbor_storm",
                     triggers=[on("start", [step("harbor_storm_burst")])]), ctx.point)


@effect("harbor_storm_burst", per_player=False)
def storm_burst(ctx, _target, _spec):
    hit_enemy = False
    for player in select(ctx, {"who": "everyone"}):
        if player.immune_until <= ctx.m.time and not statuses.flag(ctx.m, player, "intangible"):
            statuses.apply_status(ctx.m, player, "harbor_nearsight", 2)
            statuses.apply_status(ctx.m, player, "harbor_slow", 2)
            hit_enemy |= player.team != ctx.team
    if hit_enemy:
        e_sound(ctx, None, {"key": "cast_burst", "radius": 20, "range_filtered": True})


@effect("harbor_cove", per_player=False)
def cove(ctx, _target, _spec):
    smoke = _active(ctx, "harbor_cove")
    if statuses.has(ctx.m, ctx.owner, "harbor_cove_ready") and smoke:
        start = max(smoke.start, ctx.m.time + 0.8)
        if smoke.until <= start:
            return False
        shield = place(ctx, thing("zone", delay=start - ctx.m.time, lasts=smoke.until - start,
                                  radius=smoke.radius, hp=680, friendly_fire=True, sprite="harbor_shield",
                                  on_remove="harbor_shield_break"), smoke.pos)
        shield.props.update(hit_radius=smoke.radius, bullet_shell=True, source_level=smoke.props["source_level"])
        shield.data["smoke"] = smoke
        ctx.owner.status.pop("harbor_cove_ready", None)
        return
    if ctx.m.world.drop_recovery(ctx.point) is not None:
        return False
    smoke = place(ctx, thing("smoke", delay=1, travel_speed=64, lasts=19.25, radius=4.6,
                             sprite="harbor_cove", warning_sprite="harbor_cove"), ctx.point)
    ground, _ = ctx.m.world.smoke_target_heights(smoke.pos, bool(ctx.ability.get("under_deck")), 0)
    smoke.props.update(source_level=int(ground + 0.5), settled_ground=ground)
    statuses.apply_status(ctx.m, ctx.owner, "harbor_cove_ready", smoke.until - ctx.m.time)


@effect("harbor_shield_break", per_player=False)
def shield_break(ctx, _target, spec):
    if spec["reason"] == "destroy":
        smoke = ctx.obj.data["smoke"]
        smoke.until = min(smoke.until, ctx.m.time + 1)
        e_sound(ctx, None, {"key": "cast_shield_up", "radius": 20, "range_filtered": True})


@effect("harbor_tide", per_player=False)
def tide(ctx, _target, _spec):
    marker = place(ctx, thing("zone", lasts=3, radius=0.5, sprite="harbor_current",
                              triggers=[on("tick", [step("harbor_tide_grow")])]), ctx.source)
    marker.data.update(direction=ctx.aim, distance=0.0, path=[ctx.source])


@effect("harbor_tide_grow", per_player=False)
def tide_grow(ctx, _target, _spec):
    marker = ctx.obj
    path = marker.data["path"]
    distance = min(25 * ctx.dt, 60 - marker.data["distance"])
    if not marker.data.get("stop"):
        marker.pos = marker.pos + marker.data["direction"] * distance
        marker.data["distance"] += distance
        if (marker.pos - path[-1]).length() >= 2:
            path.append(marker.pos)
        if marker.data["distance"] < 60:
            return
    if path[-1] != marker.pos:
        path.append(marker.pos)
    for i, (a, b) in enumerate(zip(path, path[1:])):
        wall = place(ctx, thing("wall", delay=i * 0.06, lasts=15, radius=0.5, sprite="harbor_tide",
                                 triggers=[on("tick", [step("harbor_tide_slow")], who="everyone",
                                              area="line", width=1)]), (a + b) * 0.5)
        wall.a, wall.b = a, b
        wall.props["sight_height"] = 8
    marker.props["ended"] = True


@effect("harbor_tide_slow")
def tide_slow(ctx, player, _spec):
    if (ctx.obj.props["source_level"] <= player.level < ctx.obj.props["source_level"] + 8
            and player.immune_until <= ctx.m.time and not statuses.flag(ctx.m, player, "intangible")):
        statuses.apply_status(ctx.m, player, "harbor_slow", 0.6)


def steer(match, player, cmd, dt):
    marker = next((e for e in reversed(match.effects) if e.owner == player.pid
                   and e.props.get("sprite") == "harbor_current" and not e.props.get("ended")
                   and e.until > match.time), None)
    if marker is None or statuses.flag(match, player, "no_abilities"):
        return cmd
    if cmd.alt_fire:
        marker.data["stop"] = True
    elif cmd.fire:
        direction = marker.data["direction"]
        facing = player.facing if cmd.facing is None else cmd.facing
        turn = angle_diff(angle_of(direction), facing)
        marker.data["direction"] = direction.rotated(max(-180 * dt, min(180 * dt, turn)))
    return replace(cmd, fire=False, alt_fire=False)


@effect("harbor_reckoning", per_player=False)
def reckoning(ctx, _target, _spec):
    if statuses.has(ctx.m, ctx.owner, "harbor_wave_ready"):
        wave = _active(ctx, "harbor_wave")
        if wave is None:
            return False
        wave.data["stopped"] = True
        wave.until = max(ctx.m.time, wave.start) + 7
        ctx.owner.status.pop("harbor_wave_ready", None)
        return
    wave = place(ctx, thing("wall", delay=0.7, lasts=3.4, spawn_ahead=8, radius=0.8,
                            blocks_sight=False, sprite="harbor_wave",
                            triggers=[on("tick", [step("harbor_wave_tick")])]), ctx.source)
    side = Vec(ctx.aim.y, -ctx.aim.x) * 10.5
    wave.a, wave.b = wave.pos - side, wave.pos + side
    statuses.apply_status(ctx.m, ctx.owner, "harbor_wave_ready", wave.until - ctx.m.time)


@effect("harbor_wave_tick", per_player=False)
def wave_tick(ctx, _target, _spec):
    wave = ctx.obj
    if not wave.data.get("stopped"):
        offset = ctx.aim * (10 * min(ctx.dt, ctx.m.time - wave.start))
        wave.pos, wave.a, wave.b = wave.pos + offset, wave.a + offset, wave.b + offset
    inside = set()
    for player in select(ctx, {"who": "enemies", "area": "line", "width": 2}):
        if player.immune_until <= ctx.m.time and not statuses.flag(ctx.m, player, "intangible"):
            inside.add(player.pid)
            if player.pid not in wave.data.get("inside", ()):
                statuses.apply_status(ctx.m, player, "harbor_nearsight", 3)
                statuses.apply_status(ctx.m, player, "harbor_slow", 2)
    wave.data["inside"] = inside


COMMAND_FILTERS["harbor"] = steer
