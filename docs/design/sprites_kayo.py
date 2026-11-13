"""KAY/O's armored silhouette and blue-violet utility."""
from PIL import Image, ImageDraw

from sprites import CLEAR, save, strip
from sprites_breach import export_agent
from sprites_figure_views import LOOKS, Look

INK, STEEL, PLATE = "#181b2f", "#3e4962", "#7183a0"
VIOLET, CYAN, WHITE = "#9a72ec", "#82d8ff", "#e1f4ff"


def pose(tag, frame):
    img = Image.new("RGBA", (16, 32), CLEAR)
    d = ImageDraw.Draw(img)
    low = tag.startswith("crouch") or tag in ("land", "plant", "defuse")
    y = 4 if low else int(tag == "flinch")
    gait = (0, 2, 0, -2)[frame % 4] if "walk" in tag else int(tag in ("jump", "fall")) * 2
    for x, step in ((4, gait), (9, -gait)):
        ankle = 28 - max(0, step) - int(low) * 3
        d.rectangle((x, 17+y, x+3, ankle), fill=STEEL, outline=INK)
        d.line((x+1, 23+y, x+2, 23+y), fill=CYAN)
        d.rectangle((x, ankle, x+3, ankle+2), fill=INK)
    d.polygon([(3, 10+y), (6, 8+y), (10, 8+y), (13, 10+y), (11, 18+y),
               (5, 18+y)], fill=STEEL, outline=INK)
    d.polygon([(5, 11+y), (11, 11+y), (10, 14+y), (6, 14+y)], fill=PLATE)
    d.point((8, 12+y), fill=VIOLET)
    casting = tag.startswith(("cast", "channel"))
    lift = 5 if casting else 2 if tag in ("shoot", "reload", "equip", "melee") else gait
    for x, arm in ((1, lift), (12, -gait if not casting else 3)):
        tip = 19+y-arm
        d.rounded_rectangle((x, 10+y, x+2, max(12+y, tip)), 1, fill=PLATE, outline=INK)
        d.point((x+1, max(12+y, tip)-1), fill=VIOLET if casting else CYAN)
    d.polygon([(4, 3+y), (6, 1+y), (10, 1+y), (12, 3+y), (11, 8+y), (9, 9+y),
               (6, 8+y), (4, 6+y)], fill=PLATE, outline=INK)
    d.rectangle((5, 4+y, 10, 7+y), fill=INK)
    d.line((6, 5+y, 8, 6+y, 10, 5+y), fill=CYAN, width=1)
    return img


def utility(slot, size):
    img = Image.new("RGBA", (16, 16), CLEAR)
    d = ImageDraw.Draw(img)
    if slot == "E":
        d.polygon([(8, 0), (11, 4), (9, 10), (12, 11), (12, 13), (9, 13), (8, 15),
                   (7, 13), (4, 13), (4, 11), (7, 10), (5, 4)], fill=STEEL, outline=CYAN)
        d.line((8, 2, 8, 10), fill=VIOLET)
    elif slot == "X":
        d.polygon([(8, 0), (14, 4), (14, 11), (8, 15), (2, 11), (2, 4)], outline=CYAN, width=2)
        d.line((3, 8, 6, 8, 8, 4, 10, 11, 13, 8), fill=VIOLET, width=2)
    else:
        d.rounded_rectangle((4, 3, 11, 13), 2, fill=STEEL, outline=PLATE)
        d.rectangle((6, 1, 9, 3), fill=PLATE)
        d.line((5, 8, 10, 8), fill=WHITE if slot == "Q" else VIOLET, width=2)
        d.point((7, 11), fill=CYAN)
    return img.resize((size, size), Image.Resampling.NEAREST)


if __name__ == "__main__":
    LOOKS["kayo"] = Look(10, STEEL, INK, PLATE, STEEL, STEEL, INK, VIOLET, PLATE, INK,
                         ("..tt..", ".ssss.", ".s..s.", "..tt..", "......"))
    export_agent("kayo", pose, lambda slot: utility(slot, 32))
    for slot, name in zip("CQE", ("frag", "flash", "knife")):
        save(utility(slot, 16), f"fx/kayo_{name}.png")
    save(utility("X", 18), "ui/status/kayo_downed.png")
    for name, color in (("field", VIOLET), ("pulse", CYAN)):
        frames = []
        for phase in range(4):
            frame = Image.new("RGBA", (64, 64), CLEAR)
            d = ImageDraw.Draw(frame)
            inset = 2 if name == "field" else 11 - phase * 3
            d.ellipse((inset, inset, 63-inset, 63-inset), outline=color, width=2,
                      fill=(110, 78, 190, 52) if name == "field" else None)
            inner = inset + 5 + phase
            d.ellipse((inner, inner, 63-inner, 63-inner), outline=CYAN, width=1)
            frames.append(frame)
        save(strip(frames), f"fx/kayo_{name}.png")
