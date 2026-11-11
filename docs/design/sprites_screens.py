"""Draws the screen sprites killfeed (16x16) and select (32x64) for every agent from its idle frame.

Usage: python docs/design/sprites_screens.py [agent ...]   (no argument = all agents with an idle sprite)
killfeed: head and shoulders, the top 16 rows of the idle frame.
select:   the idle frame at 2x (nearest neighbour), so it matches the figure in game exactly.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "assets" / "agents"


def make(key: str) -> bool:
    idle_path = AGENTS / key / f"{key}_idle.png"
    if not idle_path.exists():
        print(f"warning: {idle_path.relative_to(ROOT)} missing, skipped")
        return False
    idle = Image.open(idle_path).convert("RGBA").crop((0, 0, 16, 32))
    idle.crop((0, 0, 16, 16)).save(AGENTS / key / f"{key}_killfeed.png")
    idle.resize((32, 64), Image.NEAREST).save(AGENTS / key / f"{key}_select.png")
    print(f"written: {key}_killfeed.png, {key}_select.png")
    return True


def main() -> None:
    keys = sys.argv[1:] or sorted(p.name for p in AGENTS.iterdir() if (p / f"{p.name}_idle.png").exists())
    for key in keys:
        make(key)


if __name__ == "__main__":
    main()
