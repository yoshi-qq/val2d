"""Load and scale the design session's sprites (docs/SPRITES.md).

Scale 16 px = 1 m. Scaling is nearest neighbour only (pygame.transform.scale), never smoothed.
If a file is missing, the bank returns None and play.py draws the placeholder; one warning per file.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import pygame

from gameplay.geometry import Rect, Vec
from gameplay.skins import SKIN_LINES

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
PX_PER_M = 16
WALK_FPS = 8.0


class SpriteBank:
    def __init__(self) -> None:
        self._raw: dict[str, pygame.Surface | None] = {}
        self._scaled: dict[tuple[str, int, int, int], pygame.Surface] = {}
        self._warned: set[str] = set()
        self._weapon_skins: dict[tuple[str, str], pygame.Surface] = {}
        self._weapon_pictures: dict[tuple[str, str, tuple[int, int], str], pygame.Surface] = {}

    def raw(self, rel: str) -> pygame.Surface | None:
        """Image relative to assets/, e.g. 'agents/omen/omen_idle.png'."""
        if rel not in self._raw:
            path = ASSETS / rel
            try:
                img = pygame.image.load(str(path))
                self._raw[rel] = img.convert_alpha() if pygame.display.get_surface() else img
            except (OSError, pygame.error, FileNotFoundError):
                if rel not in self._warned:
                    self._warned.add(rel)
                    warnings.warn(f"Sprite missing: assets/{rel}; drawing a placeholder.")
                self._raw[rel] = None
        return self._raw[rel]

    def frame(self, rel: str, index: int, frame_w: int) -> pygame.Surface | None:
        """Frame index from a horizontal strip with frame width frame_w (in file pixels)."""
        img = self.raw(rel)
        if img is None:
            return None
        count = max(1, img.get_width() // frame_w)
        x = (index % count) * frame_w
        return img.subsurface((x, 0, frame_w, img.get_height()))

    def scaled(self, rel: str, size: tuple[int, int], index: int = 0, frame_w: int = 0) -> pygame.Surface | None:
        w, h = max(1, size[0]), max(1, size[1])
        key = (rel, w, h, index if frame_w else -1)
        hit = self._scaled.get(key)
        if hit is not None:
            return hit
        src = self.frame(rel, index, frame_w) if frame_w else self.raw(rel)
        if src is None:
            return None
        if len(self._scaled) > 2048:
            self._scaled.clear()
        out = pygame.transform.scale(src, (w, h))
        self._scaled[key] = out
        return out

    def frames_in(self, rel: str, frame_w: int) -> int:
        img = self.raw(rel)
        return max(1, img.get_width() // frame_w) if img else 1

    def weapon(self, art: str, bounds: tuple[int, int], skin: str = "", *, view: str = "hand") -> pygame.Surface | None:
        """Draw the hand sprite at world scale, or fit a cropped sprite into a UI slot."""
        key = (art, skin, bounds, view)
        if key in self._weapon_pictures:
            return self._weapon_pictures[key]
        path = f"weapons/val2d/{art}.png"
        buy = f"weapons/val2d/{art}_buy.png"
        if view == "preview" and (ASSETS / buy).is_file():
            path = buy
        source = self.raw(path)
        if source is None:
            return None
        if skin in SKIN_LINES:
            source = self._skin_weapon(path, source, skin)
        size = bounds
        if view != "hand":
            crop = source.get_bounding_rect()
            if not crop:
                return None
            source = source.subsurface(crop)
            size = crop.fit(pygame.Rect(0, 0, *bounds)).size
        image = pygame.transform.scale(source, size)
        if len(self._weapon_pictures) >= 1024:
            self._weapon_pictures.clear()
        self._weapon_pictures[key] = image
        return image

    def _skin_weapon(self, path: str, source: pygame.Surface, skin: str) -> pygame.Surface:
        key = (path, skin)
        if key not in self._weapon_skins:
            line = SKIN_LINES[skin]
            palette = [pygame.Color(tone) for tone in line.palette]
            image = source.copy()
            for y in range(source.get_height()):
                pattern = line.pattern[y % len(line.pattern)]
                for x in range(source.get_width()):
                    pixel = source.get_at((x, y))
                    if not pixel.a:
                        continue
                    value = (pixel.r * 3 + pixel.g * 6 + pixel.b) // 10
                    tone = sum(value >= stop for stop in (35, 76, 110))
                    if tone in (1, 2) and pattern[x % len(pattern)] == "#":
                        tone = 4
                    ink = palette[tone]
                    image.set_at((x, y), (ink.r, ink.g, ink.b, pixel.a))
            self._weapon_skins[key] = image
        return self._weapon_skins[key]

    # ------------------------------------------------------------ Characters
    def agent(self, agent: str, pose: str, enemy: bool, scale: float, t: float) -> pygame.Surface | None:
        """pose: idle, walk, crouch, jump, dead. Size from the scale, walk cycle at WALK_FPS frames per second."""
        suffix = "_enemy" if enemy else ""
        rel = f"agents/{agent}/{agent}_{pose}{suffix}.png"
        if pose == "dead":
            return self.scaled(rel, (round(2 * scale), round(1 * scale)))
        size = (round(1 * scale), round(2 * scale))
        if pose == "walk":
            index = int(t * WALK_FPS) % self.frames_in(rel, 16)
            return self.scaled(rel, size, index, 16)
        return self.scaled(rel, size)

    def agent_frame(self, agent: str, pose: str, enemy: bool, scale: float, progress: float) -> pygame.Surface | None:
        """Action strip (shoot, reload, cast) at progress 0..1; None if the strip is missing."""
        suffix = "_enemy" if enemy else ""
        rel = f"agents/{agent}/{agent}_{pose}{suffix}.png"
        if self.raw(rel) is None:
            return None
        count = self.frames_in(rel, 16)
        index = min(count - 1, max(0, int(progress * count)))
        return self.scaled(rel, (round(scale), round(2 * scale)), index, 16)

    def strip_frame(self, rel: str, size: tuple[int, int], progress: float, frame_w: int) -> pygame.Surface | None:
        """Frame of an effect strip at progress 0..1 (clamped)."""
        if self.raw(rel) is None:
            return None
        count = self.frames_in(rel, frame_w)
        return self.scaled(rel, size, min(count - 1, max(0, int(progress * count))), frame_w)

    def tinted(self, rel: str, size: tuple[int, int], index: int, frame_w: int, color: tuple[int, int, int]) -> pygame.Surface | None:
        key = (f"{rel}#{color}", size[0], size[1], index)
        hit = self._scaled.get(key)
        if hit is not None:
            return hit
        base = self.scaled(rel, size, index, frame_w)
        if base is None:
            return None
        out = base.copy()
        out.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self._scaled[key] = out
        return out


# ------------------------------------------------------------ Map
def _tile_rect(target: pygame.Surface, tile: pygame.Surface, rect: pygame.Rect) -> None:
    """Tiles tile over rect; the tile grid is anchored at the map origin so neighbouring areas line up."""
    tw, th = tile.get_size()
    clip = target.get_clip()
    target.set_clip(rect.clip(clip) if clip else rect)
    x0 = rect.x - rect.x % tw
    y0 = rect.y - rect.y % th
    for y in range(y0, rect.bottom, th):
        for x in range(x0, rect.right, tw):
            target.blit(tile, (x, y))
    target.set_clip(clip)


def build_map_surface(world: object, bank: SpriteBank, scale: float) -> pygame.Surface | None:
    """The map as one image at screen scale (scale pixels per metre), north (+y) up.

    Pixel (0, 0) is world (0, height). None if the floor tile is missing.
    """
    from gameplay.world import WorldMap  # for types only; gameplay stays free of pygame

    assert isinstance(world, WorldMap)
    folder = f"maps/{world.art or world.key}"
    tile_px = max(1, round(2 * scale))  # tile 32 px = 2 m

    def tile(name: str) -> pygame.Surface | None:
        rel = f"{folder}/{name}.png" if (ASSETS / folder / f"{name}.png").exists() else f"maps/workyard/{name}.png"
        return bank.scaled(rel, (tile_px, tile_px))

    from gameplay.world import load_materials
    wall_mats, floor_mats = load_materials()

    def mat_tile(rel: str) -> pygame.Surface | None:
        return bank.scaled(rel, (tile_px, tile_px)) if (ASSETS / rel).exists() else None

    floor = mat_tile(floor_mats.get(world.floor, "")) if world.floor else None
    floor = floor or tile("stone_floor")
    if floor is None:
        return None
    w_px, h_px = round(world.width * scale), round(world.height * scale)
    surf = pygame.Surface((w_px, h_px)).convert() if pygame.display.get_surface() else pygame.Surface((w_px, h_px))

    def to_px(r: object) -> pygame.Rect:
        x0, y0, x1, y1 = r.x0, r.y0, r.x1, r.y1  # type: ignore[attr-defined]
        left, top = round(x0 * scale), round((world.height - y1) * scale)
        return pygame.Rect(left, top, max(1, round(x1 * scale) - left), max(1, round((world.height - y0) * scale) - top))

    _tile_rect(surf, floor, surf.get_rect())
    for mat, rect in world.floors:
        patch = mat_tile(floor_mats.get(mat, ""))
        if patch is not None:
            _tile_rect(surf, patch, to_px(rect))
    layers: list[tuple[str, pygame.Rect]] = []
    layers += [("site_border", to_px(s.rect)) for s in world.sites]
    # platform look: its own floor material, "floor" = keep the floor art under it, empty = the shared platform tile
    layers += [(f"floor:{p.mat}" if p.mat else "platform", to_px(p.rect)) for p in world.platforms if p.mat != "floor"]
    layers += [("ramp", to_px(r)) for r in world.ramps]
    platform_rects = {p.rect for p in world.platforms}
    object_rects = {o.rect for o in world.objects} | {w.rect for w in world.walls if w.material.startswith("obj:")}
    for wall in world.walls:
        if wall.rect in platform_rects or wall.rect in object_rects:
            continue
        if wall.rect.x0 < -0.5 or wall.rect.y0 < -0.5 or wall.rect.x1 > world.width + 0.5 or wall.rect.y1 > world.height + 0.5:
            continue
        if wall.material and wall.material in wall_mats:
            layers.append(("mat:" + wall_mats[wall.material].get("tile", ""), to_px(wall.rect)))
            continue
        if wall.height == 1 and not wall.blocks_sight:
            name = "metal_crate"
        else:
            name = "wall_thin" if wall.penetration <= 1 else "wall"
        layers.append((name, to_px(wall.rect)))
    for name, rect in layers:
        if name.startswith("floor:"):
            t = mat_tile(floor_mats.get(name[6:], ""))
        else:
            t = mat_tile(name[4:]) if name.startswith("mat:") else tile(name)
        if t is None:
            pygame.draw.rect(surf, (110, 106, 120), rect)
        else:
            _tile_rect(surf, t, rect)
    # decals, then static objects (animated ones are drawn live by play.py)
    from gameplay.world import load_things
    objects, decals = load_things()

    def place(spec: dict, thing: object) -> None:
        img = bank.raw(str(spec.get("tile", "")))
        if img is None:
            return
        r = to_px(thing.rect)  # type: ignore[attr-defined]
        rot = int(thing.rot)  # type: ignore[attr-defined]
        frames = int(spec.get("frames", 1))
        src = img.subsurface((0, 0, img.get_width() // frames, img.get_height())) if frames > 1 else img
        if rot:
            src = pygame.transform.rotate(src, -rot)
        if spec.get("tiled"):
            w_m, h_m = spec.get("size", (1.0, 1.0))
            if rot in (90, 270):
                w_m, h_m = h_m, w_m
            piece = pygame.transform.scale(src, (max(1, round(w_m * scale)), max(1, round(h_m * scale))))
            _tile_rect(surf, piece, r)
        else:
            surf.blit(pygame.transform.scale(src, (r.w, r.h)), r.topleft)

    for d in world.decals:
        place(decals.get(d.key, {}), d)
    for o in world.objects:
        spec = objects.get(o.key, {})
        if int(spec.get("frames", 1)) == 1 and not spec.get("buy_phase_only") and not spec.get("door") and not spec.get("hp"):
            place(spec, o)
    # shadow under the south edge of full-height walls, edge strip on platforms
    shadow = bank.scaled("maps/common/wall_shadow.png", (tile_px, max(1, round(tile_px / 4))))
    edge = bank.scaled("maps/common/platform_edge.png", (tile_px, max(1, round(tile_px / 8))))
    for wall in world.walls:
        if shadow is None or wall.rect in platform_rects or wall.rect in object_rects or wall.height < 2:
            continue
        if wall.rect.y0 <= 0 or wall.rect.x1 <= 0 or wall.rect.x0 >= world.width:
            continue
        r = to_px(wall.rect)
        _tile_rect(surf, shadow, pygame.Rect(r.x, r.bottom, r.w, shadow.get_height()))
    for pl in world.platforms:
        if edge is None:
            continue
        # edge strip only where the floor just south of the platform is lower (not between platforms of one level)
        x, step = pl.rect.x0, 0.5
        while x < pl.rect.x1 - 1e-6:
            x_end = min(pl.rect.x1, x + step)
            if world.ground_height(Vec((x + x_end) / 2, pl.rect.y0 - 0.1)) < pl.level - 0.01:
                r = to_px(Rect(x, pl.rect.y0, x_end, pl.rect.y1))
                _tile_rect(surf, edge, pygame.Rect(r.x, r.bottom - edge.get_height(), r.w, edge.get_height()))
            x = x_end
    # site letters painted on the floor
    for site in world.sites:
        mark = bank.scaled(f"maps/common/decals/site_{site.name.lower()}.png", (tile_px, tile_px))
        if mark is not None:
            c = to_px(site.rect).center
            surf.blit(mark, (c[0] - mark.get_width() / 2, c[1] - mark.get_height() / 2))
    return surf


# ------------------------------------------------------------ Character states (docs/design/CHARACTER_SHEETS.md)
SPEC_PATH = ROOT / "docs" / "design" / "character_sheet_spec.py"
_BUILTIN_STATES: dict[str, tuple[float | None, bool, str | None]] = {
    # tag: (fps, loop, fallback); used if the spec file is missing
    "idle": (4, True, None), "walk": (8, True, "idle"), "crouch": (4, True, "idle"), "crouch_walk": (6, True, "crouch"),
    "jump": (8, False, "idle"), "fall": (8, False, "jump"), "land": (12, False, "idle"), "shoot": (12, False, "idle"),
    "reload": (None, False, "idle"), "equip": (None, False, "idle"), "melee": (12, False, "shoot"),
    "flinch": (12, False, "idle"), "plant": (4, True, "crouch"), "defuse": (4, True, "crouch"),
    "cast_c": (8, False, "cast"), "cast_q": (8, False, "cast"), "cast_e": (8, False, "cast"), "cast_x": (8, False, "cast"),
    "channel_c": (6, True, "cast_c"), "channel_q": (6, True, "cast_q"), "channel_e": (6, True, "cast_e"),
    "channel_x": (6, True, "cast_x"), "cast": (8, False, "idle"), "dying": (10, False, "dead"), "dead": (None, False, None),
    "victory": (4, True, "idle"), "portrait": (None, False, None), "killfeed": (None, False, "portrait"),
    "select": (None, False, "portrait"),
}
SCREEN_STATES = ("_portrait", "_killfeed", "_select")
_SIZES_M: dict[str, tuple[float, float]] = {"dead": (2, 1), "portrait": (2, 2), "killfeed": (1, 1), "select": (2, 4)}


def load_states() -> dict[str, tuple[float | None, bool, str | None]]:
    """State table from the design spec (fps, loop, fallback); built-in copy if the spec is unreadable."""
    import runpy
    try:
        states = runpy.run_path(str(SPEC_PATH)).get("STATES") or []
        table = {s.tag: (s.fps, bool(s.loop), s.fallback) for s in states}
        return table or dict(_BUILTIN_STATES)
    except Exception as exc:  # the spec is a design file; the game must run without it
        warnings.warn(f"Character sheet spec unreadable ({exc}); using built-in states.")
        return dict(_BUILTIN_STATES)


class CharacterSprites:
    """Picks the frame for an agent state, following the fallback chain of the spec.

    state: tag from the spec, or "mech_<name>" (falls back to idle).
    clock: seconds since the state began (fps states) or progress 0..1 (fps None, stretched states).
    form: active form name, tries {key}@{form}_{state}.png first.
    """

    def __init__(self, bank: SpriteBank) -> None:
        self.bank = bank
        self.states = load_states()
        self._resolved: dict[tuple[str, str, bool, str | None, str], tuple[str, str] | None] = {}

    def _file(self, agent: str, name: str, enemy: bool) -> str:
        if enemy and name.endswith(SCREEN_STATES):  # screen pictures have no enemy outline
            enemy = False
        return f"agents/{agent}/{name}{'_enemy' if enemy else ''}.png"

    def resolve(self, agent: str, state: str, enemy: bool, form: str | None = None, view: str = "") -> tuple[str, str] | None:
        """(file, state actually used) after fallbacks, or None if not even idle exists (cached per call key).
        view "back" or "side": tries {key}_{state}_{view}.png first, else the front view."""
        key = (agent, state, enemy, form, view)
        if key not in self._resolved:
            found = None
            if view and not form:
                rel = self._file(agent, f"{agent}_{state}_{view}", enemy)
                found = (rel, state) if (ASSETS / rel).exists() else None
            self._resolved[key] = found or self._resolve(agent, state, enemy, form)
        return self._resolved[key]

    def _resolve(self, agent: str, state: str, enemy: bool, form: str | None) -> tuple[str, str] | None:
        seen: set[str] = set()
        tag: str | None = state
        while tag and tag not in seen:
            seen.add(tag)
            if form:
                rel = self._file(agent, f"{agent}@{form}_{tag}", enemy)
                if (ASSETS / rel).exists():
                    return rel, tag
            rel = self._file(agent, f"{agent}_{tag}", enemy)
            if (ASSETS / rel).exists():
                return rel, tag
            tag = "idle" if tag.startswith("mech_") else self.states.get(tag, (None, False, "idle"))[2]
        return None

    def duration(self, agent: str, state: str, enemy: bool = False) -> float:
        """Play time of a non-looping fps state (frames / fps), 0 if unknown."""
        found = self.resolve(agent, state, enemy)
        if not found:
            return 0.0
        fps = self.states.get(found[1], (None, False, None))[0]
        return self.bank.frames_in(found[0], self._cell_w(found[1])) / fps if fps else 0.0

    def _cell_w(self, tag: str) -> int:
        return round(_SIZES_M.get(tag, (1, 2))[0] * PX_PER_M)

    def has_view(self, agent: str, state: str, enemy: bool, view: str) -> bool:
        found = self.resolve(agent, state, enemy, None, view)
        return bool(found and found[0].endswith(f"_{view}{'_enemy' if enemy else ''}.png"))

    def frame(self, agent: str, state: str, enemy: bool, scale: float, clock: float,
              form: str | None = None, speed: float = 1.0, view: str = "") -> pygame.Surface | None:
        found = self.resolve(agent, state, enemy, form, view)
        if not found:
            return None
        rel, tag = found
        fps, loop, _ = self.states.get(tag, (8, True, None)) if not tag.startswith("mech_") else (8, True, None)
        cell_w = self._cell_w(tag)
        count = self.bank.frames_in(rel, cell_w)
        if fps is None:
            index = min(count - 1, max(0, int(clock * count)))
        else:
            index = int(clock * fps * speed)
            index = index % count if loop else min(count - 1, index)
        if tag != state and state.startswith("channel_") and tag.startswith("cast_"):
            index = count - 1  # channel falls back to the last frame of its cast
        w_m, h_m = _SIZES_M.get(tag, (1, 2))
        return self.bank.scaled(rel, (round(w_m * scale), round(h_m * scale)), index, cell_w)

    def overlays(self, agent: str, names: list[str], enemy: bool, scale: float, walk_index: int) -> list[pygame.Surface]:
        out = []
        for name in names:
            rel = self._file(agent, f"{agent}_overlay_{name}", enemy)
            if self.bank.raw(rel) is None:
                continue
            count = self.bank.frames_in(rel, 16)
            img = self.bank.scaled(rel, (round(scale), round(2 * scale)), walk_index % count, 16)
            if img is not None:
                out.append(img)
        return out


def draw_nine_slice(target: pygame.Surface, bank: SpriteBank, rel: str, rect: pygame.Rect, corner: int, k: int = 2) -> bool:
    """Draws a 9-slice frame: `corner` px corners in the file, pixels scaled k times (nearest). False if missing."""
    img = bank.raw(rel)
    if img is None:
        return False
    w, h = img.get_size()
    c, d = corner, corner * k
    parts = [((0, 0, c, c), (rect.x, rect.y, d, d)),
             ((w - c, 0, c, c), (rect.right - d, rect.y, d, d)),
             ((0, h - c, c, c), (rect.x, rect.bottom - d, d, d)),
             ((w - c, h - c, c, c), (rect.right - d, rect.bottom - d, d, d)),
             ((c, 0, w - 2 * c, c), (rect.x + d, rect.y, rect.w - 2 * d, d)),
             ((c, h - c, w - 2 * c, c), (rect.x + d, rect.bottom - d, rect.w - 2 * d, d)),
             ((0, c, c, h - 2 * c), (rect.x, rect.y + d, d, rect.h - 2 * d)),
             ((w - c, c, c, h - 2 * c), (rect.right - d, rect.y + d, d, rect.h - 2 * d)),
             ((c, c, w - 2 * c, h - 2 * c), (rect.x + d, rect.y + d, rect.w - 2 * d, rect.h - 2 * d))]
    for src, dst in parts:
        if dst[2] > 0 and dst[3] > 0:
            target.blit(pygame.transform.scale(img.subsurface(src), (dst[2], dst[3])), (dst[0], dst[1]))
    return True
