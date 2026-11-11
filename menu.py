"""Main menu of Val2d: practice against bots, host, find or join a network match, settings.

Returns the chosen settings as an argparse.Namespace for play.Game, or None to quit.
Graphics: assets/ui/menu (buttons and panel as 9-slice, title background), placeholders if missing.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pygame

from gameplay.net import DEFAULT_PORT, discover
from gameplay.world import MAP_DIR
from sprite_bank import SpriteBank, draw_nine_slice

C_BG = (22, 21, 28)
C_TEXT = (232, 230, 239)
C_MUTED = (155, 152, 170)
C_ACCENT = (224, 180, 55)
C_ERROR = (238, 76, 74)
SCALE = 3  # pixel-art scale of the menu kit


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

    # ------------------------------------------------------------ layout
    def buttons(self) -> list[Button]:
        x, y, w, h, gap = 60, 200, 360, 48, 12
        rows = [("Practice vs bots", "local"), ("Host a match", "host"), ("Find LAN match", "find"),
                (f"Join {self.address or '…'}", "join"), (f"Map: {self.args.map}", "map"),
                (f"Team size: {self.args.team_size}v{self.args.team_size}", "size"),
                (f"Rounds to win: {self.args.rounds}", "rounds"), ("Quit", "quit")]
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
        if action == "local":
            a.host, a.join = False, None
            return a
        if action == "host":
            a.host, a.join = True, None
            return a
        if action == "join" and self.address:
            a.host, a.join = False, self.address if ":" in self.address else f"{self.address}:{DEFAULT_PORT}"
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
        if not draw_nine_slice(s, self.bank, "ui/menu/textfield.png", field, 4, SCALE):
            pygame.draw.rect(s, (36, 35, 45), field)
            pygame.draw.rect(s, C_ACCENT if self.typing else C_MUTED, field, 1)
        shown = self.address + ("_" if self.typing else "")
        text = self.font.render(shown or "Host address (click to type)", True, C_TEXT if self.address else C_MUTED)
        s.blit(text, (field.x + 16, field.centery - text.get_height() / 2))
        if self.status:
            msg = self.font.render(self.status, True, C_ERROR if "No match" in self.status else C_ACCENT)
            s.blit(msg, (60, h - 50))
        cursor = self.bank.scaled("ui/menu/cursor.png", (24, 24))
        if cursor is not None:
            pygame.mouse.set_visible(False)
            s.blit(cursor, mouse)
