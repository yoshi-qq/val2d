"""Raze's orange cap, utility gear and colorful ability sprites."""
from PIL import Image, ImageDraw

from sprites import CLEAR, save
from sprites_breach import export_agent
from sprites_figure_views import LOOKS, Look
from sprites_miks import pose as base_pose

INK, GREEN, DARK = "#231b2b", "#617057", "#313e34"
ORANGE, YELLOW, SKIN = "#f48147", "#ffe479", "#a97054"
TEAL, RED = "#70ddd3", "#eb5368"
PALETTE = {
    (72, 48, 71, 255): (244, 129, 71, 255),
    (242, 130, 67, 255): (97, 112, 87, 255),
    (158, 66, 62, 255): (49, 62, 52, 255),
    (202, 136, 100, 255): (169, 112, 84, 255),
}


def pose(tag, frame):
    art = base_pose(tag, frame)
    art.putdata([PALETTE.get(pixel, pixel) for pixel in list(art.getdata())])
    d = ImageDraw.Draw(art)
    y = 3 if tag.startswith("crouch") or tag in ("land", "plant", "defuse") else int(tag == "flinch" and frame == 0)
    d.rounded_rectangle((3, 2+y, 12, 5+y), 1, fill=ORANGE)
    d.line((3, 5+y, 7, 5+y), fill=YELLOW)
    d.rectangle((3, 6+y, 4, 9+y), fill=DARK)
    d.rectangle((11, 6+y, 12, 9+y), fill=DARK)
    d.point((4, 8+y), fill=TEAL)
    d.point((10, 17+y), fill=ORANGE)
    return art


def art(slot, size):
    image = Image.new("RGBA", (16, 16), CLEAR)
    d = ImageDraw.Draw(image)
    if slot == "C":
        d.rounded_rectangle((1, 5, 14, 13), 2, fill=DARK, outline=INK)
        d.ellipse((2, 9, 6, 14), fill=INK)
        d.ellipse((10, 9, 14, 14), fill=INK)
        d.rectangle((4, 4, 11, 8), fill=ORANGE, outline=INK)
        d.line((5, 6, 10, 6), fill=YELLOW)
    elif slot == "Q":
        d.rounded_rectangle((2, 3, 13, 12), 2, fill=GREEN, outline=INK)
        d.line((3, 10, 12, 5), fill=ORANGE, width=2)
        d.ellipse((6, 5, 10, 9), fill=YELLOW, outline=INK)
    elif slot == "E":
        d.rounded_rectangle((5, 3, 10, 13), 2, fill=ORANGE, outline=INK)
        d.rectangle((6, 1, 9, 4), fill=DARK)
        d.line((5, 8, 10, 8), fill=TEAL, width=2)
        d.point((3, 4), fill=YELLOW)
        d.point((12, 11), fill=RED)
    else:
        d.polygon([(8, 1), (12, 5), (10, 11), (11, 14), (8, 12), (5, 14), (6, 11), (4, 5)],
                  fill=ORANGE, outline=INK)
        d.line((7, 7, 9, 7), fill=TEAL)
        d.line((8, 12, 8, 15), fill=YELLOW)
    return image.resize((size, size), Image.Resampling.NEAREST)


if __name__ == "__main__":
    LOOKS["raze"] = Look(11, ORANGE, RED, ORANGE, SKIN, GREEN, DARK, TEAL, ORANGE, INK,
                         ("..tt..", ".ssss.", ".s..s.", "..tt..", "......"))
    export_agent("raze", pose, lambda slot: art(slot, 32))
    for slot, name in zip("CQEX", ("bot", "pack", "grenade", "rocket")):
        save(art(slot, 16), f"fx/raze_{name}.png")
