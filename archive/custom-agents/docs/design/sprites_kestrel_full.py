"""Completes Kestrel as the full reference agent: every optional state of the blueprint,
plus one example each for a special mechanic, a form and an overlay.

Usage: python docs/design/sprites_kestrel_full.py
Optional states go to assets/agents/kestrel/ (the game uses them right away).
Mechanic, form and overlay examples go to docs/design/blueprint/examples/source/ only, because no agent declares them yet.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sprites as base  # noqa: E402
import sprites_casts as casts  # noqa: E402

TOP, PAL, HIP = base.KESTREL_TOP, base.KESTREL_PAL, "PPPPPp"
GLOW = "#ffd75e"
P = {**PAL, "*": GLOW, "+": "#fffbe8"}
BLANK = "................"
EXAMPLES = Path(__file__).resolve().parent / "blueprint" / "examples" / "source"


def put(rows: list[str], points: list[tuple[int, int, str]]) -> list[str]:
    rows = list(rows)
    for x, y, ch in points:
        if 0 <= y < len(rows) and 0 <= x < 16:
            base._set(rows, y, x, ch)
    return rows


def fig(rows: list[str], pal: dict[str, str] = P) -> Image.Image:
    return base.outline(base.from_rows(rows[:32], pal))


def stand(top: list[str], l: int = 5, r: int = 5) -> list[str]:
    return top + base.legs(l, r, HIP)


def low(top: list[str], drop: int = 3, l: int = 2, r: int = 2) -> list[str]:
    return [BLANK] * drop + top + base.legs(l, r, HIP, rows_total=32 - drop - len(top))


NO_HANDS = base._hands_off(TOP)
NO_RIGHT = put(TOP, [(12, 18, "."), (13, 18, "."), (12, 19, "."), (13, 19, ".")])


def shift(rows: list[str], dx: int, upto: int) -> list[str]:
    out = []
    for i, r in enumerate(rows):
        if i <= upto:
            r = ("." * dx + r[:16 - dx]) if dx > 0 else (r[-dx:] + "." * -dx)
        out.append(r)
    return out


def states() -> dict[str, list[Image.Image]]:
    s: dict[str, list[Image.Image]] = {}
    s["crouch_walk"] = [fig(low(TOP, 3, l, r)) for l, r in ((2, 2), (2, 1), (2, 2), (1, 2))]
    arms_out = put(NO_HANDS, [(2, 16, "S"), (13, 16, "S")])
    s["fall"] = [fig(stand(arms_out, 4, 4)), fig(stand(arms_out, 4, 3))]
    s["land"] = [fig(low(TOP, 2, 3, 3)), fig(low(TOP, 1, 4, 4))]
    hip = put(NO_RIGHT, [(12, 20, "S")])
    chest = put(NO_RIGHT, [(11, 15, "S")])
    s["equip"] = [fig(stand(hip)), fig(stand(chest)), fig(stand(TOP))]
    s["melee"] = [fig(stand(put(NO_RIGHT, [(13, 12, "S")]))),
                  fig(stand(put(NO_RIGHT, [(13, 9, "S"), (12, 8, "+"), (13, 7, "+")]))),
                  fig(stand(put(NO_RIGHT, [(10, 13, "S"), (8, 12, "+"), (7, 13, "+"), (6, 14, "+")]))),
                  fig(stand(put(NO_RIGHT, [(12, 17, "S")])))]
    s["flinch"] = [fig(stand(shift(TOP, -1, 10))), fig(stand(TOP))]
    kneel = base._hands_off(TOP)
    s["plant"] = [fig(low(put(kneel, [(6, 20, "S"), (9, 20, "S")]), 3)),
                  fig(low(put(kneel, [(5, 20, "S"), (10, 20, "S"), (7, 20, "*")]), 3))]
    s["defuse"] = [fig(low(put(kneel, [(6, 20, "S"), (8, 20, "S")]), 3)),
                   fig(low(put(kneel, [(7, 20, "S"), (9, 20, "S"), (8, 19, "+")]), 3))]
    s["dying"] = [fig(stand(shift(TOP, -1, 10))), fig(low(shift(TOP, -1, 10), 3)),
                  fig(low(TOP, 6, 1, 1)), fig(low(TOP[:18], 12, 1, 1))]
    s["victory"] = [fig(stand(put(NO_RIGHT, [(13, 9, "S"), (13, 10, "s")]))),
                    fig(stand(put(NO_HANDS, [(2, 9, "S"), (13, 9, "S"), (2, 10, "s"), (13, 10, "s")]))),
                    fig(stand(put(NO_RIGHT, [(13, 9, "S"), (13, 10, "s"), (13, 8, "*")])))]
    # channel: loops on the last pose of each cast with flickering glow
    cast = casts.casts(TOP, PAL, HIP, 0, GLOW)
    c_last = put(NO_RIGHT, [(14, 11, "S")])
    s["channel_c"] = [fig(stand(put(c_last, [(14, 10, "*")]))), fig(stand(put(c_last, [(14, 10, "+"), (15, 9, "*")])))]
    q_last = put(base._hands_off(TOP), [(2, 20, "S")])
    s["channel_q"] = [fig(low(put(q_last, [(2, 21, "*")]), 3)), fig(low(put(q_last, [(1, 21, "*"), (3, 21, "*")]), 3))]
    e_last = put(NO_HANDS, [(5, 15, "S"), (10, 15, "S")])
    s["channel_e"] = [fig(stand(put(e_last, [(7, 15, "*"), (8, 15, "+")]))), fig(stand(put(e_last, [(7, 15, "+"), (8, 15, "*"), (7, 14, "*")])))]
    x_up = put(NO_HANDS, [(2, 10, "S"), (13, 10, "S"), (2, 11, "s"), (13, 11, "s")])
    s["channel_x"] = [fig(stand(put(x_up, [(0, 12, "*"), (15, 18, "*"), (7, 1, "*")]))),
                      fig(stand(put(x_up, [(0, 18, "*"), (15, 12, "*"), (8, 1, "*")])))]
    s["cast"] = cast["cast_e"]  # shared fallback pose
    return s


def killfeed() -> Image.Image:
    idle = fig(stand(TOP))
    return idle.crop((0, 0, 16, 16))


def select_big() -> Image.Image:
    return fig(stand(TOP)).resize((32, 64), Image.NEAREST)


def mechanic_glide() -> Image.Image:
    """kestrel_mech_glide: legs together trailing, arms back, glide streaks."""
    arms_back = put(NO_HANDS, [(1, 17, "S"), (14, 17, "S")])
    frames = [fig(stand(arms_back, 5, 5)), fig(stand(put(arms_back, [(0, 24, "+"), (15, 26, "+")]), 5, 5))]
    return base.strip(frames)


def form_overdrive() -> dict[str, Image.Image]:
    """kestrel@overdrive: same figure, glowing hair and goggles, darker jacket."""
    pal = {**P, "H": "#ffb347", "h": "#d9772b", "G": "#fff3b0", "g": "#ffd75e", "J": "#3f4c27", "j": "#2a331a"}
    idle = fig(stand(put(TOP, [(6, 1, "*"), (9, 1, "*")])), pal)
    walk = [fig(stand(put(TOP, [(6, 1, "*"), (9, 1, "*")]), l, r), pal) for l, r in base.WALK]
    return {"idle": idle, "walk": base.strip(walk)}


def overlay_shield() -> Image.Image:
    """kestrel_overlay_shield: translucent shell around the figure, one frame."""
    silhouette = fig(stand(TOP))
    im = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
    src, dst = silhouette.load(), im.load()
    for y in range(32):
        for x in range(16):
            if src[x, y][3]:
                continue
            near = any(0 <= x + dx < 16 and 0 <= y + dy < 32 and src[x + dx, y + dy][3]
                       for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            if near and (x + y) % 2 == 0:
                dst[x, y] = (186, 220, 255, 170)
    return im


def main() -> None:
    for state, frames in states().items():
        base.save(base.strip(frames) if len(frames) > 1 else frames[0], f"agents/kestrel/kestrel_{state}.png")
    base.save(killfeed(), "agents/kestrel/kestrel_killfeed.png")
    base.save(select_big(), "agents/kestrel/kestrel_select.png")
    EXAMPLES.mkdir(parents=True, exist_ok=True)
    mechanic_glide().save(EXAMPLES / "kestrel_mech_glide.png")
    for state, im in form_overdrive().items():
        im.save(EXAMPLES / f"kestrel@overdrive_{state}.png")
    overlay_shield().save(EXAMPLES / "kestrel_overlay_shield.png")
    print("written: mechanic, form and overlay examples in", EXAMPLES)


if __name__ == "__main__":
    main()
