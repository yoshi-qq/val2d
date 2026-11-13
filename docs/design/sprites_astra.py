"""Draw Astra's gold accents, braids and astral effects."""
from PIL import Image, ImageDraw
from sprites import CLEAR, save
from sprites_breach import export_agent
from sprites_deadlock import pose as armor_pose
from sprites_figure_views import LOOKS, Look

INK, WHITE, LILAC, GLOW, SKIN = "#28203d", "#b275e8", "#7f52bd", "#ffd780", "#88513c"


def pose(tag, frame):
    image = armor_pose(tag, frame)
    d = ImageDraw.Draw(image)
    y = 3 if tag.startswith("crouch") or tag in ("land", "plant", "defuse") else int(tag == "flinch" and frame == 0)
    d.polygon([(4, 7+y), (4, 3+y), (7, 1+y), (11, 2+y), (12, 5+y), (10, 8+y)], fill=INK)
    d.rectangle((6, 5+y, 10, 9+y), fill=SKIN)
    d.line((4, 3+y, 7, 1+y, 10, 3+y), fill=GLOW, width=1)
    d.line((11, 4+y, 12, 11+y), fill=INK, width=2)
    d.point((10, 8+y), fill=GLOW)
    d.line((4, 12+y, 7, 16+y, 10, 13+y), fill=LILAC, width=2)
    return image


def icon(slot):
    image = Image.new("RGBA", (32, 32), CLEAR)
    d = ImageDraw.Draw(image)
    if slot in ("C", "X"):
        d.polygon([(4, 11), (15, 4), (27, 11), (27, 22), (16, 28), (4, 22)], fill=INK, outline=GLOW, width=2)
        d.line((4, 11, 16, 18, 27, 11), fill=LILAC, width=2)
        d.line((16, 18, 16, 27), fill=GLOW, width=2)
        if slot == "X":
            d.line((8, 16, 16, 11, 23, 16), fill=GLOW, width=2)
    else:
        d.polygon([(16, 3), (29, 16), (16, 29), (3, 16)], fill=INK, outline=GLOW, width=2)
        d.polygon([(16, 9), (23, 16), (16, 23), (9, 16)], fill=LILAC)
        if slot == "Q":
            d.line((6, 24, 25, 7), fill=GLOW, width=2)
    return image


if __name__ == "__main__":
    LOOKS["astra"] = Look(11, INK, WHITE, INK, SKIN, WHITE, INK, LILAC, GLOW, INK,
                        ("..tt..", ".stts.", ".stts.", "..tt..", "......"))
    export_agent("astra", pose, icon)
    for name, slot in (("well", "C"), ("nova", "Q"), ("star", "X"), ("divide", "X")):
        save(icon(slot), f"fx/astra_{name}.png")
    for name, tint in (("smoke", (99, 48, 150, 215)), ("dissipate", (157, 75, 180, 170))):
        cloud = Image.new("RGBA", (64, 64), CLEAR)
        draw = ImageDraw.Draw(cloud)
        draw.ellipse((1, 1, 62, 62), fill=tint, outline=GLOW, width=2)
        for x, y in ((17, 20), (25, 39), (41, 15), (50, 38), (37, 48)):
            draw.line((x-2, y, x+2, y), fill=GLOW)
            draw.line((x, y-2, x, y+2), fill=GLOW)
        save(cloud, f"fx/astra_{name}.png")
