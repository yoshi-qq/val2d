"""Gekko's creatures, globule reclaim, and Wingman's objective actions."""
from collections import deque
from dataclasses import replace

from gameplay.geometry import Vec, heading
from gameplay.kit import statuses
from gameplay.kit.builtins import game_event, select
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place, remove_device, schedule_ability_return
from gameplay.kit.registry import COMMAND_FILTERS, effect, target
from gameplay.nav import grid_for

SPRITES = {"C": "mosh", "Q": "wingman", "E": "dizzy", "X": "thrash"}


def _globule(ctx):
    owner = ctx.owner
    if owner is None:
        return
    if ctx.key == "X":
        if owner.passive_state.get("gekko_thrash_globule"):
            return
        owner.passive_state["gekko_thrash_globule"] = True
    globule = place(ctx, thing("zone", lasts=20, radius=0.45, sprite=f"gekko_globule_{SPRITES[ctx.key]}"), ctx.point)
    globule.props["gekko_globule"] = True


@effect("gekko_globule", per_player=False)
def globule(ctx, _player, _spec):
    _globule(ctx)


def reclaim(match, player, cmd, dt):
    nearby = [
        e for e in match.effects if e.owner == player.pid and e.props.get("gekko_globule")
        and not e.props.get("ended") and match.time < e.until and (player.pos - e.pos).length() <= 1.5
        and match._line_clear(player.pos, e.pos, player.level, ignore_effects=True)
    ] if cmd.interact and not statuses.flag(match, player, "no_abilities") else []
    if not nearby:
        player.passive_state.pop("gekko_reclaim", None)
        return False
    item = min(nearby, key=lambda e: (player.pos - e.pos).length())
    current, elapsed = player.passive_state.get("gekko_reclaim", (None, 0.0))
    elapsed = elapsed + dt if current is item else dt
    player.passive_state["gekko_reclaim"] = (item, elapsed)
    if elapsed >= 1.5:
        item.props["ended"] = True
        delay = match.deathmatch_rules["globule_reclaim_time"] if match.mode == "deathmatch" else 15
        schedule_ability_return(match, player, item.props["key"], delay)
        player.passive_state.pop("gekko_reclaim", None)
    return True


@effect("gekko_mosh_hit")
def mosh_hit(ctx, player, _spec):
    amount = 50 if (player.pos - ctx.point).length() <= 5.5 else 25
    ctx.m._damage(ctx.owner, player, amount if player.team != ctx.team else amount // 3, "body", "Mosh Pit")


@target("gekko_spike")
def spike_target(match, player, _spec):
    cursor = player.pos + heading(player.facing) * min(player.cursor_depth, 40)
    if match.phase == "planted" and match.side(player.team) == "defense":
        if match.spike_pos is not None and (match.spike_pos - cursor).length() <= 2:
            return match.spike_pos
    if match.phase == "live" and match.spike_carrier == player.pid and match.world.site_at(cursor) is not None:
        return cursor
    return None


def _creature(ctx, sprite, hp, duration, tick, **props):
    device = place(ctx, thing("sensor", lasts=duration, radius=0.42, sprite=f"gekko_{sprite}", hp=hp,
                              hit_radius=0.5, triggers=[on("tick", [step(tick)]),
                                                       on("expire", [step("gekko_finish")])]), ctx.source)
    device.props.update(on_remove="gekko_finish", **props)
    return device


def _move(ctx, direction, speed):
    obj, match = ctx.obj, ctx.m
    old = obj.pos
    level = obj.props["source_level"]
    reach = level + 0.25
    walls = [w.rect for w in match.combat_walls() if (w.full or w.top > reach)
             and (not w.on_deck or w.base <= reach) and match.wall_active(w)]
    point = old + direction * speed * ctx.dt
    obj.pos = match._move_against_walls(old, point, 0.38, walls, None)
    if match.world.ground_height(obj.pos, reach) > reach:
        obj.pos = old
    obj.props["source_level"] = match.world.floor_level(obj.pos, reach)
    return obj.pos - old


def _objective_path(match, origin, goal, start_level, inactive, barriers):
    grid = grid_for(match.world, inactive, barriers)
    level = match.world.ground_height(goal)
    if grid.line_free(origin, goal, start_level, level):
        return [goal]
    return grid.path(origin, goal, start_ground=start_level, goal_ground=level)


@effect("gekko_wingman", per_player=False)
def wingman(ctx, _player, spec):
    match, player = ctx.m, ctx.owner
    if spec.get("objective"):
        inactive = frozenset(match.open_doors | match.broken_cover)
        barriers = tuple(match.ability_walls())
        start_level = player.ground / float(match._mv["level_height"])
        path = _objective_path(match, player.pos, ctx.point, start_level, inactive, barriers)
        if not path:
            return False
        carrying = match.spike_carrier == player.pid
        device = _creature(ctx, "wingman", 60, 15, "gekko_objective", gekko_objective=True)
        device.data.update(path=deque(path), carrying=carrying, progress=0.0, goal=ctx.point)
        device.data["route_walls"] = inactive, barriers
        if carrying:
            match.spike_carrier, match.spike_pos = None, None
            player.spike_equipped = False
            player.plant_progress = 0
    else:
        device = _creature(ctx, "wingman", 60, 5, "gekko_scout")
        device.data["direction"] = ctx.aim


@effect("gekko_objective", per_player=False)
def objective(ctx, _player, _spec):
    obj, match, owner = ctx.obj, ctx.m, ctx.owner
    carrying = obj.data["carrying"]
    goal = obj.data["goal"]
    valid = (match.phase == "live" if carrying else match.phase == "planted" and match.spike_pos == goal)
    if owner is None or not valid:
        remove_device(match, obj, "cancel")
        return
    path = obj.data["path"]
    if path or obj.data.get("route_blocked"):
        walls = frozenset(match.open_doors | match.broken_cover), tuple(match.ability_walls())
        if walls != obj.data["route_walls"]:
            path = deque(_objective_path(match, obj.pos, goal, obj.props["source_level"], *walls))
            obj.data.update(path=path, route_walls=walls, route_blocked=not path)
        if obj.data.get("route_blocked"):
            return
    if path:
        offset = path[0] - obj.pos
        if offset.length() <= 0.13:
            path.popleft()
        else:
            _move(ctx, offset.normalized(), min(6.3, offset.length() / ctx.dt))
        return
    if carrying:
        site = match.world.site_at(goal, obj.props["source_level"])
        if site is None:
            remove_device(match, obj, "cancel")
            return
        if not obj.data["progress"]:
            obj.data["spike_audio"] = {"pid": owner.pid, "audio_id": -owner.pid, "key": "spike_plant",
                                       "pos": (goal.x, goal.y), "started": match.time}
            game_event(match, "plant_start", obj.data["spike_audio"])
        obj.data["progress"] += ctx.dt
        if obj.data["progress"] >= float(match._spike["plant_time"]):
            obj.data["carrying"] = False
            match._plant(owner, site.name, point=goal, level=obj.props["source_level"])
            remove_device(match, obj, "complete")
        return
    defuse_dt = match._spike_defuse_dt(ctx.dt)
    player_defuser = match.spike_player_defuser
    if (player_defuser is not None and match._can_defuse(*player_defuser)) or defuse_dt <= 0 or any(
        other is not obj and other.data.get("defusing") and not other.props.get("ended")
        for other in match.effects
    ):
        return
    prior_defuser = match.spike_device_defuser_at_tick_start
    if match.spike_player_defuser_at_tick_start is not None or (prior_defuser is not None and prior_defuser is not obj):
        if match.time >= match._spike_detonation_at():
            return
        defuse_dt = 0.0
    checkpoint = float(match._spike["defuse_checkpoint"])
    if not obj.data.get("defusing"):
        obj.data["progress"] = checkpoint if match.spike_half_defused else 0.0
        key = "spike_defuse_half" if match.spike_half_defused else "spike_defuse"
        obj.data["spike_audio"] = {"pid": owner.pid, "audio_id": -owner.pid, "key": key, "pos": (goal.x, goal.y),
                                   "started": match.time, "resumed": match.spike_half_defused}
        game_event(match, "defuse_start", obj.data["spike_audio"])
    obj.data["progress"] = match._advance_spike_defuse(owner, obj.data["progress"], defuse_dt)
    obj.data["defusing"] = True
    if obj.data["progress"] >= float(match._spike["defuse_time"]):
        match._complete_defuse(owner)
        remove_device(match, obj, "complete")


@effect("gekko_scout", per_player=False)
def scout(ctx, _player, _spec):
    obj = ctx.obj
    direction = obj.data["direction"]
    if windup := obj.data.get("windup"):
        if ctx.m.time >= windup:
            for player in select(ctx, {"who": "everyone", "radius": 7, "sight": "all"}):
                if direction.dot((player.pos - obj.pos).normalized()) >= 0.5:
                    statuses.apply_status(ctx.m, player, "concuss", 2.5)
            remove_device(ctx.m, obj, "complete")
        return
    targets = [p for p in select(ctx, {"who": "enemies", "radius": 15, "sight": "all"})
               if direction.dot((p.pos - obj.pos).normalized()) >= 0.5]
    if targets:
        offset = min(targets, key=lambda p: (p.pos - obj.pos).length()).pos - obj.pos
        direction = offset.normalized()
        if offset.length() <= 6:
            obj.data.update(windup=ctx.m.time + 0.6, direction=direction)
            obj.until = max(obj.until, obj.data["windup"] + 0.1)
            return
    moved = _move(ctx, direction, 6.3)
    obj.data["direction"] = Vec(-direction.x if abs(moved.x) < abs(direction.x) * 3 * ctx.dt else direction.x,
                                -direction.y if abs(moved.y) < abs(direction.y) * 3 * ctx.dt else direction.y)


@effect("gekko_dizzy", per_player=False)
def dizzy(ctx, _player, _spec):
    device = _creature(ctx, "dizzy", 20, 1.65, "gekko_plasma")
    device.data["landing"] = ctx.point
    device.data["seen"] = set()


@effect("gekko_plasma", per_player=False)
def plasma(ctx, _player, _spec):
    obj = ctx.obj
    elapsed = ctx.m.time - obj.start
    obj.pos = ctx.point = ctx.source + (obj.data["landing"] - ctx.source) * min(1, elapsed / 0.65)
    if elapsed < 0.65:
        return
    for target in select(ctx, {"who": "enemies", "radius": 45, "sight": "all"}):
        if target.pid in obj.data["seen"]:
            continue
        obj.data["seen"].add(target.pid)
        place(ctx, thing("zone", delay=0.35, lasts=0.13, radius=2.5, sprite="gekko_plasma",
                                triggers=[on("start", [step("gekko_plasma_hit")], who="everyone", sight="walls")]),
                     target.pos)


@effect("gekko_plasma_hit")
def plasma_hit(ctx, player, _spec):
    if not statuses.flag(ctx.m, player, "intangible"):
        statuses.apply_status(ctx.m, player, "gekko_plasma_blind", 2)


@effect("gekko_thrash", per_player=False)
def thrash(ctx, _player, _spec):
    player = ctx.owner
    device = _creature(ctx, "thrash", 180, 6.6, "gekko_drive", cancel_channel=True)
    device.data.update(direction=ctx.aim, ready=ctx.m.time + 0.6)
    player.status.pop("gekko_thrash_ready", None)
    player.channel_until = device.until


def drive_command(match, player, cmd):
    obj = next((e for e in match.effects if e.owner == player.pid and e.props.get("cancel_channel")
                and e.props.get("sprite") == "gekko_thrash" and not e.props.get("ended")), None)
    if obj is None:
        return False
    if cmd.ability == "X" and player.prev_ability != "X":
        remove_device(match, obj, "cancel")
        return True
    if match.time >= obj.data["ready"]:
        if cmd.facing is not None and not obj.data.get("lunge"):
            obj.data["direction"] = heading(cmd.facing)
        obj.data["paused"] = cmd.move_y < 0
        if cmd.fire and not player.prev_fire:
            if obj.data.get("lunge"):
                obj.data["lunge"] = match.time
            else:
                obj.data["lunge"] = match.time + 0.8
    return True


def filter_command(match, player, cmd, dt):
    if drive_command(match, player, cmd):
        return None
    busy_with_spike = match.phase == "planted" and match.side(player.team) == "defense" and match.near_spike(player, 1.5)
    if busy_with_spike:
        player.passive_state.pop("gekko_reclaim", None)
    elif reclaim(match, player, cmd, dt):
        return replace(cmd, interact=False)
    return cmd


COMMAND_FILTERS["gekko"] = filter_command


@effect("gekko_drive", per_player=False)
def drive(ctx, _player, _spec):
    obj, owner, match = ctx.obj, ctx.owner, ctx.m
    if owner is None or not owner.alive:
        remove_device(match, obj, "cancel")
        return
    if match.time < obj.data["ready"]:
        return
    obj.props["aim"] = (obj.data["direction"].x, obj.data["direction"].y)
    lunge = obj.data.get("lunge")
    if lunge is not None and match.time >= lunge:
        for player in select(ctx, {"who": "everyone", "radius": 5, "sight": "walls"}):
            if not statuses.flag(match, player, "intangible"):
                statuses.apply_status(match, player, "gekko_detained", 6)
        game_event(match, "blast", {"pos": (obj.pos.x, obj.pos.y), "radius": 5, "pid": owner.pid})
        remove_device(match, obj, "complete")
    elif lunge is not None or not obj.data.get("paused"):
        _move(ctx, obj.data["direction"], 16.25 if lunge is not None else 11.22)


@effect("gekko_finish", per_player=False)
def finish(ctx, _player, _spec):
    obj, match, owner = ctx.obj, ctx.m, ctx.owner
    if audio := obj.data.pop("spike_audio", None):
        kind = "plant_stop" if audio["key"] == "spike_plant" else "defuse_stop"
        game_event(match, kind, {"pid": audio["pid"], "audio_id": audio["audio_id"]})
    if obj.data.get("carrying"):
        match.spike_pos = obj.pos
        match.spike_ground = match.world.ground_height(obj.pos, obj.props["source_level"])
        if owner is not None:
            owner.dropped_at = match.time
    if ctx.key == "X" and owner is not None:
        owner.channel_until = 0
        owner.equip_until = max(owner.equip_until, match.time + 0.7)
    _globule(ctx)
