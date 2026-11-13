"""Export Breach's Val2d figure, ability icons and directional strips."""
from __future__ import annotations

from PIL import Image, ImageDraw

from character_sheet_spec import STATES
from sprites import CLEAR, enemy_variant, save, strip
from sprites_figure_views import export

INK, STEEL, STEEL_DARK = "#212924", "#abb9b7", "#667979"
GREEN, GREEN_DARK = "#63734f", "#3c4a39"
HAIR, HAIR_DARK, SKIN = "#d66d33", "#a74927", "#dba17b"
ENERGY = "#ffbb68"


def pose(tag: str, frame: int) -> Image.Image:
    sprite = Image.new("RGBA", (16, 32), CLEAR)
    draw = ImageDraw.Draw(sprite)
    crouched = tag.startswith("crouch") or tag in ("land", "plant", "defuse")
    gait = (0, 1, 0, -1)[frame % 4] if "walk" in tag else 0
    bend = 3 if crouched else 0
    if tag in ("shoot", "flinch") and frame == 0:
        bend += 1
    if tag in ("jump", "fall"):
        gait = 2 if tag == "jump" else 1

    for x, stride in ((5, gait), (9, -gait)):
        ankle = 29 - abs(stride) - (1 if crouched else 0)
        draw.rectangle((x, 19 + bend, x + 2, ankle), fill=GREEN_DARK, outline=INK)
        draw.line((x + 1, 21 + bend, x + 1, ankle - 1), fill=GREEN)
        draw.rectangle((x - 1, ankle - 1, x + 2, ankle + 1), fill=INK)
        draw.line((x, ankle - 1, x + 1, ankle - 1), fill=STEEL_DARK)

    draw.rounded_rectangle((3, 9 + bend, 12, 20 + bend), radius=2, fill=GREEN, outline=INK)
    draw.line((6, 12 + bend, 5, 18 + bend), fill=STEEL_DARK, width=2)
    draw.line((9, 12 + bend, 10, 18 + bend), fill=GREEN_DARK, width=2)
    draw.line((5, 19 + bend, 10, 19 + bend), fill=INK)
    draw.point((8, 19 + bend), fill=STEEL)

    casting = tag.startswith(("cast", "channel"))
    left, right = 0, 0
    if casting:
        left = 3 if tag.endswith(("_c", "_e", "_x")) else 1
        right = 4 if tag.endswith(("_q", "_x")) else 1
    elif tag in ("reload", "equip", "melee"):
        right = 1 + frame % 3
    elif tag == "shoot":
        right = 2
    elif tag == "victory":
        left, right = 2, 2
    else:
        left, right = gait, -gait
    for x, raised in ((1, left), (12, right)):
        wrist = 19 + bend - raised
        draw.rounded_rectangle((x, 11 + bend - max(raised, 0), x + 2, wrist), radius=1, fill=STEEL_DARK, outline=INK)
        draw.line((x + 1, 12 + bend - max(raised, 0), x + 1, wrist - 1), fill=STEEL)
        if casting and raised > 1:
            draw.point((x + 1, wrist), fill=ENERGY)

    draw.line((6, 2 + bend, 4, 7 + bend, 3, 9 + bend), fill=HAIR_DARK, width=2)
    draw.rounded_rectangle((4, 2 + bend, 11, 11 + bend), radius=2, fill=SKIN, outline=INK)
    draw.polygon([(5, 3 + bend), (7, 1 + bend), (10, 2 + bend), (11, 5 + bend), (6, 5 + bend)], fill=HAIR)
    draw.rectangle((6, 8 + bend, 10, 10 + bend), fill=HAIR_DARK)
    draw.line((7, 9 + bend, 9, 9 + bend), fill=HAIR)
    draw.point((6, 6 + bend), fill=INK)
    draw.point((9, 6 + bend), fill=INK)
    return sprite


def icon(slot: str) -> Image.Image:
    image = Image.new("RGBA", (32, 32), CLEAR)
    d = ImageDraw.Draw(image)
    if slot == "C":
        d.rectangle((5, 5, 9, 26), fill=STEEL_DARK)
        for x in (12, 19):
            d.line((x, 9, x + 6, 16, x, 23), fill=ENERGY, width=3)
    elif slot == "Q":
        d.polygon([(16, 3), (18, 12), (29, 16), (18, 19), (16, 29), (13, 19), (3, 16), (13, 12)], fill=ENERGY)
        d.ellipse((13, 13, 18, 18), fill="#fff5e7")
    elif slot == "E":
        d.line((4, 23, 10, 23, 12, 10, 17, 26, 21, 6, 25, 16, 29, 16), fill=ENERGY, width=3)
    else:
        for y in (8, 15, 22):
            d.line((4, y + 5, 15, y, 28, y + 5), fill=ENERGY, width=3)
    return image


def export_agent(agent, draw_pose, draw_icon) -> None:
    idle = draw_pose("idle", 0)
    dead = idle.transpose(Image.Transpose.ROTATE_90)
    for state in STATES:
        tag = state.tag
        if tag == "portrait":
            frames = [idle.crop((0, 0, 16, 16)).resize((32, 32), Image.Resampling.NEAREST)]
        elif tag == "killfeed":
            frames = [idle.crop((0, 0, 16, 16))]
        elif tag == "select":
            frames = [idle.resize((32, 64), Image.Resampling.NEAREST)]
        elif tag == "dead":
            frames = [dead]
        elif tag == "dying":
            frames = [idle.rotate(angle, center=(8, 17)) for angle in (20, 45, 70)]
        else:
            frames = [draw_pose(tag, i) for i in range(state.frames[0])]
        stem = f"agents/{agent}/{agent}_{tag}"
        save(strip(frames), f"{stem}.png")
        if tag not in ("portrait", "select", "killfeed"):
            save(strip([enemy_variant(frame) for frame in frames]), f"{stem}_enemy.png")
    for slot in "CQEX":
        save(draw_icon(slot), f"ui/ability_{agent}_{slot}.png")
    export(agent, replace=True)


if __name__ == "__main__":
    export_agent("breach", pose, icon)
