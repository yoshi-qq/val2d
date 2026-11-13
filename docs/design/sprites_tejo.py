"""Draw Tejo's orange jacket, glasses and targeting equipment."""
from PIL import Image, ImageDraw
from sprites import CLEAR, save
from sprites_breach import export_agent
from sprites_deadlock import pose as armor_pose
from sprites_figure_views import LOOKS, Look

INK, WHITE, LILAC, GLOW, SKIN = "#2b302f", "#f18944", "#bb5427", "#ffe092", "#b97958"


def pose(tag, frame):
    image = armor_pose(tag, frame)
    d = ImageDraw.Draw(image)
    y = 3 if tag.startswith("crouch") or tag in ("land", "plant", "defuse") else int(tag == "flinch" and frame == 0)
    d.polygon([(4, 7+y), (4, 3+y), (7, 1+y), (11, 2+y), (12, 5+y), (10, 8+y)], fill=INK)
    d.rectangle((6, 5+y, 10, 9+y), fill=SKIN)
    d.line((5, 6+y, 11, 6+y), fill=INK, width=2)
    d.point((7, 6+y), fill=GLOW)
    d.point((10, 6+y), fill=GLOW)
    d.polygon([(4, 11+y), (10, 10+y), (11, 16+y), (8, 19+y), (4, 17+y)], fill=WHITE, outline=INK)
    d.line((5, 11+y, 7, 16+y, 10, 13+y), fill=LILAC, width=2)
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
    LOOKS["tejo"] = Look(11, INK, WHITE, INK, SKIN, WHITE, INK, LILAC, GLOW, INK,
                        ("..tt..", ".stts.", ".stts.", "..tt..", "......"))
    export_agent("tejo", pose, icon)
    for name, slot in (("drone", "C"), ("grenade", "Q"), ("missile", "E"), ("blast", "X"), ("strike", "X")):
        save(icon(slot), f"fx/tejo_{name}.png")
    pulse = Image.new("RGBA", (64, 64), CLEAR)
    d = ImageDraw.Draw(pulse)
    for inset in (2, 9, 17):
        d.ellipse((inset, inset, 63-inset, 63-inset), outline=GLOW, width=2)
    save(pulse, "fx/tejo_pulse.png")
