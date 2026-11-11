"""Buy-menu weapon and vest icons in high resolution: 64x24, side view, muzzle right, centred.

Usage: python docs/design/sprites_buy_hd.py
Writes assets/weapons/val2d/{key}_kauf.png and assets/ui/buy/vest_{light,heavy}.png.
Shapes are drawn as value masks (1 body, 2 accent, 3 dark metal, 4 glass, 5 steel, 6 gold) and lit
automatically: highlight top/left, shadow bottom/right, darker-shade outline. Original designs.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sprites as base  # noqa: E402

hexc, darker, lighter, save = base.hexc, base.darker, base.lighter, base.save
W, H = 64, 24


def render(mask: Image.Image, colours: dict[int, str]) -> Image.Image:
    m = mask.load()
    w, h = mask.size
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    p = im.load()
    for y in range(h):
        for x in range(w):
            v = m[x, y]
            if not v:
                continue
            c = hexc(colours.get(v, colours[1]))
            same = lambda xx, yy: 0 <= xx < w and 0 <= yy < h and m[xx, yy] == v  # noqa: E731
            if not same(x, y + 1) or not same(x + 1, y):
                c = darker(c, 0.72)
            elif not same(x, y - 1) or not same(x - 1, y):
                c = lighter(c, 0.28)
            p[x, y] = c
    out = im.copy()
    o = out.load()
    for y in range(h):
        for x in range(w):
            if p[x, y][3]:
                continue
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and p[nx, ny][3]:
                    o[x, y] = darker(p[nx, ny], 0.35)
                    break
    return out


# ------------------------------------------------------------------ weapon geometry
SPECS: dict[str, dict] = {
    "spatz":    {"kind": "pistol", "L": 28, "accent": "#6c6b75"},
    "stachel":  {"kind": "pistol", "L": 30, "accent": "#a8521f", "double": True},
    "hornisse": {"kind": "pistol", "L": 32, "accent": "#c9a227", "mag": "stick", "comp": True},
    "lynx":     {"kind": "pistol", "L": 40, "accent": "#4f6b73", "silencer": 12},
    "kite":     {"kind": "pistol", "L": 38, "accent": "#8a5a43", "long": True, "sight": True},
    "bulle":    {"kind": "revolver", "L": 36, "accent": "#7a5233"},
    "wespe":    {"kind": "long", "L": 44, "B": 8, "stock": "wire", "mag": "stick", "accent": "#c9a227"},
    "sirene":   {"kind": "long", "L": 48, "B": 10, "stock": "wire", "mag": "stick", "accent": "#4f6b73", "vents": True},
    "brecher":  {"kind": "long", "L": 58, "B": 22, "stock": "full", "mag": "pump", "accent": "#7a5233"},
    "faecher":  {"kind": "long", "L": 56, "B": 16, "stock": "full", "mag": "box", "accent": "#a8521f", "vents": True},
    "falke":    {"kind": "long", "L": 56, "B": 14, "stock": "full", "mag": "curve", "accent": "#5b6b3a", "vents": True},
    "lanze":    {"kind": "long", "L": 60, "B": 16, "stock": "full", "mag": "box", "accent": "#5b6b3a", "scope": 18},
    "speer":    {"kind": "long", "L": 60, "B": 12, "stock": "full", "mag": "curve", "accent": "#36454c", "silencer": 12, "vents": True},
    "hammer":   {"kind": "long", "L": 58, "B": 14, "stock": "full", "mag": "curve", "accent": "#7a5233"},
    "heron":    {"kind": "long", "L": 58, "B": 14, "stock": "full", "mag": "curve", "accent": "#5a6b7a", "scope": 11, "vents": True},
    "elster":   {"kind": "long", "L": 60, "B": 20, "stock": "full", "mag": "box_small", "accent": "#4f6b73", "scope": 18, "bolt": True},
    "crane":    {"kind": "long", "L": 62, "B": 24, "stock": "full", "mag": "none", "accent": "#6b4a2e", "scope": 16, "double": True},
    "adler":    {"kind": "long", "L": 64, "B": 22, "stock": "full", "mag": "box", "accent": "#3e4a3a", "scope": 22, "bipod": True, "brake": True},
    "muehle":   {"kind": "long", "L": 60, "B": 16, "stock": "full", "mag": "drum", "accent": "#c9a227", "bipod": True, "vents": True},
    "walze":    {"kind": "long", "L": 64, "B": 18, "stock": "full", "mag": "belt", "accent": "#a8521f", "foregrip": True, "vents": True},
}


def draw_long(d: ImageDraw.ImageDraw, s: dict) -> None:
    L, B = s["L"], s["B"]
    x0 = (W - L) // 2
    end = x0 + L - 1
    body_end = end - B
    stock = s.get("stock")
    if stock == "full":
        d.polygon([(x0, 8), (x0 + 12, 8), (x0 + 13, 15), (x0 + 6, 15), (x0, 18)], fill=2)
        d.rectangle((x0, 8, x0 + 1, 18), fill=3)
        rx = x0 + 12
    elif stock == "wire":
        d.line([(x0 + 1, 9), (x0 + 10, 9)], fill=3, width=2)
        d.line([(x0 + 1, 15), (x0 + 10, 13)], fill=3, width=2)
        d.rectangle((x0, 8, x0 + 1, 16), fill=3)
        rx = x0 + 10
    else:
        rx = x0
    # receiver and top rail
    d.rectangle((rx, 7, body_end, 14), fill=1)
    d.rectangle((rx + 2, 5, body_end - 2, 6), fill=3)
    for x in range(rx + 3, body_end - 2, 3):
        d.point((x, 5), fill=1)
    d.rectangle((rx + (body_end - rx) // 2 - 2, 9, rx + (body_end - rx) // 2 + 2, 10), fill=3)  # ejection port
    # barrel, handguard, muzzle
    d.rectangle((body_end, 9, end, 11), fill=3)
    if s.get("double"):
        d.rectangle((body_end, 12, end, 14), fill=3)
        d.ellipse((body_end - 2, 10, body_end + 2, 14), fill=5)
    if s.get("vents") or s.get("foregrip"):
        hg_end = body_end + max(4, B // 2)
        d.rectangle((body_end, 8, hg_end, 13), fill=1)
        for x in range(body_end + 2, hg_end - 1, 3):
            d.point((x, 10), fill=3)
            d.point((x, 11), fill=3)
        d.rectangle((hg_end - 1, 6, hg_end, 8), fill=3)  # front sight
    if s.get("silencer"):
        n = s["silencer"]
        d.rectangle((end - n + 1, 8, end, 12), fill=3)
        for x in range(end - n + 3, end, 3):
            d.line([(x, 8), (x, 12)], fill=1)
    if s.get("brake"):
        d.rectangle((end - 3, 8, end, 12), fill=3)
        d.point((end - 1, 10), fill=1)
    # grip and trigger guard
    gx = rx + max(4, (body_end - rx) // 3)
    d.polygon([(gx, 15), (gx + 5, 15), (gx + 3, 22), (gx - 2, 22)], fill=3)
    d.arc((gx + 4, 12, gx + 11, 19), 0, 180, fill=3, width=1)
    # magazine
    mx = gx + 10
    mag = s.get("mag")
    if mag == "stick":
        d.rectangle((mx, 15, mx + 3, 22), fill=2)
    elif mag == "curve":
        d.polygon([(mx, 15), (mx + 5, 15), (mx + 8, 22), (mx + 3, 22)], fill=2)
    elif mag == "box":
        d.rectangle((mx, 15, mx + 7, 19), fill=2)
    elif mag == "box_small":
        d.rectangle((mx, 15, mx + 5, 18), fill=2)
    elif mag == "drum":
        d.ellipse((mx - 1, 13, mx + 10, 23), fill=2)
        d.ellipse((mx + 3, 17, mx + 6, 20), fill=3)
    elif mag == "belt":
        d.rectangle((mx, 15, mx + 9, 20), fill=2)
        for i in range(4):
            d.rectangle((mx + 10 + i * 2, 16 + i, mx + 11 + i * 2, 17 + i), fill=6)
    elif mag == "pump":
        d.rectangle((body_end + 3, 12, body_end + 13, 15), fill=2)
        for x in range(body_end + 5, body_end + 12, 2):
            d.point((x, 13), fill=3)
    if s.get("foregrip"):
        fx = body_end + 4
        d.rectangle((fx, 14, fx + 3, 21), fill=3)
    if s.get("bipod"):
        bx = body_end + 2
        d.line([(bx, 12), (bx - 3, 22)], fill=3, width=1)
        d.line([(bx + 1, 12), (bx + 5, 22)], fill=3, width=1)
    if s.get("bolt"):
        bx = rx + (body_end - rx) * 2 // 3
        d.line([(bx, 10), (bx + 2, 16)], fill=5, width=1)
        d.ellipse((bx + 1, 15, bx + 4, 18), fill=5)
    if s.get("scope"):
        n = s["scope"]
        sx = rx + max(1, (body_end - rx - n) // 2)
        d.rectangle((sx + 2, 4, sx + 3, 6), fill=3)
        d.rectangle((sx + n - 4, 4, sx + n - 3, 6), fill=3)
        d.rectangle((sx, 1, sx + n, 4), fill=3)
        d.rectangle((sx - 1, 0, sx + 1, 5), fill=3)
        d.rectangle((sx + n - 1, 0, sx + n + 1, 5), fill=3)
        d.rectangle((sx + n, 1, sx + n, 3), fill=4)


def draw_pistol(d: ImageDraw.ImageDraw, s: dict) -> None:
    L = s["L"]
    x0 = (W - L) // 2 + 2
    end = x0 + L - 1
    slide_end = end - (s.get("silencer", 0))
    d.rectangle((x0, 6, slide_end, 11), fill=1)  # slide
    d.rectangle((x0, 6, slide_end, 6), fill=1)
    for x in range(x0 + 2, x0 + 8, 2):
        d.line([(x, 7), (x, 10)], fill=3)  # serrations
    d.rectangle((x0 + 1, 12, slide_end - 3, 13), fill=3)  # frame
    d.rectangle((slide_end - 1, 8, slide_end, 9), fill=3)  # muzzle
    if s.get("double"):
        d.rectangle((slide_end - 8, 12, slide_end, 13), fill=3)
        d.rectangle((slide_end - 1, 12, slide_end, 13), fill=5)
    if s.get("long"):
        d.rectangle((slide_end - 10, 8, slide_end, 10), fill=3)
    if s.get("sight"):
        d.rectangle((slide_end - 14, 3, slide_end - 8, 5), fill=3)
        d.rectangle((slide_end - 8, 3, slide_end - 8, 4), fill=4)
    if s.get("comp"):
        d.rectangle((slide_end - 4, 5, slide_end, 12), fill=3)
        d.point((slide_end - 2, 6), fill=1)
    if s.get("silencer"):
        d.rectangle((slide_end + 1, 7, end, 11), fill=3)
        for x in range(slide_end + 3, end, 3):
            d.line([(x, 7), (x, 11)], fill=1)
    gx = x0 + 3
    d.polygon([(gx, 13), (gx + 7, 13), (gx + 6, 22), (gx - 2, 22)], fill=2)  # grip
    d.rectangle((gx - 2, 21, gx + 6, 22), fill=3)
    d.arc((gx + 6, 10, gx + 13, 17), 0, 180, fill=3, width=1)  # trigger guard
    if s.get("mag") == "stick":
        d.rectangle((gx - 1, 21, gx + 4, 23), fill=2)
        d.rectangle((gx - 1, 23, gx + 4, 23), fill=3)


def draw_revolver(d: ImageDraw.ImageDraw, s: dict) -> None:
    L = s["L"]
    x0 = (W - L) // 2 + 2
    end = x0 + L - 1
    d.rectangle((x0 + 4, 6, x0 + 14, 12), fill=1)  # frame
    d.ellipse((x0 + 7, 5, x0 + 16, 14), fill=5)  # cylinder
    for y in (7, 9, 11):
        d.line([(x0 + 9, y), (x0 + 14, y)], fill=3)
    d.rectangle((x0 + 16, 6, end, 9), fill=3)  # barrel
    d.rectangle((x0 + 16, 10, end - 6, 11), fill=1)  # ejector rod housing
    d.rectangle((end - 1, 4, end, 6), fill=3)  # sight
    d.polygon([(x0 + 2, 7), (x0 + 5, 6), (x0 + 5, 9)], fill=3)  # hammer
    d.polygon([(x0 + 3, 12), (x0 + 10, 12), (x0 + 8, 22), (x0, 21)], fill=2)  # grip
    d.arc((x0 + 9, 9, x0 + 16, 17), 0, 180, fill=3, width=1)


def draw_knife(d: ImageDraw.ImageDraw) -> None:
    d.rectangle((14, 10, 26, 14), fill=2)  # handle
    for x in range(16, 26, 3):
        d.line([(x, 10), (x, 14)], fill=3)
    d.rectangle((26, 8, 28, 16), fill=3)  # guard
    d.polygon([(29, 9), (48, 9), (52, 11), (48, 14), (29, 14)], fill=5)  # blade
    d.line([(30, 11), (46, 11)], fill=1)


COLOURS = {1: "#4a4952", 3: "#26252b", 4: "#8fb3bd", 5: "#c7ccd2", 6: "#e0b437"}


def weapon(key: str, spec: dict) -> Image.Image:
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    {"long": draw_long, "pistol": draw_pistol, "revolver": draw_revolver}[spec["kind"]](d, spec)
    return render(mask, {**COLOURS, 2: spec["accent"]})


def knife() -> Image.Image:
    mask = Image.new("L", (W, H), 0)
    draw_knife(ImageDraw.Draw(mask))
    return render(mask, {**COLOURS, 2: "#3a2f25"})


def vest(heavy: bool) -> Image.Image:
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    d.polygon([(14, 4), (22, 4), (25, 7), (39, 7), (42, 4), (50, 4), (52, 8), (52, 21), (12, 21), (12, 8)], fill=1)
    d.rectangle((15, 1, 20, 4), fill=3)
    d.rectangle((44, 1, 49, 4), fill=3)  # shoulder straps
    d.rectangle((25, 9, 39, 19), fill=2 if heavy else 1)  # front plate
    if heavy:
        d.rectangle((14, 9, 22, 19), fill=2)
        d.rectangle((42, 9, 50, 19), fill=2)
        for x in (16, 19, 44, 47):
            d.rectangle((x, 13, x + 2, 17), fill=3)  # pouches
        d.rectangle((26, 15, 38, 16), fill=6)
    else:
        d.rectangle((27, 12, 37, 13), fill=4)
    d.rectangle((12, 20, 52, 21), fill=3)
    plate = "#4a525c" if heavy else "#6b7480"
    return render(mask, {1: plate, 2: "#3e4248" if heavy else plate, 3: "#26252b", 4: "#8fb3bd", 6: "#e0b437"})


def main() -> None:
    for key, spec in SPECS.items():
        save(weapon(key, spec), f"weapons/val2d/{key}_kauf.png")
    save(knife(), "weapons/val2d/messer_kauf.png")
    save(vest(False), "ui/buy/vest_light.png")
    save(vest(True), "ui/buy/vest_heavy.png")


if __name__ == "__main__":
    main()
