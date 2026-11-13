"""Draw Miks's Val2D sprites from Riot's agent art and ability icons."""
from PIL import Image, ImageDraw

from character_sheet_spec import STATES
from sprites import CLEAR, enemy_variant, save, strip
from sprites_figure_views import LOOKS, Look, export

INK, HAIR, HAIR_SHADOW = "#231b2b", "#483047", "#322438"
SKIN, SKIN_SHADE = "#ca8864", "#8f5449"
VEST, VEST_SHADE, VEST_LIGHT = "#f28243", "#9e423e", "#ffc071"
PANTS, PANTS_SHADE = "#494568", "#2e2a47"
LIME, PURPLE, WHITE = "#d9f586", "#bf8efb", "#f9f4ed"


def pose(tag, frame):
    image = Image.new("RGBA", (16, 32), CLEAR)
    draw = ImageDraw.Draw(image)
    low = tag.startswith("crouch") or tag in ("land", "plant", "defuse")
    gait = (0, 2, 0, -2)[frame % 4] if "walk" in tag else 0
    bend = 3 if low else int(tag == "flinch" and frame == 0)
    if tag in ("jump", "fall"):
        gait = 2
    for x, lift in ((4, gait), (9, -gait)):
        ankle = 28 - max(0, lift) - (2 if low else 0)
        draw.rectangle((x, 18 + bend, x + 3, ankle), fill=PANTS, outline=INK)
        draw.line((x + 1, 22 + bend, x + 2, 22 + bend), fill=PANTS_SHADE)
        draw.rectangle((x, ankle, x + 3, ankle + 2), fill=HAIR_SHADOW, outline=INK)
        draw.line((x + 1, ankle + 1, x + 2, ankle + 1), fill=VEST_SHADE)
    draw.polygon([(5, 8 + bend), (10, 8 + bend), (12, 11 + bend), (11, 19 + bend),
                  (4, 19 + bend), (3, 11 + bend)], fill=VEST, outline=INK)
    draw.line((5, 10 + bend, 8, 13 + bend, 10, 10 + bend), fill=VEST_SHADE, width=2)
    draw.line((8, 14 + bend, 8, 17 + bend), fill=VEST_LIGHT)
    draw.line((4, 18 + bend, 11, 18 + bend), fill=PANTS_SHADE)
    draw.point((10, 18 + bend), fill=LIME)

    casting = tag.startswith(("cast", "channel"))
    lifts = (4, 5 if tag.endswith("_x") else 2) if casting else (gait, -gait)
    if tag in ("shoot", "reload", "equip", "melee", "victory"):
        lifts = (1, 3 + frame % 3)
    for x, lift in zip((2, 12), lifts):
        tip = 19 + bend - lift
        draw.line((x + (1 if x == 2 else 0), 11 + bend, x, tip), fill=SKIN, width=2)
        draw.line((x, tip - 2, x + 1, tip - 2), fill=PURPLE if casting else PANTS_SHADE)
        draw.line((x, tip, x + 1, tip), fill=LIME if casting else INK)

    draw.rounded_rectangle((4, 2 + bend, 11, 10 + bend), 2, fill=SKIN, outline=INK)
    draw.polygon([(4, 6 + bend), (3, 3 + bend), (5, 3 + bend), (5, 1 + bend), (7, 2 + bend),
                  (9, bend), (10, 2 + bend), (12, 2 + bend), (11, 5 + bend), (8, 4 + bend),
                  (6, 5 + bend), (5, 7 + bend)], fill=HAIR)
    draw.line((5, 4 + bend, 8, 2 + bend, 10, 2 + bend), fill=HAIR_SHADOW)
    for x in (6, 9):
        draw.point((x, 6 + bend), fill=INK)
    draw.point((10, 8 + bend), fill=SKIN_SHADE)
    draw.point((4, 8 + bend), fill=LIME)
    return image


def icon(slot):
    image = Image.new("RGBA", (32, 32), CLEAR)
    draw = ImageDraw.Draw(image)
    if slot == "C":
        draw.polygon([(5, 10), (10, 6), (22, 6), (27, 10), (26, 22), (21, 26), (11, 26), (6, 22)],
                     outline=WHITE, width=2)
        draw.line((8, 17, 12, 17, 14, 13, 17, 20, 19, 15, 24, 15), fill=WHITE, width=2)
    elif slot == "Q":
        for y in (5, 12, 19):
            draw.line((9, y + 6, 16, y, 23, y + 6), fill=WHITE, width=2)
    elif slot == "E":
        for y, inset in ((7, 7), (12, 5), (17, 3)):
            draw.ellipse((inset, y, 31 - inset, y + 7), outline=WHITE, width=2)
    else:
        for y, inset in ((6, 3), (12, 6), (18, 10)):
            draw.arc((inset, y - 4, 31 - inset, y + 7), 5, 175, fill=WHITE, width=2)
    return image


def export_assets():
    idle = pose("idle", 0)
    for state in STATES:
        tag = state.tag
        if tag in ("portrait", "killfeed"):
            head = idle.crop((0, 0, 16, 16))
            frames = [head.resize((32, 32), Image.Resampling.NEAREST) if tag == "portrait" else head]
        elif tag == "select":
            frames = [idle.resize((32, 64), Image.Resampling.NEAREST)]
        elif tag == "dead":
            frames = [idle.transpose(Image.Transpose.ROTATE_90)]
        elif tag == "dying":
            frames = [idle.rotate(angle, center=(8, 17)) for angle in (20, 45, 70)]
        else:
            frames = [pose(tag, frame) for frame in range(state.frames[0])]
        stem = f"agents/miks/miks_{tag}"
        save(strip(frames), f"{stem}.png")
        if tag not in ("portrait", "select", "killfeed"):
            save(strip([enemy_variant(frame) for frame in frames]), f"{stem}_enemy.png")
    LOOKS["miks"] = Look(11, HAIR, HAIR_SHADOW, HAIR, SKIN, VEST, VEST_SHADE, LIME, PANTS, INK,
                        ("......", ".ssss.", "s.tt.s", "..tt..", "......"))
    export("miks", replace=True)
    for slot in "CQEX":
        save(icon(slot), f"ui/ability_miks_{slot}.png")
    save(icon("Q").resize((18, 18), Image.Resampling.NEAREST), "ui/status/miks_haste.png")

    for name, accent in (("concuss", PURPLE), ("heal", LIME)):
        device = Image.new("RGBA", (16, 16), CLEAR)
        draw = ImageDraw.Draw(device)
        draw.polygon([(3, 4), (12, 4), (15, 8), (11, 12), (4, 12), (1, 8)], fill=PANTS_SHADE, outline=INK)
        draw.line((3, 8, 5, 6, 11, 6, 13, 8, 11, 10, 5, 10, 3, 8), fill=accent)
        draw.point((8, 8), fill=WHITE)
        save(device, f"fx/miks_pulse_{name}.png")

    smoke_frames = []
    for phase in range(4):
        smoke = Image.new("RGBA", (64, 64), CLEAR)
        draw = ImageDraw.Draw(smoke)
        draw.ellipse((0, 0, 63, 63), fill="#3b304c", outline="#9880a9", width=2)
        draw.ellipse((5, 5, 58, 58), fill="#51425f", outline="#6f5a81")
        for i, color in enumerate(("#aa78aa", "#d398a7", "#c4aa92")):
            pad = 8 + 5 * i
            draw.arc((pad, pad + 2, 63 - pad, 61 - pad), 22 + phase * 4, 160 + phase * 4, fill=color, width=2)
        smoke_frames.append(smoke)
    save(strip(smoke_frames), "fx/miks_waveform.png")


if __name__ == "__main__":
    export_assets()
