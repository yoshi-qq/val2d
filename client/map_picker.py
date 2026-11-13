"""Map selection shared by the Play menu and the IP party host."""
from __future__ import annotations

import pygame

from client.ui import Ui
from gameplay.world import load_map_raw, load_playable_map
from sprite_bank import ASSETS, SpriteBank, build_map_surface


def map_name(key: str) -> str:
    try:
        return str(load_map_raw(key).get("name", key))
    except (OSError, ValueError):
        return key


class MapPicker:
    def __init__(self, names: dict[str, str], current: str) -> None:
        self.names = names
        self.keys = tuple(names)
        self.current = current
        self.focus = self.keys.index(current)
        self.previews: dict[str, pygame.Surface | None] = {}
        self.thumbnails: dict[tuple[str, tuple[int, int]], pygame.Surface | None] = {}

    def thumbnail(self, key: str, bounds: tuple[int, int], bank: SpriteBank) -> pygame.Surface | None:
        cache_key = key, bounds
        if cache_key not in self.thumbnails:
            if key not in self.previews:
                asset = f"maps/{key}/icon.png"
                preview = bank.raw(asset) if (ASSETS / asset).is_file() else None
                if preview is None:
                    world = load_playable_map(key)
                    preview = build_map_surface(world, bank, 240 / max(world.width, world.height))
                self.previews[key] = preview
            preview = self.previews[key]
            thumbnail = None
            if preview is not None:
                size = preview.get_rect().fit(pygame.Rect((0, 0), bounds)).size
                thumbnail = pygame.transform.smoothscale(preview, size)
            self.thumbnails[cache_key] = thumbnail
        return self.thumbnails[cache_key]

    @staticmethod
    def columns(width: int) -> int:
        return min(5, max(2, (width - 56) // 155))

    def key_action(self, key: int, width: int) -> str | None:
        columns = self.columns(width)
        movement = {pygame.K_LEFT: -1, pygame.K_RIGHT: 1, pygame.K_UP: -columns, pygame.K_DOWN: columns}
        if key == pygame.K_ESCAPE:
            return "map_back"
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return f"map_pick:{self.keys[self.focus]}"
        if key == pygame.K_HOME:
            self.focus = 0
        elif key == pygame.K_END:
            self.focus = len(self.keys) - 1
        elif key in movement:
            self.focus = max(0, min(len(self.keys) - 1, self.focus + movement[key]))
        return None

    def draw(self, ui: Ui) -> None:
        ui.shade()
        width, height = ui.screen.get_size()
        columns = self.columns(width)
        rows = (len(self.keys) + columns - 1) // columns
        gap, inset = 8, 16
        card_h = min(124, (height - 112 - (rows - 1) * gap) // rows)
        panel = pygame.Rect(0, 0, min(1040, width - 24), 88 + rows * (card_h + gap) - gap)
        panel.center = (width // 2, height // 2)
        card_w = (panel.w - 2 * inset - (columns - 1) * gap) // columns
        ui.panel(panel, "bg", edge="top")
        ui.text("Select map", (panel.x + inset, panel.y + 14), "l", bold=True, upper=True, kind="title")
        ui.button(pygame.Rect(panel.right - inset - 84, panel.y + 12, 84, 32), "Back", "map_back", size="xs")
        mouse = pygame.mouse.get_pos()
        for i, key in enumerate(self.keys):
            rect = pygame.Rect(panel.x + inset + (i % columns) * (card_w + gap),
                               panel.y + 54 + (i // columns) * (card_h + gap), card_w, card_h)
            active = key == self.current
            hovered = rect.collidepoint(mouse)
            ui.skin("menu/tab_active" if active else "menu/button_hover" if hovered else "menu/tab", rect)
            if i == self.focus:
                ui.outline(rect, "text", 2)
            label = self.names[key]
            label_width = ui.size(label, "xs", upper=True, bold=True)[0]
            art = pygame.Rect(rect.x + 8, rect.y + 6, max(1, rect.w - label_width - 30), max(1, rect.h - 12))
            preview = self.thumbnail(key, art.size, ui.bank)
            if preview is not None:
                ui.screen.blit(preview, preview.get_rect(center=art.center))
            ui.text(label, (rect.right - 10, rect.centery - 7), "xs", "text", "right", upper=True, bold=True)
            ui.area(rect, f"map_pick:{key}")
        ui.text("Arrow keys to move   Enter to select   Esc to go back",
                (panel.centerx, panel.bottom - 24), "xs", "muted", "center")
