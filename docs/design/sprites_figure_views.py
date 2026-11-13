"""Export the back and right profile of each playable agent's animation strips."""
from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from character_sheet_spec import CELL_H, CELL_W, STATES
from sprites import ASSETS, CLEAR, enemy_variant, hexc, strip


@dataclass(frozen=True)
class Look:
    head_rows: int
    head: str
    head_shadow: str
    hair_or_hat: str
    skin: str
    jacket: str
    jacket_shadow: str
    trim: str
    trim_shadow: str
    outline: str
    rear_mark: tuple[str, ...]


LOOKS = {
    "brimstone": Look(10, "#c88b68", "#9b5c45", "#e0712c", "#ebb08b",
                     "#3c4a57", "#2e3a44", "#8c9ea4", "#5e717e", "#19202a",
                     ("tt..tt", "ss..ss", "ssssss", "stttts", "ssssss")),
    "omen": Look(15, "#414d95", "#303b7d", "#414d95", "#303b7d",
                 "#4f5b5e", "#212e31", "#414d95", "#303b7d", "#0f1c20",
                 ("tttt..", ".tttt.", "..tttt", "...ttt", "....tt")),
    "jett": Look(12, "#e7eef2", "#a7bacb", "#e7eef2", "#dfae99",
                 "#6596a4", "#334b67", "#c3cfdb", "#447483", "#172033",
                 ("..tt..", ".tttt.", "tttttt", ".tttt.", "..tt..")),
    "sova": Look(11, "#dbc58e", "#9e845f", "#dbc58e", "#d3a394",
                 "#475369", "#29446e", "#e2dfd0", "#8496aa", "#171d29",
                 ("tttttt", "tt..tt", "s.tt.s", "s.tt.s", "s....s")),
    "sage": Look(12, "#494957", "#292939", "#494957", "#d9ab95",
                 "#eeeaf0", "#b9b5c8", "#46b99c", "#267c79", "#181924",
                 ("..tt..", "..tt..", ".tttt.", "..tt..", "..ss..")),
    "cypher": Look(12, "#365777", "#222838", "#e1ddd0", "#365777",
                   "#e1ddd0", "#b7b7b1", "#b5825b", "#797e89", "#171d29",
                   ("tt....", ".tt...", "..tt..", "...tt.", "....tt")),
    "phoenix": Look(11, "#272321", "#603c37", "#bd7844", "#bd8062",
                    "#e3e4df", "#b6bdc5", "#ffba59", "#fc8033", "#1b202a",
                    ("..t...", "..tt..", ".tts..", "..stt.", "..tt..")),
    "killjoy": Look(11, "#382e2b", "#1b2028", "#366654", "#deb199",
                    "#f6cf50", "#d5a238", "#366654", "#2c4d43", "#1b2028",
                    ("..tt..", ".tttt.", ".t..t.", ".tttt.", "..ss..")),
    "breach": Look(11, "#a74927", "#65301e", "#d66d33", "#dba17b",
                   "#63734f", "#3c4a39", "#abb9b7", "#667979", "#212924",
                   ("t....t", ".tttt.", ".tsst.", "..tt..", "..ss..")),
    "reyna": Look(13, "#322044", "#21162e", "#633779", "#bc8267",
                  "#34284d", "#231b35", "#a457c1", "#613c82", "#171123",
                  (".tttt.", ".tttt.", "..tt..", "..tt..", ".s..s.")),
}

EXCLUDED = {"dead", "dying", "portrait", "killfeed", "select"}


def frames(path: Path) -> list[Image.Image]:
    with Image.open(path) as image:
        if image.height != CELL_H or image.width % CELL_W:
            raise ValueError(f"{path}: expected a strip of {CELL_W}x{CELL_H} frames")
        rgba = image.convert("RGBA")
    return [rgba.crop((x, 0, x + CELL_W, CELL_H)) for x in range(0, rgba.width, CELL_W)]


def head_offset(frame: Image.Image, idle: Image.Image, look: Look) -> tuple[int, int]:
    """Match the upper head so leaning and crouching carry over to the new view."""
    landmarks = [(x, y, idle.getpixel((x, y))) for y in range(1, look.head_rows - 4)
                 for x in range(2, 14) if idle.getpixel((x, y))[3]]

    def score(offset: tuple[int, int]) -> float:
        dx, dy = offset
        hits = sum(frame.getpixel((x + dx, y + dy)) == colour for x, y, colour in landmarks)
        return hits - 0.2 * (abs(dx) + abs(dy))

    return max(((x, y) for x in range(-2, 3) for y in range(-1, 7)), key=score)


def back_frame(frame: Image.Image, look: Look, offset: tuple[int, int]) -> Image.Image:
    out = frame.copy()
    px = out.load()
    dx, dy = offset
    head, shade, hat, line = map(hexc, (look.head, look.head_shadow, look.hair_or_hat, look.outline))
    cloth, shadow, trim, trim_shadow = map(hexc, (look.jacket, look.jacket_shadow, look.trim, look.trim_shadow))
    head_end = look.head_rows + dy

    for y in range(max(0, head_end - 6), head_end):
        for x in range(max(0, 3 + dx), min(CELL_W, 13 + dx)):
            colour = px[x, y]
            if not colour[3] or colour in (hat, head, shade):
                continue
            if colour == line and any(not frame.getpixel((x + ox, y + oy))[3]
                                      for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1))):
                continue
            # The hair, helmet or hood wraps around the back of the head.
            px[x, y] = head if x < 8 + dx and y < head_end - 2 else shade

    # Back panel and shoulder details sit over the chest and any hands in front.
    # Keep the outer sleeves, legs and effects from the animated pose.
    for row in range(8):
        y = head_end + row
        if y >= CELL_H - 7:
            break
        for x in range(5, 11):
            if not px[x, y][3]:
                continue
            detail = look.rear_mark[row - 1][x - 5] if 1 <= row <= len(look.rear_mark) else "."
            px[x, y] = {"t": trim, "s": trim_shadow, ".": cloth if x < 9 and row < 7 else shadow}[detail]
    return out


def profile_frame(frame: Image.Image, look: Look, offset: tuple[int, int]) -> Image.Image:
    dx, dy = offset
    head_end = look.head_rows + dy
    out = Image.new("RGBA", frame.size, CLEAR)
    src, dst = frame.load(), out.load()
    head, shadow, skin, line = map(hexc, (look.head, look.head_shadow, look.skin, look.outline))
    trim = hexc(look.trim)
    # Project the far leg and arm behind the near ones. Feet keep their original
    # height and their forward step, which keeps the walk aligned with the map.
    for y in range(CELL_H):
        for x in range(CELL_W):
            colour = src[x, y]
            if not colour[3]:
                continue
            if y < head_end and 3 + dx <= x < 13 + dx:
                target_x = 5 + (x - 3 + dx) * 2 // 3
            elif y >= head_end + 11:
                target_x = x + 2 if x < 8 else x
            else:
                target_x = 4 + x // 2
                if x >= 11:
                    target_x += 1
                if x >= 12 and head_end + 4 <= y < head_end + 9 and colour == skin:
                    target_x += 1
            if 0 <= target_x < CELL_W:
                dst[target_x, y] = colour

    face_y = head_end - 4
    face_x = 10 + max(-1, min(1, dx))
    if 0 <= face_y < CELL_H - 3:
        draw = ImageDraw.Draw(out)
        # One visible eye and a nose set the direction of the profile. Omen's
        # hood and Cypher's mask keep their own face material.
        eye = hexc("#73effa") if look.head == "#414d95" else line
        if look.head == "#365777":
            eye = hexc("#9deaff")
        draw.line((face_x - 2, face_y - 1, face_x - 2, face_y + 1), fill=head)
        draw.line((face_x, face_y - 1, face_x, face_y + 2), fill=skin)
        draw.point((face_x, face_y), fill=eye)
        draw.point((face_x + 1, face_y + 1), fill=skin)
        draw.point((face_x, face_y + 3), fill=shadow)
        if look.head == "#382e2b":
            draw.point((face_x, face_y), fill=hexc("#add6ee"))
        if look.head == "#414d95":
            draw.point((face_x + 1, face_y + 1), fill=shadow)
        if head_end + 2 < CELL_H and dst[7, head_end + 2][3]:
            draw.point((7, head_end + 2), fill=trim)
    return out


def export(agent: str, replace: bool) -> int:
    look = LOOKS[agent]
    folder = ASSETS / "agents" / agent
    idle = frames(folder / f"{agent}_idle.png")[0]
    count = 0
    for state in STATES:
        if state.tag in EXCLUDED:
            continue
        stem = f"{agent}_{state.tag}"
        source = frames(folder / f"{stem}.png")
        offsets = [head_offset(frame, idle, look) for frame in source]
        for view, draw in (("back", back_frame), ("side", profile_frame)):
            rendered = [draw(frame, look, offset) for frame, offset in zip(source, offsets)]
            for suffix, images in (("", rendered), ("_enemy", [enemy_variant(frame) for frame in rendered])):
                path = folder / f"{stem}_{view}{suffix}.png"
                if replace or not path.exists():
                    strip(images).save(path)
                    count += 1
    return count


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("agents", nargs="*", metavar="AGENT")
    parser.add_argument("--replace", action="store_true", help="Replace existing directional strips.")
    args = parser.parse_args()
    unknown = set(args.agents) - LOOKS.keys()
    if unknown:
        parser.error(f"unknown agents: {', '.join(sorted(unknown))}")
    print(f"Exported {sum(export(agent, args.replace) for agent in (args.agents or LOOKS))} directional strips.")
