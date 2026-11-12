"""Built-in mechanics of the ability kit: targets, player sets, effects and triggers.

Names here are what config/content/agents/*.py uses. Add new ones the same way (here or in config/content/mechanics/).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gameplay.geometry import Vec, angle_diff, angle_of, heading, segments_intersect
from gameplay.kit import statuses
from gameplay.kit.registry import Ctx, effect, passive_trigger, target, trigger, who

if TYPE_CHECKING:
    from gameplay.match import Match, PlayerState

BODY = 0.4  # player radius used for areas and lines


def game_event(m: Match, kind: str, data: dict[str, Any]) -> None:
    from gameplay.match import GameEvent
    m.events.append(GameEvent(kind, m.time, data))


# ------------------------------------------------------------------ targets: where an ability goes
def _aim_point(m: Match, p: PlayerState, spec: dict[str, Any], clip: bool) -> Vec:
    reach = min(p.cursor_depth, float(spec.get("range", p.cursor_depth)))
    point = p.pos + heading(p.facing) * reach
    return m._clip_to_walls(p.pos, point, p.level) if clip else point


@target("aim")
def t_aim(m: Match, p: PlayerState, spec: dict[str, Any]) -> Vec:
    """The cursor, at most `range` away, stopped in front of walls."""
    return _aim_point(m, p, spec, clip=True)


@target("aim_free")
def t_aim_free(m: Match, p: PlayerState, spec: dict[str, Any]) -> Vec:
    """The cursor, at most `range` away, through walls (remote smokes, flashes over walls)."""
    return _aim_point(m, p, spec, clip=False)


@target("self")
def t_self(m: Match, p: PlayerState, spec: dict[str, Any]) -> Vec:
    return p.pos


@target("ahead")
def t_ahead(m: Match, p: PlayerState, spec: dict[str, Any]) -> Vec:
    """A point straight ahead at the full `range` (beams, waves)."""
    return p.pos + heading(p.facing) * float(spec.get("range", spec.get("length", 10.0)))


# ------------------------------------------------------------------ player sets: who is affected
def _alive(m: Match) -> list[PlayerState]:
    return [t for t in m.players.values() if t.alive]


@who("enemies")
def w_enemies(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState]:
    return [t for t in _alive(ctx.m) if t.team != ctx.team]


@who("allies")
def w_allies(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState]:
    """Teammates without the owner."""
    return [t for t in _alive(ctx.m) if t.team == ctx.team and (ctx.owner is None or t.pid != ctx.owner.pid)]


@who("team")
def w_team(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState]:
    """Teammates and the owner."""
    return [t for t in _alive(ctx.m) if t.team == ctx.team]


@who("self")
def w_self(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState]:
    return [ctx.owner] if ctx.owner is not None and ctx.owner.alive else []


@who("everyone")
def w_everyone(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState]:
    return _alive(ctx.m)


@who("others")
def w_others(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState]:
    return [t for t in _alive(ctx.m) if ctx.owner is None or t.pid != ctx.owner.pid]


@who("other")
def w_other(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState]:
    """The second player of a passive trigger (victim of a kill, attacker of a hit)."""
    return [ctx.other] if ctx.other is not None else []


def _under_cursor(ctx: Ctx, spec: dict[str, Any], dead: bool) -> PlayerState | None:
    p = ctx.owner
    if p is None:
        return None
    reach = float(spec.get("range", ctx.ability.get("range", 10.0)))
    aim_point = p.pos + heading(p.facing) * min(p.cursor_depth, reach)
    best, best_d = None, 2.0
    for t in ctx.m.players.values():
        if t.team != p.team or t.pid == p.pid or t.alive == dead or (t.pos - p.pos).length() > reach:
            continue
        d = (t.pos - aim_point).length()
        if d < best_d:
            best, best_d = t, d
    return best


@who("cursor_ally")
def w_cursor_ally(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState]:
    """The teammate under the cursor within `range`, else the owner."""
    t = _under_cursor(ctx, spec, dead=False)
    return [t] if t is not None else w_self(ctx, spec)


@who("cursor_fallen")
def w_cursor_fallen(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState]:
    """A fallen teammate under the cursor within `range` (for revives)."""
    t = _under_cursor(ctx, spec, dead=True)
    return [t] if t is not None else []


def _seg_distance(p: Vec, a: Vec, b: Vec) -> float:
    ab = b - a
    length2 = ab.dot(ab)
    t = 0.0 if length2 <= 0 else max(0.0, min(1.0, (p - a).dot(ab) / length2))
    return (p - (a + ab * t)).length()


def in_area(ctx: Ctx, t: PlayerState, spec: dict[str, Any]) -> bool:
    """Area of a step or trigger: circle (default when a radius is known), line, beam or everywhere."""
    obj = ctx.obj
    radius = float(spec.get("radius", obj.radius if obj is not None else 0.0))
    area = spec.get("area") or ("circle" if radius > 0 else "everywhere")
    if area == "everywhere":
        return True
    if area == "circle":
        return (t.pos - ctx.point).length() <= radius
    if area == "line" and obj is not None and obj.a is not None and obj.b is not None:
        return _seg_distance(t.pos, obj.a, obj.b) <= float(spec.get("width", 0.0)) / 2 + BODY
    if area == "beam":
        rel = t.pos - ctx.source
        along = rel.dot(ctx.aim)
        length = float(spec.get("length", ctx.ability.get("length", 10.0)))
        half = float(spec.get("width", ctx.ability.get("width", 1.0))) / 2
        return 0 < along <= length and abs(ctx.aim.cross(rel)) <= half + BODY
    return False


def passes_filters(ctx: Ctx, t: PlayerState, spec: dict[str, Any]) -> bool:
    sight = spec.get("sight")  # None, "walls" (walls block) or "all" (smokes block too)
    if sight and not ctx.m._line_clear(ctx.point, t.pos, 0 if sight == "walls" else t.level, ignore_effects=sight == "walls"):
        return False
    cone = spec.get("facing")  # the player must look toward the point (flashes)
    if cone is not None and abs(angle_diff(t.facing, angle_of(ctx.point - t.pos))) > float(cone) / 2:
        return False
    return True


def select(ctx: Ctx, spec: dict[str, Any], default: str = "enemies") -> list[PlayerState]:
    from gameplay.kit.registry import WHO
    name = str(spec.get("who", default))
    fn = WHO.get(name)
    if fn is None:
        import warnings
        warnings.warn(f"Unknown player set '{name}'")
        return []
    found = [t for t in fn(ctx, spec) if (name.startswith("cursor") or in_area(ctx, t, spec)) and passes_filters(ctx, t, spec)]
    if spec.get("first") and found:
        found.sort(key=lambda t: (t.pos - ctx.point).length())
        return found[:1]
    return found


# ------------------------------------------------------------------ effects on players
@effect("damage")
def e_damage(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """amount, falloff (share lost at the edge of the radius), zone."""
    if t is None:
        return
    amount = float(step["amount"])
    falloff = float(step.get("falloff", 0.0))
    radius = float(step.get("radius", ctx.obj.radius if ctx.obj is not None else 0.0))
    if falloff and radius > 0:
        amount *= 1.0 - falloff * min(1.0, (t.pos - ctx.point).length() / radius)
    if int(amount) > 0:
        ctx.m._damage(ctx.owner, t, int(amount), str(step.get("zone", "body")), f"ability:{ctx.ability.get('name', 'ability')}")


@effect("dps")
def e_dps(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """per_second: damage over time while the trigger keeps firing (use with `tick`)."""
    if t is None:
        return
    store = ctx.obj.data if ctx.obj is not None else {}
    key = f"dps{t.pid}"
    store[key] = store.get(key, 0.0) + float(step["per_second"]) * ctx.dt
    whole = int(store[key])
    if whole >= 1:
        store[key] -= whole
        ctx.m._damage(ctx.owner, t, whole, "body", f"ability:{ctx.ability.get('name', 'ability')}")


@effect("status")
def e_status(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """name, seconds (any status in config/content/statuses.py)."""
    if t is not None:
        statuses.apply_status(ctx.m, t, str(step["name"]), float(step.get("seconds", 1.0)))


@effect("heal", who="team")
def e_heal(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """amount, over (seconds; 0 = at once)."""
    if t is None:
        return
    amount, over = float(step["amount"]), float(step.get("over", 0.0))
    if over > 0:
        t.heal_left += amount
        t.heal_rate = amount / over
    else:
        statuses._heal_whole(ctx.m, t, amount)


@effect("heal_rate", who="team")
def e_heal_rate(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """per_second while the trigger keeps firing (healing zones)."""
    if t is not None:
        statuses._heal_whole(ctx.m, t, float(step["per_second"]) * ctx.dt)


@effect("shield", who="team")
def e_shield(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """points of armor (keeps higher armor)."""
    if t is not None:
        t.armor = max(t.armor, int(step["points"]))


@effect("reveal")
def e_reveal(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """seconds the player is visible to everyone."""
    if t is not None:
        t.revealed_until = max(t.revealed_until, ctx.m.time + float(step.get("seconds", 1.5)))


@effect("cleanse", who="team")
def e_cleanse(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """Removes all harmful statuses."""
    if t is not None:
        statuses.clear_statuses(t, ctx.m)


@effect("immunity", who="self")
def e_immunity(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """seconds without harmful statuses (clears current ones)."""
    if t is not None:
        statuses.clear_statuses(t, ctx.m)
        t.immune_until = ctx.m.time + float(step["seconds"])


@effect("revive", who="cursor_fallen")
def e_revive(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """Brings a fallen player back with `health` (default full)."""
    if t is None:
        return
    t.alive, t.hp = True, int(step.get("health", ctx.m._hp))
    statuses.clear_statuses(t, ctx.m)
    game_event(ctx.m, "revive", {"pid": t.pid, "by": ctx.owner.pid if ctx.owner else None})


def _move_player(ctx: Ctx, t: PlayerState, offset: Vec) -> None:
    if offset.length() < 1e-6:
        return
    t.pos = ctx.m._clip_to_walls(t.pos, t.pos + offset, t.level)


@effect("push")
def e_push(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """strength in metres away from the point (stops at walls)."""
    if t is not None:
        away = (t.pos - ctx.point)
        _move_player(ctx, t, (away.normalized() if away.length() > 0.01 else ctx.aim) * float(step.get("strength", 2.0)))


@effect("pull")
def e_pull(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """strength in metres toward the point (never past it)."""
    if t is not None:
        to = ctx.point - t.pos
        _move_player(ctx, t, to.normalized() * min(to.length(), float(step.get("strength", 2.0))))


@effect("knock_up")
def e_knock_up(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """velocity upward in m/s (players fly and land; falls can hurt)."""
    if t is not None:
        t.vz = max(t.vz, float(step.get("velocity", 4.0)))


# ------------------------------------------------------------------ effects on the owner (movement, resources)
@effect("dash", per_player=False)
def e_dash(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """distance, duration: a fast move in the walking direction (or the aim when standing)."""
    p = ctx.owner
    if p is None:
        return
    move = p.vel.normalized() if p.vel.length() > 0.3 else ctx.aim
    p.dash_vel = move * (float(step["distance"]) / float(step["duration"]))
    p.dash_until = ctx.m.time + float(step["duration"])


@effect("hop", per_player=False)
def e_hop(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """velocity: a high jump."""
    if ctx.owner is not None:
        ctx.owner.vz = float(step["velocity"])


@effect("teleport", per_player=False)
def e_teleport(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> bool:
    """Moves the owner to the point, also up onto crates and platforms, if it lies within `range` measured in 3D
    (r² = x² + y² + z², z = height difference); cancels if it is too close or out of range."""
    p = ctx.owner
    if p is None:
        return False
    lh = float(ctx.m._mv["level_height"])
    ground = ctx.m.world.ground_height(ctx.point) * lh
    flat = (ctx.point - p.pos).length()
    rise = ground - (p.ground + p.z)
    reach = float(step.get("range", ctx.ability.get("range", 8.0)))
    if flat < 0.5 or (flat * flat + rise * rise) ** 0.5 > reach + 1e-6:
        return False
    p.pos, p.vel = ctx.point, Vec(0, 0)
    p.ground, p.z, p.vz = ground, 0.0, 0.0
    p.level = int(ground / lh + 0.5)
    return True


@effect("anchor", per_player=False)
def e_anchor(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """First use sets a return point (free), second use within `seconds` returns there."""
    p = ctx.owner
    if p is None:
        return
    if p.anchor is not None and p.anchor_until > ctx.m.time:
        p.pos, p.vel, p.anchor = p.anchor, Vec(0, 0), None
        ctx.point = p.pos
        return
    p.anchor, p.anchor_until = p.pos, ctx.m.time + float(step.get("seconds", 60.0))
    if ctx.key:
        p.charges[ctx.key] = p.charges.get(ctx.key, 0) + 1  # setting is free; the charge is used on return


@effect("overdrive", per_player=False)
def e_overdrive(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """seconds of no moving inaccuracy and faster fire (rate_mult of the ultimate)."""
    if ctx.owner is not None:
        ctx.owner.overdrive_until = ctx.m.time + float(step["seconds"])


@effect("charge", per_player=False)
def e_charge(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """slot, amount: gives charges back (never above the slot's max)."""
    p = ctx.owner
    if p is None:
        return
    slot = str(step.get("slot", ctx.key or "E"))
    ab = ctx.m.agents.get(p.agent, {}).get("abilities", {}).get(slot, {})
    p.charges[slot] = min(int(ab.get("max", 1)), p.charges.get(slot, 0) + int(step.get("amount", 1)))


@effect("ult_points", per_player=False)
def e_ult_points(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    if ctx.owner is not None:
        ctx.owner.ult_points += int(step.get("amount", 1))


@effect("credits", per_player=False)
def e_credits(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    if ctx.owner is not None:
        ctx.owner.credits += int(step.get("amount", 0))


# ------------------------------------------------------------------ effects on the world
@effect("spawn", per_player=False)
def e_spawn(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """place: another object at the point (a grenade that leaves fire, a wall that leaves smokes)."""
    from gameplay.kit.engine import place
    place(ctx, dict(step["place"]), ctx.point)


@effect("noise", per_player=False)
def e_noise(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """A footstep sound at the point (decoys); enemies hear it like a real one."""
    pid = ctx.owner.pid if ctx.owner else -1
    game_event(ctx.m, "sound", {"pid": pid, "pos": (ctx.point.x, ctx.point.y),
                                "radius": float(step.get("radius", ctx.m._sound["run_radius"])),
                                "kind": str(step.get("kind", "step")), "decoy": True})


@effect("event", per_player=False)
def e_event(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """kind: a visual/sound event for the client (blast, flash)."""
    radius = float(step.get("radius", ctx.obj.radius if ctx.obj is not None else 0.0))
    game_event(ctx.m, str(step["kind"]), {"pos": (ctx.point.x, ctx.point.y), "radius": radius,
                                          "pid": ctx.owner.pid if ctx.owner else None})


@effect("end", per_player=False)
def e_end(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """Ends the object this trigger belongs to (expire triggers do not run)."""
    if ctx.obj is not None:
        ctx.obj.props["ended"] = True


# ------------------------------------------------------------------ triggers of placed objects
# A trigger gets the context and its spec and returns the players it fires for, or None if it does not fire.
@trigger("tick")
def tr_tick(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState] | None:
    """Every frame while the object is active (use per-second effects: dps, heal_rate)."""
    return select(ctx, spec)


@trigger("every")
def tr_every(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState] | None:
    """seconds: periodically while the object is active (pulses)."""
    period = float(spec.get("seconds", 1.0))
    now, before = ctx.m.time, ctx.m.time - ctx.dt
    if int(now / period) == int(before / period):
        return None
    return select(ctx, spec)


@trigger("enter")
def tr_enter(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState] | None:
    """A player of the set steps into the area (once per stay)."""
    assert ctx.obj is not None
    inside = select(ctx, spec)
    tag = f"in:{id(spec)}"
    before = set(ctx.obj.props.get(tag, ()))
    ctx.obj.props[tag] = [t.pid for t in inside]
    fresh = [t for t in inside if t.pid not in before]
    return fresh or None


@trigger("leave")
def tr_leave(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState] | None:
    """A player of the set leaves the area."""
    assert ctx.obj is not None
    inside = {t.pid for t in select(ctx, spec)}
    tag = f"out:{id(spec)}"
    before = set(ctx.obj.props.get(tag, ()))
    ctx.obj.props[tag] = list(inside)
    gone = [ctx.m.players[pid] for pid in before - inside if pid in ctx.m.players]
    return gone or None


@trigger("cross")
def tr_cross(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState] | None:
    """A player of the set crosses the object's line (walls, tripwires)."""
    obj = ctx.obj
    if obj is None or obj.a is None or obj.b is None:
        return None
    from gameplay.kit.registry import WHO
    found = []
    for t in WHO[str(spec.get("who", "enemies"))](ctx, spec):
        last = t.last_pos if t.last_pos is not None else t.pos
        if segments_intersect(last, t.pos, obj.a, obj.b):
            found.append(t)
    if spec.get("first"):
        found = found[:1]
    return found or None


def _event_players(ctx: Ctx, spec: dict[str, Any], kinds: tuple[str, ...]) -> list[PlayerState] | None:
    from gameplay.kit.registry import WHO
    allowed = {t.pid for t in WHO[str(spec.get("who", "enemies"))](ctx, spec)}
    found = []
    for ev in ctx.m.events:
        if ev.kind not in kinds or ev.data.get("decoy"):
            continue
        t = ctx.m.players.get(ev.data.get("pid"))
        if t is not None and t.pid in allowed and in_area(ctx, t, spec) and t not in found:
            found.append(t)
    if spec.get("first"):
        found = found[:1]
    return found or None


@trigger("noise")
def tr_noise(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState] | None:
    """A player of the set makes a sound (running, landing) inside the area."""
    return _event_players(ctx, spec, ("sound",))


@trigger("gunfire")
def tr_gunfire(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState] | None:
    """A player of the set fires a weapon inside the area."""
    return _event_players(ctx, spec, ("shot",))


# start and expire are run by the engine itself; registering them makes the names known
@trigger("start")
def tr_start(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState] | None:
    """Once, when the object becomes active (after its delay)."""
    return select(ctx, spec)


@trigger("expire")
def tr_expire(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState] | None:
    """Once, when the object's time runs out (grenades, flashes)."""
    return select(ctx, spec)


# ------------------------------------------------------------------ passive triggers of agents
# A passive trigger gets the match, the agent's player and its spec, and returns a list of
# (other player or None) for every time it fires this frame.
@passive_trigger("kill")
def pt_kill(m: Match, p: PlayerState, spec: dict[str, Any], dt: float) -> list[PlayerState | None]:
    return [m.players.get(ev.data.get("pid")) for ev in m.events if ev.kind == "kill" and ev.data.get("by") == p.pid]


@passive_trigger("death")
def pt_death(m: Match, p: PlayerState, spec: dict[str, Any], dt: float) -> list[PlayerState | None]:
    return [m.players.get(ev.data.get("by")) for ev in m.events if ev.kind == "kill" and ev.data.get("pid") == p.pid]


@passive_trigger("damage_dealt")
def pt_dealt(m: Match, p: PlayerState, spec: dict[str, Any], dt: float) -> list[PlayerState | None]:
    return [m.players.get(ev.data.get("pid")) for ev in m.events if ev.kind == "hit" and ev.data.get("by") == p.pid]


@passive_trigger("damage_taken")
def pt_taken(m: Match, p: PlayerState, spec: dict[str, Any], dt: float) -> list[PlayerState | None]:
    return [m.players.get(ev.data.get("by")) for ev in m.events if ev.kind == "hit" and ev.data.get("pid") == p.pid]


@passive_trigger("ability_used")
def pt_ability(m: Match, p: PlayerState, spec: dict[str, Any], dt: float) -> list[PlayerState | None]:
    slot = spec.get("slot")
    return [None for ev in m.events if ev.kind == "ability" and ev.data.get("pid") == p.pid
            and (slot is None or ev.data.get("key") == slot)]


@passive_trigger("every")
def pt_every(m: Match, p: PlayerState, spec: dict[str, Any], dt: float) -> list[PlayerState | None]:
    period = float(spec.get("seconds", 1.0))
    return [None] if p.alive and int(m.time / period) != int((m.time - dt) / period) else []


@passive_trigger("low_health")
def pt_low(m: Match, p: PlayerState, spec: dict[str, Any], dt: float) -> list[PlayerState | None]:
    """Once each time health drops below `below`."""
    below = float(spec.get("below", 30))
    tag = f"low:{id(spec)}"
    was = p.passive_state.get(tag, False)
    now = p.alive and p.hp < below
    p.passive_state[tag] = now
    return [None] if now and not was else []
