"""Draw Iso's dark hair, white jacket and prismatic energy."""
from PIL import Image, ImageDraw
from sprites import CLEAR, save
from sprites_breach import export_agent
from sprites_deadlock import pose as armor_pose
from sprites_figure_views import LOOKS, Look

INK, WHITE, LILAC, GLOW, SKIN = "#251f33", "#ddd6e2", "#885cba", "#e3b7ff", "#c48d75"


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
    LOOKS["iso"] = Look(11, INK, WHITE, INK, SKIN, WHITE, INK, LILAC, GLOW, INK,
                        ("..tt..", ".stts.", ".stts.", "..tt..", "......"))
    export_agent("iso", pose, icon)
    for name, slot in (("screen", "C"), ("bolt", "Q"), ("orb", "E"), ("marker", "X"), ("column", "X")):
        save(icon(slot), f"fx/iso_{name}.png")
    shield = Image.new("RGBA", (32, 32), CLEAR)
    d = ImageDraw.Draw(shield)
    d.ellipse((2, 2, 29, 29), outline=GLOW, width=2)
    d.arc((5, 5, 26, 26), 30, 320, fill=LILAC, width=2)
    save(shield, "fx/iso_shield.png")
    save(shield.resize((16, 16)), "ui/status/iso_shield.png")
    save(icon("E").resize((16, 16)), "ui/status/iso_flow.png")
