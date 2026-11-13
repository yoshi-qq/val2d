"""Fade's thrown utility, Terror Trails and pursuing Prowlers."""
from collections import deque
from dataclasses import replace

from gameplay.geometry import Vec, heading, segment_circle_hit
from gameplay.kit import statuses
from gameplay.kit.builtins import game_event, select
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place
from gameplay.kit.registry import COMMAND_FILTERS, MATCH_TICKS, effect
from gameplay.nav import grid_for


def _mark(ctx, target, seconds):
    match = ctx.m
    trail = next((e for e in match.effects if e.owner == ctx.obj.owner and e.data.get("fade_trail") == target.pid
                  and not e.props.get("ended")), None)
    if trail is None:
        trail = place(ctx, thing("zone", lasts=seconds, sprite="fade_trail"), ctx.point)
        trail.props["hidden"] = "team_only"
        trail.data["fade_trail"] = target.pid
        trail.a, trail.b = ctx.point, target.pos
    else:
        trail.until = max(trail.until, match.time + seconds)


def _decay(target, amount, seconds):
    before = target.hp + target.hp_frac
    after = max(1, before - amount)
    target.hp, target.hp_frac = int(after), after - int(after)
    target.decay_pool += before - after
    target.passive_state["decay_recovery_rate"] = amount / seconds


def _eligible(ctx, player):
    return player.immune_until <= ctx.m.time and not statuses.flag(ctx.m, player, "intangible")


@effect("fade_throw", per_player=False)
def throw(ctx, _player, spec):
    mode = spec["mode"]
    flag = f"fade_{mode}_air"
    pending = next((e for e in ctx.m.effects if e.owner == ctx.owner.pid and e.data.get("fade_air") == mode
                    and not e.props.get("ended") and e.until > ctx.m.time), None)
    if pending:
        ratio = min(1, (ctx.m.time - pending.start) / 1.5)
        point = pending.a + (pending.pos - pending.a) * ratio
        pending.props["ended"] = True
        land(replace(ctx, point=point), None, spec)
        return
    obj = place(ctx, thing("blast", lasts=1.5, thrown=True, sprite=f"fade_{mode}",
                           triggers=[on("expire", [step("fade_land", mode=mode)])]), ctx.point)
    obj.data["fade_air"] = mode
    statuses.apply_status(ctx.m, ctx.owner, flag, 1.5)


@effect("fade_land", per_player=False)
def land(ctx, _player, spec):
    mode = spec["mode"]
    if ctx.owner is not None:
        ctx.owner.status.pop(f"fade_{mode}_air", None)
    if mode == "haunt":
        place(ctx, thing("sensor", delay=0.825, lasts=1.5, radius=0.55, hp=1, hit_radius=0.45,
                         sprite="fade_haunt", warning_sprite="fade_haunt",
                         triggers=[on("tick", [step("fade_scan")])]), ctx.point)
    else:
        place(ctx, thing("zone", delay=0.7, lasts=4.5, radius=6.58,
                         sprite="fade_seize_field", warning_sprite="fade_seize_field",
                         triggers=[on("start", [step("fade_bind")], who="enemies", sight="walls")]), ctx.point)


@effect("fade_scan", per_player=False)
def scan(ctx, _player, _spec):
    seen = ctx.obj.data.setdefault("seen", set())
    for player in select(ctx, {"who": "enemies", "radius": 30, "sight": "all"}):
        if player.pid not in seen and _eligible(ctx, player):
            seen.add(player.pid)
            player.revealed_until = max(player.revealed_until, ctx.m.time + 1)
            _mark(ctx, player, 12)


@effect("fade_bind")
def bind(ctx, player, _spec):
    if _eligible(ctx, player):
        _decay(player, 75, 5)
        player.passive_state["fade_tether"] = (ctx.point, ctx.obj.radius)
        statuses.apply_status(ctx.m, player, "fade_tether", 4.5)
        statuses.apply_status(ctx.m, player, "deaf", 4.5)


@effect("fade_wave", per_player=False)
def wave(ctx, _player, _spec):
    obj = ctx.obj
    distance = min(40, 4 * (1 + int((ctx.m.time - obj.start) / 0.355)))
    seen = obj.data.setdefault("seen", set())
    for player in select(ctx, {"who": "enemies", "area": "strip", "width": 20}):
        if player.pid not in seen and (player.pos - obj.a).dot(ctx.aim) <= distance and _eligible(ctx, player):
            seen.add(player.pid)
            _mark(ctx, player, 8)
            _decay(player, 80, 12)
            statuses.apply_status(ctx.m, player, "deaf", 8)


@effect("fade_prowl", per_player=False)
def prowl(ctx, _player, _spec):
    obj = place(ctx, thing("sensor", lasts=2.5, radius=0.45, hp=60, hit_radius=0.45, sprite="fade_prowler",
                           triggers=[on("tick", [step("fade_pursue")])]), ctx.source)
    obj.data["direction"] = ctx.aim


@effect("fade_pursue", per_player=False)
def pursue(ctx, _player, _spec):
    obj, match = ctx.obj, ctx.m
    level = obj.props["source_level"]
    target = match.players.get(obj.data.get("target"))
    if target is None or not target.alive or not _eligible(ctx, target):
        target = None
        obj.data.pop("target", None)
        for trail in match.effects:
            if (trail.owner == obj.owner and trail.data.get("fade_trail") and not trail.data.get("claimed")
                    and not trail.props.get("ended") and trail.until > match.time
                    and segment_circle_hit(trail.a, trail.b, obj.pos, 10)):
                target = match.players.get(trail.data["fade_trail"])
                if target and target.alive and _eligible(ctx, target):
                    trail.data["claimed"] = True
                    obj.data["tracking"] = True
                    break
                target = None
        if target is None:
            obj.data.pop("tracking", None)
            visible = [p for p in select(ctx, {"who": "enemies", "radius": 15, "sight": "all"})
                       if _eligible(ctx, p) and obj.data["direction"].dot((p.pos - obj.pos).normalized()) >= 0.6]
            target = min(visible, key=lambda p: (p.pos - obj.pos).length(), default=None)
        if target is not None:
            obj.data["target"] = target.pid
    direction, speed = obj.data["direction"], 10
    if target is not None:
        offset = target.pos - obj.pos
        clear = match._line_clear(obj.pos, target.pos, level)
        if offset.length() <= 2.5 and clear:
            bite = obj.data.setdefault("bite", match.time + 0.6)
            obj.until = max(obj.until, bite + 0.1)
            if match.time >= bite:
                statuses.apply_status(match, target, "fade_nearsight", 2.75)
                obj.props["ended"] = True
            return
        obj.data.pop("bite", None)
        speed = 15 if obj.data.get("tracking") else 12
        if clear:
            direction = offset.normalized()
        else:
            if match.time >= obj.data.get("route_at", 0):
                grid = grid_for(match.world, frozenset(match.open_doors | match.broken_cover), tuple(match.ability_walls()))
                obj.data.update(route=deque(grid.path(obj.pos, target.pos, start_ground=level, goal_ground=target.level)),
                                route_at=match.time + 0.3)
            route = obj.data["route"]
            if route and (route[0] - obj.pos).length() < 0.3:
                route.popleft()
            if route:
                direction = (route[0] - obj.pos).normalized()
    walls = [w.rect for w in match.combat_walls() if w.top > level and match.wall_active(w)
             and (not w.on_deck or w.base <= level)]
    obj.pos = match._move_against_walls(obj.pos, obj.pos + direction * speed * ctx.dt, 0.35, walls, None)


def steer(match, player, cmd, _dt):
    if cmd.fire and not statuses.flag(match, player, "no_abilities"):
        for obj in reversed(match.effects):
            if (obj.owner == player.pid and obj.props.get("sprite") == "fade_prowler" and "target" not in obj.data
                    and not obj.props.get("ended") and match.time < obj.until):
                obj.data["direction"] = heading(player.facing if cmd.facing is None else cmd.facing)
                return replace(cmd, fire=False)
    return cmd


def tick(match, _commands, _dt):
    for e in match.effects:
        if pid := e.data.get("fade_trail"):
            player = match.players.get(pid)
            if player is None or not player.alive or statuses.has(match, player, "yoru_drift"):
                e.props["ended"] = True
            else:
                if (player.pos - e.b).length() > 5:
                    e.a = player.pos
                e.b = player.pos


COMMAND_FILTERS["fade"] = steer
MATCH_TICKS["fade"] = tick
