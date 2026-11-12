"""Lobby screen and agent select."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)


class LobbyMixin:
    def pick_agent_at(self, pos: tuple[int, int]) -> None:
        for rect, key in self.agent_cards:
            if rect.collidepoint(pos):
                if self.client:
                    self.client.choose_agent(key)
                elif self.session:
                    self.session.net.choose_agent(self.me, key)
                elif self.me in self.match.players:
                    self.match.players[self.me].agent = key
                return

    def draw_lobby(self) -> None:
        s = self.screen
        s.fill(C_BG)
        title = {"host": "Lobby – you are the host", "client": "Lobby – joined"}.get(self.mode, "Choose your agent")
        self.text(title, (self.w / 2, 30), C_TEXT, big=True, center=True)
        self.text(f"Map {self.match.world.name}", (self.w / 2, 72), C_MUTED, center=True)
        mine = self.match.players.get(self.me)
        self.agent_cards = []
        keys = list(self.match.agents)
        compact = len(keys) > 12  # many agents: smaller cards, role as icon
        card_w, card_h, gap = (72, 124, 8) if compact else (104, 196, 12)
        per_row = max(1, min(len(keys), (self.w - 80) // (card_w + gap)))
        left = (self.w - per_row * (card_w + gap) + gap) / 2
        mouse = pygame.mouse.get_pos()
        for i, key in enumerate(keys):
            rect = pygame.Rect(left + (i % per_row) * (card_w + gap), 104 + (i // per_row) * (card_h + gap), card_w, card_h)
            self.agent_cards.append((rect, key))
            chosen = mine is not None and mine.agent == key
            frame = "ui/hud/rahmen_aktiv.png" if chosen else "ui/hud/rahmen.png"
            if not draw_nine_slice(s, self.bank, frame, rect, 8, 1):
                pygame.draw.rect(s, C_SITE if chosen else C_MUTED, rect, 1)
            if rect.collidepoint(mouse) and not chosen:
                pygame.draw.rect(s, C_TEXT, rect, 1)
            size = (32, 64) if compact else (64, 128)
            pic = self.bank.scaled(f"agents/{key}/{key}_select.png", size) or                 self.bank.scaled(f"agents/{key}/{key}_portrait.png", (size[0], size[0]))
            if pic is not None:
                s.blit(pic, (rect.centerx - pic.get_width() / 2, rect.y + 8))
            agent = self.match.agents[key]
            role = str(agent.get("role", ""))
            if compact:
                self.text(agent["name"], (rect.centerx, rect.bottom - 46), C_SITE if chosen else C_TEXT, center=True)
                icon = self.bank.scaled(f"ui/icons/role_{role.lower()}.png", (16, 16))
                if icon is not None:
                    s.blit(icon, (rect.centerx - 8, rect.bottom - 24))
            else:
                self.text(agent["name"], (rect.centerx, rect.bottom - 48), C_SITE if chosen else C_TEXT, center=True)
                self.text(role, (rect.centerx, rect.bottom - 26), C_MUTED, center=True)
        y = 104 + ((len(keys) - 1) // per_row + 1) * (card_h + gap) + 6
        if mine is not None:
            abil = self.match.agents.get(mine.agent, {}).get("abilities", {})
            x = self.w / 2 - 2 * 230
            for k in ("C", "Q", "E", "X"):
                ab = abil.get(k, {})
                icon = self.bank.scaled(f"ui/faehigkeit_{mine.agent}_{k}.png", (32, 32))
                if icon is not None:
                    s.blit(icon, (x, y))
                self.text(f"{k} {ab.get('name', '')}", (x + 40, y + 2), C_TEXT)
                self.text(str(ab.get("kind", "")), (x + 40, y + 22), C_MUTED)
                x += 230
            y += 64
        if self.mode != "local":
            for team in (0, 1):
                row = y
                self.text(f"Team {team + 1}", (self.w / 2 - 300 + team * 340, row), C_ALLY if team == 0 else C_ENEMY)
                for p in (p for p in self.match.players.values() if p.team == team):
                    row += 24
                    self.text(f"{p.name}  ({self.match.agents.get(p.agent, {}).get('name', p.agent)})", (self.w / 2 - 300 + team * 340, row))
        if self.mode == "host":
            net = self.session.net if self.session else None
            where = ""
            if net is not None:
                where = f"join code {net.join_code}" if net.mode == "internet" else f"address {net.join_code}"
                if net.warning:
                    self.status = net.warning
            hint = f"Click an agent · Enter starts · bots fill up to {self.team_size} per team · {where}"
        elif self.mode == "local" and self.practice:
            hint = "Click an agent · Enter opens the practice range"
        elif self.mode == "local":
            hint = f"Click an agent · Enter starts ({self.team_size} vs {self.team_size} with bots)"
        else:
            hint = "Click an agent · waiting for the host to start …"
        self.text(hint, (self.w / 2, self.h - 90), C_SITE, center=True)
        if self.status:
            self.text(self.status, (self.w / 2, self.h - 60), C_ENEMY, center=True)
