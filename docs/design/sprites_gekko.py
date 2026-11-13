"""Gekko's lime buzz cut, violet vest and four radivores in the Val2D palette."""
from PIL import Image, ImageDraw

from sprites import CLEAR, save, strip
from sprites_breach import export_agent
from sprites_figure_views import LOOKS, Look
from sprites_miks import pose as base_pose

INK, LIME, HAIR_SHADE = "#231b2b", "#c9e84b", "#79873b"
VIOLET, PURPLE_SHADE, TRIM = "#775b9f", "#4a3766", "#bd9cdd"
GREEN, GOLD, CYAN, RED = "#a9ec69", "#ffc874", "#6be4f9", "#f37a9c"
CREATURES = dict(mosh=GREEN, wingman=GOLD, dizzy=CYAN, thrash=RED)
WARDROBE = {
    "#483047": LIME, "#322438": HAIR_SHADE, "#f28243": VIOLET,
    "#9e423e": PURPLE_SHADE, "#ffc071": TRIM, "#d9f586": GREEN,
}
WARDROBE = {tuple(bytes.fromhex(a[1:])) + (255,): tuple(bytes.fromhex(b[1:])) + (255,)
            for a, b in WARDROBE.items()}


def pose(tag, frame):
    source = base_pose(tag, frame)
    source.putdata([WARDROBE.get(pixel, pixel) for pixel in source.getdata()])
    draw = ImageDraw.Draw(source)
    bend = 3 if tag.startswith("crouch") or tag in ("land", "plant", "defuse") else int(tag == "flinch" and frame == 0)
    draw.rounded_rectangle((4, 2 + bend, 11, 5 + bend), radius=1, fill=LIME)
    draw.line((4, 5 + bend, 10, 5 + bend), fill=HAIR_SHADE)
    draw.point((3, 14 + bend), fill="#354858")
    return source


def creature(name, size=16):
    image = Image.new("RGBA", (16, 16), CLEAR)
    draw = ImageDraw.Draw(image)
    color = CREATURES[name]
    if name == "wingman":
        draw.polygon([(2, 4), (5, 6), (8, 3), (12, 5), (14, 9), (13, 14), (10, 14),
                      (9, 12), (7, 12), (6, 14), (3, 14), (2, 10)], fill=color, outline=INK)
        draw.line((6, 8, 10, 8), fill=INK, width=2)
    elif name == "thrash":
        draw.polygon([(0, 5), (5, 7), (8, 3), (11, 6), (15, 7), (14, 11), (7, 13), (4, 11), (0, 13)],
                     fill=color, outline=INK)
        draw.line((10, 9, 13, 9), fill="#fff4e0")
        draw.point((12, 7), fill=INK)
    elif name == "dizzy":
        draw.polygon([(0, 6), (4, 5), (8, 2), (12, 5), (15, 6), (13, 10), (9, 13), (5, 11), (2, 10)],
                     fill=color, outline=INK)
        draw.ellipse((5, 5, 11, 10), fill=VIOLET)
        draw.ellipse((7, 6, 9, 8), fill="#f3fdff")
    else:
        draw.ellipse((1, 4, 14, 13), fill=color, outline=INK)
        draw.line((5, 4, 6, 1, 8, 4), fill=color, width=2)
        draw.point((5, 8), fill=INK)
        draw.point((10, 8), fill=INK)
    return image.resize((size, size), Image.Resampling.NEAREST)


def icon(slot):
    return creature(dict(C="mosh", Q="wingman", E="dizzy", X="thrash")[slot], 32)


if __name__ == "__main__":
    LOOKS["gekko"] = Look(10, LIME, HAIR_SHADE, LIME, "#ca8864", VIOLET, PURPLE_SHADE, GREEN, TRIM, INK,
                         ("s....s", ".ssss.", ".tttt.", "..tt..", "..ss.."))
    export_agent("gekko", pose, icon)
    for name, color in CREATURES.items():
        save(creature(name), f"fx/gekko_{name}.png")
        globe = Image.new("RGBA", (16, 16), CLEAR)
        draw = ImageDraw.Draw(globe)
        draw.ellipse((2, 2, 13, 13), fill=PURPLE_SHADE, outline=color, width=2)
        draw.ellipse((5, 5, 10, 10), fill=color)
        save(globe, f"fx/gekko_globule_{name}.png")
    for name, color in (("pit", GREEN), ("plasma", CYAN)):
        frames = []
        for phase in range(3):
            area = Image.new("RGBA", (64, 64), CLEAR)
            draw = ImageDraw.Draw(area)
            draw.ellipse((1, 1, 62, 62), fill=(122, 205, 82, 75) if name == "pit" else (68, 183, 248, 115),
                         outline=color, width=2)
            for x, y, r in ((20, 24, 5), (41, 19, 4), (39, 39, 7), (22, 43, 4), (32, 29, 8)):
                draw.ellipse((x-r-phase, y-r, x+r+phase, y+r), outline=color, width=1)
            frames.append(area)
        save(strip(frames), f"fx/gekko_{name}.png")
