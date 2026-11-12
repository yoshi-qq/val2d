"""The settings window, shared by the main menu and the in-game escape menu: tabs General, Controls, Crosshair, Audio;
sliders, switches, name, key bindings, crosshair colour with preview. Saved to ~/.val2d/settings.json on close."""
from __future__ import annotations

from typing import Any

import pygame

import user_settings
from client.ui import Ui

SETTINGS_TABS = (("general", "General"), ("controls", "Controls"), ("crosshair", "Crosshair"), ("audio", "Audio"))
SLIDERS = {"general": (("sensitivity", "Mouse sensitivity"), ("camera_push", "Camera ahead")),
           "crosshair": (("crosshair_size", "Size"), ("crosshair_gap", "Gap")),
           "audio": (("volume", "Overall volume"),)}
CHECKS = {"general": (("fullscreen", "Fullscreen (from the next start of a match)"),),
          "crosshair": (("crosshair_dot", "Centre dot"),)}


class SettingsPanel:
    def __init__(self, ui: Ui) -> None:
        self.ui = ui
        self.settings: dict[str, Any] = user_settings.load()
        self.tab = "general"
        self.binding: str | None = None
        self.typing_name = False
        self.dragging: str | None = None

    # ------------------------------------------------------------ input
    def handle(self, ev: pygame.event.Event) -> str | None:
        """One input event while the window is open. Returns "closed" when it was closed (and saved)."""
        if ev.type == pygame.KEYDOWN and self.binding is not None:
            if ev.key != pygame.K_ESCAPE:
                name = pygame.key.name(ev.key)
                keys = self.settings["keys"]
                for other, bound in list(keys.items()):
                    if bound == name and other != self.binding:
                        keys[other] = keys[self.binding]  # swap instead of double binding
                keys[self.binding] = name
            self.binding = None
            return None
        if ev.type == pygame.KEYDOWN and self.typing_name:
            if ev.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_KP_ENTER):
                self.typing_name = False
            elif ev.key == pygame.K_BACKSPACE:
                self.settings["name"] = self.settings["name"][:-1]
            elif ev.unicode and ev.unicode.isprintable() and len(self.settings["name"]) < 16:
                self.settings["name"] += ev.unicode
            return None
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            return self.close()
        if ev.type == pygame.MOUSEMOTION and self.dragging:
            self._slide(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            hit = self.ui.hit_at(ev.pos)
            self.typing_name = False
            if hit is None:
                return None
            if hit.action.startswith("slider:"):
                self.dragging = hit.action[7:]
                self._slide(ev.pos)
            elif hit.action == "field:name":
                self.typing_name = True
            else:
                self.ui.pressed = hit.action
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self.dragging = None
            hit = self.ui.hit_at(ev.pos)
            action, self.ui.pressed = self.ui.pressed, None
            if hit is not None and action == hit.action:
                return self.activate(action)
        return None

    def activate(self, action: str) -> str | None:
        st = self.settings
        if action == "settings_close":
            return self.close()
        if action.startswith("stab:"):
            self.tab, self.binding = action[5:], None
        elif action.startswith("check:"):
            st[action[6:]] = not st[action[6:]]
        elif action == "color":
            colors = user_settings.CROSSHAIR_COLORS
            current = st["crosshair_color"]
            st["crosshair_color"] = colors[(colors.index(current) + 1) % len(colors)] if current in colors else colors[0]
        elif action.startswith("bind:"):
            self.binding = action[5:]
        elif action == "defaults":
            name = st["name"]
            self.settings = user_settings.defaults()
            self.settings["name"] = name
        return None

    def close(self) -> str:
        if not self.settings["name"].strip():
            self.settings["name"] = "Player"
        user_settings.save(self.settings)
        self.binding, self.typing_name, self.dragging = None, False, None
        return "closed"

    def _slide(self, pos: tuple[int, int]) -> None:
        hit = next((h for h in self.ui.hits if h.action == f"slider:{self.dragging}"), None)
        if hit is None or not self.dragging:
            return
        low, high = user_settings.LIMITS[self.dragging]
        frac = max(0.0, min(1.0, (pos[0] - hit.rect.x) / max(1, hit.rect.w)))
        self.settings[self.dragging] = round(low + frac * (high - low), 3)

    # ------------------------------------------------------------ drawing
    def draw(self) -> None:
        ui, st = self.ui, self.settings
        screen = ui.screen
        w, h = screen.get_size()
        ui.shade()
        box = pygame.Rect(120, 60, w - 240, h - 120)
        ui.panel(box, "bg", edge="top")
        ui.outline(box, "line")
        ui.text("Settings", (box.x + 32, box.y + 22), "l", "text", upper=True, bold=True, kind="title")
        x = box.x + 250
        for key, label in SETTINGS_TABS:
            tw = ui.size(label, "m", upper=True, bold=True)[0] + 36
            ui.tab(pygame.Rect(x, box.y + 12, tw, 50), label, f"stab:{key}", self.tab == key)
            x += tw
        ui.button(pygame.Rect(box.right - 130, box.y + 18, 100, 36), "Close", "settings_close", size="s")
        ui.line((box.x, box.y + 70), (box.right, box.y + 70))
        y = box.y + 96
        if self.tab == "general":
            ui.text("Name", (box.x + 40, y + 10), "s", "muted", upper=True)
            field = pygame.Rect(box.x + 330, y, 360, 40)
            ui.fill(field, "panel_light")
            ui.outline(field, "accent" if self.typing_name else "line")
            ui.text(st["name"] + ("_" if self.typing_name else ""), (field.x + 12, field.y + 12), "m")
            ui.area(field, "field:name")
            y += 64
        for key, label in SLIDERS.get(self.tab, ()):
            low, high = user_settings.LIMITS[key]
            ui.text(label, (box.x + 40, y + 2), "s", "muted", upper=True)
            ui.slider(pygame.Rect(box.x + 330, y, 360, 20), (st[key] - low) / (high - low), f"slider:{key}")
            ui.text(f"{st[key]:.2f}", (box.x + 720, y), "s")
            y += 52
        for key, label in CHECKS.get(self.tab, ()):
            ui.checkbox(pygame.Rect(box.x + 40, y, 26, 26), bool(st[key]), f"check:{key}")
            ui.text(label, (box.x + 80, y + 5), "s")
            y += 44
        if self.tab == "crosshair":
            r = pygame.Rect(box.x + 330, y, 40, 40)
            pygame.draw.rect(screen, pygame.Color(st["crosshair_color"]), r)
            ui.outline(r, "text")
            ui.area(r, "color")
            ui.text("Colour (click)", (box.x + 40, y + 12), "s", "muted", upper=True)
            prev = pygame.Rect(box.right - 260, box.y + 110, 200, 200)
            ui.fill(prev, "panel_light")
            self._crosshair_preview(prev.center)
        if self.tab == "controls":
            mouse = pygame.mouse.get_pos()
            for i, (action, key) in enumerate(st["keys"].items()):
                col, row = divmod(i, 10)
                r = pygame.Rect(box.x + 40 + col * 500, y + row * 40, 470, 34)
                active = self.binding == action
                ui.fill(r, "panel_light" if r.collidepoint(mouse) or active else "panel")
                ui.text(action.replace("_", " "), (r.x + 14, r.y + 9), "s", "muted", upper=True)
                ui.text("press a key …" if active else key, (r.right - 14, r.y + 9), "s", "accent" if active else "text", "right",
                        upper=not active, bold=True)
                ui.area(r, f"bind:{action}")
            ui.text("Click an action, then press the new key (Esc keeps the old one).", (box.x + 40, box.bottom - 40), "xs", "muted",
                    upper=True)
        if self.tab != "controls":
            ui.button(pygame.Rect(box.x + 32, box.bottom - 50, 180, 34), "Defaults", "defaults", size="xs")

    def _crosshair_preview(self, at: tuple[int, int]) -> None:
        """Same drawing as in the game (client/crosshair.py), shown twice as large to judge the pixels."""
        from client import crosshair
        st = self.settings
        small = pygame.Surface((100, 100), pygame.SRCALPHA)
        crosshair.draw(small, (50, 50), pygame.Color(st["crosshair_color"]), st["crosshair_size"], st["crosshair_gap"],
                       bool(st["crosshair_dot"]))
        self.ui.screen.blit(pygame.transform.scale(small, (200, 200)), (at[0] - 100, at[1] - 100))
