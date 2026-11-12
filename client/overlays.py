"""In-game overlays: escape menu (Resume, Settings, Leave match, Quit game) with the full settings window, leave and
quit confirmations (Alt+F4 asks, a second Alt+F4 quits).

The match keeps running behind the menu, like in an online game; the own player just stands still.
"""
from __future__ import annotations

import pygame

import user_settings
from client.settings_panel import SettingsPanel
from client.ui import Ui, color


class _NoKeys:
    """Stands in for pygame.key.get_pressed() while a menu is open: nothing is held."""

    def __getitem__(self, key: int) -> bool:
        return False


NO_KEYS = _NoKeys()
ESCAPE_MENU = (("Resume", "resume"), ("Settings", "settings"), ("Leave match", "leave"), ("Quit game", "quit"))


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

    def apply_player_settings(self) -> None:
        """Takes the saved settings into the running match: sensitivity, camera, volume, keys, crosshair."""
        from client.common import key_codes
        st = user_settings.load()
        self.sens, self.camera_push, self.sound.volume = float(st["sensitivity"]), float(st["camera_push"]), float(st["volume"])
        self.keys = key_codes(dict(st["keys"]))
        self.ability_keys = {self.keys["ability_c"]: "C", self.keys["ability_q"]: "Q", self.keys["ability_e"]: "E",
                             self.keys["ability_x"]: "X"}
        self.crosshair = {k: st[k] for k in ("crosshair_color", "crosshair_size", "crosshair_gap", "crosshair_dot")}

    def reload_content(self) -> None:
        """Reads agents, abilities, weapons, armor, statuses and patches again (matches against bots and the range);
        map and rule changes apply from the next match."""
        from gameplay.data import load_armor, load_weapons
        from gameplay.kit.library import load_library
        from gameplay.kit.statuses import load_statuses
        from gameplay.match import load_agents
        from gameplay.patches import reload_all
        reload_all()
        load_library.cache_clear()
        m = self.match
        m.agents, m.weapons, m.armor, m.statuses = load_agents(), load_weapons(), load_armor(), load_statuses()
        self.status = f"Content reloaded: {len(m.agents)} agents, {len(m.weapons)} weapons (maps and rules: next match)"
        self.sound.play("ui_click", gain=0.6)

    def overlay_event(self, ev: pygame.event.Event) -> str | None:
        """Handles an input event while an overlay is open. Returns "leave" or "quit" to end the match loop."""
        if self.overlay == "settings":
            if self.settings_panel.handle(ev) == "closed":
                self.apply_player_settings()
                self.overlay = "pause"
            return None
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            if self.overlay in ("leave", "quit", "surrender"):
                self.overlay = "pause" if getattr(self, "_from_pause", False) else ""
            else:
                self.close_overlay()
            return None
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            hit = self.kit.hit_at(ev.pos)
            if hit is not None:
                self.kit.pressed = hit.action
            return None
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            hit = self.kit.hit_at(ev.pos)
            action, self.kit.pressed = self.kit.pressed, None
            if hit is None or hit.action != action:
                return None
            if action == "resume":
                self.close_overlay()
            elif action == "settings":
                self.settings_panel = SettingsPanel(self.kit)
                self.overlay = "settings"
            elif action == "reload":
                self.reload_content()
            elif action == "surrender":
                self._from_pause = True
                self.overlay = "surrender"
            elif action == "surrender_yes":
                me = self.match.players.get(self.me)
                if me is not None:
                    self.match.surrender(me.team)
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

    def draw_overlay(self) -> None:
        if not self.overlay:
            return
        ui = self.kit
        ui.begin()
        w, h = self.screen.get_size()
        if self.overlay == "settings":
            self.settings_panel.draw()
            return
        if self.overlay in ("pause", "leave", "quit", "surrender"):
            # like the real escape menu: dimmed game, a centred column of large text buttons
            ui.fill(self.screen.get_rect(), "#0f1923d0")
            ui.modal_from = len(ui.hits)
            cx = w // 2
            y = h // 2 - 2 * 62
            entries = list(ESCAPE_MENU)
            if self.mode == "local":  # own match: content files can be reloaded while playing
                entries.insert(2, ("Reload content", "reload"))
            if self.mode in ("local", "host") and self.match.phase in ("buy", "live", "planted", "end") and not self.match.practice:
                entries.insert(-1, ("Surrender", "surrender"))
            for label, action in entries:
                r = pygame.Rect(cx - 170, y, 340, 54)
                hover = r.collidepoint(pygame.mouse.get_pos())
                if hover:
                    ui.fill(r, "#ece8e126")
                    pygame.draw.rect(self.screen, color("accent"), (r.x, r.y, 4, r.h))
                ui.text(label, (cx, r.y + 12), "l", "text" if hover else "muted", "center", upper=True, bold=True, kind="title")
                ui.area(r, action)
                y += 62
            ui.text("Esc resumes · the match keeps running", (cx, h - 44), "xs", "muted", "center", upper=True)
        if self.overlay == "leave":
            ui.dialog("Leave match?", "You go back to the main menu." + (" The match ends for everyone." if self.session else ""),
                      [("Cancel", "cancel", False), ("Leave", "leave_yes", True)])
        elif self.overlay == "surrender":
            ui.dialog("Surrender?", "Your team loses the match now.", [("Cancel", "cancel", False), ("Surrender", "surrender_yes", True)])
        elif self.overlay == "quit":
            ui.dialog("Quit Val2d?", "Alt+F4 again quits at once.", [("Cancel", "cancel", False), ("Quit", "quit_yes", True)])
