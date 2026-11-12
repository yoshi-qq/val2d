"""Archived layouts for regression tests that depend on their geometry."""

import json
from pathlib import Path

from gameplay.world import WorldMap, parse_map

ARCHIVED_MAPS = Path(__file__).resolve().parents[1] / "archive/custom-maps/gameplay/data/maps"


def load_archived_map(key: str) -> WorldMap:
    path = ARCHIVED_MAPS / f"{key}.json"
    return parse_map(key, json.loads(path.read_text(encoding="utf-8")))
