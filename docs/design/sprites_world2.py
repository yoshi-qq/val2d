"""Map elements, second set: more floors, walls, large objects, nature and decals. Original designs.

Usage: python docs/design/sprites_world2.py
Output: assets/maps/common (tiles), assets/maps/common/props (objects), assets/maps/common/decals.
Objects are value masks lit automatically (sprites_buy_hd.render): 1 base, 2 accent, 3 dark, 4 glass, 5 light metal, 6 gold.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sprites as base  # noqa: E402
import sprites_buy_hd as lit  # noqa: E402
import sprites_world as w1  # noqa: E402

hexc, darker, lighter, save = base.hexc, base.darker, base.lighter, base.save
T, PROPS, DECALS = "maps/common/", "maps/common/props/", "maps/common/decals/"


def blank(w: int, h: int) -> Image.Image:
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def masked(w: int, h: int, paint, colours: dict[int, str]) -> Image.Image:
    mask = Image.new("L", (w, h), 0)
    paint(ImageDraw.Draw(mask))
    return lit.render(mask, colours)


# ------------------------------------------------------------------ floors
def make_floors() -> None:
    save(w1.seamless(w1.noise_tile("#3e3d44", 30, 21, 0.08, 0.85)), T + "floor_asphalt.png")
    plate = Image.new("RGBA", (32, 32), hexc("#6b7480"))
    p = plate.load()
    for y in range(32):
        for x in range(32):
            if (x % 6 == 1 and y % 6 in (1, 2)) or (x % 6 == 4 and y % 6 in (4, 5)):
                p[x, y] = hexc("#8a93a0")
            elif (x % 6 == 2 and y % 6 == 2) or (x % 6 == 5 and y % 6 == 5):
                p[x, y] = hexc("#4a525c")
    save(w1.edge_light(plate), T + "floor_metal_plate.png")
    planks = Image.new("RGBA", (32, 32), hexc("#8a6a44"))
    p = planks.load()
    rng = random.Random(4)
    for y in range(32):
        for x in range(32):
            row = y // 8
            if y % 8 == 7 or (x + row * 11) % 32 == 0:
                p[x, y] = hexc("#5e4630")
            elif y % 8 == 0:
                p[x, y] = hexc("#a0805a")
            elif rng.random() < 0.04:
                p[x, y] = hexc("#765a3a")
    save(planks, T + "floor_planks.png")
    carpet = Image.new("RGBA", (32, 32), hexc("#6a2a32"))
    p = carpet.load()
    for y in range(32):
        for x in range(32):
            if (x + y) % 8 == 0 or (x - y) % 8 == 0:
                p[x, y] = hexc("#7e3a42")
            if x % 16 == 0 or y % 16 == 0:
                p[x, y] = hexc("#8a6a2a")
    save(carpet, T + "floor_carpet.png")
    grass = w1.seamless(w1.noise_tile("#4a6a34", 60, 7, 0.14, 0.8))
    p = grass.load()
    for _ in range(14):
        x, y = rng.randrange(32), rng.randrange(1, 32)
        p[x, y] = hexc("#6a8a44")
        p[x, y - 1] = hexc("#7a9a50")
    save(grass, T + "floor_grass.png")
    save(w1.seamless(w1.noise_tile("#857e74", 90, 8, 0.18, 0.75)), T + "floor_gravel.png")
    dark = Image.new("RGBA", (32, 32), hexc("#3a3843"))
    p = dark.load()
    for y in range(32):
        for x in range(32):
            if x % 16 == 0 or y % 16 == 0:
                p[x, y] = hexc("#2a2832")
            elif x % 16 == 1 or y % 16 == 1:
                p[x, y] = hexc("#46444f")
    save(dark, T + "floor_tiles_dark.png")
    cobble = Image.new("RGBA", (32, 32), hexc("#4a4650"))
    d = ImageDraw.Draw(cobble)
    for row in range(4):
        for i in range(-1, 5):
            x0 = i * 8 + (4 if row % 2 else 0)
            tone = 104 + ((i * 7 + row * 3) % 4) * 8
            d.rounded_rectangle((x0 + 1, row * 8 + 1, x0 + 7, row * 8 + 7), radius=2, fill=(tone, tone - 6, tone + 6, 255))
    save(cobble, T + "floor_cobble.png")


# ------------------------------------------------------------------ walls
def make_walls() -> None:
    sheet = Image.new("RGBA", (32, 32), hexc("#5a6670"))
    p = sheet.load()
    for y in range(32):
        for x in range(32):
            k = x % 4
            p[x, y] = hexc(("#6e7a84", "#5a6670", "#46525c", "#5a6670")[k])
    save(w1.edge_light(sheet, 0.1, 0.7), T + "wall_metal_sheet.png")
    bags = blank(32, 32)
    d = ImageDraw.Draw(bags)
    for row in range(4):
        for i in range(-1, 3):
            x0 = i * 16 + (8 if row % 2 else 0)
            d.rounded_rectangle((x0 + 1, row * 8, x0 + 15, row * 8 + 7), radius=3, fill=hexc("#a8946a"), outline=hexc("#6b5c40"))
            d.line([(x0 + 3, row * 8 + 1), (x0 + 13, row * 8 + 1)], fill=hexc("#c0ad82"))
    save(bags, T + "wall_sandbags.png")
    stone = Image.new("RGBA", (32, 32), hexc("#4e4a52"))
    d = ImageDraw.Draw(stone)
    rng = random.Random(9)
    for row in range(4):
        x = -rng.randrange(0, 8)
        while x < 32:
            wdt = rng.randrange(7, 13)
            tone = rng.randrange(96, 124)
            d.rectangle((x + 1, row * 8 + 1, x + wdt - 1, row * 8 + 7), fill=(tone, tone - 4, tone + 6, 255))
            d.line([(x + 1, row * 8 + 1), (x + wdt - 1, row * 8 + 1)], fill=(tone + 18, tone + 14, tone + 22, 255))
            x += wdt
    save(stone, T + "wall_stone.png")
    cont = Image.new("RGBA", (32, 32), hexc("#8a3a2a"))
    p = cont.load()
    for y in range(32):
        for x in range(32):
            p[x, y] = hexc(("#a04a36", "#8a3a2a", "#6e2e22", "#8a3a2a")[y % 4])
    save(w1.edge_light(cont, 0.12, 0.7), T + "wall_container.png")
    chain = blank(32, 32)
    p = chain.load()
    for y in range(32):
        for x in range(32):
            if (x + y) % 6 == 0 or (x - y) % 6 == 0:
                p[x, y] = (170, 176, 184, 200)
    for x in range(32):
        p[x, 0] = (120, 126, 134, 255)
        p[x, 31] = (120, 126, 134, 255)
    for y in range(32):
        p[0, y] = (90, 96, 104, 255)
    save(chain, T + "fence_chainlink.png")
    hedge = w1.seamless(w1.noise_tile("#2f5a2e", 90, 13, 0.18, 0.7))
    w1.edge_light(hedge, 0.1, 0.65)
    save(hedge, T + "wall_hedge.png")
    barrier = masked(32, 32, lambda d: (d.rectangle((0, 8, 31, 23), fill=1), d.rectangle((0, 12, 31, 19), fill=5),
                                        d.rectangle((14, 8, 17, 23), fill=3)), {1: "#8a8790", 3: "#4a4850", 5: "#a8a5ae"})
    save(barrier, T + "wall_jersey_barrier.png")


# ------------------------------------------------------------------ objects
def make_objects() -> None:
    def container(d: ImageDraw.ImageDraw) -> None:
        d.rectangle((0, 0, 95, 31), fill=2)
        for x in range(2, 92, 4):
            d.line([(x, 2), (x, 29)], fill=3)
        d.rectangle((0, 0, 95, 1), fill=1)
        d.rectangle((90, 2, 95, 29), fill=1)
        d.line([(92, 4), (92, 27)], fill=3)
        for x, y in ((2, 2), (93, 2), (2, 29), (93, 29)):
            d.point((x, y), fill=5)
    save(masked(96, 32, container, {1: "#6a6670", 2: "#3e6a7a", 3: "#2a4a56", 5: "#c7ccd2"}), PROPS + "container_large.png")

    def car(d: ImageDraw.ImageDraw) -> None:
        d.rounded_rectangle((2, 2, 61, 29), radius=8, fill=2)
        d.rounded_rectangle((18, 5, 44, 26), radius=4, fill=1)  # roof
        d.rectangle((14, 6, 18, 25), fill=4)  # windscreen
        d.rectangle((44, 7, 47, 24), fill=4)  # rear window
        for x in (8, 50):
            d.rectangle((x, 0, x + 7, 2), fill=3)
            d.rectangle((x, 29, x + 7, 31), fill=3)
        d.rectangle((59, 7, 61, 10), fill=6)
        d.rectangle((59, 21, 61, 24), fill=6)
    save(masked(64, 32, car, {1: "#7a3a3a", 2: "#a04a46", 3: "#1b1a1a", 4: "#8fb3bd", 6: "#fff3b0"}), PROPS + "car.png")

    def generator(d: ImageDraw.ImageDraw) -> None:
        d.rectangle((0, 2, 23, 15), fill=2)
        d.rectangle((2, 4, 13, 13), fill=1)
        for x in range(3, 13, 2):
            d.line([(x, 5), (x, 12)], fill=3)
        d.ellipse((16, 5, 21, 10), fill=6)
        d.rectangle((0, 0, 23, 1), fill=3)
    save(masked(24, 16, generator, {1: "#4a525c", 2: "#c9a227", 3: "#26252b", 6: "#ff5a4f"}), PROPS + "generator.png")

    def dumpster(d: ImageDraw.ImageDraw) -> None:
        d.rectangle((0, 0, 31, 19), fill=2)
        d.rectangle((1, 1, 15, 18), fill=1)
        d.rectangle((16, 1, 30, 18), fill=1)
        d.line([(15, 1), (15, 18)], fill=3)
    save(masked(32, 20, dumpster, {1: "#3e5a3a", 2: "#2a3e27", 3: "#16201a"}), PROPS + "dumpster.png")

    def stack(d: ImageDraw.ImageDraw) -> None:
        d.rectangle((0, 0, 23, 23), fill=1)
        d.rectangle((2, 2, 21, 21), fill=2)
        d.line([(2, 2), (21, 21)], fill=1, width=2)
        d.line([(21, 2), (2, 21)], fill=1, width=2)
        d.rectangle((10, 10, 13, 13), fill=3)
    save(masked(24, 24, stack, {1: "#8a6a40", 2: "#a8804f", 3: "#5e4630"}), PROPS + "crate_stack.png")

    def vending(d: ImageDraw.ImageDraw) -> None:
        d.rectangle((0, 0, 15, 11), fill=2)
        d.rectangle((2, 2, 9, 9), fill=4)
        d.rectangle((11, 2, 13, 4), fill=6)
        d.rectangle((11, 6, 13, 9), fill=3)
    save(masked(16, 12, vending, {2: "#3a6a8a", 3: "#1b1a1a", 4: "#cfe3e8", 6: "#e0b437", 1: "#3a6a8a"}), PROPS + "vending_machine.png")

    def table(d: ImageDraw.ImageDraw) -> None:
        d.rectangle((0, 0, 23, 15), fill=1)
        d.rectangle((2, 2, 21, 13), fill=2)
    save(masked(24, 16, table, {1: "#6b5236", 2: "#8a6a44"}), PROPS + "table.png")
    save(masked(8, 8, lambda d: (d.rectangle((0, 0, 7, 7), fill=1), d.rectangle((1, 0, 6, 2), fill=3)),
                {1: "#6b5236", 3: "#4a3824"}), PROPS + "chair.png")

    def tree(d: ImageDraw.ImageDraw) -> None:
        d.ellipse((0, 2, 20, 22), fill=1)
        d.ellipse((10, 0, 31, 20), fill=1)
        d.ellipse((6, 10, 28, 31), fill=1)
        d.ellipse((10, 8, 20, 18), fill=2)
        d.ellipse((14, 14, 17, 17), fill=3)
    save(masked(32, 32, tree, {1: "#3e6a34", 2: "#4f8a42", 3: "#4a3020"}), PROPS + "tree.png")
    save(masked(16, 16, lambda d: (d.ellipse((0, 2, 9, 11), fill=1), d.ellipse((5, 0, 15, 10), fill=1), d.ellipse((3, 5, 14, 15), fill=1),
                                   d.ellipse((6, 5, 10, 9), fill=2)), {1: "#3e6a34", 2: "#5a9a4a"}), PROPS + "bush.png")
    save(masked(16, 12, lambda d: (d.polygon([(1, 8), (4, 2), (10, 0), (15, 4), (14, 10), (5, 11)], fill=1),
                                   d.polygon([(5, 4), (9, 2), (11, 5), (7, 6)], fill=5)), {1: "#6e6a74", 5: "#8e8a94"}), PROPS + "rock.png")
    pipe = masked(32, 8, lambda d: (d.rectangle((0, 1, 31, 6), fill=1), d.rectangle((0, 1, 31, 2), fill=5),
                                    d.rectangle((14, 0, 17, 7), fill=3)), {1: "#6b7480", 3: "#3e4248", 5: "#8a93a0"})
    save(pipe, PROPS + "pipe.png")
    save(masked(16, 16, lambda d: (d.rectangle((1, 1, 14, 14), fill=1), d.rectangle((3, 3, 12, 12), fill=2)),
                {1: "#5c5866", 2: "#6e6a78"}), PROPS + "pillar.png")
    save(masked(16, 12, lambda d: (d.rectangle((0, 0, 15, 11), fill=1), d.line([(0, 5), (15, 5)], fill=3), d.rectangle((6, 4, 9, 7), fill=2)),
                {1: "#b89468", 2: "#d8c8a0", 3: "#8a6a44"}), PROPS + "boxes_cardboard.png")
    save(masked(8, 8, lambda d: (d.ellipse((0, 0, 7, 7), fill=1), d.ellipse((2, 2, 5, 5), fill=3)),
                {1: "#4a525c", 3: "#1b1a1a"}), PROPS + "trash_bin.png")
    save(masked(16, 32, lambda d: ([d.rectangle((2, 0, 3, 31), fill=1), d.rectangle((12, 0, 13, 31), fill=1)],
                                   [d.rectangle((2, y, 13, y + 1), fill=5) for y in range(3, 31, 6)]),
                {1: "#8a8790", 5: "#a8a5ae"}), PROPS + "ladder.png")
    save(masked(12, 12, lambda d: (d.polygon([(6, 0), (11, 6), (6, 11), (0, 6)], fill=2), d.rectangle((5, 3, 6, 7), fill=3),
                                   d.rectangle((5, 8, 6, 8), fill=3)), {1: "#e0b437", 2: "#e0b437", 3: "#1b1a1a"}), PROPS + "warning_sign.png")


# ------------------------------------------------------------------ decals
def alpha_blob(size: int, colour: tuple[int, int, int], alpha: int, seed: int, squash: float = 1.0) -> Image.Image:
    rng = random.Random(seed)
    im = blank(size, size)
    p = im.load()
    c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            dd = math.hypot((x - c) / squash, y - c) / (size / 2)
            if dd < 0.9 and rng.random() < 1.1 - dd:
                p[x, y] = colour + (int(alpha * (1 - dd * 0.6)),)
    return im


def make_decals() -> None:
    save(alpha_blob(32, (70, 96, 120), 150, 2, 1.4), DECALS + "puddle.png")
    tire = blank(32, 32)
    p = tire.load()
    for y in range(32):
        for off in (9, 21):
            x = off + int(2 * math.sin(y / 6))
            for dx in range(3):
                if (y + dx) % 3:
                    p[x + dx, y] = (20, 18, 24, 120)
    save(tire, DECALS + "tire_marks.png")
    line = blank(32, 4)
    ImageDraw.Draw(line).rectangle((0, 1, 31, 2), fill=(232, 230, 220, 190))
    save(line, DECALS + "paint_line.png")
    steps = blank(16, 16)
    for x, y in ((3, 1), (9, 5), (3, 9), (9, 13)):
        ImageDraw.Draw(steps).ellipse((x, y, x + 2, y + 3), fill=(30, 26, 22, 110))
    save(steps, DECALS + "footprints.png")
    tuft = base.from_rows(["..G..G..", ".GG.GG..", "GGGGGGG.", "........"], {"G": "#5a8a3a"})
    save(tuft, DECALS + "grass_tuft.png")
    manhole = masked(16, 16, lambda d: (d.ellipse((0, 0, 15, 15), fill=3), d.ellipse((2, 2, 13, 13), fill=1),
                                        [d.line([(4, y), (11, y)], fill=3) for y in (5, 8, 11)]), {1: "#5a5f66", 3: "#26252b"})
    save(manhole, DECALS + "manhole.png")
    leaves = blank(32, 32)
    rng = random.Random(6)
    for _ in range(22):
        x, y = rng.randrange(30), rng.randrange(31)
        c = rng.choice(((160, 110, 50), (190, 140, 60), (120, 90, 40)))
        leaves.load()[x, y] = c + (200,)
        leaves.load()[x + 1, y] = c + (150,)
    save(leaves, DECALS + "leaves.png")
    cross = blank(16, 16)
    d = ImageDraw.Draw(cross)
    d.line([(2, 2), (13, 13)], fill=(224, 180, 55, 170), width=2)
    d.line([(13, 2), (2, 13)], fill=(224, 180, 55, 170), width=2)
    save(cross, DECALS + "paint_x.png")


def main() -> None:
    make_floors()
    make_walls()
    make_objects()
    make_decals()


if __name__ == "__main__":
    main()
