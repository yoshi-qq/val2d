"""Main menu of Val2d: play against bots, host or join a network match, browse agents, settings.

Returns the chosen settings as an argparse.Namespace for client.game.Game, or None to quit.
Esc closes whatever is open (dialog, settings, a tab) and never quits; closing the window (Alt+F4) asks first,
a second Alt+F4 quits at once.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pygame

import user_settings
from client.inventory import Inventory
from client.settings_panel import SettingsPanel
from client.ui import Ui, color
from gameplay.kit.describe import cost_text, describe
from gameplay.match import DEFAULT_AGENT, playable_agents
from gameplay.netgame import DEFAULT_PORT, discover
from gameplay.world import DEFAULT_MAP, PLAYABLE_MAP_KEYS
from sprite_bank import ASSETS, SpriteBank

MODES = (("standard", "Standard", "13 rounds to win, sides switch after 12. Plant or defuse the bomb."),
         ("quick", "Quick", "First to 5, with Swiftplay economy."),
         ("deathmatch", "Team deathmatch", "Respawns, free buying, first team to the kill limit."))
TABS = (("agents", "Agents", -148), ("play", "Play", 0), ("inventory", "Inventory", 140), ("career", "Career", 275))
PLAY_MODES = (("standard", "Unrated", "13 rounds to win, sides switch after 12. Plant or defuse the spike."),
              ("quick", "Swiftplay", "First to 5 rounds. Switch sides after four."),
              ("deathmatch", "Team deathmatch", "Respawns, free buying, first team to the kill limit."),
              ("custom", "Custom", "Host or join a match with friends on your network or over the internet."))
ROLE_ORDER = ("Duelist", "Initiator", "Controller", "Sentinel")


def map_name(key: str) -> str:
    """Display name of a map (its "name"), the key if the file cannot be read."""
    from gameplay.world import load_map_raw
    try:
        return str(load_map_raw(key).get("name", key))
    except (OSError, ValueError):
        return key


class MainMenu:
    def __init__(self, screen: pygame.Surface, font: pygame.font.Font, big: pygame.font.Font, defaults: argparse.Namespace) -> None:
        self.screen = screen
        self.font, self.big = font, big
        self.bank = SpriteBank()
        self.ui = Ui(screen, self.bank)
        self.inventory = Inventory(self.ui)
        self.args = defaults
        if not hasattr(self.args, "mode"):
            self.args.mode = "standard"
        self.maps = list(PLAYABLE_MAP_KEYS)
        self.map_names = {k: map_name(k) for k in self.maps}
        if self.args.map not in self.maps:
            self.args.map = DEFAULT_MAP
        if self.args.agent not in self.agents():
            self.args.agent = DEFAULT_AGENT
        self.address = ""
        self.typing = False
        self.status = ""
        self.found: list[tuple[str, int, str]] = []
        self.tab = "play"
        self.view = "main"
        self.play_mode = self.args.mode
        self.dialog = ""              # "" or "quit"
        self.panel = SettingsPanel(self.ui)
        self.settings = self.panel.settings
        self.career_match: int | None = None  # match shown in detail on the Career page
        self.agent_view = self.args.agent
        self.apply_settings()

    def apply_settings(self) -> None:
        a, st = self.args, self.settings
        a.sensitivity, a.camera_push, a.volume = st["sensitivity"], st["camera_push"], st["volume"]
        a.name = st["name"]
        a.fullscreen = bool(st.get("fullscreen", False))
        a.keys = dict(st["keys"])
        a.crosshair = {k: st[k] for k in ("crosshair_color", "crosshair_size", "crosshair_gap", "crosshair_dot")}

    def agents(self) -> dict[str, dict]:
        return playable_agents()

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
            self.settings = self.panel.settings
            self.apply_settings()
            self.view = "main"
        elif self.career_match is not None:
            self.career_match = None
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
            if self.tab == "inventory":
                self.inventory.open(self.settings["weapon_skins"])
        elif action.startswith("inventory:"):
            if self.inventory.activate(action, self.settings["weapon_skins"]):
                saved = user_settings.load()
                saved["weapon_skins"] = self.settings["weapon_skins"]
                user_settings.save(saved)
        elif action == "settings":
            self.panel = SettingsPanel(self.ui)
            self.view = "settings"
        elif action == "local":
            a.host, a.join, a.practice = False, None, False
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
        elif action.startswith("career:"):
            self.career_match = int(action[7:])
        elif action == "career_back":
            self.career_match = None
        elif action.startswith("agent:"):
            self.agent_view = action[6:]
        elif action == "pick_agent":
            a.agent = self.agent_view
            self.status = f"{self.agents()[a.agent]['name']} selected"
        return None

    # ------------------------------------------------------------ drawing
    def draw(self) -> None:
        s, ui = self.screen, self.ui
        ui.screen = s
        ui.begin()
        w, h = s.get_size()
        bg = self.bank.scaled("ui/menu/title_background.png", (w, h))
        if bg is not None:
            s.blit(bg, (0, 0))
        else:
            s.fill(color("bg"))
        self.draw_top_bar(w)
        if self.tab == "inventory":
            self.inventory.draw(w, h, self.settings["weapon_skins"])
        else:
            {"play": self.draw_play, "agents": self.draw_agents, "career": self.draw_career}[self.tab](w, h)
        if self.status:
            ui.text(self.status, (40, h - 34), "s", "enemy" if "No match" in self.status or "No connection" in self.status else "gold")
        if self.view == "settings":
            self.panel.draw()
        if self.dialog == "quit":
            ui.dialog("Quit Val2d?", "Alt+F4 again quits at once.", [("Cancel", "quit_no", False), ("Quit", "quit_yes", True)])

    def draw_top_bar(self, w: int) -> None:
        """Main tabs around Play, with the profile controls on the right."""
        ui, s = self.ui, self.screen
        bar = pygame.Rect(0, 0, w, 64)
        ui.fill(bar, "#0f1923e6")
        pygame.draw.rect(s, color("line"), (0, 63, w, 1))
        logo = self.bank.scaled("logo.png", (36, 36))
        if logo is not None:
            s.blit(logo, (24, 14))
        ui.text("VAL2D", (68 if logo else 24, 22), "m", "text", bold=True, kind="title")
        cx = w // 2
        for key, label, offset in TABS:
            big = key == "play"
            size = "l" if big else "m"
            tw = ui.size(label, size, upper=True, bold=True)[0]
            x = cx + offset - tw // 2
            r = pygame.Rect(x - 12, 0, tw + 24, 64)
            active = self.tab == key
            hover = r.collidepoint(pygame.mouse.get_pos())
            if active or hover:
                ui.skin("menu/tab_active" if active else "menu/tab", r.inflate(0, -12))
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
            ui.skin("menu/tab_active" if active else "menu/button_hover" if hover else "menu/tab", r)
            ui.text(name, (r.centerx, r.y + 9), "s", "text" if active or hover else "muted", "center", upper=True, bold=True)
            ui.area(r, f"mode:{key}")
            x += tw
        about = dict((k, t) for k, _, t in PLAY_MODES)[self.play_mode]
        ui.text(about, (w // 2, 120), "xs", "muted", "center", upper=True)
        if self.play_mode == "custom":
            self.draw_custom(w, h)
            return
        self.draw_party(w, h)
        ui.text("Map", (w // 2, h - 168), "xs", "muted", "center", upper=True)
        ui.fill(pygame.Rect(w // 2 - 126, h - 148, 252, 36), "panel")
        ui.text(self.map_names.get(a.map, a.map), (w // 2, h - 140), "m", "text", "center", upper=True, bold=True)
        if len(self.maps) > 1:
            ui.button(pygame.Rect(w // 2 - 170, h - 148, 40, 36), "<", "map_prev", size="s")
            ui.button(pygame.Rect(w // 2 + 130, h - 148, 40, 36), ">", "map_next", size="s")
        ui.button(pygame.Rect(w // 2 - 170, h - 96, 340, 64), "Start", "start", primary=True, size="xl")
        ui.text("Rounds, overtime and cheats are set in the lobby", (w // 2, h - 26), "xs", "muted", "center", upper=True)

    def draw_party(self, w: int, h: int) -> None:
        """Five player-card slots like a party: you in the middle, bots of your team around you; click + to add a bot,
        a bot card to remove it (team size)."""
        ui, a, s = self.ui, self.args, self.screen
        card_w, card_h, gap = 150, 300, 16
        slots = 5
        left = w // 2 - (slots * card_w + (slots - 1) * gap) // 2
        mates = a.team_size - 1
        bot_slots = [1, 3, 0, 4][:mates]
        for i in range(slots):
            r = pygame.Rect(left + i * (card_w + gap), 148, card_w, card_h)
            if i == 2:
                if not ui.sprite("menu/party_self", r):
                    ui.panel(r, "panel", edge="top")
                art = self.bank.scaled(f"agents/{a.agent}/{a.agent}_select.png", (120, 240))
                if art is not None:
                    s.blit(art, (r.centerx - 60, r.y + 18))
                band = pygame.Rect(r.x, r.bottom - 44, r.w, 44)
                ui.fill(band, "#0f1923f0")
                ui.text(self.settings["name"], (r.centerx, band.y + 6), "s", "text", "center", bold=True)
                ui.text(self.agents().get(a.agent, {}).get("name", a.agent), (r.centerx, band.y + 24), "xs", "accent", "center",
                        upper=True)
            elif i in bot_slots:
                if not ui.sprite("menu/party_bot", r):
                    ui.panel(r)
                ui.sprite("icons/person", pygame.Rect(r.centerx - 18, r.centery - 27, 36, 36))
                ui.fill(pygame.Rect(r.x + 2, r.bottom - 44, r.w - 4, 42), "bg")
                ui.text("Bot", (r.centerx, r.bottom - 42), "s", "text", "center", upper=True, bold=True)
                ui.text("click to remove", (r.centerx, r.bottom - 23), "xs", "muted", "center", upper=True)
                ui.outline(r, "text" if r.collidepoint(pygame.mouse.get_pos()) else "line")
                ui.area(r, "party_remove")
            else:
                ui.skin("menu/button_hover" if r.collidepoint(pygame.mouse.get_pos()) else "menu/tab", r)
                ui.sprite("icons/plus", pygame.Rect(r.centerx - 12, r.centery - 14, 24, 24))
                ui.text("add a bot", (r.centerx, r.centery + 24), "xs", "muted", "center", upper=True)
                ui.area(r, "party_add")
        ui.text(f"{a.team_size} vs {a.team_size}", (w // 2, 148 + card_h + 10), "s", "text", "center", upper=True, bold=True)

    def draw_custom(self, w: int, h: int) -> None:
        """Custom games: host a lobby (LAN or with a join code) or join one."""
        ui = self.ui
        host = pygame.Rect(w // 2 - 470, 160, 440, 280)
        ui.panel(host, "panel", edge="top")
        ui.text("Host", (host.x + 24, host.y + 20), "l", "text", upper=True, bold=True, kind="title")
        ui.text(f"Map {self.map_names.get(self.args.map, self.args.map)} · lobby rules are set in the lobby", (host.x + 24, host.y + 66), "xs", "muted", upper=True)
        ui.button(pygame.Rect(host.x + 24, host.y + 110, 392, 48), "Host LAN match", "host", primary=True)
        ui.button(pygame.Rect(host.x + 24, host.y + 170, 392, 48), "Host online (join code)", "host_online")
        ui.text(self.map_names.get(self.args.map, self.args.map), (host.x + 220, host.y + 236), "s", "text", "center", upper=True, bold=True)
        if len(self.maps) > 1:
            ui.button(pygame.Rect(host.x + 24, host.y + 228, 40, 36), "<", "map_prev", size="s")
            ui.button(pygame.Rect(host.right - 64, host.y + 228, 40, 36), ">", "map_next", size="s")
        join = pygame.Rect(w // 2 + 30, 160, 440, 280)
        ui.panel(join, "panel", edge="top")
        ui.text("Join", (join.x + 24, join.y + 20), "l", "text", upper=True, bold=True, kind="title")
        field = pygame.Rect(join.x + 24, join.y + 70, 272, 44)
        ui.textfield(field, self.typing)
        shown = self.address + ("_" if self.typing else "")
        ui.text(shown or "Join code or address", (field.x + 12, field.y + 14), "s", "text" if self.address else "muted")
        ui.area(field, "field:address")
        ui.button(pygame.Rect(field.right + 12, field.y, 108, 44), "Join", "join", primary=True, enabled=bool(self.address))
        ui.button(pygame.Rect(join.x + 24, join.y + 130, 220, 40), "Find LAN match", "find", size="s")
        for i, (address, port, host_name) in enumerate(self.found[:3]):
            ui.button(pygame.Rect(join.x + 24, join.y + 180 + i * 32, 392, 28), f"{host_name}  {address}", f"lan:{i}", size="xs")

    def draw_career(self, w: int, h: int) -> None:
        """Career page like the real one: totals on top, the match history as rows (click one for its scoreboard),
        patch notes of the active balance patches on the right."""
        from client import history
        from gameplay.patches import notes
        ui, s = self.ui, self.screen
        data = list(reversed(history.load()))
        if self.career_match is not None and 0 <= self.career_match < len(data):
            self.draw_match_scoreboard(data[self.career_match], w, h)
            return
        ui.text("Career", (40, 84), "xl", "text", upper=True, bold=True, kind="title")
        eliminated = history.summary(data)
        stats = (("Matches", str(eliminated["played"])), ("Wins", str(eliminated["wins"])), ("Win rate", f"{eliminated['win_rate']:.0f} %"),
                 ("K / D", f"{eliminated['kd']:.2f}"), ("Kills", str(eliminated["kills"])),
                 ("Most played", self.agents().get(eliminated["favourite"], {}).get("name", "-") if eliminated["favourite"] else "-"))
        for i, (label, value) in enumerate(stats):
            r = pygame.Rect(40 + i * 140, 150, 130, 64)
            ui.fill(r, "panel")
            ui.text(value, (r.x + 12, r.y + 8), "m", "text", bold=True)
            ui.text(label, (r.x + 12, r.y + 38), "xs", "muted", upper=True)
        ui.text("Match history", (40, 238), "s", "muted", upper=True)
        if not data:
            ui.text("No matches yet. Finished matches against bots or online appear here.", (40, 266), "s", "muted")
        y = 264
        for i, d in enumerate(data[:9]):
            r = pygame.Rect(40, y, 820, 42)
            hover = r.collidepoint(pygame.mouse.get_pos())
            won = d.get("won")
            ui.fill(r, "panel_light" if hover else "panel")
            pygame.draw.rect(s, color("ally" if won else "enemy" if won is False else "muted"), (r.x, r.y, 4, r.h))
            pic = self.bank.scaled(f"agents/{d.get('agent')}/{d.get('agent')}_killfeed.png", (30, 30))
            if pic is not None:
                s.blit(pic, (r.x + 12, r.y + 6))
            me = next((p for p in d.get("players", []) if p.get("me")), {})
            ui.text("Victory" if won else "Defeat" if won is False else "Draw", (r.x + 54, r.y + 12), "s",
                    "ally" if won else "enemy" if won is False else "muted", upper=True, bold=True)
            ui.text(f"{d['score'][0]} : {d['score'][1]}", (r.x + 190, r.y + 12), "s", "text", bold=True)
            ui.text(f"{d.get('map_name', d.get('map', ''))} · {d.get('mode', '')}", (r.x + 280, r.y + 12), "xs", "muted", upper=True)
            ui.text(f"{me.get('kills', 0)} / {me.get('deaths', 0)} · {me.get('score', 0)}", (r.x + 560, r.y + 12), "s", "text")
            ui.text(str(d.get("when", ""))[:16].replace("T", " ") + " UTC", (r.right - 12, r.y + 13), "xs", "muted", "right")
            ui.area(r, f"career:{i}")
            y += 48
        px = 900
        ui.text("Patch notes", (px, 238), "s", "muted", upper=True)
        active = notes()
        y = 266
        if not active:
            ui.text("No balance patches (config/patches).", (px, y), "xs", "muted")
        for version, text in reversed(active):
            ui.text(f"Patch {version}", (px, y), "s", "accent", upper=True, bold=True)
            y += 22
            for ln in ui.wrap(text or "(no notes)", "xs", w - px - 30):
                ui.text(ln, (px, y), "xs", "text")
                y += 18
            y += 12

    def draw_match_scoreboard(self, d: dict, w: int, h: int) -> None:
        """The stored final scoreboard of one match (Tab scoreboard of that match)."""
        ui, s = self.ui, self.screen
        won = d.get("won")
        ui.text("Victory" if won else "Defeat" if won is False else "Draw", (w // 2, 80), "xxl",
                "ally" if won else "enemy" if won is False else "muted", "center", upper=True, bold=True, kind="title")
        ui.text(f"{d['score'][0]} : {d['score'][1]} · {d.get('map_name', '')} · {d.get('mode', '')} · "
                f"{str(d.get('when', ''))[:16].replace('T', ' ')} UTC", (w // 2, 156), "s", "muted", "center", upper=True)
        x, y = w // 2 - 380, 196
        for label, cx in (("Player", 44), ("Agent", 250), ("K", 420), ("D", 480), ("Score", 540)):
            ui.text(label, (x + cx, y), "xs", "muted", upper=True)
        y += 22
        for own in (True, False):
            for p in (p for p in d.get("players", []) if p.get("own_team") == own):
                r = pygame.Rect(x, y, 760, 32)
                ui.fill(r, "panel_light" if p.get("me") else "panel")
                tint = color("ally" if own else "enemy")
                band = pygame.Surface(r.size, pygame.SRCALPHA)
                band.fill((tint.r, tint.g, tint.b, 46))
                s.blit(band, r.topleft)
                pygame.draw.rect(s, tint, (r.x, r.y, 4, r.h))
                pic = self.bank.scaled(f"agents/{p.get('agent')}/{p.get('agent')}_killfeed.png", (24, 24))
                if pic is not None:
                    s.blit(pic, (r.x + 12, r.y + 4))
                ui.text(p.get("name", ""), (r.x + 44, r.y + 8), "s", "gold" if p.get("me") else "text", bold=bool(p.get("me")))
                ui.text(self.agents().get(p.get("agent"), {}).get("name", p.get("agent", "")), (r.x + 250, r.y + 9), "xs", "muted",
                        upper=True)
                ui.text(str(p.get("kills", 0)), (r.x + 420, r.y + 8), "s", "text", bold=True)
                ui.text(str(p.get("deaths", 0)), (r.x + 480, r.y + 8), "s", "text")
                ui.text(str(p.get("score", 0)), (r.x + 540, r.y + 8), "s", "text")
                y += 36
            y += 12
        hx = w // 2 - len(d.get("history", [])) * 14
        for won_round, _ in d.get("history", []):
            pygame.draw.rect(s, color("ally" if won_round else "enemy"), (hx, h - 110, 22, 6))
            hx += 28
        ui.button(pygame.Rect(w // 2 - 120, h - 80, 240, 44), "Back", "career_back", size="s")







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
        role = info["role"]
        has_icon = role in ROLE_ORDER and ui.sprite(f"icons/role_{role.lower()}", pygame.Rect(px, 213, 24, 24))
        ui.text(role, (px + (30 if has_icon else 2), 214), "m", "accent", upper=True, bold=True)
        y = 256
        width = w - px - 40
        for slot in ("C", "Q", "E", "X"):
            ab = info["abilities"][slot]
            ui.keycap((px, y), slot, "s")
            icon = self.bank.scaled(f"ui/ability_{self.agent_view}_{slot}.png", (28, 28))
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


