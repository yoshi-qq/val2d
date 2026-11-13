"""Suppression pulses and NULL/cmd's stabilization state."""
from dataclasses import replace

from gameplay.geometry import Vec, angle_diff, angle_of
from gameplay.kit import statuses
from gameplay.kit.builtins import damage_map_cover, game_event, select
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place
from gameplay.kit.registry import COMMAND_FILTERS, LETHAL_FILTERS, MATCH_TICKS, effect

DOWNED = "kayo_downed"


@effect("kayo_frag")
def frag(ctx, player, _spec):
    distance = (player.pos - ctx.point).length()
    amount = round(60 - 35 * max(0, distance - 1) / 3)
    ctx.m._damage(ctx.owner, player, amount, "body", "ability:FRAG/ment")


@effect("kayo_frag_cover", per_player=False)
def frag_cover(ctx, _player, _spec):
    damage_map_cover(ctx, {"do": "damage", "radius": 4, "amount": 60, "cover_mult": 1})


@effect("kayo_flash")
def flash(ctx, player, _spec):
    angle = abs(angle_diff(player.facing, angle_of(ctx.point - player.pos)))
    if not statuses.flag(ctx.m, player, "intangible"):
        statuses.apply_status(ctx.m, player, "blind", max(0.25, 2.25 - 2 * angle / 180))


@effect("kayo_suppress", per_player=False)
def suppress(ctx, _player, spec):
    radius = spec["radius"]
    names = []
    for player in select(ctx, {"who": "enemies", "radius": radius}):
        if not statuses.flag(ctx.m, player, "intangible"):
            statuses.apply_status(ctx.m, player, "suppress", spec["seconds"])
            if statuses.has(ctx.m, player, "suppress"):
                names.append(ctx.m.agents[player.agent]["name"])
    sound = {"key": "cast_sonic", "pos": (ctx.point.x, ctx.point.y), "radius": radius}
    if spec.get("range_filtered"):
        sound["range_filtered"] = True
    game_event(ctx.m, "sound_fx", sound)
    place(ctx, thing("zone", lasts=0.26, radius=radius, sprite="kayo_pulse"), ctx.point)
    if names and spec["seconds"] == 8:
        game_event(ctx.m, "kayo_scan", {"team": ctx.team, "agents": sorted(names)})


@effect("kayo_overload", per_player=False)
def overload(ctx, _target, _spec):
    statuses.apply_status(ctx.m, ctx.owner, "kayo_overload", 13.1)
    place(ctx, thing("none", delay=1, lasts=12.12, hidden="all",
                     triggers=[on("tick", [step("kayo_follow_pulses")])]), ctx.source)


@effect("kayo_follow_pulses", per_player=False)
def follow_pulses(ctx, _target, _spec):
    if ctx.owner is None or not ctx.owner.alive:
        ctx.obj.props["ended"] = True
        return
    count = ctx.obj.data.get("pulses", 0)
    if count >= 5 or ctx.m.time < ctx.obj.start + count * 3:
        return
    ctx.obj.data["pulses"] = count + 1
    suppress(replace(ctx, point=ctx.owner.pos), None,
             {"radius": 42.5, "seconds": 4, "range_filtered": True})


def down(match, attacker, player, source, zone):
    if source == "spike" or not statuses.has(match, player, "kayo_overload"):
        return False
    player.status.pop("kayo_overload", None)
    player.hp, player.armor, player.overheal = 850, 0, 0
    player.armor_key, player.armor_reserve, player.armor_regen_at = "", 0, None
    player.heal_left, player.hp_frac = 0, 0
    player.vel, player.vz, player.dash_until = Vec(0, 0), 0, 0
    player.plant_progress = player.defuse_progress = 0
    player.defusing = False
    player.zipline = None
    player.spike_equipped = False
    player.dropped_at = match.time
    if match.spike_carrier == player.pid:
        match.spike_carrier, match.spike_pos = None, player.pos
        match.spike_ground = match.world.ground_height(player.pos, player.level)
    player.passive_state["kayo_downed"] = (match.time + 15, attacker.pid if attacker else None, source, zone)
    statuses.apply_status(match, player, DOWNED, float("inf"))
    game_event(match, "kayo_announcement", {"team": player.team, "ally": "cast_dark", "enemy": "cast_burst"})
    return True


LETHAL_FILTERS["kayo"] = down


def filter_command(match, player, cmd, _dt):
    if statuses.has(match, player, DOWNED):
        return None
    return cmd


COMMAND_FILTERS["kayo"] = filter_command


def stabilize(match, commands, dt):
    from gameplay.match import Effect

    for player in match.players.values():
        last, progress, channel = player.passive_state.get("kayo_stabilize", (None, 0, None))
        if not player.alive or not statuses.has(match, player, DOWNED):
            if channel is not None:
                channel.props["ended"] = True
                player.passive_state.pop("kayo_stabilize", None)
            continue
        deadline, attacker, source, zone = player.passive_state[DOWNED]
        helper = next((p for p in match.players.values() if p is not player and p.alive and p.team == player.team
                       and p.channel_until <= match.time
                       and not statuses.flag(match, p, "no_interact") and commands.get(p.pid) and commands[p.pid].interact
                       and (p.pos - player.pos).length() <= 1.5 and not match._deck_between(p, player)
                       and match._line_clear(p.pos, player.pos, p.level, ignore_effects=True)), None)
        if helper is not None:
            if last != helper.pid:
                if channel is not None:
                    channel.props["ended"] = True
                game_event(match, "sound_fx", {"key": "ab_revive", "pos": (player.pos.x, player.pos.y),
                                              "radius": 15, "range_filtered": True})
                channel = Effect("kayo_stabilize", player.pid, player.team, player.pos,
                                 match.time + 1.5, 15, start=match.time,
                                 props={"hidden": "team_only", "duel_id": player.duel_id})
                match.effects.append(channel)
            progress = progress + dt if last == helper.pid else dt
            deadline += dt
            player.passive_state[DOWNED] = (deadline, attacker, source, zone)
            player.passive_state["kayo_stabilize"] = (helper.pid, progress, channel)
            if progress >= 1.5:
                channel.props["ended"] = True
                player.hp = max(1, round(match._hp * player.hp / 850))
                player.status.pop(DOWNED, None)
                player.passive_state.pop(DOWNED, None)
                player.passive_state.pop("kayo_stabilize", None)
                player.channel_until = player.equip_until = match.time + 1.55
                game_event(match, "kayo_announcement",
                           {"team": player.team, "ally": "cast_buff", "enemy": "cast_beam"})
            continue
        if channel is not None:
            channel.props["ended"] = True
            player.passive_state.pop("kayo_stabilize", None)
        if match.time >= deadline:
            match._kill(match.players.get(attacker), player, source, zone)


MATCH_TICKS["kayo"] = stabilize
