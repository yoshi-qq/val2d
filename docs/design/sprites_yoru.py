"""Yoru's blue jacket, swept hair and rift utility."""
from PIL import Image, ImageDraw

from sprites import CLEAR, save
from sprites_breach import export_agent
from sprites_figure_views import LOOKS, Look
from sprites_chamber import pose as base_pose

INK, BLUE, CYAN, GOLD, SKIN = "#161b35", "#375bc1", "#78d3ff", "#f7ab61", "#c68f72"


def pose(tag, frame):
    art = base_pose(tag, frame)
    d = ImageDraw.Draw(art)
    y = 3 if tag.startswith("crouch") or tag in ("land", "plant", "defuse") else int(tag == "flinch" and frame == 0)
    d.polygon([(4, 5+y), (2, 2+y), (6, 2+y), (8, y), (12, 2+y), (13, 4+y), (8, 3+y)],
              fill=BLUE, outline=INK)
    d.line((4, 3+y, 8, 2+y, 11, 3+y), fill=CYAN)
    d.line((5, 11+y, 7, 17+y, 10, 16+y, 11, 11+y), fill=BLUE, width=3)
    d.point((8, 15+y), fill=GOLD)
    return art


def icon(slot):
    art = Image.new("RGBA", (32, 32), CLEAR)
    d = ImageDraw.Draw(art)
    if slot == "C":
        for x in (11, 21):
            d.ellipse((x-4, 4, x+4, 12), outline=CYAN, width=2)
            d.line((x-6, 25, x-4, 17, x+4, 17, x+6, 25), fill=BLUE, width=2)
    elif slot == "Q":
        d.polygon([(16, 2), (19, 12), (29, 16), (19, 20), (16, 30), (12, 20), (3, 16), (12, 12)],
                  fill=BLUE, outline=CYAN, width=2)
        d.point((16, 16), fill=GOLD)
    elif slot == "E":
        for inset in (3, 8, 12):
            d.arc((inset, inset, 31-inset, 31-inset), 24, 324, fill=CYAN if inset != 8 else BLUE, width=2)
    else:
        d.polygon([(4, 5), (10, 8), (16, 5), (22, 8), (28, 5), (25, 21),
                   (16, 28), (7, 21)], fill=BLUE, outline=CYAN, width=2)
        d.line((9, 14, 14, 17), fill=GOLD, width=2)
        d.line((18, 17, 23, 14), fill=GOLD, width=2)
    return art


if __name__ == "__main__":
    LOOKS["yoru"] = Look(11, INK, BLUE, BLUE, SKIN, BLUE, INK, CYAN, GOLD, INK,
                         ("..tt..", ".ssss.", ".s..s.", "..tt..", "......"))
    export_agent("yoru", pose, icon)
    for slot, name in (("C", "marker"), ("Q", "flash"), ("E", "gate")):
        save(icon(slot).resize((16, 16), Image.Resampling.NEAREST), f"fx/yoru_{name}.png")
    save(icon("X").resize((18, 18), Image.Resampling.NEAREST), "ui/status/yoru_drift.png")
