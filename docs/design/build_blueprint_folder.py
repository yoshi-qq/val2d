"""Builds docs/design/blueprint/: one empty template for every kind of sprite Val2d uses,
with guides, plus an index (README.md), the style guide and a palette.

Usage: python docs/design/build_blueprint_folder.py
Templates are transparent PNGs at the exact size and frame count of the real sprite; guides are
faint, meant for a locked "guides" layer in Aseprite. Regenerate after changing the spec.
"""
from __future__ import annotations

import math
import runpy
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from character_sheet_spec import ANCHOR, GROUND_ROW, STATES, ZONES  # noqa: E402

ROOT = HERE.parents[1]
OUT = HERE / "blueprint"

Guide = Callable[[Image.Image, int, int, int], None]  # image, frame x offset, frame w, frame h

A_ZONE = {"head": (238, 76, 74, 70), "body": (224, 180, 55, 60), "legs": (79, 214, 200, 60)}
WHITE = (255, 255, 255)


def dot(p, x: int, y: int, a: int, w: int, h: int, ox: int = 0) -> None:
    if 0 <= x < w and 0 <= y < h:
        p[ox + x, y] = WHITE + (a,)


# ------------------------------------------------------------------ guides
def g_agent(im: Image.Image, ox: int, w: int, h: int) -> None:
    p = im.load()
    for name, z in ZONES.items():
        (x0, x1), (y0, y1) = z["x"], z["y"]
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                p[ox + x, y] = A_ZONE[name]
    for x in range(w):
        dot(p, x, GROUND_ROW, 110, w, h, ox)
    for y in range(h):
        dot(p, 0, y, 40, w, h, ox)
        dot(p, w - 1, y, 40, w, h, ox)
    ax, ay = ANCHOR
    for d in (-1, 0, 1):
        dot(p, ax + d, ay, 200, w, h, ox)
        dot(p, ax, ay + d, 200, w, h, ox)


def g_dead(im: Image.Image, ox: int, w: int, h: int) -> None:
    """Figure lying, head on the left: zones rotated."""
    p = im.load()
    for name, z in ZONES.items():
        (x0, x1), (y0, y1) = z["x"], z["y"]
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                ry, rx = 15 - x, y  # rotate 90° counter-clockwise into 32x16
                if 0 <= rx < w and 0 <= ry < h:
                    p[ox + rx, ry] = A_ZONE[name]


def g_box(margin: int) -> Guide:
    def guide(im: Image.Image, ox: int, w: int, h: int) -> None:
        p = im.load()
        for x in range(margin, w - margin):
            dot(p, x, margin, 90, w, h, ox)
            dot(p, x, h - 1 - margin, 90, w, h, ox)
        for y in range(margin, h - margin):
            dot(p, margin, y, 90, w, h, ox)
            dot(p, w - 1 - margin, y, 90, w, h, ox)
    return guide


def g_corners(im: Image.Image, ox: int, w: int, h: int) -> None:
    p = im.load()
    for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        dot(p, x, y, 120, w, h, ox)


def g_circle(im: Image.Image, ox: int, w: int, h: int) -> None:
    p = im.load()
    cx, cy, r = (w - 1) / 2, (h - 1) / 2, min(w, h) / 2 - 0.5
    for a in range(0, 360, 4):
        dot(p, int(round(cx + math.cos(math.radians(a)) * r)), int(round(cy + math.sin(math.radians(a)) * r)), 110, w, h, ox)
    for d in (-1, 0, 1):
        dot(p, int(cx) + d, int(cy), 180, w, h, ox)
        dot(p, int(cx), int(cy) + d, 180, w, h, ox)
    g_corners(im, ox, w, h)


def g_tile(im: Image.Image, ox: int, w: int, h: int) -> None:
    """Light from the top left: light edge top/left, shadow edge bottom/right."""
    p = im.load()
    for i in range(w):
        p[ox + i, 0] = (255, 255, 255, 70)
        p[ox + i, h - 1] = (0, 0, 0, 90)
    for i in range(h):
        p[ox + 0, i] = (255, 255, 255, 70)
        p[ox + w - 1, i] = (0, 0, 0, 90)
    for i in range(0, w, 2):
        dot(p, i, h // 2, 35, w, h, ox)
        dot(p, w // 2, i, 35, w, h, ox)


def g_weapon(im: Image.Image, ox: int, w: int, h: int) -> None:
    """Side view, muzzle right: barrel axis, grip zone, muzzle column."""
    p = im.load()
    axis = int(3.5 * h / 8)
    for x in range(w):
        dot(p, x, axis, 60, w, h, ox)
    for y in range(h):
        dot(p, w - 1, y, 130, w, h, ox)
    gx0, gx1 = int(w * 0.3), int(w * 0.45)
    for y in range(int(h * 0.62), h):
        for x in range(gx0, gx1):
            p[ox + x, y] = (224, 180, 55, 50)


def g_icon(im: Image.Image, ox: int, w: int, h: int) -> None:
    g_box(2)(im, ox, w, h)


def g_icon_ult(im: Image.Image, ox: int, w: int, h: int) -> None:
    p = im.load()
    for i in range(1, w - 1):
        for x, y in ((i, 0), (i, h - 1), (0, i), (w - 1, i)):
            p[ox + x, y] = (224, 180, 55, 120)
    g_box(2)(im, ox, w, h)


def g_nine(im: Image.Image, ox: int, w: int, h: int, corner: int = 4) -> None:
    p = im.load()
    for i in range(w):
        dot(p, i, corner, 90, w, h, ox)
        dot(p, i, h - 1 - corner, 90, w, h, ox)
    for i in range(h):
        dot(p, corner, i, 90, w, h, ox)
        dot(p, w - 1 - corner, i, 90, w, h, ox)


def g_nine8(im: Image.Image, ox: int, w: int, h: int) -> None:
    g_nine(im, ox, w, h, 8)


def g_bar(im: Image.Image, ox: int, w: int, h: int) -> None:
    p = im.load()
    for x in range(1, w - 1):
        for y in range(1, h - 1):
            p[ox + x, y] = (224, 180, 55, 45) if y < 3 else (224, 180, 55, 25)


def g_banner(im: Image.Image, ox: int, w: int, h: int) -> None:
    p = im.load()
    for x in range(3, w - 3):
        p[ox + x, 2] = (79, 214, 200, 110)
        p[ox + x, h - 3] = (79, 214, 200, 70)
    for y in range(6, 15):
        for x in range(12, w - 12):
            p[ox + x, y] = (255, 255, 255, 30)


def g_portrait(im: Image.Image, ox: int, w: int, h: int) -> None:
    p = im.load()
    for x in range(w):
        for y in range(h):
            p[ox + x, y] = (39, 38, 49, 255)
    head = (int(w * 0.25), int(h * 0.06), int(w * 0.75), int(h * 0.62))
    for x in range(head[0], head[2]):
        for y in range(head[1], head[3]):
            p[ox + x, y] = (238, 76, 74, 45)


def g_select(im: Image.Image, ox: int, w: int, h: int) -> None:
    """32x64 = the 16x32 figure at 2x: zones scaled."""
    p = im.load()
    for name, z in ZONES.items():
        (x0, x1), (y0, y1) = z["x"], z["y"]
        for y in range(y0 * 2, (y1 + 1) * 2):
            for x in range(x0 * 2, (x1 + 1) * 2):
                p[ox + x, y] = A_ZONE[name]


def g_trail(im: Image.Image, ox: int, w: int, h: int) -> None:
    g_agent(im, ox, w, h)


def g_none(im: Image.Image, ox: int, w: int, h: int) -> None:
    g_corners(im, ox, w, h)


# ------------------------------------------------------------------ catalogue
@dataclass(frozen=True)
class Entry:
    file: str          # path inside blueprint/
    target: str        # where the finished sprite goes
    size: tuple[int, int]
    frames: int
    fps: str
    purpose: str
    guide: Guide
    category: str
    example: str | None = None  # finished sprite (path from the repo root) shown on top of the template


def _config(name: str, probe: str) -> dict:
    try:
        data = runpy.run_path(str(ROOT / "config" / f"{name}.py"))
    except Exception as exc:  # the blueprint must still build
        print(f"warning: config/{name}.py not readable: {exc}")
        return {}
    for value in data.values():
        if isinstance(value, dict) and probe in value:
            return value
    return {}


def catalogue() -> list[Entry]:
    e: list[Entry] = []
    for st in STATES:
        guide = {"dead": g_dead, "portrait": g_portrait, "killfeed": g_portrait, "select": g_select}.get(st.tag, g_agent)
        fps = f"{st.fps:g} fps" if st.fps else ("stretched" if st.tag in ("reload", "equip") else "still")
        need = "required" if st.required else f"optional, falls back to {st.fallback}"
        e.append(Entry(f"agents/agent_{st.tag}.png", f"assets/agents/{{key}}/{{key}}_{st.tag}.png", st.size, st.frames[1],
                       fps, f"{st.note} ({need}; {st.frames[0]}–{st.frames[1]} frames, template has the maximum)", guide, "Agents",
                       f"assets/agents/kestrel/kestrel_{st.tag}.png"))
    e += [
        Entry("agents/agent_mech_NAME.png", "assets/agents/{key}/{key}_mech_{name}.png", (16, 32), 6, "6 fps",
              "extra state for a special mechanic (glide, hover, carry); 1–6 frames, loops, falls back to idle", g_agent, "Agents",
              "docs/design/blueprint/examples/source/kestrel_mech_glide.png"),
        Entry("agents/agent@FORM_idle.png", "assets/agents/{key}/{key}@{form}_{state}.png", (16, 32), 4, "as the state",
              "form: replaces a state while the form is active; draw at least idle and walk", g_agent, "Agents",
              "docs/design/blueprint/examples/source/kestrel@overdrive_walk.png"),
        Entry("agents/agent_overlay_NAME.png", "assets/agents/{key}/{key}_overlay_{name}.png", (16, 32), 4, "as walk",
              "overlay on top of every state (glowing eyes, shield shell); 1 frame or as many as walk", g_agent, "Agents",
              "overlay:assets/agents/kestrel/kestrel_idle.png+docs/design/blueprint/examples/source/kestrel_overlay_shield.png"),
    ]
    weapons = _config("weapons", "spatz")
    keys = ", ".join(k for k in weapons if k != "messer") or "see config/weapons.py"
    e += [
        Entry("weapons/weapon_hand.png", "assets/weapons/val2d/{key}.png", (16, 8), 1, "still",
              f"weapon in hand, side view, muzzle right; keys: {keys}", g_weapon, "Weapons", "assets/weapons/val2d/falke.png"),
        Entry("weapons/weapon_buy.png", "assets/weapons/val2d/{key}_kauf.png", (64, 24), 1, "still",
              "buy-menu icon, 64 × 24, centred, lit automatically with outline (docs/design/sprites_buy_hd.py)", g_weapon, "Weapons", "assets/weapons/val2d/falke_kauf.png"),
        Entry("weapons/knife.png", "assets/weapons/val2d/messer.png", (16, 8), 1, "still", "knife, blade right", g_weapon, "Weapons", "assets/weapons/val2d/messer.png"),
    ]
    for name, file, purpose in (
        ("floor", "boden_stein", "walkable floor, 2 × 2 m, tiles seamlessly"),
        ("wall_thick", "wand", "thick wall top (penetration 2–3)"),
        ("wall_thin", "wand_duenn", "thin wall top (penetration 0–1), visibly lighter material"),
        ("crate", "kiste_metall", "crate seen from above, height 1 level, can be climbed"),
        ("platform", "plattform", "raised floor (level 1)"),
        ("ramp", "rampe", "ramp between levels, steps run across the direction of travel"),
        ("site_border", "platz_rand", "bomb site border, transparent centre, laid over the floor"),
    ):
        e.append(Entry(f"tiles/tile_{name}.png", f"assets/maps/{{map}}/{file}.png", (32, 32), 1, "still", purpose, g_tile, "Map tiles",
                       f"assets/maps/werkhof/{file}.png"))
    fx = [
        ("bomb", "spike", (16, 16), 2, "4 fps", "bomb carried and planted: LED on, off", g_none),
        ("muzzle_flash", "muendung", (8, 8), 3, "15 fps", "muzzle flash, once per shot", g_none),
        ("wall_impact", "einschlag_wand", (8, 8), 3, "15 fps", "bullet hits a wall", g_none),
        ("body_hit", "treffer_koerper", (8, 8), 3, "15 fps", "bullet hits a body (no gore)", g_none),
        ("bomb_explosion", "spike_explosion", (64, 64), 6, "10 fps", "bomb explosion, scaled to the blast radius", g_circle),
        ("smoke", "dunst", (64, 64), 1, "still", "smoke sphere, scaled to the radius", g_circle),
        ("smoke_forming", "dunst_aufbau", (64, 64), 4, "8 fps", "smoke forming, then smoke", g_circle),
        ("zone", "zone", (64, 64), 3, "4 fps", "generic area (white, tinted per status in code)", g_circle),
        ("slow_field", "bann", (64, 64), 1, "still", "agent-specific field", g_circle),
        ("slow_field_pulse", "bann_puls", (64, 64), 3, "4 fps", "field pulse, loops", g_circle),
        ("blast", "blast", (64, 64), 6, "12 fps", "generic blast ring, scaled to the radius", g_circle),
        ("sensor", "lauscher", (6, 6), 1, "still", "small device lying on the ground", g_none),
        ("sensor_pulse", "lauscher_puls", (32, 32), 3, "6 fps", "sensor pulse ring", g_circle),
        ("flash", "funke", (16, 16), 1, "still", "flash projectile", g_circle),
        ("flash_burst", "funke_explosion", (16, 16), 3, "10 fps", "flash going off", g_circle),
        ("vapor_wall", "schleier", (16, 16), 1, "still", "wall segment, tiled along the wall", g_none),
        ("vapor_wall_forming", "schleier_aufbau", (16, 16), 3, "8 fps", "wall forming", g_none),
        ("dash_trail", "gleiten_spur", (16, 32), 3, "12 fps", "trail behind a dashing figure (same cell as the figure)", g_trail),
        ("hop_dust", "satz_staub", (16, 8), 3, "10 fps", "dust under the feet at take-off", g_none),
        ("tripwire", "tripwire", (16, 4), 1, "still", "wire, tiled along its length", g_none),
        ("tripwire_node", "tripwire_node", (6, 6), 1, "still", "wire anchor at both ends", g_none),
        ("alarm", "alarm", (16, 16), 2, "3 fps", "alarm device blinking", g_none),
        ("wave", "wave", (16, 16), 3, "10 fps", "wave band, tiled along the line", g_none),
    ]
    for name, file, size, frames, fps, purpose, guide in fx:
        e.append(Entry(f"effects/fx_{name}.png", f"assets/fx/{file}.png", size, frames, fps, purpose, guide, "Effects", f"assets/fx/{file}.png"))
    e += [
        Entry("ui/ability_icon.png", "assets/ui/faehigkeit_{agent}_{C|Q|E}.png", (32, 32), 1, "still",
              "ability icon: dark plate, 24 × 24 glyph in white with the agent's accent colour", g_icon, "Interface", "assets/ui/faehigkeit_kestrel_C.png"),
        Entry("ui/ability_icon_ult.png", "assets/ui/faehigkeit_{agent}_X.png", (32, 32), 1, "still",
              "ultimate icon: as above with a gold frame and corner highlights", g_icon_ult, "Interface", "assets/ui/faehigkeit_kestrel_X.png"),
        Entry("ui/hud_icon.png", "assets/ui/hud/{name}.png", (16, 16), 1, "still",
              "HUD icon: leben, schild, credits, munition, kopfschuss, spike_klein, uhr, tot", g_box(0), "Interface", "assets/ui/hud/schild.png"),
        Entry("ui/status_icon.png", "assets/ui/status/{status}.png", (16, 16), 1, "still",
              "status icon: nearsight, concuss, slow, vulnerable, decay, suppress, detain, deaf, stim", g_box(0), "Interface", "assets/ui/status/slow.png"),
        Entry("ui/minimap_icon.png", "assets/ui/minimap/{name}.png", (12, 12), 1, "still",
              "minimap: selbst (arrow points up), verbuendet, feind, tot, spike, dunst, bann, schleier", g_box(0), "Interface", "assets/ui/minimap/selbst.png"),
        Entry("ui/frame_nine_slice.png", "assets/ui/hud/rahmen.png, rahmen_aktiv.png", (24, 24), 1, "still",
              "nine-slice frame, 8 px corners, centre stretches", g_nine8, "Interface", "assets/ui/hud/rahmen_aktiv.png"),
        Entry("ui/bar.png", "assets/ui/hud/balken_{leben|schild|fortschritt|leer}.png", (96, 12), 1, "still",
              "bar, stretched horizontally; fill drawn over balken_leer", g_bar, "Interface", "assets/ui/hud/balken_schild.png"),
        Entry("ui/banner.png", "assets/ui/banner/{name}.png", (160, 32), 1, "still",
              "round banner, height 32, width = text + 40 px, game font fixed_sys at 16 px without smoothing", g_banner, "Interface", "assets/ui/banner/seitenwechsel.png"),
        Entry("ui/logo.png", "assets/logo.png (+ icon.ico 16/32/48)", (48, 48), 1, "still",
              "game logo, also program icon", g_box(1), "Interface", "assets/logo.png"),
        Entry("ui/player_card.png", "assets/menu/lobby/playercard.png", (64, 128), 1, "still",
              "lobby player card with logo at (8, 10)", g_box(4), "Interface", "assets/menu/lobby/playercard.png"),
    ]
    e += batch_three()
    return e


MULTI_FRAME = {"spawn_barrier": 2, "beacon": 2, "mine": 2, "anchor_marker": 2, "reveal_marker": 2, "projectile_orb": 2,
               "impact_puff": 3, "teleport": 4, "heal": 3, "revive": 4, "shield_shell": 3, "immunity_aura": 2}
BATCH_THREE = [
    ("ui/menu", "Interface: menus", "assets/ui/menu/{name}.png"),
    ("ui/icons", "Interface: icons", "assets/ui/icons/{name}.png"),
    ("ui/buy", "Interface: buy menu", "assets/ui/buy/{name}.png"),
    ("maps/common", "Map tiles: common set", "assets/maps/common/{name}.png"),
    ("maps/common/props", "Map props", "assets/maps/common/props/{name}.png"),
    ("maps/common/decals", "Map decals", "assets/maps/common/decals/{name}.png"),
    ("fx/ability", "Ability sprites (generic)", "assets/fx/ability/{name}.png"),
]


def batch_three() -> list[Entry]:
    """One template per file of the third batch, sized from the finished sprite."""
    out: list[Entry] = []
    for folder, category, target in BATCH_THREE:
        for f in sorted((ROOT / "assets" / folder).glob("*.png")):
            name = f.stem
            with Image.open(f) as im:
                w, h = im.size
            frames = MULTI_FRAME.get(name, 1)
            fw = w // frames
            if folder == "maps/common" and (fw, h) == (32, 32):
                guide: Guide = g_tile
            elif (fw, h) == (16, 32):
                guide = g_agent
            elif name.startswith(("button", "panel", "textfield", "tab", "checkbox")):
                guide = g_nine
            elif fw >= 24 and h >= 24 and fw == h:
                guide = g_circle
            else:
                guide = g_corners
            fps = "still" if frames == 1 else ("4 fps" if frames == 2 else "10 fps")
            purpose = name.replace("_", " ")
            if name == "title_background":
                purpose = "menu background, full native screen 480 × 270, left 200 px darker for the menu buttons"
                guide = g_corners
            short = folder.replace("/", "_")
            out.append(Entry(f"{short}/{name}.png", target.format(name=name), (fw, h), frames, fps, purpose, guide,
                             category, str(f.relative_to(ROOT)).replace("\\", "/")))
    return out


# ------------------------------------------------------------------ output
def template(entry: Entry) -> Image.Image:
    w, h = entry.size
    im = Image.new("RGBA", (w * entry.frames, h), (0, 0, 0, 0))
    for i in range(entry.frames):
        entry.guide(im, i * w, w, h)
    return im


def load_example(entry: Entry) -> Image.Image | None:
    if not entry.example:
        return None
    try:
        if entry.example.startswith("overlay:"):
            under, over = entry.example[len("overlay:"):].split("+")
            im = Image.open(ROOT / under).convert("RGBA").crop((0, 0, 16, 32))
            im.alpha_composite(Image.open(ROOT / over).convert("RGBA"))
            return im
        return Image.open(ROOT / entry.example).convert("RGBA")
    except OSError as exc:
        print(f"warning: example for {entry.file} missing: {exc}")
        return None


def example_image(entry: Entry) -> Image.Image | None:
    """The finished sprite drawn over its template, so alignment with the guides is visible."""
    ex = load_example(entry)
    if ex is None:
        return None
    tpl = template(entry)
    canvas = Image.new("RGBA", (max(tpl.width, ex.width), max(tpl.height, ex.height)), (0, 0, 0, 0))
    canvas.alpha_composite(tpl)
    canvas.alpha_composite(ex)
    return canvas


def example_name(entry: Entry) -> str:
    return "examples/" + Path(entry.file).stem + ".example.png"


def overview(entries: list[Entry]) -> Image.Image:
    f = ImageFont.load_default()
    scale_for = lambda e: 4 if e.size[1] <= 16 else 3 if e.size[1] <= 32 else 2 if e.size[1] <= 64 else 1  # noqa: E731
    rows = []
    for e in entries:
        im = template(e)
        ex = example_image(e)
        if ex is not None:
            both = Image.new("RGBA", (im.width + 4 + ex.width, max(im.height, ex.height)), (0, 0, 0, 0))
            both.alpha_composite(im)
            both.alpha_composite(ex, (im.width + 4, 0))
            im = both
        s = scale_for(e)
        rows.append((e, im.resize((im.width * s, im.height * s), Image.NEAREST)))
    width = 1200
    height = 40 + sum(max(img.height, 26) + 16 for _, img in rows)
    sheet = Image.new("RGBA", (width, height), (31, 30, 39, 255))
    d = ImageDraw.Draw(sheet)
    d.text((10, 10), "Val2d sprite blueprints - template (left) and finished example (right)", fill=(232, 230, 239), font=f)
    y = 36
    category = ""
    for e, img in rows:
        if e.category != category:
            category = e.category
            d.text((10, y), category.upper(), fill=(79, 214, 200), font=f)
            y += 16
        d.text((10, y), Path(e.file).name, fill=(232, 230, 239), font=f)
        d.text((10, y + 12), f"{e.size[0]}x{e.size[1]} x{e.frames}  {e.fps}", fill=(155, 152, 170), font=f)
        bg = Image.new("RGBA", img.size, (52, 50, 60, 255))
        bg.alpha_composite(img)
        sheet.alpha_composite(bg.crop((0, 0, min(bg.width, width - 260), bg.height)), (250, y))
        y += max(img.height, 26) + 16
    return sheet


def index(entries: list[Entry]) -> str:
    lines = [
        "# Val2d sprite blueprints",
        "",
        "Every kind of sprite the game uses, as an empty template at its exact size and frame count.",
        "Open a template in Aseprite, put it on a locked `guides` layer, draw on a layer above, hide the guides and export to the target path.",
        "Rules: `STYLE_GUIDE.md` in this folder. Agents in detail: `../CHARACTER_SHEETS.md`. Colours: `palette.png`.",
        "Frames sit side by side in one strip without spacing; the template always has the maximum number of frames.",
        "Every template has a finished example in `examples/` (Kestrel and the Workyard set), drawn over the guides.",
        "Regenerate this folder with `python docs/design/build_blueprint_folder.py`.",
        "",
        "Guide colours: red = head zone, gold = body zone or grip/fill area, teal = leg zone or accent line,",
        "white cross = centre/anchor, white line = ground row, white ring = maximum radius, light/dark edge = light from the top left.",
        "",
    ]
    category = ""
    for e in entries:
        if e.category != category:
            category = e.category
            lines += ["", f"## {category}", "", "| Template | Example | Target file | Frame size | Frames | Speed | Purpose |", "|---|---|---|---|---|---|---|"]
        ex = f"[example]({example_name(e)})" if e.example else "–"
        lines.append(f"| `{e.file}` | {ex} | `{e.target}` | {e.size[0]}×{e.size[1]} | {e.frames} | {e.fps} | {e.purpose} |")
    return "\n".join(lines) + "\n"


PALETTE = [
    ("Background", ["#16151c", "#1f1e27", "#272631", "#363443"]),
    ("Darkest / outline base", ["#16151b", "#1b1a1a", "#232228", "#2d2c31"]),
    ("Neutral greys", ["#46454d", "#545c64", "#6b7480", "#7d8790", "#9b98aa", "#c7ccd2", "#e8e6ef"]),
    ("Warm materials", ["#c4ae88", "#a8956f", "#8a7660", "#7a5233", "#5a3a26", "#3a2f25"]),
    ("Accents", ["#e0b437", "#f08a24", "#ffd75e", "#fffbe8", "#9a7ad8", "#6fbf73", "#8fb3bd"]),
    ("Reserved: team and enemy", ["#4fd6c8", "#ee4c4a"]),
]


def palette() -> Image.Image:
    f = ImageFont.load_default()
    sw = 28
    im = Image.new("RGBA", (12 + 200 + 7 * (sw + 4), 12 + len(PALETTE) * (sw + 10)), (31, 30, 39, 255))
    d = ImageDraw.Draw(im)
    for r, (name, cols) in enumerate(PALETTE):
        y = 8 + r * (sw + 10)
        d.text((8, y + 8), name, fill=(232, 230, 239), font=f)
        for i, c in enumerate(cols):
            x = 210 + i * (sw + 4)
            d.rectangle((x, y, x + sw - 1, y + sw - 1), fill=c, outline=(13, 12, 18))
    return im


def main() -> None:
    entries = catalogue()
    for e in entries:
        path = OUT / e.file
        path.parent.mkdir(parents=True, exist_ok=True)
        template(e).save(path)
        ex = example_image(e)
        if ex is not None:
            (OUT / "examples").mkdir(parents=True, exist_ok=True)
            ex.save(OUT / example_name(e))
    overview(entries).save(OUT / "OVERVIEW.png")
    palette().save(OUT / "palette.png")
    (OUT / "README.md").write_text(index(entries), encoding="utf-8")
    print(f"written: {len(entries)} templates, OVERVIEW.png, palette.png, README.md in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
