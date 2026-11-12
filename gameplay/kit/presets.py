"""Presets: the 21 classic building blocks written as compositions of the kit.

An ability with kind="smoke" (and its values) is expanded by the preset of that name. To build something
the presets cannot, write the composition yourself (see docs/MODDING.md); a preset is a good template.
"""
from __future__ import annotations

from typing import Any

from gameplay.kit.registry import preset


def _steps_status(ab: dict[str, Any], key: str = "status", time_key: str = "status_time", default_time: float = 1.0) -> list[dict[str, Any]]:
    return [{"do": "status", "name": ab[key], "seconds": float(ab.get(time_key, default_time))}] if ab.get(key) else []


@preset("smoke")
def smoke(ab: dict[str, Any]) -> dict[str, Any]:
    return {"target": "aim_free" if ab.get("remote") else "aim",
            "place": {"look": "smoke", "lasts": ab["duration"], "radius": ab["radius"]}}


@preset("wall")
def wall(ab: dict[str, Any]) -> dict[str, Any]:
    triggers = []
    if ab.get("cross_status"):
        triggers.append({"when": "cross", "who": "enemies",
                         "do": _steps_status(ab, "cross_status", "cross_time")})
    return {"target": "aim", "place": {"look": "wall", "shape": "line", "length": ab["length"], "lasts": ab["duration"],
                                       "along": bool(ab.get("along", False)), "triggers": triggers}}


preset("vapor_wall")(wall)


@preset("flash")
def flash(ab: dict[str, Any]) -> dict[str, Any]:
    through = bool(ab.get("through_walls", False))
    pop = {"when": "expire", "who": "everyone", "facing": ab["cone"], "sight": None if through else "all",
           "do": [{"do": "status", "name": "blind", "seconds": ab["blind"]}, {"do": "event", "kind": "flash"}]}
    return {"target": "throw" if ab.get("throw", True) else "aim_free" if through else "aim",
            "place": {"look": "flash", "thrown": True, "lasts": ab["fuse"], "triggers": [pop], "sprite": ab.get("sprite")}}


@preset("zone")
def zone(ab: dict[str, Any]) -> dict[str, Any]:
    slow_field = ab.get("kind") == "slow_field"
    status = ab.get("status") or ("slow" if slow_field else None)
    enemy_steps: list[dict[str, Any]] = []
    if status:
        enemy_steps.append({"do": "status", "name": status, "seconds": float(ab.get("status_time", 0.5))})
    if ab.get("reveal", slow_field):
        enemy_steps.append({"do": "reveal", "seconds": 0.25})
    if float(ab.get("dps", 0.0)):
        enemy_steps.append({"do": "dps", "per_second": float(ab["dps"])})
    triggers = [{"when": "tick", "who": "enemies", "do": enemy_steps}] if enemy_steps else []
    if float(ab.get("heal_allies", 0.0)):
        triggers.append({"when": "tick", "who": "team", "do": [{"do": "heal_rate", "per_second": float(ab["heal_allies"])}]})
    return {"target": "aim", "place": {"look": "zone", "delay": float(ab.get("delay", 0.0)), "lasts": ab["duration"],
                                       "radius": ab["radius"], "status_hint": status, "triggers": triggers}}


preset("slow_field")(zone)


@preset("blast")
def blast(ab: dict[str, Any]) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    if float(ab.get("damage", 0.0)):
        steps.append({"do": "damage", "amount": float(ab["damage"]), "falloff": 0.5})
    steps += _steps_status(ab)
    steps.append({"do": "event", "kind": "blast"})
    return {"target": "throw" if ab.get("throw", True) else "aim",
            "place": {"look": "blast", "thrown": True, "lasts": float(ab.get("delay", 0.0)),
                                       "radius": ab["radius"], "status_hint": ab.get("status"),
                                       "triggers": [{"when": "expire", "who": "enemies", "sight": "walls", "do": steps}]}}


@preset("wave")
def wave(ab: dict[str, Any]) -> dict[str, Any]:
    area = {"who": "enemies", "area": "beam", "length": ab["length"], "width": float(ab.get("width", 1.0))}
    steps = []
    if int(ab.get("damage", 0)):
        steps.append({"do": "damage", "amount": int(ab["damage"]), **area})
    steps += [{**s, **area} for s in _steps_status(ab)]
    return {"target": "ahead", "range": ab["length"], "do": steps}


@preset("sensor")
def sensor(ab: dict[str, Any]) -> dict[str, Any]:
    pulse = {"when": "every", "seconds": ab["pulse"], "who": "enemies", "sight": "walls",
             "do": [{"do": "reveal", "seconds": 1.5}]}
    return {"target": "aim" if "range" in ab else "self",
            "place": {"look": "sensor", "lasts": ab["duration"], "radius": ab["radius"], "triggers": [pulse]}}


@preset("alarm")
def alarm(ab: dict[str, Any]) -> dict[str, Any]:
    ring = {"when": "noise", "who": "enemies", "first": True, "consume": True,
            "do": [{"do": "status", "name": ab.get("status", "concuss"), "seconds": float(ab.get("status_time", 2.0))},
                   {"do": "reveal", "seconds": 1.5}]}
    return {"target": "aim", "place": {"look": "alarm", "lasts": ab["duration"], "radius": ab["radius"], "triggers": [ring]}}


@preset("tripwire")
def tripwire(ab: dict[str, Any]) -> dict[str, Any]:
    snap = {"when": "cross", "who": "enemies", "first": True, "consume": True,
            "do": [{"do": "status", "name": ab.get("status", "detain"), "seconds": float(ab.get("status_time", 2.0))},
                   {"do": "reveal", "seconds": 3.0}]}
    return {"target": "aim", "range": 3.0,
            "place": {"look": "tripwire", "shape": "line", "length": ab["length"], "clip_ends": True,
                      "lasts": ab["duration"], "triggers": [snap]}}


@preset("dash")
def dash(ab: dict[str, Any]) -> dict[str, Any]:
    return {"target": "self", "do": [{"do": "dash", "distance": ab["distance"], "duration": ab["duration"]}]}


@preset("hop")
def hop(ab: dict[str, Any]) -> dict[str, Any]:
    return {"target": "self", "do": [{"do": "hop", "velocity": ab["velocity"]}]}


@preset("teleport")
def teleport(ab: dict[str, Any]) -> dict[str, Any]:
    return {"target": "teleport_aim", "do": [{"do": "teleport"}]}


@preset("anchor")
def anchor(ab: dict[str, Any]) -> dict[str, Any]:
    return {"target": "self", "do": [{"do": "anchor", "seconds": float(ab.get("duration", 60.0))}]}


@preset("heal")
def heal(ab: dict[str, Any]) -> dict[str, Any]:
    return {"target": "self", "do": [{"do": "heal", "who": "cursor_ally", "amount": ab["amount"], "over": max(0.1, float(ab["duration"]))}]}


@preset("stim")
def stim(ab: dict[str, Any]) -> dict[str, Any]:
    return {"target": "self", "do": [{"do": "status", "who": "team", "radius": ab["radius"], "name": "stim", "seconds": ab["duration"]}]}


@preset("shield")
def shield(ab: dict[str, Any]) -> dict[str, Any]:
    return {"target": "self", "do": [{"do": "shield", "who": "cursor_ally", "points": ab["points"]}]}


@preset("revive")
def revive(ab: dict[str, Any]) -> dict[str, Any]:
    return {"target": "self", "do": [{"do": "revive", "who": "cursor_fallen", "required": True}]}


@preset("reveal_all")
def reveal_all(ab: dict[str, Any]) -> dict[str, Any]:
    return {"target": "self", "do": [{"do": "reveal", "who": "enemies", "area": "everywhere", "seconds": ab["duration"]}]}


@preset("overdrive")
def overdrive(ab: dict[str, Any]) -> dict[str, Any]:
    return {"target": "self", "do": [{"do": "overdrive", "seconds": ab["duration"]}]}


@preset("immunity")
def immunity(ab: dict[str, Any]) -> dict[str, Any]:
    seconds, regen = float(ab["duration"]), float(ab.get("regen", 5.0))
    return {"target": "self", "do": [{"do": "immunity", "who": "self", "seconds": seconds},
                                     {"do": "heal", "who": "self", "amount": regen * seconds, "over": seconds},
                                     {"do": "status", "who": "self", "name": "stim", "seconds": seconds}]}


@preset("decoy")
def decoy(ab: dict[str, Any]) -> dict[str, Any]:
    steps = {"when": "every", "seconds": 1 / 3, "do": [{"do": "noise"}]}
    return {"target": "self", "place": {"look": "decoy", "lasts": ab["duration"], "move": float(ab.get("speed", 5.0)),
                                        "triggers": [steps]}}
