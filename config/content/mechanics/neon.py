"""Neon's Battery, electric utility and beam."""
from dataclasses import replace

from gameplay.geometry import Rect, Vec, heading
from gameplay.kit import statuses
from gameplay.kit.builtins import game_event
from gameplay.kit.dsl import event, on, status, thing
from gameplay.kit.engine import place
from gameplay.kit.registry import COMMAND_FILTERS, MATCH_TICKS, effect

SPRINT, ULT, SLIDE = "neon_sprint", "neon_overdrive", "neon_slide"


@effect("neon_lane", per_player=False)
def lane(ctx, _target, _spec):
    side = ctx.aim.rotated(90) * 1.75
    for offset in (side, side * -1):
        start = ctx.source + offset - ctx.aim * 1.5
        place(ctx, thing("wall", delay=0.4, lasts=4, shape="line", length=46.5, along=True,
                         forward=True, sprite="neon_lane"), start)


def _impact(match, source, aim, reach, level):
    nearest = reach
    wall = None
    candidates = [w.rect for w in match.combat_walls() if w.top > level and match.wall_active(w)
                  and (not w.on_deck or w.base <= level)]
    bounds = Rect(0, 0, match.world.width, match.world.height)
    boundary = bounds.ray_interval(source, aim)
    if boundary and boundary[1] < nearest:
        nearest, wall = boundary[1], bounds
    for rect in candidates:
        hit = rect.ray_interval(source, aim)
        if hit is not None and 0 <= hit[0] < nearest:
            nearest, wall = hit[0], rect
    return source + aim * nearest, wall


@effect("neon_bolt", per_player=False)
def bolt(ctx, _target, _spec):
    reach = min(ctx.ability["range"], max(2, ctx.owner.cursor_depth))
    first, wall = _impact(ctx.m, ctx.source, ctx.aim, reach, ctx.owner.level)
    aim = ctx.aim
    if wall is not None:
        x_edge = min(abs(first.x - wall.x0), abs(first.x - wall.x1))
        y_edge = min(abs(first.y - wall.y0), abs(first.y - wall.y1))
        aim = Vec(-aim.x, aim.y) if x_edge <= y_edge else Vec(aim.x, -aim.y)
    second, _ = _impact(ctx.m, first + aim * 0.05, aim, 8, ctx.owner.level)
    for origin, point, delay in ((ctx.source, first, 0), (first, second, 0.24)):
        place(replace(ctx, source=origin), thing("blast", delay=delay, lasts=0.24, radius=0.3,
                                                thrown=True, sprite="neon_bolt"), point)
        place(ctx, thing("zone", delay=1.24 + delay, lasts=0.22, radius=5, sprite="neon_relay",
                         warning_sprite="neon_relay", triggers=[on("start", [status("concuss", 2.5),
                         event("blast")], who="everyone")]), point)


@effect("neon_sprint", per_player=False)
def sprint(ctx, _target, _spec):
    player = ctx.owner
    if statuses.has(ctx.m, player, SPRINT):
        player.status.pop(SPRINT, None)
        player.equip_until = max(player.equip_until, ctx.m.time + 0.7)
    elif statuses.has(ctx.m, player, ULT):
        return False
    elif player.passive_state.get("neon_battery", 100) < 2:
        game_event(ctx.m, "neon_battery_insufficient", {"pid": player.pid})
        return False
    else:
        statuses.apply_status(ctx.m, player, SPRINT, float("inf"))
        player.reload_until = player.burst_left = 0


@effect("neon_overdrive", per_player=False)
def overdrive(ctx, _target, _spec):
    player = ctx.owner
    player.status.pop(SPRINT, None)
    player.passive_state.update(neon_battery=100.0, neon_ammo=40.0, neon_next_shot=ctx.m.time + 1,
                                neon_recharge_at=ctx.m.time + 1)
    player.charges["E"] = 1
    statuses.apply_status(ctx.m, player, ULT, float("inf"))
    player.overdrive_until = float("inf")
    player.equip_until = ctx.m.time + 1
    player.reload_until = player.burst_left = 0


@effect("neon_refill", per_player=False)
def refill(ctx, _target, _spec):
    if statuses.has(ctx.m, ctx.owner, ULT):
        ctx.owner.passive_state["neon_battery"] = 100.0


def _end(player):
    player.status.pop(SPRINT, None)
    player.status.pop(ULT, None)
    player.overdrive_until = 0


def _slide(match, player, cmd, facing):
    if (not player.charges.get("E") or player.z > 0.001 or cmd.move_y < 0
            or not (cmd.move_x or cmd.move_y) or match.phase not in ("live", "planted")):
        return
    player.charges["E"] -= 1
    player.status.pop(SPRINT, None)
    player.dash_until = match.time + 0.6
    player.dash_vel = Vec(cmd.move_x, cmd.move_y).normalized().rotated(facing) * (7 / 0.6)
    statuses.apply_status(match, player, SLIDE, 0.6)
    player.equip_until = max(player.equip_until, match.time + 0.2)


def filter_command(match, player, cmd, dt):
    sprinting, ult = statuses.has(match, player, SPRINT), statuses.has(match, player, ULT)
    if not (sprinting or ult):
        return replace(cmd, crouch=True) if statuses.has(match, player, SLIDE) else cmd
    if statuses.flag(match, player, "no_abilities"):
        _end(player)
        return replace(cmd, fire=False, alt_fire=False)
    if cmd.slot and sprinting:
        _end(player)
        player.equip_until = match.time + 0.7
        return cmd
    facing = player.facing if cmd.facing is None else cmd.facing
    if cmd.alt_fire and not player.prev_alt and not (ult and cmd.fire):
        _slide(match, player, cmd, facing)
    if ult and cmd.fire and not statuses.flag(match, player, "no_fire") and not player.spike_equipped \
            and match.phase in ("live", "planted") and not match.deathmatch_spawn_protected(player):
        state = player.passive_state
        threshold = 1 if state.get("neon_beam_firing") else 10
        if match.time >= max(state["neon_next_shot"], player.equip_until) and state["neon_ammo"] >= threshold:
            player.facing = facing
            player.cursor_depth = max(0, min(120, cmd.cursor_depth))
            match._fire_bullet(player, match.ability_weapons["neon_beam"], 1)
            state["neon_ammo"] -= 1
            state["neon_next_shot"] = match.time + 0.05
            state["neon_recharge_at"] = match.time + 0.5
            state["neon_beam_firing"] = state["neon_ammo"] >= 1
    if not cmd.fire:
        player.passive_state.pop("neon_beam_firing", None)
    return replace(cmd, fire=False, alt_fire=False, reload=False,
                   crouch=cmd.crouch or statuses.has(match, player, SLIDE))


def tick(match, _commands, dt):
    for player in match.players.values():
        if player.agent != "neon":
            continue
        state = player.passive_state
        ult = statuses.has(match, player, ULT)
        active = ult or statuses.has(match, player, SPRINT)
        previous = state.get("neon_battery", 100)
        state["neon_battery"] = max(0, min(100, previous + dt * (-6.25 if active else 100 / 60)))
        if player.alive and active:
            if state["neon_battery"] == 0 < previous:
                game_event(match, "neon_battery_empty", {"pid": player.pid})
            elif state["neon_battery"] < 20 <= previous:
                game_event(match, "neon_battery_low", {"pid": player.pid})
        if not player.alive or state["neon_battery"] == 0:
            _end(player)
        elif ult and match.time >= state["neon_recharge_at"]:
            state["neon_ammo"] = min(40, state["neon_ammo"] + dt * 20)


COMMAND_FILTERS["neon"] = filter_command
MATCH_TICKS["neon"] = tick
