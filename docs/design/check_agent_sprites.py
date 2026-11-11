"""Checks an agent's exported strips against the blueprint and creates the enemy variants.

Usage: python docs/design/check_agent_sprites.py kestrel [--no-enemy]
For every state in docs/design/character_sheet_spec.py it checks size and frame count,
the colour budget (outline excluded), reserved team colours and free columns 0 and 15, then writes *_feind.png
(red outer outline) next to each strip unless --no-enemy is given.
Problems are printed as warnings; nothing is deleted.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character_sheet_spec import CELL_H, CELL_W, MAX_COLOURS, RESERVED, STATES  # noqa: E402
from sprites import enemy_variant  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
NO_ENEMY_VARIANT = {"dead", "portrait", "killfeed", "select", "victory"}


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def check(key: str, make_enemy: bool) -> int:
    folder = ROOT / "assets" / "agents" / key
    problems = 0
    colours: set[tuple[int, int, int]] = set()
    reserved = {hex_to_rgb(v): k for k, v in RESERVED.items()}
    for st in STATES:
        path = folder / f"{key}_{st.tag}.png"
        if not path.exists():
            if st.required:
                print(f"MISSING  {path.name} (required)")
                problems += 1
            else:
                print(f"optional {path.name} not there, the game uses {st.fallback}")
            continue
        im = Image.open(path).convert("RGBA")
        w, h = st.size
        frames, rest = divmod(im.width, w)
        if im.height != h or rest:
            print(f"SIZE     {path.name}: {im.width}x{im.height}, expected height {h} and width a multiple of {w}")
            problems += 1
            continue
        if not st.frames[0] <= frames <= st.frames[1]:
            print(f"FRAMES   {path.name}: {frames} frames, allowed {st.frames[0]}-{st.frames[1]}")
            problems += 1
        px = im.load()
        reserved_hits: dict[str, int] = {}
        border_hits = 0
        for y in range(im.height):
            for x in range(im.width):
                r, g, b, a = px[x, y]
                if a == 0:
                    continue
                edge = any(not (0 <= x + dx < im.width and 0 <= y + dy < im.height) or px[x + dx, y + dy][3] == 0
                           for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)))
                ability = st.tag.startswith(("cast", "channel"))
                if not edge and not ability and st.tag not in ("dead", "portrait", "select"):  # outline, glow and derived strips excluded
                    colours.add((r, g, b))
                if (r, g, b) in reserved:
                    reserved_hits[reserved[(r, g, b)]] = reserved_hits.get(reserved[(r, g, b)], 0) + 1
                fx = x % w
                if (w, h) == (CELL_W, CELL_H) and fx in (0, CELL_W - 1):
                    border_hits += 1
        for name, count in reserved_hits.items():
            if count > 6:
                print(f"COLOUR   {path.name}: {count} px in the reserved {name} colour (team/enemy marking)")
                problems += 1
        if border_hits and not st.tag.startswith(("cast", "channel")):
            print(f"BORDER   {path.name}: {border_hits} px in column 0 or 15; keep both free outside ability frames")
            problems += 1
        if make_enemy and st.tag not in NO_ENEMY_VARIANT:
            enemy_variant(im).save(folder / f"{key}_{st.tag}_feind.png")
    if len(colours) > MAX_COLOURS + 4:  # small tolerance for glow pixels in ability frames
        print(f"PALETTE  {len(colours)} drawn colours over all strips; the budget is {MAX_COLOURS}")
        problems += 1
    print(f"{key}: {problems} problem(s)")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("agent")
    ap.add_argument("--no-enemy", action="store_true")
    args = ap.parse_args()
    sys.exit(1 if check(args.agent, not args.no_enemy) else 0)


if __name__ == "__main__":
    main()
