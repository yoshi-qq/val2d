"""Main menu of Val2d: practice against bots, host, find or join a network match, settings.

Returns the chosen settings as an argparse.Namespace for play.Game, or None to quit.
Graphics: assets/ui/menu (buttons and panel as 9-slice, title background), placeholders if missing.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pygame

from gameplay.netgame import DEFAULT_PORT, discover
from gameplay.world import MAP_DIR
import user_settings
from sprite_bank import SpriteBank, draw_nine_slice

C_BG = (22, 21, 28)
C_TEXT = (232, 230, 239)
C_MUTED = (155, 152, 170)
C_ACCENT = (224, 180, 55)
C_ERROR = (238, 76, 74)
SCALE = 3  # pixel-art scale of the menu kit
MODE_NAMES = {"standard": "Standard", "quick": "Quick (first to 4)", "deathmatch": "Team deathmatch"}


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    action: str
    enabled: bool = True


def map_keys() -> list[str]:
    return sorted(p.stem for p in Path(MAP_DIR).glob("*.json")) or ["werkhof"]


class MainMenu:
    def __init__(self, screen: pygame.Surface, font: pygame.font.Font, big: pygame.font.Font, defaults: argparse.Namespace) -> None:
        self.screen = screen
        self.font, self.big = font, big
        self.bank = SpriteBank()
        self.args = defaults
        self.maps = map_keys()
        if self.args.map not in self.maps:
            self.args.map = self.maps[0]
        self.address = ""
        self.typing = False
        self.status = ""
        self.found: list[tuple[str, int, str]] = []
        self.pressed: str | None = None
        self.view = "main"
        self.settings = user_settings.load()
        self.dragging: str | None = None
        self.typing_name = False
        self.binding: str | None = None
        self.apply_settings()

    def apply_settings(self) -> None:
        a, st = self.args, self.settings
        a.sensitivity, a.camera_push, a.volume = st["sensitivity"], st["camera_push"], st["volume"]
        a.name = st["name"]
        a.all_around, a.sound_rings = st["all_around"] or a.all_around, st["sound_rings"] or a.sound_rings
        a.fullscreen = bool(st.get("fullscreen", False))
        a.keys = dict(st["keys"])
        a.crosshair = {k: st[k] for k in ("crosshair_color", "crosshair_size", "crosshair_gap", "crosshair_dot")}

    # ------------------------------------------------------------ settings view
    SLIDERS = (("sensitivity", "Mouse sensitivity"), ("camera_push", "Camera ahead"), ("volume", "Volume"),
               ("crosshair_size", "Crosshair size"), ("crosshair_gap", "Crosshair gap"))
    CHECKS = (("all_around", "All-around sight (lobby rule)"), ("sound_rings", "Sound rings (lobby rule)"),
              ("fullscreen", "Fullscreen"), ("crosshair_dot", "Crosshair centre dot"))

    def slider_rect(self, i: int) -> pygame.Rect:
        return pygame.Rect(360, 210 + i * 46, 420, 22)

    def check_rect(self, i: int) -> pygame.Rect:
        return pygame.Rect(80, 445 + i * 40, 30, 30)

    def name_rect(self) -> pygame.Rect:
        return pygame.Rect(360, 150, 420, 44)

    def back_button(self) -> Button:
        return Button(pygame.Rect(80, 630, 300, 44), "Save and back", "back")

    def controls_button(self) -> Button:
        return Button(pygame.Rect(420, 630, 300, 44), "Controls", "controls")

    def color_rect(self) -> pygame.Rect:
        return pygame.Rect(860, 210 + 3 * 46, 36, 36)

    def key_rect(self, i: int) -> pygame.Rect:
        col, row = divmod(i, 10)
        return pygame.Rect(80 + col * 560, 150 + row * 44, 520, 38)

    def draw_crosshair_preview(self, at: tuple[int, int]) -> None:
        st = self.settings
        color = pygame.Color(st["crosshair_color"])
        size, gap = 7 * st["crosshair_size"], st["crosshair_gap"]
        x, y = at
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            pygame.draw.line(self.screen, color, (x + dx * gap, y + dy * gap), (x + dx * (gap + size), y + dy * (gap + size)), 2)
        if st["crosshair_dot"]:
            pygame.draw.circle(self.screen, color, (x, y), 2)

    def draw_controls(self) -> None:
        s = self.screen
        s.blit(self.big.render("Controls", True, C_TEXT), (80, 80))
        mouse = pygame.mouse.get_pos()
        for i, (action, key) in enumerate(self.settings["keys"].items()):
            r = self.key_rect(i)
            active = self.binding == action
            state = "button_pressed" if active else "button_hover" if r.collidepoint(mouse) else "button"
            if not draw_nine_slice(s, self.bank, f"ui/menu/{state}.png", r, 4, 2):
                pygame.draw.rect(s, C_MUTED, r, 1)
            s.blit(self.font.render(action.replace("_", " "), True, C_TEXT), (r.x + 14, r.y + 10))
            label = "press a key …" if active else key
            s.blit(self.font.render(label, True, C_ACCENT if active else C_TEXT), (r.x + 300, r.y + 10))
        s.blit(self.font.render("Click an action, then press the new key (Esc keeps the old one). Mouse buttons: fire, alternate fire.",
                                True, C_MUTED), (80, 600))
        b = self.back_button()
        if not draw_nine_slice(s, self.bank, f"ui/menu/{'button_hover' if b.rect.collidepoint(mouse) else 'button'}.png", b.rect, 4, SCALE):
            pygame.draw.rect(s, C_MUTED, b.rect, 1)
        s.blit(self.font.render("Back", True, C_TEXT), (b.rect.x + 18, b.rect.y + 13))

    def settings_click(self, pos: tuple[int, int]) -> None:
        if self.view == "controls":
            for i, action in enumerate(user_settings.DEFAULT_KEYS):
                if self.key_rect(i).collidepoint(pos):
                    self.binding = action
            if self.back_button().rect.collidepoint(pos):
                self.binding = None
            return
        if self.controls_button().rect.collidepoint(pos):
            self.view = "controls"
            return
        if self.color_rect().collidepoint(pos):
            colors = user_settings.CROSSHAIR_COLORS
            current = self.settings["crosshair_color"]
            self.settings["crosshair_color"] = colors[(colors.index(current) + 1) % len(colors)] if current in colors else colors[0]
        self.typing_name = self.name_rect().collidepoint(pos)
        for i, (key, _) in enumerate(self.SLIDERS):
            if self.slider_rect(i).inflate(0, 16).collidepoint(pos):
                self.dragging = key
                self.slide(pos)
        for i, (key, _) in enumerate(self.CHECKS):
            if self.check_rect(i).collidepoint(pos):
                self.settings[key] = not self.settings[key]

    def slide(self, pos: tuple[int, int]) -> None:
        if not self.dragging:
            return
        i = [k for k, _ in self.SLIDERS].index(self.dragging)
        r = self.slider_rect(i)
        low, high = user_settings.LIMITS[self.dragging]
        frac = max(0.0, min(1.0, (pos[0] - r.x) / r.w))
        self.settings[self.dragging] = round(low + frac * (high - low), 3)

    def draw_settings(self) -> None:
        s = self.screen
        st = self.settings
        s.blit(self.big.render("Settings", True, C_TEXT), (80, 80))
        s.blit(self.font.render("Name", True, C_MUTED), (80, 162))
        field = self.name_rect()
        if not draw_nine_slice(s, self.bank, "ui/menu/textfield.png", field, 4, SCALE):
            pygame.draw.rect(s, (36, 35, 45), field)
        s.blit(self.font.render(st["name"] + ("_" if self.typing_name else ""), True, C_TEXT), (field.x + 16, field.y + 13))
        for i, (key, label) in enumerate(self.SLIDERS):
            r = self.slider_rect(i)
            low, high = user_settings.LIMITS[key]
            frac = (st[key] - low) / (high - low)
            s.blit(self.font.render(label, True, C_MUTED), (80, r.y + 3))
            track = self.bank.scaled("ui/menu/slider_track.png", (r.w, r.h))
            fill = self.bank.scaled("ui/menu/slider_fill.png", (r.w, r.h))
            knob = self.bank.scaled("ui/menu/slider_knob.png", (r.h + 8, r.h + 8))
            if track is not None and fill is not None:
                s.blit(track, r.topleft)
                s.blit(fill, r.topleft, (0, 0, round(r.w * frac), r.h))
            else:
                pygame.draw.rect(s, C_MUTED, r, 1)
                pygame.draw.rect(s, C_ACCENT, (r.x, r.y, r.w * frac, r.h))
            kx = r.x + r.w * frac
            if knob is not None:
                s.blit(knob, (kx - knob.get_width() / 2, r.centery - knob.get_height() / 2))
            s.blit(self.font.render(f"{st[key]:.2f}", True, C_TEXT), (r.right + 20, r.y + 3))
        for i, (key, label) in enumerate(self.CHECKS):
            r = self.check_rect(i)
            box = self.bank.scaled(f"ui/menu/checkbox{'_on' if st[key] else ''}.png", (r.w, r.h))
            if box is not None:
                s.blit(box, r.topleft)
            else:
                pygame.draw.rect(s, C_ACCENT if st[key] else C_MUTED, r, 0 if st[key] else 2)
            s.blit(self.font.render(label, True, C_TEXT), (r.right + 16, r.y + 9))
        r = self.color_rect()
        pygame.draw.rect(s, pygame.Color(st["crosshair_color"]), r)
        pygame.draw.rect(s, C_TEXT, r, 1)
        s.blit(self.font.render("Crosshair colour (click)", True, C_MUTED), (r.right + 12, r.y + 9))
        self.draw_crosshair_preview((r.centerx + 60, r.bottom + 60))
        cb = self.controls_button()
        mouse = pygame.mouse.get_pos()
        if not draw_nine_slice(s, self.bank, f"ui/menu/{'button_hover' if cb.rect.collidepoint(mouse) else 'button'}.png", cb.rect, 4, SCALE):
            pygame.draw.rect(s, C_MUTED, cb.rect, 1)
        s.blit(self.font.render(cb.label, True, C_TEXT), (cb.rect.x + 18, cb.rect.y + 13))
        b = self.back_button()
        state = "button_hover" if b.rect.collidepoint(mouse) else "button"
        if not draw_nine_slice(s, self.bank, f"ui/menu/{state}.png", b.rect, 4, SCALE):
            pygame.draw.rect(s, C_MUTED, b.rect, 1)
        s.blit(self.font.render(b.label, True, C_TEXT), (b.rect.x + 18, b.rect.y + 15))

    # ------------------------------------------------------------ layout
    def buttons(self) -> list[Button]:
        if self.view in ("settings", "controls"):
            return [self.back_button()]
        x, y, w, h, gap = 60, 140, 360, 38, 6
        rows = [("Practice vs bots", "local"), ("Practice range", "range"), ("Host LAN match", "host"),
                ("Host online (join code)", "host_online"),
                ("Find LAN match", "find"),
                (f"Join {self.address or '…'}", "join"), (f"Map: {self.args.map}", "map"),
                (f"Team size: {self.args.team_size}v{self.args.team_size}", "size"),
                (f"Rounds to win: {self.args.rounds}", "rounds"), (f"Mode: {MODE_NAMES[getattr(self.args, 'mode', 'standard')]}", "mode"),
                ("Settings", "settings"), ("Quit", "quit")]
        out = []
        for i, (label, action) in enumerate(rows):
            enabled = action != "join" or bool(self.address)
            out.append(Button(pygame.Rect(x, y + i * (h + gap), w, h), label, action, enabled))
        for i, (address, port, host_name) in enumerate(self.found[:4]):
            out.append(Button(pygame.Rect(460, 260 + i * (h + gap), 380, h), f"Join {host_name} ({address})", f"lan:{i}"))
        return out

    def address_rect(self) -> pygame.Rect:
        return pygame.Rect(460, 200, 380, 48)

    # ------------------------------------------------------------ loop
    def run(self) -> argparse.Namespace | None:
        clock = pygame.time.Clock()
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)
        while True:
            clock.tick(60)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return None
                if ev.type == pygame.KEYDOWN and self.binding is not None:
                    if ev.key != pygame.K_ESCAPE:
                        name = pygame.key.name(ev.key)
                        keys = self.settings["keys"]
                        for other, bound in list(keys.items()):
                            if bound == name and other != self.binding:
                                keys[other] = keys[self.binding]  # swap instead of double binding
                        keys[self.binding] = name
                    self.binding = None
                    continue
                if ev.type == pygame.KEYDOWN and self.typing_name:
                    if ev.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                        self.typing_name = False
                    elif ev.key == pygame.K_BACKSPACE:
                        self.settings["name"] = self.settings["name"][:-1]
                    elif ev.unicode and ev.unicode.isprintable() and len(self.settings["name"]) < 16:
                        self.settings["name"] += ev.unicode
                    continue
                if ev.type == pygame.MOUSEMOTION and self.dragging:
                    self.slide(ev.pos)
                    continue
                if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.dragging:
                    self.dragging = None
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.view in ("settings", "controls"):
                    self.settings_click(ev.pos)
                if ev.type == pygame.KEYDOWN and self.typing:
                    if ev.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                        self.typing = False
                    elif ev.key == pygame.K_BACKSPACE:
                        self.address = self.address[:-1]
                    elif ev.unicode and (ev.unicode.isalnum() or ev.unicode in ".:-") and len(self.address) < 40:
                        self.address += ev.unicode
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    return None
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    self.typing = self.address_rect().collidepoint(ev.pos)
                    hit = next((b for b in self.buttons() if b.rect.collidepoint(ev.pos) and b.enabled), None)
                    self.pressed = hit.action if hit else None
                elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.pressed:
                    hit = next((b for b in self.buttons() if b.rect.collidepoint(ev.pos) and b.enabled), None)
                    action, self.pressed = self.pressed, None
                    if hit and hit.action == action:
                        result = self.activate(action)
                        if result is not None:
                            return result if result is not False else None
            self.draw()
            pygame.display.flip()

    def activate(self, action: str) -> argparse.Namespace | bool | None:
        a = self.args
        if action == "quit":
            return False
        if action == "settings":
            self.view = "settings"
            return None
        if action == "back" and self.view == "controls":
            self.view = "settings"
            return None
        if action == "back":
            if not self.settings["name"].strip():
                self.settings["name"] = "Player"
            user_settings.save(self.settings)
            self.apply_settings()
            self.view = "main"
            return None
        if action == "local":
            a.host, a.join, a.practice = False, None, False
            return a
        if action == "range":
            a.host, a.join, a.practice = False, None, True
            return a
        if action == "host":
            a.host, a.join, a.online = True, None, False
            return a
        if action == "host_online":
            a.host, a.join, a.online = True, None, True
            return a
        if action == "join" and self.address:
            lan = "." in self.address or self.address.lower() == "localhost"
            target = f"{self.address}:{DEFAULT_PORT}" if lan and ":" not in self.address else self.address
            a.host, a.join, a.online = False, target, False
            return a
        if action == "find":
            self.status = "Searching the local network …"
            self.draw()
            pygame.display.flip()
            self.found = discover(2.0)
            self.status = f"{len(self.found)} match(es) found" if self.found else "No match found on this network"
        elif action.startswith("lan:"):
            address, port, _ = self.found[int(action[4:])]
            a.host, a.join = False, f"{address}:{port}"
            return a
        elif action == "map":
            a.map = self.maps[(self.maps.index(a.map) + 1) % len(self.maps)]
        elif action == "size":
            a.team_size = a.team_size % 5 + 1
        elif action == "mode":
            order = list(MODE_NAMES)
            a.mode = order[(order.index(getattr(a, "mode", "standard")) + 1) % len(order)]
        elif action == "rounds":
            a.rounds = {13: 5, 5: 9, 9: 13}.get(a.rounds, 13)
        return None

    # ------------------------------------------------------------ drawing
    def draw(self) -> None:
        s = self.screen
        w, h = s.get_size()
        bg = self.bank.scaled("ui/menu/title_background.png", (w, h))
        if bg is not None:
            s.blit(bg, (0, 0))
        else:
            s.fill(C_BG)
        if self.view in ("settings", "controls"):
            shade = pygame.Surface((w, h), pygame.SRCALPHA)
            shade.fill((10, 10, 16, 200))
            s.blit(shade, (0, 0))
            self.draw_settings() if self.view == "settings" else self.draw_controls()
            cursor = self.bank.scaled("ui/menu/cursor.png", (24, 24))
            if cursor is not None:
                pygame.mouse.set_visible(False)
                s.blit(cursor, pygame.mouse.get_pos())
            return
        logo = self.bank.scaled("logo.png", (96, 96))
        if logo is not None:
            s.blit(logo, (60, 40))
        title = self.big.render("Val2d", True, C_TEXT)
        s.blit(title, (170 if logo else 60, 70))
        mouse = pygame.mouse.get_pos()
        for b in self.buttons():
            state = "button_disabled" if not b.enabled else "button_pressed" if self.pressed == b.action \
                else "button_hover" if b.rect.collidepoint(mouse) else "button"
            if not draw_nine_slice(s, self.bank, f"ui/menu/{state}.png", b.rect, 4, SCALE):
                pygame.draw.rect(s, (60, 58, 72) if state == "button_hover" else (36, 35, 45), b.rect)
                pygame.draw.rect(s, C_MUTED, b.rect, 1)
            label = self.font.render(b.label, True, C_TEXT if b.enabled else C_MUTED)
            s.blit(label, (b.rect.x + 18, b.rect.centery - label.get_height() / 2))
        field = self.address_rect()
        s.blit(self.font.render(f"Playing as {self.settings['name']}", True, C_MUTED), (460, 170))
        if not draw_nine_slice(s, self.bank, "ui/menu/textfield.png", field, 4, SCALE):
            pygame.draw.rect(s, (36, 35, 45), field)
            pygame.draw.rect(s, C_ACCENT if self.typing else C_MUTED, field, 1)
        shown = self.address + ("_" if self.typing else "")
        text = self.font.render(shown or "Join code or LAN address (click to type)", True, C_TEXT if self.address else C_MUTED)
        s.blit(text, (field.x + 16, field.centery - text.get_height() / 2))
        if self.status:
            msg = self.font.render(self.status, True, C_ERROR if "No match" in self.status else C_ACCENT)
            s.blit(msg, (60, h - 50))
        cursor = self.bank.scaled("ui/menu/cursor.png", (24, 24))
        if cursor is not None:
            pygame.mouse.set_visible(False)
            s.blit(cursor, mouse)
