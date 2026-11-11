"""Load and scale the design session's sprites (docs/SPRITES.md).

Scale 16 px = 1 m. Scaling is nearest neighbour only (pygame.transform.scale), never smoothed.
If a file is missing, the bank returns None and play.py draws the placeholder; one warning per file.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
PX_PER_M = 16
WALK_FPS = 8.0


class SpriteBank:
    def __init__(self) -> None:
        self._raw: dict[str, pygame.Surface | None] = {}
        self._scaled: dict[tuple[str, int, int, int], pygame.Surface] = {}
        self._warned: set[str] = set()

    def raw(self, rel: str) -> pygame.Surface | None:
        """Image relative to assets/, e.g. 'agents/kestrel/kestrel_idle.png'."""
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

    # ------------------------------------------------------------ Characters
    def agent(self, agent: str, pose: str, enemy: bool, scale: float, t: float) -> pygame.Surface | None:
        """pose: idle, walk, crouch, jump, dead. Size from the scale, walk cycle at WALK_FPS frames per second."""
        suffix = "_feind" if enemy else ""
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
        suffix = "_feind" if enemy else ""
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
    folder = f"maps/{world.key}"
    tile_px = max(1, round(2 * scale))  # tile 32 px = 2 m

    def tile(name: str) -> pygame.Surface | None:
        rel = f"{folder}/{name}.png" if (ASSETS / folder / f"{name}.png").exists() else f"maps/werkhof/{name}.png"
        return bank.scaled(rel, (tile_px, tile_px))

    floor = tile("boden_stein")
    if floor is None:
        return None
    w_px, h_px = round(world.width * scale), round(world.height * scale)
    surf = pygame.Surface((w_px, h_px)).convert() if pygame.display.get_surface() else pygame.Surface((w_px, h_px))

    def to_px(r: object) -> pygame.Rect:
        x0, y0, x1, y1 = r.x0, r.y0, r.x1, r.y1  # type: ignore[attr-defined]
        left, top = round(x0 * scale), round((world.height - y1) * scale)
        return pygame.Rect(left, top, max(1, round(x1 * scale) - left), max(1, round((world.height - y0) * scale) - top))

    _tile_rect(surf, floor, surf.get_rect())
    layers: list[tuple[str, pygame.Rect]] = []
    layers += [("platz_rand", to_px(s.rect)) for s in world.sites]
    layers += [("plattform", to_px(p.rect)) for p in world.platforms]
    layers += [("rampe", to_px(r)) for r in world.ramps]
    platform_rects = {p.rect for p in world.platforms}
    for wall in world.walls:
        if wall.rect in platform_rects:
            continue
        if wall.rect.x0 < -0.5 or wall.rect.y0 < -0.5 or wall.rect.x1 > world.width + 0.5 or wall.rect.y1 > world.height + 0.5:
            continue
        if wall.height == 1 and not wall.blocks_sight:
            name = "kiste_metall"
        else:
            name = "wand_duenn" if wall.penetration <= 1 else "wand"
        layers.append((name, to_px(wall.rect)))
    for name, rect in layers:
        t = tile(name)
        if t is None:
            pygame.draw.rect(surf, (110, 106, 120), rect)
        else:
            _tile_rect(surf, t, rect)
    return surf
