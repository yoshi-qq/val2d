"""Draw Harbor's teal field gear and water utility."""
from PIL import Image, ImageDraw, ImageColor

from sprites import CLEAR, save
from sprites_breach import export_agent
from sprites_figure_views import LOOKS, Look
from sprites_waylay import BLUE, GOLD, HAIR, NAVY, SHADE, pose as base_pose

INK, TEAL, BLUEGRAY = "#19282e", "#24636a", "#54818b"
SKIN, BEARD, GOLDEN, FOAM = "#b77653", "#312320", "#e7bd68", "#a3f7ef"
WATER = "#4faeaf"
PALETTE = {ImageColor.getcolor(old, "RGBA"): ImageColor.getcolor(new, "RGBA")
           for old, new in ((GOLD, TEAL), (SHADE, BLUEGRAY), (BLUE, BLUEGRAY), (NAVY, INK), (HAIR, BEARD))}


def pose(tag, frame):
    image = base_pose(tag, frame)
    image.putdata([PALETTE.get(pixel, pixel) for pixel in image.getdata()])
    draw = ImageDraw.Draw(image)
    y = 3 if tag.startswith("crouch") or tag in ("land", "plant", "defuse") else int(tag == "flinch" and frame == 0)
    draw.polygon([(4, 5+y), (5, 2+y), (9, 1+y), (12, 3+y), (11, 8+y), (4, 8+y)], fill=BEARD)
    draw.rectangle((5, 5+y, 10, 9+y), fill=SKIN)
    draw.line((5, 8+y, 6, 10+y, 9, 10+y, 10, 8+y), fill=BEARD, width=2)
    draw.point((9, 6+y), fill=INK)
    draw.line((5, 11+y, 8, 15+y, 10, 13+y), fill=GOLDEN)
    return image


def icon(slot):
    image = Image.new("RGBA", (32, 32), CLEAR)
    d = ImageDraw.Draw(image)
    if slot == "C":
        for inset in (3, 8, 13):
            d.arc((inset, inset, 31-inset, 31-inset), 30, 315, fill=FOAM, width=2)
    elif slot == "Q":
        d.polygon([(3, 20), (9, 11), (15, 15), (21, 7), (28, 12), (26, 23), (4, 26)],
                  fill=TEAL, outline=FOAM, width=2)
        d.line((6, 22, 13, 19, 18, 20, 25, 15), fill=WATER, width=2)
    elif slot == "E":
        d.ellipse((4, 4, 27, 27), fill=TEAL, outline=FOAM, width=2)
        d.arc((7, 9, 24, 23), 30, 320, fill=WATER, width=3)
        d.polygon([(12, 14), (16, 11), (20, 14), (19, 20), (16, 23), (13, 20)], outline=GOLDEN)
    else:
        d.polygon([(2, 24), (8, 22), (13, 10), (20, 6), (26, 9), (29, 16), (23, 13),
                   (20, 16), (22, 21), (29, 24), (27, 27), (2, 27)], fill=TEAL, outline=FOAM, width=2)
    return image


def water_art():
    for key, shield in (("cove", False), ("shield", True), ("storm", False)):
        image = Image.new("RGBA", (64, 64), CLEAR)
        d = ImageDraw.Draw(image)
        if shield:
            d.ellipse((1, 1, 62, 62), outline=GOLDEN, width=2)
            d.ellipse((4, 4, 59, 59), outline=FOAM, width=2)
        else:
            d.ellipse((1, 1, 62, 62), fill=(31, 116, 129, 214 if key == "cove" else 105), outline=WATER, width=2)
            for inset in (7, 14, 22):
                d.arc((inset, inset, 63-inset, 63-inset), 40 + inset * 2, 310, fill=FOAM, width=2)
        save(image, f"fx/harbor_{key}.png")
    for key, color in (("tide", WATER), ("wave", FOAM)):
        image = Image.new("RGBA", (24, 24), CLEAR)
        d = ImageDraw.Draw(image)
        d.polygon([(0, 7), (6, 4), (14, 8), (23, 7), (23, 16), (17, 19), (9, 16), (0, 16)], fill=TEAL)
        d.line((0, 7, 6, 4, 14, 8, 23, 7), fill=color, width=3)
        d.line((0, 13, 9, 11, 16, 14, 23, 13), fill=WATER, width=2)
        save(image, f"fx/harbor_{key}.png")
    save(icon("E"), "fx/harbor_current.png")


if __name__ == "__main__":
    LOOKS["harbor"] = Look(11, INK, TEAL, BEARD, SKIN, BLUEGRAY, INK, WATER, GOLDEN, INK,
                           ("..tt..", ".ssss.", ".stts.", "..tt..", "......"))
    export_agent("harbor", pose, icon)
    water_art()
