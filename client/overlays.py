"""In-game overlays: pause menu (Esc), quick settings, leave and quit confirmations (Alt+F4 asks, a second Alt+F4 quits).

The match keeps running behind the pause menu, like in an online game; the own player just stands still.
"""
from __future__ import annotations

import pygame

import user_settings
from client.ui import Ui

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
            ui.shade()
            panel = pygame.Rect(0, 0, 420, h)
            ui.panel(panel, "bg")
            ui.line((panel.right, 0), (panel.right, h))
            ui.text("Paused", (48, 70), "xl", "text", upper=True, bold=True, kind="title")
            ui.text("The match keeps running.", (50, 128), "s", "muted")
            y = 180
            for label, action, primary in (("Resume", "resume", True), ("Leave match", "leave", False), ("Quit game", "quit", False)):
                ui.button(pygame.Rect(48, y, 320, 48), label, action, primary=primary)
                y += 60
            y += 20
            ui.text("Quick settings", (48, y), "s", "muted", upper=True)
            y += 34
            for key, label, _ in PAUSE_SLIDERS:
                value = self.sens if key == "sensitivity" else self.sound.volume
                low, high = user_settings.LIMITS[key]
                ui.text(label, (48, y), "xs", "muted", upper=True)
                ui.slider(pygame.Rect(48, y + 24, 260, 18), (value - low) / (high - low), f"slider:{key}")
                ui.text(f"{value:.2f}", (324, y + 22), "s")
                y += 64
            ui.text("Esc resumes", (48, h - 48), "xs", "muted", upper=True)
        if self.overlay == "leave":
            ui.dialog("Leave match?", "You go back to the main menu." + (" The match ends for everyone." if self.session else ""),
                      [("Cancel", "cancel", False), ("Leave", "leave_yes", True)])
        elif self.overlay == "quit":
            ui.dialog("Quit Val2d?", "Alt+F4 again quits at once.", [("Cancel", "cancel", False), ("Quit", "quit_yes", True)])
