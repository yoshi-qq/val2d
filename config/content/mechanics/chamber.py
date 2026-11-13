"""Trademark lock-on and Rendezvous anchor lifecycle."""
from dataclasses import replace

from gameplay.geometry import Vec
from gameplay.kit import statuses
from gameplay.kit.builtins import game_event, select, t_aim
from gameplay.kit.dsl import on, status, step, thing
from gameplay.kit.engine import place
from gameplay.kit.registry import effect, passive_trigger, target

SLOW_FIELD = thing("zone", lasts=4, radius=6, sprite="chamber_slow",
                   triggers=[on("tick", [status("chamber_slow", 0.15)], who="everyone")])


def _valid_ground(match, player, point, level):
    return (match.buy_phase_allows_landing(player, point)
            and not any(w.top > level and (not w.on_deck or w.base <= level) and match.wall_active(w)
                        and w.rect.circle_push(point, 0.4) for w in match.combat_walls()))


@target("chamber_ground")
def ground_target(match, player, spec):
    if statuses.has(match, player, "chamber_anchor") and spec.get("instant_with_status"):
        return player.pos
    point = t_aim(match, player, spec)
    if not (0.4 <= point.x <= match.world.width - 0.4 and 0.4 <= point.y <= match.world.height - 0.4):
        return None
    level = match.world.floor_level(point, player.level)
    return point if _valid_ground(match, player, point, level) else None


@effect("chamber_trademark", per_player=False)
def trademark(ctx, _player, _spec):
    obj, match = ctx.obj, ctx.m
    level = obj.props["source_level"]
    pid = obj.data.get("tracked")
    player = match.players.get(pid)
    if (player is None or not player.alive or statuses.flag(match, player, "intangible")
            or match.world.deck_blocks(obj.pos, level + 1, player.pos, player.level + 1)
            or not match._line_clear(obj.pos, player.pos, min(level, player.level))):
        obj.data.pop("tracked", None)
        candidates = [p for p in select(ctx, {"who": "enemies", "radius": 10, "sight": "all"})
                      if not statuses.flag(match, p, "intangible")
                      and not match.world.deck_blocks(obj.pos, level + 1, p.pos, p.level + 1)]
        if candidates:
            target = min(candidates, key=lambda p: (p.pos - obj.pos).length())
            obj.data.update(tracked=target.pid, lock_at=match.time + 0.9)
            game_event(match, "sound_fx", {"key": "ab_sensor", "pos": (obj.pos.x, obj.pos.y), "radius": 20})
        return
    if obj.data.get("lock_at", float("inf")) <= match.time:
        obj.props["ended"] = True
        if player.z <= 2:
            place(ctx, SLOW_FIELD, player.pos)


def _anchor(match, player):
    return next((e for e in match.effects if e.owner == player.pid and e.props.get("chamber_anchor")
                 and not e.props.get("ended") and e.until > match.time), None)


@effect("chamber_rendezvous", per_player=False)
def rendezvous(ctx, _player, _spec):
    player, match = ctx.owner, ctx.m
    anchor = _anchor(match, player)
    if anchor is None:
        anchor = place(ctx, thing("sensor", lasts=300, hp=50, hit_radius=0.42, radius=18,
                                  recall_recharge=30, sprite="chamber_anchor"), ctx.point)
        ground = match.world.ground_height(ctx.point, player.level)
        anchor.data["ground"] = ground
        anchor.props.update(chamber_anchor=True, on_remove="chamber_anchor_removed",
                            source_level=match.world.floor_level(ctx.point, player.level))
        statuses.apply_status(match, player, "chamber_anchor", 300)
        return
    if (player.z > 0.001 or abs(player.vz) > 0.001 or (anchor.pos - player.pos).length() > 18
            or match.time < anchor.data.get("ready_at", 0)
            or not _valid_ground(match, player, anchor.pos, anchor.props["source_level"])):
        return False
    transit = place(ctx, thing("none", delay=0.1, lasts=0.15, hidden="all",
                               triggers=[on("start", [step("chamber_arrive")], consume=True)]), anchor.pos)
    transit.data.update(anchor=anchor, cast_at=match.time)
    player.channel_until = match.time + 1.3
    player.equip_until = max(player.equip_until, player.channel_until)
    player.reload_until = player.dash_until = 0
    player.vel = Vec(0, 0)


@effect("chamber_arrive", per_player=False)
def arrive(ctx, _player, _spec):
    player, match = ctx.owner, ctx.m
    anchor = ctx.obj.data["anchor"]
    if (player is None or not player.alive or player.died_at >= ctx.obj.data["cast_at"]
            or statuses.flag(match, player, "no_abilities") or anchor.props.get("ended")
            or not _valid_ground(match, player, anchor.pos, anchor.props["source_level"])):
        if player is not None:
            player.channel_until = player.equip_until = match.time
        return
    anchor.data["ready_at"] = match.time + (3 if match.phase == "buy" else 30)
    for pos in (player.pos, anchor.pos):
        game_event(match, "sound_fx", {"key": "ab_teleport", "pos": (pos.x, pos.y), "radius": 42.5})
    player.pos = player.last_pos = anchor.pos
    player.ground = anchor.data["ground"] * float(match._mv["level_height"])
    player.level = anchor.props["source_level"]
    player.vel, player.z, player.vz = Vec(0, 0), 0, 0


@effect("chamber_anchor_removed", per_player=False)
def anchor_removed(ctx, _player, spec):
    if ctx.owner is not None:
        ctx.owner.status.pop("chamber_anchor", None)
    if spec["reason"] == "recall":
        ready_at = ctx.obj.data.get("ready_at", 0)
        if ready_at > ctx.m.time:
            ctx.obj.props["recall_recharge"] = ready_at - ctx.m.time


@passive_trigger("chamber_tour_kill")
def tour_kill(match, player, _spec, _dt):
    return [match.players[event.data["pid"]] for event in match.events
            if event.kind == "kill" and event.data.get("by") == player.pid
            and event.data.get("weapon") == "tour_de_force" and event.data["pid"] in match.players]


@effect("chamber_tour_field", per_player=False)
def tour_field(ctx, _player, _spec):
    victim = ctx.other
    if victim is not None and victim.team != ctx.team and victim.z <= 2:
        place(replace(ctx, source=victim.pos), SLOW_FIELD, victim.pos)
