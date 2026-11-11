"""Higher-resolution HUD: ability icons 32x32, HUD and status icons 16x16, minimap 12x12,
frames 24x24 (nine-slice, 8 px corners), bars 96x12, banners 32 px high with the game font.

Usage: python docs/design/sprites_hud_hd.py
Same file names as before, so the game picks them up; sizes doubled (minimap x1.5).
Shapes are drawn as masks, then lit automatically: highlight on top/left edges, shadow on
bottom/right edges, darker-shade outline around everything (style guide section 1).
"""
from __future__ import annotations

import math
import runpy
import sys
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sprites as base  # noqa: E402
import sprites_roster as roster  # noqa: E402

ROOT = base.ROOT
hexc, darker, lighter, save = base.hexc, base.darker, base.lighter, base.save
INK = (14, 13, 18, 255)
WHITE, GREY = "#e8e6ef", "#9b98aa"
TEAL, RED, GOLD = "#4fd6c8", "#ee4c4a", "#e0b437"

Painter = Callable[[ImageDraw.ImageDraw, int], None]  # draw, size; fill 1 = base colour, 2 = accent


# ------------------------------------------------------------------ rendering
def render(paint: Painter, size: int, base_col: str, accent: str, outline_col: tuple | None = None) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    paint(ImageDraw.Draw(mask), size)
    m = mask.load()
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    p = im.load()
    cols = {1: hexc(base_col), 2: hexc(accent)}
    for y in range(size):
        for x in range(size):
            v = m[x, y]
            if not v:
                continue
            c = cols.get(v, cols[1])
            up = y == 0 or m[x, y - 1] != v
            left = x == 0 or m[x - 1, y] != v
            down = y == size - 1 or m[x, y + 1] != v
            right = x == size - 1 or m[x + 1, y] != v
            if down or right:
                c = darker(c, 0.72)
            elif up or left:
                c = lighter(c, 0.25)
            p[x, y] = c
    out = im.copy()
    o = out.load()
    for y in range(size):
        for x in range(size):
            if p[x, y][3]:
                continue
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < size and 0 <= ny < size and p[nx, ny][3]:
                    o[x, y] = outline_col or darker(p[nx, ny], 0.35)
                    break
    return out


def star(d: ImageDraw.ImageDraw, cx: float, cy: float, r1: float, r2: float, n: int, fill: int, rot: float = 0) -> None:
    pts = []
    for i in range(n * 2):
        r = r1 if i % 2 == 0 else r2
        a = math.pi * i / n + rot
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    d.polygon(pts, fill=fill)


def sine(d: ImageDraw.ImageDraw, y0: float, amp: float, size: int, width: int, fill: int, phase: float = 0) -> None:
    pts = [(x, y0 + amp * math.sin(x / size * 2 * math.pi * 1.5 + phase)) for x in range(1, size - 1)]
    d.line(pts, fill=fill, width=width)


def figure(d: ImageDraw.ImageDraw, cx: float, top: float, s: float, fill: int) -> None:
    d.ellipse((cx - 3 * s, top, cx + 3 * s, top + 6 * s), fill=fill)
    d.polygon([(cx - 5 * s, top + 16 * s), (cx - 4 * s, top + 7 * s), (cx + 4 * s, top + 7 * s), (cx + 5 * s, top + 16 * s)], fill=fill)


# 24x24 glyph painters (coordinates for size 24)
GLYPHS: dict[str, Painter] = {
    "flash": lambda d, s: (star(d, 12, 12, 11, 4, 8, 1, 0.2), d.ellipse((8, 8, 15, 15), fill=2)),
    "hop": lambda d, s: (d.polygon([(12, 1), (21, 11), (15, 11), (15, 17), (9, 17), (9, 11), (3, 11)], fill=1),
                         d.ellipse((3, 18, 20, 22), fill=2)),
    "dash": lambda d, s: (d.polygon([(8, 5), (22, 12), (8, 19), (11, 12)], fill=1),
                          [d.line([(1, y), (7 - abs(12 - y) // 3, y)], fill=2, width=2) for y in (7, 12, 17)]),
    "overdrive": lambda d, s: (d.ellipse((1, 1, 22, 22), outline=1, width=3),
                               d.polygon([(13, 3), (6, 13), (11, 13), (9, 21), (17, 10), (12, 10)], fill=2)),
    "sensor": lambda d, s: (d.arc((2, 0, 21, 16), 200, 340, fill=2, width=2), d.arc((6, 4, 17, 14), 200, 340, fill=2, width=2),
                            d.pieslice((4, 11, 19, 26), 180, 360, fill=1), d.rectangle((3, 18, 20, 21), fill=1), d.ellipse((9, 13, 14, 18), fill=2)),
    "wall": lambda d, s: ([d.rectangle((x, 3, x + 3, 21), fill=1) for x in (2, 8, 14, 20)], d.rectangle((1, 10, 22, 13), fill=2)),
    "smoke": lambda d, s: (d.ellipse((1, 9, 12, 20), fill=1), d.ellipse((10, 9, 22, 21), fill=1), d.ellipse((5, 3, 18, 15), fill=1),
                           d.ellipse((9, 7, 14, 11), fill=2)),
    "zone": lambda d, s: ([d.arc((1, 1, 22, 22), a, a + 30, fill=1, width=3) for a in range(0, 360, 45)],
                          d.polygon([(12, 6), (18, 12), (12, 18), (6, 12)], fill=2)),
    "decoy": lambda d, s: (figure(d, 9, 3, 1.1, 1), figure(d, 16, 5, 0.9, 2)),
    "teleport": lambda d, s: (d.ellipse((0, 7, 9, 16), outline=1, width=2), d.ellipse((14, 7, 23, 16), outline=1, width=2),
                              d.polygon([(7, 10), (14, 10), (14, 7), (19, 12), (14, 17), (14, 14), (7, 14)], fill=2)),
    "blast": lambda d, s: (star(d, 12, 13, 11, 7, 10, 2), d.ellipse((6, 7, 18, 19), fill=1), d.ellipse((10, 11, 13, 14), fill=2)),
    "immunity": lambda d, s: (d.polygon([(12, 22), (2, 11), (2, 6), (6, 2), (12, 6), (18, 2), (22, 6), (22, 11)], fill=1),
                              d.rectangle((10, 6, 13, 16), fill=2), d.rectangle((7, 9, 16, 12), fill=2)),
    "shield": lambda d, s: (d.polygon([(2, 2), (21, 2), (21, 11), (12, 22), (2, 11)], fill=1),
                            d.polygon([(7, 6), (16, 6), (16, 11), (12, 16), (7, 11)], fill=2)),
    "wave": lambda d, s: (sine(d, 8, 4, 24, 3, 1), sine(d, 16, 4, 24, 3, 2, 1.0)),
    "tripwire": lambda d, s: (d.rectangle((2, 6, 5, 21), fill=1), d.rectangle((18, 6, 21, 21), fill=1),
                              d.line([(5, 12), (18, 12)], fill=2, width=2), d.ellipse((1, 3, 6, 8), fill=2), d.ellipse((17, 3, 22, 8), fill=2)),
    "alarm": lambda d, s: (d.pieslice((4, 2, 19, 22), 180, 360, fill=1), d.rectangle((4, 11, 19, 17), fill=1), d.rectangle((2, 17, 21, 19), fill=1),
                           d.ellipse((9, 18, 14, 23), fill=2), d.arc((0, 0, 23, 20), 210, 250, fill=2, width=2), d.arc((0, 0, 23, 20), 290, 330, fill=2, width=2)),
    "revive": lambda d, s: (figure(d, 12, 7, 1.0, 1), d.polygon([(12, 0), (17, 5), (14, 5), (14, 8), (10, 8), (10, 5), (7, 5)], fill=2)),
    "anchor": lambda d, s: (d.ellipse((5, 1, 18, 14), fill=1), d.polygon([(6, 10), (17, 10), (12, 22)], fill=1), d.ellipse((9, 5, 14, 10), fill=2)),
    "heal": lambda d, s: (d.rectangle((9, 2, 14, 21), fill=2), d.rectangle((2, 9, 21, 14), fill=2), d.rectangle((11, 4, 12, 19), fill=1),
                          d.rectangle((4, 11, 19, 12), fill=1)),
    "reveal_all": lambda d, s: (d.ellipse((0, 5, 23, 18), fill=1), d.ellipse((7, 6, 16, 17), fill=2), d.ellipse((10, 9, 13, 14), fill=1),
                                [d.line([(12, 0), (12, 3)], fill=2, width=2), d.line([(3, 1), (5, 4)], fill=2, width=2), d.line([(20, 1), (18, 4)], fill=2, width=2)]),
}


def plate(size: int, ult: bool) -> Image.Image:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=4, fill=hexc("#1f1e27"), outline=INK)
    d.line([(3, 1), (size - 4, 1)], fill=hexc("#34323e"))
    d.line([(3, size - 2), (size - 4, size - 2)], fill=hexc("#16151c"))
    if ult:
        d.rounded_rectangle((0, 0, size - 1, size - 1), radius=4, outline=hexc(GOLD))
        d.rounded_rectangle((1, 1, size - 2, size - 2), radius=3, outline=hexc("#8a6a1a"))
        for x, y in ((2, 2), (size - 3, 2), (2, size - 3), (size - 3, size - 3)):
            im.load()[x, y] = hexc("#fff3b0")
    return im


def ability_icon(kind: str, accent: str, ult: bool) -> Image.Image:
    paint = GLYPHS.get(kind)
    if paint is None:
        print(f"warning: no glyph for kind {kind}, using zone")
        paint = GLYPHS["zone"]
    g = render(paint, 24, WHITE, accent)
    im = plate(32, ult)
    im.alpha_composite(g, (4, 4))
    return im


def agent_accents() -> dict[str, str]:
    acc = {"kestrel": "#ffd75e", "marrow": "#bac4d6"}
    acc.update({k: str(v["glow"]) for k, v in roster.AGENT_LOOKS.items()})
    return acc


def make_ability_icons() -> None:
    agents = roster._config("agents", "kestrel")
    acc = agent_accents()
    for key, info in agents.items():
        for slot, ab in info["abilities"].items():
            save(ability_icon(str(ab["kind"]), acc.get(key, GOLD), slot == "X"), f"ui/faehigkeit_{key}_{slot}.png")


# ------------------------------------------------------------------ HUD, status, minimap (16 / 12 px)
def small(paint: Painter, size: int, base_col: str, accent: str) -> Image.Image:
    inner = render(paint, size - 2, base_col, accent)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    im.alpha_composite(inner, (1, 1))
    return im


HUD: dict[str, tuple[Painter, str, str]] = {
    "leben": (lambda d, s: (d.rectangle((5, 1, 8, 12), fill=1), d.rectangle((1, 5, 12, 8), fill=1)), WHITE, WHITE),
    "schild": (lambda d, s: (d.polygon([(1, 1), (12, 1), (12, 6), (6, 12), (1, 6)], fill=1), d.polygon([(4, 3), (9, 3), (9, 6), (6, 9), (4, 6)], fill=2)), "#8fb3bd", "#cfe3e8"),
    "credits": (lambda d, s: (d.ellipse((0, 0, 13, 13), fill=1), d.ellipse((3, 3, 10, 10), fill=2), d.rectangle((6, 4, 7, 9), fill=1)), GOLD, "#a8821f"),
    "munition": (lambda d, s: (d.rectangle((4, 4, 9, 12), fill=1), d.pieslice((4, 0, 9, 8), 180, 360, fill=2), d.rectangle((4, 11, 9, 12), fill=2)), "#c7ccd2", GOLD),
    "kopfschuss": (lambda d, s: (d.ellipse((2, 1, 11, 10), fill=1), d.rectangle((4, 9, 9, 12), fill=1), d.ellipse((4, 4, 6, 6), fill=2), d.ellipse((7, 4, 9, 6), fill=2),
                                 d.line([(6, 0), (6, 13)], fill=2), d.line([(0, 6), (13, 6)], fill=2)), WHITE, RED),
    "spike_klein": (lambda d, s: (d.rectangle((1, 2, 12, 11), fill=1), d.rectangle((4, 4, 9, 9), fill=2), d.rectangle((1, 10, 12, 11), fill=2)), "#6b7480", "#ff5a4f"),
    "uhr": (lambda d, s: (d.ellipse((0, 0, 13, 13), fill=1), d.ellipse((2, 2, 11, 11), fill=2), d.line([(6, 3), (6, 7), (9, 7)], fill=1, width=1)), WHITE, "#2a2933"),
    "tot": (lambda d, s: (d.ellipse((1, 0, 12, 10), fill=1), d.rectangle((3, 9, 10, 12), fill=1), d.rectangle((3, 4, 5, 6), fill=2), d.rectangle((8, 4, 10, 6), fill=2),
                          d.line([(4, 11), (4, 12)], fill=2), d.line([(7, 11), (7, 12)], fill=2)), GREY, "#2a2933"),
}

STATUS: dict[str, tuple[Painter, str, str]] = {
    "nearsight": (lambda d, s: (d.ellipse((0, 3, 13, 10), fill=1), d.ellipse((4, 3, 9, 10), fill=2), d.rectangle((0, 3, 13, 5), fill=1)), WHITE, "#545c64"),
    "concuss": (lambda d, s: (d.arc((2, 2, 11, 11), 0, 300, fill=1, width=2), star(d, 2, 2, 2.5, 1, 4, 2), star(d, 11, 11, 2.5, 1, 4, 2)), WHITE, GOLD),
    "slow": (lambda d, s: (d.polygon([(1, 0), (12, 0), (7, 6), (12, 13), (1, 13), (6, 6)], fill=1), d.polygon([(3, 11), (10, 11), (6, 8)], fill=2)), "#9a7ad8", "#d8c8ff"),
    "vulnerable": (lambda d, s: (d.polygon([(1, 1), (12, 1), (12, 6), (6, 12), (1, 6)], fill=1), d.line([(7, 1), (5, 5), (8, 7), (6, 11)], fill=2, width=2)), RED, "#2a1414"),
    "decay": (lambda d, s: (d.polygon([(6, 12), (0, 5), (0, 2), (3, 0), (6, 3), (9, 0), (12, 2), (12, 5)], fill=1), d.line([(6, 3), (5, 6), (7, 8), (6, 11)], fill=2, width=1)), "#9a7ad8", "#2a1f3a"),
    "suppress": (lambda d, s: (d.polygon([(8, 0), (3, 7), (6, 7), (4, 13), (10, 5), (7, 5)], fill=1), d.line([(0, 0), (13, 13)], fill=2, width=2)), GOLD, RED),
    "detain": (lambda d, s: (d.arc((3, 0, 10, 8), 180, 360, fill=1, width=2), d.rectangle((1, 5, 12, 13), fill=1), d.rectangle((6, 8, 7, 10), fill=2)), "#c7ccd2", "#2a2933"),
    "deaf": (lambda d, s: (d.arc((1, 0, 11, 12), 260, 100, fill=1, width=3), d.line([(1, 12), (12, 1)], fill=2, width=2)), WHITE, RED),
    "stim": (lambda d, s: (d.polygon([(6, 0), (12, 6), (9, 6), (6, 3), (3, 6), (0, 6)], fill=1), d.polygon([(6, 6), (12, 12), (9, 12), (6, 9), (3, 12), (0, 12)], fill=2)), "#6fbf73", "#b8f0b0"),
}

MINIMAP: dict[str, tuple[Painter, str, str]] = {
    "selbst": (lambda d, s: d.polygon([(5, 0), (9, 9), (5, 7), (1, 9)], fill=1), WHITE, WHITE),
    "verbuendet": (lambda d, s: (d.ellipse((0, 0, 9, 9), fill=1), d.ellipse((3, 3, 6, 6), fill=2)), TEAL, "#b4fff6"),
    "feind": (lambda d, s: (d.polygon([(5, 0), (9, 5), (5, 9), (1, 5)], fill=1), d.rectangle((4, 4, 5, 5), fill=2)), RED, "#ffb4a8"),
    "tot": (lambda d, s: (d.line([(1, 1), (8, 8)], fill=1, width=2), d.line([(8, 1), (1, 8)], fill=1, width=2)), GREY, GREY),
    "spike": (lambda d, s: (d.rectangle((0, 2, 9, 8), fill=1), d.rectangle((3, 4, 6, 6), fill=2)), GOLD, "#ff5a4f"),
    "dunst": (lambda d, s: (d.ellipse((0, 2, 6, 8), fill=1), d.ellipse((3, 1, 9, 7), fill=1), d.ellipse((2, 4, 8, 9), fill=1)), "#9a9aac", "#c8c8d8"),
    "bann": (lambda d, s: d.ellipse((0, 0, 9, 9), outline=1, width=2), "#9664c8", "#9664c8"),
    "schleier": (lambda d, s: (d.rectangle((0, 3, 9, 6), fill=1), d.rectangle((0, 3, 9, 3), fill=2)), "#bac4d6", WHITE),
}


def make_small_icons() -> None:
    for name, (paint, c1, c2) in HUD.items():
        save(small(paint, 16, c1, c2), f"ui/hud/{name}.png")
    for name, (paint, c1, c2) in STATUS.items():
        save(small(paint, 16, c1, c2), f"ui/status/{name}.png")
    for name, (paint, c1, c2) in MINIMAP.items():
        save(small(paint, 12, c1, c2), f"ui/minimap/{name}.png")


# ------------------------------------------------------------------ frames, bars, banners
def frame(edge: str, glow: str | None) -> Image.Image:
    s = 24
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, s - 1, s - 1), radius=3, fill=hexc("#1f1e27"), outline=hexc(edge))
    d.rectangle((2, 2, s - 3, s // 2), fill=hexc("#23222c"))
    d.line([(3, 1), (s - 4, 1)], fill=hexc("#3a3846"))
    d.line([(1, 3), (1, s - 4)], fill=hexc("#2f2d3a"))
    d.line([(3, s - 2), (s - 4, s - 2)], fill=hexc("#16151c"))
    d.line([(s - 2, 3), (s - 2, s - 4)], fill=hexc("#16151c"))
    for x, y in ((3, 3), (s - 4, 3), (3, s - 4), (s - 4, s - 4)):
        im.load()[x, y] = hexc("#4b4855")
    if glow:
        d.rounded_rectangle((1, 1, s - 2, s - 2), radius=2, outline=hexc(glow)[:3] + (110,))
    return im


def bar(fill: str | None) -> Image.Image:
    w, h = 96, 12
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=2, fill=INK)
    if fill is None:
        d.rectangle((2, 2, w - 3, h - 3), fill=hexc("#2a2933"))
        d.line([(2, h - 3), (w - 3, h - 3)], fill=hexc("#22212a"))
    else:
        c = hexc(fill)
        d.rectangle((2, 2, w - 3, h - 3), fill=c)
        d.line([(2, 2), (w - 3, 2)], fill=lighter(c, 0.35))
        d.rectangle((2, 7, w - 3, h - 3), fill=darker(c, 0.82))
        d.line([(2, h - 3), (w - 3, h - 3)], fill=darker(c, 0.65))
    for x in (24, 48, 72):
        d.line([(x, 2), (x, h - 3)], fill=(14, 13, 18, 120))
    return im


BANNERS = {"sieg": ("VICTORY", TEAL), "niederlage": ("DEFEAT", RED), "seitenwechsel": ("SWITCHING SIDES", GOLD),
           "spike_gelegt": ("BOMB PLANTED", RED), "entschaerft": ("BOMB DEFUSED", TEAL), "verlaengerung": ("OVERTIME", GOLD)}


def banner(text: str, accent: str) -> Image.Image:
    font = ImageFont.truetype(str(ROOT / "font" / "fixed_sys.ttf"), 16)
    probe = Image.new("L", (400, 40), 0)
    pd = ImageDraw.Draw(probe)
    pd.fontmode = "1"
    pd.text((0, 0), text, font=font, fill=255)
    bbox = probe.getbbox() or (0, 0, 10, 10)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    w, h = tw + 40, 32
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    d.polygon([(6, 0), (w - 7, 0), (w - 1, 6), (w - 1, h - 7), (w - 7, h - 1), (6, h - 1), (0, h - 7), (0, 6)], fill=INK)
    d.polygon([(7, 1), (w - 8, 1), (w - 2, 7), (w - 2, h - 8), (w - 8, h - 2), (7, h - 2), (1, h - 8), (1, 7)], fill=hexc("#1f1e27"))
    d.rectangle((3, 3, w - 4, 13), fill=hexc("#23222c"))
    a = hexc(accent)
    d.line([(8, 3), (w - 9, 3)], fill=a)
    d.line([(8, h - 4), (w - 9, h - 4)], fill=darker(a, 0.6))
    for sx in (5, w - 6):
        d.polygon([(sx, h // 2 - 4), (sx + (3 if sx < w // 2 else -3), h // 2), (sx, h // 2 + 4)], fill=a)
    tx, ty = (w - tw) // 2 - bbox[0], (h - th) // 2 - bbox[1]
    d.text((tx + 1, ty + 1), text, font=font, fill=INK)
    d.text((tx, ty), text, font=font, fill=hexc(WHITE))
    return im


def make_panels() -> None:
    save(frame("#0e0d12", None), "ui/hud/rahmen.png")
    save(frame(TEAL, TEAL), "ui/hud/rahmen_aktiv.png")
    save(bar(WHITE), "ui/hud/balken_leben.png")
    save(bar("#8fb3bd"), "ui/hud/balken_schild.png")
    save(bar(GOLD), "ui/hud/balken_fortschritt.png")
    save(bar(None), "ui/hud/balken_leer.png")
    for key, (text, accent) in BANNERS.items():
        save(banner(text, accent), f"ui/banner/{key}.png")


def main() -> None:
    make_ability_icons()
    make_small_icons()
    make_panels()


if __name__ == "__main__":
    main()
