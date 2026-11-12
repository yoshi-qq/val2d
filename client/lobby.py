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
        for x in range(0, self.w, 4):  # faint vertical light in the centre like the agent select backdrop
            glow = max(0, 26 - abs(x - self.w // 2) // 16)
            pygame.draw.rect(s, (15 + glow, 25 + glow, 35 + glow), (x, 0, 4, self.h))
        title = "Choose your agent" if self.mode != "local" or not self.practice else "Range"
        ui.text(title, (self.w // 2, 20), "l", "text", "center", upper=True, bold=True, kind="title")
        sub = {"host": "you host", "client": "waiting for the host"}.get(self.mode, "match vs bots")
        ui.text(f"{m.world.name} · {getattr(m, 'mode', 'standard')} · {sub}", (self.w // 2, 58), "xs", "muted", "center",
                upper=True)
        self.draw_team_list(24, 96)
        self.draw_chosen_agent()
        self.draw_agent_grid()
        self.draw_rules_panel(pygame.Rect(self.w - 324, 96, 300, 470))
        if self.mode == "host":
            net = self.session.net if self.session else None
            if net is not None:
                where = f"Join code {net.join_code}" if net.mode == "internet" else f"Address {net.join_code}"
                ui.text(where, (self.w - 174, 578), "s", "gold", "center", bold=True)
                if net.warning:
                    self.status = net.warning
        if self.status:
            ui.text(self.status, (24, self.h - 30), "s", "enemy")

    def draw_team_list(self, x: int, y: int) -> None:
        """Own team down the left: portrait, name, agent (like the agent select sidebar)."""
        ui, m, s = self.kit, self.match, self.screen
        me = m.players.get(self.me)
        team = me.team if me else 0
        ui.text("Your team", (x, y - 22), "xs", "muted", upper=True)
        for p in sorted((p for p in m.players.values() if p.team == team), key=lambda p: (p.pid != self.me, p.pid)):
            r = pygame.Rect(x, y, 230, 52)
            ui.fill(r, "panel_light" if p.pid == self.me else "panel")
            pygame.draw.rect(s, color("ally"), (r.x, r.y, 3, r.h))
            pic = self.bank.scaled(f"agents/{p.agent}/{p.agent}_portrait.png", (44, 44))
            if pic is not None:
                s.blit(pic, (r.x + 8, r.y + 4))
            ui.text(p.name, (r.x + 60, r.y + 8), "s", "gold" if p.pid == self.me else "text", bold=True)
            ui.text(m.agents.get(p.agent, {}).get("name", p.agent), (r.x + 60, r.y + 28), "xs", "muted", upper=True)
            y += 58
        enemies = [p for p in m.players.values() if p.team != team]
        if enemies and self.mode != "local":
            ui.text(f"Enemy team · {len(enemies)} players", (x, y + 8), "xs", "enemy", upper=True)

    def draw_chosen_agent(self) -> None:
        """The chosen agent large in the centre, name and role beside, abilities underneath."""
        ui, m, s = self.kit, self.match, self.screen
        mine = m.players.get(self.me)
        if mine is None:
            return
        agent = m.agents.get(mine.agent, {})
        art = self.bank.scaled(f"agents/{mine.agent}/{mine.agent}_select.png", (150, 300))
        cx = self.w // 2 - 60
        if art is not None:
            s.blit(art, (cx - 75, 90))
        ui.text(agent.get("name", mine.agent), (cx + 100, 120), "xxl", "text", upper=True, bold=True, kind="title")
        ui.text(agent.get("role", ""), (cx + 104, 190), "s", "accent", upper=True, bold=True)
        y = 230
        for slot in ("C", "Q", "E", "X"):
            ab = agent.get("abilities", {}).get(slot, {})
            icon = self.bank.scaled(f"ui/faehigkeit_{mine.agent}_{slot}.png", (28, 28))
            if icon is not None:
                s.blit(icon, (cx + 104, y))
            ui.text(slot, (cx + 140, y + 6), "xs", "muted", bold=True)
            ui.text(ab.get("name", ""), (cx + 160, y + 6), "s", "text", upper=True)
            y += 36

    def draw_agent_grid(self) -> None:
        """Agent icons in rows at the bottom centre, the chosen one framed; LOCK IN / START below."""
        ui, m, s = self.kit, self.match, self.screen
        mine = m.players.get(self.me)
        self.agent_cards = []
        keys = list(m.agents)
        cell, gap, per_row = 44, 6, 15
        rows = (len(keys) - 1) // per_row + 1
        width = min(len(keys), per_row) * (cell + gap) - gap
        x0, y0 = self.w // 2 - width // 2 - 100, self.h - 96 - rows * (cell + gap)
        mouse = pygame.mouse.get_pos()
        for i, key in enumerate(keys):
            r = pygame.Rect(x0 + (i % per_row) * (cell + gap), y0 + (i // per_row) * (cell + gap), cell, cell)
            self.agent_cards.append((r, key))
            chosen = mine is not None and mine.agent == key
            ui.fill(r, "panel_light" if r.collidepoint(mouse) or chosen else "panel")
            pic = self.bank.scaled(f"agents/{key}/{key}_portrait.png", (cell - 6, cell - 6))
            if pic is not None:
                s.blit(pic, (r.x + 3, r.y + 3))
            if chosen:
                ui.outline(r.inflate(4, 4), "text")
            ui.area(r, f"agent:{key}")
        if self.mode == "client":
            ui.text("Waiting for the host to start …", (x0 + width // 2, self.h - 62), "s", "muted", "center", upper=True)
        else:
            label = "Open range" if self.practice else "Lock in"
            ui.button(pygame.Rect(x0 + width // 2 - 150, self.h - 80, 300, 56), label, "start", primary=True, size="l")




    def draw_rules_panel(self, box: pygame.Rect) -> None:
        """Toggles and round count; cheats only matter (and are only clickable) while cheats are allowed."""
        ui, lobby = self.kit, self.match.cfg.lobby
        edit = self.can_edit_rules()
        ui.panel(box, "panel", edge="top")
        ui.text("Lobby rules", (box.x + 20, box.y + 18), "m", "text", upper=True, bold=True)
        if not edit:
            ui.text("set by the host", (box.right - 20, box.y + 20), "xs", "muted", "right", upper=True)
        y = box.y + 56
        ui.text("Rounds", (box.x + 20, y + 10), "s", "muted", upper=True)
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
            y += 34

        for name, label in RULES:
            toggle(name, label, edit)
        y += 8
        ui.line((box.x + 20, y), (box.right - 20, y))
        y += 14
        toggle("allow_cheats", "Allow cheats", edit)
        for name, label in CHEATS:
            toggle(name, label, edit and lobby.allow_cheats, indent=24)
