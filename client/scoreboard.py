"""Scoreboard (Tab), match result, damage report after dying, round history; flat UI style."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)
from client.ui import color

COLUMNS = (("Agent", 44), ("Ult", 268), ("K", 330), ("D", 380), ("Score", 430), ("Loadout", 510), ("Credits", 620), ("Ping", 700))


class ScoreboardMixin:
    def score_of(self, p: PlayerState) -> int:
        return p.remote_score if self.mode == "client" else self.match.combat_score(p)

    def draw_damage_report(self, me: PlayerState) -> None:
        """After dying or at round end: damage dealt to and taken from each opponent this round (left side)."""
        m, ui = self.match, self.kit
        rows = m.remote_report if self.mode == "client" else m.damage_report(me.pid)
        if not rows:
            return
        x, w = 16, 300
        y = int(HUD["minimap_radius"]) * 2 + 130
        box = pygame.Rect(x, y, w, 40 + 30 * len(rows[:5]))
        ui.panel(box, "panel", edge="top")
        ui.text("This round", (x + 12, y + 10), "xs", "muted", upper=True, bold=True)
        ui.text("dealt", (x + 200, y + 10), "xs", "ally", "right", upper=True)
        ui.text("taken", (x + w - 12, y + 10), "xs", "enemy", "right", upper=True)
        y += 34
        for row in rows[:5]:
            other = m.players.get(int(row["pid"]))
            if other is None:
                continue
            head = self.bank.scaled(f"agents/{other.agent}/{other.agent}_killfeed.png", (22, 22))
            if head is not None:
                self.screen.blit(head, (x + 10, y))
            ui.text(other.name[:12], (x + 40, y + 3), "s")
            ui.text(f"{row['dealt']} ({row['dealt_hits']})", (x + 200, y + 3), "s", "ally", "right", bold=True)
            ui.text(f"{row['taken']} ({row['taken_hits']})", (x + w - 12, y + 3), "s", "enemy", "right", bold=True)
            y += 30

    def draw_round_history(self, y: float) -> None:
        """One mark per finished round: colour = who won (me or them), letter = how it ended."""
        m, ui = self.match, self.kit
        me = m.players.get(self.me)
        letters = {"Attackers eliminated": "E", "Defenders eliminated": "E", "Time ran out": "T",
                   "Bomb defused": "D", "Bomb detonated": "B"}
        x = self.w / 2 - len(m.history) * 14
        for winner, reason in m.history:
            won = me is not None and winner == me.team
            r = pygame.Rect(round(x), round(y), 24, 24)
            if won:
                pygame.draw.rect(self.screen, color("ally"), r)
            else:
                ui.outline(r, "enemy", 2)
            ui.text(letters.get(reason, "?"), (r.centerx, r.y + 4), "xs", "bg" if won else "enemy", "center", bold=True)
            x += 28

    def draw_scores(self) -> None:
        m, ui = self.match, self.kit
        me = m.players.get(self.me)
        ui.fill(self.screen.get_rect(), "#0f1923e6")
        over = m.phase == "over"
        mine = m.score[me.team] if me else m.score[0]
        theirs = m.score[1 - me.team] if me else m.score[1]
        if over:
            won = me is not None and m.match_winner == me.team
            ui.text("Victory" if won else "Defeat", (self.w / 2, 40), "xxl", "ally" if won else "enemy", "center", upper=True,
                    bold=True, kind="title")
        ui.text(str(mine), (self.w / 2 - 70, 130 if over else 40), "xl", "ally", "right", bold=True, kind="numbers")
        ui.text(":", (self.w / 2, 130 if over else 40), "xl", "muted", "center", bold=True)
        ui.text(str(theirs), (self.w / 2 + 70, 130 if over else 40), "xl", "enemy", bold=True, kind="numbers")
        top = 200 if over else 110
        if over and m.players:
            mvp = max(m.players.values(), key=self.score_of)
            ui.text(f"MVP  {mvp.name} · {m.agents.get(mvp.agent, {}).get('name', mvp.agent)} · {self.score_of(mvp)}",
                    (self.w / 2, top - 14), "s", "gold", "center", upper=True, bold=True)
            top += 16
        x, w = self.w / 2 - 380, 760
        y = top
        for label, cx in COLUMNS:
            ui.text(label, (x + cx, y), "xs", "muted", upper=True)
        y += 22
        teams = (me.team, 1 - me.team) if me is not None else (0, 1)
        for team in teams:
            own = me is not None and team == me.team
            players = sorted((p for p in m.players.values() if p.team == team), key=lambda p: -self.score_of(p))
            for p in players:
                row = pygame.Rect(x, y, w, 34)
                ui.panel(row, "panel_light" if p.pid == self.me else "panel")
                tint = color("ally" if own else "enemy")
                band = pygame.Surface(row.size, pygame.SRCALPHA)
                band.fill((tint.r, tint.g, tint.b, 46 if p.pid != self.me else 80))
                self.screen.blit(band, row.topleft)
                pygame.draw.rect(self.screen, tint, (row.x, row.y, 4, row.h))
                ab = m.agents.get(p.agent, {}).get("abilities", {}).get("X", {})
                cost = int(ab.get("cost", 7))
                for j in range(cost):
                    pygame.draw.rect(self.screen, color("ult" if j < min(p.ult_points, cost) else "line"),
                                     (x + 268 + j * 7, y + 14, 5, 5))
                if p.weapon and p.alive:
                    gun = self.bank.scaled(f"weapons/val2d/{p.weapon.key}.png", (48, 24))
                    if gun is not None:
                        self.screen.blit(gun, (x + 510, y + 5))
                    if p.armor:
                        ui.text(str(p.armor), (x + 566, y + 9), "xs", "muted")
                head = self.bank.scaled(f"agents/{p.agent}/{p.agent}_killfeed.png", (24, 24))
                if head is not None:
                    if not p.alive:
                        head = head.copy()
                        head.fill((90, 90, 90, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    self.screen.blit(head, (x + 12, y + 5))
                col = "text" if p.alive or over else "muted"
                ui.text(p.name, (x + 44, y + 8), "s", col, bold=p.pid == self.me)
                ui.text(m.agents.get(p.agent, {}).get("name", p.agent), (x + 170, y + 9), "xs", "muted", upper=True)
                ui.text(str(p.kills), (x + 330, y + 8), "s", col, bold=True)
                ui.text(str(p.deaths), (x + 380, y + 8), "s", col)
                ui.text(str(self.score_of(p)), (x + 430, y + 8), "s", col)
                if own:
                    ui.text(str(p.credits), (x + 620, y + 8), "s", "gold")
                if p.is_bot:
                    ui.text("bot", (x + 700, y + 9), "xs", "muted", upper=True)
                elif p.ping_ms is not None:
                    ui.text(f"{p.ping_ms} ms", (x + 700, y + 8), "s", "muted")
                y += 38
            y += 14
        if m.history:
            self.draw_round_history(self.h - 84)
        if over:
            ui.text("Enter: back to the menu", (self.w / 2, self.h - 40), "s", "gold", "center", upper=True, bold=True)
