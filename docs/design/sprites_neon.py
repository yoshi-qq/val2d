"""Neon's blue twin tails and electric Val2D ability art."""
from PIL import Image, ImageDraw

from sprites import CLEAR, save
from sprites_breach import export_agent
from sprites_figure_views import LOOKS, Look
from sprites_waylay import pose as base_pose

NAVY, BLUE, CYAN, GOLD = "#24345c", "#377fe4", "#7ef8fd", "#ffe77e"
INK, SKIN = "#172338", "#b77557"


def pose(tag, frame):
    art = base_pose(tag, frame)
    d = ImageDraw.Draw(art)
    y = 3 if tag.startswith("crouch") or tag in ("land", "plant", "defuse") else int(tag == "flinch" and frame == 0)
    for x in (1, 11):
        d.polygon([(x, 3+y), (x+3, 2+y), (x+3, 8+y), (x, 12+y)], fill=BLUE, outline=NAVY)
        d.point((x+1, 5+y), fill=CYAN)
    d.rounded_rectangle((4, 2+y, 11, 9+y), 2, fill=SKIN, outline=INK)
    d.polygon([(3, 4+y), (6, 1+y), (10, 1+y), (12, 4+y), (8, 4+y), (5, 6+y)], fill=BLUE)
    d.line((6, 2+y, 10, 2+y), fill=CYAN)
    for x in (6, 9):
        d.point((x, 6+y), fill=INK)
    d.polygon([(5, 10+y), (10, 10+y), (11, 16+y), (7, 18+y), (5, 16+y)], fill=NAVY)
    d.line((7, 11+y, 10, 12+y, 8, 15+y, 10, 15+y), fill=GOLD)
    return art


def icon(slot):
    art = Image.new("RGBA", (32, 32), CLEAR)
    d = ImageDraw.Draw(art)
    if slot == "C":
        for x in (5, 17):
            d.line((x, 27, x+5, 17, x+2, 17, x+8, 5), fill=CYAN, width=3)
    elif slot == "Q":
        d.line((4, 7, 14, 23, 22, 10, 28, 17), fill=CYAN, width=3)
        for x, y in ((14, 23), (28, 17)):
            d.ellipse((x-3, y-3, x+3, y+3), outline=GOLD, width=2)
    elif slot == "E":
        for x in (3, 12, 21):
            d.line((x, 8, x+8, 16, x, 24), fill=CYAN, width=2)
    else:
        d.polygon([(19, 2), (6, 18), (15, 18), (12, 30), (27, 12), (18, 12)],
                  fill=CYAN, outline=GOLD, width=2)
    return art


if __name__ == "__main__":
    LOOKS["neon"] = Look(11, BLUE, NAVY, BLUE, SKIN, NAVY, INK, CYAN, GOLD, INK,
                         ("..tt..", ".ssss.", ".s..s.", "..tt..", "......"))
    export_agent("neon", pose, icon)
    for slot, name, size in (("C", "lane", 16), ("Q", "bolt", 16), ("Q", "relay", 64)):
        save(icon(slot).resize((size, size), Image.Resampling.NEAREST), f"fx/neon_{name}.png")
    save(icon("X"), "weapons/val2d/neon_beam.png")
    for slot, name in (("E", "sprint"), ("X", "overdrive")):
        save(icon(slot).resize((18, 18), Image.Resampling.NEAREST), f"ui/status/neon_{name}.png")
