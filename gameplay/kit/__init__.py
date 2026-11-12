"""Ability kit: targets, player sets, effects, triggers, statuses and presets, all registered by name.

Mechanics from config/mechanics/*.py are loaded once at import, so new effects and triggers need no change
to the game code. See docs/MODDING.md.
"""
from __future__ import annotations

import warnings

from gameplay.data import ROOT, _load_py
from gameplay.kit import builtins, presets  # noqa: F401  (registers the built-in mechanics)
from gameplay.kit.engine import expand, place, run_steps, tick, use
from gameplay.kit.registry import EFFECTS, PASSIVE_TRIGGERS, PRESETS, TARGETS, TRIGGERS, WHO, Ctx
from gameplay.kit.statuses import (add, apply_status, clear_statuses, flag, has, load_statuses, lowest, mult,
                                   speed_factor)

MECHANICS_DIR = ROOT / "config" / "mechanics"

__all__ = ["EFFECTS", "PASSIVE_TRIGGERS", "PRESETS", "TARGETS", "TRIGGERS", "WHO", "Ctx", "add", "apply_status",
           "clear_statuses", "expand", "flag", "has", "load_statuses", "lowest", "mult", "place", "run_steps",
           "speed_factor", "tick", "use", "load_mechanics", "check_ability"]


def load_mechanics() -> list[str]:
    """Runs every config/mechanics/*.py (files starting with _ are skipped). Returns the loaded file names."""
    loaded = []
    if MECHANICS_DIR.is_dir():
        for path in sorted(MECHANICS_DIR.glob("*.py")):
            if path.name.startswith("_"):
                continue
            _load_py(path, "__name__")
            loaded.append(path.stem)
    return loaded


def check_ability(ab: dict) -> list[str]:
    """Problems in an ability definition (unknown preset, target, effect, trigger, player set or status)."""
    problems: list[str] = []
    try:
        spec = expand(ab)
    except (KeyError, TypeError, ValueError) as exc:
        return [f"{ab.get('name', '?')}: {exc}"]
    if str(spec.get("target", "aim")) not in TARGETS:
        problems.append(f"unknown target {spec.get('target')}")
    statuses = load_statuses()

    def steps(items: list, where: str) -> None:
        for s in items:
            name = s.get("do")
            if name not in EFFECTS:
                problems.append(f"{where}: unknown effect {name}")
            if "who" in s and s["who"] not in WHO:
                problems.append(f"{where}: unknown player set {s['who']}")
            if name == "status" and s.get("name") not in statuses:
                problems.append(f"{where}: unknown status {s.get('name')}")
            if name == "spawn":
                obj(s.get("place", {}), where + " > spawn")

    def obj(spec_place: dict, where: str) -> None:
        for tr in spec_place.get("triggers", []):
            if tr.get("when") not in TRIGGERS:
                problems.append(f"{where}: unknown trigger {tr.get('when')}")
            steps(tr.get("do", []), f"{where} > {tr.get('when')}")

    steps(spec.get("do", []), "do")
    if spec.get("place"):
        obj(spec["place"], "place")
    return [f"{ab.get('name', '?')}: {p}" for p in problems]


try:
    load_mechanics()
except Exception as exc:  # a broken mechanics file must not stop the game
    warnings.warn(f"config/mechanics could not be loaded: {exc}")
