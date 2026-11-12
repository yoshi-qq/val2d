"""Generates the Val2d logo drafts as pixel art (48x48) plus one player card each (64x128).

Usage: python docs/design/logo_design.py
Output: docs/design/logo-design/ (chosen: crosshair, copied to assets/logo.png, icon.ico, playercard.png)
Rules: docs/DECISIONS.md (darker-shade outline, two shading steps, light from the top left).
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image

Color = tuple[int, int, int, int]

BG: Color = (27, 26, 34, 255)
BG_LIGHT: Color = (42, 40, 51, 255)
EDGE: Color = (13, 12, 18, 255)
GRID: Color = (36, 35, 45, 255)
CYAN: Color = (79, 214, 200, 255)
CYAN_DARK: Color = (44, 127, 120, 255)
CYAN_DEEP: Color = (28, 78, 74, 255)
CYAN_LIGHT: Color = (180, 255, 246, 255)
RED: Color = (238, 76, 74, 255)
GRAY: Color = (159, 179, 184, 255)
CLEAR: Color = (0, 0, 0, 0)

OUT = Path(__file__).parent / "logo-design"


def darken(c: Color, f: float = 0.45) -> Color:
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f), 255)


def rounded_plate(size: int = 48, r: int = 4) -> Image.Image:
    im = Image.new("RGBA", (size, size), CLEAR)
    px = im.load()
    for y in range(1, size - 1):
        for x in range(1, size - 1):
            cx = min(max(x, r + 1), size - 2 - r)
            cy = min(max(y, r + 1), size - 2 - r)
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                px[x, y] = BG
    outline(im, EDGE)
    # light from the top left: first inner row/column brighter
    for y in range(size):
        for x in range(size):
            if px[x, y] == BG and (px[x, y - 1] == EDGE or px[x - 1, y] == EDGE):
                px[x, y] = BG_LIGHT
    return im


def outline(im: Image.Image, color: Color | None = None) -> None:
    """Outer outline: fixed colour or a darker shade of the neighbouring pixel."""
    px = im.load()
    w, h = im.size
    src = im.copy().load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3]:
                continue
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and src[nx, ny][3]:
                    px[x, y] = color or darken(src[nx, ny])
                    break


def dot(px, x0: int, y0: int, s: int, c: Color) -> None:
    for y in range(y0 - 1, y0 + s + 1):
        for x in range(x0 - 1, x0 + s + 1):
            px[x, y] = EDGE
    for y in range(y0, y0 + s):
        for x in range(x0, x0 + s):
            px[x, y] = c
    px[x0, y0] = (min(c[0] + 50, 255), min(c[1] + 50, 255), min(c[2] + 50, 255), 255)


def logo_cone() -> Image.Image:
    im = rounded_plate()
    px = im.load()
    ax, ay, half, reach = 23.5, 37.0, math.radians(41), 29.0
    inside = set()
    for y in range(4, 40):
        for x in range(4, 44):
            dx, dy = x - ax, ay - y
            if dy > 0 and abs(math.atan2(dx, dy)) <= half and math.hypot(dx, dy) <= reach:
                inside.add((x, y))
    for x, y in inside:
        near = math.hypot(x - ax, ay - y) < reach * 0.55
        px[x, y] = CYAN_DARK if near else CYAN_DEEP
    for x, y in inside:
        if any((x + dx, y + dy) not in inside for dx, dy in ((0, -1), (-1, 0), (1, 0))):
            px[x, y] = CYAN
    dot(px, 22, 36, 4, CYAN_LIGHT)
    dot(px, 28, 15, 3, RED)
    return im


def logo_crosshair() -> Image.Image:
    im = rounded_plate()
    px = im.load()
    for y in range(3, 45):
        for x in range(3, 45):
            if px[x, y] in (BG, BG_LIGHT) and (x % 12 == 0 or y % 12 == 0):
                px[x, y] = GRID
    c, r = 23.5, 13.0
    for y in range(48):
        for x in range(48):
            d = math.hypot(x - c, y - c)
            gap = abs(x - c) < 3 or abs(y - c) < 3
            if r - 1 <= d <= r + 1 and not gap:
                px[x, y] = CYAN if (x < c or y < c) else CYAN_DARK
    for i in range(6, 15):
        for a, b in ((23, i), (24, i), (23, 47 - i), (24, 47 - i)):
            px[a, b] = CYAN
        for a, b in ((i, 23), (i, 24), (47 - i, 23), (47 - i, 24)):
            px[a, b] = CYAN
    dot(px, 22, 22, 4, RED)
    return im


GLYPHS = {
    "2": [" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"],
    "D": ["#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "],
}


def logo_wordmark() -> Image.Image:
    im = rounded_plate()
    px = im.load()
    s, x0, y0 = 3, 7, 12
    layers = ((3, CYAN_DEEP), (2, CYAN_DEEP), (1, CYAN_DARK), (0, CYAN_LIGHT))
    for off, col in layers:
        for gi, ch in enumerate("2D"):
            for ry, row in enumerate(GLYPHS[ch]):
                for rx, bit in enumerate(row):
                    if bit != "#":
                        continue
                    for yy in range(s):
                        for xx in range(s):
                            x = x0 + gi * 18 + rx * s + xx + off
                            y = y0 + ry * s + yy + off
                            px[x, y] = col
    return im


def playercard(logo: Image.Image) -> Image.Image:
    im = Image.new("RGBA", (64, 128), CLEAR)
    px = im.load()
    for y in range(1, 126):
        for x in range(4, 60):
            if y <= 110 or abs(x - 31.5) <= (125 - y) * 1.9:
                px[x, y] = BG
    outline(im, EDGE)
    for y in range(128):
        for x in range(64):
            if px[x, y] == BG and (px[x, y - 1] == EDGE or px[x - 1, y] == EDGE):
                px[x, y] = BG_LIGHT
    for x in range(8, 56):
        px[x, 104] = GRAY
        px[x, 105] = darken(GRAY, 0.6)
    im.alpha_composite(logo, (8, 10))
    return im


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for name, fn in (("cone", logo_cone), ("crosshair", logo_crosshair), ("wordmark", logo_wordmark)):
        logo = fn()
        logo.save(OUT / f"logo_{name}.png")
        playercard(logo).save(OUT / f"playercard_{name}.png")
        print(name, "saved")


if __name__ == "__main__":
    main()
