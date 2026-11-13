"""Skye's heal pool, steerable creatures and autonomous Seekers."""
from collections import deque
from dataclasses import replace

from gameplay.geometry import Vec, heading, segment_circle_hit
from gameplay.kit import statuses
from gameplay.kit.builtins import game_event, select
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place, remove_device
from gameplay.kit.registry import COMMAND_FILTERS, Ctx, effect
from gameplay.nav import grid_for


def _find(match, player, key):
    return next((e for e in match.effects if e.owner == player.pid and e.props.get("sprite") == f"skye_{key}"
                 and not e.props.get("ended") and e.until > match.time), None)


def _move(ctx, direction, distance):
    obj, match = ctx.obj, ctx.m
    level = obj.props["source_level"]
    walls = [w.rect for w in match.combat_walls() if w.top > level and (not w.on_deck or w.base <= level)
             and match.wall_active(w)]
    old = obj.pos
    obj.pos = match._move_against_walls(old, old + direction * distance, 0.32, walls, None)
    return old


@effect("skye_regrowth", per_player=False)
def regrowth(ctx, _target, _spec):
    owner = ctx.owner
    if owner.passive_state.get("skye_heal_pool", 100) <= 0:
        return False
    statuses.apply_status(ctx.m, owner, "skye_regrowth", 300)
    statuses.apply_status(ctx.m, owner, "skye_heal_pool", 300)


def _heal(match, player, dt):
    pool = player.passive_state.get("skye_heal_pool", 100.0)
    ctx = Ctx(match, player, player.team, player.pos, player.pos, heading(player.facing))
    allies = [p for p in select(ctx, {"who": "allies", "radius": 18, "sight": "all", "injured": True})
              if not match._deck_between(player, p)]
    if not allies:
        return
    amount = min(pool, dt * 20)
    for ally in allies:
        statuses._heal_whole(match, ally, amount, healer=player.pid)
    player.passive_state["skye_heal_pool"] = pool - amount
    if pool - amount <= 1e-6:
        player.status.pop("skye_regrowth", None)
        player.status.pop("skye_heal_pool", None)


@effect("skye_tiger", per_player=False)
def tiger(ctx, _target, _spec):
    obj = place(ctx, thing("sensor", delay=0.18, lasts=6, hp=80, hit_radius=0.5, radius=0.45,
                           sprite="skye_tiger", warning_sprite="skye_tiger", cancel_channel=True,
                           triggers=[on("tick", [step("skye_tiger_move")]),
                                     on("expire", [step("skye_tiger_end")])]), ctx.source)
    obj.props["on_remove"] = "skye_tiger_end"
    obj.data.update(direction=ctx.aim, movement=Vec(0, 0))
    ctx.owner.channel_until = obj.until
    ctx.owner.vel = Vec(0, 0)


@effect("skye_tiger_end", per_player=False)
def tiger_end(ctx, _target, _spec):
    if ctx.owner is not None:
        ctx.owner.channel_until = 0
        ctx.owner.equip_until = ctx.m.time + 0.7


@effect("skye_tiger_move", per_player=False)
def tiger_move(ctx, _target, _spec):
    obj, match = ctx.obj, ctx.m
    if ctx.owner is None or not ctx.owner.alive:
        remove_device(match, obj, "cancel")
        return
    if "leap" not in obj.data:
        move = obj.data["movement"]
        _move(ctx, move.normalized(), min(1, move.length()) * 7 * ctx.dt)
        return
    distance = min(obj.data["leap"], 20 * ctx.dt)
    old = _move(ctx, obj.data["direction"], distance)
    ctx.point = obj.pos
    level = obj.props["source_level"]
    victim = next((p for p in match.players.values() if p.alive and p.team != ctx.team and p.level == level
                   and not statuses.flag(match, p, "intangible") and segment_circle_hit(old, obj.pos, p.pos, 0.6)), None)
    obj.data["leap"] -= distance
    if victim is None and obj.data["leap"] > 0 and (obj.pos - old).length() >= distance * 0.9:
        return
    if victim is not None:
        match._damage(ctx.owner, victim, 30, "body", "ability:Trailblazer")
    for player in select(ctx, {"who": "everyone", "radius": 3.5, "sight": "walls"}):
        if not statuses.flag(match, player, "intangible"):
            statuses.apply_status(match, player, "concuss", 4 - 1.5 * (player.pos - obj.pos).length() / 3.5)
    game_event(match, "blast", {"pos": (obj.pos.x, obj.pos.y), "radius": 3.5, "pid": obj.owner})
    remove_device(match, obj, "complete")


@effect("skye_hawk", per_player=False)
def hawk(ctx, _target, _spec):
    if obj := _find(ctx.m, ctx.owner, "hawk"):
        obj.data.setdefault("burst_at", min(obj.until, ctx.m.time + 0.3))
        return
    obj = place(ctx, thing("sensor", lasts=2, radius=0.4, sprite="skye_hawk",
                           triggers=[on("tick", [step("skye_hawk_move")]),
                                     on("expire", [step("skye_flash")])]), ctx.source)
    obj.data["direction"] = ctx.aim
    statuses.apply_status(ctx.m, ctx.owner, "skye_hawk", 2)


@effect("skye_hawk_move", per_player=False)
def hawk_move(ctx, _target, _spec):
    _move(ctx, ctx.obj.data["direction"], 18 * ctx.dt)
    if ctx.m.time >= ctx.obj.data.get("burst_at", float("inf")):
        flash(replace(ctx, point=ctx.obj.pos), None, {})
        ctx.obj.props["ended"] = True


@effect("skye_flash", per_player=False)
def flash(ctx, _target, _spec):
    duration = 1 + 1.25 * min(1, (ctx.m.time - ctx.obj.start) / 0.75)
    seen = False
    for player in select(ctx, {"who": "everyone", "radius": 35, "sight": "all", "facing": 180}):
        if not statuses.flag(ctx.m, player, "intangible"):
            statuses.apply_status(ctx.m, player, "blind", duration)
            seen |= player.team != ctx.team
    if ctx.owner is not None:
        ctx.owner.status.pop("skye_hawk", None)
    game_event(ctx.m, "flash", {"pos": (ctx.point.x, ctx.point.y), "radius": 35, "pid": ctx.obj.owner})
    if seen:
        game_event(ctx.m, "sound_fx", {"key": "ab_reveal", "pos": (ctx.source.x, ctx.source.y), "radius": 24})


@effect("skye_seekers", per_player=False)
def seekers(ctx, _target, _spec):
    enemies = sorted((p for p in ctx.m.players.values() if p.alive and p.team != ctx.team),
                     key=lambda p: (p.pos - ctx.source).length())[:3]
    if not enemies:
        return False
    for index, player in enumerate(enemies):
        obj = place(ctx, thing("sensor", lasts=15, hp=120, hit_radius=0.45, radius=0.45, sprite="skye_seeker",
                               triggers=[on("tick", [step("skye_seek")])]),
                    ctx.source + ctx.aim.rotated(90) * (index - (len(enemies) - 1) / 2) * 0.7)
        obj.data["target"] = player.pid


@effect("skye_seek", per_player=False)
def seek(ctx, _target, _spec):
    obj, match = ctx.obj, ctx.m
    target = match.players.get(obj.data["target"])
    if target is None or not target.alive:
        remove_device(match, obj, "cancel")
        return
    offset = target.pos - obj.pos
    level = obj.props["source_level"]
    if offset.length() <= 0.8 and level == target.level and not statuses.flag(match, target, "intangible"):
        statuses.apply_status(match, target, "skye_seeker_sight", 3)
        statuses.apply_status(match, target, "skye_seeker_slow", 5)
        remove_device(match, obj, "complete")
        return
    if match.time >= obj.data.get("path_at", 0):
        grid = grid_for(match.world, frozenset(match.open_doors | match.broken_cover), tuple(match.ability_walls()))
        path = [target.pos] if grid.line_free(obj.pos, target.pos, level, target.level) else grid.path(
            obj.pos, target.pos, start_ground=level, goal_ground=target.level)
        obj.data.update(path=deque(path), path_at=match.time + 0.35)
    path = obj.data["path"]
    if path:
        delta = path[0] - obj.pos
        if delta.length() < 0.15:
            path.popleft()
        else:
            _move(ctx, delta.normalized(), min(delta.length(), 6 * ctx.dt))
            obj.props["source_level"] = match.world.floor_level(obj.pos, level + 0.25)


def filter_command(match, player, cmd, dt):
    facing = player.facing if cmd.facing is None else cmd.facing
    suppressed = statuses.flag(match, player, "no_abilities")
    if obj := _find(match, player, "tiger"):
        if suppressed or (cmd.ability == "Q" and player.prev_ability != "Q"):
            remove_device(match, obj, "cancel")
            return None
        if match.time >= obj.start and "leap" not in obj.data:
            player.facing = facing
            obj.data.update(direction=heading(facing), movement=Vec(cmd.move_x, cmd.move_y).rotated(facing))
            if cmd.fire and not player.prev_fire:
                obj.data["leap"] = 12.0
        return None
    if statuses.has(match, player, "skye_regrowth"):
        if suppressed or cmd.slot or cmd.ability:
            player.status.pop("skye_regrowth", None)
            return replace(cmd, ability=None) if cmd.ability == "C" else cmd
        if cmd.fire:
            _heal(match, player, dt)
            return replace(cmd, fire=False, alt_fire=False)
    if not suppressed and cmd.fire and (obj := _find(match, player, "hawk")):
        obj.data["direction"] = heading(facing)
        return replace(cmd, fire=False)
    return cmd


COMMAND_FILTERS["skye"] = filter_command
