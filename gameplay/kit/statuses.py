"""Statuses as data (config/content/statuses.py): each status is a set of modifiers, read by the game through
mult(), add(), lowest() and flag(). A new status needs no code, only an entry in config/content/statuses.py.

Modifiers (all optional):
  speed, damage_taken, damage_dealt, fire_rate, reload    factors, multiplied over all active statuses
  spread_add, hp_per_second                               added up (negative hp_per_second drains health)
  sight_range, seen_within                                metres, the smallest active value counts
  blind, deaf, no_abilities, revealed, lethal             switches
  decay, decay_regen                                      health drained per second (never below 1), given back afterwards
  positive                                                a buff: immunity does not block it, cleanse keeps it
"""
from __future__ import annotations

import warnings
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from gameplay.data import ROOT, _load_py

if TYPE_CHECKING:
    from gameplay.match import Match, PlayerState

STATUS_PATH = ROOT / "config" / "content" / "statuses.py"
FALLBACK: dict[str, dict[str, Any]] = {
    "blind": {"blind": True}, "nearsight": {"sight_range": 5.0}, "concuss": {"speed": 0.6, "spread_add": 6.0},
    "slow": {"speed": 0.55}, "vulnerable": {"damage_taken": 1.5}, "decay": {"decay": 15.0, "decay_regen": 10.0},
    "suppress": {"no_abilities": True}, "detain": {"speed": 0.0}, "deaf": {"deaf": True},
    "stim": {"fire_rate": 1.12, "reload": 0.8, "positive": True},
}
MULTIPLY = ("speed", "damage_taken", "damage_dealt", "fire_rate", "reload")
ADD = ("spread_add", "hp_per_second")
LOWEST = ("sight_range", "seen_within")
FLAGS = ("blind", "deaf", "no_abilities", "revealed", "lethal", "positive")
KNOWN = set(MULTIPLY) | set(ADD) | set(LOWEST) | set(FLAGS) | {"decay", "decay_regen", "icon", "note"}


@lru_cache(maxsize=1)
def load_statuses() -> dict[str, dict[str, Any]]:
    raw = _load_py(STATUS_PATH, "STATUSES")
    if not isinstance(raw, dict) or not raw:
        warnings.warn("config/content/statuses.py has no STATUSES; built-in statuses apply.")
        return dict(FALLBACK)
    out: dict[str, dict[str, Any]] = {}
    for name, mods in raw.items():
        if not isinstance(mods, dict):
            warnings.warn(f"Status {name} skipped: not a dict")
            continue
        unknown = set(mods) - KNOWN
        if unknown:
            warnings.warn(f"Status {name}: unknown modifiers {sorted(unknown)} ignored")
        out[str(name)] = dict(mods)
    return out


def defs(m: Match) -> dict[str, dict[str, Any]]:
    return getattr(m, "statuses", None) or load_statuses()


def has(m: Match, p: PlayerState, status: str) -> bool:
    return p.status.get(status, 0.0) > m.time


def active(m: Match, p: PlayerState) -> list[dict[str, Any]]:
    table = defs(m)
    return [table[name] for name, until in p.status.items() if until > m.time and name in table]


def apply_status(m: Match, p: PlayerState, status: str, seconds: float) -> None:
    table = defs(m)
    if status not in table:
        warnings.warn(f"Unknown status {status}")
        return
    if seconds <= 0 or not p.alive:
        return
    if p.immune_until > m.time and not table[status].get("positive"):
        return
    if table[status].get("blind"):
        p.blind_until = max(p.blind_until, m.time + seconds)
    p.status[status] = max(p.status.get(status, 0.0), m.time + seconds)


def clear_statuses(p: PlayerState, m: Match | None = None, keep_positive: bool = True) -> None:
    table = defs(m) if m is not None else load_statuses()
    p.status = {k: v for k, v in p.status.items() if keep_positive and table.get(k, {}).get("positive")}
    p.blind_until = 0.0


def mult(m: Match, p: PlayerState, key: str) -> float:
    f = 1.0
    for mods in active(m, p):
        if key in mods:
            f *= float(mods[key])
    return f


def add(m: Match, p: PlayerState, key: str) -> float:
    return sum(float(mods[key]) for mods in active(m, p) if key in mods)


def lowest(m: Match, p: PlayerState, key: str) -> float | None:
    values = [float(mods[key]) for mods in active(m, p) if key in mods]
    return min(values) if values else None


def flag(m: Match, p: PlayerState, key: str) -> bool:
    return any(mods.get(key) for mods in active(m, p))


def speed_factor(m: Match, p: PlayerState) -> float:
    return max(0.0, mult(m, p, "speed"))


def _heal_whole(m: Match, p: PlayerState, amount: float) -> None:
    p.hp_frac += amount
    whole = int(p.hp_frac)
    p.hp_frac -= whole
    p.hp = min(m._hp, p.hp + whole)


def tick_player(m: Match, p: PlayerState, dt: float) -> None:
    """Healing over time, decay, health per second and reveal from statuses."""
    if not p.alive:
        return
    if p.heal_left > 0:
        amount = min(p.heal_left, p.heal_rate * dt)
        p.heal_left -= amount
        _heal_whole(m, p, amount)
    decay = [mods for mods in active(m, p) if mods.get("decay")]
    if decay:
        drain = max(float(d["decay"]) for d in decay) * dt
        before = p.hp + p.hp_frac
        after = max(1.0, before - drain)
        p.decay_pool += before - after
        p.hp, p.hp_frac = int(after), after - int(after)
    elif p.decay_pool > 0:
        regen = max((float(d.get("decay_regen", 10.0)) for d in defs(m).values() if d.get("decay")), default=10.0)
        back = min(p.decay_pool, regen * dt)
        p.decay_pool -= back
        _heal_whole(m, p, back)
    per_second = add(m, p, "hp_per_second")
    if per_second > 0:
        _heal_whole(m, p, per_second * dt)
    elif per_second < 0:
        p.status_drain = getattr(p, "status_drain", 0.0) - per_second * dt
        whole = int(p.status_drain)
        if whole:
            p.status_drain -= whole
            if flag(m, p, "lethal"):
                m._damage(None, p, whole, "body", "status")
            else:
                p.hp = max(1, p.hp - whole)
    if flag(m, p, "revealed"):
        p.revealed_until = max(p.revealed_until, m.time + 0.1)
