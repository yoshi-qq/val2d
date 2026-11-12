"""Built-in mechanics of the ability kit: targets, player sets, effects and triggers.

Names here are what config/content/agents/*.py uses. Add new ones the same way (here or in config/content/mechanics/).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gameplay.geometry import Rect, Vec, angle_diff, angle_of, heading, segments_intersect
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


def throw_factor(m: Match, spec: dict[str, Any]) -> float:
    """Hidden share of the cursor distance a throwable flies (its own `throw_factor`, else the rule)."""
    from gameplay.data import rule
    return float(spec.get("throw_factor", rule("abilities", "throw_factor", 0.8)))


@target("throw")
def t_throw(m: Match, p: PlayerState, spec: dict[str, Any]) -> Vec:
    """Throwables: no landing preview; the throw flies throw_factor times the cursor distance (at most `range`),
    stopped by walls unless it flies over them (through_walls)."""
    reach = min(p.cursor_depth * throw_factor(m, spec), float(spec.get("range", p.cursor_depth)))
    point = p.pos + heading(p.facing + float(spec.get("curve_angle", 0))) * reach
    return point if spec.get("through_walls") else m._clip_to_walls(p.pos, point, p.level)


@target("aim_free")
def t_aim_free(m: Match, p: PlayerState, spec: dict[str, Any]) -> Vec:
    """The cursor, at most `range` away, through walls (remote smokes, flashes over walls)."""
    return _aim_point(m, p, spec, clip=False)


@target("teleport_aim")
def t_teleport_aim(m: Match, p: PlayerState, spec: dict[str, Any]) -> Vec | None:
    point = _aim_point(m, p, spec, clip=True)
    return point if can_land(m, p, point) else None


@target("self")
def t_self(m: Match, p: PlayerState, spec: dict[str, Any]) -> Vec:
    return p.pos


@target("enemy_corpse")
def t_enemy_corpse(m: Match, p: PlayerState, spec: dict[str, Any]) -> Vec | None:
    reach = float(spec["range"])
    cursor = _aim_point(m, p, spec, clip=False)
    candidates = [t.pos for t in m.players.values() if not t.alive and t.team != p.team
                  and (t.pos - p.pos).length() <= reach and (t.pos - cursor).length() <= 1.0
                  and m._line_clear(p.pos, t.pos, p.level, ignore_effects=True)]
    return min(candidates, key=lambda pos: (pos - cursor).length(), default=None)


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
    best, best_d = None, float(spec.get("cursor_radius", ctx.ability.get("cursor_radius", 2.0)))
    for t in ctx.m.players.values():
        if t.team != p.team or t.pid == p.pid or t.alive == dead or (t.pos - p.pos).length() > reach:
            continue
        if spec.get("injured", ctx.ability.get("injured")) and t.hp + t.decay_pool >= ctx.m._hp:
            continue
        if dead and any(e.props.get("revive_pid") == t.pid and not e.props.get("ended") for e in ctx.m.effects):
            continue
        if ctx.m._deck_between(p, t):
            continue
        if spec.get("require_sight") and not ctx.m._line_clear(p.pos, t.pos, p.level):
            continue
        d = (t.pos - aim_point).length()
        if d < best_d:
            best, best_d = t, d
    return best


@target("aim_ally")
def t_aim_ally(m: Match, p: PlayerState, spec: dict[str, Any]) -> Vec | None:
    ally = _under_cursor(Ctx(m, p, p.team, p.pos, p.pos, heading(p.facing)), spec, dead=False)
    return ally.pos if ally is not None else None


@target("aim_fallen")
def t_aim_fallen(m: Match, p: PlayerState, spec: dict[str, Any]) -> Vec | None:
    ally = _under_cursor(Ctx(m, p, p.team, p.pos, p.pos, heading(p.facing)), spec, dead=True)
    return ally.pos if ally is not None else None


@who("cursor_ally")
def w_cursor_ally(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState]:
    """The teammate under the cursor within `range`, else the owner."""
    t = _under_cursor(ctx, spec, dead=False)
    return [t] if t is not None else [] if spec.get("required") else w_self(ctx, spec)


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
    if area == "sweep" and obj is not None:
        return _seg_distance(t.pos, obj.data.get("previous_pos", ctx.point), ctx.point) <= radius
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
    if spec.get("injured") and t.hp + t.decay_pool >= ctx.m._hp:
        return False
    sight = spec.get("sight")  # None, "walls" (walls block) or "all" (smokes block too)
    origin = ctx.source if spec.get("area") == "beam" else ctx.point
    aim_cone = ctx.ability.get("aim_cone")
    if aim_cone is not None and abs(angle_diff(angle_of(ctx.aim), angle_of(t.pos - origin))) > float(aim_cone) / 2:
        return False
    if sight and not ctx.m._line_clear(origin, t.pos, t.level, ignore_effects=sight == "walls"):
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
def damage_map_cover(ctx: Ctx, spec: dict[str, Any]) -> None:
    """Apply opted-in ability damage once per map object, independently of player hits."""
    m, obj = ctx.m, ctx.obj
    if not m.cover_health:
        return
    level = obj.props.get("source_level", 0) if obj is not None else (ctx.owner.level if ctx.owner else 0)
    radius = float(spec.get("radius", obj.radius if obj is not None else 0.0))
    area = spec.get("area") or "circle"
    continuous = spec["do"] == "dps"
    amount = float(spec["per_second"]) * ctx.dt if continuous else float(spec["amount"])
    for wall in m.world.walls:
        if wall.hp <= 0 or not m.wall_active(wall):
            continue
        r = wall.rect
        if area == "beam" or (area == "line" and obj is not None and obj.a is not None and obj.b is not None):
            start, end = (obj.a, obj.b) if area == "line" else (
                ctx.source, ctx.source + ctx.aim * float(spec.get("length", ctx.ability.get("length", 10.0)))
            )
            half = float(spec.get("width", ctx.ability.get("width", 0.0))) / 2
            if area == "line":
                half += BODY
            delta = end - start
            interval = Rect(r.x0 - half, r.y0 - half, r.x1 + half, r.y1 + half).ray_interval(start, delta)
            if interval is None or interval[0] > 1:
                continue
            origin = start + delta * interval[0] if area == "line" else start
        elif area == "circle" and radius > 0:
            origin = ctx.point
        else:
            continue
        point = Vec(max(r.x0, min(r.x1, origin.x)), max(r.y0, min(r.y1, origin.y)))
        distance = (point - origin).length()
        if area == "circle" and distance > radius:
            continue
        cover_level = m.world.floor_level(r.center)
        if m.world.deck_blocks(origin, level + 1.0, point, cover_level + 1.0):
            continue
        if not spec.get("cover_through_walls") and not m._line_clear(
            origin, point, min(level, cover_level), ignore_effects=True, ignore_wall=wall
        ):
            continue
        scale = 1.0 - float(spec.get("falloff", 0.0)) * distance / radius if area == "circle" else 1.0
        damage = amount * float(spec["cover_mult"]) * scale
        if continuous and obj is not None:
            pending = obj.data.setdefault("cover_dps", {})
            damage += pending.get(r, 0.0)
            pending[r] = damage - int(damage)
        if damage >= 1:
            m._damage_cover(wall, int(damage))


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


@effect("snapshot")
def e_snapshot(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """Leave a frozen location for the caster's team without revealing a moving enemy."""
    from gameplay.kit.engine import place
    if t is not None:
        place(ctx, {"look": "snapshot", "lasts": step["seconds"], "hidden": "enemies"}, t.pos)


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
    if step.get("delay"):
        from gameplay.kit.engine import place
        marker = place(ctx, {"look": "zone", "delay": step["delay"], "lasts": 0,
                             "warning_sprite": step.get("sprite"), "radius": BODY}, t.pos)
        marker.props["revive_pid"] = t.pid
        marker.data["revive_health"] = int(step.get("health", ctx.m._hp))
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
    if p is None or not p.alive:
        return False
    lh = float(ctx.m._mv["level_height"])
    ground = ctx.m.world.ground_height(ctx.point, p.level) * lh
    flat = (ctx.point - p.pos).length()
    rise = ground - (p.ground + p.z)
    reach = float(step.get("range", ctx.ability.get("range", 8.0)))
    if flat < 0.5 or (not ctx.ability.get("global_target") and (flat * flat + rise * rise) ** 0.5 > reach + 1e-6) \
            or not can_land(ctx.m, p, ctx.point):
        return False
    p.pos, p.vel = ctx.point, Vec(0, 0)
    p.ground, p.z, p.vz = ground, 0.0, 0.0
    p.level = int(ground / lh + 0.5)
    return True


def can_land(m: Match, p: PlayerState, point: Vec) -> bool:
    radius = float(m._mv["radius"])
    if not (radius <= point.x <= m.world.width - radius and radius <= point.y <= m.world.height - radius):
        return False
    level = m.world.floor_level(point, p.level)
    return ((point - p.pos).length() >= 0.5
            and not any(m.wall_active(w) and w.top > level and (not w.on_deck or w.base <= level)
                        and w.rect.circle_push(point, radius)
                        for w in m.combat_walls())
            and not any(t.pid != p.pid and t.alive and t.level == level
                        and (t.pos - point).length() < 2 * radius for t in m.players.values()))


@effect("channel_teleport", per_player=False)
def e_channel_teleport(ctx: Ctx, t: PlayerState | None, spec: dict[str, Any]) -> bool:
    from gameplay.kit.engine import place
    if ctx.owner is None or not can_land(ctx.m, ctx.owner, ctx.point):
        return False
    delay = float(spec["seconds"])
    ctx.owner.channel_until = ctx.m.time + delay
    ctx.owner.vel = Vec(0, 0)
    shade = {"hp": 1, "hit_radius": float(ctx.m._mv["radius"]), "cancel_channel": True} if spec.get("cancel_channel") else {}
    place(ctx, {"look": "zone", "lasts": delay, "radius": 0.8, **shade,
                "sprite": spec["sprite"], "triggers": [{"when": "expire", "do": [{"do": "teleport"}]}]}, ctx.point)
    return True


def barrier_rects(m: Match, p: PlayerState, point: Vec, spec: dict[str, Any]) -> list[Rect]:
    count, length, width = int(spec["blocks"]), float(spec["length"]), float(spec["width"])
    along = heading(round(p.facing / 90) * 90).rotated(90)
    if spec.get("along"):
        along = along.rotated(90)
    size = length / count
    horizontal = abs(along.x) > abs(along.y)
    dx, dy = (size / 2, width / 2) if horizontal else (width / 2, size / 2)
    solid = [w.rect for w in m.combat_walls() if w.top > p.level and m.wall_active(w)]
    result = []
    for i in range(count):
        center = point + along * (size * (i - (count - 1) / 2))
        rect = Rect(center.x - dx, center.y - dy, center.x + dx, center.y + dy)
        if not (0 <= rect.x0 < rect.x1 <= m.world.width and 0 <= rect.y0 < rect.y1 <= m.world.height):
            continue
        if any(rect.x0 < w.x1 and rect.x1 > w.x0 and rect.y0 < w.y1 and rect.y1 > w.y0 for w in solid):
            continue
        if any(t.alive and rect.circle_push(t.pos, float(m._mv["radius"])) for t in m.players.values()):
            continue
        result.append(rect)
    return result


@effect("barrier", per_player=False)
def e_barrier(ctx: Ctx, t: PlayerState | None, spec: dict[str, Any]) -> bool:
    from gameplay.kit.engine import place
    from gameplay.world import Wall
    if ctx.owner is None:
        return False
    rects = barrier_rects(ctx.m, ctx.owner, ctx.point, spec)
    for rect in rects:
        block = place(ctx, {"look": "wall", "lasts": spec["duration"], "sprite": spec["sprite"]}, rect.center)
        block.props["barrier"] = Wall(rect, 3, hp=int(spec["hp"]))
        block.data["hp"] = int(spec["hp"])
        if "fortify_after" in spec:
            block.data["fortify_at"] = ctx.m.time + float(spec["fortify_after"])
            block.data["fortify_hp"] = int(spec["fortified_hp"]) - int(spec["hp"])
    return bool(rects)


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


@effect("sound", per_player=False)
def e_sound(ctx: Ctx, t: PlayerState | None, step: dict[str, Any]) -> None:
    """key, radius: plays assets/sounds/<key>.wav at the point (heard like any other sound, not a footstep)."""
    game_event(ctx.m, "sound_fx", {"key": str(step["key"]), "pos": (ctx.point.x, ctx.point.y),
                                   "radius": float(step.get("radius", 30.0))})


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
    if "offset" in spec and ctx.obj is not None:
        tag = f"pulse:{id(spec)}"
        pulse = ctx.obj.data.get(tag, 0)
        if pulse >= spec.get("count", float("inf")) or now < ctx.obj.start + float(spec["offset"]) + pulse * period:
            return None
        ctx.obj.data[tag] = pulse + 1
        return select(ctx, spec)
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


@trigger("tripwire_chain")
def tr_tripwire_chain(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState] | None:
    obj = ctx.obj
    assert obj is not None and obj.a is not None and obj.b is not None
    now = ctx.m.time
    victim = ctx.m.players.get(obj.data.get("chained"))
    if victim is not None:
        out_of_range = _seg_distance(victim.pos, obj.a, obj.b) > float(spec["break_distance"])
        if victim.alive and now < obj.data["zap_at"] and not out_of_range:
            return None
        obj.data.pop("chained", None)
        obj.data["rearm_at"] = now + float(spec["rearm"])
        return [victim] if victim.alive else None
    if now < obj.data.get("rearm_at", 0):
        return None
    targets = tr_cross(ctx, spec)
    if targets:
        victim = targets[0]
        windup = float(spec["windup"])
        statuses.apply_status(ctx.m, victim, "tripwire_slow", windup)
        obj.data["chained"], obj.data["zap_at"] = victim.pid, now + windup
    return None


@trigger("chase")
def tr_chase(ctx: Ctx, spec: dict[str, Any]) -> list[PlayerState] | None:
    obj = ctx.obj
    assert obj is not None
    victim = ctx.m.players.get(obj.data.get("chase_pid"))
    if victim is None or not victim.alive:
        targets = select(ctx, spec)
        if not targets:
            return None
        victim = targets[0]
        obj.data["chase_pid"] = victim.pid
    delta = victim.pos - obj.pos
    distance = delta.length()
    step = min(distance, ctx.dt * float(spec["speed"]))
    if step > 0:
        obj.pos = ctx.point = ctx.m._clip_to_walls(obj.pos, obj.pos + delta.normalized() * step,
                                                   int(obj.props["source_level"]))
    if (victim.pos - obj.pos).length() <= 2 * BODY and ctx.m._line_clear(obj.pos, victim.pos, victim.level):
        return select(ctx, {**spec, "radius": spec["blast_radius"], "first": False})
    return None


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
