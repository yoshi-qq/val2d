"""Builds the character sheet templates under docs/design/templates/.

Usage: python docs/design/character_templates.py
Outputs:
  character_guides.png        16x32 guide layer for Aseprite (hit zones, anchor, ground row)
  character_guides_x8.png     same, scaled x8 for reading
  character_sheet_layout.png  every state as a row with its frame slots (reference)
  example_omen_sheet.png   the layout filled with Omen's existing strips
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character_sheet_spec import ANCHOR, CELL_H, CELL_W, GROUND_ROW, STATES, ZONES  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "templates"
ZONE_COLOURS = {"head": (238, 76, 74, 70), "body": (224, 180, 55, 60), "legs": (79, 214, 200, 60)}


def guide_cell() -> Image.Image:
    im = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    p = im.load()
    for name, z in ZONES.items():
        (x0, x1), (y0, y1) = z["x"], z["y"]
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                p[x, y] = ZONE_COLOURS[name]
    for x in range(CELL_W):
        p[x, GROUND_ROW] = (255, 255, 255, 110)
    for x in (0, CELL_W - 1):
        for y in range(CELL_H):
            p[x, y] = (255, 255, 255, 40)
    ax, ay = ANCHOR
    for d in (-1, 0, 1):
        p[ax + d, ay] = (255, 255, 255, 200)
        p[ax, ay + d] = (255, 255, 255, 200)
    return im


def font() -> ImageFont.ImageFont:
    return ImageFont.load_default()


def layout(example: str | None = None) -> Image.Image:
    scale = 3
    label_w = 150
    gap = 4
    rows = []
    for st in STATES:
        w, h = st.size
        rows.append((st, w, h))
    max_frames = max(s.frames[1] for s in STATES)
    width = label_w + max_frames * (CELL_W * 2 * scale + gap) + 20
    height = sum(h * scale + 14 for _, _, h in rows) + 40
    im = Image.new("RGBA", (width, height), (31, 30, 39, 255))
    d = ImageDraw.Draw(im)
    f = font()
    title = "Val2d character sheet layout" + (f" - example: {example}" if example else "")
    d.text((10, 10), title, fill=(232, 230, 239), font=f)
    guide = guide_cell().resize((CELL_W * scale, CELL_H * scale), Image.NEAREST)
    y = 34
    for st, w, h in rows:
        req = "required" if st.required else f"optional -> {st.fallback}"
        fps = f"{st.fps:g} fps" if st.fps else "stretched" if st.tag in ("reload", "equip") else "still"
        d.text((10, y), st.tag, fill=(232, 230, 239) if st.required else (155, 152, 170), font=f)
        d.text((10, y + 12), f"{st.frames[0]}-{st.frames[1]} fr, {fps}", fill=(155, 152, 170), font=f)
        d.text((10, y + 24), req, fill=(79, 214, 200) if st.required else (120, 118, 134), font=f)
        strip = None
        if example:
            path = ROOT / "assets" / "agents" / example / f"{example}_{st.tag}.png"
            if path.exists():
                strip = Image.open(path).convert("RGBA")
        x = label_w
        for i in range(st.frames[1]):
            cw, ch = w * scale, h * scale
            box = (x, y, x + cw - 1, y + ch - 1)
            optional_slot = i >= st.frames[0]
            d.rectangle(box, outline=(80, 78, 92) if optional_slot else (130, 126, 146), fill=(43, 42, 52, 255))
            if (w, h) == (CELL_W, CELL_H):
                im.alpha_composite(guide, (x, y))
            if strip is not None and strip.height == h and (i + 1) * w <= strip.width:
                frame = strip.crop((i * w, 0, (i + 1) * w, h)).resize((cw, ch), Image.NEAREST)
                im.alpha_composite(frame, (x, y))
            d.text((x + 2, y + ch - 11), str(i + 1), fill=(155, 152, 170), font=f)
            x += cw + gap
        y += h * scale + 14
    return im


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    g = guide_cell()
    g.save(OUT / "character_guides.png")
    g.resize((CELL_W * 8, CELL_H * 8), Image.NEAREST).save(OUT / "character_guides_x8.png")
    layout().save(OUT / "character_sheet_layout.png")
    layout("omen").save(OUT / "example_omen_sheet.png")
    for name in ("character_guides.png", "character_guides_x8.png", "character_sheet_layout.png", "example_omen_sheet.png"):
        print("written:", (OUT / name).relative_to(ROOT))


if __name__ == "__main__":
    main()
