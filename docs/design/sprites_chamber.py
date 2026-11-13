"""Chamber's tailored waistcoat, gold glasses, gadgets and weapon silhouettes."""
from PIL import Image, ImageDraw

from sprites import CLEAR, save, strip
from sprites_breach import export_agent
from sprites_figure_views import LOOKS, Look

INK, NAVY, BLUE = "#1c2231", "#253c65", "#516e99"
SHIRT, SHADOW, GOLD = "#eee7de", "#a5aab9", "#edbe66"
HAIR, SKIN, TEAL = "#3b2c2b", "#c68f72", "#89ead9"


def pose(tag, frame):
    art = Image.new("RGBA", (16, 32), CLEAR)
    draw = ImageDraw.Draw(art)
    low = tag.startswith("crouch") or tag in ("land", "plant", "defuse")
    bend = 3 if low else int(tag == "flinch" and frame == 0)
    gait = (0, 2, 0, -2)[frame % 4] if "walk" in tag else int(tag in ("jump", "fall")) * 2
    for x, lift in ((4, gait), (9, -gait)):
        ankle = 28 - max(0, lift) - int(low) * 2
        draw.rectangle((x, 18 + bend, x + 3, ankle), fill=NAVY, outline=INK)
        draw.line((x + 1, 21 + bend, x + 1, ankle), fill=BLUE)
        draw.rectangle((x, ankle, x + 3, ankle + 2), fill=INK)
    draw.polygon([(5, 9 + bend), (10, 9 + bend), (12, 12 + bend), (10, 19 + bend),
                  (5, 19 + bend), (3, 12 + bend)], fill=NAVY, outline=INK)
    draw.polygon([(5, 10 + bend), (10, 10 + bend), (8, 15 + bend)], fill=SHIRT)
    draw.line((8, 11 + bend, 8, 15 + bend), fill=GOLD)
    draw.point((9, 17 + bend), fill=GOLD)
    casting = tag.startswith(("cast", "channel"))
    lifts = (4, 5 if tag.endswith("_x") else 2) if casting else (gait, -gait)
    if tag in ("shoot", "reload", "equip", "melee", "victory"):
        lifts = (1, 3 + frame % 3)
    for x, lift in zip((2, 12), lifts):
        tip = 19 + bend - lift
        draw.line((x, 12 + bend, x, tip), fill=SHIRT, width=2)
        draw.line((x, tip - 2, x + 1, tip - 2), fill=SHADOW)
        draw.line((x, tip, x + 1, tip), fill=GOLD if casting else SKIN)
    draw.rounded_rectangle((4, 2 + bend, 11, 10 + bend), 2, fill=SKIN, outline=INK)
    draw.polygon([(4, 6 + bend), (3, 3 + bend), (5, 1 + bend), (10, 1 + bend), (12, 3 + bend),
                  (11, 5 + bend), (7, 4 + bend), (5, 6 + bend)], fill=HAIR)
    draw.line((5, 6 + bend, 10, 6 + bend), fill=GOLD)
    for x in (6, 9):
        draw.point((x, 7 + bend), fill=INK)
    return art


def weapon(rifle):
    art = Image.new("RGBA", (48, 16), CLEAR)
    d = ImageDraw.Draw(art)
    if rifle:
        d.polygon([(2, 7), (8, 7), (10, 5), (31, 5), (34, 7), (46, 7), (46, 9),
                   (25, 9), (22, 13), (19, 13), (20, 9), (9, 9), (6, 11), (2, 11)], fill=INK)
        d.line((5, 8, 43, 8), fill=GOLD, width=2)
        d.rectangle((17, 3, 27, 4), fill=GOLD)
        d.line((23, 11, 25, 9), fill=BLUE)
    else:
        d.polygon([(12, 4), (35, 4), (36, 8), (25, 9), (22, 14), (16, 14), (17, 9), (12, 8)], fill=INK)
        d.line((13, 5, 34, 5), fill=GOLD, width=2)
        d.line((16, 8, 30, 8), fill=BLUE)
        d.line((19, 11, 18, 13), fill=GOLD)
    return art


def device(anchor):
    art = Image.new("RGBA", (16, 16), CLEAR)
    d = ImageDraw.Draw(art)
    d.polygon([(8, 1), (14, 7), (13, 12), (9, 14), (3, 13), (2, 7)], fill=NAVY, outline=INK)
    d.line((3, 11, 8, 13, 13, 10), fill=GOLD, width=2)
    d.polygon([(8, 2), (12, 7), (8, 11), (4, 7)], outline=GOLD, fill=TEAL if anchor else BLUE)
    if not anchor:
        d.line((5, 7, 11, 7), fill=TEAL, width=2)
    return art


def icon(slot):
    art = Image.new("RGBA", (32, 32), CLEAR)
    if slot in "CE":
        art.alpha_composite(device(slot == "E").resize((26, 26), Image.Resampling.NEAREST), (3, 3))
    else:
        silhouette = weapon(slot == "X")
        silhouette = silhouette.crop(silhouette.getbbox())
        silhouette.thumbnail((30, 22), Image.Resampling.NEAREST)
        art.alpha_composite(silhouette, ((32 - silhouette.width) // 2, (32 - silhouette.height) // 2))
    return art


if __name__ == "__main__":
    LOOKS["chamber"] = Look(11, HAIR, INK, HAIR, SKIN, NAVY, BLUE, GOLD, SHADOW, INK,
                           (".s..s.", "......", ".tttt.", "..tt..", "......"))
    export_agent("chamber", pose, icon)
    for key, rifle in (("headhunter", False), ("tour_de_force", True)):
        save(weapon(rifle), f"weapons/val2d/{key}.png")
    save(device(False), "fx/chamber_trademark.png")
    save(device(True), "fx/chamber_anchor.png")
    frames = []
    for phase in range(4):
        art = Image.new("RGBA", (64, 64), CLEAR)
        d = ImageDraw.Draw(art)
        d.ellipse((1, 1, 62, 62), fill=(161, 109, 55, 70), outline=GOLD)
        for inset in (5, 12, 19):
            d.arc((inset, inset, 63-inset, 63-inset), 35 + 8 * phase, 270 + 8 * phase, fill=TEAL, width=2)
        frames.append(art)
    save(strip(frames), "fx/chamber_slow.png")
