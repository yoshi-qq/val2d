"""Build the Val2d interface PNGs with Pillow; agent ability sprites are authored separately."""
from __future__ import annotations

import math
import runpy
import sys
from io import BytesIO
from PIL import Image, ImageColor, ImageDraw, ImageFont

from sprites import ASSETS, ROOT
from sprites_hud_hd import BANNERS, GLYPHS, HUD, MINIMAP, STATUS, Painter
from sprites_world import ICONS8, glyph
from sprites_buy_hd import SPECS, draw_long, draw_pistol, draw_revolver

sys.path.insert(0, str(ROOT))
theme = runpy.run_path(str(ROOT / "config/client/theme.py"))["THEME"]["colors"]
INK, PAPER, RED, MINT, GOLD = (theme[key] for key in ("bg", "text", "accent", "ally", "ult"))
EDGE = "#65757d"
SLATE = "#202e38"


def write(im: Image.Image, key: str) -> None:
    path = ASSETS / "ui" / f"{key}.png"
    buffer = BytesIO()
    im.save(buffer, format="PNG")
    data = buffer.getvalue()
    if path.is_file() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".png.tmp")
    try:
        temporary.write_bytes(data)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def canvas(w: int, h: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGBA", (w, h))
    return im, ImageDraw.Draw(im)


def plate(w: int, h: int, fill: str, edge: str, cut: int = 3) -> Image.Image:
    im, d = canvas(w, h)
    d.polygon([(0, 0), (w - 1 - cut, 0), (w - 1, cut), (w - 1, h - 1),
               (cut, h - 1), (0, h - 1 - cut)], fill=fill, outline=edge)
    return im


def backdrop() -> Image.Image:
    w, h = 480, 270
    im, d = canvas(w, h)
    for y in range(h):
        d.line((0, y, w, y), fill=(13 + y // 27, 22 + y // 19, 33 + y // 17))
    d.polygon([(288, 0), (480, 0), (480, 270), (400, 270), (219, 89)], fill="#233743")
    d.polygon([(383, 0), (480, 0), (480, 216), (445, 181), (445, 99)], fill="#aa2f41")
    d.polygon([(421, 0), (480, 0), (480, 151), (421, 92)], fill=RED)
    d.polygon([(0, 170), (98, 270), (0, 270)], fill="#283e48")
    d.polygon([(0, 197), (73, 270), (0, 270)], fill="#702637")
    d.line([(0, 158), (110, 269)], fill="#795565")
    d.line([(328, 0), (479, 151)], fill="#50616b")
    d.line([(249, 119), (400, 270)], fill="#50616b")
    d.line([(0, 233), (479, 233)], fill="#39505c")
    return im


def menu() -> None:
    for name, fill, edge in (
        ("button", SLATE, EDGE), ("button_hover", "#354b56", PAPER),
        ("button_pressed", INK, MINT), ("button_disabled", "#19252e", "#35434b"),
        ("button_primary", RED, RED), ("button_primary_hover", "#ff5c69", PAPER),
        ("button_primary_pressed", "#bd3944", RED),
        ("tab", "#19252e", "#35434b"), ("tab_active", "#2c3d46", RED),
        ("textfield", "#0c151d", EDGE),
    ):
        write(plate(16, 16, fill, edge), f"menu/{name}")
    write(plate(24, 24, "#14212bf7", EDGE, 5), "menu/panel")
    for on in (False, True):
        im = plate(8, 8, SLATE if not on else MINT, EDGE if not on else MINT, 1)
        if on:
            ImageDraw.Draw(im).line([(2, 4), (3, 5), (5, 2)], fill=INK)
        write(im, "menu/checkbox_on" if on else "menu/checkbox")
    for key, col in (("track", EDGE), ("fill", MINT)):
        im, d = canvas(16, 6)
        d.rectangle((0, 2, 15, 3), fill=col)
        write(im, f"menu/slider_{key}")
    write(plate(6, 6, PAPER, PAPER, 2), "menu/slider_knob")
    im, d = canvas(12, 13)
    d.polygon([(0, 0), (10, 8), (6, 8), (8, 11), (6, 12), (4, 9), (0, 12)], fill=PAPER, outline=INK)
    write(im, "menu/cursor")
    write(backdrop(), "menu/title_background")
    for key, accent, body in (("party_self", RED, "#382a38"), ("party_bot", EDGE, "#253a45")):
        im = plate(75, 150, INK, accent, 4)
        d = ImageDraw.Draw(im)
        d.polygon([(1, 35), (74, 108), (74, 139), (1, 66)], fill=body)
        d.polygon([(14, 1), (29, 1), (74, 46), (74, 61)], fill=body)
        d.line([(1, 77), (55, 131)], fill=accent)
        d.line([(41, 1), (74, 34)], fill=accent)
        d.line([(1, 0), (29, 0)], fill=accent, width=2)
        write(im, f"menu/{key}")


def flat_glyph(painter: Painter, size: int, base: str, detail: str) -> Image.Image:
    mask = Image.new("L", (size - 2, size - 2))
    painter(ImageDraw.Draw(mask), size - 2)
    im = Image.new("RGBA", (size, size))
    for value, col in ((1, base), (2, detail)):
        im.paste(ImageColor.getrgb(col), (1, 1, size - 1, size - 1), mask.point(lambda v: 255 if v == value else 0))
    return im


def credits(size: int) -> Image.Image:
    im, d = canvas(size, size)
    m = size // 2
    d.polygon([(m, 1), (size - 2, m), (m, size - 2), (1, m)], outline=PAPER, width=2)
    d.line((m - 1, m + 2, m + 2, m - 1), fill=PAPER, width=2)
    return im


def icons() -> None:
    arrows = {"arrow_up": [(1, 5), (3, 2), (6, 5)], "arrow_down": [(1, 2), (3, 5), (6, 2)],
              "arrow_left": [(5, 1), (2, 3), (5, 6)], "arrow_right": [(2, 1), (5, 3), (2, 6)]}
    for key, rows in ICONS8.items():
        im = glyph(rows, {"W": PAPER, "R": RED})
        if key in arrows:
            im, d = canvas(8, 8)
            d.line(arrows[key], fill=PAPER, width=1)
        write(im, f"icons/{key}")
    for level in range(4):
        im, d = canvas(8, 8)
        for i in range(4):
            d.line((i * 2, 6 - i * 2, i * 2, 6), fill=(RED, GOLD, MINT, MINT)[level] if i <= level else EDGE)
        write(im, f"icons/ping_{level}")
    for key, col in (("win", MINT), ("loss", RED), ("empty", EDGE)):
        im, d = canvas(6, 6)
        d.polygon([(2, 0), (5, 2), (3, 5), (0, 3)], fill=col if key == "win" else None, outline=col)
        write(im, f"icons/round_{key}")
    write(credits(12), "icons/credits_large")
    for key, kind in (("role_duelist", "dash"), ("role_initiator", "flash"), ("role_controller", "smoke"),
                      ("role_sentinel", "shield"), ("side_attack", "hop"), ("side_defense", "shield")):
        im = flat_glyph(GLYPHS[kind], 26, PAPER, MINT if key == "side_defense" else PAPER)
        write(im.resize((16, 16), Image.Resampling.NEAREST), f"icons/{key}")


def buy() -> None:
    for cat, key, legacy_key in (
        ("sidearm", "sheriff", "bulle"),
        ("smg", "spectre", "sirene"),
        ("shotgun", "bucky", "brecher"),
        ("rifle", "bulldog", "falke"),
        ("sniper", "operator", "adler"),
        ("heavy", "odin", "walze"),
    ):
        mask = Image.new("L", (64, 24))
        spec = SPECS[key if key in SPECS else legacy_key]
        painter = {"long": draw_long, "pistol": draw_pistol, "revolver": draw_revolver}[spec["kind"]]
        painter(ImageDraw.Draw(mask), spec)
        mask = mask.point(lambda v: 255 if v else 0).resize((16, 7), Image.Resampling.BOX)
        im, _ = canvas(16, 16)
        im.paste(ImageColor.getrgb(PAPER), (0, 4, 16, 11), mask)
        write(im, f"buy/cat_{cat}")
    for key, kind in (("armor", "shield"), ("abilities", "flash")):
        write(flat_glyph(GLYPHS[kind], 26, PAPER, SLATE).resize((16, 16), Image.Resampling.NEAREST), f"buy/cat_{key}")
    for key in ("light", "regen", "heavy"):
        im, d = canvas(64, 24)
        d.polygon([(14, 3), (23, 3), (27, 7), (37, 7), (41, 3), (50, 3),
                   (48, 10), (53, 14), (50, 22), (14, 22), (11, 14), (16, 10)], fill="#667e86", outline=PAPER)
        d.polygon([(23, 10), (40, 10), (43, 14), (41, 19), (23, 19), (20, 14)], fill=PAPER)
        if key == "heavy":
            d.line((13, 14, 19, 14), fill=MINT, width=3)
            d.line((45, 14, 51, 14), fill=MINT, width=3)
            d.line((23, 18, 41, 18), fill=INK, width=2)
        if key == "regen":
            d.line([(23, 16), (28, 11), (34, 11), (38, 15)], fill=INK, width=2)
            d.polygon([(34, 15), (41, 15), (41, 10)], fill=MINT)
        write(im, "buy/regen_shield" if key == "regen" else f"buy/vest_{key}")
    for key, fill, edge in (("card", "#25343e", "#42545e"), ("card_owned", "#24453f", MINT),
                            ("card_hover", "#314e49", MINT), ("card_locked", "#1a2731", "#34444e")):
        write(plate(24, 24, fill, edge, 4), f"buy/{key}")


def match() -> None:
    for folder, entries, size in (("hud", HUD, 16), ("status", STATUS, 16), ("minimap", MINIMAP, 12)):
        for key, (paint, _, _) in entries.items():
            primary = {"ally": MINT, "enemy": RED, "spike": RED, "eliminated": "#a2b2bb", "stim": MINT}.get(key, PAPER)
            detail = MINT if key == "stim" else INK if key in {"timer", "detain", "decay", "vulnerable"} else "#a5c7c7"
            write(flat_glyph(paint, size, primary, detail), f"{folder}/{key}")
    write(credits(16), "hud/credits")
    im, d = canvas(16, 16)
    d.polygon([(8, 1), (14, 8), (8, 14), (1, 8)], outline=RED, width=2)
    d.rectangle((7, 4, 8, 11), fill=PAPER)
    write(im, "hud/carrier_hint")
    for folder, items in (
        ("hud", {"frame": (SLATE, EDGE), "frame_active": (SLATE, MINT), "ability_panel": ("#121f2aa8", EDGE),
                 "weapon_panel": ("#121f2aa8", EDGE), "score_panel": ("#101c28e8", EDGE),
                 "killfeed_row": ("#101c28e6", "#50616b"), "killfeed_row_self": ("#253e42f0", MINT)}),
        ("scoreboard", {"row": ("#21303ae8", "#344852"), "row_self": ("#344d51", MINT),
                        "header_team_a": ("#23433e", MINT), "header_team_b": ("#442a35", RED)}),
    ):
        for key, (fill, edge) in items.items():
            write(plate(24, 24, fill, edge, 4), f"{folder}/{key}")
    for key, col in (("health", PAPER), ("shield", MINT), ("progress", GOLD), ("empty", "#485862")):
        im, d = canvas(96, 12)
        d.rectangle((0, 3, 95, 8), fill=col)
        write(im, f"hud/bar_{key}")
    for key, col in (("wall", "#9fadb3"), ("crate", "#536d78")):
        im, d = canvas(4, 4)
        d.rectangle((0, 0, 3, 3), fill=col)
        d.line((0, 0, 3, 0), fill="#b4c2c7" if key == "wall" else "#758d98")
        write(im, f"minimap/{key}")
    im, d = canvas(104, 104)
    d.ellipse((0, 0, 103, 103), outline="#0c151e")
    d.ellipse((1, 1, 102, 102), outline="#84949b")
    for start in (0, 90, 180, 270):
        d.arc((0, 0, 103, 103), start - 7, start + 7, fill=PAPER)
    write(im, "minimap/frame")
    for suffix, col in (("", PAPER), ("_hit", RED)):
        im, d = canvas(4, 4)
        d.rectangle((0, 0, 3, 3), fill=INK)
        d.rectangle((1, 1, 2, 2), fill=col)
        write(im, f"crosshair/dot{suffix}")
        write(Image.new("RGBA", (2, 8), col), f"crosshair/arm{suffix}")


def banners() -> None:
    font = ImageFont.truetype(str(ROOT / "font/fixed_sys.ttf"), 16)
    for key, (title, _) in BANNERS.items():
        edge = MINT if key in {"victory", "bomb_defused"} else RED if key in {"defeat", "bomb_planted"} else GOLD
        left, top, right, bottom = font.getbbox(title)
        w = max(115, right - left + 50)
        im = plate(w, 32, "#13212dee", edge, 8)
        d = ImageDraw.Draw(im)
        d.polygon([(0, 0), (14, 0), (6, 9), (0, 9)], fill=edge)
        d.polygon([(w - 1, 31), (w - 15, 31), (w - 8, 22), (w - 1, 22)], fill=edge)
        d.fontmode = "1"
        d.text(((w - right + left) // 2 - left, (32 - bottom + top) // 2 - top), title, font=font, fill=PAPER)
        write(im, f"banner/{key}")


if __name__ == "__main__":
    for build in (menu, icons, buy, match, banners):
        build()
