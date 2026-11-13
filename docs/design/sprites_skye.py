"""Skye's copper braid, headband and green spirit animals."""
from PIL import Image, ImageDraw

from sprites import CLEAR, save
from sprites_breach import export_agent
from sprites_figure_views import LOOKS, Look
from sprites_raze import pose as base_pose

INK, GREEN, DARK = "#23283a", "#5c8155", "#304237"
HAIR, SKIN, LIME = "#b95832", "#c38768", "#d0f17d"
TEAL = "#77d6a0"


def pose(tag, frame):
    image = base_pose(tag, frame)
    draw = ImageDraw.Draw(image)
    y = 3 if tag.startswith("crouch") or tag in ("land", "plant", "defuse") else int(tag == "flinch" and frame == 0)
    draw.polygon([(8, 4+y), (12, 5+y), (13, 12+y), (11, 17+y), (10, 14+y), (11, 10+y)],
                 fill=HAIR, outline=INK)
    draw.rounded_rectangle((4, 2+y, 11, 9+y), 2, fill=SKIN, outline=INK)
    draw.polygon([(4, 5+y), (4, 3+y), (7, 1+y), (10, 2+y), (12, 4+y), (9, 5+y)], fill=HAIR)
    draw.line((4, 5+y, 11, 5+y), fill=GREEN, width=2)
    draw.point((6, 7+y), fill=INK)
    draw.point((9, 7+y), fill=INK)
    draw.line((6, 11+y, 8, 16+y, 10, 11+y), fill=TEAL)
    return image


def spirit(slot, size):
    image = Image.new("RGBA", (16, 16), CLEAR)
    d = ImageDraw.Draw(image)
    if slot == "C":
        for point in ((8, 1), (14, 6), (12, 13), (4, 13), (2, 6)):
            x, y = point
            d.line((8, 8, x, y), fill=GREEN, width=2)
            d.ellipse((x-1, y-1, x+1, y+1), fill=LIME)
        d.line((8, 5, 8, 11), fill=LIME, width=2)
        d.line((5, 8, 11, 8), fill=LIME, width=2)
    elif slot == "Q":
        d.polygon([(1, 8), (4, 4), (6, 5), (10, 5), (12, 3), (15, 7),
                   (13, 12), (10, 14), (5, 14), (2, 11)], fill=GREEN, outline=INK)
        d.line((4, 8, 6, 8), fill=LIME)
        d.line((10, 8, 12, 8), fill=LIME)
        d.line((6, 11, 9, 11), fill=DARK, width=2)
    elif slot == "E":
        d.polygon([(0, 4), (6, 6), (8, 2), (10, 6), (15, 4), (12, 10),
                   (9, 10), (8, 14), (6, 10), (3, 10)], fill=TEAL, outline=INK)
        d.line((4, 7, 8, 8, 12, 7), fill=LIME)
    else:
        for x, y in ((8, 4), (4, 10), (12, 10)):
            d.polygon([(x, y-3), (x+3, y), (x, y+4), (x-3, y)], fill=GREEN, outline=LIME)
            d.point((x, y), fill=TEAL)
    return image.resize((size, size), Image.Resampling.NEAREST)


if __name__ == "__main__":
    LOOKS["skye"] = Look(11, HAIR, DARK, GREEN, SKIN, GREEN, DARK, TEAL, LIME, INK,
                         ("..tt..", ".ssss.", ".s..s.", "..tt..", "......"))
    export_agent("skye", pose, lambda slot: spirit(slot, 32))
    for slot, key in zip("QEX", ("tiger", "hawk", "seeker")):
        save(spirit(slot, 16), f"fx/skye_{key}.png")
