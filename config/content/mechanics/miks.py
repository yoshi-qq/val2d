"""Miks's pulse falloff, paired buffs and Bassquake channel."""
from gameplay.kit import statuses
from gameplay.kit.builtins import w_cursor_ally
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place
from gameplay.kit.registry import effect, passive_trigger

BUFF_DURATION = 8
BUFFS = ("miks_stim", "miks_haste")
HARMONIZE_WINDUP = 0.1


@effect("miks_concuss")
def concuss(ctx, player, _spec):
    distance = (player.pos - ctx.point).length()
    duration = 2 * max(0, 1 - distance / ctx.obj.radius)
    statuses.apply_status(ctx.m, player, "concuss", duration)


@effect("miks_harmonize", per_player=False)
def harmonize(ctx, _player, spec):
    owner = ctx.owner
    ally = None
    if not spec.get("self_cast"):
        allies = w_cursor_ally(ctx, {**ctx.ability, "required": True})
        if not allies:
            return False
        ally = allies[0]
    windup = place(ctx, thing("none", delay=HARMONIZE_WINDUP, lasts=0.2,
                              triggers=[on("start", [step("miks_apply_harmonize")], consume=True)]), owner.pos)
    windup.data.update(ally=ally.pid if ally is not None else None, cast_at=ctx.m.time)
    owner.channel_until = windup.start
    owner.equip_until = max(owner.equip_until, windup.start + 0.3)


@effect("miks_apply_harmonize", per_player=False)
def apply_harmonize(ctx, _player, _spec):
    owner = ctx.owner
    cast_at = ctx.obj.data["cast_at"]
    if owner is None or not owner.alive or owner.died_at >= cast_at:
        return
    ally = ctx.m.players.get(ctx.obj.data["ally"])
    pair = [owner]
    if ally is not None and ally.alive and ally.died_at < cast_at:
        pair.append(ally)
        owner.passive_state["harmonize_link"] = (ally.pid, cast_at, ctx.m.time + BUFF_DURATION)
    else:
        owner.passive_state.pop("harmonize_link", None)
    for player in pair:
        for buff in BUFFS:
            statuses.apply_status(ctx.m, player, buff, BUFF_DURATION)


@passive_trigger("miks_harmonize_kill")
def harmonize_kill(match, owner, _spec, _dt):
    link = owner.passive_state.get("harmonize_link")
    if link is None:
        return []
    pid, started, expires = link
    ally = match.players.get(pid)
    if ally is None or not ally.alive or ally.died_at >= started or owner.died_at >= started or match.time >= expires:
        owner.passive_state.pop("harmonize_link", None)
        return []
    if any(e.kind == "kill" and e.data.get("by") in (owner.pid, ally.pid) for e in match.events):
        owner.passive_state["harmonize_link"] = (pid, started, match.time + BUFF_DURATION)
        return [ally]
    return []


@effect("miks_refresh_harmonize", per_player=False)
def refresh_harmonize(ctx, _player, _spec):
    for player in (ctx.owner, ctx.other):
        for buff in BUFFS:
            statuses.apply_status(ctx.m, player, buff, BUFF_DURATION)


@effect("miks_bassquake", per_player=False)
def bassquake(ctx, _player, _spec):
    end = ctx.m.time + ctx.ability["place"]["delay"]
    ctx.owner.channel_until = end
    ctx.owner.equip_until = max(ctx.owner.equip_until, end + 0.25)
