"""Scoreboard (Tab), match result, damage report after dying, round history; flat UI style."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)
from client.ui import color

COLUMNS = (
    ("Player", 44), ("Agent", 170), ("Ult", 268), ("K", 330), ("D", 365), ("A", 400),
    ("Score", 440), ("Loadout", 510), ("Credits", 620), ("Ping", 700),
)


class ScoreboardMixin:
    round_history_page = 0
    round_history_focus: int | None = None
    scoreboard_name_focus: str | None = None

    def scoreboard_name_event(self, ev: pygame.event.Event) -> bool:
        if self.match.phase == "lobby" or not (self.match.phase == "over" or self.ui.show_scores):
            self.scoreboard_name_focus = None
            return False
        if ev.type != pygame.KEYDOWN or ev.key not in (pygame.K_UP, pygame.K_DOWN):
            return False
        names = [hit.action for hit in self.kit.hits[self.kit.modal_from:]
                 if hit.action.startswith("scoreboard_name:")]
        if not names:
            return False
        reverse = ev.key == pygame.K_UP
        if self.scoreboard_name_focus in names:
            index = names.index(self.scoreboard_name_focus) + (-1 if reverse else 1)
        else:
            index = -1 if reverse else 0
        self.scoreboard_name_focus = names[index % len(names)]
        self.round_history_focus = None
        return True

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
        available = self.w - 32
        minimum = ui.size("?", "xs", bold=True)[0] + 4
        history = m.history
        start = 0
        self.round_history_page = 0 if len(history) * minimum <= available else self.round_history_page
        if len(history) * minimum > available:
            button_width = max(ui.size(label, "xs", upper=True)[0]
                               for label in (f"< {len(history)} [PgUp]", f"[PgDn] {len(history)} >")) + 20
            available -= 2 * (button_width + 6)
            count = max(1, available // minimum)
            self.round_history_page = min(self.round_history_page, (len(history) - 1) // count)
            end = len(history) - self.round_history_page * count
            start = max(0, end - count)
            history = history[start:end]
            ui.button(pygame.Rect(16, round(y), button_width, 24), f"< {start} [PgUp]", "history_older",
                      enabled=start > 0, size="xs")
            newer = len(m.history) - end
            ui.button(pygame.Rect(self.w - 16 - button_width, round(y), button_width, 24),
                      f"[PgDn] {newer} >", "history_newer", enabled=newer > 0, size="xs")
        pitch = min(28, available // max(1, len(history)))
        marker_width = min(24, pitch - 2)
        x = (self.w - len(history) * pitch) // 2
        ui.text("E  Elimination   T  Time ran out", (16, 8), "xs", "muted")
        ui.text("D  Defused   B  Detonated", (16, 26), "xs", "muted")
        won_label, lost_label = ("Round won", "Round lost") if me is not None else ("Team 1", "Team 2")
        right = self.w - 20
        won_right = right - ui.size(lost_label, "xs")[0] - 16
        ui.text(won_label, (won_right, 26), "xs", "ally", "right")
        ui.text(lost_label, (right, 26), "xs", "enemy", "right")
        reference_team = me.team if me is not None else 0
        ui.text("Left / Right: round details", (16, 44), "xs", "muted")
        mouse = pygame.mouse.get_pos()
        hovered = None
        focused = None
        for number, (winner, reason) in enumerate(history, start=start + 1):
            won = winner == reference_team
            r = pygame.Rect(x, round(y), marker_width, 24)
            col = "ally" if won else "enemy"
            ui.skin("scoreboard/header_team_a" if won else "scoreboard/header_team_b", r)
            ui.text(letters.get(reason, "?"), (r.centerx, r.y + 4), "xs", col, "center", bold=True)
            ui.area(r, f"history_round:{number}", enabled=False)
            is_focused = self.round_history_focus == number
            if is_focused or r.collidepoint(mouse):
                outcome = won_label if won else lost_label
                detail = r, f"Round {number} · {outcome} · {reason}"
                if is_focused:
                    focused = detail
                    ui.outline(r, "text")
                if r.collidepoint(mouse):
                    hovered = detail
            x += pitch
        if detail := focused or (hovered if self.scoreboard_name_focus is None else None):
            marker, label = detail
            width, height = ui.size(label, "xs")
            width += 16
            height += 10
            left = max(8, min(marker.centerx - width // 2, self.w - width - 8))
            top = marker.top - height - 4
            ui.panel(pygame.Rect(left, top, width, height), "bg")
            ui.text(label, (left + 8, top + 5), "xs")

    def round_history_event(self, ev: pygame.event.Event) -> bool:
        if self.match.phase == "lobby" or not (self.match.phase == "over" or self.ui.show_scores):
            self.round_history_focus = None
            return False
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE and (self.round_history_focus is not None or self.scoreboard_name_focus):
                self.round_history_focus = None
                self.scoreboard_name_focus = None
                return True
            if ev.key in (pygame.K_LEFT, pygame.K_RIGHT):
                visible = [int(hit.action.partition(":")[2]) for hit in self.kit.hits[self.kit.modal_from:]
                           if hit.action.startswith("history_round:")]
                if not visible:
                    return False
                direction = -1 if ev.key == pygame.K_LEFT else 1
                if self.round_history_focus in visible:
                    index = visible.index(self.round_history_focus) + direction
                    self.round_history_focus = visible[max(0, min(len(visible) - 1, index))]
                else:
                    self.round_history_focus = visible[-1 if direction < 0 else 0]
                self.scoreboard_name_focus = None
                return True
            action = {pygame.K_PAGEUP: "history_older", pygame.K_PAGEDOWN: "history_newer"}.get(ev.key)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            hit = self.kit.hit_at(ev.pos)
            action = hit.action if hit else None
        else:
            return False
        if action not in ("history_older", "history_newer") or not any(
                hit.enabled and hit.action == action for hit in self.kit.hits[self.kit.modal_from:]):
            return False
        self.round_history_page += 1 if action == "history_older" else -1
        self.round_history_page = max(0, self.round_history_page)
        self.round_history_focus = None
        return True

    def draw_scores(self) -> None:
        m, ui = self.match, self.kit
        me = m.players.get(self.me)
        ui.fill(self.screen.get_rect(), "#0f1923e6")
        over = m.phase == "over"
        compact = self.h < 600
        mine = m.score[me.team] if me else m.score[0]
        theirs = m.score[1 - me.team] if me else m.score[1]
        if over:
            won = me is not None and m.match_winner == me.team
            title = "Draw" if m.match_winner is None else "Victory" if won else "Defeat"
            ink = "muted" if m.match_winner is None else "ally" if won else "enemy"
            ui.text(title, (self.w / 2, 4 if compact else 40), "l" if compact else "xxl", ink, "center", upper=True,
                    bold=True, kind="title")
        score_y = (38 if over else 12) if compact else (130 if over else 40)
        score_size = "m" if compact else "xl"
        ui.text(str(mine), (self.w / 2 - 70, score_y), score_size, "ally", "right", bold=True, kind="numbers")
        ui.text(":", (self.w / 2, score_y), score_size, "muted", "center", bold=True)
        ui.text(str(theirs), (self.w / 2 + 70, score_y), score_size, "enemy", bold=True, kind="numbers")
        top = (72 if over else 58) if compact else (200 if over else 110)
        if over and m.players:
            mvp = max(m.players.values(), key=self.score_of)
            name = mvp.name
            suffix = f" · {m.agents.get(mvp.agent, {}).get('name', mvp.agent)} · {self.score_of(mvp)}"
            label = f"MVP  {name}{suffix}"
            if ui.size(label, "s", upper=True, bold=True)[0] > self.w - 32:
                while name and ui.size(f"MVP  {name}…{suffix}", "s", upper=True, bold=True)[0] > self.w - 32:
                    name = name[:-1]
                label = f"MVP  {name.rstrip()}…{suffix}"
            ui.text(label, (self.w / 2, top - 14), "s", "gold", "center", upper=True, bold=True)
            top += 16
        x, w = self.w / 2 - 380, 760
        y = top
        header_height, row_height = (18, 22) if compact else (24, 32)
        text_offset = 3 if compact else 8
        portrait = 18 if compact else 24
        mouse = pygame.mouse.get_pos()
        hovered_name = ""
        focused_name = ""
        focused_cell = None
        has_shortened_names = False
        teams = (me.team, 1 - me.team) if me is not None else (0, 1)
        for team in teams:
            own = me is not None and team == me.team
            ui.skin("scoreboard/header_team_a" if own else "scoreboard/header_team_b", pygame.Rect(x, y, w, header_height))
            ui.sprite("icons/side_attack" if m.side(team) == "attack" else "icons/side_defense",
                      pygame.Rect(x + 12, y + 2, header_height - 4, header_height - 4))
            for label, cx in COLUMNS:
                ui.text(label, (x + cx, y + (1 if compact else 4)), "xs", "text", upper=True)
            y += header_height + 2
            players = sorted((p for p in m.players.values() if p.team == team), key=lambda p: -self.score_of(p))
            for p in players:
                row = pygame.Rect(x, y, w, row_height)
                text_y = y + text_offset
                ui.skin("scoreboard/row_self" if p.pid == self.me else "scoreboard/row", row)
                cost = m.ultimate_cost(p)
                if m.mode == "deathmatch" or cost > 9:
                    ui.text(f"{min(p.ult_points, cost)}/{cost}", (x + 268, text_y + 1), "xs",
                            "ult" if p.ult_points >= cost else "muted")
                else:
                    for j in range(cost):
                        pygame.draw.rect(self.screen, color("ult" if j < min(p.ult_points, cost) else "line"),
                                         (x + 268 + j * 6, row.centery - 2, 4, 5))
                if p.weapon and p.alive:
                    gun = ui.silhouette(f"weapons/val2d/{self.weapon_art(p.weapon.key)}.png", (46, 16))
                    if gun is not None:
                        self.screen.blit(gun, (x + 510, row.centery - gun.get_height() // 2))
                    if p.armor:
                        ui.text(str(p.armor), (x + 566, text_y + 1), "xs", "muted")
                head = self.bank.scaled(f"agents/{p.agent}/{p.agent}_killfeed.png", (portrait, portrait))
                if head is not None:
                    if not p.alive:
                        head = head.copy()
                        head.fill((90, 90, 90, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    self.screen.blit(head, (x + 12, row.centery - portrait // 2))
                col = "text" if p.alive or over else "muted"
                bold_name = p.pid == self.me
                name = p.name
                if ui.size(name, "s", bold=bold_name)[0] > 118:
                    cell = pygame.Rect(x + 44, y, 126, row_height)
                    action = f"scoreboard_name:{p.pid}"
                    ui.area(cell, action, enabled=False)
                    has_shortened_names = True
                    if cell.collidepoint(mouse):
                        hovered_name = name
                    if self.scoreboard_name_focus == action:
                        focused_name, focused_cell = name, cell
                    while name and ui.size(name + "…", "s", bold=bold_name)[0] > 118:
                        name = name[:-1]
                    name = name.rstrip() + "…"
                ui.text(name, (x + 44, text_y), "s", col, bold=bold_name)
                ui.text(m.agents.get(p.agent, {}).get("name", p.agent), (x + 170, text_y + 1), "xs", "muted", upper=True)
                ui.text(str(p.kills), (x + 330, text_y), "s", col, bold=True)
                ui.text(str(p.deaths), (x + 365, text_y), "s", col)
                ui.text(str(p.assists), (x + 400, text_y), "s", col)
                ui.text(str(self.score_of(p)), (x + 440, text_y), "s", col)
                if own:
                    ui.text(str(p.credits), (x + 620, text_y), "s", "gold")
                if p.is_bot:
                    ui.text("bot", (x + 700, text_y + 1), "xs", "muted", upper=True)
                elif p.ping_ms is not None:
                    ui.text(f"{p.ping_ms} ms", (x + 700, text_y), "s", "muted")
                y += row_height + (0 if compact else 2)
            y += 4 if compact else 8
        if m.history:
            self.draw_round_history(self.h - (92 if over else 84))
        else:
            self.round_history_page = 0
            self.round_history_focus = None
        if over:
            cx, y = self.w // 2, self.h - 64
            if self.session:
                ui.button(pygame.Rect(cx - 275, y, 270, 48), "Return to party [Enter]", "party", primary=True, size="s")
                ui.button(pygame.Rect(cx + 5, y, 270, 48), "Close party [Shift+Enter]", "to_menu", size="s")
            elif self.client:
                closed = getattr(self.client, "party_closed", False)
                if closed:
                    message = "The host closed the party"
                    label = "Back to menu [Enter]"
                elif self.client.connected:
                    message = "The host can reopen the party lobby"
                    label = "Leave party [Enter]"
                else:
                    message = "Disconnected from the host"
                    label = "Leave party [Shift+Enter]"
                ui.text(message, (cx - 155, y + 15), "s", "text", "center")
                ui.button(pygame.Rect(cx + 5, y, 250, 48), label, "to_menu", size="s")
            else:
                ui.button(pygame.Rect(cx - 150, y, 300, 48), "Back to menu [Enter]", "to_menu", primary=True, size="s")
        if has_shortened_names:
            ui.text("Up / Down: full names", (x + w, 8), "xs", "muted", "right")
        if focused_cell is not None:
            ui.outline(focused_cell, "text")
        else:
            self.scoreboard_name_focus = None
        if full_name := focused_name or (hovered_name if self.round_history_focus is None else ""):
            anchor = focused_cell.midtop if focused_name else mouse
            lines = ui.wrap(full_name, "s", self.w - 48, break_words=True)
            line_height = ui.size("Ag", "s")[1] + 2
            width = max(ui.size(line, "s")[0] for line in lines) + 16
            height = len(lines) * line_height + 12
            left = max(8, min(anchor[0], self.w - width - 8))
            top = anchor[1] - height - 8
            if top < 8:
                top = anchor[1] + 16
            ui.panel(pygame.Rect(left, top, width, height), "bg")
            for i, line in enumerate(lines):
                ui.text(line, (left + 8, top + 6 + i * line_height), "s")
