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
from client.settings_panel import SettingsPanel
from client.ui import Ui, color
from gameplay.kit.describe import cost_text, describe
from gameplay.netgame import DEFAULT_PORT, discover
from gameplay.world import map_keys as world_map_keys
from sprite_bank import ASSETS, SpriteBank

MODES = (("standard", "Standard", "13 rounds to win, sides switch after 12. Plant or defuse the bomb."),
         ("quick", "Quick", "First to 4, shorter rounds, same economy."),
         ("deathmatch", "Team deathmatch", "Respawns, free buying, first team to the kill limit."))
TABS = (("agents", "Agents"), ("play", "Play"), ("career", "Career"))  # PLAY sits in the middle, large
PLAY_MODES = (("standard", "Unrated", "13 rounds to win, sides switch after 12. Plant or defuse the spike."),
              ("quick", "Swiftplay", "First to 4, shorter rounds, same economy."),
              ("deathmatch", "Team deathmatch", "Respawns, free buying, first team to the kill limit."),
              ("range", "Range", "Practice alone: lanes at 10, 20, 30 and 45 m, standing and moving targets."),
              ("custom", "Custom", "Host or join a match with friends on your network or over the internet."))
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
        self.view = "main"
        self.play_mode = getattr(self.args, "mode", "standard") if not getattr(self.args, "practice", False) else "range"            # main or settings (overlay)
        self.dialog = ""              # "" or "quit"
        self.panel = SettingsPanel(self.ui)
        self.settings = self.panel.settings
        self.agent_view = getattr(self.args, "agent", "kestrel")
        self.apply_settings()

    def apply_settings(self) -> None:
        a, st = self.args, self.settings
        a.sensitivity, a.camera_push, a.volume = st["sensitivity"], st["camera_push"], st["volume"]
        a.name = st["name"]
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
        if self.view == "settings" and not self.dialog:
            if self.panel.handle(ev) == "closed":
                self.settings = self.panel.settings
                self.apply_settings()
                self.view = "main"
            return None
        if ev.type == pygame.KEYDOWN and self.typing:
            if ev.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_KP_ENTER):
                self.typing = False
                if ev.key != pygame.K_ESCAPE and self.address:
                    return self.activate("join")
                return None
            if ev.key == pygame.K_BACKSPACE:
                self.address = self.address[:-1]
            elif ev.unicode and (ev.unicode.isalnum() or ev.unicode in ".:-") and len(self.address) < 40:
                self.address += ev.unicode
            return None
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.close_top()
            return None
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            hit = self.ui.hit_at(ev.pos)
            action, self.ui.pressed = self.ui.pressed, None
            if hit and action == hit.action:
                return self.activate(action)
            return None
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            hit = self.ui.hit_at(ev.pos)
            self.typing = False
            if hit is None:
                return None
            if hit.action == "field:address":
                self.typing = True
                return None
            self.ui.pressed = hit.action
        return None

    def close_top(self) -> None:
        """Esc: closes the topmost thing that is open; on the home tab nothing happens."""
        if self.dialog:
            self.dialog = ""
        elif self.view == "settings":
            self.panel.close()
            self.apply_settings()
            self.view = "main"
        elif self.tab != "play":
            self.tab = "play"
        elif self.play_mode == "custom":
            self.play_mode = "standard"


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
            self.panel = SettingsPanel(self.ui)
            self.view = "settings"
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
            self.play_mode = action[5:]
            if self.play_mode in ("standard", "quick", "deathmatch"):
                a.mode = self.play_mode
        elif action == "start":
            if self.play_mode == "range":
                return self.activate("range")
            if self.play_mode != "custom":
                a.mode = self.play_mode
                return self.activate("local")
        elif action == "party_add":
            a.team_size = min(5, a.team_size + 1)
        elif action == "party_remove":
            a.team_size = max(1, a.team_size - 1)
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
        {"play": self.draw_play, "agents": self.draw_agents, "career": self.draw_career}[self.tab](w, h)
        if self.status:
            ui.text(self.status, (40, h - 34), "s", "enemy" if "No match" in self.status or "No connection" in self.status else "gold")
        if self.view == "settings":
            self.panel.draw()
        if self.dialog == "quit":
            ui.dialog("Quit Val2d?", "Alt+F4 again quits at once.", [("Cancel", "quit_no", False), ("Quit", "quit_yes", True)])

    def draw_top_bar(self, w: int) -> None:
        """Valorant-style navigation: logo left, AGENTS · PLAY · CAREER centred with PLAY larger, name, settings and
        quit on the right."""
        ui, s = self.ui, self.screen
        bar = pygame.Rect(0, 0, w, 64)
        ui.fill(bar, "#0f1923e6")
        pygame.draw.rect(s, color("line"), (0, 63, w, 1))
        logo = self.bank.scaled("logo.png", (36, 36))
        if logo is not None:
            s.blit(logo, (24, 14))
        ui.text("VAL2D", (68 if logo else 24, 22), "m", "text", bold=True, kind="title")
        cx = w // 2
        for key, label in TABS:
            big = key == "play"
            size = "l" if big else "m"
            tw = ui.size(label, size, upper=True, bold=True)[0]
            x = cx - tw // 2 if big else (cx - 120 - tw if key == "agents" else cx + 120)
            r = pygame.Rect(x - 12, 0, tw + 24, 64)
            active = self.tab == key
            hover = r.collidepoint(pygame.mouse.get_pos())
            ui.text(label, (r.centerx, 32 - ui.size(label, size)[1] // 2), size, "text" if active or hover else "muted",
                    "center", upper=True, bold=True, kind="title")
            if active:
                pygame.draw.rect(s, color("accent"), (r.x + 12, 60, tw, 4))
            ui.area(r, f"tab:{key}")
        ui.text(self.settings["name"], (w - 196, 24), "s", "text", "right", bold=True)
        ui.button(pygame.Rect(w - 180, 14, 96, 36), "Settings", "settings", size="xs")
        ui.button(pygame.Rect(w - 76, 14, 56, 36), "X", "quit", size="s")

    def draw_play(self, w: int, h: int) -> None:
        """Mode row under the top bar, the party in the centre, map selection and START at the bottom centre."""
        ui, a, s = self.ui, self.args, self.screen
        x = w // 2 - sum(ui.size(n, "s", upper=True, bold=True)[0] + 44 for _, n, _ in PLAY_MODES) // 2
        for key, name, _ in PLAY_MODES:
            tw = ui.size(name, "s", upper=True, bold=True)[0] + 44
            r = pygame.Rect(x, 76, tw - 6, 34)
            active = self.play_mode == key
            hover = r.collidepoint(pygame.mouse.get_pos())
            ui.fill(r, "text" if active else "panel_light" if hover else "panel")
            ui.text(name, (r.centerx, r.y + 9), "s", "bg" if active else "text", "center", upper=True, bold=True)
            ui.area(r, f"mode:{key}")
            x += tw
        about = dict((k, t) for k, _, t in PLAY_MODES)[self.play_mode]
        ui.text(about, (w // 2, 120), "xs", "muted", "center", upper=True)
        if self.play_mode == "custom":
            self.draw_custom(w, h)
            return
        self.draw_party(w, h)
        if self.play_mode != "range":
            ui.text("Map", (w // 2, h - 168), "xs", "muted", "center", upper=True)
            ui.button(pygame.Rect(w // 2 - 170, h - 148, 40, 36), "<", "map_prev", size="s")
            ui.fill(pygame.Rect(w // 2 - 126, h - 148, 252, 36), "panel")
            ui.text(a.map, (w // 2, h - 140), "m", "text", "center", upper=True, bold=True)
            ui.button(pygame.Rect(w // 2 + 130, h - 148, 40, 36), ">", "map_next", size="s")
        ui.button(pygame.Rect(w // 2 - 170, h - 96, 340, 64), "Start", "start", primary=True, size="xl")
        ui.text("Rounds, overtime and cheats are set in the lobby", (w // 2, h - 26), "xs", "muted", "center", upper=True)

    def draw_party(self, w: int, h: int) -> None:
        """Five player-card slots like a party: you in the middle, bots of your team around you; click + to add a bot,
        a bot card to remove it (team size)."""
        ui, a, s = self.ui, self.args, self.screen
        card_w, card_h, gap = 150, 300, 16
        slots = 1 if self.play_mode == "range" else 5
        order = [2, 1, 3, 0, 4][:slots] if slots == 5 else [0]
        left = w // 2 - (slots * card_w + (slots - 1) * gap) // 2
        mates = a.team_size - 1
        bot_slots = [1, 3, 0, 4][:mates]
        for i in range(slots):
            r = pygame.Rect(left + i * (card_w + gap), 148, card_w, card_h)
            if slots == 1 or i == 2:
                ui.fill(r, "panel")
                pygame.draw.rect(s, color("accent"), (r.x, r.y, r.w, 4))
                art = self.bank.scaled(f"agents/{a.agent}/{a.agent}_select.png", (120, 240))
                if art is not None:
                    s.blit(art, (r.centerx - 60, r.y + 18))
                band = pygame.Rect(r.x, r.bottom - 44, r.w, 44)
                ui.fill(band, "#0f1923f0")
                ui.text(self.settings["name"], (r.centerx, band.y + 6), "s", "text", "center", bold=True)
                ui.text(self.agents().get(a.agent, {}).get("name", a.agent), (r.centerx, band.y + 24), "xs", "accent", "center",
                        upper=True)
            elif i in bot_slots:
                ui.fill(r, "panel")
                ui.text("Bot", (r.centerx, r.centery - 10), "m", "muted", "center", upper=True, bold=True)
                ui.text("click to remove", (r.centerx, r.centery + 16), "xs", "muted", "center", upper=True)
                ui.outline(r, "text" if r.collidepoint(pygame.mouse.get_pos()) else "line")
                ui.area(r, "party_remove")
            else:
                ui.outline(r, "text" if r.collidepoint(pygame.mouse.get_pos()) else "line")
                ui.text("+", (r.centerx, r.centery - 20), "xl", "muted", "center", bold=True)
                ui.text("add a bot", (r.centerx, r.centery + 24), "xs", "muted", "center", upper=True)
                ui.area(r, "party_add")
        del order
        if self.play_mode != "range":
            ui.text(f"{a.team_size} vs {a.team_size}", (w // 2, 148 + card_h + 10), "s", "text", "center", upper=True, bold=True)

    def draw_custom(self, w: int, h: int) -> None:
        """Custom games: host a lobby (LAN or with a join code) or join one."""
        ui = self.ui
        host = pygame.Rect(w // 2 - 470, 160, 440, 280)
        ui.panel(host, "panel", edge="top")
        ui.text("Host", (host.x + 24, host.y + 20), "l", "text", upper=True, bold=True, kind="title")
        ui.text(f"Map {self.args.map} · lobby rules are set in the lobby", (host.x + 24, host.y + 66), "xs", "muted", upper=True)
        ui.button(pygame.Rect(host.x + 24, host.y + 110, 392, 48), "Host LAN match", "host", primary=True)
        ui.button(pygame.Rect(host.x + 24, host.y + 170, 392, 48), "Host online (join code)", "host_online")
        ui.button(pygame.Rect(host.x + 24, host.y + 228, 40, 36), "<", "map_prev", size="s")
        ui.text(self.args.map, (host.x + 220, host.y + 236), "s", "text", "center", upper=True, bold=True)
        ui.button(pygame.Rect(host.right - 64, host.y + 228, 40, 36), ">", "map_next", size="s")
        join = pygame.Rect(w // 2 + 30, 160, 440, 280)
        ui.panel(join, "panel", edge="top")
        ui.text("Join", (join.x + 24, join.y + 20), "l", "text", upper=True, bold=True, kind="title")
        field = pygame.Rect(join.x + 24, join.y + 70, 272, 44)
        ui.fill(field, "panel_light")
        ui.outline(field, "accent" if self.typing else "line")
        shown = self.address + ("_" if self.typing else "")
        ui.text(shown or "Join code or address", (field.x + 12, field.y + 14), "s", "text" if self.address else "muted")
        ui.area(field, "field:address")
        ui.button(pygame.Rect(field.right + 12, field.y, 108, 44), "Join", "join", primary=True, enabled=bool(self.address))
        ui.button(pygame.Rect(join.x + 24, join.y + 130, 220, 40), "Find LAN match", "find", size="s")
        for i, (address, port, host_name) in enumerate(self.found[:3]):
            ui.button(pygame.Rect(join.x + 24, join.y + 180 + i * 32, 392, 28), f"{host_name}  {address}", f"lan:{i}", size="xs")

    def draw_career(self, w: int, h: int) -> None:
        """Career page: patch notes of the active balance patches (config/patches); match history is not recorded yet."""
        from gameplay.patches import notes
        ui = self.ui
        ui.text("Career", (40, 84), "xl", "text", upper=True, bold=True, kind="title")
        ui.text("Patch notes", (42, 150), "m", "text", upper=True, bold=True)
        active = notes()
        if not active:
            ui.text("No balance patches active (config/patches).", (42, 184), "s", "muted")
        y = 184
        for version, text in reversed(active):
            ui.text(f"Patch {version}", (42, y), "s", "accent", upper=True, bold=True)
            y += 24
            for ln in ui.wrap(text or "(no notes)", "s", w - 120):
                ui.text(ln, (42, y), "s", "text")
                y += 20
            y += 14
        ui.text("Match history is not recorded yet.", (42, h - 40), "xs", "muted", upper=True)







    def draw_agents(self, w: int, h: int) -> None:
        ui = self.ui
        agents = self.agents()
        ui.text("Agents", (40, 84), "xl", "text", upper=True, bold=True, kind="title")
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


