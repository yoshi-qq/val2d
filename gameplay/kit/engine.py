"""Runs abilities: target -> immediate steps -> placed object with triggers -> steps.

An ability (config/content/agents/*.py) is a dict. Either it names a preset (`kind="smoke"`, values beside it), or it
is composed:
    target   where it goes: "aim" (default), "aim_free", "self", "ahead" (registry TARGETS); `range` limits it
    do       steps run at once on use, e.g. [{"do": "dash", "distance": 7, "duration": 0.2}]
    place    an object left in the world: look, lasts, delay, radius, shape, length, thrown, clip_ends,
             blocks_sight, hidden, move, triggers=[{"when": "...", "who": "...", "do": [steps]}, ...]
A step is {"do": effect name, ...its values}; `who`, `area`, `radius`, `sight`, `facing`, `first` choose the players.
"""
from __future__ import annotations

import math
import warnings
from typing import TYPE_CHECKING, Any

from gameplay.geometry import Vec, heading
from gameplay.kit import statuses
from gameplay.kit.builtins import damage_map_cover, select
from gameplay.kit.registry import EFFECTS, PASSIVE_TRIGGERS, PRESETS, TARGETS, TRIGGERS, Ctx

if TYPE_CHECKING:
    from gameplay.match import Effect, Match, PlayerState

LOOKS = ("smoke", "wall", "flash", "zone", "blast", "sensor", "alarm", "tripwire", "decoy", "snapshot", "none")


def expand(ab: dict[str, Any]) -> dict[str, Any]:
    """Turns a preset ability (kind=...) into its composed form; composed abilities pass through."""
    if "do" in ab or "place" in ab:
        return ab
    fn = PRESETS.get(str(ab.get("kind", "")))
    if fn is None:
        raise ValueError(f"unknown kind '{ab.get('kind')}' and no do/place given")
    spec = fn(ab)
    return {**ab, **spec}


def _blocks_effect(ctx: Ctx, player: PlayerState) -> bool:
    return player.dm_ghost or (player.team != ctx.team and ctx.m.deathmatch_spawn_protected(player))


def run_steps(ctx: Ctx, steps: list[dict[str, Any]], players: list[PlayerState] | None = None,
              trigger_spec: dict[str, Any] | None = None) -> bool:
    """Runs steps in order. `players` (from a trigger) are used by every step that names no `who`.
    Returns False if a step cancelled (only matters on use)."""
    for step in steps:
        if ctx.m.mode == "deathmatch" and ctx.m.phase == "over":
            return True
        d = EFFECTS.get(str(step.get("do", "")))
        if d is None:
            warnings.warn(f"Unknown effect '{step.get('do')}' in {ctx.ability.get('name', '?')}")
            continue
        if not d.per_player:
            if d.fn(ctx, None, step) is False:
                return False
            continue
        targets = players if players is not None and "who" not in step else select(ctx, step, default=d.who)
        if not targets and step.get("required"):
            return False
        if step.get("cover_mult") and step["do"] in ("damage", "dps"):
            damage_map_cover(ctx, {**(trigger_spec or {}), **step})
        for t in targets:
            if ctx.m.mode == "deathmatch" and ctx.m.phase == "over":
                return True
            if _blocks_effect(ctx, t):
                continue
            d.fn(ctx, t, step)
    return True


def _status_hint(triggers: list[dict[str, Any]]) -> str | None:
    """First status an object applies; the client colours zones by it."""
    for tr in triggers:
        for step in tr.get("do", []):
            if step.get("do") == "status":
                return str(step.get("name"))
    return None


def line_endpoints(m: Match, point: Vec, aim: Vec, level: int, spec: dict[str, Any]) -> tuple[Vec, Vec]:
    across = aim if spec.get("along") else aim.rotated(90)
    half = across * (float(spec.get("length", 6.0)) / 2)
    a, b = (point, point + half * 2) if spec.get("forward") else (point - half, point + half)
    if spec.get("clip_ends"):
        a, b = m._clip_to_walls(point, a, level), m._clip_to_walls(point, b, level)
    return a, b


def place(ctx: Ctx, spec: dict[str, Any], point: Vec) -> Effect:
    """Leaves an object in the world at `point`."""
    from gameplay.match import Effect
    m, now = ctx.m, ctx.m.time
    look = str(spec.get("look", "zone"))
    if look not in LOOKS:
        warnings.warn(f"Unknown look '{look}'; drawn as a zone")
        look = "zone"
    if spec.get("spawn_ahead"):
        point = point + ctx.aim * float(spec["spawn_ahead"])
    delay, lasts = float(spec.get("delay", 0.0)), float(spec.get("lasts", 10.0))
    ground = height = None
    if spec.get("settle_on_floor"):
        lift = float(ctx.ability.get("target_lift", 0))
        ground, height = m.world.smoke_target_heights(point, bool(ctx.ability.get("under_deck")), lift)
    if spec.get("travel_speed"):
        distance = (m.smoke_target_distance(ctx.owner, point, height)
                    if height is not None and ctx.owner is not None else (point - ctx.source).length())
        delay += distance / float(spec["travel_speed"])
    a = b = None
    if spec.get("shape") == "line":
        a, b = line_endpoints(m, point, ctx.aim, ctx.owner.level if ctx.owner else 0, spec)
    elif spec.get("thrown"):
        a = ctx.source
    triggers = list(spec.get("triggers", []))
    props: dict[str, Any] = {
        "triggers": triggers, "ability": ctx.ability, "key": ctx.key, "source": (ctx.source.x, ctx.source.y),
        "aim": (ctx.aim.x, ctx.aim.y), "blocks_sight": spec.get("blocks_sight", look in ("smoke", "wall")),
        "hidden": spec.get("hidden", {"decoy": "all", "alarm": "enemies", "tripwire": "enemies"}.get(look)),
        "status": spec.get("status_hint") or _status_hint(triggers), "move": float(spec.get("move", 0.0)),
        "sprite": spec.get("sprite"), "warning_sprite": spec.get("warning_sprite"),
        "sprite_width": spec.get("sprite_width"),
        "manual": spec.get("manual"), "bot_trigger_radius": spec.get("bot_trigger_radius"),
        "thrown": bool(spec.get("thrown")),
        "move_through_walls": bool(spec.get("move_through_walls")),
        "source_level": ctx.obj.props.get("source_level", 0) if ctx.obj else (ctx.owner.level if ctx.owner else 0),
    }
    if props["warning_sprite"]:
        props["warning_start"] = now
    e = Effect(look, ctx.owner.pid if ctx.owner else -1, ctx.team, point, now + delay + lasts,
               radius=float(spec.get("radius", 0.0)), a=a, b=b, start=now + delay, props=props)
    if spec.get("thrown") and ctx.ability.get("bolt_path"):
        e.props["bolt_path"] = ctx.ability["bolt_path"]
        e.data["bolt_range"] = ctx.ability["bolt_range"]
        e.data["bolt_bounces"] = ctx.ability.get("bounces", 0)
        e.data["bolt_walls"] = tuple(m.active_sight_walls(e.props["source_level"]))
    if ground is not None and height is not None:
        e.props["settled_ground"] = ground
        if height > ground:
            e.props["fall"] = (height - ground, float(spec["fall_speed"]))
    for key in ("hp", "hit_radius", "destroy_recharge", "recall_recharge", "owner_range", "reactivate", "detect_range",
                "cancel_channel", "friendly_fire", "cone", "fade_sound", "hit_sound", "device_vision", "on_remove"):
        if key in spec:
            e.props[key] = spec[key]
    if "hp" in spec:
        e.data["hp"] = int(spec["hp"])
    if spec.get("return_on_lethal") and ctx.owner is not None:
        e.data["return_armor"] = (ctx.owner.armor, ctx.owner.armor_key, ctx.owner.armor_reserve, ctx.owner.armor_regen_at)
        e.data["return_facing"] = ctx.owner.facing
    m.effects.append(e)
    return e


def resolve_target(m: Match, p: PlayerState, spec: dict[str, Any]) -> Vec | None:
    target_name = str(spec.get("target", "aim"))
    finder = TARGETS.get(target_name)
    if finder is None:
        raise ValueError(f"unknown target '{target_name}'")
    return finder(m, p, spec)


def use(m: Match, p: PlayerState, key: str, ab: dict[str, Any], point: Vec | None = None,
        *, direction: Vec | None = None) -> Vec | None:
    """Carries out ability `ab`. Returns the target point, or None if nothing happened (no charge used).
    point: a point chosen on the map (multi-placement); it is kept within `range` of the user."""
    spec = expand(ab)
    if point is not None and not spec.get("global_target"):
        reach = float(spec.get("range", 30.0))
        offset = point - p.pos
        if offset.length() > reach:
            point = p.pos + offset.normalized() * reach
    if point is None and spec.get("max_bounces"):
        from gameplay.kit.builtins import bolt_path
        path = bolt_path(m, p, spec)
        point = path[-1]
        spec["bolt_path"] = [(v.x, v.y) for v in path]
        spec["bolt_range"] = min(p.cursor_depth, float(spec["range"]))
    if point is None:
        point = resolve_target(m, p, spec)
    return _use_at(m, p, key, spec, point, direction)


def _use_at(m: Match, p: PlayerState, key: str, spec: dict[str, Any], point: Vec | None,
            direction: Vec | None = None) -> Vec | None:
    if point is None:
        return None
    if spec.get("place", {}).get("settle_on_floor") and not m.valid_tactical_point(p, spec, point):
        return None
    ctx = Ctx(m, p, p.team, point, p.pos, direction or heading(p.facing), ability=spec, key=key)
    if not run_steps(ctx, list(spec.get("do", []))):
        return None
    if spec.get("place"):
        place(ctx, dict(spec["place"]), ctx.point)
    return ctx.point


def _ctx_for(m: Match, e: Effect, dt: float) -> Ctx:
    sx, sy = e.props.get("source", (e.pos.x, e.pos.y))
    ax, ay = e.props.get("aim", (0.0, 1.0))
    return Ctx(m, m.players.get(e.owner), e.team, e.pos, Vec(sx, sy), Vec(ax, ay), ability=e.props.get("ability", {}),
               key=str(e.props.get("key", "")), obj=e, dt=dt)


def _fire(ctx: Ctx, tr: dict[str, Any], players: list[PlayerState] | None) -> None:
    if tr.get("once_per_player") and ctx.obj is not None and players is not None:
        seen = ctx.obj.data.setdefault(f"hit:{id(tr)}", set())
        players = [p for p in players if p.pid not in seen]
        seen.update(p.pid for p in players if not _blocks_effect(ctx, p))
    run_steps(ctx, list(tr.get("do", [])), players, tr)
    if tr.get("consume"):
        ctx.obj.props["ended"] = True  # type: ignore[union-attr]


def aimed_device(m: Match, p: PlayerState, depth: float) -> Effect | None:
    cursor = p.pos + heading(p.facing) * depth
    devices = [e for e in m.effects if e.owner == p.pid
               and (e.props.get("manual") or e.props.get("recall_recharge") is not None) and not e.props.get("ended")
               and (e.props.get("remote_recall") or (m.phase == "buy" if e.props.get("recall_buy_only") else m.phase != "buy"))
               and (e.pos - p.pos).length() <= e.props.get("recall_range", math.inf)
               and e.start <= m.time < e.until
               and min((pos - cursor).length() for pos in device_hit_points(e)) <= 1.25
               and (e.props.get("remote_recall") or m._line_clear(p.pos, e.pos, p.level, ignore_effects=True))]
    return min(devices, key=lambda e: (e.pos - cursor).length(), default=None)


def activate_device(m: Match, e: Effect) -> None:
    ctx = _ctx_for(m, e, 0.0)
    for tr in e.props.get("triggers", []):
        if tr.get("when") == "activate":
            _fire(ctx, tr, select(ctx, tr))
    e.props["ended"] = True


def device_hit_points(e: Effect) -> tuple[Vec, ...]:
    if e.kind == "tripwire" and e.a is not None and e.b is not None:
        return e.a, e.b
    return (e.pos,)


def remove_device(m: Match, e: Effect, reason: str) -> None:
    if e.props.get("ended"):
        return
    e.props["ended"] = True
    if reason == "destroy" and e.props.get("sprite") == "killjoy_lockdown_pulse" and m.time < e.start:
        from gameplay.kit.builtins import game_event

        game_event(m, "lockdown_destroyed", {"team": e.team})
    if hook := e.props.get("on_remove"):
        EFFECTS[hook].fn(_ctx_for(m, e, 0), None, {"reason": reason})
    owner = m.players.get(e.owner)
    delay = e.props.get(f"{reason}_recharge")
    if owner is not None and delay is not None:
        key = e.props["key"]
        if m.mode == "deathmatch" and reason == "recall":
            schedule_ability_return(m, owner, key, m.deathmatch_rules["device_recall_time"])
        elif m.mode != "deathmatch":
            schedule_ability_return(m, owner, key, float(delay))
    if owner is not None and e.props.get("cancel_channel"):
        owner.channel_until = 0.0
        if owner.alive and (origin := e.props.get("return_position")) is not None:
            owner.pos, owner.ground, owner.z, owner.level = origin
            owner.vel, owner.vz = Vec(0, 0), 0.0
            owner.status.pop("omen_shade", None)
            from gameplay.kit.builtins import reequip_weapon
            reequip_weapon(m, owner)


def device_operational(ctx: Ctx, e: Effect) -> bool:
    reach = e.props.get("owner_range")
    if reach is None:
        return True
    p, m = ctx.owner, ctx.m
    active = p is not None and p.alive and not statuses.flag(m, p, "no_abilities") and (p.pos - e.pos).length() <= reach
    if not active:
        e.data["dormant"] = True
        return False
    if e.data.pop("dormant", False):
        e.data.pop("chained", None)
        e.data["reactivate_at"] = m.time + float(e.props.get("reactivate", 0))
    return m.time >= e.data.get("reactivate_at", 0)


def return_to_marker(m: Match, p: PlayerState, marker: Effect | None = None) -> bool:
    if marker is None:
        marker = next((e for e in m.effects if e.owner == p.pid and "return_armor" in e.data
                       and not e.props.get("ended") and e.until >= m.time), None)
    if marker is None or not p.alive or p.dm_ghost or p.duel_id != marker.props.get("duel_id", 0):
        return False
    marker.props["ended"] = True
    p.pos = p.last_pos = marker.pos
    p.ability_return_at = m.time
    p.hp = m._hp
    if not marker.data.get("keep_current_armor"):
        p.armor, p.armor_key, p.armor_reserve, p.armor_regen_at = marker.data["return_armor"]
    p.facing = marker.data["return_facing"]
    p.vel, p.z, p.vz = Vec(0, 0), 0.0, 0.0
    reach = marker.props.get("source_level", float("inf"))
    p.ground = m.world.ground_height(p.pos, reach) * float(m._mv["level_height"])
    p.level = m.world.floor_level(p.pos, reach)
    p.plant_progress = p.defuse_progress = p.reload_until = p.dash_until = 0.0
    p.heal_left = p.heal_rate = 0.0
    if m.mode == "deathmatch":
        p.hp_frac = p.decay_pool = p.status_drain = 0.0
    statuses.clear_statuses(p, m, keep_positive=False)
    from gameplay.kit.builtins import game_event
    game_event(m, "ability_return", {"pid": p.pid, "pos": (p.pos.x, p.pos.y), "facing": p.facing})
    return True


def _finish_resurrection(m: Match, e: Effect) -> None:
    revived = m.players.get(e.props["revive_pid"])
    if revived is not None and not revived.alive:
        EFFECTS["revive"].fn(_ctx_for(m, e, 0.0), revived, {"health": e.data["revive_health"],
                                                           "recovery": e.data["revive_recovery"]})


def finish_round_resurrections(m: Match) -> None:
    for e in m.effects:
        if "revive_pid" in e.props and not e.props.get("ended") and e.until <= m.time:
            _finish_resurrection(m, e)
            e.props["ended"] = True


def refresh_bolt_path(m: Match, e: Effect, previous_time: float) -> None:
    from gameplay.kit.builtins import trace_bolt

    level = e.props["source_level"]
    walls = tuple(m.active_sight_walls(level))
    if walls == e.data["bolt_walls"]:
        return
    points = [Vec(*point) for point in e.props["bolt_path"]]
    segments = [(a, b - a) for a, b in zip(points, points[1:]) if a != b]
    total = sum(delta.length() for _, delta in segments)
    duration = max(e.until - e.start, 1e-6)
    progress = max(0.0, (previous_time - e.start) / duration)
    if progress >= 1 or not segments:
        return
    travelled = total * progress
    distance = travelled
    for index, (start, delta) in enumerate(segments):
        length = delta.length()
        if distance < length:
            direction = delta.normalized()
            pos = start + direction * distance
            remaining = max(0.0, e.data["bolt_range"] - travelled)
            bounces = max(0, e.data["bolt_bounces"] - index)
            path = trace_bolt(m, pos, direction, level, remaining, bounces)
            e.a, e.pos, e.start = pos, path[-1], max(e.start, previous_time)
            distance_left = sum((b - a).length() for a, b in zip(path, path[1:]))
            e.until = e.start + distance_left * duration / total
            e.props["bolt_path"] = [(v.x, v.y) for v in path]
            e.data.update(bolt_range=remaining, bolt_bounces=bounces, bolt_walls=walls)
            return
        distance -= length


def tick(m: Match, dt: float) -> None:
    now = m.time
    keep: list[Effect] = []
    existing = list(m.effects)
    # Resolve suppression pulses before a teleport that would complete on the same tick.
    existing.sort(key=lambda e: (not e.props.get("early_intercept"), bool(e.props.get("interruptible_teleport"))))
    for e in existing:
        if m.mode == "deathmatch" and m.phase == "over":
            return
        if e.props.get("ended"):
            continue
        triggers: list[dict[str, Any]] = e.props.get("triggers", [])
        if e.props.get("bolt_path") and now >= e.start:
            refresh_bolt_path(m, e, now - dt)
        ctx = _ctx_for(m, e, dt)
        if (e.props.get("interruptible_teleport") and not e.props.get("return_position")
                and ctx.owner is not None and statuses.flag(m, ctx.owner, "no_abilities")):
            owner = ctx.owner
            owner.channel_until = 0.0
            if owner.status.get("weapon_recovery") == e.props.get("teleport_recovery_until"):
                owner.status.pop("weapon_recovery", None)
            from gameplay.kit.builtins import reequip_weapon
            reequip_weapon(m, owner)
            remove_device(m, e, "cancel")
            continue
        if e.props.get("move_through_walls") and now >= e.start:
            active_dt = max(0.0, min(now, e.until) - max(now - dt, e.start))
            e.data["previous_pos"] = e.pos
            e.pos = ctx.point = e.pos + ctx.aim * (float(e.props["move"]) * active_dt)
            if now >= e.until and active_dt:
                for tr in triggers:
                    if tr.get("when") == "tick":
                        _fire(ctx, tr, select(ctx, tr))
        if m.cover_health and e.props.get("thrown") and e.a is not None and now >= e.start and e.until > e.start:
            progress = min(1.0, (now - e.start) / (e.until - e.start))
            previous = e.data.get("glass_progress", 0.0)
            path = e.pos - e.a
            if progress > previous:
                m.break_glass(e.a + path * previous, e.a + path * progress, e.props["source_level"])
                e.data["glass_progress"] = progress
        if now >= e.until:
            if "return_armor" in e.data and ctx.owner is not None:
                return_to_marker(m, ctx.owner, e)
            if "revive_pid" in e.props:
                if m.phase == "planted" or (m.phase == "live" and m.mode != "deathmatch" and not m.practice):
                    # Resolve round-ending outcomes before a same-tick resurrection.
                    keep.append(e)
                    continue
                if m.phase in ("buy", "live"):
                    _finish_resurrection(m, e)
            for tr in triggers:
                if tr.get("when") == "expire":
                    _fire(ctx, tr, select(ctx, tr))
            continue
        if now < e.start:
            keep.append(e)
            continue
        fade_sound = e.props.get("fade_sound")
        if fade_sound and now >= e.until - float(fade_sound["lead"]):
            e.props.pop("fade_sound")
            EFFECTS["sound"].fn(ctx, None, {**fade_sound, "range_filtered": True})
        if e.data.get("fortify_at", math.inf) <= now:
            e.data["hp"] += e.data.pop("fortify_hp")
            e.data.pop("fortify_at")
        if not device_operational(ctx, e):
            keep.append(e)
            continue
        bot_radius = e.props.get("bot_trigger_radius")
        if (bot_radius and ctx.owner is not None and ctx.owner.alive and ctx.owner.is_bot
                and not statuses.flag(m, ctx.owner, "no_abilities")
                and ctx.owner.duel_id == e.props.get("duel_id", 0)
                and not m.in_deathmatch_spawn(ctx.owner) and any(
                    p.alive and p.team != e.team and not p.dm_ghost
                    and p.duel_id == ctx.owner.duel_id
                    and (p.pos - e.pos).length() <= bot_radius and not m.deathmatch_spawn_protected(p)
                    for p in m.players.values()
                )):
            activate_device(m, e)
            continue
        if e.props.get("move") and e.a is None and not e.props.get("move_through_walls"):
            step = ctx.aim * (float(e.props["move"]) * dt)
            e.data["previous_pos"] = e.pos
            e.pos = m._clip_to_walls(e.pos, e.pos + step, int(e.props["source_level"]))
            ctx.point = e.pos
        for tr in triggers:
            when = str(tr.get("when", ""))
            if when in ("expire", "activate"):
                continue
            if when == "start" and e.props.get("started"):
                continue
            fn = TRIGGERS.get(when)
            if fn is None:
                warnings.warn(f"Unknown trigger '{when}'")
                continue
            players = fn(ctx, tr)
            if players is not None:
                _fire(ctx, tr, players)
            if e.props.get("ended"):
                break
        e.props["started"] = True
        if not e.props.get("ended"):
            keep.append(e)
    if m.mode == "deathmatch" and m.phase == "over":
        return
    # objects placed by triggers this frame were appended behind the old ones; they start next frame
    m.effects = keep + m.effects[len(existing):]
    for p in m.players.values():
        statuses.tick_player(m, p, dt)
        _passives(m, p, dt)
        _recharge(m, p, dt)
        p.last_pos = p.pos


def _passives(m: Match, p: PlayerState, dt: float) -> None:
    for tr in m.agents.get(p.agent, {}).get("passives", []):
        fn = PASSIVE_TRIGGERS.get(str(tr.get("when", "")))
        if fn is None:
            continue
        if not p.alive and tr.get("when") != "death":
            continue
        for other in fn(m, p, tr, dt):
            ctx = Ctx(m, p, p.team, p.pos, p.pos, heading(p.facing), ability={"name": tr.get("name", "passive")}, other=other, dt=dt)
            run_steps(ctx, list(tr.get("do", [])), select(ctx, tr, default="self"))


def schedule_ability_return(m: Match, p: PlayerState, key: str, delay: float) -> None:
    ready_at = m.time + delay
    if m.mode == "deathmatch":
        p.dm_device_recalls.setdefault(key, []).append(ready_at)
    else:
        p.ability_ready_at[key] = ready_at


def _return_ability(m: Match, p: PlayerState, key: str, ab: dict[str, Any], count: int) -> None:
    if key == "X" and ab.get("free_with_status"):
        statuses.apply_status(m, p, ab["free_with_status"], float("inf"))
    else:
        p.charges[key] = min(int(ab["max"]), p.charges.get(key, 0) + count)


def _recharge(m: Match, p: PlayerState, dt: float) -> None:
    if m.mode == "deathmatch":
        if m.phase == "live":
            kit = m.agents[p.agent]["abilities"]
            for key, deadlines in list(p.dm_device_recalls.items()):
                pending = [deadline for deadline in deadlines if deadline > m.time]
                returned = len(deadlines) - len(pending)
                if returned and (key != "X" or p.alive):
                    _return_ability(m, p, key, kit[key], returned)
                elif returned:
                    continue
                if pending:
                    p.dm_device_recalls[key] = pending
                else:
                    del p.dm_device_recalls[key]
            cooldowns = m.deathmatch_rules["ability_cooldowns"].get(p.agent, ())
            for key, cooldown in zip(("C", "Q", "E"), cooldowns):
                if cooldown <= 0:
                    continue
                ab = kit[key]
                if p.agent == "veto" and key == "E" and statuses.has(m, p, "veto_interceptor_ready"):
                    continue
                if p.agent == "clove" and key == "E" and not p.alive and p.charges.get(key, 0) >= 1:
                    p.recharge_timers[key] = min(cooldown, p.recharge_timers.get(key, 0.0) + dt)
                    continue
                if ab.get("shared_charge") or p.charges.get(key, 0) >= int(ab["max"]):
                    p.recharge_timers[key] = 0.0
                    continue
                if p.charges.get(key, 0) + len(p.dm_device_recalls.get(key, ())) >= int(ab["max"]):
                    continue
                elapsed = p.recharge_timers.get(key, 0.0) + dt
                if elapsed >= cooldown:
                    p.charges[key] = p.charges.get(key, 0) + 1
                    elapsed -= cooldown
                p.recharge_timers[key] = elapsed
        return
    if m.phase not in ("buy", "live", "planted"):
        return
    for key, ab in m.agents.get(p.agent, {}).get("abilities", {}).items():
        if not p.alive and not ab.get("dead_range"):
            continue
        ready_at = p.ability_ready_at.get(key)
        if ready_at is not None and m.time >= ready_at:
            _return_ability(m, p, key, ab, 1)
            del p.ability_ready_at[key]
        if m.phase == "buy" or key == "X" or "recharge" not in ab:
            continue
        maximum = int(ab["max"]) if p.alive else 1
        if p.charges.get(key, 0) >= maximum:
            p.recharge_timers[key] = 0.0
            continue
        p.recharge_timers[key] = p.recharge_timers.get(key, 0.0) + dt
        if p.recharge_timers[key] >= float(ab["recharge"]):
            p.recharge_timers[key] = 0.0
            p.charges[key] = p.charges.get(key, 0) + 1
            p.temporary_charges[key] = p.temporary_charges.get(key, 0) + 1
