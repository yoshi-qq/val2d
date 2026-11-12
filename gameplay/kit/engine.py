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


def run_steps(ctx: Ctx, steps: list[dict[str, Any]], players: list[PlayerState] | None = None,
              trigger_spec: dict[str, Any] | None = None) -> bool:
    """Runs steps in order. `players` (from a trigger) are used by every step that names no `who`.
    Returns False if a step cancelled (only matters on use)."""
    for step in steps:
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
    if spec.get("travel_speed"):
        delay += (point - ctx.source).length() / float(spec["travel_speed"])
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
    e = Effect(look, ctx.owner.pid if ctx.owner else -1, ctx.team, point, now + delay + lasts,
               radius=float(spec.get("radius", 0.0)), a=a, b=b, start=now + delay, props=props)
    for key in ("hp", "hit_radius", "destroy_recharge", "recall_recharge", "owner_range", "reactivate", "detect_range",
                "cancel_channel"):
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


def use(m: Match, p: PlayerState, key: str, ab: dict[str, Any], point: Vec | None = None) -> Vec | None:
    """Carries out ability `ab`. Returns the target point, or None if nothing happened (no charge used).
    point: a point chosen on the map (multi-placement); it is kept within `range` of the user."""
    spec = expand(ab)
    if point is not None and not spec.get("global_target"):
        reach = float(spec.get("range", 30.0))
        offset = point - p.pos
        if offset.length() > reach:
            point = p.pos + offset.normalized() * reach
    if point is None:
        point = resolve_target(m, p, spec)
    return _use_at(m, p, key, spec, point)


def _use_at(m: Match, p: PlayerState, key: str, spec: dict[str, Any], point: Vec | None) -> Vec | None:
    if point is None:
        return None
    ctx = Ctx(m, p, p.team, point, p.pos, heading(p.facing), ability=spec, key=key)
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
        seen.update(p.pid for p in players)
    run_steps(ctx, list(tr.get("do", [])), players, tr)
    if tr.get("consume"):
        ctx.obj.props["ended"] = True  # type: ignore[union-attr]


def aimed_device(m: Match, p: PlayerState, depth: float) -> Effect | None:
    cursor = p.pos + heading(p.facing) * depth
    devices = [e for e in m.effects if e.owner == p.pid
               and (e.props.get("manual") or e.props.get("recall_recharge") is not None) and not e.props.get("ended")
               and e.start <= m.time < e.until
               and min((pos - cursor).length() for pos in device_hit_points(e)) <= 1.25
               and m._line_clear(p.pos, e.pos, p.level, ignore_effects=True)]
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
    e.props["ended"] = True
    owner = m.players.get(e.owner)
    delay = e.props.get(f"{reason}_recharge")
    if owner is not None and delay is not None:
        owner.ability_ready_at[e.props["key"]] = m.time + float(delay)
    if owner is not None and e.props.get("cancel_channel"):
        owner.channel_until = 0.0


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
    if marker is None or not p.alive:
        return False
    marker.props["ended"] = True
    p.pos = p.last_pos = marker.pos
    p.hp = m._hp
    p.armor, p.armor_key, p.armor_reserve, p.armor_regen_at = marker.data["return_armor"]
    p.facing = marker.data["return_facing"]
    p.vel, p.z, p.vz = Vec(0, 0), 0.0, 0.0
    reach = marker.props.get("source_level", float("inf"))
    p.ground = m.world.ground_height(p.pos, reach) * float(m._mv["level_height"])
    p.level = m.world.floor_level(p.pos, reach)
    p.plant_progress = p.defuse_progress = p.reload_until = p.dash_until = 0.0
    p.heal_left = p.heal_rate = 0.0
    statuses.clear_statuses(p, m, keep_positive=False)
    from gameplay.kit.builtins import game_event
    game_event(m, "ability_return", {"pid": p.pid, "pos": (p.pos.x, p.pos.y), "facing": p.facing})
    return True


def tick(m: Match, dt: float) -> None:
    now = m.time
    keep: list[Effect] = []
    existing = list(m.effects)
    for e in existing:
        if e.props.get("ended"):
            continue
        triggers: list[dict[str, Any]] = e.props.get("triggers", [])
        ctx = _ctx_for(m, e, dt)
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
            if (revived := m.players.get(e.props.get("revive_pid"))) is not None and not revived.alive:
                EFFECTS["revive"].fn(ctx, revived, {"health": e.data["revive_health"]})
            for tr in triggers:
                if tr.get("when") == "expire":
                    _fire(ctx, tr, select(ctx, tr))
            continue
        if now < e.start:
            keep.append(e)
            continue
        if e.data.get("fortify_at", math.inf) <= now:
            e.data["hp"] += e.data.pop("fortify_hp")
            e.data.pop("fortify_at")
        if not device_operational(ctx, e):
            keep.append(e)
            continue
        bot_radius = e.props.get("bot_trigger_radius")
        if bot_radius and ctx.owner is not None and ctx.owner.alive and ctx.owner.is_bot and any(
            p.alive and p.team != e.team and (p.pos - e.pos).length() <= bot_radius for p in m.players.values()
        ):
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


def _recharge(m: Match, p: PlayerState, dt: float) -> None:
    if not p.alive or m.phase not in ("live", "planted"):
        return
    for key, ab in m.agents.get(p.agent, {}).get("abilities", {}).items():
        ready_at = p.ability_ready_at.get(key)
        if ready_at is not None and m.time >= ready_at:
            p.charges[key] = min(int(ab["max"]), p.charges.get(key, 0) + 1)
            del p.ability_ready_at[key]
        if key == "X" or "recharge" not in ab:
            continue
        if p.charges.get(key, 0) >= int(ab["max"]):
            p.recharge_timers[key] = 0.0
            continue
        p.recharge_timers[key] = p.recharge_timers.get(key, 0.0) + dt
        if p.recharge_timers[key] >= float(ab["recharge"]):
            p.recharge_timers[key] = 0.0
            p.charges[key] = p.charges.get(key, 0) + 1
            p.temporary_charges[key] = p.temporary_charges.get(key, 0) + 1
