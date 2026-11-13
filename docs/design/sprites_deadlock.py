"""Draw Deadlock's pale armor, prosthetic arm and nanowire effects."""
from PIL import Image, ImageColor, ImageDraw

from sprites import CLEAR, save
from sprites_breach import export_agent
from sprites_figure_views import LOOKS, Look
from sprites_waylay import BLUE, GOLD, NAVY, SHADE, pose as base_pose

INK, ARMOR, STEEL = "#273245", "#c7d8de", "#748eaa"
SKIN, HAIR, WIRE, GLOW = "#d69680", "#e3dbb9", "#3679bd", "#8ce7f7"
PALETTE = {ImageColor.getcolor(old, "RGBA"): ImageColor.getcolor(new, "RGBA")
           for old, new in ((GOLD, ARMOR), (SHADE, STEEL), (BLUE, WIRE), (NAVY, INK))}


def pose(tag, frame):
    image = base_pose(tag, frame)
    image.putdata([PALETTE.get(pixel, pixel) for pixel in image.getdata()])
    d = ImageDraw.Draw(image)
    y = 3 if tag.startswith("crouch") or tag in ("land", "plant", "defuse") else int(tag == "flinch" and frame == 0)
    d.polygon([(4, 7+y), (4, 3+y), (6, 1+y), (10, 2+y), (12, 5+y), (11, 9+y)], fill=HAIR, outline=INK)
    d.rectangle((6, 5+y, 10, 9+y), fill=SKIN)
    d.line((6, 4+y, 9, 3+y, 11, 5+y), fill=HAIR, width=2)
    d.point((9, 6+y), fill=INK)
    d.line((4, 11+y, 7, 14+y, 10, 12+y), fill=INK)
    d.line((12, 12+y, 13, 16+y), fill=STEEL, width=2)
    d.point((13, 16+y), fill=GLOW)
    return image


def icon(slot):
    image = Image.new("RGBA", (32, 32), CLEAR)
    d = ImageDraw.Draw(image)
    if slot == "C":
        d.line((4, 16, 27, 16), fill=WIRE, width=3)
        d.line((16, 4, 16, 27), fill=WIRE, width=3)
        for x, y in ((16, 16), (5, 16), (26, 16), (16, 5), (16, 26)):
            d.ellipse((x-3, y-3, x+3, y+3), fill=INK, outline=GLOW)
    elif slot == "Q":
        d.rectangle((5, 12, 12, 20), fill=STEEL, outline=GLOW)
        for right in (18, 24, 29):
            d.arc((6, 32-right, right, right), -65, 65, fill=GLOW, width=2)
    elif slot == "E":
        d.ellipse((4, 4, 27, 27), fill=INK, outline=GLOW, width=2)
        for x in (10, 16, 22):
            d.line((x, 8, 32-x, 23), fill=WIRE, width=2)
            d.line((8, x, 23, 32-x), fill=GLOW)
    else:
        d.ellipse((6, 2, 25, 29), fill=INK, outline=GLOW, width=2)
        for y in (8, 13, 18, 23):
            d.line((7, y, 24, y+3), fill=WIRE, width=2)
        d.line((16, 6, 16, 25), fill=GLOW)
    return image


if __name__ == "__main__":
    LOOKS["deadlock"] = Look(11, INK, ARMOR, HAIR, SKIN, STEEL, INK, WIRE, GLOW, INK,
                             ("..ss..", ".stts.", ".stts.", "..tt..", "......"))
    export_agent("deadlock", pose, icon)
    for name, slot in (("mesh", "C"), ("node", "C"), ("sensor", "Q"), ("net", "E"),
                       ("pulse", "X"), ("cocoon", "X")):
        save(icon(slot), f"fx/deadlock_{name}.png")
