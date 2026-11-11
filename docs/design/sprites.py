"""Generates the Val2d sprites of the design session as PNG files under assets/.

Usage: python docs/design/sprites.py
Rules (docs/ENTSCHEIDUNGEN.md, sprite concept): 16 px = 1 m, figure 16x32, tile 32x32,
outline in a darker shade of the neighbouring colour, two shading steps, light from the top left,
sprites are team-neutral; enemy variant with a red outline (*_feind.png). All figures and items
are original designs. File names stay German so existing code keeps working.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
ENEMY = (238, 76, 74, 255)
CLEAR = (0, 0, 0, 0)
Color = tuple[int, int, int, int]


def hexc(h: str) -> Color:
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), 255)


def darker(c: Color, f: float = 0.5) -> Color:
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f), 255)


def lighter(c: Color, f: float = 0.2) -> Color:
    return tuple(int(v + (255 - v) * f) for v in c[:3]) + (255,)  # type: ignore[return-value]


def from_rows(rows: list[str], pal: dict[str, str]) -> Image.Image:
    w = max(len(r) for r in rows)
    im = Image.new("RGBA", (w, len(rows)), CLEAR)
    px = im.load()
    for y, row in enumerate(rows):
        assert len(row) == w, f"row {y} has {len(row)} instead of {w} characters: {row!r}"
        for x, ch in enumerate(row):
            if ch != ".":
                px[x, y] = hexc(pal[ch])
    return im


def outline(im: Image.Image, color: Color | None = None) -> Image.Image:
    """Outer outline: fixed colour or a darker shade of the neighbouring pixel."""
    out = im.copy()
    src, dst = im.load(), out.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            if src[x, y][3]:
                continue
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and src[nx, ny][3]:
                    dst[x, y] = color or darker(src[nx, ny], 0.45)
                    break
    return out


def enemy_variant(im: Image.Image) -> Image.Image:
    """Replaces the outline (outermost pixels) with red."""
    out = im.copy()
    src, dst = im.load(), out.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            if not src[x, y][3]:
                continue
            edge = any(not (0 <= x + dx < w and 0 <= y + dy < h) or not src[x + dx, y + dy][3]
                       for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)))
            if edge:
                dst[x, y] = ENEMY
    return out


def save(im: Image.Image, rel: str) -> None:
    path = ASSETS / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    print("written:", rel, im.size)


def strip(frames: list[Image.Image]) -> Image.Image:
    w, h = frames[0].size
    out = Image.new("RGBA", (w * len(frames), h), CLEAR)
    for i, f in enumerate(frames):
        out.alpha_composite(f, (i * w, 0))
    return out


# ------------------------------------------------------------------ agents
def legs(left: int, right: int, hip: str, rows_total: int = 11, coat_rows: int = 0) -> list[str]:
    """Legs from row 21: hip, trouser legs (P/p), boots (B). Length 5 = fully extended."""
    out = []
    for i in range(rows_total):
        y = 21 + i
        a = ["."] * 16
        if i < 2:
            for x in range(5, 11):
                a[x] = hip[x - 5]
        if i < coat_rows:
            for x in range(4, 12):
                a[x] = "C" if x < 11 else "c"
        for length, x0, outward in ((left, 5, 4), (right, 9, 12)):
            end = 23 + length
            if 23 <= y < end and not (i < coat_rows):
                a[x0], a[x0 + 1], a[x0 + 2] = "P", "P", "p"
            if y == end:
                a[x0] = a[x0 + 1] = a[x0 + 2] = "B"
            if y == end + 1:
                a[x0] = a[x0 + 1] = a[x0 + 2] = "B"
                a[outward] = "B"
        out.append("".join(a))
    return out


KESTREL_TOP = [
    "................",
    "......H..H......",
    ".....HHHHHH.....",
    "....HHHHHHHH....",
    "....HHHHHHHh....",
    "....HhSSSSSh....",
    "....SGGSSGGs....",
    "....SggSSggs....",
    "....SSSSSSSs....",
    ".....SSSSSs.....",
    "....FFFFFFFf....",
    "...JFFFFFFFfj...",
    "..JJJJFFJJJJj...",
    "..JJjJFfJjJJj...",
    "..JJJJJFfJJJj...",
    "..JJ.JJJJJJ.Jj..",
    "..JJ.JJJJJJ.Jj..",
    "..JJ.KKKKKK.Jj..",
    "..SS.PPPPPP.Ss..",
    "..ss.PPPPPP.ss..",
    ".....PPPPPP.....",
]
KESTREL_PAL = {"H": "#c4562c", "h": "#8f3a1f", "S": "#d9a07a", "s": "#a8735a", "G": "#8fb3bd", "g": "#4f6b73",
               "F": "#d8b77a", "f": "#a88a52", "J": "#5b6b3a", "j": "#3f4c27", "K": "#3a2f25",
               "P": "#3a3b44", "p": "#26272e", "B": "#1f1c1a"}

MARROW_TOP = [
    "................",
    "................",
    "......SSSS......",
    ".....SSSSSS.....",
    "....SSSSSSSs....",
    "....SSSSSSSs....",
    "....SEESSEEs....",
    "....SMMMMMMs....",
    "....SMmRRmMs....",
    ".....MMMMMm.....",
    "......nnnn......",
    "...CCCCCCCCc....",
    "..CCCCcCCCCCc...",
    "..CCYCcCCYCCc...",
    "..CCCCcCCCCCc...",
    "..CC.CcCCCC.Cc..",
    "..CC.CcCCCC.Cc..",
    "..CC.KKKKKK.Cc..",
    "..SS.CcCCCC.Ss..",
    "..ss.CcCCCC.ss..",
    ".....CcCCCc.....",
]
MARROW_PAL = {"S": "#8a5a43", "s": "#63402f", "E": "#1b1a1a", "M": "#7d8790", "m": "#545c64", "R": "#c9a227",
              "n": "#2a2d33", "C": "#36454c", "c": "#243036", "Y": "#c9a227", "K": "#1f1c1a",
              "P": "#2d2c31", "p": "#1f1e23", "B": "#1b1a1a"}

WALK = [(5, 5), (5, 3), (5, 5), (3, 5)]


def agent_frames(top: list[str], pal: dict[str, str], hip: str, coat_rows: int) -> dict[str, list[Image.Image]]:
    def figure(rows: list[str]) -> Image.Image:
        return outline(from_rows(rows, pal))

    idle = figure(top + legs(5, 5, hip, coat_rows=coat_rows))
    walk = [figure(top + legs(l, r, hip, coat_rows=coat_rows)) for l, r in WALK]
    crouch_rows = ["................"] * 3 + top[:-0 or None] + legs(2, 2, hip, rows_total=8, coat_rows=min(coat_rows, 2))
    crouch = figure(crouch_rows[:32])
    jump = figure(top + legs(3, 3, hip, coat_rows=coat_rows))
    dead = idle.rotate(90, expand=True)
    dead = Image.eval(dead, lambda v: v)  # same colours
    px = dead.load()
    for y in range(dead.size[1]):
        for x in range(dead.size[0]):
            c = px[x, y]
            if c[3]:
                px[x, y] = (int(c[0] * 0.7), int(c[1] * 0.7), int(c[2] * 0.75), 255)
    return {"idle": [idle], "walk": walk, "crouch": [crouch], "jump": [jump], "dead": [dead]}


def portrait(top: list[str], pal: dict[str, str]) -> Image.Image:
    head = outline(from_rows(top[:16], pal))
    big = head.resize((32, 32), Image.NEAREST)
    bg = Image.new("RGBA", (32, 32), hexc("#272631"))
    bg.alpha_composite(big)
    return bg


def make_agents() -> None:
    for key, top, pal, hip, coat in (("kestrel", KESTREL_TOP, KESTREL_PAL, "PPPPPp", 0),
                                     ("marrow", MARROW_TOP, MARROW_PAL, "CCCCCc", 2)):
        frames = agent_frames(top, pal, hip, coat)
        for state, imgs in frames.items():
            im = imgs[0] if len(imgs) == 1 else strip(imgs)
            save(im, f"agents/{key}/{key}_{state}.png")
            save(enemy_variant(im) if state != "dead" else im, f"agents/{key}/{key}_{state}_feind.png")
        save(portrait(top, pal), f"agents/{key}/{key}_portrait.png")


# ------------------------------------------------------------------ weapons
GUN_SPECS: dict[str, dict[str, object]] = {
    # length in px (of 16), barrel, magazine, stock, scope, accent colour
    "spatz":    {"len": 9,  "barrel": 3, "mag": "pistol", "stock": None, "scope": False, "accent": "#6c6b75"},
    "hornisse": {"len": 9,  "barrel": 3, "mag": "pistol", "stock": None, "scope": False, "accent": "#c9a227"},
    "bulle":    {"len": 10, "barrel": 4, "mag": "drum",   "stock": None, "scope": False, "accent": "#8a5a43"},
    "stachel":  {"len": 8,  "barrel": 2, "mag": "pistol", "stock": None, "scope": False, "accent": "#a8521f"},
    "wespe":    {"len": 11, "barrel": 2, "mag": "stick",  "stock": "wire", "scope": False, "accent": "#c9a227"},
    "sirene":   {"len": 12, "barrel": 3, "mag": "stick",  "stock": "wire", "scope": False, "accent": "#4f6b73"},
    "brecher":  {"len": 14, "barrel": 6, "mag": None,     "stock": "full", "scope": False, "accent": "#7a5233"},
    "faecher":  {"len": 13, "barrel": 4, "mag": "box",    "stock": "full", "scope": False, "accent": "#a8521f"},
    "falke":    {"len": 14, "barrel": 4, "mag": "curve",  "stock": "full", "scope": False, "accent": "#5b6b3a"},
    "speer":    {"len": 15, "barrel": 5, "mag": "curve",  "stock": "full", "scope": False, "accent": "#36454c", "silencer": True},
    "hammer":   {"len": 15, "barrel": 4, "mag": "curve",  "stock": "full", "scope": False, "accent": "#7a5233"},
    "lanze":    {"len": 16, "barrel": 5, "mag": "box",    "stock": "full", "scope": True,  "accent": "#5b6b3a"},
    "elster":   {"len": 15, "barrel": 6, "mag": "box",    "stock": "full", "scope": True,  "accent": "#4f6b73"},
    "adler":    {"len": 16, "barrel": 7, "mag": "box",    "stock": "full", "scope": True,  "accent": "#2d2c31"},
    "muehle":   {"len": 15, "barrel": 4, "mag": "drum",   "stock": "full", "scope": False, "accent": "#c9a227"},
    "walze":    {"len": 16, "barrel": 5, "mag": "belt",   "stock": "full", "scope": False, "accent": "#a8521f"},
}


def draw_gun(spec: dict[str, object], w: int, h: int) -> Image.Image:
    """Side view, muzzle to the right; drawn in grid units scaled to w x h."""
    body, dark, light = hexc("#46454d"), hexc("#232228"), hexc("#6c6b75")
    accent = hexc(str(spec["accent"]))
    u = w / 16.0
    im = Image.new("RGBA", (w, h), CLEAR)
    px = im.load()

    def rect(x0: float, y0: float, x1: float, y1: float, c: Color) -> None:
        for y in range(int(y0 * h / 8), max(int(y0 * h / 8) + 1, int(y1 * h / 8))):
            for x in range(int(x0 * u), max(int(x0 * u) + 1, int(x1 * u))):
                if 0 <= x < w and 0 <= y < h:
                    px[x, y] = c

    length = int(spec["len"])  # type: ignore[arg-type]
    barrel = int(spec["barrel"])  # type: ignore[arg-type]
    start = 16 - length
    body_end = 16 - barrel
    stock = spec["stock"]
    if stock == "full":
        rect(start, 2, start + 3, 5, accent)
        rect(start, 4, start + 1, 5, darker(accent, 0.6))
    elif stock == "wire":
        rect(start, 2, start + 2, 3, dark)
        rect(start, 4, start + 2, 5, dark)
    rstart = start + (3 if stock == "full" else 2 if stock == "wire" else 0)
    rect(rstart, 2, body_end, 5, body)
    rect(rstart, 2, body_end, 3, light)
    rect(body_end, 3, 16, 4, dark)
    if spec.get("silencer"):
        rect(16 - 3, 2.5, 16, 4.5, dark)
    rect(rstart + 1, 5, rstart + 2.5, 7, dark)  # grip
    mag = spec["mag"]
    mx = rstart + 3
    if mag == "pistol":
        rect(rstart, 5, rstart + 1.6, 8, dark)
    elif mag == "stick":
        rect(mx, 5, mx + 1.2, 8, accent)
    elif mag == "curve":
        rect(mx, 5, mx + 1.4, 7, accent)
        rect(mx + 0.6, 7, mx + 2.0, 8, accent)
    elif mag == "box":
        rect(mx, 5, mx + 2, 6.5, accent)
    elif mag == "drum":
        rect(mx, 5, mx + 2.4, 7.5, accent)
    elif mag == "belt":
        rect(mx, 5, mx + 3, 7, accent)
        rect(mx + 3, 5, mx + 4, 6, hexc("#c9a227"))
    if spec["scope"]:
        rect(rstart + 1, 0.5, rstart + 5, 2, dark)
        rect(rstart + 1, 0.5, rstart + 2, 1.3, hexc("#8fb3bd"))
    return outline(im) if h >= 12 else im


def make_weapons() -> None:
    for key, spec in GUN_SPECS.items():
        save(draw_gun(spec, 16, 8), f"weapons/val2d/{key}.png")
        save(draw_gun(spec, 32, 12), f"weapons/val2d/{key}_kauf.png")
    knife = from_rows(["................", "................", "..........LLLL..", "kkkkkkLLLLLLLl..",
                       "kkkkkkLLLLLLl...", "..........ll....", "................", "................"],
                      {"k": "#3a2f25", "L": "#c7ccd2", "l": "#8a9199"})
    save(knife, "weapons/val2d/messer.png")


# ------------------------------------------------------------------ tiles
def make_tiles() -> None:
    rng = random.Random(11)
    base = hexc("#c4ae88")
    stone = Image.new("RGBA", (32, 32), base)
    px = stone.load()
    tones = [[rng.uniform(-10, 10) for _ in range(2)] for _ in range(2)]
    for row in range(2):
        off = 8 if row else 0
        for i in range(-1, 3):
            sx, sy, v = i * 16 + off, row * 16, tones[row][(i + 2) % 2]
            for y in range(sy, sy + 16):
                for x in range(sx, sx + 16):
                    if 0 <= x < 32:
                        c = tuple(int(max(0, min(255, b + v))) for b in base[:3]) + (255,)
                        if y == sy or x == sx:
                            c = lighter(c, 0.12)  # type: ignore[arg-type]
                        if y == sy + 15 or x == sx + 15:
                            c = darker(c, 0.78)  # type: ignore[arg-type]
                        px[x, y] = c
    for _ in range(16):
        x, y = rng.randrange(32), rng.randrange(32)
        px[x, y] = darker(px[x, y], 0.88) if rng.random() < 0.5 else lighter(px[x, y], 0.1)
    save(stone, "maps/werkhof/boden_stein.png")

    wall = Image.new("RGBA", (32, 32), hexc("#5c5866"))
    wp = wall.load()
    for y in range(32):
        for x in range(32):
            if 3 <= x < 29 and 3 <= y < 29:
                wp[x, y] = hexc("#67636f")
            if y == 0 or x == 0:
                wp[x, y] = hexc("#7a7684")
            if y >= 30 or x >= 30:
                wp[x, y] = hexc("#3a3743")
    for _ in range(5):
        x, y = rng.randrange(4, 28), rng.randrange(4, 24)
        for s in range(4):
            wp[x, y + s] = hexc("#4b4855")
            x += rng.choice((0, 1))
    save(wall, "maps/werkhof/wand.png")

    thin = Image.new("RGBA", (32, 32), hexc("#8a7660"))
    tp = thin.load()
    for y in range(32):
        for x in range(32):
            if x % 8 == 0:
                tp[x, y] = hexc("#6b5a48")
            if y == 0 or x == 0:
                tp[x, y] = hexc("#a08a70") if x % 8 else tp[x, y]
            if y == 31:
                tp[x, y] = hexc("#4f4235")
    save(thin, "maps/werkhof/wand_duenn.png")

    crate = Image.new("RGBA", (32, 32), hexc("#2b3c45"))
    cp = crate.load()
    for y in range(2, 30):
        for x in range(2, 30):
            cp[x, y] = hexc("#4d6a77")
    for i in range(28):
        for d in (0, 1):
            if 2 + i + d < 30:
                cp[2 + i + d, 2 + i] = hexc("#3b525d")
                cp[29 - i - d, 2 + i] = hexc("#3b525d")
    for i in range(2, 30):
        cp[i, 2] = cp[2, i] = hexc("#6d8c99")
        cp[i, 29] = cp[29, i] = hexc("#1f2c33")
    for x, y in ((4, 4), (27, 4), (4, 27), (27, 27)):
        cp[x, y] = hexc("#a9c2cc")
    save(crate, "maps/werkhof/kiste_metall.png")

    plat = Image.new("RGBA", (32, 32), hexc("#56535f"))
    pp = plat.load()
    for y in range(32):
        for x in range(32):
            if (x + y) % 6 == 0:
                pp[x, y] = hexc("#4a4753")
            if y == 0 or x == 0:
                pp[x, y] = hexc("#6e6a78")
    save(plat, "maps/werkhof/plattform.png")

    ramp = Image.new("RGBA", (32, 32), hexc("#5a5664"))
    rp = ramp.load()
    for y in range(32):
        for x in range(32):
            if y % 4 == 0:
                rp[x, y] = hexc("#6f6b79")
            if y % 4 == 3:
                rp[x, y] = hexc("#46434f")
    save(ramp, "maps/werkhof/rampe.png")

    site = Image.new("RGBA", (32, 32), CLEAR)
    sp = site.load()
    for y in range(32):
        for x in range(32):
            if (x + y) % 8 < 2 and (x < 2 or y < 2 or x > 29 or y > 29):
                sp[x, y] = (224, 180, 55, 200)
    save(site, "maps/werkhof/platz_rand.png")


# ------------------------------------------------------------------ spike, effects, icons
SPIKE_ROWS = ["................", "................", "...oooooooooo...", "...oMMMMMMMMo...", "...oMmmmmmmMo...",
              "...oMmCCCCmMo...", "...oMmCLLCmMo...", "...oMmCLLCmMo...", "...oMmCCCCmMo...", "...oMmmmmmmMo...",
              "...oYkYkYkYkYo..", "...oMMMMMMMMo...", "...oooooooooo...", "....kk....kk....", "................",
              "................"]


def make_fx() -> None:
    base = {"o": "#16151b", "M": "#6b7480", "m": "#4a525c", "C": "#24323a", "Y": "#e0b437", "k": "#1b1a1a"}
    on = from_rows(SPIKE_ROWS, {**base, "L": "#ff5a4f"})
    off = from_rows(SPIKE_ROWS, {**base, "L": "#5a2a2a"})
    save(strip([on, off]), "fx/spike.png")
    flash_rows = [
        ["........", "........", "....Y...", "...YWO..", "....O...", "........", "........", "........"],
        ["...Y....", "..YWY.Y.", "YYWWWYO.", "..YWWO..", "...OYO..", ".....O..", "........", "........"],
        ["........", "...g....", "..gGg...", "...gG...", "....g...", "........", "........", "........"],
    ]
    fpal = {"Y": "#ffd75e", "W": "#fffbe8", "O": "#f08a24", "G": "#8a8893", "g": "#5d5c66"}
    save(strip([from_rows(r, fpal) for r in flash_rows]), "fx/muendung.png")

    rng = random.Random(4)

    def disc(size: int, inner: Color, edge: Color, dither: float) -> Image.Image:
        im = Image.new("RGBA", (size, size), CLEAR)
        p = im.load()
        c = (size - 1) / 2
        for y in range(size):
            for x in range(size):
                d = math.hypot(x - c, y - c) / (size / 2)
                if d <= 1.0:
                    col = inner if d < 0.75 else edge
                    if d > 0.75 and rng.random() < dither:
                        continue
                    if d < 0.75 and (x * 7 + y * 3) % 11 == 0:
                        col = lighter(col, 0.08)  # type: ignore[arg-type]
                    p[x, y] = col
        return im

    save(disc(64, (136, 136, 152, 235), (110, 110, 126, 200), 0.35), "fx/dunst.png")
    ring = Image.new("RGBA", (64, 64), CLEAR)
    rp = ring.load()
    for y in range(64):
        for x in range(64):
            d = math.hypot(x - 31.5, y - 31.5)
            if 29 <= d <= 31.5:
                rp[x, y] = (150, 100, 200, 230)
            elif d < 29 and (x + y) % 6 == 0:
                rp[x, y] = (120, 80, 170, 90)
    save(ring, "fx/bann.png")
    vapor = Image.new("RGBA", (16, 16), CLEAR)
    vp = vapor.load()
    for y in range(4, 12):
        for x in range(16):
            if rng.random() < (0.95 if 5 <= y <= 10 else 0.5):
                vp[x, y] = (186, 196, 214, 230) if y < 8 else (150, 160, 180, 230)
    save(vapor, "fx/schleier.png")
    sensor = from_rows(["..oo..", ".oCCo.", "oCLLCo", "oCLLCo", ".oCCo.", "..oo.."],
                       {"o": "#16151b", "C": "#545c64", "L": "#8fb3bd"})
    save(sensor, "fx/lauscher.png")
    funke = Image.new("RGBA", (16, 16), CLEAR)
    fp = funke.load()
    for a in range(8):
        ang = a * math.pi / 4
        for r in range(1, 8):
            x, y = int(7.5 + math.cos(ang) * r), int(7.5 + math.sin(ang) * r)
            fp[x, y] = (255, 251, 232, 255) if r < 4 else (255, 215, 94, 255)
    save(funke, "fx/funke.png")


ICONS: dict[str, list[str]] = {
    "kestrel_C": ["................", ".......W........", "...W...W...W....", "....W..W..W.....", ".....WWWWW......", "..WWWWYYYWWWW...", ".....WWWWW......", "....W..W..W.....", "...W...W...W....", ".......W........", "................", "................", "................", "................", "................", "................"],
    "kestrel_Q": ["................", ".......W........", "......WWW.......", ".....WWWWW......", "....WW.W.WW.....", ".......W........", ".......W........", ".......W........", ".....YYYYY......", "....YYYYYYY.....", "................", "................", "................", "................", "................", "................"],
    "kestrel_E": ["................", "................", "..W.....WW......", ".W.....WWWW.....", "W.....WWWWWW....", "WWWWWWWWWWWWW...", "W.....WWWWWW....", ".W.....WWWW.....", "..W.....WW......", "................", "................", "................", "................", "................", "................", "................"],
    "kestrel_X": ["................", "......YYY.......", ".....YWWWY......", "....YWWWWWY.....", "....YWWYWWY.....", "....YWWYWWY.....", "....YWWWWWY.....", ".....YWWWY......", "......YYY.......", "................", "................", "................", "................", "................", "................", "................"],
    "marrow_C": ["................", "......WWW.......", ".....W...W......", "....W..W..W.....", "....W.WWW.W.....", "....W..W..W.....", ".....W...W......", "......WWW.......", ".......W........", "......WWW.......", "................", "................", "................", "................", "................", "................"],
    "marrow_Q": ["................", "..W..W..W..W....", "..W..W..W..W....", "..WWWWWWWWWW....", "..WWWWWWWWWW....", "..W..W..W..W....", "..W..W..W..W....", "................", "................", "................", "................", "................", "................", "................", "................", "................"],
    "marrow_E": ["................", ".....WWWW.......", "...WWWWWWWW.....", "..WWWWWWWWWW....", "..WWWWWWWWWW....", "..WWWWWWWWWW....", "...WWWWWWWW.....", ".....WWWW.......", "................", "................", "................", "................", "................", "................", "................", "................"],
    "marrow_X": ["................", "....YYYYYY......", "...Y......Y.....", "..Y..WWWW..Y....", "..Y.W....W.Y....", "..Y.W.WW.W.Y....", "..Y.W....W.Y....", "..Y..WWWW..Y....", "...Y......Y.....", "....YYYYYY......", "................", "................", "................", "................", "................", "................"],
}


def make_icons() -> None:
    pal = {"W": "#e8e6ef", "Y": "#e0b437"}
    for key, rows in ICONS.items():
        rows = [r.ljust(16, ".")[:16] for r in rows]
        save(from_rows(rows, pal), f"ui/faehigkeit_{key}.png")


HUD_ICONS: dict[str, tuple[list[str], dict[str, str]]] = {
    "leben": (["..WW....", "..WW....", "WWWWWW..", "WWWWWW..", "..WW....", "..WW....", "........", "........"], {"W": "#e8e6ef"}),
    "schild": (["SSSSSS..", "SsSSsS..", "SSSSSS..", "SSSSSS..", ".SSSS...", "..SS....", "........", "........"], {"S": "#8fb3bd", "s": "#4f6b73"}),
    "credits": (["..YYY...", ".YyyyY..", "YyYYyY..", "YyYYyY..", ".YyyyY..", "..YYY...", "........", "........"], {"Y": "#e0b437", "y": "#a8821f"}),
    "munition": (["..Y.....", ".YYY....", ".WWW....", ".WWW....", ".WWW....", ".WWW....", ".ggg....", "........"], {"Y": "#e0b437", "W": "#c7ccd2", "g": "#8a9199"}),
    "kopfschuss": (["..WWW...", ".W...W..", "W.W.W.W.", "W.....W.", ".W.W.W..", "..WWW...", "........", "........"], {"W": "#ee4c4a"}),
    "spike_klein": (["oooooo..", "oMLLMo..", "oMLLMo..", "oYkYko..", "oooooo..", "........", "........", "........"], {"o": "#16151b", "M": "#6b7480", "L": "#ff5a4f", "Y": "#e0b437", "k": "#1b1a1a"}),
    "uhr": (["..WWW...", ".W.W.W..", "W..W..W.", "W..WW.W.", "W.....W.", ".W...W..", "..WWW...", "........"], {"W": "#e8e6ef"}),
    "tot": ([".WWWW...", "WWWWWW..", "W.WW.W..", "WWWWWW..", ".W.W.W..", "........", "........", "........"], {"W": "#9b98aa"}),
}


def panel(size: int, fill: str, edge: str, light: str) -> Image.Image:
    """Nine-slice frame: 4 px corners, stretchable centre (bars and buy menu)."""
    im = Image.new("RGBA", (size, size), CLEAR)
    p = im.load()
    for y in range(size):
        for x in range(size):
            corner = (x < 2 and y < 2) or (x >= size - 2 and y < 2) or (x < 2 and y >= size - 2) or (x >= size - 2 and y >= size - 2)
            if corner and not ((x in (1, size - 2)) and (y in (1, size - 2))):
                continue
            if x == 0 or y == 0 or x == size - 1 or y == size - 1 or (x in (1, size - 2) and y in (1, size - 2)):
                p[x, y] = hexc(edge)
            elif x == 1 or y == 1:
                p[x, y] = hexc(light)
            else:
                p[x, y] = hexc(fill)
    return im


def bar(width: int, fill: str, shade: str) -> Image.Image:
    im = Image.new("RGBA", (width, 6), CLEAR)
    p = im.load()
    for x in range(width):
        for y in range(6):
            if y in (0, 5) or x in (0, width - 1):
                p[x, y] = hexc("#16151b")
            else:
                p[x, y] = hexc(fill) if y < 3 else hexc(shade)
    return im


def make_hud() -> None:
    for key, (rows, pal) in HUD_ICONS.items():
        save(from_rows(rows, pal), f"ui/hud/{key}.png")
    save(panel(12, "#1f1e27", "#0e0d12", "#2f2d3a"), "ui/hud/rahmen.png")
    save(panel(12, "#2a2933", "#4fd6c8", "#3a3846"), "ui/hud/rahmen_aktiv.png")
    save(bar(48, "#e8e6ef", "#9b98aa"), "ui/hud/balken_leben.png")
    save(bar(48, "#8fb3bd", "#4f6b73"), "ui/hud/balken_schild.png")
    save(bar(48, "#e0b437", "#a8821f"), "ui/hud/balken_fortschritt.png")
    save(bar(48, "#3a3846", "#2a2933"), "ui/hud/balken_leer.png")


MINIMAP: dict[str, tuple[list[str], dict[str, str]]] = {
    "selbst": (["...W....", "..WWW...", ".WWWWW..", "WWWWWWW.", "..WWW...", "..WWW...", "........", "........"], {"W": "#e8e6ef"}),
    "verbuendet": (["..CCC...", ".CcccC..", "CcccccC.", "CcccccC.", ".CcccC..", "..CCC...", "........", "........"], {"C": "#16151b", "c": "#4fd6c8"}),
    "feind": (["..RRR...", ".RrrrR..", "RrrrrrR.", "RrrrrrR.", ".RrrrR..", "..RRR...", "........", "........"], {"R": "#16151b", "r": "#ee4c4a"}),
    "tot": (["r.....r.", ".r...r..", "..r.r...", "...r....", "..r.r...", ".r...r..", "r.....r.", "........"], {"r": "#9b98aa"}),
    "spike": (["oooooo..", "oYLLYo..", "oYLLYo..", "oooooo..", "........", "........", "........", "........"], {"o": "#16151b", "Y": "#e0b437", "L": "#ff5a4f"}),
    "dunst": (["..ggg...", ".gGGGg..", "gGGGGGg.", "gGGGGGg.", ".gGGGg..", "..ggg...", "........", "........"], {"g": "#6e6e80", "G": "#9a9aac"}),
    "bann": (["..ppp...", ".p...p..", "p.....p.", "p.....p.", ".p...p..", "..ppp...", "........", "........"], {"p": "#9664c8"}),
    "schleier": (["........", "........", "WWWWWWW.", "wwwwwww.", "........", "........", "........", "........"], {"W": "#bac4d6", "w": "#8a94a6"}),
}

FONT5: dict[str, list[str]] = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "Ä": [".#.#.", ".....", ".###.", "#...#", "#####", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".####", "#....", "#....", "#....", "#....", "#....", ".####"],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".####", "#....", "#....", "#..##", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["###", ".#.", ".#.", ".#.", ".#.", ".#.", "###"],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", ".#.#.", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    " ": ["..", "..", "..", "..", "..", "..", ".."],
}

BANNERS = {
    "sieg": ("VICTORY", "#4fd6c8"),
    "niederlage": ("DEFEAT", "#ee4c4a"),
    "seitenwechsel": ("SWITCHING SIDES", "#e0b437"),
    "spike_gelegt": ("BOMB PLANTED", "#ee4c4a"),
    "entschaerft": ("BOMB DEFUSED", "#4fd6c8"),
    "verlaengerung": ("OVERTIME", "#e0b437"),
}


def text_image(text: str, color: str, shadow: str) -> Image.Image:
    glyphs = [FONT5[ch] for ch in text]
    width = sum(len(g[0]) + 1 for g in glyphs) + 1
    im = Image.new("RGBA", (width, 9), CLEAR)
    p = im.load()
    x0 = 0
    for g in glyphs:
        for y, row in enumerate(g):
            for x, bit in enumerate(row):
                if bit == "#":
                    p[x0 + x + 1, y + 1] = hexc(shadow)
        for y, row in enumerate(g):
            for x, bit in enumerate(row):
                if bit == "#":
                    p[x0 + x, y] = hexc(color) if y < 4 else darker(hexc(color), 0.8)
        x0 += len(g[0]) + 1
    return im


def banner(text: str, accent: str) -> Image.Image:
    t = text_image(text, "#e8e6ef", "#0e0d12")
    w, h = t.width + 24, 21
    im = Image.new("RGBA", (w, h), CLEAR)
    p = im.load()
    for y in range(h):
        inset = 0 if 2 <= y <= h - 3 else (1 if y in (1, h - 2) else 2)
        for x in range(inset, w - inset):
            edge = y in (0, h - 1) or x in (inset, w - inset - 1)
            p[x, y] = hexc("#0e0d12") if edge else hexc("#1f1e27")
    for x in range(3, w - 3):
        p[x, 2] = hexc(accent)
        p[x, h - 3] = darker(hexc(accent), 0.6)
    for y in range(4, h - 4):
        p[3, y] = p[w - 4, y] = hexc(accent)
    im.alpha_composite(t, (12, 6))
    return im


def make_minimap_and_banners() -> None:
    for key, (rows, pal) in MINIMAP.items():
        save(from_rows(rows, pal), f"ui/minimap/{key}.png")
    for key, (text, accent) in BANNERS.items():
        save(banner(text, accent), f"ui/banner/{key}.png")


def _set(rows: list[str], y: int, x: int, ch: str) -> None:
    r = list(rows[y])
    r[x] = ch
    rows[y] = "".join(r)


def _hands_off(top: list[str]) -> list[str]:
    rows = list(top)
    for y in (18, 19):
        for x in (2, 3, 12, 13):
            _set(rows, y, x, ".")
    return rows


def action_frames(top: list[str], pal: dict[str, str], hip: str, coat: int, glow: str) -> dict[str, list[Image.Image]]:
    """Shoot (2), reload (4), cast (3). The game draws weapon and muzzle flash separately."""
    pal = {**pal, "*": glow}
    base_legs = legs(5, 5, hip, coat_rows=coat)

    def fig(rows: list[str]) -> Image.Image:
        return outline(from_rows(rows + base_legs, pal))

    # shoot: recoil, upper body 1 px lower
    recoil = ["................"] + top[:-1]
    shoot = [fig(top), fig(recoil)]
    # reload: hands to the belt and back
    r1 = _hands_off(top)
    for x, ch in ((4, "S"), (11, "s")):
        _set(r1, 17, x, ch)
    r2 = _hands_off(top)
    for x, ch in ((6, "S"), (7, "S"), (8, "S"), (9, "s")):
        _set(r2, 16, x, ch)
    reload = [fig(top), fig(r1), fig(r2), fig(r1)]
    # cast: right hand up, glow
    c1 = list(top)
    for y in (18, 19):
        _set(c1, y, 12, ".")
        _set(c1, y, 13, ".")
    _set(c1, 13, 14, "S")
    c2 = list(c1)
    _set(c2, 13, 14, ".")
    _set(c2, 10, 14, "S")
    _set(c2, 9, 14, "*")
    _set(c2, 9, 15, "*")
    _set(c2, 8, 14, "*")
    cast = [fig(c1), fig(c2), fig(c1)]
    return {"shoot": shoot, "reload": reload, "cast": cast}


def make_agent_actions() -> None:
    for key, top, pal, hip, coat, glow in (("kestrel", KESTREL_TOP, KESTREL_PAL, "PPPPPp", 0, "#ffd75e"),
                                           ("marrow", MARROW_TOP, MARROW_PAL, "CCCCCc", 2, "#bac4d6")):
        for state, frames in action_frames(top, pal, hip, coat, glow).items():
            im = strip(frames)
            save(im, f"agents/{key}/{key}_{state}.png")
            save(enemy_variant(im), f"agents/{key}/{key}_{state}_feind.png")


def make_fx_anims() -> None:
    rng = random.Random(9)

    def blank(w: int, h: int) -> Image.Image:
        return Image.new("RGBA", (w, h), CLEAR)

    def disc(size: int, frac: float, inner: Color, edge: Color, dither: float) -> Image.Image:
        im = blank(size, size)
        p = im.load()
        c = (size - 1) / 2
        rad = size / 2 * frac
        for y in range(size):
            for x in range(size):
                d = math.hypot(x - c, y - c)
                if d <= rad:
                    if d > rad * 0.75 and rng.random() < dither:
                        continue
                    p[x, y] = inner if d < rad * 0.75 else edge
        return im

    save(strip([disc(64, f, (136, 136, 152, 235), (110, 110, 126, 200), 0.4) for f in (0.35, 0.6, 0.82, 1.0)]), "fx/dunst_aufbau.png")

    def ring(size: int, r0: float, r1: float, col: Color, fill_alpha: int) -> Image.Image:
        im = blank(size, size)
        p = im.load()
        c = (size - 1) / 2
        for y in range(size):
            for x in range(size):
                d = math.hypot(x - c, y - c)
                if r0 <= d <= r1:
                    p[x, y] = col
                elif d < r0 and fill_alpha and (x + y) % 6 == 0:
                    p[x, y] = col[:3] + (fill_alpha,)
        return im

    save(strip([ring(64, 29 - i, 31.5, (150, 100, 200, 230 - i * 40), 90 - i * 25) for i in range(3)]), "fx/bann_puls.png")
    save(strip([ring(32, r, r + 1.5, (143, 179, 189, 220 - i * 60), 0) for i, r in enumerate((4, 9, 14))]), "fx/lauscher_puls.png")

    def burst(size: int, length: int, core: Color, tip: Color) -> Image.Image:
        im = blank(size, size)
        p = im.load()
        c = (size - 1) / 2
        for a in range(8):
            ang = a * math.pi / 4
            for r in range(0, length):
                x, y = int(c + math.cos(ang) * r), int(c + math.sin(ang) * r)
                if 0 <= x < size and 0 <= y < size:
                    p[x, y] = core if r < length / 2 else tip
        return im

    save(strip([burst(16, 3, (255, 251, 232, 255), (255, 215, 94, 255)), burst(16, 8, (255, 251, 232, 255), (255, 215, 94, 255)),
                burst(16, 8, (255, 251, 232, 120), (255, 215, 94, 90))]), "fx/funke_explosion.png")

    trail = []
    for i in range(3):
        im = blank(16, 32)
        p = im.load()
        alpha = 200 - i * 70
        for y in range(4, 30, 2):
            for x in (1, 14) if i < 2 else (3, 12):
                if rng.random() < 0.8:
                    p[x, y] = (255, 251, 232, alpha)
        trail.append(im)
    save(strip(trail), "fx/gleiten_spur.png")

    dust = []
    for i in range(3):
        im = blank(16, 8)
        p = im.load()
        for _ in range(10 + i * 4):
            x = int(8 + rng.gauss(0, 2 + i * 1.5))
            y = int(6 - abs(rng.gauss(0, 1 + i)))
            if 0 <= x < 16 and 0 <= y < 8:
                p[x, y] = (196, 174, 136, 220 - i * 60)
        dust.append(im)
    save(strip(dust), "fx/satz_staub.png")

    veil = []
    for dens in (0.3, 0.65, 0.95):
        im = blank(16, 16)
        p = im.load()
        for y in range(4, 12):
            for x in range(16):
                if rng.random() < dens * (1.0 if 5 <= y <= 10 else 0.5):
                    p[x, y] = (186, 196, 214, 230) if y < 8 else (150, 160, 180, 230)
        veil.append(im)
    save(strip(veil), "fx/schleier_aufbau.png")

    boom = []
    for i, frac in enumerate((0.2, 0.45, 0.7, 0.9, 1.0, 1.0)):
        im = blank(64, 64)
        p = im.load()
        rad = 32 * frac
        for y in range(64):
            for x in range(64):
                d = math.hypot(x - 31.5, y - 31.5)
                if d > rad:
                    continue
                if i < 4:
                    col = (255, 251, 232, 255) if d < rad * 0.4 else (255, 215, 94, 255) if d < rad * 0.7 else (240, 138, 36, 240)
                elif i == 4:
                    col = (240, 138, 36, 200) if d > rad * 0.6 else (93, 92, 102, 220)
                else:
                    if rng.random() < 0.5:
                        continue
                    col = (93, 92, 102, 160)
                p[x, y] = col
        boom.append(im)
    save(strip(boom), "fx/spike_explosion.png")

    wall_hit = [from_rows(r, {"W": "#fffbe8", "Y": "#ffd75e", "g": "#8a8893"}) for r in (
        ["........", "........", "...W....", "..WYW...", "...W....", "........", "........", "........"],
        ["........", ".Y...Y..", "..Y.Y...", "...W....", "..Y.Y...", ".g...g..", "........", "........"],
        ["........", "........", "..g.g...", "...g....", "..g.g...", "........", "........", "........"])]
    save(strip(wall_hit), "fx/einschlag_wand.png")
    body_hit = [from_rows(r, {"R": "#ee4c4a", "r": "#a8322f", "W": "#ffffff"}) for r in (
        ["........", "........", "...R....", "..RWR...", "...R....", "........", "........", "........"],
        ["........", ".R...R..", "..r.r...", "...W....", "..r.r...", ".R...R..", "........", "........"],
        ["........", "........", "..r.r...", "........", "..r.r...", "........", "........", "........"])]
    save(strip(body_hit), "fx/treffer_koerper.png")


def main() -> None:
    make_agents()
    make_agent_actions()
    make_fx_anims()
    make_weapons()
    make_tiles()
    make_fx()
    make_icons()
    make_hud()
    make_minimap_and_banners()


if __name__ == "__main__":
    main()
