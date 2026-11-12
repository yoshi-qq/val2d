"""In-game overlays: pause menu (Esc), quick settings, leave and quit confirmations (Alt+F4 asks, a second Alt+F4 quits).

The match keeps running behind the pause menu, like in an online game; the own player just stands still.
"""
from __future__ import annotations

import pygame

import user_settings
from client.ui import Ui, color

class _NoKeys:
    """Stands in for pygame.key.get_pressed() while a menu is open: nothing is held."""

    def __getitem__(self, key: int) -> bool:
        return False


NO_KEYS = _NoKeys()
PAUSE_SLIDERS = (("sensitivity", "Mouse sensitivity", "sens"), ("volume", "Volume", None))


class OverlaysMixin:
    overlay: str
    kit: Ui
    quit_program: bool

    def open_overlay(self, name: str) -> None:
        self.overlay = name
        self.aiming = None
        self.ui.buy_open = False
        self.grab(False)

    def close_overlay(self) -> None:
        self.overlay = ""
        self.kit.pressed = None
        self._drag = None

    def overlay_event(self, ev: pygame.event.Event) -> str | None:
        """Handles an input event while an overlay is open. Returns "leave" or "quit" to end the match loop."""
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            if self.overlay in ("leave", "quit"):
                self.overlay = "pause" if getattr(self, "_from_pause", False) else ""
            else:
                self.close_overlay()
            return None
        if ev.type == pygame.MOUSEMOTION and getattr(self, "_drag", None):
            self._slide(ev.pos)
            return None
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            hit = self.kit.hit_at(ev.pos)
            if hit is None:
                return None
            if hit.action.startswith("slider:"):
                self._drag = hit.action[7:]
                self._slide(ev.pos)
            else:
                self.kit.pressed = hit.action
            return None
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self._drag = None
            hit = self.kit.hit_at(ev.pos)
            action, self.kit.pressed = self.kit.pressed, None
            if hit is None or hit.action != action:
                return None
            if action == "resume":
                self.close_overlay()
            elif action in ("leave", "quit"):
                self._from_pause = self.overlay == "pause"
                self.overlay = action
            elif action == "cancel":
                self.overlay = "pause" if getattr(self, "_from_pause", False) else ""
            elif action == "leave_yes":
                return "leave"
            elif action == "quit_yes":
                self.quit_program = True
                return "quit"
        return None

    def _slide(self, pos: tuple[int, int]) -> None:
        hit = next((h for h in self.kit.hits if h.action == f"slider:{self._drag}"), None)
        if hit is None:
            return
        low, high = user_settings.LIMITS[self._drag]
        frac = max(0.0, min(1.0, (pos[0] - hit.rect.x) / max(1, hit.rect.w)))
        value = round(low + frac * (high - low), 3)
        if self._drag == "sensitivity":
            self.sens = value
        elif self._drag == "volume":
            self.sound.volume = value
        saved = user_settings.load()
        saved[self._drag] = value
        user_settings.save(saved)

    def draw_overlay(self) -> None:
        if not self.overlay:
            return
        ui = self.kit
        ui.begin()
        w, h = self.screen.get_size()
        if self.overlay in ("pause", "leave", "quit"):
            # like the real escape menu: dimmed game, a centred column of large text buttons
            ui.fill(self.screen.get_rect(), "#0f1923d0")
            ui.modal_from = len(ui.hits)
            cx = w // 2
            y = h // 2 - 170
            for label, action in (("Resume", "resume"), ("Leave match", "leave"), ("Quit game", "quit")):
                r = pygame.Rect(cx - 170, y, 340, 54)
                hover = r.collidepoint(pygame.mouse.get_pos())
                if hover:
                    ui.fill(r, "#ece8e126")
                    pygame.draw.rect(self.screen, color("accent"), (r.x, r.y, 4, r.h))
                ui.text(label, (cx, r.y + 12), "l", "text" if hover else "muted", "center", upper=True, bold=True, kind="title")
                ui.area(r, action)
                y += 62
            y += 30
            ui.line((cx - 170, y), (cx + 170, y))
            y += 20
            for key, label, _ in PAUSE_SLIDERS:
                value = self.sens if key == "sensitivity" else self.sound.volume
                low, high = user_settings.LIMITS[key]
                ui.text(label, (cx - 170, y), "xs", "muted", upper=True)
                ui.slider(pygame.Rect(cx - 170, y + 22, 280, 18), (value - low) / (high - low), f"slider:{key}")
                ui.text(f"{value:.2f}", (cx + 170, y + 20), "s", "text", "right")
                y += 60
            ui.text("Esc resumes · the match keeps running", (cx, h - 44), "xs", "muted", "center", upper=True)
        if self.overlay == "leave":
            ui.dialog("Leave match?", "You go back to the main menu." + (" The match ends for everyone." if self.session else ""),
                      [("Cancel", "cancel", False), ("Leave", "leave_yes", True)])
        elif self.overlay == "quit":
            ui.dialog("Quit Val2d?", "Alt+F4 again quits at once.", [("Cancel", "cancel", False), ("Quit", "quit_yes", True)])
