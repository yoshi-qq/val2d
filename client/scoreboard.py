"""Scoreboard, damage report, round history."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)


class ScoreboardMixin:
    def score_of(self, p: PlayerState) -> int:
        return p.remote_score if self.mode == "client" else self.match.combat_score(p)

    def draw_damage_report(self, me: PlayerState) -> None:
        """After dying or at round end: damage dealt to and taken from each opponent this round."""
        m = self.match
        rows = m.remote_report if self.mode == "client" else m.damage_report(me.pid)
        if not rows:
            return
        x, y, w = 24, self.h / 2 - 40, 330
        self.panel("ui/hud/ability_panel.png", pygame.Rect(x - 10, y - 34, w + 20, 40 + 30 * len(rows[:5])))
        self.text("This round: dealt / taken", (x, y - 26), C_MUTED)
        for row in rows[:5]:
            other = m.players.get(int(row["pid"]))
            if other is None:
                continue
            head = self.bank.scaled(f"agents/{other.agent}/{other.agent}_killfeed.png", (24, 24))
            if head is not None:
                self.screen.blit(head, (x, y))
            self.text(other.name[:12], (x + 30, y + 3), C_TEXT)
            self.text(f"{row['dealt']} ({row['dealt_hits']})", (x + 170, y + 3), C_ALLY)
            self.text(f"{row['taken']} ({row['taken_hits']})", (x + 250, y + 3), C_ENEMY)
            y += 30

    def draw_round_history(self, y: float) -> None:
        """One mark per finished round: colour = winning side for me, letter = how it ended."""
        m = self.match
        me = m.players.get(self.me)
        letters = {"Attackers eliminated": "E", "Defenders eliminated": "E", "Time ran out": "T",
                   "Bomb defused": "D", "Bomb detonated": "B"}
        x = self.w / 2 - len(m.history) * 13
        for winner, reason in m.history:
            won = me is not None and winner == me.team
            pygame.draw.rect(self.screen, C_ALLY if won else C_ENEMY, (x, y, 22, 22), 0 if won else 2)
            self.text(letters.get(reason, "?"), (x + 6, y + 2), C_BG if won else C_ENEMY)
            x += 26

    def draw_scores(self) -> None:
        m = self.match
        me = m.players.get(self.me)
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((10, 10, 16, 200))
        self.screen.blit(overlay, (0, 0))
        title = "Match over" if m.phase == "over" else "Scoreboard"
        if m.history:
            self.draw_round_history(self.h - 74)
        if m.phase == "over" and m.players:
            mvp = max(m.players.values(), key=self.score_of)
            self.text(f"MVP: {mvp.name} ({m.agents.get(mvp.agent, {}).get('name', mvp.agent)}) – {self.score_of(mvp)} points",
                      (self.w / 2, 122), C_SITE, center=True)
        if m.phase == "over":
            self.text("Enter or Esc: back to the menu", (self.w / 2, self.h - 40), C_SITE, center=True)
        if m.phase == "over" and me is not None:
            title += ": won" if m.match_winner == me.team else ": lost"
        self.text(f"{title}   {m.score[0]} : {m.score[1]}", (self.w / 2, 92), C_TEXT, big=True, center=True)
        x, w, y = self.w / 2 - 320, 640, 150
        for team in (0, 1):
            own = me is not None and team == me.team
            header = pygame.Rect(x, y, w, 32)
            if not draw_nine_slice(self.screen, self.bank, f"ui/scoreboard/header_team_{'a' if own else 'b'}.png", header, 8, 1):
                pygame.draw.rect(self.screen, C_ALLY if own else C_ENEMY, header, 1)
            self.text(f"Team {team + 1}" + ("  (you)" if own else ""), (x + 16, y + 6))
            skull = self.bank.scaled("ui/icons/skull.png", (16, 16))
            trophy = self.bank.scaled("ui/icons/trophy.png", (16, 16))
            coin = self.bank.scaled("ui/hud/credits.png", (16, 16))
            for icon, col_x in ((trophy, x + 380), (skull, x + 450), (coin, x + 540)):
                if icon is not None:
                    self.screen.blit(icon, (col_x, y + 8))
            y += 38
            for p in sorted((p for p in m.players.values() if p.team == team), key=lambda p: -p.kills):
                row = pygame.Rect(x, y, w, 36)
                rel = "ui/scoreboard/row_self.png" if p.pid == self.me else "ui/scoreboard/row.png"
                if not draw_nine_slice(self.screen, self.bank, rel, row, 8, 1):
                    pygame.draw.rect(self.screen, C_MUTED, row, 1)
                head = self.bank.scaled(f"agents/{p.agent}/{p.agent}_killfeed.png", (24, 24))
                if head is not None:
                    self.screen.blit(head, (x + 10, y + 6))
                col = C_TEXT if p.alive else C_MUTED
                self.text(p.name, (x + 44, y + 9), col)
                self.text(m.agents.get(p.agent, {}).get("name", p.agent), (x + 220, y + 9), C_MUTED)
                self.text(str(p.kills), (x + 384, y + 9), col)
                self.text(str(p.deaths), (x + 454, y + 9), col)
                self.text(str(self.score_of(p)), (x + 490, y + 9), C_MUTED)
                credits = "" if (me is not None and p.team != me.team) else str(p.credits)
                self.text(credits, (x + 544, y + 9), C_SITE)
                if p.is_bot:
                    self.text("BOT", (x + 596, y + 9), C_MUTED)
                elif p.ping_ms is not None:
                    bars = 3 if p.ping_ms < 50 else 2 if p.ping_ms < 100 else 1 if p.ping_ms < 200 else 0
                    icon = self.bank.scaled(f"ui/icons/ping_{bars}.png", (16, 16))
                    if icon is not None:
                        self.screen.blit(icon, (x + 596, y + 10))
                    self.text(f"{p.ping_ms}", (x + 600 + (18 if icon else 0), y + 9), C_MUTED)
                y += 40
            y += 18
