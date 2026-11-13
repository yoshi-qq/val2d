"""Draw Vyse's metal mask, jacket and thorn effects."""
from PIL import Image, ImageDraw
from sprites import CLEAR, save
from sprites_breach import export_agent
from sprites_deadlock import pose as armor_pose
from sprites_figure_views import LOOKS, Look

INK, STEEL, LILAC, GOLD = "#241e32", "#c4bccd", "#8a69b5", "#ffca68"

def pose(tag, frame):
    image = armor_pose(tag, frame)
    d = ImageDraw.Draw(image)
    y = 3 if tag.startswith("crouch") or tag in ("land", "plant", "defuse") else int(tag == "flinch" and frame == 0)
    d.polygon([(3, 3+y), (6, 4+y), (10, 4+y), (13, 2+y), (12, 9+y), (8, 12+y), (4, 9+y)], fill=INK, outline=LILAC)
    d.line((5, 6+y, 7, 7+y), fill=GOLD)
    d.line((9, 7+y, 11, 6+y), fill=GOLD)
    return image

def icon(slot):
    image = Image.new("RGBA", (32, 32), CLEAR)
    d = ImageDraw.Draw(image)
    if slot == "Q":
        d.polygon([(3, 25), (4, 10), (11, 14), (16, 5), (20, 13), (28, 8), (28, 26)], fill=INK, outline=STEEL, width=2)
        d.line((7, 22, 13, 16, 19, 22, 25, 15), fill=LILAC, width=2)
    elif slot == "E":
        for x, y in ((16, 9), (9, 16), (23, 16), (16, 23)):
            d.ellipse((x-5, y-5, x+5, y+5), fill=LILAC, outline=STEEL)
        d.ellipse((12, 12, 20, 20), fill=INK, outline=GOLD, width=2)
    else:
        for x in (5, 12, 20, 27):
            d.line((x, 26, 16, 14, x, 5 if slot == "X" else 9), fill=LILAC, width=2)
            d.line((x, 13, x, 7, min(29, x+4), 9), fill=STEEL, width=2)
        d.ellipse((13, 11, 19, 17), fill=GOLD)
    return image

def field(name, slot, fill):
    image = Image.new("RGBA", (64, 64), CLEAR)
    d = ImageDraw.Draw(image)
    d.ellipse((1, 1, 62, 62), fill=fill, outline=LILAC, width=2)
    for inset in (7, 14):
        d.arc((inset, inset, 63-inset, 63-inset), 35, 340, fill=STEEL)
    image.alpha_composite(icon(slot), (16, 16))
    save(image, f"fx/vyse_{name}.png")

if __name__ == "__main__":
    LOOKS["vyse"] = Look(11, INK, STEEL, INK, INK, STEEL, INK, LILAC, GOLD, INK,
                         ("t....t", ".tttt.", ".stts.", "..tt..", "......"))
    export_agent("vyse", pose, icon)
    for name, slot in (("nest", "C"), ("shear_trap", "Q"), ("shear_wall", "Q"), ("rose", "E")):
        save(icon(slot), f"fx/vyse_{name}.png")
    field("vines", "C", (74, 44, 102, 105))
    field("garden", "X", (74, 44, 102, 60))
