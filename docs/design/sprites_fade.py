"""Fade's asymmetrical hair, dark field gear and nightmare utility."""
from PIL import Image, ImageDraw

from sprites import CLEAR, save
from sprites_breach import export_agent
from sprites_figure_views import LOOKS, Look
from sprites_waylay import pose as base_pose

INK, COAT, SILVER, SKIN = "#1f1c30", "#443a58", "#ccc5de", "#bb7b68"
VIOLET, PINK = "#8459bd", "#e594cb"


def pose(tag, frame):
    img = base_pose(tag, frame)
    draw = ImageDraw.Draw(img)
    y = 3 if tag.startswith("crouch") or tag in ("land", "plant", "defuse") else int(tag == "flinch" and frame == 0)
    draw.polygon([(4, 4+y), (7, 1+y), (11, 2+y), (13, 5+y), (12, 13+y), (10, 11+y),
                  (4, 10+y), (3, 7+y)], fill=INK)
    draw.rounded_rectangle((5, 4+y, 11, 9+y), 1, fill=SKIN)
    draw.line((4, 5+y, 7, 2+y, 10, 2+y), fill=SILVER, width=2)
    draw.line((11, 3+y, 12, 10+y), fill=COAT, width=2)
    draw.point((7, 6+y), fill=INK)
    draw.point((10, 6+y), fill=PINK)
    draw.polygon([(5, 10+y), (9, 10+y), (11, 14+y), (10, 18+y), (5, 18+y)], fill=COAT, outline=INK)
    draw.line((5, 11+y, 8, 13+y, 10, 12+y), fill=VIOLET)
    return img


def icon(slot):
    img = Image.new("RGBA", (32, 32), CLEAR)
    d = ImageDraw.Draw(img)
    if slot == "C":
        d.polygon([(3, 8), (10, 10), (16, 5), (22, 10), (29, 8), (25, 22), (16, 29), (7, 22)],
                  fill=COAT, outline=VIOLET, width=2)
        d.line((8, 15, 13, 17), fill=PINK, width=2)
        d.line((19, 17, 24, 15), fill=PINK, width=2)
    elif slot == "Q":
        d.ellipse((5, 5, 26, 26), outline=PINK, width=2)
        d.line((4, 21, 14, 8, 23, 23, 27, 10), fill=VIOLET, width=3)
    elif slot == "E":
        d.polygon([(3, 16), (10, 9), (21, 9), (29, 16), (21, 23), (10, 23)],
                  fill=COAT, outline=VIOLET, width=2)
        d.ellipse((12, 11, 20, 21), fill=PINK)
        d.line((16, 12, 16, 20), fill=INK, width=2)
    else:
        for x in (3, 9, 15):
            d.line((x, 25, x+4, 13, x+12, 5), fill=VIOLET, width=2)
        d.arc((9, 5, 28, 24), 10, 160, fill=PINK, width=2)
    return img


if __name__ == "__main__":
    LOOKS["fade"] = Look(11, INK, COAT, SILVER, SKIN, COAT, INK, VIOLET, PINK, INK,
                         ("..tt..", ".ssss.", ".s..s.", "..tt..", "......"))
    export_agent("fade", pose, icon)
    for slot, key in (("C", "prowler"), ("Q", "seize"), ("E", "haunt")):
        save(icon(slot).resize((16, 16), Image.Resampling.NEAREST), f"fx/fade_{key}.png")
    field = Image.new("RGBA", (64, 64), CLEAR)
    d = ImageDraw.Draw(field)
    d.ellipse((1, 1, 62, 62), fill=(73, 41, 102, 95), outline=VIOLET, width=2)
    d.arc((8, 8, 55, 55), 25, 310, fill=PINK, width=2)
    d.ellipse((24, 24, 39, 39), fill=COAT, outline=PINK)
    save(field, "fx/fade_seize_field.png")
