"""Draws the four required ability animations (cast_c, cast_q, cast_e, cast_x) for every agent.

Usage: python docs/design/sprites_casts.py
Poses: C throws overhead, Q places something on the ground, E gathers energy at the chest,
X charges, raises both arms and fills the cell with glow. Enemy variants are written by
docs/design/check_agent_sprites.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sprites as base  # noqa: E402
import sprites_roster as roster  # noqa: E402

BLANK = "................"


def _agents() -> dict[str, tuple[list[str], dict[str, str], str, int, str]]:
    out = {
        "kestrel": (base.KESTREL_TOP, base.KESTREL_PAL, "PPPPPp", 0, "#ffd75e"),
        "marrow": (base.MARROW_TOP, base.MARROW_PAL, "CCCCCc", 2, "#bac4d6"),
    }
    for key, look in roster.AGENT_LOOKS.items():
        top = roster.HEADS[str(look["head"])] + roster.TORSOS[str(look["torso"])]
        pal = {**roster.COMMON, **look["pal"]}  # type: ignore[dict-item]
        out[key] = (top, pal, str(look.get("hip", "PPPPPp")), int(look.get("coat_rows", 0)), str(look["glow"]))  # type: ignore[arg-type]
    return out


def casts(top: list[str], pal: dict[str, str], hip: str, coat: int, glow: str) -> dict[str, list]:
    pal = {**pal, "*": glow, "+": "#fffbe8"}
    stand_legs = base.legs(5, 5, hip, coat_rows=coat)

    def stand(rows: list[str]):
        return base.outline(base.from_rows(rows + stand_legs, pal))

    def crouched(rows: list[str]):
        full = [BLANK] * 3 + rows + base.legs(2, 2, hip, rows_total=8, coat_rows=min(coat, 2))
        return base.outline(base.from_rows(full[:32], pal))

    def put(rows: list[str], points: list[tuple[int, int, str]]) -> list[str]:
        rows = list(rows)
        for x, y, ch in points:
            if 0 <= y < len(rows) and 0 <= x < 16:
                base._set(rows, y, x, ch)
        return rows

    no_right = put(top, [(12, 18, "."), (13, 18, "."), (12, 19, "."), (13, 19, ".")])
    no_left = put(top, [(2, 18, "."), (3, 18, "."), (2, 19, "."), (3, 19, ".")])
    no_hands = base._hands_off(top)

    # C: throw overhead with the right hand
    c = [stand(put(no_right, [(14, 19, "S")])),
         stand(put(no_right, [(13, 8, "S"), (13, 7, "*"), (14, 7, "*")])),
         stand(put(no_right, [(14, 11, "S"), (12, 4, "*"), (12, 3, "+"), (13, 5, "*")]))]
    # Q: kneel and place with the left hand
    q = [crouched(top),
         crouched(put(no_left, [(2, 20, "S"), (2, 21, "*")])),
         crouched(put(no_left, [(2, 20, "S"), (1, 21, "*"), (2, 21, "+"), (3, 21, "*")]))]
    # E: gather energy at the chest with both hands
    chest = put(no_hands, [(5, 15, "S"), (10, 15, "S")])
    e = [stand(chest),
         stand(put(chest, [(7, 15, "*"), (8, 15, "*")])),
         stand(put(chest, [(6, 15, "*"), (7, 15, "+"), (8, 15, "+"), (9, 15, "*"), (7, 14, "*"), (8, 16, "*")]))]
    # X: charge, raise both arms, glow fills the cell, recover
    arms_up = put(no_hands, [(2, 10, "S"), (13, 10, "S"), (2, 11, "s"), (13, 11, "s")])
    ring = [(x, y, "*") for x, y in ((0, 8), (15, 8), (0, 14), (15, 14), (0, 20), (15, 20), (0, 26), (15, 26))]
    bright = [(x, y, "+") for x, y in ((0, 11), (15, 11), (0, 17), (15, 17), (0, 23), (15, 23))]
    halo = [(x, 1, "*") for x in range(6, 10)] + [(7, 0, "+"), (8, 0, "+")]
    x_frames = [crouched(top),
                stand(arms_up),
                stand(put(arms_up, ring)),
                stand(put(arms_up, ring + bright + halo)),
                stand(put(top, [(1, 12, "*"), (14, 16, "*"), (1, 22, "*")]))]
    return {"cast_c": c, "cast_q": q, "cast_e": e, "cast_x": x_frames}


def main() -> None:
    for key, (top, pal, hip, coat, glow) in _agents().items():
        for state, frames in casts(top, pal, hip, coat, glow).items():
            base.save(base.strip(frames), f"agents/{key}/{key}_{state}.png")


if __name__ == "__main__":
    main()
