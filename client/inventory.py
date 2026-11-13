"""Weapon collection in the main menu."""
from __future__ import annotations

import pygame

from client.ui import Ui, color
from gameplay.data import load_weapons
from gameplay.skins import SKIN_LINES, skin_options

WEAPONS_PER_PAGE = 21
FOCUS_DIRECTIONS = {pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0),
                    pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}


class Inventory:
    def __init__(self, ui: Ui) -> None:
        self.ui = ui
        self.weapons = load_weapons()
        self.weapon = "vandal" if "vandal" in self.weapons else next(iter(self.weapons))
        self.preview = ""
        self.focus: str | None = None
        self.page = list(self.weapons).index(self.weapon) // WEAPONS_PER_PAGE

    def open(self, equipped: dict[str, str]) -> None:
        self.preview = equipped.get(self.weapon, "")

    def turn_page(self, steps: int) -> None:
        last_page = (len(self.weapons) - 1) // WEAPONS_PER_PAGE
        self.page = max(0, min(last_page, self.page + steps))
        self.focus = None

    def keyboard_action(self, key: int, reverse: bool, equipped: dict[str, str]) -> str | None:
        weapons = list(self.weapons)
        if key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
            self.turn_page(-1 if key == pygame.K_PAGEUP else 1)
            self.focus = f"inventory:weapon:{weapons[self.page * WEAPONS_PER_PAGE]}"
            return None
        first = self.page * WEAPONS_PER_PAGE
        actions = [f"inventory:weapon:{weapon}" for weapon in weapons[first:first + WEAPONS_PER_PAGE]]
        actions.extend(f"inventory:skin:{skin}" for skin in ("", *skin_options(self.weapon)))
        if self.preview != equipped.get(self.weapon, ""):
            actions.append("inventory:equip")
        if key in FOCUS_DIRECTIONS:
            self.move_focus(FOCUS_DIRECTIONS[key], actions)
            return None
        if key == pygame.K_TAB:
            if self.focus in actions:
                step = -1 if reverse else 1
                self.focus = actions[(actions.index(self.focus) + step) % len(actions)]
            else:
                current = f"inventory:weapon:{self.weapon}"
                self.focus = actions[-1] if reverse else current if current in actions else actions[0]
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and self.focus in actions:
            return self.focus
        return None

    def move_focus(self, direction: tuple[int, int], actions: list[str]) -> None:
        cards = {hit.action: hit.rect for hit in self.ui.hits if hit.enabled and hit.action in actions}
        if not cards:
            return
        if self.focus not in cards:
            selected = f"inventory:weapon:{self.weapon}"
            self.focus = selected if selected in cards else next(iter(cards))
        origin = cards[self.focus]
        dx, dy = direction
        candidates = []
        for action, rect in cards.items():
            x, y = rect.centerx - origin.centerx, rect.centery - origin.centery
            forward = x * dx + y * dy
            if forward <= 0:
                continue
            lateral = abs(x * dy - y * dx)
            aligned = (rect.top < origin.bottom and origin.top < rect.bottom) if dx else (
                rect.left < origin.right and origin.left < rect.right)
            candidates.append((not aligned, forward + 2 * lateral, lateral, action))
        if candidates:
            self.focus = min(candidates)[-1]

    def activate(self, action: str, equipped: dict[str, str]) -> bool:
        """Update the selection. Return True when the saved loadout changed."""
        if action.startswith("inventory:weapon:"):
            self.weapon = action.removeprefix("inventory:weapon:")
            self.open(equipped)
        elif action.startswith("inventory:skin:"):
            self.preview = action.removeprefix("inventory:skin:")
        elif action.startswith("inventory:page:"):
            self.turn_page(int(action.removeprefix("inventory:page:")))
        elif action == "inventory:equip" and self.preview != equipped.get(self.weapon, ""):
            if self.preview:
                equipped[self.weapon] = self.preview
            else:
                equipped.pop(self.weapon, None)
            return True
        return False

    def draw(self, w: int, h: int, equipped: dict[str, str]) -> None:
        ui = self.ui
        compact = w < 1000 or h < 580
        left, top, gap = (18, 112, 6) if compact else (36, 146, 10)
        cell_w, cell_h = (w // 2 - 2 * gap) // 3, (h - top - 72) // 7
        right = left + 3 * (cell_w + gap) + 14
        right_w = w - right - left
        ui.text("Collection", (left, 72 if compact else 82), "l" if compact else "xl", bold=True, upper=True, kind="title")
        if not compact:
            ui.text("Weapons", (left, top - 25), "xs", "muted", bold=True, upper=True)
        first = self.page * WEAPONS_PER_PAGE
        for i, key in enumerate(list(self.weapons)[first:first + WEAPONS_PER_PAGE]):
            col, row = i // 7, i % 7
            rect = pygame.Rect(left + col * (cell_w + gap), top + row * cell_h, cell_w, cell_h - 6)
            weapon = self.weapons[key]
            skin = equipped.get(key, "")
            self.card(rect, f"inventory:weapon:{key}", key == self.weapon)
            self.picture(weapon.art, skin, (rect.w - 24, 15 if compact else 31),
                         (rect.centerx, rect.y + (8 if compact else 20)))
            ui.text(weapon.name, (rect.x + 8, rect.bottom - (16 if compact else 25)), "xs" if compact else "s", bold=True)
            if not compact and (line := SKIN_LINES.get(skin)):
                ui.text(line.name, (rect.right - 10, rect.bottom - 23), "xs", "muted", "right")
        if len(self.weapons) > WEAPONS_PER_PAGE:
            y = top + 7 * cell_h + 8
            ui.button(pygame.Rect(left, y, 90, 32), "Previous", "inventory:page:-1", enabled=first > 0, size="xs")
            ui.button(pygame.Rect(left + 100, y, 90, 32), "Next", "inventory:page:1",
                      enabled=first + WEAPONS_PER_PAGE < len(self.weapons), size="xs")

        weapon = self.weapons[self.weapon]
        current = equipped.get(self.weapon, "")
        preview_line = SKIN_LINES.get(self.preview)
        preview = pygame.Rect(right, top, right_w, 142 if compact else 234)
        ui.panel(preview, edge="top", edge_col=preview_line.palette[-1] if preview_line else "line")
        ui.text(weapon.name, (preview.x + 20, preview.y + 12), "l", bold=True, upper=True, kind="title")
        ui.text(preview_line.name if preview_line else "Standard", (preview.x + 21, preview.y + (44 if compact else 55)), "s", "muted")
        self.picture(weapon.art, self.preview, (right_w - 48, 42 if compact else 108),
                     (preview.centerx, preview.y + (80 if compact else 131)))
        active = self.preview == current
        equip = pygame.Rect(preview.right - 146, preview.bottom - 44, 126, 34)
        ui.button(equip,
                  "Equipped" if active else "Equip", "inventory:equip", primary=not active, enabled=not active, size="s")

        if self.focus == "inventory:equip" and not active:
            ui.outline(equip.inflate(4, 4), "text", 2)

        y = preview.bottom + (7 if compact else 14)
        ui.text("Skins", (right, y), "xs", "muted", bold=True, upper=True)
        card_w = (right_w - gap) // 2
        for i, skin in enumerate(("", *skin_options(self.weapon))):
            rect = pygame.Rect(right + (i % 2) * (card_w + gap),
                               y + (18 if compact else 24) + (i // 2) * (48 if compact else 73),
                               card_w, 43 if compact else 65)
            self.card(rect, f"inventory:skin:{skin}", skin == self.preview)
            line = SKIN_LINES.get(skin)
            ui.text(line.name if line else "Standard", (rect.x + 8, rect.y + 5 if compact else rect.y + 11),
                    "xs" if compact else "s", bold=True)
            if skin == current:
                ui.text("Equipped", (rect.x + 8, rect.y + (22 if compact else 34)), "xs", "ally")
            self.picture(weapon.art, skin, (58, 16) if compact else (96, 40),
                         (rect.right - (34 if compact else 60), rect.y + 29 if compact else rect.centery))

        ui.text("Arrows / Tab to focus   Enter to select   PgUp / PgDn for pages",
                (w - left, 87 if compact else 114), "xs", "muted", "right")

    def card(self, rect: pygame.Rect, action: str, selected: bool) -> None:
        ui = self.ui
        hover = rect.collidepoint(pygame.mouse.get_pos())
        ui.skin("buy/card_hover" if hover or selected else "buy/card", rect)
        if selected:
            pygame.draw.rect(ui.screen, color("accent"), (rect.x, rect.y, 3, rect.h))
        if self.focus == action:
            ui.outline(rect, "text", 2)
        ui.area(rect, action)

    def picture(self, art: str, skin: str, bounds: tuple[int, int], center: tuple[int, int]) -> None:
        picture = self.ui.bank.weapon(art, bounds, skin, view="preview")
        if picture is not None:
            self.ui.screen.blit(picture, picture.get_rect(center=center))
