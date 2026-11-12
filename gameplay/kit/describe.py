"""Short ability descriptions for the agent screen and the in-game help (hold F1).

An ability's own `desc` wins; otherwise the text is built from the preset and its values, or, for composed
abilities, from the target, the object and the effects.
"""
from __future__ import annotations

from typing import Any


def _n(v: Any) -> str:
    f = float(v)
    return str(int(f)) if f.is_integer() else f"{f:g}"


def _status(ab: dict[str, Any], key: str = "status", time_key: str = "status_time") -> str:
    if not ab.get(key):
        return ""
    return f" ({ab[key]}, {_n(ab.get(time_key, 1))} s)"


PRESET_TEXT = {
    "smoke": lambda a: f"Places a smoke {'anywhere' if a.get('remote') else 'at the cursor'} within {_n(a.get('range', 20))} m "
                       f"(radius {_n(a['radius'])} m) that blocks sight for {_n(a['duration'])} s.",
    "wall": lambda a: f"Raises a {_n(a['length'])} m wall at the cursor that blocks sight for {_n(a['duration'])} s"
                      + (f"; enemies crossing it get {a['cross_status']} for {_n(a.get('cross_time', 1))} s." if a.get("cross_status") else "."),
    "vapor_wall": lambda a: PRESET_TEXT["wall"](a),
    "flash": lambda a: f"Throws a flash that pops after {_n(a['fuse'])} s and blinds everyone looking at it for {_n(a['blind'])} s"
                       + (" (also over walls)." if a.get("through_walls") else "."),
    "zone": lambda a: f"Marks a {_n(a['radius'])} m area at the cursor for {_n(a['duration'])} s"
                      + (f" after {_n(a['delay'])} s" if a.get("delay") else "")
                      + (f": enemies inside take {_n(a['dps'])} damage per second" if a.get("dps") else ": enemies inside")
                      + (f" get {a['status']}" if a.get("status") else "")
                      + (" and are revealed" if a.get("reveal") else "")
                      + (f"; allies heal {_n(a['heal_allies'])} per second" if a.get("heal_allies") else "") + ".",
    "slow_field": lambda a: PRESET_TEXT["zone"](a),
    "blast": lambda a: f"Throws a charge that bursts after {_n(a.get('delay', 0))} s (radius {_n(a['radius'])} m)"
                       + (f", dealing up to {_n(a['damage'])} damage" if a.get("damage") else "") + _status(a) + ".",
    "wave": lambda a: f"Sends a {_n(a['length'])} m wave straight ahead through walls"
                      + (f", dealing {_n(a['damage'])} damage" if a.get("damage") else "") + _status(a) + ".",
    "sensor": lambda a: f"Places a sensor that reveals enemies within {_n(a['radius'])} m every {_n(a['pulse'])} s "
                        f"for {_n(a['duration'])} s.",
    "alarm": lambda a: f"Hides an alarm (radius {_n(a['radius'])} m): the first enemy making noise nearby is revealed"
                       + _status(a) + ".",
    "tripwire": lambda a: f"Stretches a hidden {_n(a['length'])} m wire in front of you: the first enemy crossing it is revealed"
                          + _status(a) + ".",
    "dash": lambda a: f"Dashes {_n(a['distance'])} m in the direction you move.",
    "hop": lambda a: "Jumps high into the air.",
    "teleport": lambda a: f"Teleports to the cursor (up to {_n(a.get('range', 8))} m, not onto higher ground).",
    "anchor": lambda a: f"First use marks your position, the second use within {_n(a.get('duration', 60))} s brings you back.",
    "heal": lambda a: f"Heals the ally under the cursor (or yourself) by {_n(a['amount'])} over {_n(a['duration'])} s.",
    "stim": lambda a: f"You and allies within {_n(a['radius'])} m fire and reload faster for {_n(a['duration'])} s.",
    "shield": lambda a: f"Gives the ally under the cursor (or yourself) {_n(a['points'])} armor.",
    "revive": lambda a: f"Revives a fallen ally under the cursor within {_n(a.get('range', 10))} m.",
    "reveal_all": lambda a: f"Reveals every enemy on the map for {_n(a['duration'])} s.",
    "overdrive": lambda a: f"For {_n(a['duration'])} s you are accurate while moving and fire faster.",
    "immunity": lambda a: f"For {_n(a['duration'])} s you ignore negative effects and heal {_n(a.get('regen', 5))} per second.",
    "decoy": lambda a: f"Sends fake footsteps walking forward for {_n(a['duration'])} s.",
}

EFFECT_TEXT = {
    "damage": lambda s: f"deals {_n(s['amount'])} damage", "dps": lambda s: f"deals {_n(s['per_second'])} damage per second",
    "status": lambda s: f"applies {s['name']} ({_n(s.get('seconds', 1))} s)", "heal": lambda s: f"heals {_n(s['amount'])}",
    "heal_rate": lambda s: f"heals {_n(s['per_second'])} per second", "shield": lambda s: f"gives {_n(s['points'])} armor",
    "reveal": lambda s: "reveals", "cleanse": lambda s: "removes negative effects", "push": lambda s: "pushes away",
    "pull": lambda s: "pulls in", "knock_up": lambda s: "knocks up", "dash": lambda s: "dashes", "hop": lambda s: "jumps high",
    "teleport": lambda s: "teleports", "revive": lambda s: "revives an ally", "spawn": lambda s: f"leaves a {s['place'].get('look', 'field')}",
    "immunity": lambda s: "grants immunity", "overdrive": lambda s: "overdrives",
}
WHEN_TEXT = {"start": "when it activates", "expire": "when it bursts", "tick": "while inside", "every": "periodically",
             "enter": "when someone enters", "leave": "when someone leaves", "cross": "when crossed",
             "noise": "when someone makes noise nearby", "gunfire": "when someone shoots nearby"}


def _steps(steps: list[dict[str, Any]]) -> str:
    parts = [EFFECT_TEXT[s["do"]](s) for s in steps if s.get("do") in EFFECT_TEXT]
    return ", ".join(parts)


def describe(ab: dict[str, Any]) -> str:
    if ab.get("desc"):
        return str(ab["desc"])
    kind = str(ab.get("kind", ""))
    if kind in PRESET_TEXT and "place" not in ab and "do" not in ab:
        try:
            return PRESET_TEXT[kind](ab)
        except (KeyError, TypeError, ValueError):
            return kind.replace("_", " ").title()
    out = []
    if ab.get("do"):
        out.append(_steps(ab["do"]).capitalize())
    place = ab.get("place")
    if place:
        bits = [f"Places a {place.get('look', 'field')} for {_n(place.get('lasts', 10))} s"]
        for tr in place.get("triggers", []):
            text = _steps(tr.get("do", []))
            if text:
                bits.append(f"{WHEN_TEXT.get(tr.get('when', ''), tr.get('when', ''))} it {text}")
        out.append("; ".join(bits))
    return (". ".join(o for o in out if o) + ".") if out else str(ab.get("name", ""))


def cost_text(slot: str, ab: dict[str, Any]) -> str:
    if slot == "X":
        return f"{ab.get('cost', '?')} ultimate points"
    parts = []
    if int(ab.get("price", 0)):
        parts.append(f"{ab['price']} credits")
    else:
        parts.append("free each round")
    if int(ab.get("max", 1)) > 1:
        parts.append(f"max {ab['max']}")
    if ab.get("recharge"):
        parts.append(f"recharges in {_n(ab['recharge'])} s")
    if ab.get("kills_to_recharge"):
        parts.append(f"recharges after {ab['kills_to_recharge']} kills")
    return " · ".join(parts)
