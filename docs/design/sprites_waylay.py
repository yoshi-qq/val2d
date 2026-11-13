"""Draw Waylay's yellow high-collar kit and prismatic effects in Val2D's pixel style."""
from PIL import Image, ImageDraw

from sprites import CLEAR, save, strip
from sprites_breach import export_agent
from sprites_figure_views import LOOKS, Look

INK, NAVY, BLUE = "#181b32", "#303759", "#62689a"
HAIR, HAIR_SHADE, SILVER = "#3b344d", "#65566c", "#d8d0de"
SKIN, GOLD, SHADE = "#bc7858", "#ffd269", "#bc783e"
CYAN, PINK, WHITE = "#8ffce8", "#ff99e9", "#fff2d8"


def pose(tag, frame):
    image = Image.new("RGBA", (16, 32), CLEAR)
    draw = ImageDraw.Draw(image)
    crouch = tag.startswith("crouch") or tag in ("land", "plant", "defuse")
    bend = 3 if crouch else int(tag == "flinch" and frame == 0)
    gait = (0, 2, 0, -2)[frame % 4] if "walk" in tag else 0
    if tag in ("jump", "fall"):
        gait = 2
    for x, lift in ((4, gait), (9, -gait)):
        ankle = 28 - max(0, lift) - (2 if crouch else 0)
        draw.rectangle((x, 18 + bend, x + 3, ankle), fill=NAVY, outline=INK)
        draw.rectangle((x, 21 + bend, x + 3, 23 + bend), fill=BLUE, outline=INK)
        draw.rectangle((x, ankle, x + 3, ankle + 2), fill=INK)
        draw.line((x + 1, ankle + 1, x + 2, ankle + 1), fill=GOLD)

    draw.polygon([(4, 8 + bend), (10, 8 + bend), (12, 11 + bend), (10, 19 + bend),
                  (5, 19 + bend), (3, 12 + bend)], fill=GOLD, outline=INK)
    draw.line((5, 10 + bend, 7, 15 + bend, 11, 13 + bend), fill=SHADE, width=2)
    draw.line((5, 17 + bend, 10, 18 + bend), fill=NAVY, width=2)
    draw.point((8, 14 + bend), fill=CYAN)

    casting = tag.startswith(("cast", "channel"))
    lifts = (5, 4 if tag.endswith(("_q", "_x")) else 1) if casting else (gait, -gait)
    if tag in ("shoot", "reload", "equip", "melee", "victory"):
        lifts = (1, 3 + frame % 3)
    for x, lift in zip((2, 12), lifts):
        tip = 19 + bend - lift
        draw.line((x, 12 + bend, x, tip), fill=SKIN, width=2)
        draw.line((x, 11 + bend, x + 1, 13 + bend), fill=NAVY, width=2)
        draw.line((x, tip, x + 1, tip), fill=CYAN if casting else BLUE)
        if casting and lift >= 4:
            draw.point((x, tip - 2), fill=PINK)

    draw.rounded_rectangle((4, 2 + bend, 11, 10 + bend), 2, fill=SKIN, outline=INK)
    draw.polygon([(3, 5 + bend), (4, 2 + bend), (7, 1 + bend), (11, 2 + bend),
                  (12, 5 + bend), (11, 8 + bend), (9, 4 + bend), (5, 6 + bend)], fill=HAIR)
    draw.line((4, 4 + bend, 5, 3 + bend, 9, 2 + bend, 11, 3 + bend), fill=HAIR_SHADE)
    draw.line((4, 5 + bend, 3, 8 + bend, 4, 10 + bend), fill=SILVER)
    draw.line((11, 5 + bend, 12, 7 + bend, 11, 9 + bend), fill=SILVER)
    for x in (6, 9):
        draw.point((x, 6 + bend), fill=INK)
    return image


def icon(slot):
    image = Image.new("RGBA", (32, 32), CLEAR)
    draw = ImageDraw.Draw(image)
    if slot == "C":
        draw.polygon([(16, 3), (20, 12), (29, 16), (20, 20), (16, 29), (12, 20), (3, 16), (12, 12)],
                     outline=WHITE, width=2)
        draw.polygon([(16, 11), (20, 16), (16, 21), (12, 16)], fill=CYAN)
    elif slot == "Q":
        for x, color in ((5, PINK), (13, WHITE)):
            draw.line((x, 6, x + 10, 16, x, 26), fill=color, width=3)
        draw.line((5, 16, 29, 16), fill=CYAN, width=2)
    elif slot == "E":
        draw.polygon([(15, 3), (25, 15), (15, 28), (5, 15)], outline=WHITE, width=2)
        draw.line((27, 8, 18, 16, 27, 23), fill=CYAN, width=2)
        draw.polygon([(15, 11), (19, 16), (15, 21), (11, 16)], fill=PINK)
    else:
        draw.line((3, 4, 15, 15, 3, 27), fill=WHITE, width=2)
        draw.line((29, 4, 17, 15, 29, 27), fill=WHITE, width=2)
        draw.line((16, 3, 16, 29), fill=GOLD, width=2)
        draw.line((5, 15, 27, 15), fill=CYAN)
    return image


def crystal(core):
    image = Image.new("RGBA", (16, 16), CLEAR)
    draw = ImageDraw.Draw(image)
    draw.polygon([(8, 0), (13, 4), (15, 8), (11, 13), (8, 15), (2, 11), (0, 7), (4, 3)], fill=INK)
    draw.polygon([(8, 1), (13, 8), (8, 14), (2, 8)], fill=core, outline=WHITE)
    draw.line((8, 1, 8, 14), fill=WHITE)
    draw.line((2, 8, 13, 8), fill=CYAN)
    return image


if __name__ == "__main__":
    LOOKS["waylay"] = Look(11, HAIR, HAIR_SHADE, SILVER, SKIN, GOLD, SHADE, CYAN, NAVY, INK,
                          ("s....s", "..tt..", ".ssss.", ".ssss.", "..ss.."))
    export_agent("waylay", pose, icon)
    for name, fill in (("saturate", PINK), ("beacon", GOLD), ("mote", CYAN)):
        save(crystal(fill), f"fx/waylay_{name}.png")
    rings = []
    for width in (1, 2, 3, 2):
        image = Image.new("RGBA", (64, 64), CLEAR)
        draw = ImageDraw.Draw(image)
        draw.ellipse((1, 1, 62, 62), fill=(249, 163, 222, 25), outline=PINK, width=width)
        draw.arc((5, 5, 58, 58), 25, 140, fill=GOLD, width=width)
        draw.arc((5, 5, 58, 58), 205, 320, fill=CYAN, width=width)
        rings.append(image)
    save(strip(rings), "fx/waylay_saturate_field.png")
    for slot, name in (("C", "hinder"), ("X", "haste")):
        save(icon(slot).resize((18, 18), Image.Resampling.NEAREST), f"ui/status/waylay_{name}.png")
