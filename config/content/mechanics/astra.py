"""Astra's shared stars and map-wide wall."""
from gameplay.geometry import Rect, Vec, heading
from gameplay.kit import statuses
from gameplay.kit.builtins import e_pull, e_sound, select
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place, remove_device, schedule_ability_return
from gameplay.kit.registry import Ctx, MATCH_TICKS, effect, target


def _stars(match, player):
    return [e for e in match.effects if e.owner == player.pid and e.props.get("sprite") == "astra_star"
            and not e.props.get("ended")]


@target("astra_star")
def star_target(match, player, _spec):
    aim = player.pos + heading(player.facing) * player.cursor_depth
    star = min(_stars(match, player), key=lambda e: (e.pos - aim).length(), default=None)
    return star.pos if star is not None and (star.pos - aim).length() <= 2 else None


@effect("astra_place_star", per_player=False)
def place_star(ctx, _player, spec):
    match, player, point = ctx.m, ctx.owner, ctx.point
    reclaim = spec.get("reclaim", False)
    if match.phase not in ("buy", "live", "planted") or not player.alive or player.duel_id:
        return
    if (player.channel_until > match.time or statuses.flag(match, player, "no_abilities")
            or match.in_deathmatch_spawn(player)):
        return
    if (not 0 <= point.x <= match.world.width or not 0 <= point.y <= match.world.height
            or match.world.drop_recovery(point) is not None):
        return
    nearby = [star for star in _stars(match, player) if (star.pos - point).length() < 1]
    if reclaim:
        if nearby and (match.phase == "buy" or nearby[0].start <= match.time):
            remove_device(match, nearby[0], "recall")
        return
    if nearby:
        return
    if not match.cheat("infinite_abilities"):
        if player.charges.get("E", 0) <= 0:
            return
        player.charges["E"] -= 1
        if player.temporary_charges.get("E", 0):
            player.temporary_charges["E"] -= 1
        else:
            for purchase in reversed(player.purchases):
                if purchase["item"] == "E":
                    player.purchases.remove(purchase)
                    break
    ctx = Ctx(match, player, player.team, point, player.pos, heading(player.facing), key="E")
    star = place(ctx, thing("sensor", delay=0.65, lasts=3600, radius=0.45, sprite="astra_star",
                             hidden="enemies", detect_range=12, recall_recharge=25,
                             on_remove="astra_recall"), point)
    star.props.update(remote_recall=True, source_level=match.world.floor_level(point))


def _smoke(ctx, point, level, seconds, delay=0):
    sprite = "astra_smoke" if seconds > 1 else "astra_dissipate"
    obj = place(ctx, thing("smoke", delay=delay, lasts=seconds, radius=4.75, sprite=sprite,
                            warning_sprite=sprite,
                            fade_sound={"key": "cast_whoosh", "lead": 1.5, "radius": 14} if seconds > 1 else None), point)
    obj.props.update(source_level=level, settled_ground=level)


@effect("astra_recall", per_player=False)
def recall(ctx, _player, spec):
    if spec["reason"] != "recall" or ctx.owner is None:
        return
    ctx.obj.props.pop("recall_recharge", None)
    if ctx.m.phase == "buy":
        ctx.owner.charges["E"] = min(5, ctx.owner.charges.get("E", 0) + 1)
    else:
        if ctx.m.mode == "deathmatch":
            schedule_ability_return(ctx.m, ctx.owner, "E", ctx.m.deathmatch_rules["astra"]["dissipate_time"])
        else:
            ctx.owner.passive_state.setdefault("astra_returns", []).append(ctx.m.time + 25)
        _smoke(ctx, ctx.point, ctx.obj.props["source_level"], 1)


@effect("astra_activate", per_player=False)
def activate(ctx, _player, spec):
    match, owner, mode = ctx.m, ctx.owner, spec["mode"]
    if match.phase not in ("live", "planted"):
        return False
    star = next((e for e in _stars(match, owner) if e.pos == ctx.point and e.start <= match.time), None)
    if star is None:
        return False
    cooldowns = owner.passive_state.setdefault("astra_cooldowns", {})
    queue = cooldowns.setdefault(mode, [])
    queue[:] = [ready for ready in queue if ready > match.time]
    if len(queue) >= (2 if mode == "smoke" else 1):
        return False
    cooldown = {"well": 60, "nova": 60, "smoke": 35}[mode]
    if match.mode == "deathmatch":
        cooldown = match.deathmatch_rules["astra"]["activation_cooldowns"][mode]
    queue.append(max(queue, default=match.time) + cooldown)
    star.props["ended"] = True
    level = star.props["source_level"]
    if mode == "smoke":
        _smoke(ctx, star.pos, level, 14.25, 0.45)
    elif mode == "nova":
        zone = place(ctx, thing("zone", delay=1, lasts=0.3, radius=4.75, sprite="astra_nova",
                                warning_sprite="astra_nova",
                                triggers=[on("start", [step("astra_burst", mode="nova")])]), star.pos)
        zone.props["source_level"] = level
    else:
        zone = place(ctx, thing("zone", delay=1.25, lasts=2, radius=4.75, sprite="astra_well",
                                warning_sprite="astra_well",
                                triggers=[on("tick", [step("astra_pull")]),
                                          on("expire", [step("astra_burst", mode="well")])]), star.pos)
        zone.props["source_level"] = level
    e_sound(ctx, None, {"key": "cast_arcane", "radius": 20, "range_filtered": True})


def _affected(ctx):
    level = ctx.obj.props["source_level"]
    return [p for p in select(ctx, {"who": "everyone"})
            if abs(p.level - level) <= 1 and p.immune_until <= ctx.m.time
            and not statuses.flag(ctx.m, p, "intangible")]


@effect("astra_pull", per_player=False)
def pull(ctx, _player, _spec):
    for player in _affected(ctx):
        e_pull(ctx, player, {"strength": min(4 * ctx.dt, (ctx.point - player.pos).length())})


@effect("astra_burst", per_player=False)
def burst(ctx, _player, spec):
    for player in _affected(ctx):
        statuses.apply_status(ctx.m, player, "concuss" if spec["mode"] == "nova" else "iso_vulnerable", 2.5)


@effect("astra_divide", per_player=False)
def divide(ctx, _player, _spec):
    if ctx.m.phase not in ("live", "planted"):
        return False
    world = ctx.m.world
    bounds = Rect(0, 0, world.width, world.height)
    # ray_interval clamps an interior entry to zero, so trace each direction.
    forward = bounds.ray_interval(ctx.point, ctx.aim)
    backward = bounds.ray_interval(ctx.point, ctx.aim * -1)
    if forward is None or backward is None:
        return False
    wall = place(ctx, thing("wall", delay=0.4, lasts=21, sprite="astra_divide"), ctx.point)
    wall.a, wall.b = ctx.point - ctx.aim * backward[1], ctx.point + ctx.aim * forward[1]
    wall.props.update(bullet_screen=True, all_heights=True, blocks_sound=True)
    e_sound(ctx, None, {"key": "cast_dark", "radius": 100, "range_filtered": True})


def tick(match, _commands, _dt):
    for player in match.players.values():
        if player.agent != "astra":
            continue
        pending = player.passive_state.get("astra_returns", [])
        if pending:
            remaining = [deadline for deadline in pending if deadline > match.time]
            player.charges["E"] = min(5, player.charges.get("E", 0) + len(pending) - len(remaining))
            player.passive_state["astra_returns"] = remaining


MATCH_TICKS["astra"] = tick
