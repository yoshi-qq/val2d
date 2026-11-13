"""Veto's anchors, snare, utility interception and mutation."""
from gameplay.geometry import Vec, heading, projectile_progress
from gameplay.kit import statuses
from gameplay.kit.builtins import can_land, e_sound, select, t_aim
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place, remove_device, schedule_ability_return
from gameplay.kit.registry import effect, target


# These moving effects use neither the thrown flag nor a damageable device.
INTERCEPTABLE_PROJECTILES = {
    "tejo_grenade", "tejo_missile", "fade_seize", "gekko_plasma", "skye_hawk",
    "raze_grenade", "raze_rocket", "viper_canister", "kayo_flash", "kayo_frag",
    "waylay_saturate", "miks_pulse_heal", "miks_pulse_concuss", "yoru_flash",
}
EXEMPT_DEVICES = {"harbor_shield", "yoru_clone", "yoru_decoy"}


def _owned(match, owner, sprite):
    return [e for e in match.effects if e.owner == owner.pid and e.props.get("sprite") == sprite
            and not e.props.get("ended") and match.time < e.until]


def _looked_at(match, player):
    direction = heading(player.facing)
    choices = []
    for obj in _owned(match, player, "veto_vortex"):
        offset = obj.pos - player.pos
        if (obj.start <= match.time and 0 < offset.length() <= 30 and direction.dot(offset.normalized()) >= 0.97):
            choices.append((abs(direction.cross(offset)), offset.length(), obj))
    return min(choices, key=lambda row: row[:2])[2] if choices else None


@target("veto_ground")
def ground(match, player, spec):
    if spec["name"] == "Crosscut" and _looked_at(match, player):
        return player.pos
    if spec["name"] == "Interceptor" and statuses.has(match, player, "veto_interceptor_ready"):
        return player.pos
    point = t_aim(match, player, spec)
    return point if can_land(match, player, point) and match.world.drop_recovery(point) is None else None


@effect("veto_crosscut", per_player=False)
def crosscut(ctx, _player, _spec):
    match, owner = ctx.m, ctx.owner
    if (vortex := _looked_at(match, owner)) is not None:
        if owner.zipline is not None or owner.z > 0.01:
            return False
        transit = place(ctx, thing("zone", delay=1, lasts=0.1, hidden="all",
                                    triggers=[on("start", [step("veto_arrive")], consume=True)]), vortex.pos)
        transit.props["interruptible_teleport"] = True
        transit.data["vortex"] = vortex
        transit.data["cast_at"] = match.time
        owner.channel_until = owner.equip_until = match.time + 1.6
        owner.vel = Vec(0, 0)
        return
    if statuses.has(match, owner, "veto_crosscut_ready"):
        return False
    vortex = place(ctx, thing("sensor", delay=0.75, lasts=3600, radius=0.4, hp=20, hit_radius=0.4,
                              recall_recharge=0, sprite="veto_vortex", on_remove="veto_vortex_removed",
                              triggers=[on("tick", [step("veto_vortex_aim")])]), ctx.point)
    vortex.props.update(recall_buy_only=True, source_level=match.world.floor_level(ctx.point, owner.level))


@effect("veto_vortex_aim", per_player=False)
def vortex_aim(ctx, _player, _spec):
    if ctx.owner is not None and ctx.owner.alive and _looked_at(ctx.m, ctx.owner):
        statuses.apply_status(ctx.m, ctx.owner, "veto_crosscut_ready", 0.1)


@effect("veto_vortex_removed", per_player=False)
def vortex_removed(ctx, _player, _spec):
    if ctx.owner:
        ctx.owner.status.pop("veto_crosscut_ready", None)


@effect("veto_arrive", per_player=False)
def arrive(ctx, _player, _spec):
    match, owner, vortex = ctx.m, ctx.owner, ctx.obj.data["vortex"]
    if (owner is None or not owner.alive or owner.dm_ghost or owner.duel_id or owner.died_at >= ctx.obj.data["cast_at"]
            or vortex.props.get("ended")
            or statuses.flag(match, owner, "no_abilities")):
        return
    level = vortex.props["source_level"]
    if not can_land(match, owner, vortex.pos):
        return
    e_sound(ctx, None, {"key": "ab_teleport", "radius": 30, "at_owner": True})
    owner.pos = owner.last_pos = vortex.pos
    owner.level = level
    owner.ground = match.world.ground_height(vortex.pos, level) * match._mv["level_height"]
    owner.vel, owner.z, owner.vz = Vec(0, 0), 0, 0
    e_sound(ctx, None, {"key": "ab_teleport", "radius": 30, "range_filtered": True})
    remove_device(match, vortex, "used")


@effect("veto_trap_land", per_player=False)
def trap_land(ctx, _player, _spec):
    trap = place(ctx, thing("sensor", delay=1.5, lasts=3600, radius=0.4, hp=20, hit_radius=0.4,
                             hidden="enemies", detect_range=9, owner_range=float("inf"), recall_recharge=0,
                             sprite="veto_trap", triggers=[on("tick", [step("veto_trap_tick")])]), ctx.point)
    trap.props.update(recall_buy_only=True, source_level=ctx.m.world.floor_level(ctx.point))


@effect("veto_trap_tick", per_player=False)
def trap_tick(ctx, _player, _spec):
    trap = ctx.obj
    if "trigger_at" not in trap.data:
        if any(abs(p.level - trap.props["source_level"]) <= 1 and p.immune_until <= ctx.m.time
               and not statuses.flag(ctx.m, p, "intangible")
               for p in select(ctx, {"radius": 6.58, "sight": "all"})):
            trap.data["trigger_at"] = ctx.m.time + 0.5
            trap.props["hidden"] = None
            trap.props.pop("recall_recharge", None)
            e_sound(ctx, None, {"key": "cast_charge_up", "radius": 20, "range_filtered": True})
        return
    if ctx.m.time < trap.data["trigger_at"]:
        return
    field = place(ctx, thing("zone", lasts=4.5, radius=6.58, sprite="veto_field"), trap.pos)
    for player in select(ctx, {"who": "everyone", "radius": 6.58, "sight": "all"}):
        if (statuses.flag(ctx.m, player, "intangible") or player.immune_until > ctx.m.time
                or abs(player.level - trap.props["source_level"]) > 1):
            continue
        before = player.hp + player.hp_frac
        after = max(1, before - 75)
        player.hp, player.hp_frac = int(after), after - int(after)
        player.decay_pool += before - after
        player.passive_state.update(decay_recovery_rate=75 / 4.5, veto_tether=(field.pos, field.radius))
        statuses.apply_status(ctx.m, player, "veto_tether", 4.5)
        statuses.apply_status(ctx.m, player, "deaf", 4.5)
    trap.props["ended"] = True


@effect("veto_interceptor", per_player=False)
def interceptor(ctx, _player, _spec):
    match, owner = ctx.m, ctx.owner
    deployed = _owned(match, owner, "veto_interceptor")
    if deployed:
        obj = deployed[0]
        if match.time < obj.start or "active_at" in obj.data:
            return False
        obj.data["active_at"] = match.time + 0.5
        obj.until = obj.data["active_at"] + 9
        obj.radius = 18
        obj.props.pop("recall_recharge", None)
        owner.status.pop("veto_interceptor_ready", None)
        cooldown = match.deathmatch_rules["ability_cooldowns"]["veto"][2] if match.mode == "deathmatch" else 45
        schedule_ability_return(match, owner, "E", cooldown)
        e_sound(ctx, None, {"key": "cast_tech", "radius": 20, "range_filtered": True})
        return
    if match.time < owner.ability_ready_at.get("E", 0):
        return False
    obj = place(ctx, thing("sensor", delay=0.35, lasts=3600, radius=0.4, hp=20, hit_radius=0.4,
                            recall_recharge=20, destroy_recharge=45, sprite="veto_interceptor",
                            owner_range=float("inf"), on_remove="veto_interceptor_removed",
                            triggers=[on("tick", [step("veto_intercept")])]), ctx.point)
    obj.props["early_intercept"] = True
    obj.props["source_level"] = match.world.floor_level(ctx.point, owner.level)
    statuses.apply_status(match, owner, "veto_interceptor_ready", 3600)


@effect("veto_interceptor_removed", per_player=False)
def interceptor_removed(ctx, _player, _spec):
    if ctx.owner is not None:
        ctx.owner.status.pop("veto_interceptor_ready", None)
        if "active_at" in ctx.obj.data:
            ctx.obj.props.pop("destroy_recharge", None)
        elif _spec["reason"] == "destroy" and ctx.m.mode == "deathmatch":
            cooldown = ctx.m.deathmatch_rules["ability_cooldowns"]["veto"][2]
            ctx.owner.recharge_timers["E"] = 0.0
            schedule_ability_return(ctx.m, ctx.owner, "E", cooldown)


def _projectile_point(obj, now):
    if not obj.props.get("thrown") or obj.a is None:
        return obj.pos
    fraction = projectile_progress(now, obj.start, obj.until,
                                   lands_at_expiry=obj.props.get("sprite") == "sova_recon_bolt")
    return obj.a + (obj.pos - obj.a) * max(0, min(1, fraction))


@effect("veto_intercept", per_player=False)
def intercept(ctx, _player, _spec):
    interceptor, match = ctx.obj, ctx.m
    if match.time < interceptor.data.get("active_at", float("inf")):
        return
    level = interceptor.props["source_level"]
    targets = []
    for obj in list(match.effects):
        sprite = obj.props.get("sprite")
        if (obj.team == interceptor.team or obj.props.get("ended") or not obj.start <= match.time < obj.until
                or obj.props.get("duel_id", 0) != interceptor.props.get("duel_id", 0)
                or sprite in EXEMPT_DEVICES):
            continue
        damageable = obj.data.get("hp", 0) > 0
        if not (damageable or obj.props.get("thrown") or sprite in INTERCEPTABLE_PROJECTILES):
            continue
        point = _projectile_point(obj, match.time)
        distance = (point - interceptor.pos).length()
        if distance > 18 or not match._line_clear(interceptor.pos, point, level):
            continue
        if obj.props.get("hidden") in ("all", "enemies") and distance > obj.props.get("detect_range", 0):
            continue
        if damageable:
            targets.append((distance, obj, point))
        else:
            remove_device(match, obj, "intercept")
            _beam(ctx, point)
    if targets and match.time >= interceptor.data.get("next_beam", 0):
        _, obj, point = min(targets, key=lambda item: item[0])
        previous = interceptor.data.get("beam_target")
        interceptor.data["beam_target"] = obj
        if previous is not None and previous is not obj and not interceptor.data.pop("switching", False):
            interceptor.data.update(next_beam=match.time + 0.2, switching=True)
            return
        interceptor.data.pop("switching", None)
        interceptor.data["next_beam"] = match.time + 0.125
        obj.data["hp"] -= 100
        if obj.data["hp"] <= 0:
            remove_device(match, obj, "destroy")
        _beam(ctx, point)


def _beam(ctx, point):
    beam = place(ctx, thing("zone", lasts=0.15, radius=0.12, sprite="veto_beam"), point)
    beam.a, beam.b = ctx.point, point


@effect("veto_evolution", per_player=False)
def evolution(ctx, _player, _spec):
    if statuses.has(ctx.m, ctx.owner, "veto_evolved"):
        return False
    ctx.owner.equip_until = ctx.m.time + 1
    place(ctx, thing("zone", delay=1, lasts=0.1, hidden="all",
                     triggers=[on("start", [step("veto_mutate")], consume=True)]), ctx.point)


@effect("veto_mutate", per_player=False)
def mutate(ctx, _player, _spec):
    player, match = ctx.owner, ctx.m
    if player is None or not player.alive or player.died_at >= ctx.obj.start - 1:
        return
    statuses.clear_statuses(player, match, keep_positive=True)
    player.tagged_until = player.revealed_until = 0
    statuses.apply_status(match, player, "veto_evolved", float("inf"))
    player.immune_until = float("inf")
