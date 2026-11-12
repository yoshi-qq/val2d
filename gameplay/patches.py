"""Balance patches: config/patches/*.py change values of agents, abilities, weapons, armor, statuses, rules and maps
without touching their own files. Patches apply in file-name order (01_..., 02_...), so a later patch wins.

A patch file defines:
    VERSION = "1.02"                  shown in the patch notes (Career page)
    NOTES = "Kestrel flash shorter"   one line or several, also shown there
    PATCH = {
        "agents":   {"kestrel": {"C": {"blind": 1.2}, "X": {"cost": 8}, "role": "Duelist"}},
        "weapons":  {"assault_rifle": {"price": 3000, "damage": [(60, 160, 40, 34)]}},
        "armor":    {"heavy_shield": {"price": 1100}},
        "statuses": {"slow": {"speed": 0.6}},
        "rules":    {"economy": {"start": 900}},
        "settings": {"hit_zones": {"head_half_width": 0.27}},
        "maps":     {"workyard": {"set": {"name": "Workyard"}, "add": {"crates": [[20, 20, 22, 22]]},
                                 "remove": {"crates": [[30, 10, 32, 12]]}}},
    }
A value of None removes a key (for example "alt": None takes the right-click variant away).
Files starting with _ are templates and are never loaded.
"""
from __future__ import annotations

import copy
import warnings
from functools import lru_cache
from typing import Any

from gameplay.data import CONFIG_DIR, _load_py

PATCH_DIR = CONFIG_DIR / "patches"
SECTIONS = ("agents", "weapons", "armor", "statuses", "rules", "settings", "maps")


@lru_cache(maxsize=1)
def load_patches() -> tuple[tuple[str, str, str, dict[str, Any]], ...]:
    """(file name, version, notes, patch) of every patch file, in file-name order."""
    out = []
    if not PATCH_DIR.is_dir():
        return ()
    for path in sorted(PATCH_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        patch = _load_py(path, "PATCH")
        if not isinstance(patch, dict):
            warnings.warn(f"Patch {path.name} has no PATCH dict; skipped.")
            continue
        unknown = set(patch) - set(SECTIONS)
        if unknown:
            warnings.warn(f"Patch {path.name}: unknown sections {sorted(unknown)} ignored")
        version = str(_load_py(path, "VERSION") or path.stem)
        notes = str(_load_py(path, "NOTES") or "")
        out.append((path.name, version, notes, patch))
    return tuple(out)


def merge(base: dict[str, Any], change: dict[str, Any]) -> dict[str, Any]:
    """Deep merge: dicts merge key by key, other values replace, None removes the key."""
    out = dict(base)
    for key, value in change.items():
        if value is None:
            out.pop(key, None)
        elif isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def section(name: str) -> list[tuple[str, dict[str, Any]]]:
    """(file name, changes) of one section from every patch, in order."""
    return [(fname, p[name]) for fname, _, _, p in load_patches() if isinstance(p.get(name), dict)]


def apply_table(name: str, table: dict[str, Any], create: bool = False) -> dict[str, Any]:
    """Applies a section to a table of entries (agents, weapons, statuses, ...). Unknown entries warn unless create."""
    out = dict(table)
    for fname, changes in section(name):
        for key, change in changes.items():
            if key not in out and not create:
                warnings.warn(f"Patch {fname}: {name} has no {key!r}; change ignored")
                continue
            if change is None:
                out.pop(key, None)
            elif isinstance(change, dict):
                out[key] = merge(out.get(key, {}), change)
    return out


def apply_agent(key: str, agent: dict[str, Any]) -> dict[str, Any]:
    """Patches one agent: top-level fields and the abilities C/Q/E/X (written as "C": {...} in the patch)."""
    out = copy.deepcopy(agent)
    for fname, changes in section("agents"):
        change = changes.get(key)
        if not isinstance(change, dict):
            continue
        for field, value in change.items():
            if field in ("C", "Q", "E", "X"):
                if not isinstance(value, dict):
                    warnings.warn(f"Patch {fname}: agents.{key}.{field} must be a dict")
                    continue
                out.setdefault("abilities", {})
                out["abilities"][field] = merge(out["abilities"].get(field, {}), value)
            elif value is None:
                out.pop(field, None)
            else:
                out[field] = copy.deepcopy(value)
    return out


def apply_map(key: str, raw: dict[str, Any]) -> dict[str, Any]:
    """Patches map data: "set" replaces top-level values, "add" appends to lists, "remove" deletes equal list items."""
    out = copy.deepcopy(raw)
    for fname, changes in section("maps"):
        change = changes.get(key)
        if not isinstance(change, dict):
            continue
        for field, value in dict(change.get("set", {})).items():
            out[field] = copy.deepcopy(value)
        for field, items in dict(change.get("add", {})).items():
            out.setdefault(field, [])
            if isinstance(out[field], dict) and isinstance(items, dict):  # spawns per team
                for team, pts in items.items():
                    out[field].setdefault(str(team), []).extend(copy.deepcopy(pts))
            else:
                out[field].extend(copy.deepcopy(items))
        for field, items in dict(change.get("remove", {})).items():
            if isinstance(out.get(field), list):
                before = len(out[field])
                out[field] = [x for x in out[field] if x not in items and not (isinstance(x, dict) and x.get("rect") in items)]
                if len(out[field]) == before:
                    warnings.warn(f"Patch {fname}: maps.{key}.remove.{field} matched nothing")
    return out


def reload_all() -> None:
    """Forgets every loaded config file, so the next load reads agents, weapons, statuses, rules, settings, materials and
    patches again (used by "Reload content" in the escape menu)."""
    from gameplay import data, match, world
    from gameplay.kit import statuses
    for fn in (load_patches, data.load_config, data.load_weapons, data.load_armor, data.load_rules, statuses.load_statuses,
               match.load_agents, world.load_materials, world.load_things):
        fn.cache_clear()


def notes() -> list[tuple[str, str]]:
    """(version, notes) of every active patch, newest last."""
    return [(version, text) for _, version, text, _ in load_patches()]
