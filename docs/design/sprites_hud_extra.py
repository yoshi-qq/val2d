"""Fourth batch: everything the game still drew as shapes or text (list from the coding session, 12.11.2026).

Usage: python docs/design/sprites_hud_extra.py
World effects (white, tinted in code), crosshair, nine-slice panels (24x24, 8 px corners),
minimap fills and the bomb-carrier hint. In the Val2d style.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sprites as base  # noqa: E402
import sprites_hud_hd as hd  # noqa: E402

hexc, darker, lighter, save = base.hexc, base.darker, base.lighter, base.save
INK = (14, 13, 18, 255)
TEAL, RED, GOLD, WHITE = "#4fd6c8", "#ee4c4a", "#e0b437", "#e8e6ef"


def blank(w: int, h: int) -> Image.Image:
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


# ------------------------------------------------------------------ world effects
def make_world_fx() -> None:
    for name, core, glow in (("tracer", (255, 236, 170, 230), (255, 215, 94, 110)),
                             ("tracer_own", (255, 251, 232, 255), (255, 225, 140, 150))):
        im = blank(16, 2)
        p = im.load()
        for x in range(16):
            p[x, 0] = core if x % 8 < 6 else glow
            p[x, 1] = glow if x % 8 < 6 else (glow[0], glow[1], glow[2], glow[3] // 2)
        save(im, f"fx/{name}.png")

    frames = []
    for f in range(3):  # sound ring: thin, white, fading as it grows
        im = blank(64, 64)
        p = im.load()
        alpha = (230, 160, 80)[f]
        r = 31.0
        for a in range(0, 720):
            ang = math.radians(a / 2)
            x, y = int(round(31.5 + math.cos(ang) * r)), int(round(31.5 + math.sin(ang) * r))
            if 0 <= x < 64 and 0 <= y < 64 and (f < 2 or a % 6 < 4):
                p[x, y] = (255, 255, 255, alpha)
        frames.append(im)
    save(base.strip(frames), "fx/sound_ring.png")

    ring = blank(64, 64)
    p = ring.load()
    for a in range(0, 720):
        ang = math.radians(a / 2)
        if (a // 20) % 2:
            continue
        for r in (30.5, 31.3):
            x, y = int(round(31.5 + math.cos(ang) * r)), int(round(31.5 + math.sin(ang) * r))
            if 0 <= x < 64 and 0 <= y < 64:
                p[x, y] = (255, 255, 255, 220)
    for d in (-1, 0, 1):
        p[31 + d, 31] = (255, 255, 255, 160)
        p[31, 31 + d] = (255, 255, 255, 160)
    save(ring, "fx/radius_ring.png")

    marker = base.from_rows(["...WW...", "..WWWW..", ".WWWWWW.", "WWWWWWWW", "..WWWW..", "..WWWW..", "........", "........"],
                            {"W": "#ffffff"})
    mp = marker.load()
    for y in range(8):
        for x in range(8):
            if mp[x, y][3]:
                mp[x, y] = (255, 255, 255, 235 if y < 4 else 170)
    save(marker, "fx/facing_marker.png")


# ------------------------------------------------------------------ crosshair
def make_crosshair() -> None:
    for suffix, col in (("", (120, 255, 200, 255)), ("_hit", (238, 76, 74, 255))):
        dot = blank(4, 4)
        dp = dot.load()
        for x, y in ((1, 0), (2, 0), (0, 1), (3, 1), (0, 2), (3, 2), (1, 3), (2, 3)):
            dp[x, y] = INK
        for x, y in ((1, 1), (2, 1), (1, 2), (2, 2)):
            dp[x, y] = col
        save(dot, f"ui/crosshair/dot{suffix}.png")
        arm = blank(2, 8)
        ap = arm.load()
        for y in range(8):
            ap[0, y] = col
            ap[1, y] = darker(col, 0.55)
        ap[0, 0] = lighter(col, 0.4)
        save(arm, f"ui/crosshair/arm{suffix}.png")


# ------------------------------------------------------------------ nine-slice panels (24x24, 8 px corners)
def panel(fill: str, edge: tuple | str, top: str, stripe: str | None = None, alpha: int = 255, notch: str | None = None) -> Image.Image:
    s = 24
    im = blank(s, s)
    d = ImageDraw.Draw(im)
    e = hexc(edge) if isinstance(edge, str) else edge
    f = hexc(fill)[:3] + (alpha,)
    d.rounded_rectangle((0, 0, s - 1, s - 1), radius=3, fill=f, outline=e)
    d.line([(3, 1), (s - 4, 1)], fill=hexc(top)[:3] + (min(255, alpha + 40),))
    d.line([(3, s - 2), (s - 4, s - 2)], fill=(14, 13, 18, min(255, alpha)))
    if stripe:
        d.rectangle((1, 3, 2, s - 4), fill=hexc(stripe))
    if notch:
        for x, y in ((3, 3), (s - 4, 3), (3, s - 4), (s - 4, s - 4)):
            im.load()[x, y] = hexc(notch)
    return im


def make_panels() -> None:
    save(panel("#121118", INK, "#2f2d3a", alpha=210, notch="#4b4855"), "ui/minimap/frame.png")
    wall = blank(4, 4)
    ImageDraw.Draw(wall).rectangle((0, 0, 3, 3), fill=hexc("#6e6a78"))
    wall.load()[0, 0] = hexc("#8a879a")
    save(wall, "ui/minimap/wall.png")
    crate = blank(4, 4)
    ImageDraw.Draw(crate).rectangle((0, 0, 3, 3), fill=hexc("#4d6a77"))
    crate.load()[3, 3] = hexc("#2b3c45")
    save(crate, "ui/minimap/crate.png")
    save(panel("#1f1e27", INK, "#2f2d3a", alpha=200), "ui/hud/killfeed_row.png")
    save(panel("#2a2933", hexc(GOLD)[:3] + (230,), "#46434f", stripe=GOLD, alpha=225), "ui/hud/killfeed_row_self.png")
    save(panel("#1f1e27", INK, "#2f2d3a", alpha=235), "ui/scoreboard/row.png")
    save(panel("#2a2933", TEAL, "#46434f", stripe=TEAL, alpha=240), "ui/scoreboard/row_self.png")
    save(panel("#1e3a39", TEAL, "#2f5a57", alpha=245, notch=TEAL), "ui/scoreboard/header_team_a.png")
    save(panel("#3a1e20", RED, "#5a2f31", alpha=245, notch=RED), "ui/scoreboard/header_team_b.png")
    score = panel("#1f1e27", INK, "#34323e", alpha=230, notch="#4b4855")
    ImageDraw.Draw(score).line([(8, 22), (15, 22)], fill=hexc(GOLD))
    save(score, "ui/hud/score_panel.png")
    save(panel("#1f1e27", INK, "#2f2d3a", alpha=200, notch="#4b4855"), "ui/hud/weapon_panel.png")
    save(panel("#1f1e27", INK, "#2f2d3a", alpha=200, notch="#4b4855"), "ui/hud/ability_panel.png")


def make_carrier_hint() -> None:
    bomb = hd.small(hd.HUD["spike_klein"][0], 16, hd.HUD["spike_klein"][1], hd.HUD["spike_klein"][2])
    key = base.from_rows(["oooooo", "oWWWWo", "oWoooo", "oWWWo.", "oWooo.", "oWo...", "ooo..."], {"o": "#0e0d12", "W": GOLD})
    im = blank(16, 16)
    im.alpha_composite(bomb.crop((0, 0, 16, 16)), (0, 0))
    im.alpha_composite(key, (10, 9))
    save(im, "ui/hud/carrier_hint.png")


def main() -> None:
    make_world_fx()
    make_crosshair()
    make_panels()
    make_carrier_hint()


if __name__ == "__main__":
    main()
