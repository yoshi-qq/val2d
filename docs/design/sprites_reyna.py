"""Draw Reyna's pixel sprites, HUD icons and utility."""
from PIL import Image, ImageDraw

from sprites import CLEAR, save, strip
from sprites_breach import export_agent

INK = "#171123"
HAIR, HAIR_LIGHT = "#322044", "#633779"
SUIT, SUIT_SHADOW = "#47315e", "#251d36"
SKIN, GOLD = "#bc8267", "#efb269"
VIOLET, GLOW = "#d767f5", "#ffd1ff"


def pose(tag: str, frame: int) -> Image.Image:
    image = Image.new("RGBA", (16, 32), CLEAR)
    d = ImageDraw.Draw(image)
    crouch = tag.startswith("crouch") or tag in ("land", "plant", "defuse")
    bend = 3 if crouch else int(tag in ("shoot", "flinch") and frame == 0)
    gait = (0, 1, 0, -1)[frame % 4] if "walk" in tag else 0
    if tag in ("jump", "fall"):
        gait = 2 if tag == "jump" else 1
    for x, lift in ((5, gait), (9, -gait)):
        ankle = 29 - max(0, lift) - (2 if crouch else 0)
        d.rectangle((x, 18 + bend, x + 2, ankle), fill=SUIT_SHADOW, outline=INK)
        d.line((x + 1, 20 + bend, x + 1, ankle), fill=SUIT)
        d.rectangle((x - 1, ankle, x + 2, ankle + 1), fill=INK)

    d.polygon([(3, 5 + bend), (11, 4 + bend), (13, 13 + bend),
               (12, 18 + bend), (10, 16 + bend), (4, 17 + bend), (2, 14 + bend)], fill=HAIR, outline=INK)
    d.polygon([(5, 9 + bend), (10, 9 + bend), (12, 12 + bend), (10, 17 + bend),
               (11, 20 + bend), (4, 20 + bend), (5, 17 + bend), (3, 12 + bend)], fill=SUIT, outline=INK)
    d.line((5, 11 + bend, 8, 15 + bend, 10, 11 + bend), fill=HAIR_LIGHT)
    d.line((5, 18 + bend, 10, 18 + bend), fill=SUIT_SHADOW)
    d.point((8, 15 + bend), fill=VIOLET)

    casting = tag.startswith(("cast", "channel"))
    left, right = gait, -gait
    if casting:
        left, right = (4, 3) if tag.endswith(("_e", "_x")) else (5, 1)
    elif tag in ("reload", "equip", "shoot", "melee", "victory"):
        left, right = 1, 2 + frame % 3
    for x, lift in ((2, left), (12, right)):
        y = 12 + bend - max(0, lift)
        d.rounded_rectangle((x, y, x + 1, 19 + bend - lift), radius=1, fill=SUIT_SHADOW)
        d.point((x, y + 2), fill=HAIR_LIGHT)
        d.point((x, 19 + bend - lift), fill=VIOLET if casting and lift >= 3 else SKIN)

    d.rounded_rectangle((4, 2 + bend, 11, 10 + bend), radius=2, fill=SKIN, outline=INK)
    d.polygon([(4, 5 + bend), (5, 2 + bend), (8, 1 + bend), (11, 2 + bend), (12, 6 + bend),
               (9, 4 + bend), (7, 5 + bend), (5, 7 + bend)], fill=HAIR)
    d.line((6, 3 + bend, 8, 2 + bend, 10, 3 + bend), fill=HAIR_LIGHT)
    for x in (6, 9):
        d.point((x, 6 + bend), fill=INK)
    for x in (4, 11):
        d.point((x, 9 + bend), fill=GOLD)
    d.line((11, 10 + bend, 12, 14 + bend), fill=HAIR_LIGHT)
    return image


def icon(slot: str) -> Image.Image:
    image = Image.new("RGBA", (32, 32), CLEAR)
    d = ImageDraw.Draw(image)
    if slot == "C":
        d.line((3, 16, 10, 10, 16, 8, 22, 10, 29, 16, 22, 22, 16, 24, 10, 22, 3, 16), fill=VIOLET, width=2)
        d.ellipse((12, 11, 20, 21), fill=GLOW)
        d.line((16, 13, 16, 19), fill=HAIR, width=2)
    elif slot == "Q":
        d.ellipse((6, 6, 25, 25), outline=VIOLET, width=2)
        d.line((16, 10, 16, 22), fill=GLOW, width=3)
        d.line((10, 16, 22, 16), fill=GLOW, width=3)
    elif slot == "E":
        for x in (4, 11, 18):
            d.line((x, 25, x + 10, 9), fill=VIOLET, width=3)
    else:
        d.polygon([(5, 7), (11, 14), (16, 5), (21, 14), (27, 7), (23, 23), (9, 23)], outline=VIOLET, width=2)
        d.line((10, 27, 22, 27), fill=GLOW, width=2)
    return image


def utility(eye: bool) -> Image.Image:
    frames = []
    for radius in (5, 6, 7, 6):
        frame = Image.new("RGBA", (16, 16), CLEAR)
        d = ImageDraw.Draw(frame)
        d.ellipse((8 - radius, 8 - radius, 8 + radius, 8 + radius), fill=HAIR_LIGHT, outline=VIOLET)
        if eye:
            d.ellipse((3, 6, 13, 10), fill=GLOW)
            d.line((8, 6, 8, 10), fill=INK, width=2)
        else:
            d.polygon([(8, 3), (12, 8), (8, 12), (4, 8)], fill=VIOLET)
            d.ellipse((6, 6, 9, 9), fill=GLOW)
        frames.append(frame)
    return strip(frames)


if __name__ == "__main__":
    export_agent("reyna", pose, icon)
    save(utility(True), "fx/ability/reyna_eye.png")
    save(utility(False), "fx/ability/reyna_soul.png")
    save(icon("E").resize((18, 18), Image.Resampling.NEAREST), "ui/status/dismiss.png")
    save(icon("X").resize((18, 18), Image.Resampling.NEAREST), "ui/status/empress.png")
