"""Clove's temporary health, lingering utility and self-resurrection."""
from gameplay.geometry import Vec
from gameplay.kit import statuses
from gameplay.kit.builtins import game_event
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place
from gameplay.kit.registry import MATCH_TICKS, effect


@effect("clove_pick_me_up", per_player=False)
def pick_me_up(ctx, _player, _spec):
    p = ctx.owner
    if not statuses.has(ctx.m, p, "clove_pick_ready"):
        return False
    p.status.pop("clove_pick_ready", None)
    p.overheal = max(p.overheal, max(0, min(50, 150 - p.hp - p.armor)))
    p.overheal_until = ctx.m.time + 10
    statuses.apply_status(ctx.m, p, "clove_haste", 3)
    p.equip_until = ctx.m.time + 0.7


@effect("clove_meddle_land", per_player=False)
def meddle_land(ctx, _player, _spec):
    place(ctx, thing("zone", delay=0.75, lasts=0.35, radius=4, sprite="clove_meddle",
                     warning_sprite="clove_meddle",
                     triggers=[on("start", [step("clove_decay")], who="everyone", sight="walls")]), ctx.point)


@effect("clove_decay")
def decay(ctx, player, _spec):
    if statuses.flag(ctx.m, player, "intangible") or player.immune_until > ctx.m.time:
        return
    statuses.apply_status(ctx.m, player, "clove_decay", 0.75)
    statuses.apply_status(ctx.m, player, "clove_decay_hold", 3.25)
    player.passive_state["decay_recovery_rate"] = 90 / 1.75


@effect("clove_smoke", per_player=False)
def smoke(ctx, _player, _spec):
    if ctx.m.world.drop_recovery(ctx.point) is not None:
        return False
    dead = not ctx.owner.alive
    sprite = "clove_smoke_dead" if dead else "clove_smoke"
    place(ctx, thing("smoke", delay=1, lasts=6 if dead else 14, radius=4, sprite=sprite,
                     warning_sprite=sprite, settle_on_floor=True, fall_speed=5,
                     fade_sound={"key": "cast_whoosh", "lead": 2, "radius": 12}), ctx.point)


def _end_phase(match, player):
    player.status.pop("clove_phase", None)
    player.channel_until = player.equip_until = match.time + 0.8
    statuses.apply_status(match, player, "clove_second_chance", 10.8)
    player.passive_state["clove_duel_from"] = player.channel_until


@effect("clove_revive", per_player=False)
def revive(ctx, _player, _spec):
    p, match = ctx.owner, ctx.m
    if p.alive:
        if not statuses.has(match, p, "clove_phase") or match.time < p.channel_until:
            return False
        _end_phase(match, p)
        return
    if not match.can_cast_dead(p, "X"):
        return False
    p.passive_state["clove_revived_round"] = True
    p.channel_until = match.time + 1.5
    place(ctx, thing("zone", delay=1.5, lasts=0, radius=0.8, warning_sprite="clove_revive",
                     triggers=[on("expire", [step("clove_rise")])]), p.pos)


@effect("clove_rise", per_player=False)
def rise(ctx, _player, _spec):
    p, match = ctx.owner, ctx.m
    if p is None or p.alive or match.phase not in ("live", "planted"):
        return
    match._restore_death_drop(p)
    statuses.clear_statuses(p, match, keep_positive=False)
    p.alive, p.hp, p.hp_frac = True, match._hp, 0
    p.armor, p.armor_reserve, p.armor_key, p.armor_regen_at = 0, 0, "", None
    p.decay_pool = p.heal_left = p.heal_rate = 0
    p.vel, p.z, p.vz = Vec(0, 0), 0, 0
    p.pos = match.world.drop_recovery(p.pos) or p.pos
    p.ground = match.world.ground_height(p.pos) * match._mv["level_height"]
    p.level = match.world.floor_level(p.pos)
    p.channel_until = p.equip_until = match.time
    p.reload_until = p.burst_left = p.dash_until = 0
    statuses.apply_status(match, p, "clove_phase", 2)
    game_event(match, "revive", {"pid": p.pid, "by": p.pid})


def tick(match, _commands, _dt):
    kills = [e for e in match.events if e.kind == "kill"]
    for p in list(match.players.values()):
        if p.agent != "clove" or not p.alive:
            continue
        if (deadline := p.status.get("clove_phase")) is not None and deadline <= match.time:
            _end_phase(match, p)
        for event in kills:
            victim = match.players.get(event.data["pid"])
            if victim is None or p.team == victim.team:
                continue
            hit_at = p.passive_state.get("clove_last_hit", {}).pop(victim.pid, -float("inf"))
            direct = event.data.get("by") == p.pid
            if direct or match.time - hit_at <= 6:
                statuses.apply_status(match, p, "clove_pick_ready", 4.5)
            since = p.passive_state.get("clove_duel_from")
            if since is not None and match.time >= since and (direct or hit_at >= since):
                p.status.pop("clove_second_chance", None)
                p.passive_state.pop("clove_duel_from", None)
        if (deadline := p.status.get("clove_second_chance")) is not None and deadline <= match.time:
            p.status.pop("clove_second_chance", None)
            p.passive_state.pop("clove_duel_from", None)
            match._kill(None, p, "ability:Not Dead Yet", "body")


MATCH_TICKS["clove"] = tick
