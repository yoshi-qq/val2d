"""Short helpers for writing agents and abilities in config/content/agents/*.py.

    from gameplay.kit.dsl import *

    AGENT = agent("Ember", role="Duelist",
        C=ability("Firebomb", price=200, max=1, target="aim", range=14, preview="zone", bot="offense",
                  place=thing("blast", lasts=1.0, radius=3, thrown=True, triggers=[
                      on("expire", who="enemies", do=[damage(40, falloff=0.5), event("blast"),
                          spawn(thing("zone", lasts=4, radius=3, triggers=[on("tick", do=[dps(20)])]))]),
                  ])),
        Q=preset("hop", "Leap", price=150, max=2, velocity=6.5),
        E=preset("dash", "Glide", max=1, start=1, distance=7, duration=0.2, kills_to_recharge=2),
        X=preset("overdrive", "Overdrive", cost=7, duration=8, rate_mult=1.15),
        passives=[on("kill", do=[heal(20)])],
    )

Every helper returns a plain dict, so dicts written by hand work the same.
"""
from __future__ import annotations

from typing import Any

__all__ = ["agent", "preset", "ability", "library", "thing", "on", "step", "sound",
           "damage", "dps", "status", "heal", "heal_rate", "shield", "reveal", "cleanse", "immunity", "revive",
           "push", "pull", "knock_up", "dash", "hop", "teleport", "anchor", "overdrive", "charge", "ult_points",
           "credits", "spawn", "noise", "event", "end"]


def agent(name: str, role: str = "", order: int = 999, sprites: dict[str, Any] | None = None,
          passives: list[dict[str, Any]] | None = None, **slots: dict[str, Any]) -> dict[str, Any]:
    """An agent: name, role, abilities C, Q, E, X; optional sprite mechanics and passives (triggers on the agent)."""
    missing = [s for s in ("C", "Q", "E", "X") if s not in slots]
    if missing:
        raise ValueError(f"agent {name}: slots {missing} missing")
    return {"name": name, "role": role, "order": order, "abilities": {s: slots[s] for s in ("C", "Q", "E", "X")},
            "sprites": dict(sprites or {}), "passives": list(passives or [])}


# right-click variants the presets get unless an ability sets its own `alt` (or alt=None for none)
PRESET_ALT = {
    "flash": lambda v: {"range": round(float(v["range"]) * 0.4, 2), "fuse": round(float(v["fuse"]) * 0.6, 2), "throw": "underhand"},
    "blast": lambda v: {"range": round(float(v["range"]) * 0.5, 2), "throw": "lob"},
    "wall": lambda v: {"along": True},
    "vapor_wall": lambda v: {"along": True},
}


def preset(kind: str, name: str, **values: Any) -> dict[str, Any]:
    """A classic building block (smoke, wall, flash, zone, blast, wave, ...) with its values.
    alt={...}: values for the right-click cast (defaults: underhand flash, lobbed charge, wall along the aim)."""
    out = {"name": name, "kind": kind, **_slot_defaults(values), **values}
    if "alt" not in values and kind in PRESET_ALT:
        try:
            out["alt"] = PRESET_ALT[kind](values)
        except (KeyError, TypeError, ValueError):
            pass
    if out.get("alt") is None:
        out.pop("alt", None)
    return out


def ability(name: str, target: str = "aim", do: list[dict[str, Any]] | None = None, place: dict[str, Any] | None = None,
            preview: str = "", bot: str = "", **values: Any) -> dict[str, Any]:
    """A composed ability. preview: how the aim preview looks (a preset name such as zone, wall, wave, teleport;
    empty = none). bot: "offense", "buff", "place" or "heal", so bots know when to use it."""
    out = {"name": name, "kind": "custom", "target": target, "do": list(do or []), "preview": preview, "bot": bot,
           **_slot_defaults(values), **values}
    if place is not None:
        out["place"] = place
    return out


def _slot_defaults(values: dict[str, Any]) -> dict[str, Any]:
    if "cost" in values:  # ultimate
        return {}
    return {"price": 0, "max": 1, "start": 0}


def library(name: str, **overrides: Any) -> dict[str, Any]:
    """An ability from config/content/abilities (ready-made), with values changed: library("firebomb", price=300)."""
    from gameplay.kit.library import get
    return {**get(name), **overrides}


def thing(look: str, lasts: float = 10.0, triggers: list[dict[str, Any]] | None = None, **values: Any) -> dict[str, Any]:
    """An object left in the world. look: smoke, wall, flash, zone, blast, sensor, alarm, tripwire, decoy, none.
    Values: delay, radius, shape="line", length, thrown, clip_ends, blocks_sight, hidden ("enemies"/"all"), move (m/s)."""
    return {"look": look, "lasts": lasts, "triggers": list(triggers or []), **values}


def on(when: str, do: list[dict[str, Any]], **values: Any) -> dict[str, Any]:
    """A trigger: when (start, expire, tick, every, enter, leave, cross, noise, gunfire; for passives: kill, death,
    damage_dealt, damage_taken, ability_used, every, low_health) and the steps it runs.
    Values choose the players: who, area, radius, sight, facing, first; consume=True ends the object."""
    return {"when": when, "do": list(do), **values}


def step(effect: str, **values: Any) -> dict[str, Any]:
    """Any effect by name, also ones registered in config/content/mechanics/."""
    return {"do": effect, **values}


def damage(amount: float, falloff: float = 0.0, **values: Any) -> dict[str, Any]:
    return step("damage", amount=amount, falloff=falloff, **values)


def dps(per_second: float, **values: Any) -> dict[str, Any]:
    return step("dps", per_second=per_second, **values)


def status(name: str, seconds: float, **values: Any) -> dict[str, Any]:
    return step("status", name=name, seconds=seconds, **values)


def heal(amount: float, over: float = 0.0, **values: Any) -> dict[str, Any]:
    return step("heal", amount=amount, over=over, **values)


def heal_rate(per_second: float, **values: Any) -> dict[str, Any]:
    return step("heal_rate", per_second=per_second, **values)


def shield(points: int, **values: Any) -> dict[str, Any]:
    return step("shield", points=points, **values)


def reveal(seconds: float, **values: Any) -> dict[str, Any]:
    return step("reveal", seconds=seconds, **values)


def cleanse(**values: Any) -> dict[str, Any]:
    return step("cleanse", **values)


def immunity(seconds: float, **values: Any) -> dict[str, Any]:
    return step("immunity", seconds=seconds, **values)


def revive(health: int = 100, **values: Any) -> dict[str, Any]:
    return step("revive", health=health, required=True, **values)


def push(strength: float, **values: Any) -> dict[str, Any]:
    return step("push", strength=strength, **values)


def pull(strength: float, **values: Any) -> dict[str, Any]:
    return step("pull", strength=strength, **values)


def knock_up(velocity: float, **values: Any) -> dict[str, Any]:
    return step("knock_up", velocity=velocity, **values)


def dash(distance: float, duration: float) -> dict[str, Any]:
    return step("dash", distance=distance, duration=duration)


def hop(velocity: float) -> dict[str, Any]:
    return step("hop", velocity=velocity)


def teleport() -> dict[str, Any]:
    return step("teleport")


def anchor(seconds: float = 60.0) -> dict[str, Any]:
    return step("anchor", seconds=seconds)


def overdrive(seconds: float) -> dict[str, Any]:
    return step("overdrive", seconds=seconds)


def charge(slot: str, amount: int = 1) -> dict[str, Any]:
    return step("charge", slot=slot, amount=amount)


def ult_points(amount: int = 1) -> dict[str, Any]:
    return step("ult_points", amount=amount)


def credits(amount: int) -> dict[str, Any]:
    return step("credits", amount=amount)


def spawn(place: dict[str, Any]) -> dict[str, Any]:
    return step("spawn", place=place)


def sound(key: str, radius: float = 30.0) -> dict[str, Any]:
    """Plays a sound file (assets/sounds/<key>.wav) at the point for everyone in `radius` metres."""
    return step("sound", key=key, radius=radius)


def noise(**values: Any) -> dict[str, Any]:
    return step("noise", **values)


def event(kind: str, **values: Any) -> dict[str, Any]:
    return step("event", kind=kind, **values)


def end() -> dict[str, Any]:
    return step("end")
