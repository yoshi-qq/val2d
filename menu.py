"""Main menu of Val2d: play against bots, practice, host or join a network match, browse agents, settings.

Returns the chosen settings as an argparse.Namespace for client.game.Game, or None to quit.
Esc closes whatever is open (dialog, settings, a tab) and never quits; closing the window (Alt+F4) asks first,
a second Alt+F4 quits at once.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pygame

import user_settings
from client.ui import Ui, color
from gameplay.kit.describe import cost_text, describe
from gameplay.netgame import DEFAULT_PORT, discover
from gameplay.world import map_keys as world_map_keys
from sprite_bank import ASSETS, SpriteBank

MODES = (("standard", "Standard", "13 rounds to win, sides switch after 12. Plant or defuse the bomb."),
         ("quick", "Quick", "First to 4, shorter rounds, same economy."),
         ("deathmatch", "Team deathmatch", "Respawns, free buying, first team to the kill limit."))
TABS = (("play", "Play"), ("practice", "Practice"), ("online", "Multiplayer"), ("agents", "Agents"))
SETTINGS_TABS = (("general", "General"), ("crosshair", "Crosshair"), ("controls", "Controls"))
SLIDERS = {"general": (("sensitivity", "Mouse sensitivity"), ("camera_push", "Camera ahead"), ("volume", "Volume")),
           "crosshair": (("crosshair_size", "Size"), ("crosshair_gap", "Gap"))}
CHECKS = {"general": (("fullscreen", "Fullscreen"), ("all_around", "All-around sight (lobby rule)"),
                      ("sound_rings", "Sound rings (lobby rule)")),
          "crosshair": (("crosshair_dot", "Centre dot"),)}
ROLE_ORDER = ("Duelist", "Initiator", "Controller", "Sentinel")


def map_keys() -> list[str]:
    return world_map_keys() or ["werkhof"]


class MainMenu:
    def __init__(self, screen: pygame.Surface, font: pygame.font.Font, big: pygame.font.Font, defaults: argparse.Namespace) -> None:
        self.screen = screen
        self.font, self.big = font, big
        self.ui = Ui(screen)
        self.bank = SpriteBank()
        self.args = defaults
        if not hasattr(self.args, "mode"):
            self.args.mode = "standard"
        self.maps = map_keys()
        if self.args.map not in self.maps:
            self.args.map = self.maps[0]
        self.address = ""
        self.typing = False
        self.status = ""
        self.found: list[tuple[str, int, str]] = []
        self.tab = "play"
        self.view = "main"            # main or settings (overlay)
        self.settings_tab = "general"
        self.dialog = ""              # "" or "quit"
        self.settings = user_settings.load()
        self.dragging: str | None = None
        self.typing_name = False
        self.binding: str | None = None
        self.agent_view = getattr(self.args, "agent", "kestrel")
        self.apply_settings()

    def apply_settings(self) -> None:
        a, st = self.args, self.settings
        a.sensitivity, a.camera_push, a.volume = st["sensitivity"], st["camera_push"], st["volume"]
        a.name = st["name"]
        a.all_around, a.sound_rings = st["all_around"] or a.all_around, st["sound_rings"] or a.sound_rings
        a.fullscreen = bool(st.get("fullscreen", False))
        a.keys = dict(st["keys"])
        a.crosshair = {k: st[k] for k in ("crosshair_color", "crosshair_size", "crosshair_gap", "crosshair_dot")}

    def agents(self) -> dict[str, dict]:
        from gameplay.match import load_agents
        return load_agents()

    # ------------------------------------------------------------ loop
    def run(self) -> argparse.Namespace | None:
        clock = pygame.time.Clock()
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)
        while True:
            clock.tick(60)
            for ev in pygame.event.get():
                result = self.handle(ev)
                if result is not None:
                    return result if result is not False else None
            self.draw()
            pygame.display.flip()

    def handle(self, ev: pygame.event.Event) -> argparse.Namespace | bool | None:
        """One input event. Returns a Namespace to start a match, False to quit, None to stay."""
        if ev.type == pygame.QUIT:
            if self.dialog == "quit":
                return False  # second Alt+F4: quit at once
            self.dialog = "quit"
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
            return None
        if ev.type == pygame.KEYDOWN and (self.typing_name or self.typing):
            target = "name" if self.typing_name else "address"
            text = self.settings["name"] if target == "name" else self.address
            if ev.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_KP_ENTER):
                self.typing_name = self.typing = False
                if target == "address" and ev.key != pygame.K_ESCAPE and self.address:
                    return self.activate("join")
                return None
            if ev.key == pygame.K_BACKSPACE:
                text = text[:-1]
            elif ev.unicode and ev.unicode.isprintable():
                ok = (len(text) < 16) if target == "name" else (len(text) < 40 and (ev.unicode.isalnum() or ev.unicode in ".:-"))
                text += ev.unicode if ok else ""
            if target == "name":
                self.settings["name"] = text
            else:
                self.address = text
            return None
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.close_top()
            return None
        if ev.type == pygame.MOUSEMOTION and self.dragging:
            self.slide(ev.pos)
            return None
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self.dragging = None
            hit = self.ui.hit_at(ev.pos)
            action, self.ui.pressed = self.ui.pressed, None
            if hit and action == hit.action:
                return self.activate(action)
            return None
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            hit = self.ui.hit_at(ev.pos)
            self.typing = self.typing_name = False
            if hit is None:
                return None
            if hit.action.startswith("slider:"):
                self.dragging = hit.action[7:]
                self.slide(ev.pos)
                return None
            if hit.action in ("field:address", "field:name"):
                self.typing, self.typing_name = hit.action == "field:address", hit.action == "field:name"
                return None
            self.ui.pressed = hit.action
        return None

    def close_top(self) -> None:
        """Esc: closes the topmost thing that is open; on the home tab nothing happens."""
        if self.dialog:
            self.dialog = ""
        elif self.view == "settings":
            self.activate("settings_close")
        elif self.tab != "play":
            self.tab = "play"

    def slide(self, pos: tuple[int, int]) -> None:
        hit = next((h for h in self.ui.hits if h.action == f"slider:{self.dragging}"), None)
        if hit is None or not self.dragging:
            return
        r = hit.rect
        low, high = user_settings.LIMITS[self.dragging]
        frac = max(0.0, min(1.0, (pos[0] - r.x) / max(1, r.w)))
        self.settings[self.dragging] = round(low + frac * (high - low), 3)

    def activate(self, action: str) -> argparse.Namespace | bool | None:
        a = self.args
        if action == "quit":
            self.dialog = "quit"
        elif action == "quit_yes":
            return False
        elif action == "quit_no":
            self.dialog = ""
        elif action.startswith("tab:"):
            self.tab = action[4:]
        elif action == "settings":
            self.view = "settings"
        elif action.startswith("stab:"):
            self.settings_tab = action[5:]
        elif action in ("settings_close", "back"):
            if not self.settings["name"].strip():
                self.settings["name"] = "Player"
            user_settings.save(self.settings)
            self.apply_settings()
            self.view, self.binding = "main", None
        elif action.startswith("check:"):
            key = action[6:]
            self.settings[key] = not self.settings[key]
        elif action == "color":
            colors = user_settings.CROSSHAIR_COLORS
            current = self.settings["crosshair_color"]
            self.settings["crosshair_color"] = colors[(colors.index(current) + 1) % len(colors)] if current in colors else colors[0]
        elif action.startswith("bind:"):
            self.binding = action[5:]
        elif action == "local":
            a.host, a.join, a.practice = False, None, False
            return a
        elif action == "range":
            a.host, a.join, a.practice = False, None, True
            return a
        elif action == "host":
            a.host, a.join, a.online = True, None, False
            return a
        elif action == "host_online":
            a.host, a.join, a.online = True, None, True
            return a
        elif action == "join" and self.address:
            lan = "." in self.address or self.address.lower() == "localhost"
            target = f"{self.address}:{DEFAULT_PORT}" if lan and ":" not in self.address else self.address
            a.host, a.join, a.online = False, target, False
            return a
        elif action == "find":
            self.status = "Searching the local network …"
            self.draw()
            pygame.display.flip()
            self.found = discover(2.0)
            self.status = f"{len(self.found)} match(es) found" if self.found else "No match found on this network"
        elif action.startswith("lan:"):
            address, port, _ = self.found[int(action[4:])]
            a.host, a.join = False, f"{address}:{port}"
            return a
        elif action.startswith("mode:"):
            a.mode = action[5:]
        elif action in ("map_next", "map_prev"):
            step = 1 if action == "map_next" else -1
            a.map = self.maps[(self.maps.index(a.map) + step) % len(self.maps)]
        elif action.startswith("size:"):
            a.team_size = int(action[5:])
        elif action.startswith("rounds:"):
            a.rounds = int(action[7:])
        elif action.startswith("agent:"):
            self.agent_view = action[6:]
        elif action == "pick_agent":
            a.agent = self.agent_view
            self.status = f"{self.agents()[a.agent]['name']} selected"
        return None

    # ------------------------------------------------------------ drawing
    def draw(self) -> None:
        s, ui = self.screen, self.ui
        ui.begin()
        w, h = s.get_size()
        bg = self.bank.scaled("ui/menu/title_background.png", (w, h))
        if bg is not None:
            s.blit(bg, (0, 0))
            shade = pygame.Surface((w, h), pygame.SRCALPHA)
            for x in range(0, w, 8):  # darker on the left where the content sits
                alpha = int(235 - 120 * x / w)
                pygame.draw.rect(shade, (15, 25, 35, alpha), (x, 0, 8, h))
            s.blit(shade, (0, 0))
        else:
            s.fill(color("bg"))
        self.draw_top_bar(w)
        {"play": self.draw_play, "practice": self.draw_practice, "online": self.draw_online, "agents": self.draw_agents}[self.tab](w, h)
        if self.status:
            ui.text(self.status, (40, h - 34), "s", "enemy" if "No match" in self.status or "No connection" in self.status else "gold")
        if self.view == "settings":
            self.draw_settings(w, h)
        if self.dialog == "quit":
            ui.dialog("Quit Val2d?", "Alt+F4 again quits at once.", [("Cancel", "quit_no", False), ("Quit", "quit_yes", True)])

    def draw_top_bar(self, w: int) -> None:
        ui = self.ui
        ui.panel(pygame.Rect(0, 0, w, 64), "panel")
        ui.line((0, 64), (w, 64), "line")
        logo = self.bank.scaled("logo.png", (40, 40))
        if logo is not None:
            self.screen.blit(logo, (24, 12))
        ui.text("VAL2D", (74 if logo else 24, 18), "l", "text", bold=True, kind="title")
        x = 300
        for key, label in TABS:
            tw = ui.size(label, "m", upper=True, bold=True)[0] + 40
            ui.tab(pygame.Rect(x, 8, tw, 52), label, f"tab:{key}", self.tab == key)
            x += tw
        ui.button(pygame.Rect(w - 260, 14, 130, 36), "Settings", "settings", size="s")
        ui.button(pygame.Rect(w - 116, 14, 92, 36), "Quit", "quit", size="s")
        ui.text(f"Playing as {self.settings['name']}  ·  {self.agents().get(self.args.agent, {}).get('name', self.args.agent)}",
                (w - 24, 72), "s", "muted", "right")

    def section(self, title: str, pos: tuple[int, int], sub: str = "") -> None:
        self.ui.text(title, pos, "xl", "text", upper=True, bold=True, kind="title")
        if sub:
            self.ui.text(sub, (pos[0] + 2, pos[1] + 56), "s", "muted")

    def draw_play(self, w: int, h: int) -> None:
        ui, a = self.ui, self.args
        self.section("Play", (40, 96), "Match against bots. Pick a mode and a map, then start.")
        for i, (key, name, text) in enumerate(MODES):
            r = pygame.Rect(40 + i * 300, 190, 284, 120)
            chosen = getattr(a, "mode", "standard") == key
            ui.panel(r, "panel_light" if chosen else "panel", edge="left" if chosen else "", edge_col="accent")
            ui.outline(r, "text" if r.collidepoint(pygame.mouse.get_pos()) else "line")
            ui.text(name, (r.x + 18, r.y + 16), "m", "text", upper=True, bold=True)
            for j, ln in enumerate(ui.wrap(text, "s", r.w - 36)):
                ui.text(ln, (r.x + 18, r.y + 50 + j * 20), "s", "muted")
            ui.area(r, f"mode:{key}")
        self._options_row(330)
        ui.button(pygame.Rect(w - 340, h - 110, 300, 64), "Start", "local", primary=True, size="l")

    def _options_row(self, y: int) -> None:
        ui, a = self.ui, self.args
        ui.text("Map", (40, y), "s", "muted", upper=True)
        ui.button(pygame.Rect(40, y + 26, 44, 44), "<", "map_prev")
        ui.panel(pygame.Rect(92, y + 26, 240, 44), "panel")
        ui.text(a.map, (212, y + 36), "m", "text", "center", upper=True, bold=True)
        ui.button(pygame.Rect(340, y + 26, 44, 44), ">", "map_next")
        ui.text("Team size", (440, y), "s", "muted", upper=True)
        for i in range(1, 6):
            ui.button(pygame.Rect(440 + (i - 1) * 52, y + 26, 44, 44), f"{i}", f"size:{i}", selected=a.team_size == i)
        ui.text("Rounds to win", (740, y), "s", "muted", upper=True)
        for i, n in enumerate((5, 9, 13)):
            ui.button(pygame.Rect(740 + i * 64, y + 26, 56, 44), str(n), f"rounds:{n}", selected=a.rounds == n)
        has_preview = (ASSETS / "maps" / a.map / "preview.png").exists()  # optional, from the design session
        preview = self.bank.scaled(f"maps/{a.map}/preview.png", (344, 194)) if has_preview else None
        if preview is not None:
            self.screen.blit(preview, (40, y + 90))

    def draw_practice(self, w: int, h: int) -> None:
        ui = self.ui
        self.section("Practice", (40, 96), "Warm up alone.")
        cards = (("Range", "Lanes at 10, 20, 30 and 45 m with standing and moving targets. Buy anything, accuracy shown on top.", "range"),
                 ("Bots", "A match against bots with the mode and map from the Play tab.", "local"))
        for i, (title, text, action) in enumerate(cards):
            r = pygame.Rect(40 + i * 460, 190, 440, 220)
            ui.panel(r, "panel", edge="left")
            ui.text(title, (r.x + 24, r.y + 20), "l", "text", upper=True, bold=True, kind="title")
            for j, ln in enumerate(ui.wrap(text, "s", r.w - 48)):
                ui.text(ln, (r.x + 24, r.y + 70 + j * 22), "s", "muted")
            ui.button(pygame.Rect(r.x + 24, r.bottom - 64, 180, 44), "Start", action, primary=True)

    def draw_online(self, w: int, h: int) -> None:
        ui = self.ui
        self.section("Multiplayer", (40, 96), "Play with friends on the same network or over the internet.")
        host = pygame.Rect(40, 190, 440, 240)
        ui.panel(host, "panel", edge="left")
        ui.text("Host", (host.x + 24, host.y + 20), "l", "text", upper=True, bold=True, kind="title")
        ui.text(f"Map {self.args.map} · {dict((k, n) for k, n, _ in MODES)[getattr(self.args, 'mode', 'standard')]}",
                (host.x + 24, host.y + 66), "s", "muted")
        ui.button(pygame.Rect(host.x + 24, host.y + 110, 392, 44), "Host LAN match", "host", primary=True)
        ui.button(pygame.Rect(host.x + 24, host.y + 166, 392, 44), "Host online (join code)", "host_online")
        join = pygame.Rect(520, 190, 520, 240)
        ui.panel(join, "panel", edge="left")
        ui.text("Join", (join.x + 24, join.y + 20), "l", "text", upper=True, bold=True, kind="title")
        field = pygame.Rect(join.x + 24, join.y + 70, 340, 44)
        ui.fill(field, "panel_light")
        ui.outline(field, "accent" if self.typing else "line")
        shown = self.address + ("_" if self.typing else "")
        ui.text(shown or "Join code or LAN address", (field.x + 14, field.y + 12), "m", "text" if self.address else "muted")
        ui.area(field, "field:address")
        ui.button(pygame.Rect(field.right + 12, field.y, 120, 44), "Join", "join", primary=True, enabled=bool(self.address))
        ui.button(pygame.Rect(join.x + 24, join.y + 130, 220, 40), "Find LAN match", "find")
        for i, (address, port, host_name) in enumerate(self.found[:4]):
            ui.button(pygame.Rect(join.x + 24, join.y + 250 + i * 48, 472, 40), f"{host_name}  {address}", f"lan:{i}")

    def draw_agents(self, w: int, h: int) -> None:
        ui = self.ui
        agents = self.agents()
        self.section("Agents", (40, 96))
        x0, y0, cell = 40, 170, 64
        ordered = sorted(agents.items(), key=lambda kv: (ROLE_ORDER.index(kv[1]["role"]) if kv[1]["role"] in ROLE_ORDER else 9, kv[1]["name"]))
        for i, (key, info) in enumerate(ordered):
            r = pygame.Rect(x0 + (i % 6) * (cell + 8), y0 + (i // 6) * (cell + 8), cell, cell)
            chosen, viewing = key == self.args.agent, key == self.agent_view
            ui.fill(r, "panel_light" if viewing else "panel")
            pic = self.bank.scaled(f"agents/{key}/{key}_portrait.png", (cell - 8, cell - 8))
            if pic is not None:
                self.screen.blit(pic, (r.x + 4, r.y + 4))
            else:
                ui.text(info["name"][:2], (r.centerx, r.y + 20), "m", "text", "center", upper=True)
            ui.outline(r, "accent" if viewing else "gold" if chosen else "line", 2 if viewing or chosen else 1)
            ui.area(r, f"agent:{key}")
        info = agents.get(self.agent_view)
        if info is None:
            return
        px = x0 + 6 * (cell + 8) + 30
        ui.panel(pygame.Rect(px - 16, 150, w - px - 8, h - 280), "panel")
        big = self.bank.scaled(f"agents/{self.agent_view}/{self.agent_view}_select.png", (120, 240))
        if big is not None:
            self.screen.blit(big, (px, 170))
            px += 150
        ui.text(info["name"], (px, 160), "xl", "text", upper=True, bold=True, kind="title")
        ui.text(info["role"], (px + 2, 214), "m", "accent", upper=True, bold=True)
        y = 256
        width = w - px - 40
        for slot in ("C", "Q", "E", "X"):
            ab = info["abilities"][slot]
            ui.keycap((px, y), slot, "s")
            icon = self.bank.scaled(f"ui/faehigkeit_{self.agent_view}_{slot}.png", (28, 28))
            tx = px + 40
            if icon is not None:
                self.screen.blit(icon, (tx, y - 4))
                tx += 36
            ui.text(ab["name"], (tx, y), "m", "text", upper=True, bold=True)
            ui.text(cost_text(slot, ab), (px + width, y + 2), "xs", "gold" if slot == "X" else "muted", "right")
            for j, ln in enumerate(ui.wrap(describe(ab), "s", width - 40)):
                ui.text(ln, (px + 40, y + 28 + j * 20), "s", "muted")
            y += 36 + 20 * len(ui.wrap(describe(ab), "s", width - 40)) + 16
        chosen = self.agent_view == self.args.agent
        ui.button(pygame.Rect(w - 300, h - 100, 260, 56), "Selected" if chosen else "Select", "pick_agent", primary=not chosen,
                  enabled=not chosen)

    def draw_settings(self, w: int, h: int) -> None:
        ui, st = self.ui, self.settings
        ui.shade()
        box = pygame.Rect(120, 70, w - 240, h - 140)
        ui.panel(box, "bg", edge="top")
        ui.outline(box, "line")
        ui.text("Settings", (box.x + 32, box.y + 22), "l", "text", upper=True, bold=True, kind="title")
        x = box.x + 260
        for key, label in SETTINGS_TABS:
            tw = ui.size(label, "m", upper=True, bold=True)[0] + 40
            ui.tab(pygame.Rect(x, box.y + 12, tw, 50), label, f"stab:{key}", self.settings_tab == key)
            x += tw
        ui.button(pygame.Rect(box.right - 150, box.y + 18, 120, 36), "Close", "settings_close", size="s")
        ui.line((box.x, box.y + 70), (box.right, box.y + 70))
        y = box.y + 96
        if self.settings_tab == "general":
            ui.text("Name", (box.x + 40, y + 10), "s", "muted", upper=True)
            field = pygame.Rect(box.x + 300, y, 360, 40)
            ui.fill(field, "panel_light")
            ui.outline(field, "accent" if self.typing_name else "line")
            ui.text(st["name"] + ("_" if self.typing_name else ""), (field.x + 12, field.y + 10), "m")
            ui.area(field, "field:name")
            y += 64
        if self.settings_tab in SLIDERS:
            for key, label in SLIDERS[self.settings_tab]:
                low, high = user_settings.LIMITS[key]
                ui.text(label, (box.x + 40, y + 2), "s", "muted", upper=True)
                ui.slider(pygame.Rect(box.x + 300, y, 360, 20), (st[key] - low) / (high - low), f"slider:{key}")
                ui.text(f"{st[key]:.2f}", (box.x + 690, y), "s")
                y += 52
            for key, label in CHECKS.get(self.settings_tab, ()):
                ui.checkbox(pygame.Rect(box.x + 40, y, 26, 26), bool(st[key]), f"check:{key}")
                ui.text(label, (box.x + 80, y + 3), "s")
                y += 44
        if self.settings_tab == "crosshair":
            r = pygame.Rect(box.x + 300, y, 40, 40)
            pygame.draw.rect(self.screen, pygame.Color(st["crosshair_color"]), r)
            ui.outline(r, "text")
            ui.area(r, "color")
            ui.text("Colour (click)", (box.x + 40, y + 10), "s", "muted", upper=True)
            prev = pygame.Rect(box.right - 260, box.y + 110, 200, 200)
            ui.fill(prev, "panel_light")
            self.draw_crosshair_preview(prev.center)
        if self.settings_tab == "controls":
            mouse = pygame.mouse.get_pos()
            for i, (action, key) in enumerate(st["keys"].items()):
                col, row = divmod(i, 10)
                r = pygame.Rect(box.x + 40 + col * 500, y + row * 42, 470, 36)
                active = self.binding == action
                ui.fill(r, "panel_light" if r.collidepoint(mouse) or active else "panel")
                ui.text(action.replace("_", " "), (r.x + 14, r.y + 9), "s", "muted", upper=True)
                ui.text("press a key …" if active else key, (r.right - 14, r.y + 8), "s", "accent" if active else "text", "right",
                        upper=not active, bold=True)
                ui.area(r, f"bind:{action}")
            ui.text("Click an action, then press the new key (Esc keeps the old one).", (box.x + 40, box.bottom - 40), "s", "muted")

    def draw_crosshair_preview(self, at: tuple[int, int]) -> None:
        st = self.settings
        col = pygame.Color(st["crosshair_color"])
        size, gap = 7 * st["crosshair_size"], st["crosshair_gap"]
        x, y = at
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            pygame.draw.line(self.screen, col, (x + dx * gap, y + dy * gap), (x + dx * (gap + size), y + dy * (gap + size)), 2)
        if st["crosshair_dot"]:
            pygame.draw.circle(self.screen, col, (x, y), 2)
