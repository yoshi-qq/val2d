"""Draw Clove's violet hair, pale jacket and butterflies."""
from PIL import Image, ImageDraw
from sprites import CLEAR, save
from sprites_breach import export_agent
from sprites_deadlock import pose as armor_pose
from sprites_figure_views import LOOKS, Look

INK, WHITE, LILAC, GLOW, SKIN = "#542762", "#e9d9e9", "#b44d99", "#fdbcf0", "#c48d75"


def pose(tag, frame):
    image = armor_pose(tag, frame)
    d = ImageDraw.Draw(image)
    y = 3 if tag.startswith("crouch") or tag in ("land", "plant", "defuse") else int(tag == "flinch" and frame == 0)
    d.polygon([(4, 7+y), (4, 3+y), (7, 1+y), (11, 2+y), (12, 5+y), (10, 8+y)], fill=INK)
    d.rectangle((6, 5+y, 10, 9+y), fill=SKIN)
    d.line((5, 5+y, 9, 3+y), fill=INK, width=2)
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
    LOOKS["clove"] = Look(11, INK, WHITE, INK, SKIN, WHITE, INK, LILAC, GLOW, INK,
                        ("..tt..", ".stts.", ".stts.", "..tt..", "......"))
    export_agent("clove", pose, icon)
    for name, slot in (("meddle", "Q"), ("revive", "X")):
        save(icon(slot), f"fx/clove_{name}.png")
    for suffix, tint in (("", (171, 89, 158, 217)), ("_dead", (85, 50, 119, 224))):
        cloud = Image.new("RGBA", (64, 64), CLEAR)
        draw = ImageDraw.Draw(cloud)
        draw.ellipse((1, 1, 62, 62), fill=tint, outline=LILAC, width=2)
        for inset in (7, 14, 20):
            draw.arc((inset, inset, 63-inset, 63-inset), inset * 4, 310, fill=GLOW, width=2)
        save(cloud, f"fx/clove_smoke{suffix}.png")
    save(icon("C").resize((16, 16)), "ui/status/clove_haste.png")
    save(icon("X").resize((16, 16)), "ui/status/clove_revive.png")
