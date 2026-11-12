"""Lobby screen: agent select, teams and the lobby rules (set here by the host or, against bots, by the player;
everyone else sees them read-only). Start with the button or Enter."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)
from client.ui import color

RULES = (("overtime", "Overtime: win by two"), ("play_all_rounds", "Play out all rounds"),
         ("all_around_sight", "All-around sight"), ("sound_rings", "Sound rings"))
CHEATS = (("infinite_ammo", "Infinite ammo"), ("infinite_abilities", "Infinite abilities"),
          ("invincibility", "Invincibility"), ("bullet_tracers", "Bullet tracers"))


class LobbyMixin:
    def can_edit_rules(self) -> bool:
        return self.mode in ("local", "host") and self.match.phase == "lobby"

    def start_from_lobby(self) -> None:
        if self.session:
            self.session.start(self.team_size)
        elif self.mode == "local" and self.practice:
            self.match.start_practice()
            for d in self.match.players.values():
                if d.dummy:
                    d.pos, d.facing = d.home, 180.0
        elif self.mode == "local":
            self.match.start()

    def pick_agent_at(self, pos: tuple[int, int]) -> None:
        """A click in the lobby: rule toggles, rounds, start button or an agent card."""
        hit = self.kit.hit_at(pos)
        if hit is not None:
            lobby = self.match.cfg.lobby
            if hit.action.startswith("rule:") and self.can_edit_rules():
                name = hit.action[5:]
                self.match.set_rules(**{name: not getattr(lobby, name)})
                self.sound.play("ui_click", gain=0.5)
            elif hit.action.startswith("rounds:") and self.can_edit_rules():
                self.match.set_rules(win_rounds=int(hit.action[7:]))
                self.sound.play("ui_click", gain=0.5)
            elif hit.action == "start" and self.mode != "client":
                self.start_from_lobby()
            if not hit.action.startswith("agent:"):
                return
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
        s, ui, m = self.screen, self.kit, self.match
        ui.begin()
        s.fill(color("bg"))
        title = {"host": "Lobby · you host", "client": "Lobby"}.get(self.mode, "Range" if self.practice else "Match vs bots")
        ui.text(title, (40, 28), "xl", "text", upper=True, bold=True, kind="title")
        ui.text(f"{m.world.name} · {getattr(m, 'mode', 'standard')}", (42, 84), "s", "muted", upper=True)
        self.draw_agent_cards(40, 120, self.w - 470)
        self.draw_rules_panel(pygame.Rect(self.w - 400, 28, 372, self.h - 150))
        if self.mode != "local":
            self.draw_teams(40, self.h - 230)
        if self.mode == "host":
            net = self.session.net if self.session else None
            if net is not None:
                where = f"Join code {net.join_code}" if net.mode == "internet" else f"Address {net.join_code}"
                ui.text(where, (self.w - 400, self.h - 112), "m", "gold", bold=True)
                if net.warning:
                    self.status = net.warning
        if self.mode == "client":
            ui.text("Waiting for the host to start …", (self.w - 214, self.h - 76), "s", "muted", "center", upper=True)
        else:
            label = "Open range" if self.practice else "Start"
            ui.button(pygame.Rect(self.w - 400, self.h - 84, 372, 56), label, "start", primary=True, size="l")
        if self.status:
            ui.text(self.status, (40, self.h - 40), "s", "enemy")

    def draw_agent_cards(self, x0: int, y0: int, width: int) -> None:
        s, ui, m = self.screen, self.kit, self.match
        mine = m.players.get(self.me)
        self.agent_cards = []
        cell, gap = 64, 8
        per_row = max(1, width // (cell + gap))
        mouse = pygame.mouse.get_pos()
        keys = list(m.agents)
        for i, key in enumerate(keys):
            r = pygame.Rect(x0 + (i % per_row) * (cell + gap), y0 + (i // per_row) * (cell + gap), cell, cell)
            self.agent_cards.append((r, key))
            chosen = mine is not None and mine.agent == key
            ui.fill(r, "panel_light" if r.collidepoint(mouse) or chosen else "panel")
            pic = self.bank.scaled(f"agents/{key}/{key}_portrait.png", (cell - 8, cell - 8))
            if pic is not None:
                s.blit(pic, (r.x + 4, r.y + 4))
            ui.outline(r, "gold" if chosen else "text" if r.collidepoint(mouse) else "line")
            ui.area(r, f"agent:{key}")
        if mine is None:
            return
        agent = m.agents.get(mine.agent, {})
        y = y0 + ((len(keys) - 1) // per_row + 1) * (cell + gap) + 12
        ui.text(agent.get("name", mine.agent), (x0, y), "l", "text", upper=True, bold=True, kind="title")
        ui.text(agent.get("role", ""), (x0 + 4 + ui.size(agent.get("name", ""), "l", upper=True, bold=True)[0] + 12, y + 14),
                "s", "accent", upper=True, bold=True)
        x = x0
        for slot in ("C", "Q", "E", "X"):
            ab = agent.get("abilities", {}).get(slot, {})
            ui.keycap((x, y + 46), slot, "xs")
            icon = self.bank.scaled(f"ui/faehigkeit_{mine.agent}_{slot}.png", (24, 24))
            if icon is not None:
                s.blit(icon, (x + 26, y + 42))
            ui.text(ab.get("name", ""), (x + 56, y + 46), "s", "text", upper=True)
            x += 190

    def draw_teams(self, x0: int, y0: int) -> None:
        ui, m = self.kit, self.match
        for team in (0, 1):
            x = x0 + team * 360
            ui.text(f"Team {team + 1}", (x, y0), "s", "ally" if team == 0 else "enemy", upper=True, bold=True)
            row = y0 + 24
            for p in (p for p in m.players.values() if p.team == team):
                ui.text(f"{p.name} · {m.agents.get(p.agent, {}).get('name', p.agent)}", (x, row), "s",
                        "gold" if p.pid == self.me else "text")
                row += 22

    def draw_rules_panel(self, box: pygame.Rect) -> None:
        """Toggles and round count; cheats only matter (and are only clickable) while cheats are allowed."""
        ui, lobby = self.kit, self.match.cfg.lobby
        edit = self.can_edit_rules()
        ui.panel(box, "panel", edge="top")
        ui.text("Lobby rules", (box.x + 20, box.y + 18), "m", "text", upper=True, bold=True)
        if not edit:
            ui.text("set by the host", (box.right - 20, box.y + 20), "xs", "muted", "right", upper=True)
        y = box.y + 56
        ui.text("Rounds to win", (box.x + 20, y + 10), "s", "muted", upper=True)
        for i, n in enumerate((5, 9, 13)):
            ui.button(pygame.Rect(box.right - 20 - (3 - i) * 52, y, 46, 36), str(n), f"rounds:{n}",
                      selected=lobby.win_rounds == n, enabled=edit)
        y += 52

        def toggle(name: str, label: str, enabled: bool, indent: int = 0) -> None:
            nonlocal y
            on = bool(getattr(lobby, name))
            r = pygame.Rect(box.x + 20 + indent, y, 24, 24)
            ui.checkbox(r, on, f"rule:{name}") if enabled else ui.outline(r, "line")
            if on and not enabled:
                pygame.draw.rect(self.screen, color("muted"), r.inflate(-8, -8))
            ui.text(label, (r.right + 12, y + 4), "s", "text" if enabled else "muted")
            y += 36

        for name, label in RULES:
            toggle(name, label, edit)
        y += 8
        ui.line((box.x + 20, y), (box.right - 20, y))
        y += 14
        toggle("allow_cheats", "Allow cheats", edit)
        for name, label in CHEATS:
            toggle(name, label, edit and lobby.allow_cheats, indent=24)
