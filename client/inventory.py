"""Weapon collection in the main menu."""
from __future__ import annotations

import pygame

from client.ui import Ui, color
from gameplay.data import load_weapons
from gameplay.skins import SKIN_LINES, skin_options

WEAPONS_PER_PAGE = 21


class Inventory:
    def __init__(self, ui: Ui) -> None:
        self.ui = ui
        self.weapons = load_weapons()
        self.weapon = "vandal" if "vandal" in self.weapons else next(iter(self.weapons))
        self.preview = ""
        self.page = list(self.weapons).index(self.weapon) // WEAPONS_PER_PAGE

    def open(self, equipped: dict[str, str]) -> None:
        self.preview = equipped.get(self.weapon, "")

    def activate(self, action: str, equipped: dict[str, str]) -> bool:
        """Update the selection. Return True when the saved loadout changed."""
        if action.startswith("inventory:weapon:"):
            self.weapon = action.removeprefix("inventory:weapon:")
            self.open(equipped)
        elif action.startswith("inventory:skin:"):
            self.preview = action.removeprefix("inventory:skin:")
        elif action.startswith("inventory:page:"):
            self.page += int(action.removeprefix("inventory:page:"))
        elif action == "inventory:equip" and self.preview != equipped.get(self.weapon, ""):
            if self.preview:
                equipped[self.weapon] = self.preview
            else:
                equipped.pop(self.weapon, None)
            return True
        return False

    def draw(self, w: int, h: int, equipped: dict[str, str]) -> None:
        ui = self.ui
        left, top, gap = 36, 146, 10
        cell_w, cell_h = (w // 2 - 2 * gap) // 3, (h - top - 72) // 7
        right = left + 3 * (cell_w + gap) + 14
        right_w = w - right - left
        ui.text("Inventory", (left, 82), "xl", bold=True, upper=True, kind="title")
        ui.text("Weapons", (left, top - 25), "xs", "muted", bold=True, upper=True)
        first = self.page * WEAPONS_PER_PAGE
        for i, key in enumerate(list(self.weapons)[first:first + WEAPONS_PER_PAGE]):
            col, row = i // 7, i % 7
            rect = pygame.Rect(left + col * (cell_w + gap), top + row * cell_h, cell_w, cell_h - 6)
            weapon = self.weapons[key]
            skin = equipped.get(key, "")
            self.card(rect, f"inventory:weapon:{key}", key == self.weapon)
            ui.text(weapon.name, (rect.x + 12, rect.y + 9), "s", bold=True)
            ui.text(SKIN_LINES[skin].name if skin else "Standard", (rect.x + 12, rect.y + 30), "xs", "muted")
            self.picture(weapon.art, skin, (74, 30), (rect.right - 49, rect.centery))
        if len(self.weapons) > WEAPONS_PER_PAGE:
            y = top + 7 * cell_h + 8
            ui.button(pygame.Rect(left, y, 90, 32), "Previous", "inventory:page:-1", enabled=first > 0, size="xs")
            ui.button(pygame.Rect(left + 100, y, 90, 32), "Next", "inventory:page:1",
                      enabled=first + WEAPONS_PER_PAGE < len(self.weapons), size="xs")

        weapon = self.weapons[self.weapon]
        current = equipped.get(self.weapon, "")
        preview_line = SKIN_LINES.get(self.preview)
        preview = pygame.Rect(right, top, right_w, 234)
        ui.panel(preview, edge="top", edge_col=preview_line.palette[-1] if preview_line else "line")
        ui.text(weapon.name, (preview.x + 20, preview.y + 17), "l", bold=True, upper=True, kind="title")
        ui.text(preview_line.name if preview_line else "Standard", (preview.x + 21, preview.y + 55), "s", "muted")
        self.picture(weapon.art, self.preview, (right_w - 64, 108), (preview.centerx, preview.y + 131))
        active = self.preview == current
        ui.button(pygame.Rect(preview.right - 146, preview.bottom - 49, 126, 34),
                  "Equipped" if active else "Equip", "inventory:equip", primary=not active, enabled=not active, size="s")

        y = preview.bottom + 14
        ui.text("Skins", (right, y), "xs", "muted", bold=True, upper=True)
        card_w = (right_w - gap) // 2
        for i, skin in enumerate(("", *skin_options(self.weapon))):
            rect = pygame.Rect(right + (i % 2) * (card_w + gap), y + 24 + (i // 2) * 73, card_w, 65)
            self.card(rect, f"inventory:skin:{skin}", skin == self.preview)
            line = SKIN_LINES.get(skin)
            ui.text(line.name if line else "Standard", (rect.x + 12, rect.y + 11), "s", bold=True)
            if skin == current:
                ui.text("Equipped", (rect.x + 12, rect.y + 34), "xs", "ally")
            self.picture(weapon.art, skin, (96, 40), (rect.right - 60, rect.centery))

    def card(self, rect: pygame.Rect, action: str, selected: bool) -> None:
        ui = self.ui
        hover = rect.collidepoint(pygame.mouse.get_pos())
        ui.skin("buy/card_hover" if hover or selected else "buy/card", rect)
        if selected:
            pygame.draw.rect(ui.screen, color("accent"), (rect.x, rect.y, 3, rect.h))
        ui.area(rect, action)

    def picture(self, art: str, skin: str, bounds: tuple[int, int], center: tuple[int, int]) -> None:
        picture = self.ui.bank.weapon(art, bounds, skin, view="preview")
        if picture is not None:
            self.ui.screen.blit(picture, picture.get_rect(center=center))
