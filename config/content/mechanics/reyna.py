"""Reyna's soul orbs, Devour and Dismiss."""
from dataclasses import replace

from gameplay.geometry import heading
from gameplay.kit import statuses
from gameplay.kit.engine import place
from gameplay.kit.registry import effect, passive_trigger, target


def _available_orb(match, player):
    return next((orb for orb in match.effects if orb.owner == player.pid and orb.props.get("soul_orb")
                 and not orb.props.get("ended") and orb.start > player.died_at and match.time < orb.until
                 and match._line_clear(player.pos, orb.pos, player.level, ignore_effects=True)), None)


@target("leer_eye")
def leer_eye(match, player, spec):
    aim = heading(player.facing)
    walls = match.active_sight_walls(player.level)
    point = player.pos + aim * float(spec["range"])
    while (wall := next((wall for wall in walls if wall.rect.contains(point)), None)) is not None:
        interval = wall.rect.ray_interval(point, aim * -1)
        if interval is None:
            return None
        point -= aim * (interval[1] + 0.05)
        if (point - player.pos).dot(aim) <= 0:
            return None
    return point


@target("soul_orb")
def soul_orb(match, player, spec):
    if spec.get("devour") and statuses.has(match, player, "empress"):
        return None  # Empress automatically starts Devour when the orb appears.
    orb = _available_orb(match, player)
    return orb.pos if orb is not None else None


@passive_trigger("reyna_vitality")
def vitality(match, player, _spec, _dt):
    marks = player.passive_state.setdefault("soul_marks", {})
    victims = []
    for event in match.events:
        if event.kind not in ("hit", "kill"):
            continue
        victim = match.players.get(event.data["pid"])
        if victim is None or victim.team == player.team:
            continue
        if event.kind == "hit" and event.data.get("by") == player.pid:
            marks[victim.pid] = match.time + 3
        if event.kind == "kill":
            marked = marks.pop(victim.pid, 0) > match.time
            if marked or event.data.get("by") == player.pid:
                victims.append(victim)
    return victims


@effect("create_soul_orb", per_player=False)
def create_orb(ctx, _target, _step):
    if ctx.owner is None or ctx.other is None:
        return
    empowered = statuses.has(ctx.m, ctx.owner, "empress")
    if not (empowered or ctx.owner.charges.get("E", 0) or ctx.m.cheat("infinite_abilities")):
        return
    orb = place(ctx, {"look": "zone", "radius": 0.32, "lasts": 3, "sprite": "ability/reyna_soul"}, ctx.other.pos)
    orb.props.update(soul_orb=True, owner_only=True)
    if empowered and not statuses.flag(ctx.m, ctx.owner, "no_abilities"):
        _tether(replace(ctx, point=orb.pos), empowered=True)


def _tether(ctx, empowered):
    duration = 2.5 if empowered else 3.0
    tether = place(ctx, {"look": "none", "lasts": duration + 0.15,
                         "triggers": [{"when": "tick", "do": [{"do": "devour_heal"}]}]}, ctx.point)
    tether.props.update(devour_tether=not empowered, empowered=empowered, heal_rate=50 / duration, owner_only=True)
    tether.data["remaining"] = 50.0


@effect("devour_soul", per_player=False)
def devour_soul(ctx, _target, _step):
    orb = _available_orb(ctx.m, ctx.owner) if ctx.owner is not None else None
    if orb is None:
        return False
    orb.props["ended"] = True
    _tether(replace(ctx, point=orb.pos), empowered=False)


@effect("devour_heal", per_player=False)
def devour_heal(ctx, _target, _step):
    owner, tether, match = ctx.owner, ctx.obj, ctx.m
    if owner is None or tether is None:
        return
    if not owner.alive or tether.start <= owner.died_at:
        tether.props["ended"] = True
        return
    empowered = tether.props["empowered"]
    lost_overheal = any(e.kind == "hit" and e.data["pid"] == owner.pid and e.data.get("overheal")
                        for e in match.events)
    if not empowered and (lost_overheal or not match._line_clear(owner.pos, ctx.point, owner.level, ignore_effects=True)):
        tether.props["ended"] = True
        return
    amount = min(tether.data["remaining"], tether.props["heal_rate"] * ctx.dt)
    tether.data["remaining"] -= amount
    amount += tether.data.get("fraction", 0.0)
    whole = int(amount + 1e-8)
    tether.data["fraction"] = amount - whole
    restored = min(whole, match._hp - owner.hp)
    owner.hp += restored
    added = min(whole - restored, max(0, 50 - owner.armor - owner.overheal))
    if added:
        owner.overheal += added
        owner.overheal_until = float("inf") if empowered else match.time + 10
    if tether.data["remaining"] <= 1e-8:
        tether.props["ended"] = True


@effect("dismiss_soul", per_player=False)
def dismiss_soul(ctx, _target, _step):
    owner = ctx.owner
    orb = _available_orb(ctx.m, owner) if owner is not None else None
    if orb is None:
        return False
    orb.props["ended"] = True
    statuses.apply_status(ctx.m, owner, "dismiss", 1.5)
    if statuses.has(ctx.m, owner, "empress"):
        statuses.apply_status(ctx.m, owner, "dismiss_invisible", 1.5)
        owner.passive_state["invisible_dismiss_started"] = ctx.m.time
    owner.reload_until = owner.burst_left = 0
    owner.equip_until = ctx.m.time + 2.1


@passive_trigger("reyna_reappeared")
def reappeared(match, player, _spec, _dt):
    if statuses.has(match, player, "dismiss_invisible"):
        return []
    started = player.passive_state.pop("invisible_dismiss_started", None)
    return [player] if started is not None and started > player.died_at else []


@effect("empress", per_player=False)
def empress(ctx, _target, _step):
    if ctx.owner is not None:
        if ctx.owner.overheal:
            ctx.owner.overheal_until = float("inf")
        statuses.apply_status(ctx.m, ctx.owner, "empress", float("inf"))
