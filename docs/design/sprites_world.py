"""Third sprite batch: interface (menus, buttons, icons), map set (tiles, props, decals)
and generic ability sprites (projectiles, devices, character effects). All original designs.

Usage: python docs/design/sprites_world.py
Output: assets/ui/menu, assets/ui/icons, assets/ui/buy, assets/maps/common, assets/fx/ability
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sprites as base  # noqa: E402

hexc, darker, lighter, save, strip, from_rows, outline = (
    base.hexc, base.darker, base.lighter, base.save, base.strip, base.from_rows, base.outline)
CLEAR = base.CLEAR
INK = "#0e0d12"
TEAL, RED, GOLD = "#4fd6c8", "#ee4c4a", "#e0b437"
WHITE = "#e8e6ef"


def blank(w: int, h: int) -> Image.Image:
    return Image.new("RGBA", (w, h), CLEAR)


def rect(im: Image.Image, x0: int, y0: int, x1: int, y1: int, c) -> None:
    """Inclusive rectangle fill; c is hex or RGBA tuple."""
    col = hexc(c) if isinstance(c, str) else c
    p = im.load()
    for y in range(max(0, y0), min(im.height, y1 + 1)):
        for x in range(max(0, x0), min(im.width, x1 + 1)):
            p[x, y] = col


def glyph(rows: list[str], pal: dict[str, str]) -> Image.Image:
    w = max(len(r) for r in rows)
    return from_rows([r.ljust(w, ".") for r in rows], pal)


# ================================================================== interface
def nine(size: int, corner: int, fill: str, edge: str, light: str, shadow: str, inset: str | None = None) -> Image.Image:
    im = blank(size, size)
    p = im.load()
    for y in range(size):
        for x in range(size):
            if (x in (0, size - 1)) and (y in (0, size - 1)):
                continue
            if x in (0, size - 1) or y in (0, size - 1):
                p[x, y] = hexc(edge)
            elif y == 1:
                p[x, y] = hexc(light)
            elif y == size - 2:
                p[x, y] = hexc(shadow)
            else:
                p[x, y] = hexc(fill)
    if inset:
        for i in range(corner, size - corner):
            p[i, 2] = hexc(inset)
    return im


def make_menu() -> None:
    btn = {
        "button": ("#2a2933", INK, "#3a3846", "#1b1a22"),
        "button_hover": ("#34323e", TEAL, "#46434f", "#22212a"),
        "button_pressed": ("#1f1e27", INK, "#1b1a22", "#3a3846"),
        "button_disabled": ("#232229", "#2d2c35", "#2a2930", "#1f1e25"),
    }
    for name, (fill, edge, light, shadow) in btn.items():
        save(nine(16, 4, fill, edge, light, shadow), f"ui/menu/{name}.png")
    save(nine(24, 6, "#1f1e27", INK, "#2f2d3a", "#17161d", inset="#2a2833"), "ui/menu/panel.png")
    save(nine(16, 4, "#121118", "#2d2c35", "#0e0d12", "#3a3846"), "ui/menu/textfield.png")
    save(nine(16, 4, "#232229", INK, "#2f2d3a", "#1b1a22"), "ui/menu/tab.png")
    tab_on = nine(16, 4, "#2f2d3a", INK, "#46434f", "#2f2d3a")
    rect(tab_on, 2, 14, 13, 14, TEAL)
    save(tab_on, "ui/menu/tab_active.png")
    # checkbox and slider
    box = nine(8, 2, "#121118", "#46434f", "#0e0d12", "#2d2c35")
    save(box, "ui/menu/checkbox.png")
    on = box.copy()
    for x, y in ((2, 4), (3, 5), (4, 4), (5, 3), (5, 2)):
        on.load()[x, y] = hexc(TEAL)
    save(on, "ui/menu/checkbox_on.png")
    track = nine(16, 2, "#121118", "#2d2c35", "#0e0d12", "#2a2933")
    save(track.resize((16, 16)).crop((0, 5, 16, 11)), "ui/menu/slider_track.png")
    fill = blank(16, 6)
    rect(fill, 1, 1, 14, 2, TEAL)
    rect(fill, 1, 3, 14, 4, darker(hexc(TEAL), 0.7))
    save(fill, "ui/menu/slider_fill.png")
    knob = glyph(["..oo..", ".oWWo.", "oWWWso", "oWWWso", ".osso.", "..oo.."], {"o": INK, "W": WHITE, "s": "#9b98aa"})
    save(knob, "ui/menu/slider_knob.png")
    # mouse cursor
    cursor = glyph(["o...........", "oo..........", "oWo.........", "oWWo........", "oWWWo.......", "oWWWWo......",
                    "oWWWWWo.....", "oWWWWWWo....", "oWWWWoooo...", "oWWoWo......", "oWo.oWo.....", "oo..oWo.....",
                    ".....oo....."], {"o": INK, "W": WHITE})
    save(cursor, "ui/menu/cursor.png")
    make_title_background()


def make_title_background() -> None:
    """480x270 menu background: an abstract top-down yard at night, original."""
    rng = random.Random(5)
    w, h = 480, 270
    im = Image.new("RGBA", (w, h), hexc("#16151c"))
    p = im.load()
    for y in range(0, h, 32):
        for x in range(0, w, 32):
            tone = rng.choice((0, 2, 4))
            rect(im, x, y, x + 31, y + 31, (26 + tone, 25 + tone, 33 + tone, 255))
            for i in range(32):
                if x + i < w and y < h:
                    p[x + i, y] = (31, 30, 39, 255)
                if y + i < h and x < w:
                    p[x, y + i] = (31, 30, 39, 255)
    for _ in range(9):  # walls
        x, y = rng.randrange(0, w - 120), rng.randrange(0, h - 20)
        horizontal = rng.random() < 0.6
        x1, y1 = (x + rng.randrange(60, 160), y + 7) if horizontal else (x + 7, y + rng.randrange(40, 110))
        rect(im, x, y, x1, y1, "#3a3743")
        rect(im, x, y, x1, y, "#4b4855")
    for _ in range(14):  # crates
        x, y = rng.randrange(0, w - 16), rng.randrange(0, h - 16)
        rect(im, x, y, x + 15, y + 15, "#2b3c45")
        rect(im, x + 1, y + 1, x + 14, y + 14, "#36505c")
        rect(im, x + 1, y + 1, x + 14, y + 1, "#4d6a77")
    cx, cy = 330, 240  # view cone, teal and faint
    for y in range(h):
        for x in range(w):
            dx, dy = x - cx, cy - y
            if dy > 0 and abs(math.atan2(dx, dy)) < 0.75 and math.hypot(dx, dy) < 230:
                r, g, b, a = p[x, y]
                f = 1 - math.hypot(dx, dy) / 230
                p[x, y] = (int(r + (79 - r) * 0.10 * f), int(g + (214 - g) * 0.10 * f), int(b + (200 - b) * 0.10 * f), 255)
    for y in range(h):  # vignette on the left for the menu buttons
        for x in range(0, 200):
            r, g, b, a = p[x, y]
            f = 0.55 + 0.45 * x / 200
            p[x, y] = (int(r * f), int(g * f), int(b * f), 255)
    save(im, "ui/menu/title_background.png")


ICONS8: dict[str, list[str]] = {
    "close": ["W.....W.", ".W...W..", "..W.W...", "...W....", "..W.W...", ".W...W..", "W.....W.", "........"],
    "arrow_left": ["...W....", "..WW....", ".WWWWWW.", "WWWWWWW.", ".WWWWWW.", "..WW....", "...W....", "........"],
    "arrow_right": ["....W...", "....WW..", "WWWWWW..", "WWWWWWW.", "WWWWWW..", "....WW..", "....W...", "........"],
    "arrow_up": ["...W....", "..WWW...", ".WWWWW..", "WWWWWWW.", "..WWW...", "..WWW...", "..WWW...", "........"],
    "arrow_down": ["..WWW...", "..WWW...", "..WWW...", "WWWWWWW.", ".WWWWW..", "..WWW...", "...W....", "........"],
    "check": ["........", "......W.", ".....WW.", "W...WW..", "WW.WW...", ".WWW....", "..W.....", "........"],
    "plus": ["...W....", "...W....", "...W....", "WWWWWWW.", "...W....", "...W....", "...W....", "........"],
    "minus": ["........", "........", "........", "WWWWWWW.", "........", "........", "........", "........"],
    "lock": ["..WWW...", ".W...W..", ".W...W..", "WWWWWWW.", "WWW.WWW.", "WWW.WWW.", "WWWWWWW.", "........"],
    "gear": ["..W.W...", ".WWWWW..", "WWW.WWW.", "WW...WW.", "WWW.WWW.", ".WWWWW..", "..W.W...", "........"],
    "sound_on": ["...W....", "..WW..W.", "WWWW.W..", "WWWW.W.W", "WWWW.W..", "..WW..W.", "...W....", "........"],
    "sound_off": ["...W....", "..WW....", "WWWW.R.R", "WWWW..R.", "WWWW.R.R", "..WW....", "...W....", "........"],
    "mic": ["..WWW...", "..WWW...", "..WWW...", ".WWWWW..", ".W.W.W..", "...W....", "..WWW...", "........"],
    "person": ["..WWW...", "..WWW...", "...W....", ".WWWWW..", "W.WWW.W.", "..W.W...", "..W.W...", "........"],
    "trophy": ["WWWWWWW.", "W.WWW.W.", ".WWWWW..", "..WWW...", "...W....", "..WWW...", ".WWWWW..", "........"],
    "skull": [".WWWWW..", "WWWWWWW.", "W..W..W.", "WWWWWWW.", ".WW.WW..", ".W.W.W..", "........", "........"],
}


def make_icons() -> None:
    for name, rows in ICONS8.items():
        save(glyph(rows, {"W": WHITE, "R": RED}), f"ui/icons/{name}.png")
    for level in range(4):
        im = blank(8, 8)
        for i in range(4):
            col = (TEAL if level >= 2 else GOLD if level == 1 else RED) if i < max(level, 1) else "#3a3846"
            rect(im, i * 2, 6 - i * 2, i * 2, 6, col)
        save(im, f"ui/icons/ping_{level}.png")
    pips = {"round_win": TEAL, "round_loss": RED, "round_empty": "#3a3846"}
    for name, col in pips.items():
        im = glyph([".oooo.", "oCCCCo", "oCCCCo", "oCCCCo", "oCCCCo", ".oooo."], {"o": INK, "C": col})
        save(im, f"ui/icons/{name}.png")
    coin = glyph(["...oooooo...", "..oYYYYYYo..", ".oYyyyyyyYo.", "oYyYYYYYYyYo", "oYyYyyyyyyYo", "oYyYYYYYyyYo",
                  "oYyyyyyYYyYo", "oYyYYYYYYyYo", ".oYyyyyyyYo.", "..oYYYYYYo..", "...oooooo...", "............"],
                 {"o": "#6b5410", "Y": GOLD, "y": "#a8821f"})
    save(coin, "ui/icons/credits_large.png")
    roles = {
        "role_duelist": ["......WW........", ".....WW.........", "....WW..........", "...WWWWWW.......", ".......WW.......",
                         "......WW........", ".....WW.........", "....W..........."],
        "role_initiator": ["....WWWWWW......", "..WW......WW....", ".W...WWWW...W...", "W...W.YY.W...W..", ".W...WWWW...W...",
                           "..WW......WW....", "....WWWWWW......", "................"],
        "role_controller": ["....WWWW........", "..WWWWWWWW......", ".WWWWWWWWWW.....", "WWWWWWWWWWWW....", "WWWWWWWWWWWW....",
                            ".WWWWWWWWWW.....", "..WWWWWWWW......", "................"],
        "role_sentinel": ["WWWWWWWWWW......", "WYWWWWWWYW......", "WWWWWWWWWW......", "WWWWWWWWWW......", ".WWWWWWWW.......",
                          "..WWWWWW........", "....WW..........", "................"],
    }
    for name, rows in roles.items():
        im = blank(16, 16)
        im.alpha_composite(glyph(rows, {"W": WHITE, "Y": GOLD}), (2, 4))
        save(im, f"ui/icons/{name}.png")
    sides = {
        "side_attack": ["......WW........", ".....WWWW.......", "....WWWWWW......", "...WW.WW.WW.....", "......WW........",
                        "......WW........", "....WWWWWW......", "................"],
        "side_defense": ["WWWWWWWWWWW.....", "W.........W.....", "W..WWWWW..W.....", "W..W...W..W.....", ".W.WWWWW.W......",
                         "..W.....W.......", "....WWW.........", "................"],
    }
    for name, rows in sides.items():
        im = blank(16, 16)
        im.alpha_composite(glyph(rows, {"W": GOLD}), (2, 4))
        save(im, f"ui/icons/{name}.png")


def make_buy() -> None:
    cats = {
        "cat_sidearm": ["..........", "WWWWWWWWW.", "WWWWWWWWWW", "WWW.......", "WW........", "WW........"],
        "cat_smg": ["............", ".WWWWWWWWWW.", "WWWWWWWWWWWW", "W..WW.W.....", "...WW.W.....", "......W....."],
        "cat_shotgun": ["..............", "WWWWWWWWWWWWWW", "WWWWWWWWWWWWW.", "WWW.WW........", "WW..W.........", "..............."],
        "cat_rifle": ["....WWWW......", "WWWWWWWWWWWWWW", "WWWWWWWWWWW...", "WWW.WW.W......", "WW...W.W......", "........W....."],
        "cat_sniper": ["....WWWWW.....", "WWWWWWWWWWWWWW", "WWWWWWWWW.....", "WWW.WW........", "WW............", ".............."],
        "cat_heavy": ["..............", "WWWWWWWWWWWWWW", "WWWWWWWWWWWW..", "WWW.WWWW......", "WW..WWWW......", "....WWWW......"],
        "cat_armor": ["..WW..WW..", ".WWWWWWWW.", "WWWWWWWWWW", "WWWYYYYWWW", "WWWWWWWWWW", ".WWWWWWWW."],
        "cat_abilities": ["....W.....", "...WWW....", "WWWWWWWWW.", ".WWWWWWW..", "..WW.WW...", ".W.....W.."],
    }
    for name, rows in cats.items():
        im = blank(16, 16)
        g = glyph(rows, {"W": WHITE, "Y": GOLD})
        im.alpha_composite(g, ((16 - g.width) // 2, (16 - g.height) // 2))
        save(im, f"ui/buy/{name}.png")
    for name, plate, trim in (("vest_light", "#6b7480", "#8fb3bd"), ("vest_heavy", "#4a525c", GOLD)):
        rows = ["..........................", "......SS..........SS......", ".....SSSSSSSSSSSSSSSS.....",
                "....SPPPPPPPPPPPPPPPPS....", "....SPPPPPPPPPPPPPPPPS....", "....SPPTTPPPPPPPPTTPPS....",
                "....SPPPPPPPPPPPPPPPPS....", "....SPPPPPPPPPPPPPPPPS....", "....SPPPPPPPPPPPPPPPPS....",
                ".....SPPPPPPPPPPPPPPS.....", "......SSSSSSSSSSSSSS......", ".........................."]
        if name == "vest_heavy":
            rows[6] = "....SPPTTTTTTTTTTTTPPS...."
        im = blank(32, 12)
        im.alpha_composite(outline(glyph(rows, {"S": "#2d2c31", "P": plate, "T": trim})), (3, 0))
        save(im, f"ui/buy/{name}.png")


# ================================================================== map set
def noise_tile(base_hex: str, speckle: int, seed: int, light: float = 0.1, shade: float = 0.82) -> Image.Image:
    rng = random.Random(seed)
    im = Image.new("RGBA", (32, 32), hexc(base_hex))
    p = im.load()
    for _ in range(speckle):
        x, y = rng.randrange(32), rng.randrange(32)
        p[x, y] = darker(p[x, y], shade) if rng.random() < 0.5 else lighter(p[x, y], light)
    return im


def edge_light(im: Image.Image, light: float = 0.12, shade: float = 0.78) -> Image.Image:
    p = im.load()
    for i in range(32):
        p[i, 0] = lighter(p[i, 0], light)
        p[0, i] = lighter(p[0, i], light)
        p[i, 31] = darker(p[i, 31], shade)
        p[31, i] = darker(p[31, i], shade)
    return im


def make_tiles() -> None:
    rng = random.Random(3)
    t = "maps/common/"
    save(edge_light(noise_tile("#7d7a80", 18, 1)), t + "floor_concrete.png")
    grate = Image.new("RGBA", (32, 32), hexc("#2d2c31"))
    g = grate.load()
    for y in range(32):
        for x in range(32):
            if x % 4 == 0 or y % 4 == 0:
                g[x, y] = hexc("#5a5f66") if (x % 4 == 0) != (y % 4 == 0) else hexc("#6b7480")
    save(edge_light(grate), t + "floor_grate.png")
    tiles = Image.new("RGBA", (32, 32), hexc("#a8a59c"))
    tp = tiles.load()
    for y in range(32):
        for x in range(32):
            if (x // 8 + y // 8) % 2:
                tp[x, y] = hexc("#96938a")
            if x % 8 == 0 or y % 8 == 0:
                tp[x, y] = hexc("#7d7a72")
    save(edge_light(tiles), t + "floor_tiles.png")
    save(edge_light(noise_tile("#c9b07a", 40, 4, 0.12, 0.85)), t + "floor_sand.png")
    save(edge_light(noise_tile("#6b5236", 40, 5, 0.1, 0.8)), t + "floor_dirt.png")
    cracked = Image.open(base.ASSETS / "maps/werkhof/boden_stein.png").convert("RGBA")
    cp = cracked.load()
    x, y = 6, 4
    for _ in range(22):
        cp[x, y] = darker(cp[x, y], 0.6)
        x = max(1, min(30, x + rng.choice((0, 1, 1))))
        y = max(1, min(30, y + rng.choice((1, 1, 0))))
    save(cracked, t + "floor_stone_cracked.png")
    brick = Image.new("RGBA", (32, 32), hexc("#7a4a36"))
    bp = brick.load()
    for y in range(32):
        for x in range(32):
            row = y // 6
            if y % 6 == 5 or (x + (8 if row % 2 else 0)) % 16 == 15:
                bp[x, y] = hexc("#4a2e22")
            elif y % 6 == 0:
                bp[x, y] = hexc("#8f5a43")
    save(edge_light(brick), t + "wall_brick.png")
    concrete = noise_tile("#5f5c63", 14, 7)
    rect(concrete, 3, 3, 28, 28, "#69666e")
    save(edge_light(concrete, 0.14, 0.7), t + "wall_concrete.png")
    fence = blank(32, 32)
    for x in range(32):
        for y in range(32):
            if x % 8 in (1, 2, 3, 4, 5, 6):
                fence.load()[x, y] = hexc("#9a7a52") if x % 8 != 6 else hexc("#6b5236")
    rect(fence, 0, 6, 31, 7, "#5a4430")
    rect(fence, 0, 24, 31, 25, "#5a4430")
    save(fence, t + "fence_wood.png")
    glass = blank(32, 32)
    rect(glass, 0, 12, 31, 19, (143, 179, 189, 150))
    rect(glass, 0, 12, 31, 12, (220, 240, 245, 200))
    rect(glass, 0, 19, 31, 19, (60, 80, 90, 220))
    for i in range(4, 28, 9):
        glass.load()[i, 14] = (255, 255, 255, 220)
    save(glass, t + "window_glass.png")
    for state in ("closed", "open"):
        door = blank(32, 32)
        rect(door, 0, 10, 31, 21, "#2b3c45")
        if state == "closed":
            rect(door, 1, 11, 30, 20, "#4d6a77")
            rect(door, 15, 11, 16, 20, "#2b3c45")
            rect(door, 1, 11, 30, 11, "#6d8c99")
            door.load()[14, 15] = hexc(GOLD)
            door.load()[17, 15] = hexc(GOLD)
        else:
            rect(door, 1, 11, 5, 20, "#4d6a77")
            rect(door, 26, 11, 30, 20, "#4d6a77")
            rect(door, 6, 11, 25, 20, (0, 0, 0, 0))
        save(door, t + f"door_{state}.png")
    barrier = []
    for f in range(2):
        im = blank(32, 32)
        for y in range(32):
            for x in range(32):
                if (x + y + f * 2) % 4 == 0:
                    im.load()[x, y] = (79, 214, 200, 90)
        rect(im, 0, 0, 31, 0, (79, 214, 200, 200))
        rect(im, 0, 31, 31, 31, (79, 214, 200, 200))
        barrier.append(im)
    save(strip(barrier), t + "spawn_barrier.png")
    shadow = blank(32, 8)
    for y in range(8):
        rect(shadow, 0, y, 31, y, (0, 0, 0, int(120 * (1 - y / 8))))
    save(shadow, t + "wall_shadow.png")
    edge = blank(32, 4)
    rect(edge, 0, 0, 31, 0, "#8a879a")
    for y in range(1, 4):
        rect(edge, 0, y, 31, y, (0, 0, 0, 140 - y * 35))
    save(edge, t + "platform_edge.png")


def make_props() -> None:
    t = "maps/common/props/"
    props = {
        "barrel": (["..oooooooo..", ".oRRRRRRRRo.", "oRrrrrrrrrRo", "oRrRRRRRRrRo", "oRrR....RrRo", "oRrR....RrRo",
                    "oRrR....RrRo", "oRrR....RrRo", "oRrRRRRRRrRo", "oRrrrrrrrrRo", ".oRRRRRRRRo.", "..oooooooo.."],
                   {"o": "#2a1a14", "R": "#a8521f", "r": "#7a3a17", ".": "."}),
        "crate_small": (["oooooooooooo", "oWWWWWWWWWWo", "oWwwwwwwwwWo", "oWwWwwwwWwWo", "oWwwWwwWwwWo", "oWwwwWWwwwWo",
                         "oWwwwWWwwwWo", "oWwwWwwWwwWo", "oWwWwwwwWwWo", "oWwwwwwwwwWo", "oWWWWWWWWWWo", "oooooooooooo"],
                        {"o": "#3a2a1c", "W": "#a8804f", "w": "#8a6a40"}),
        "pallet": (["oooooooooooooooo", "oWWWWWWWWWWWWWWo", "o..............o", "oWWWWWWWWWWWWWWo", "o..............o",
                    "oWWWWWWWWWWWWWWo", "o..............o", "oWWWWWWWWWWWWWWo", "oooooooooooooooo"],
                   {"o": "#5a4430", "W": "#b8925f"}),
        "cone": (["....oo....", "...oOOo...", "..oOWWOo..", ".oOOOOOOo.", "oOWWWWWWOo", "oooooooooo"],
                 {"o": "#3a1a0e", "O": "#f08a24", "W": WHITE}),
        "plant": (["...gg.g...", ".gGGgGGg..", "gGGgGGgGg.", ".gGGGGGg..", "..ooooo...", "..oBBBo...", "..oBBBo...", "...ooo...."],
                  {"g": "#2a4a2a", "G": "#4f8a4a", "o": "#3a2a1c", "B": "#8a5a3a"}),
        "lamp": (["..oooo..", ".oYYYYo.", "oYWWWWYo", "oYWWWWYo", ".oYYYYo.", "..oooo.."],
                 {"o": "#2d2c31", "Y": GOLD, "W": "#fffbe8"}),
        "debris": (["..oo....o.", ".oGGo..oGo", "..oo..oGGo", "o.....oo..", "Go..o.....", "o..oGo..oo", "...oo...oG"],
                   {"o": "#3a3743", "G": "#7d7a80"}),
        "bench": (["oooooooooooooooooooooooooooooooo", "oWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWo", "owwwwwwwwwwwwwwwwwwwwwwwwwwwwwwo",
                   "oWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWo", "owwwwwwwwwwwwwwwwwwwwwwwwwwwwwwo", "oooooooooooooooooooooooooooooooo",
                   ".oo..........................oo.", ".oo..........................oo."],
                  {"o": "#2a2622", "W": "#9a7a52", "w": "#7a5e3c"}),
    }
    for name, (rows, pal) in props.items():
        pal = {k: v for k, v in pal.items() if k != "."}
        save(glyph(rows, pal), t + f"{name}.png")


def make_decals() -> None:
    t = "maps/common/decals/"
    rng = random.Random(8)
    crack = blank(32, 32)
    x, y = 4, 6
    for _ in range(40):
        crack.load()[x, y] = (20, 18, 24, 170)
        if rng.random() < 0.3:
            crack.load()[min(31, x + 1), y] = (20, 18, 24, 110)
        x, y = max(0, min(31, x + rng.choice((0, 1, 1)))), max(0, min(31, y + rng.choice((0, 1, 1, -1))))
    save(crack, t + "crack.png")
    stain = blank(32, 32)
    for yy in range(32):
        for xx in range(32):
            d = math.hypot((xx - 15) / 1.3, yy - 16)
            if d < 10 and rng.random() < 0.9 - d / 14:
                stain.load()[xx, yy] = (20, 18, 24, 120)
    save(stain, t + "oil_stain.png")
    arrow = glyph(["......YY........", ".....YYYY.......", "....YYYYYY......", "...YYYYYYYY.....", ".....YYYY.......",
                   ".....YYYY.......", ".....YYYY.......", ".....YYYY......."], {"Y": "#e0b437"})
    a = blank(16, 16)
    a.alpha_composite(arrow, (0, 4))
    px = a.load()
    for yy in range(16):
        for xx in range(16):
            if px[xx, yy][3]:
                px[xx, yy] = px[xx, yy][:3] + (170,)
    save(a, t + "arrow.png")
    letters = {
        "A": [".YYY.", "Y...Y", "Y...Y", "YYYYY", "Y...Y", "Y...Y", "Y...Y"],
        "B": ["YYYY.", "Y...Y", "Y...Y", "YYYY.", "Y...Y", "Y...Y", "YYYY."],
        "C": [".YYYY", "Y....", "Y....", "Y....", "Y....", "Y....", ".YYYY"],
    }
    for name, rows in letters.items():
        g = glyph(rows, {"Y": "#e0b437"}).resize((10, 14), Image.NEAREST)
        im = blank(16, 16)
        im.alpha_composite(g, (3, 1))
        px = im.load()
        for yy in range(16):
            for xx in range(16):
                if px[xx, yy][3]:
                    px[xx, yy] = px[xx, yy][:3] + (180,)
        save(im, t + f"site_{name.lower()}.png")
    hazard = blank(32, 8)
    for yy in range(8):
        for xx in range(32):
            hazard.load()[xx, yy] = (224, 180, 55, 190) if (xx + yy) % 8 < 4 else (22, 21, 27, 190)
    save(hazard, t + "hazard_stripe.png")
    drain = glyph(["oooooooooooooooo", "oGGGGGGGGGGGGGGo", "oG.G.G.G.G.G.GGo", "oGGGGGGGGGGGGGGo", "oG.G.G.G.G.G.GGo",
                   "oGGGGGGGGGGGGGGo", "oG.G.G.G.G.G.GGo", "oGGGGGGGGGGGGGGo", "oooooooooooooooo"],
                  {"o": "#16151b", "G": "#5a5f66"})
    save(drain, t + "drain.png")
    scorch = blank(32, 32)
    for yy in range(32):
        for xx in range(32):
            d = math.hypot(xx - 15.5, yy - 15.5)
            if d < 14 and rng.random() < 1.05 - d / 14:
                scorch.load()[xx, yy] = (14, 12, 16, int(200 * (1 - d / 15)))
    save(scorch, t + "scorch.png")


# ================================================================== generic ability sprites
def make_ability_fx() -> None:
    t = "fx/ability/"
    orb = [glyph(["..oo..", ".oWCo.", "oWCCCo", "oCCCCo", ".oCCo.", "..oo.."], {"o": INK, "W": "#ffffff", "C": c})
           for c in ("#d8dce6", "#ffffff")]
    save(strip(orb), t + "projectile_orb.png")
    save(glyph(["......W.", "oooooWWW", "oCCCCCWW", "oooooWWW", "......W."], {"o": INK, "C": "#8fb3bd", "W": WHITE}),
         t + "projectile_dart.png")
    save(glyph([".oooo.", "oMMMMo", "oMYMMo", "oMMMMo", ".oooo."], {"o": INK, "M": "#5a5f66", "Y": GOLD}), t + "grenade.png")
    save(glyph([".W.", "WWW", ".W."], {"W": WHITE}), t + "arc_dot.png")
    mine = [glyph([".oooooo.", "oMMMMMMo", "oMmLLmMo", "oMmLLmMo", "oMMMMMMo", ".oooooo."],
                  {"o": INK, "M": "#5a5f66", "m": "#3e4248", "L": led}) for led in ("#ff5a4f", "#5a2a2a")]
    save(strip(mine), t + "mine.png")
    beacon = []
    for f in range(2):
        im = blank(16, 16)
        im.alpha_composite(glyph(["..oooo..", ".oMMMMo.", "oMmYYmMo", "oMmYYmMo", ".oMMMMo.", "..oMMo..", "..oMMo..",
                                  ".oooooo."], {"o": INK, "M": "#7d8790", "m": "#545c64", "Y": GOLD}), (4, 6))
        for a in range(0, 360, 30):
            r = 3 + f * 2
            x, y = int(7.5 + math.cos(math.radians(a)) * (r + 3)), int(5 + math.sin(math.radians(a)) * r * 0.6)
            if 0 <= x < 16 and 0 <= y < 16 and not im.load()[x, y][3]:
                im.load()[x, y] = (224, 180, 55, 200 - f * 70)
        beacon.append(im)
    save(strip(beacon), t + "beacon.png")
    anchor = [glyph(["....W.....", "...WYW....", "..WYYYW...", "...WYW....", "....W.....", "....W.....", "..WWWWW...",
                     ".W.....W.."], {"W": WHITE if f == 0 else "#9b98aa", "Y": GOLD}) for f in range(2)]
    save(strip(anchor), t + "anchor_marker.png")
    step = glyph(["..WW....", ".WWWW...", ".WWWW...", "..WW....", "........", "....WW..", "...WWWW.", "....WW.."], {"W": "#c7ccd2"})
    sp = step.load()
    for y in range(8):
        for x in range(8):
            if sp[x, y][3]:
                sp[x, y] = sp[x, y][:3] + (140,)
    save(step, t + "decoy_step.png")
    reveal = [glyph(["...R...", "..RWR..", ".RWWWR.", "RWWWWWR", ".RWWWR.", "..RWR..", "...R..."], {"R": RED, "W": c})
              for c in ("#ffb4a8", RED)]
    save(strip(reveal), t + "reveal_marker.png")
    puff = []
    for f, rad in enumerate((3, 5, 7)):
        im = blank(16, 16)
        for y in range(16):
            for x in range(16):
                d = math.hypot(x - 7.5, y - 7.5)
                if d < rad and (x * 3 + y * 5 + f) % 4:
                    im.load()[x, y] = (186, 186, 200, 220 - f * 60)
        puff.append(im)
    save(strip(puff), t + "impact_puff.png")

    def column(frames: int, colour: tuple[int, int, int], kind: str) -> Image.Image:
        """Effects on a figure, same 16x32 cell as the agent (centre = player position)."""
        out = []
        rng = random.Random(len(kind))
        for f in range(frames):
            im = blank(16, 32)
            p = im.load()
            prog = (f + 1) / frames
            for y in range(32):
                for x in range(16):
                    if kind == "teleport":
                        w = 7 * (1 - abs(prog - 0.5) * 1.6)
                        if abs(x - 7.5) < max(w, 0.5) and (y + f * 3) % 3 != 0:
                            p[x, y] = colour + (int(220 * (1 - abs(prog - 0.5))),)
                    elif kind == "revive":
                        if abs(x - 7.5) < 2 + prog * 4 and y > 31 - prog * 34:
                            p[x, y] = colour + (int(180 * (1.2 - abs(x - 7.5) / 7)),)
                    elif kind == "shield":
                        dx, dy = (x - 7.5) / 7.5, (y - 15.5) / 15.5
                        d = math.hypot(dx, dy)
                        if 0.85 < d < 1.0 and (x + y + f) % 2 == 0:
                            p[x, y] = colour + (200,)
                    elif kind == "immunity":
                        dx, dy = (x - 7.5) / 7.5, (y - 15.5) / 15.5
                        if 0.9 < math.hypot(dx, dy) < 1.0 and (y // 2 + f) % 2 == 0:
                            p[x, y] = colour + (210,)
            if kind == "heal":
                for _ in range(6):
                    x, y = rng.randrange(3, 13), int(28 - prog * 20 - rng.randrange(0, 6))
                    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                        if 0 <= x + dx < 16 and 0 <= y + dy < 32:
                            p[x + dx, y + dy] = colour + (230,)
            out.append(im)
        return strip(out)

    save(column(4, (154, 122, 216), "teleport"), t + "teleport.png")
    save(column(3, (111, 191, 115), "heal"), t + "heal.png")
    save(column(4, (255, 251, 232), "revive"), t + "revive.png")
    save(column(3, (186, 220, 255), "shield"), t + "shield_shell.png")
    save(column(2, (255, 215, 94), "immunity"), t + "immunity_aura.png")


def main() -> None:
    make_menu()
    make_icons()
    make_buy()
    make_tiles()
    make_props()
    make_decals()
    make_ability_fx()


if __name__ == "__main__":
    main()
