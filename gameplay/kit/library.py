"""Ability library: ready-made abilities in config/content/abilities/*.py (ABILITIES = {"name": ability, ...}) that any
agent can take with library("name", ...overrides). Files starting with _ are skipped."""
from __future__ import annotations

import copy
import warnings
from functools import lru_cache
from typing import Any

from gameplay.data import CONTENT_DIR, _load_py

LIBRARY_DIR = CONTENT_DIR / "abilities"


@lru_cache(maxsize=1)
def load_library() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not LIBRARY_DIR.is_dir():
        return out
    for path in sorted(LIBRARY_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        table = _load_py(path, "ABILITIES")
        if not isinstance(table, dict):
            warnings.warn(f"Ability library {path.name} has no ABILITIES dict; skipped.")
            continue
        for name, ab in table.items():
            if name in out:
                warnings.warn(f"Ability library: {name!r} defined twice; {path.name} wins.")
            out[str(name)] = dict(ab)
    return out


def get(name: str) -> dict[str, Any]:
    ab = load_library().get(name)
    if ab is None:
        raise KeyError(f"no ability {name!r} in config/content/abilities")
    return copy.deepcopy(ab)
