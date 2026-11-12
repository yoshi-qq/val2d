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

import warnings
from typing import TYPE_CHECKING, Any

from gameplay.geometry import Vec, heading
from gameplay.kit import statuses
from gameplay.kit.builtins import damage_map_cover, select
from gameplay.kit.registry import EFFECTS, PASSIVE_TRIGGERS, PRESETS, TARGETS, TRIGGERS, Ctx

if TYPE_CHECKING:
    from gameplay.match import Effect, Match, PlayerState

LOOKS = ("smoke", "wall", "flash", "zone", "blast", "sensor", "alarm", "tripwire", "decoy", "none")


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


def place(ctx: Ctx, spec: dict[str, Any], point: Vec) -> Effect:
    """Leaves an object in the world at `point`."""
    from gameplay.match import Effect
    m, now = ctx.m, ctx.m.time
    look = str(spec.get("look", "zone"))
    if look not in LOOKS:
        warnings.warn(f"Unknown look '{look}'; drawn as a zone")
        look = "zone"
    delay, lasts = float(spec.get("delay", 0.0)), float(spec.get("lasts", 10.0))
    a = b = None
    if spec.get("shape") == "line":
        across = ctx.aim if spec.get("along") else ctx.aim.rotated(90)  # along=True: the line points where you aim
        side = across * (float(spec.get("length", 6.0)) / 2)
        a, b = point - side, point + side
        if spec.get("clip_ends"):
            level = ctx.owner.level if ctx.owner else 0
            a, b = m._clip_to_walls(point, a, level), m._clip_to_walls(point, b, level)
    elif spec.get("thrown"):
        a = ctx.source
    triggers = list(spec.get("triggers", []))
    props: dict[str, Any] = {
        "triggers": triggers, "ability": ctx.ability, "key": ctx.key, "source": (ctx.source.x, ctx.source.y),
        "aim": (ctx.aim.x, ctx.aim.y), "blocks_sight": spec.get("blocks_sight", look in ("smoke", "wall")),
        "hidden": spec.get("hidden", {"decoy": "all", "alarm": "enemies", "tripwire": "enemies"}.get(look)),
        "status": spec.get("status_hint") or _status_hint(triggers), "move": float(spec.get("move", 0.0)),
        "thrown": bool(spec.get("thrown")),
        "source_level": ctx.obj.props.get("source_level", 0) if ctx.obj else (ctx.owner.level if ctx.owner else 0),
    }
    e = Effect(look, ctx.owner.pid if ctx.owner else -1, ctx.team, point, now + delay + lasts,
               radius=float(spec.get("radius", 0.0)), a=a, b=b, start=now + delay, props=props)
    m.effects.append(e)
    return e


def use(m: Match, p: PlayerState, key: str, ab: dict[str, Any], point: Vec | None = None) -> Vec | None:
    """Carries out ability `ab`. Returns the target point, or None if nothing happened (no charge used).
    point: a point chosen on the map (multi-placement); it is kept within `range` of the user."""
    spec = expand(ab)
    if point is not None:
        reach = float(spec.get("range", 30.0))
        offset = point - p.pos
        if offset.length() > reach:
            point = p.pos + offset.normalized() * reach
        return _use_at(m, p, key, spec, point)
    target_name = str(spec.get("target", "aim"))
    finder = TARGETS.get(target_name)
    if finder is None:
        raise ValueError(f"unknown target '{target_name}'")
    point = finder(m, p, spec)
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
    run_steps(ctx, list(tr.get("do", [])), players, tr)
    if tr.get("consume"):
        ctx.obj.props["ended"] = True  # type: ignore[union-attr]


def tick(m: Match, dt: float) -> None:
    now = m.time
    keep: list[Effect] = []
    existing = list(m.effects)
    for e in existing:
        triggers: list[dict[str, Any]] = e.props.get("triggers", [])
        ctx = _ctx_for(m, e, dt)
        if m.cover_health and e.props.get("thrown") and e.a is not None and now >= e.start and e.until > e.start:
            progress = min(1.0, (now - e.start) / (e.until - e.start))
            previous = e.data.get("glass_progress", 0.0)
            path = e.pos - e.a
            if progress > previous:
                m.break_glass(e.a + path * previous, e.a + path * progress, e.props["source_level"])
                e.data["glass_progress"] = progress
        if now >= e.until:
            for tr in triggers:
                if tr.get("when") == "expire":
                    _fire(ctx, tr, select(ctx, tr))
            continue
        if now < e.start:
            keep.append(e)
            continue
        if e.props.get("move") and e.a is None:
            step = ctx.aim * (float(e.props["move"]) * dt)
            e.pos = m._clip_to_walls(e.pos, e.pos + step, 0)
            ctx.point = e.pos
        for tr in triggers:
            when = str(tr.get("when", ""))
            if when == "expire":
                continue
            if when == "start":
                if e.props.get("started"):
                    continue
                e.props["started"] = True
            fn = TRIGGERS.get(when)
            if fn is None:
                warnings.warn(f"Unknown trigger '{when}'")
                continue
            players = fn(ctx, tr)
            if players is not None:
                _fire(ctx, tr, players)
            if e.props.get("ended"):
                break
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
        if key == "X" or "recharge" not in ab:
            continue
        if p.charges.get(key, 0) >= int(ab["max"]):
            p.recharge_timers[key] = 0.0
            continue
        p.recharge_timers[key] = p.recharge_timers.get(key, 0.0) + dt
        if p.recharge_timers[key] >= float(ab["recharge"]):
            p.recharge_timers[key] = 0.0
            p.charges[key] = p.charges.get(key, 0) + 1
