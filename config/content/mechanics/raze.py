"""Raze's autonomous bot, satchel boost, cluster grenades and rocket."""
from dataclasses import replace

from gameplay.geometry import Vec, heading, segment_circle_hit
from gameplay.kit import statuses
from gameplay.kit.builtins import damage_map_cover, game_event, select
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place
from gameplay.kit.registry import COMMAND_FILTERS, effect


def _blast(ctx, radius, inner, low, high, who, cover, *, self_damage=False):
    match = ctx.m
    for player in select(ctx, {"who": who, "radius": radius, "sight": "walls"}):
        distance = (player.pos - ctx.point).length()
        fraction = max(0, distance - inner) / (radius - inner)
        match._damage(ctx.owner, player, round(high + (low - high) * fraction), "body",
                      f"ability:{ctx.ability['name']}")
    if self_damage and ctx.owner is not None and (ctx.owner.pos - ctx.point).length() <= radius:
        player = ctx.owner
        if match._line_clear(ctx.point, player.pos, player.level, ignore_effects=True):
            fraction = max(0, (player.pos - ctx.point).length() - inner) / (radius - inner)
            match._damage(player, player, round(high + (low - high) * fraction), "body",
                          f"ability:{ctx.ability['name']}")
    damage_map_cover(ctx, {"do": "damage", "amount": high, "cover_mult": cover, "radius": radius, "sight": "walls"})
    for device in list(match.effects):
        if (device is ctx.obj or device.team == ctx.team or not device.props.get("hit_radius")
                or device.props.get("ended") or (device.pos - ctx.point).length() > radius):
            continue
        if match._line_clear(ctx.point, device.pos, device.props["source_level"], ignore_effects=True):
            device.data["hp"] -= round(high * cover)
            if device.data["hp"] <= 0:
                from gameplay.kit.engine import remove_device
                remove_device(match, device, "destroy")
    game_event(match, "blast", {"pos": (ctx.point.x, ctx.point.y), "radius": radius,
                                "pid": ctx.owner.pid if ctx.owner else None})


@effect("raze_bot", per_player=False)
def bot(ctx, _player, _spec):
    device = place(ctx, thing("sensor", delay=0.7, lasts=4.3, hp=60, hit_radius=0.5,
                              radius=0.45, sprite="raze_bot", warning_sprite="raze_bot",
                              triggers=[on("tick", [step("raze_bot_move")])]), ctx.source)
    device.data["direction"] = ctx.aim


@effect("raze_bot_move", per_player=False)
def bot_move(ctx, _player, _spec):
    obj, match = ctx.obj, ctx.m
    if "explode_at" in obj.data:
        if match.time >= obj.data["explode_at"]:
            obj.props["ended"] = True
            _blast(ctx, 6, 2, 30, 80, "enemies", 2.5)
        return
    direction = obj.data["direction"]
    visible = [p for p in select(ctx, {"who": "enemies", "radius": 15, "sight": "all"})
               if not statuses.flag(match, p, "intangible")
               and direction.dot((p.pos - obj.pos).normalized()) >= 0.57]
    speed = 5.5
    if visible:
        target = min(visible, key=lambda p: (p.pos - obj.pos).length())
        offset = target.pos - obj.pos
        direction, speed = offset.normalized(), 8
        if offset.length() <= 2.5:
            obj.data["explode_at"] = match.time + 0.6
            obj.until = max(obj.until, obj.data["explode_at"] + 0.11)
            return
    old = obj.pos
    level = obj.props["source_level"]
    walls = [w.rect for w in match.combat_walls() if w.top > level and
             (not w.on_deck or w.base <= level) and match.wall_active(w)]
    delta = direction * (speed * ctx.dt)
    obj.pos = match._move_against_walls(old, old + delta, 0.35, walls, None)
    moved = obj.pos - old
    obj.data["direction"] = Vec(-direction.x if abs(moved.x) < abs(delta.x) * 0.5 else direction.x,
                                -direction.y if abs(moved.y) < abs(delta.y) * 0.5 else direction.y)


@effect("raze_pack", per_player=False)
def pack(ctx, _player, _spec):
    match, player = ctx.m, ctx.owner
    active = next((e for e in match.effects if e.owner == player.pid and e.props.get("raze_pack")
                   and not e.props.get("ended")), None)
    if active is not None:
        pack_burst(replace(ctx, obj=active, point=active.pos), None, {})
        active.props["ended"] = True
        return
    device = place(ctx, thing("sensor", lasts=5, radius=0.4, hp=20, hit_radius=0.4, sprite="raze_pack",
                              triggers=[on("expire", [step("raze_pack_burst")])]), ctx.point)
    device.props.update(raze_pack=True, on_remove="raze_pack_destroyed")
    statuses.apply_status(match, player, "raze_pack_active", 5)


@effect("raze_pack_destroyed", per_player=False)
def pack_destroyed(ctx, _player, _spec):
    if ctx.owner is not None:
        ctx.owner.status.pop("raze_pack_active", None)


@effect("raze_pack_burst", per_player=False)
def pack_burst(ctx, _player, _spec):
    if ctx.owner is not None:
        ctx.owner.status.pop("raze_pack_active", None)
    match = ctx.m
    for player in select(ctx, {"who": "everyone", "radius": 5, "sight": "walls"}):
        if statuses.flag(match, player, "intangible"):
            continue
        offset = player.pos - ctx.point
        direction = offset.normalized() if offset.length() > 0.05 else heading(player.facing)
        strength = max(0.15, 1 - offset.length() / 5)
        slow = statuses.mult(match, player, "dash_speed")
        player.dash_until = match.time + 0.28
        player.dash_vel = direction * (15 * strength)
        player.vz = max(player.vz, 6.5 * strength * slow)
    if match.time - ctx.obj.start >= 1.5:
        _blast(ctx, 5, 2, 20, 50, "enemies", 2.25)
    else:
        game_event(match, "blast", {"pos": (ctx.point.x, ctx.point.y), "radius": 5, "pid": ctx.obj.owner})


@effect("raze_cluster", per_player=False)
def cluster(ctx, _player, _spec):
    _blast(ctx, 5.5, 2.5, 1, 55, "everyone", 2.5)
    level = ctx.obj.props["source_level"]
    for angle in (45, 135, 225, 315):
        target = ctx.m._clip_to_walls(ctx.point, ctx.point + ctx.aim.rotated(angle) * 3, level)
        place(replace(ctx, source=ctx.point), thing("blast", lasts=0.667, radius=5.25, thrown=True,
                     sprite="raze_grenade", triggers=[on("expire", [step("raze_submunition")])]), target)


@effect("raze_submunition", per_player=False)
def submunition(ctx, _player, _spec):
    _blast(ctx, 5.25, 2.5, 1, 55, "everyone", 2.5)


@effect("raze_showstopper", per_player=False)
def showstopper(ctx, _player, _spec):
    player = ctx.owner
    statuses.apply_status(ctx.m, player, "raze_showstopper", 10)
    player.passive_state["raze_launcher_ready"] = ctx.m.time + 1.4
    player.equip_until = ctx.m.time + 1.4
    player.reload_until = player.burst_left = 0


def filter_command(match, player, cmd, _dt):
    if not statuses.has(match, player, "raze_showstopper"):
        return cmd
    if statuses.flag(match, player, "no_abilities") or cmd.slot or (cmd.ability == "X" and player.prev_ability != "X"):
        player.status.pop("raze_showstopper", None)
        return replace(cmd, ability=None) if cmd.ability == "X" else cmd
    if (cmd.fire and not player.prev_fire and match.time >= player.passive_state["raze_launcher_ready"]
            and match.phase in ("live", "planted") and not statuses.flag(match, player, "no_fire")
            and not match.deathmatch_spawn_protected(player)):
        from gameplay.kit.registry import Ctx
        aim = heading(player.facing if cmd.facing is None else cmd.facing)
        ability = match.agents[player.agent]["abilities"]["X"]
        ctx = Ctx(match, player, player.team, player.pos, player.pos, aim, ability=ability, key="X")
        place(ctx, thing("sensor", lasts=2.5, radius=0.32, sprite="raze_rocket",
                         triggers=[on("tick", [step("raze_rocket_move")])]), player.pos)
        player.status.pop("raze_showstopper", None)
        player.equip_until = match.time + 0.4
        player.dash_until, player.dash_vel = match.time + 0.18, aim * -11
        game_event(match, "sound_fx", {"key": "ab_blast", "pos": (player.pos.x, player.pos.y), "radius": 50})
    return replace(cmd, fire=False, alt_fire=False, reload=False)


COMMAND_FILTERS["raze"] = filter_command


@effect("raze_rocket_move", per_player=False)
def rocket_move(ctx, _player, _spec):
    obj, match = ctx.obj, ctx.m
    source = obj.pos
    requested = source + ctx.aim * (40 * ctx.dt)
    level = obj.props["source_level"]
    distance = (requested - source).length()
    for wall in match.combat_walls():
        if wall.top <= level or (wall.on_deck and wall.base > level) or not match.wall_active(wall):
            continue
        hit = wall.rect.ray_interval(source, ctx.aim)
        if hit is not None and hit[1] > 0:
            distance = min(distance, max(0, hit[0] - 0.03))
    wall_impact = distance < (requested - source).length()
    end = source + ctx.aim * distance
    for target in [*match.players.values(), *match.effects]:
        if target is obj or target is ctx.owner:
            continue
        if hasattr(target, "alive"):
            valid = target.alive and target.level == level and not statuses.flag(match, target, "intangible")
        else:
            valid = target.props.get("hit_radius") and not target.props.get("ended") and target.props["source_level"] == level
        if valid and segment_circle_hit(source, end, target.pos, 0.48):
            distance = min(distance, max(0, (target.pos - source).dot(ctx.aim) - 0.35))
            wall_impact = True
    obj.pos = source + ctx.aim * distance
    if wall_impact or not (0 < obj.pos.x < match.world.width and 0 < obj.pos.y < match.world.height):
        obj.props["ended"] = True
        _blast(replace(ctx, point=obj.pos), 7, 4, 30, 150, "enemies", 10, self_damage=True)
