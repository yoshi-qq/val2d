"""Ability building blocks and statuses (values in config/agents.py).

use(): carries out one ability. tick(): runs placed effects, statuses, decay and recharges.
All blocks are generic and data-driven; agents only combine them.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gameplay.geometry import Vec, angle_diff, angle_of, heading, segments_intersect

if TYPE_CHECKING:
    from gameplay.match import Effect, Match, PlayerState

STATUSES = ("blind", "nearsight", "concuss", "slow", "vulnerable", "decay", "suppress", "detain", "deaf", "stim")
DEFAULT_RULES: dict[str, float] = dict(
    nearsight_range=5.0, concuss_spread=6.0, concuss_speed=0.6, slow_speed=0.55, vulnerable_mult=1.5,
    decay_per_second=15.0, decay_regen=10.0, stim_rate=1.12, stim_reload=0.8,
)


# ------------------------------------------------------------------ statuses
def has(m: Match, p: PlayerState, status: str) -> bool:
    return p.status.get(status, 0.0) > m.time


def apply_status(m: Match, p: PlayerState, status: str, seconds: float) -> None:
    if status not in STATUSES or seconds <= 0 or not p.alive:
        return
    if p.immune_until > m.time and status != "stim":
        return
    if status == "blind":
        p.blind_until = max(p.blind_until, m.time + seconds)
    p.status[status] = max(p.status.get(status, 0.0), m.time + seconds)


def clear_statuses(p: PlayerState) -> None:
    p.status = {k: v for k, v in p.status.items() if k == "stim"}
    p.blind_until = 0.0


def rule(m: Match, key: str) -> float:
    return float(m.status_rules.get(key, DEFAULT_RULES[key]))


def speed_factor(m: Match, p: PlayerState) -> float:
    if has(m, p, "detain"):
        return 0.0
    f = 1.0
    if has(m, p, "slow"):
        f *= rule(m, "slow_speed")
    if has(m, p, "concuss"):
        f *= rule(m, "concuss_speed")
    return f


# ------------------------------------------------------------------ use
def _target_point(m: Match, p: PlayerState, ab: dict[str, Any], clip: bool = True) -> Vec:
    aim = heading(p.facing)
    reach = min(p.cursor_depth, float(ab.get("range", p.cursor_depth)))
    point = p.pos + aim * reach
    return m._clip_to_walls(p.pos, point, p.level) if clip else point


def _ally_under_cursor(m: Match, p: PlayerState, reach: float, dead: bool = False) -> PlayerState | None:
    aim_point = p.pos + heading(p.facing) * min(p.cursor_depth, reach)
    best: PlayerState | None = None
    best_d = 2.0
    for t in m.players.values():
        if t.team != p.team or t.pid == p.pid or t.alive == dead:
            continue
        if (t.pos - p.pos).length() > reach:
            continue
        d = (t.pos - aim_point).length()
        if d < best_d:
            best, best_d = t, d
    return best


def use(m: Match, p: PlayerState, key: str, ab: dict[str, Any]) -> Vec | None:
    """Carries out ability `ab`. Returns the target point, or None if nothing happened (no charge used)."""
    from gameplay.match import Effect

    kind = str(ab.get("kind", ""))
    now = m.time
    aim = heading(p.facing)
    if kind == "smoke":
        pos = _target_point(m, p, ab, clip=not ab.get("remote", False))
        m.effects.append(Effect("smoke", p.pid, p.team, pos, now + float(ab["duration"]), radius=float(ab["radius"]), start=now))
        return pos
    if kind in ("wall", "vapor_wall"):
        pos = _target_point(m, p, ab)
        side = aim.rotated(90) * (float(ab["length"]) / 2)
        props = {"cross_status": ab.get("cross_status"), "cross_time": float(ab.get("cross_time", 0.0))}
        m.effects.append(Effect("wall", p.pid, p.team, pos, now + float(ab["duration"]), a=pos - side, b=pos + side, start=now,
                                props=props))
        return pos
    if kind == "flash":
        pos = _target_point(m, p, ab, clip=not ab.get("through_walls", False))
        m.effects.append(Effect("flash", p.pid, p.team, pos, now + float(ab["fuse"]),
                                data={"blind": float(ab["blind"]), "cone": float(ab["cone"])},
                                props={"through_walls": bool(ab.get("through_walls", False))}))
        return pos
    if kind in ("zone", "slow_field"):
        pos = _target_point(m, p, ab)
        status = ab.get("status") or ("slow" if kind == "slow_field" else None)
        props = {"status": status, "status_time": float(ab.get("status_time", 0.5)), "dps": float(ab.get("dps", 0.0)),
                 "reveal": bool(ab.get("reveal", kind == "slow_field")), "heal": float(ab.get("heal_allies", 0.0))}
        delay = float(ab.get("delay", 0.0))
        m.effects.append(Effect("zone", p.pid, p.team, pos, now + delay + float(ab["duration"]), radius=float(ab["radius"]),
                                start=now + delay, props=props))
        return pos
    if kind == "blast":
        pos = _target_point(m, p, ab)
        props = {"damage": float(ab.get("damage", 0.0)), "status": ab.get("status"), "status_time": float(ab.get("status_time", 0.0))}
        m.effects.append(Effect("blast", p.pid, p.team, pos, now + float(ab.get("delay", 0.0)), radius=float(ab["radius"]), props=props))
        return pos
    if kind == "wave":
        _wave(m, p, ab)
        return p.pos + aim * float(ab["length"])
    if kind == "sensor":
        pos = _target_point(m, p, ab) if "range" in ab else p.pos
        m.effects.append(Effect("sensor", p.pid, p.team, pos, now + float(ab["duration"]), radius=float(ab["radius"]),
                                data={"pulse": float(ab["pulse"])}))
        return pos
    if kind == "alarm":
        pos = _target_point(m, p, ab)
        props = {"status": ab.get("status", "concuss"), "status_time": float(ab.get("status_time", 2.0))}
        m.effects.append(Effect("alarm", p.pid, p.team, pos, now + float(ab["duration"]), radius=float(ab["radius"]), props=props))
        return pos
    if kind == "tripwire":
        pos = _target_point(m, p, {"range": 3.0})
        side = aim.rotated(90) * (float(ab["length"]) / 2)
        a, b = m._clip_to_walls(pos, pos - side, p.level), m._clip_to_walls(pos, pos + side, p.level)
        props = {"status": ab.get("status", "detain"), "status_time": float(ab.get("status_time", 2.0))}
        m.effects.append(Effect("tripwire", p.pid, p.team, pos, now + float(ab["duration"]), a=a, b=b, props=props))
        return pos
    if kind == "dash":
        move = p.vel.normalized() if p.vel.length() > 0.3 else aim
        p.dash_vel = move * (float(ab["distance"]) / float(ab["duration"]))
        p.dash_until = now + float(ab["duration"])
        return p.pos
    if kind == "hop":
        p.vz = float(ab["velocity"])
        return p.pos
    if kind == "teleport":
        goal = _target_point(m, p, ab)
        if (goal - p.pos).length() < 0.5 or m.world.floor_level(goal) > p.level:
            return None
        p.pos = goal
        p.vel = Vec(0, 0)
        return goal
    if kind == "anchor":
        if p.anchor is not None and p.anchor_until > now:
            target = p.anchor
            p.pos, p.vel, p.anchor = target, Vec(0, 0), None
            return target
        p.anchor, p.anchor_until = p.pos, now + float(ab.get("duration", 60.0))  # shown to the owner's team
        p.charges[key] = p.charges.get(key, 0) + 1  # setting is free; the charge is used on return
        return p.pos
    if kind == "heal":
        target = _ally_under_cursor(m, p, float(ab.get("range", 10.0))) or p
        target.heal_left += float(ab["amount"])
        target.heal_rate = float(ab["amount"]) / max(0.1, float(ab["duration"]))
        return target.pos
    if kind == "stim":
        for t in m.players.values():
            if t.alive and t.team == p.team and (t.pos - p.pos).length() <= float(ab["radius"]):
                apply_status(m, t, "stim", float(ab["duration"]))
        return p.pos
    if kind == "shield":
        target = _ally_under_cursor(m, p, float(ab.get("range", 10.0))) or p
        target.armor = max(target.armor, int(ab["points"]))
        return target.pos
    if kind == "revive":
        target = _ally_under_cursor(m, p, float(ab.get("range", 10.0)), dead=True)
        if target is None:
            return None
        target.alive, target.hp = True, m._hp
        clear_statuses(target)
        m.events.append(_event(m, "revive", {"pid": target.pid, "by": p.pid}))
        return target.pos
    if kind == "reveal_all":
        for t in m.players.values():
            if t.alive and t.team != p.team:
                t.revealed_until = max(t.revealed_until, now + float(ab["duration"]))
        return p.pos
    if kind == "overdrive":
        p.overdrive_until = now + float(ab["duration"])
        return p.pos
    if kind == "immunity":
        clear_statuses(p)
        p.immune_until = now + float(ab["duration"])
        p.heal_left += float(ab.get("regen", 5.0)) * float(ab["duration"])
        p.heal_rate = float(ab.get("regen", 5.0))
        apply_status(m, p, "stim", float(ab["duration"]))
        return p.pos
    if kind == "decoy":
        m.effects.append(Effect("decoy", p.pid, p.team, p.pos, now + float(ab["duration"]),
                                data={"vx": aim.x * float(ab.get("speed", 5.0)), "vy": aim.y * float(ab.get("speed", 5.0))}))
        return p.pos
    return None


def _event(m: Match, kind: str, data: dict[str, Any]) -> Any:
    from gameplay.match import GameEvent
    return GameEvent(kind, m.time, data)


def _wave(m: Match, p: PlayerState, ab: dict[str, Any]) -> None:
    aim = heading(p.facing)
    length, half = float(ab["length"]), float(ab.get("width", 1.0)) / 2
    for t in m.players.values():
        if not t.alive or t.team == p.team:
            continue
        rel = t.pos - p.pos
        along = rel.dot(aim)
        if 0 < along <= length and abs(aim.cross(rel)) <= half + 0.4:
            dmg = int(ab.get("damage", 0))
            if dmg:
                m._damage(p, t, dmg, "body", f"ability:{ab.get('name', 'wave')}")
            if ab.get("status"):
                apply_status(m, t, str(ab["status"]), float(ab.get("status_time", 1.0)))


# ------------------------------------------------------------------ tick
def tick(m: Match, dt: float) -> None:
    now = m.time
    keep: list[Effect] = []
    for e in m.effects:
        if e.kind == "flash":
            if now >= e.until:
                _pop_flash(m, e)
                continue
        elif e.kind == "blast":
            if now >= e.until:
                _detonate(m, e)
                continue
        elif now >= e.until:
            continue
        elif e.kind == "sensor" and int(now / e.data["pulse"]) != int((now - dt) / e.data["pulse"]):
            for t in m.players.values():
                if t.alive and t.team != e.team and (t.pos - e.pos).length() <= e.radius and m._line_clear(e.pos, t.pos, 0, ignore_effects=True):
                    t.revealed_until = now + 1.5
        elif e.kind == "zone" and now >= e.start:
            _zone(m, e, dt)
        elif e.kind == "alarm":
            if _alarm(m, e):
                continue
        elif e.kind == "tripwire":
            if _tripwire(m, e):
                continue
        elif e.kind == "wall" and e.props.get("cross_status") and e.a and e.b:
            _wall_crossing(m, e, dt)
        elif e.kind == "decoy":
            step = Vec(e.data["vx"], e.data["vy"]) * dt
            e.pos = m._clip_to_walls(e.pos, e.pos + step, 0) if step.length() > 0 else e.pos
            if int(now * 3) != int((now - dt) * 3):
                m.events.append(_event(m, "sound", {"pid": e.owner, "pos": (e.pos.x, e.pos.y),
                                                    "radius": m._sound["run_radius"], "kind": "step", "decoy": True}))
        keep.append(e)
    m.effects = keep
    for p in m.players.values():
        _tick_player(m, p, dt)


def _pop_flash(m: Match, e: Effect) -> None:
    m.events.append(_event(m, "flash", {"pos": (e.pos.x, e.pos.y), "pid": e.owner}))
    through = bool(e.props.get("through_walls"))
    for t in m.players.values():
        if not t.alive:
            continue
        if not through and not m._line_clear(t.pos, e.pos, t.level, ignore_effects=False):
            continue
        if abs(angle_diff(t.facing, angle_of(e.pos - t.pos))) <= e.data["cone"] / 2:
            apply_status(m, t, "blind", e.data["blind"])


def _detonate(m: Match, e: Effect) -> None:
    owner = m.players.get(e.owner)
    for t in m.players.values():
        if not t.alive or (t.pos - e.pos).length() > e.radius:
            continue
        if not m._line_clear(e.pos, t.pos, 0, ignore_effects=True):
            continue
        if t.team != e.team or t.pid == e.owner:
            dmg = float(e.props.get("damage", 0.0))
            if dmg and t.team != e.team:
                falloff = 1.0 - 0.5 * (t.pos - e.pos).length() / max(e.radius, 0.1)
                m._damage(owner, t, int(dmg * falloff), "body", "ability")
            if e.props.get("status") and t.team != e.team:
                apply_status(m, t, str(e.props["status"]), float(e.props.get("status_time", 1.0)))
    m.events.append(_event(m, "blast", {"pos": (e.pos.x, e.pos.y), "radius": e.radius, "pid": e.owner}))


def _zone(m: Match, e: Effect, dt: float) -> None:
    owner = m.players.get(e.owner)
    for t in m.players.values():
        if not t.alive or (t.pos - e.pos).length() > e.radius:
            continue
        if t.team == e.team:
            heal = float(e.props.get("heal", 0.0))
            if heal:
                t.hp = min(m._hp, t.hp + heal * dt)
            continue
        if e.props.get("status"):
            apply_status(m, t, str(e.props["status"]), float(e.props.get("status_time", 0.5)))
        if e.props.get("reveal"):
            t.revealed_until = max(t.revealed_until, m.time + 0.25)
        dps = float(e.props.get("dps", 0.0))
        if dps:
            e.data["acc"] = e.data.get("acc", 0.0) + dps * dt
            if e.data["acc"] >= 1.0:
                whole = int(e.data["acc"])
                e.data["acc"] -= whole
                m._damage(owner, t, whole, "body", "ability")


def _alarm(m: Match, e: Effect) -> bool:
    """True if the alarm went off (it is used up)."""
    for ev in m.events:
        if ev.kind != "sound":
            continue
        t = m.players.get(ev.data.get("pid"))
        if t is None or not t.alive or t.team == e.team:
            continue
        if (t.pos - e.pos).length() <= e.radius:
            apply_status(m, t, str(e.props["status"]), float(e.props["status_time"]))
            t.revealed_until = max(t.revealed_until, m.time + 1.5)
            return True
    return False


def _tripwire(m: Match, e: Effect) -> bool:
    assert e.a is not None and e.b is not None
    for t in m.players.values():
        if not t.alive or t.team == e.team:
            continue
        last = t.last_pos if t.last_pos is not None else t.pos
        if segments_intersect(last, t.pos, e.a, e.b):
            apply_status(m, t, str(e.props["status"]), float(e.props["status_time"]))
            t.revealed_until = max(t.revealed_until, m.time + 3.0)
            return True
    return False


def _wall_crossing(m: Match, e: Effect, dt: float) -> None:
    assert e.a is not None and e.b is not None
    for t in m.players.values():
        if not t.alive or t.team == e.team:
            continue
        last = t.last_pos if t.last_pos is not None else t.pos
        if segments_intersect(last, t.pos, e.a, e.b):
            apply_status(m, t, str(e.props["cross_status"]), float(e.props.get("cross_time", 1.0)))


def _tick_player(m: Match, p: PlayerState, dt: float) -> None:
    if not p.alive:
        return
    if p.heal_left > 0:
        amount = min(p.heal_left, p.heal_rate * dt)
        p.heal_left -= amount
        p.hp_frac += amount
        whole = int(p.hp_frac)
        p.hp_frac -= whole
        p.hp = min(m._hp, p.hp + whole)
    if has(m, p, "decay"):
        drain = rule(m, "decay_per_second") * dt
        before = p.hp + p.hp_frac
        after = max(1.0, before - drain)
        p.decay_pool += before - after
        p.hp, p.hp_frac = int(after), after - int(after)
    elif p.decay_pool > 0:
        back = min(p.decay_pool, rule(m, "decay_regen") * dt)
        p.decay_pool -= back
        p.hp_frac += back
        whole = int(p.hp_frac)
        p.hp_frac -= whole
        p.hp = min(m._hp, p.hp + whole)
    ab_all = m.agents.get(p.agent, {}).get("abilities", {})
    if m.phase in ("live", "planted"):
        for key, ab in ab_all.items():
            if key == "X" or "recharge" not in ab:
                continue
            if p.charges.get(key, 0) >= int(ab["max"]):
                p.recharge_timers[key] = 0.0
                continue
            p.recharge_timers[key] = p.recharge_timers.get(key, 0.0) + dt
            if p.recharge_timers[key] >= float(ab["recharge"]):
                p.recharge_timers[key] = 0.0
                p.charges[key] = p.charges.get(key, 0) + 1
    p.last_pos = p.pos
