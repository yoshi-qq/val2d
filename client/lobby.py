"""Lobby screen: agent select, teams and the lobby rules (set here by the host or, against bots, by the player;
everyone else sees them read-only). Start with the button or Enter."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)
from client.agent_details import AGENT_PASSIVES, AGENT_ROLES, draw_role_picker
from client.map_picker import MapPicker, map_name
from client.ui import color
from gameplay.kit.describe import describe
from gameplay.world import PLAYABLE_MAP_KEYS

RULES = (("overtime", "Overtime: win by two"), ("play_all_rounds", "Play out all rounds"),
         ("all_around_sight", "All-around sight"), ("sound_rings", "Sound rings"))
CHEATS = (("infinite_ammo", "Infinite ammo"), ("infinite_magazines", "Infinite magazines"),
          ("infinite_abilities", "Infinite abilities"),
          ("invincibility", "Invincibility"), ("bullet_tracers", "Bullet tracers"))
PARTY_MODES = {"standard": "Standard", "quick": "Swiftplay", "deathmatch": "Team Deathmatch"}


class LobbyMixin:
    party_map_picker: MapPicker | None = None
    rule_focus: str | None = None
    agent_abilities_open = False
    ability_detail = 0
    ability_preview_agent: str | None = None

    def preview_agent_key(self) -> str | None:
        mine = self.match.players.get(self.me)
        if self.ability_preview_agent in self.match.agents:
            return self.ability_preview_agent
        return mine.agent if mine else None

    def open_lobby_abilities(self, agent_key: str | None = None) -> None:
        candidate = agent_key or self.agent_focus
        self.ability_preview_agent = candidate if candidate in self.match.agents else None
        self.agent_abilities_open = True
        self.ability_detail = 0

    def browse_lobby_abilities(self, step: int) -> None:
        mine = self.match.players.get(self.me)
        keys = tuple(self.match.agents)
        if mine is None or not keys:
            return
        current = self.ability_preview_agent if self.ability_preview_agent in keys else mine.agent
        index = keys.index(current) if current in keys else 0
        self.ability_preview_agent = keys[(index + step) % len(keys)]
        if self.ability_detail == 4 and self.ability_preview_agent not in AGENT_PASSIVES:
            self.ability_detail = 3

    def choose_preview_agent(self) -> None:
        mine = self.match.players.get(self.me)
        key = self.ability_preview_agent
        if (mine is None or key is None or key not in self.match.agents or key == mine.agent
                or self.match.phase != "lobby" or (self.client and not self.client.connected)):
            return
        self.choose_lobby_agent(key)
        self.agent_abilities_open = False

    def preview_agent_at(self, pos: tuple[int, int]) -> None:
        if (self.match.phase != "lobby" or self.agent_abilities_open or self.party_map_picker is not None
                or self.me not in self.match.players):
            return
        hit = self.kit.hit_at(pos)
        if hit and hit.action.startswith("agent:"):
            agent_key = hit.action.removeprefix("agent:")
            if agent_key in self.match.agents:
                self.rule_focus = None
                self.open_lobby_abilities(agent_key)

    def lobby_abilities_key(self, key: int) -> bool:
        if self.match.phase != "lobby":
            self.agent_abilities_open = False
            return False
        if key == pygame.K_F1 and self.me in self.match.players:
            if self.agent_abilities_open:
                self.agent_abilities_open = False
            else:
                self.open_lobby_abilities()
            return True
        if not self.agent_abilities_open:
            return False
        if key == pygame.K_ESCAPE:
            self.agent_abilities_open = False
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.choose_preview_agent()
        elif key in (pygame.K_UP, pygame.K_DOWN):
            count = 5 if self.preview_agent_key() in AGENT_PASSIVES else 4
            self.ability_detail = (self.ability_detail + (-1 if key == pygame.K_UP else 1)) % count
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.browse_lobby_abilities(-1 if key == pygame.K_LEFT else 1)
        return True
    agent_focus: str | None = None
    agent_page = 0
    lobby_agent_query = ""
    lobby_agent_searching = False
    lobby_agent_role = 0
    lobby_role_picker_open = False

    def lobby_role_action(self, action: str) -> None:
        if action == "role_back":
            self.lobby_role_picker_open = False
        elif action.startswith("role_pick:"):
            self.lobby_agent_role = int(action.removeprefix("role_pick:"))
            self.set_lobby_agent_query(self.lobby_agent_query)
            self.lobby_role_picker_open = False

    def lobby_agent_keys(self) -> list[str]:
        query = self.lobby_agent_query.strip().casefold()
        role = AGENT_ROLES[self.lobby_agent_role]
        return [key for key, agent in self.match.agents.items()
                if query in agent.get("name", key).casefold()
                and (self.lobby_agent_role == 0 or agent.get("role") == role)]

    def cycle_lobby_agent_role(self, step: int) -> None:
        self.lobby_agent_role = (self.lobby_agent_role + step) % len(AGENT_ROLES)
        self.set_lobby_agent_query(self.lobby_agent_query)

    def set_lobby_agent_query(self, query: str) -> None:
        self.lobby_agent_query = query
        self.agent_page = 0
        self.agent_focus = None

    def lobby_agent_search_key(self, ev: pygame.event.Event) -> bool:
        if self.match.phase != "lobby":
            self.lobby_agent_searching = False
            self.lobby_agent_query = ""
            self.lobby_agent_role = 0
            self.lobby_role_picker_open = False
            return False
        if self.lobby_role_picker_open:
            if ev.key == pygame.K_ESCAPE:
                self.lobby_role_action("role_back")
            elif pygame.K_1 <= ev.key <= pygame.K_5:
                self.lobby_role_action(f"role_pick:{ev.key - pygame.K_1}")
            return True
        if (ev.key == pygame.K_DELETE and getattr(ev, "mod", 0) & pygame.KMOD_CTRL
                and (self.lobby_agent_query or self.lobby_agent_role)):
            self.reset_lobby_agent_filters()
            return True
        if not self.lobby_agent_searching:
            modifiers = getattr(ev, "mod", 0)
            if ev.key == pygame.K_r and modifiers & pygame.KMOD_CTRL:
                self.lobby_role_picker_open = True
                return True
            if ev.key == pygame.K_r and not modifiers & (pygame.KMOD_CTRL | pygame.KMOD_ALT | pygame.KMOD_GUI):
                self.cycle_lobby_agent_role(-1 if modifiers & pygame.KMOD_SHIFT else 1)
                return True
            if ev.key != pygame.K_SLASH:
                return False
            self.lobby_agent_searching = True
            return True
        if ev.key == pygame.K_ESCAPE:
            self.set_lobby_agent_query("")
            self.lobby_agent_searching = False
        elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
            self.lobby_agent_searching = False
            if keys := self.lobby_agent_keys():
                self.focus_agent(keys[0])
        elif ev.key == pygame.K_BACKSPACE:
            self.set_lobby_agent_query(self.lobby_agent_query[:-1])
        elif (value := getattr(ev, "unicode", "")) and value.isprintable():
            self.set_lobby_agent_query((self.lobby_agent_query + value)[:24])
        return True

    def agent_grid_shape(self) -> tuple[int, int]:
        if self.w < 1000:
            return max(1, (self.w - 344) // 48), 2
        if self.mode == "local":
            return 4, max(2, (self.h - 208) // 60)
        return max(1, (self.agent_area().w + 8) // 60), 2

    def reset_lobby_agent_filters(self) -> None:
        self.lobby_agent_role = 0
        self.lobby_agent_searching = False
        self.set_lobby_agent_query("")
        own = self.match.players.get(self.me)
        if own and own.agent in self.match.agents:
            self.focus_agent(own.agent)

    def focus_agent(self, key: str) -> None:
        columns, rows = self.agent_grid_shape()
        self.agent_focus = key
        keys = self.lobby_agent_keys()
        self.agent_page = keys.index(key) // (columns * rows) if key in keys else 0

    def choose_lobby_agent(self, key: str) -> None:
        if self.match.phase != "lobby" or key not in self.match.agents:
            return
        self.focus_agent(key)
        if self.client:
            self.client.choose_agent(key)
        elif self.session:
            self.session.net.choose_agent(self.me, key)
        elif self.me in self.match.players:
            self.match.players[self.me].agent = key

    def lobby_agent_key(self, key: int) -> bool:
        if self.match.phase != "lobby":
            return False
        keys = self.lobby_agent_keys()
        if not keys:
            return False
        if key == pygame.K_ESCAPE and self.agent_focus is not None:
            self.agent_focus = None
            return True
        if key == pygame.K_SPACE and self.agent_focus in keys:
            self.choose_lobby_agent(self.agent_focus)
            return True
        columns, rows = self.agent_grid_shape()
        steps = {pygame.K_LEFT: -1, pygame.K_RIGHT: 1, pygame.K_UP: -columns, pygame.K_DOWN: columns,
                 pygame.K_PAGEUP: -columns * rows, pygame.K_PAGEDOWN: columns * rows, pygame.K_TAB: 0}
        if key not in steps and key not in (pygame.K_HOME, pygame.K_END):
            return False
        mine = self.match.players.get(self.me)
        current = self.agent_focus if self.agent_focus in keys else mine.agent if mine and mine.agent in keys else keys[0]
        index = 0 if key == pygame.K_HOME else len(keys) - 1 if key == pygame.K_END else keys.index(current) + steps[key]
        self.focus_agent(keys[max(0, min(len(keys) - 1, index))])
        return True

    def party_map_action(self, action: str) -> None:
        if not self.session or self.match.phase != "lobby":
            return
        if action == "choose_map":
            names = {key: map_name(key) for key in PLAYABLE_MAP_KEYS}
            self.party_map_picker = MapPicker(names, self.match.world.key)
        elif action == "map_back":
            self.party_map_picker = None
        elif self.party_map_picker is not None and action.startswith("map_pick:"):
            key = action.removeprefix("map_pick:")
            if key in PLAYABLE_MAP_KEYS and self.session.configure_lobby(map_key=key):
                self.refresh_map_art()
            self.party_map_picker = None

    def party_map_key(self, key: int) -> bool:
        if not self.session or self.match.phase != "lobby":
            return False
        if self.party_map_picker is not None:
            if action := self.party_map_picker.key_action(key, self.w):
                self.party_map_action(action)
            return True
        if key == pygame.K_m:
            self.party_map_action("choose_map")
            return True
        return False

    def choose_party_team(self, team: int) -> None:
        own = self.match.players.get(self.me)
        if (self.match.phase != "lobby" or own is None or own.team == team
                or sum(p.team == team for p in self.match.players.values()) >= 5):
            return
        if self.client and self.client.connected:
            self.client.choose_team(team)
        elif self.session:
            self.session.net.choose_team(self.me, team)

    def party_team_key(self, key: int) -> bool:
        if key != pygame.K_t or self.match.phase != "lobby" or not (self.client or self.session):
            return False
        if own := self.match.players.get(self.me):
            self.choose_party_team(1 - own.team)
        return True

    def copy_party_address(self) -> None:
        if not self.session or self.match.phase != "lobby":
            return
        try:
            pygame.scrap.put_text(self.session.net.join_code)
            self.status = "Invite copied"
        except pygame.error:
            self.status = "Copy unavailable. Share the address shown above."

    def party_copy_key(self, key: int, modifiers: int) -> bool:
        if key != pygame.K_c or not modifiers & pygame.KMOD_CTRL or not self.session or self.match.phase != "lobby":
            return False
        self.copy_party_address()
        return True

    def can_edit_rules(self) -> bool:
        return self.mode in ("local", "host") and self.match.phase == "lobby"

    def lobby_rule_key(self, key: int, modifiers: int) -> bool:
        if not self.can_edit_rules():
            self.rule_focus = None
            return False
        controls = [hit.action for hit in self.kit.hits[self.kit.modal_from:]
                    if hit.enabled and hit.action.startswith(("rule:", "rounds:"))]
        if key == pygame.K_F7:
            self.rule_focus = None if self.rule_focus or not controls else controls[0]
            return True
        if self.rule_focus is None:
            return False
        if key == pygame.K_ESCAPE or not controls:
            self.rule_focus = None
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and self.rule_focus in controls:
            hit = next(hit for hit in self.kit.hits if hit.action == self.rule_focus and hit.enabled)
            self.pick_agent_at(hit.rect.center, keyboard=True)
        elif key in (pygame.K_TAB, pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
            reverse = key in (pygame.K_UP, pygame.K_LEFT) or (key == pygame.K_TAB and modifiers & pygame.KMOD_SHIFT)
            if self.rule_focus in controls:
                index = controls.index(self.rule_focus) + (-1 if reverse else 1)
            else:
                index = -1 if reverse else 0
            self.rule_focus = controls[index % len(controls)]
        return True

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

    def change_party_setting(self, field: str, step: int) -> None:
        if not self.session or self.match.phase != "lobby":
            return
        if field == "map":
            keys = PLAYABLE_MAP_KEYS
            index = keys.index(self.match.world.key)
            if self.session.configure_lobby(map_key=keys[(index + step) % len(keys)]):
                self.refresh_map_art()
        elif field == "mode":
            keys = tuple(PARTY_MODES)
            index = keys.index(self.match.mode)
            self.session.configure_lobby(mode=keys[(index + step) % len(keys)])

    def party_mode_key(self, key: int, modifiers: int) -> bool:
        if (key != pygame.K_v or modifiers & (pygame.KMOD_CTRL | pygame.KMOD_ALT | pygame.KMOD_GUI)
                or not self.session or self.match.phase != "lobby"):
            return False
        self.change_party_setting("mode", -1 if modifiers & pygame.KMOD_SHIFT else 1)
        return True

    def pick_agent_at(self, pos: tuple[int, int], *, keyboard: bool = False) -> None:
        """A click in the lobby: rule toggles, rounds, start button or an agent card."""
        if not keyboard:
            self.rule_focus = None
            self.lobby_agent_searching = False
        hit = self.kit.hit_at(pos)
        if self.lobby_role_picker_open:
            if hit:
                self.lobby_role_action(hit.action)
            return
        if self.agent_abilities_open:
            if hit and hit.action == "agent_abilities_close":
                self.agent_abilities_open = False
            elif hit and hit.action == "agent_abilities_choose":
                self.choose_preview_agent()
            elif hit and hit.action.startswith("ability_detail:"):
                self.ability_detail = int(hit.action.rsplit(":", 1)[1])
            elif hit and hit.action.startswith("ability_agent:"):
                self.browse_lobby_abilities(int(hit.action.rsplit(":", 1)[1]))
            return
        if self.party_map_picker is not None:
            if hit is not None:
                self.party_map_action(hit.action)
            return
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
            elif hit.action == "agent_abilities_open":
                self.open_lobby_abilities()
            elif hit.action == "choose_map":
                self.party_map_action(hit.action)
            elif hit.action == "lobby_agent_search":
                self.lobby_agent_searching = True
            elif hit.action == "lobby_agent_search_clear":
                self.set_lobby_agent_query("")
            elif hit.action == "lobby_agent_filters_reset":
                self.reset_lobby_agent_filters()
            elif hit.action == "lobby_agent_role":
                self.lobby_role_picker_open = True
            elif hit.action.startswith("agent_page:"):
                columns, rows = self.agent_grid_shape()
                page = self.agent_page + int(hit.action.removeprefix("agent_page:"))
                keys = self.lobby_agent_keys()
                index = page * columns * rows
                if 0 <= index < len(keys):
                    self.focus_agent(keys[index])
            elif hit.action.startswith("setting:"):
                _, field, step = hit.action.split(":")
                self.change_party_setting(field, int(step))
            elif hit.action.startswith("team:"):
                self.choose_party_team(int(hit.action[5:]))
            elif hit.action == "copy_address":
                self.copy_party_address()
            if not hit.action.startswith("agent:"):
                return
        for rect, key in self.agent_cards:
            if rect.collidepoint(pos) and key in self.match.agents and self.match.phase == "lobby":
                self.choose_lobby_agent(key)
                return

    def draw_lobby(self) -> None:
        s, ui, m = self.screen, self.kit, self.match
        ui.begin()
        s.fill(color("bg"))
        for x in range(0, self.w, 4):  # faint vertical light in the centre like the agent select backdrop
            glow = max(0, 26 - abs(x - self.w // 2) // 16)
            pygame.draw.rect(s, (15 + glow, 25 + glow, 35 + glow), (x, 0, 4, self.h))
        title = "Party lobby" if self.mode != "local" else "Range" if self.practice else "Choose your agent"
        ui.text(title, (self.w // 2, 20), "l", "text", "center", upper=True, bold=True, kind="title")
        sub = {"host": "you host", "client": "connected to the host"}.get(self.mode)
        if self.mode == "client" and self.client and not self.client.connected:
            sub = "party closed" if getattr(self.client, "party_closed", False) else "disconnected from the host"
        ui.text(sub or f"{m.world.name} · {PARTY_MODES[m.mode]} · match vs bots", (self.w // 2, 58),
                "xs", "muted", "center", upper=True)
        if self.mode == "local" and self.w >= 1000:
            self.draw_team_picks()
        elif self.mode != "local":
            self.draw_party_teams(24, 96)
            self.draw_party_settings(pygame.Rect(self.w - 324, 90, 300, 74))
        self.draw_chosen_agent()
        self.draw_agent_grid()
        top = 176 if self.mode != "local" else 96
        compact = self.w < 1000
        self.draw_rules_panel(pygame.Rect(self.w - 324, top, 300, self.h - top - 42 if compact else 489))
        if self.session:
            net = self.session.net
            copy = "Copy join code" if net.mode == "internet" else "Copy IP address"
            if compact:
                ui.text(net.join_code, (self.w - 316, self.h - 30), "xs", "gold", bold=True)
                ui.button(pygame.Rect(self.w - 172, self.h - 38, 148, 28), "Copy [Ctrl+C]", "copy_address", size="xs")
            else:
                ui.text(net.join_code, (24, self.h - 116), "s", "gold", bold=True)
                ui.button(pygame.Rect(24, self.h - 91, 216, 36), f"{copy} [Ctrl+C]", "copy_address", size="xs")
            if net.warning and not self.status:
                self.status = net.warning
        elif self.client and not self.client.connected:
            closed = getattr(self.client, "party_closed", False)
            label = "Back to menu [Enter]" if closed else "Reconnect [Enter]"
            ui.button(pygame.Rect(24, self.h - 91, 216, 36), label, "to_menu" if closed else "rejoin",
                      primary=True, enabled=closed or not self.rejoin_cleanup_pending(), size="s")
        if self.status:
            width = self.w - (352 if compact and self.session else 48)
            lines = ui.wrap(self.status, "s", width)
            self.draw_rejoin_details_button(pygame.Rect(self.w - 156, self.h - 91, 132, 36), lines, width)
            shown = lines[:2]
            for i, line in enumerate(shown):
                if ui.size(line, "s")[0] > width or (i == 1 and len(lines) > 2):
                    while line and ui.size(line + "…", "s")[0] > width:
                        line = line[:-1]
                    line = line.rstrip() + "…"
                line_height = ui.size("Ag", "s")[1]
                ui.text(line, (24, self.h - 30 - (len(shown) - i - 1) * line_height), "s", "muted")
        if self.party_map_picker is not None:
            self.party_map_picker.draw(ui)
        elif self.agent_abilities_open:
            self.draw_lobby_abilities()
        elif self.lobby_role_picker_open:
            draw_role_picker(ui, self.lobby_agent_role)

    def draw_lobby_abilities(self) -> None:
        mine = self.match.players.get(self.me)
        if mine is None:
            return
        ui = self.kit
        agent_key = self.preview_agent_key()
        agent = self.match.agents.get(agent_key, {})
        passive = AGENT_PASSIVES.get(agent_key)
        ui.shade()
        box = pygame.Rect(0, 0, min(640, self.w - 32), 392)
        box.center = (self.w // 2, self.h // 2)
        ui.panel(box, "bg", edge="top")
        ui.text(agent.get("name", agent_key), (box.x + 22, box.y + 20), "l", bold=True, upper=True, kind="title")
        if agent_key != mine.agent:
            ui.text("Preview", (box.x + 22, box.y + 51), "xs", "ally", upper=True)
        ui.button(pygame.Rect(box.right - 122, box.y + 15, 102, 34),
                  "Close [Esc]", "agent_abilities_close", size="xs")
        if agent_key != mine.agent:
            ui.button(pygame.Rect(box.right - 174, box.y + 50, 154, 22),
                      "Select [Enter]", "agent_abilities_choose", primary=True,
                      enabled=self.client is None or self.client.connected, size="xs")
        self.draw_lobby_ability_rows(agent_key, agent, box.x + 22, box.y + 76)
        slots = ("C", "Q", "E", "X", "passive") if passive else ("C", "Q", "E", "X")
        for index, slot in enumerate(slots):
            row = pygame.Rect(box.x + 16, box.y + 73 + index * 36, box.w - 32, 34)
            if slot == "passive" and passive:
                ui.text(f"Passive · {passive[0]}", (box.x + 22, row.y + 10), "s", "text", upper=True)
            if index == self.ability_detail:
                ui.outline(row, "ally", 1)
                ability = agent.get("abilities", {}).get(slot)
                description = describe(ability) if ability else ""
                if slot == "passive" and passive:
                    description = passive[1].format(jump=pygame.key.name(self.keys["jump"]).upper())
                for line_no, line in enumerate(ui.wrap(description, "xs", box.w - 44)):
                    ui.text(line, (box.x + 22, box.y + (258 if passive else 238) + line_no * 15), "xs", "text")
            ui.area(row, f"ability_detail:{index}")
        y = box.bottom - 29
        ui.button(pygame.Rect(box.x + 22, y, 94, 22), "< Agent", "ability_agent:-1", size="xs")
        ui.button(pygame.Rect(box.x + 124, y, 94, 22), "Agent >", "ability_agent:1", size="xs")
        ui.text("Left / Right: agent   Up / Down: ability", (box.right - 22, y + 5), "xs", "muted", "right")

    def draw_party_settings(self, box: pygame.Rect) -> None:
        ui, m = self.kit, self.match
        for i, (field, value) in enumerate((("mode", PARTY_MODES[m.mode]), ("map", m.world.name))):
            y = box.y + i * 40
            ui.text(field, (box.x + 8, y + 9), "xs", "muted", upper=True)
            if self.session and field == "map":
                ui.button(pygame.Rect(box.x + 91, y, box.w - 124, 34), f"{value}  [M]", "choose_map", size="xs")
            else:
                label = f"{value} [V]" if self.session and field == "mode" else value
                ui.text(label, (box.centerx + 21, y + 8), "xs" if self.session else "s",
                        "text", "center", bold=True)
            if self.session:
                ui.button(pygame.Rect(box.x + 58, y, 27, 34), "<", f"setting:{field}:-1", size="xs")
                ui.button(pygame.Rect(box.right - 27, y, 27, 34), ">", f"setting:{field}:1", size="xs")

    def draw_party_teams(self, x: int, y: int) -> None:
        ui, m = self.kit, self.match
        players = tuple(m.players.values())
        own = m.players.get(self.me)
        compact = self.w < 1000
        top = y
        for team, label in enumerate(("Attack first", "Defend first")):
            if compact:
                x, y = 24 + team * 143, top - 8
            members = [p for p in players if p.team == team]
            ui.text(label if m.mode != "deathmatch" else f"Team {team + 1}", (x, y + 8), "s", "text", bold=True)
            if own and own.team != team:
                join = pygame.Rect(x, y + 26, 58, 19) if compact else pygame.Rect(x + 146, y, 70, 29)
                ui.button(join, "Join [T]", f"team:{team}", size="xs",
                          enabled=len(members) < 5 and (self.session is not None or self.client.connected))
            y += 48 if compact else 34
            for p in members:
                row = pygame.Rect(x, y, 135 if compact else 216, 18 if compact else 29)
                ui.fill(row, "panel_light" if p.pid == self.me else "panel")
                size = 14 if compact else 23
                portrait = self.bank.scaled(f"agents/{p.agent}/{p.agent}_portrait.png", (size, size))
                if portrait is not None:
                    self.screen.blit(portrait, (x + 4, y + 3))
                ui.text(p.name[:12] if compact else p.name, (x + 23 if compact else x + 36, y + (3 if compact else 8)),
                        "xs" if compact else "s", "gold" if p.pid == self.me else "text")
                y += 20 if compact else 32
            y += 10

    def draw_team_picks(self) -> None:
        """Show the local team's choices beneath the agent preview."""
        ui, m, s = self.kit, self.match, self.screen
        me = m.players.get(self.me)
        team = me.team if me else 0
        players = sorted((p for p in m.players.values() if p.team == team), key=lambda p: (p.pid != self.me, p.pid))
        area = self.agent_area()
        gap, width, y = 8, (area.w - 32) // 5, self.h - 176
        x = area.centerx - (len(players) * (width + gap) - gap) // 2
        for p in players:
            r = pygame.Rect(x, y, width, 52)
            ui.fill(r, "panel_light" if p.pid == self.me else "panel")
            pygame.draw.rect(s, color("ally"), (r.x, r.y, 3, r.h))
            pic = self.bank.scaled(f"agents/{p.agent}/{p.agent}_portrait.png", (34, 34))
            if pic is not None:
                s.blit(pic, (r.x + 7, r.y + 9))
            ui.text(p.name, (r.x + 45, r.y + 8), "s", "gold" if p.pid == self.me else "text", bold=True)
            ui.text(m.agents.get(p.agent, {}).get("name", p.agent), (r.x + 45, r.y + 28), "xs", "muted", upper=True)
            x += width + gap

    def draw_chosen_agent(self) -> None:
        """The chosen agent large in the centre, name and role beside, abilities underneath."""
        ui, m, s = self.kit, self.match, self.screen
        mine = m.players.get(self.me)
        if mine is None:
            return
        agent = m.agents.get(mine.agent, {})
        if self.w < 1000:
            x = (self.w - 324) // 2 if self.mode == "local" else self.w - 425
            ui.text(agent.get("name", mine.agent), (x, 91), "l", "text", "center", upper=True, bold=True, kind="title")
            ui.text(agent.get("role", ""), (x, 122), "xs", "accent", "center", upper=True, bold=True)
            art = self.bank.scaled(f"agents/{mine.agent}/{mine.agent}_select.png", (34, 68))
            if art is not None:
                s.blit(art, art.get_rect(midtop=(x, 143)))
            ui.button(pygame.Rect(x - 68, 214, 136, 22), "Abilities [F1]", "agent_abilities_open", size="xs")
            return
        art = self.bank.scaled(f"agents/{mine.agent}/{mine.agent}_select.png", (150, 300))
        cx = self.agent_area().centerx - 108
        if art is not None:
            s.blit(art, (cx - 75, 90))
        ui.text(agent.get("name", mine.agent), (cx + 100, 120), "xxl", "text", upper=True, bold=True, kind="title")
        ui.text(agent.get("role", ""), (cx + 104, 190), "s", "accent", upper=True, bold=True)
        self.draw_lobby_ability_rows(mine.agent, agent, cx + 104, 230)
        ui.button(pygame.Rect(cx + 104, 376, 136, 26), "Abilities [F1]", "agent_abilities_open", size="xs")

    def draw_lobby_ability_rows(self, agent_key: str, agent: dict, x: int, y: int) -> None:
        ui, s = self.kit, self.screen
        for slot in ("C", "Q", "E", "X"):
            ab = agent.get("abilities", {}).get(slot, {})
            icon = self.bank.scaled(f"ui/ability_{agent_key}_{slot}.png", (28, 28))
            if icon is not None:
                s.blit(icon, (x, y))
            key = pygame.key.name(self.keys[f"ability_{slot.lower()}"])
            ui.text(key, (x + 36, y + 6), "xs", "muted", upper=True, bold=True)
            ui.text(ab.get("name", ""), (x + 36 + max(20, ui.size(key, "xs", upper=True, bold=True)[0] + 8), y + 6),
                    "s", "text", upper=True)
            y += 36

    def agent_area(self) -> pygame.Rect:
        """Reserve the centre for agent art, portraits and the match action."""
        return pygame.Rect(272, 84, self.w - 620, self.h - 108)

    def draw_agent_grid(self) -> None:
        """Place the roster beside local team selection or beneath the IP party preview."""
        ui, m, s = self.kit, self.match, self.screen
        mine = m.players.get(self.me)
        self.agent_cards = []
        keys = self.lobby_agent_keys()
        result_count = len(keys)
        area = self.agent_area()
        compact = self.w < 1000
        cell, gap = (40, 8) if compact else (52, 8)
        per_row, page_rows = self.agent_grid_shape()
        page_size = per_row * page_rows
        last_page = max(0, (len(keys) - 1) // page_size)
        self.agent_page = min(self.agent_page, last_page)
        keys = keys[self.agent_page * page_size:(self.agent_page + 1) * page_size]
        rows = (len(keys) - 1) // per_row + 1
        width = min(len(keys), per_row) * (cell + gap) - gap
        center = (self.w - 324) // 2 if compact else area.centerx
        if compact:
            x0, y0 = center - width // 2, self.h - 208
        elif self.mode == "local":
            x0, y0 = 24, 112
        else:
            x0, y0 = center - width // 2, self.h - 130 - rows * (cell + gap)
        search_x = 24 if compact or self.mode == "local" else center - 136
        search_y = 78 if not compact and self.mode == "local" else (self.h - 232 if compact else y0 - 27)
        field = pygame.Rect(search_x, search_y, 94 if compact else 105, 20)
        ui.textfield(field, self.lobby_agent_searching)
        shown = self.lobby_agent_query + ("_" if self.lobby_agent_searching else "")
        while shown and ui.size(shown, "xs")[0] > field.w - 12:
            shown = shown[1:]
        ui.text(shown or "Search [/]", (field.x + 6, field.y + 3), "xs", "text")
        ui.area(field, "lobby_agent_search")
        if self.lobby_agent_query:
            ui.button(pygame.Rect(field.right + 4, field.y, 22, field.h), "X", "lobby_agent_search_clear", size="xs")
        role = pygame.Rect(field.right + 30, field.y, 166, field.h)
        ui.button(role, f"{AGENT_ROLES[self.lobby_agent_role]} [Ctrl+R]", "lobby_agent_role",
                  selected=self.lobby_agent_role != 0, size="xs")
        if self.lobby_agent_query or self.lobby_agent_role:
            reset_x = role.right + 5
            if compact and self.mode != "local":
                reset_x = field.x
            reset_y = field.y if reset_x != field.x else self.h - 82
            ui.button(pygame.Rect(reset_x, reset_y, 126 if compact else 136, field.h),
                      "Reset [Ctrl+Del]", "lobby_agent_filters_reset", size="xs")
        if not keys:
            ui.text("No agents found", (field.x, field.bottom + 10), "xs", "text")
        mouse = pygame.mouse.get_pos()
        hovered_agent = None
        for i, key in enumerate(keys):
            r = pygame.Rect(x0 + (i % per_row) * (cell + gap), y0 + (i // per_row) * (cell + gap), cell, cell)
            self.agent_cards.append((r, key))
            chosen = mine is not None and mine.agent == key
            hovered = r.collidepoint(mouse)
            if hovered:
                hovered_agent = key
            ui.fill(r, "panel_light" if hovered or chosen else "panel")
            pic = self.bank.scaled(f"agents/{key}/{key}_portrait.png", (cell - 6, cell - 6))
            if pic is not None:
                s.blit(pic, (r.x + 3, r.y + 3))
            else:
                ui.text(m.agents[key].get("name", key)[:3 if compact else 5], (r.centerx, r.centery - 6),
                        "xs", "text", "center", upper=True, bold=True)
            if chosen:
                ui.outline(r.inflate(4, 4), "ally", 2)
            if key == self.agent_focus:
                ui.outline(r, "text", 2)
            ui.area(r, f"agent:{key}")
        hint_y = self.h - 105 if compact or self.mode != "local" else y0 + rows * (cell + gap) + 4
        hint_x = center if compact or self.mode != "local" else x0 + 112
        mouse_name = m.agents.get(hovered_agent, {}).get("name", "")
        focus_name = m.agents.get(self.agent_focus, {}).get("name", "")
        if mouse_name:
            hint = f"{mouse_name}  /  Right-click to preview"
        elif focus_name:
            hint = f"{focus_name}  /  Space selects  /  F1 previews"
        else:
            hint = "Arrows to browse  /  Space to select"
        if result_count and (self.lobby_agent_query or self.lobby_agent_role):
            count = f"{result_count}/{len(m.agents)} agents"
            hint_width = 2 * min(hint_x - 12, self.w - hint_x - 12)
            if not mouse_name and not focus_name:
                hint = f"{count}  /  Space to select"
            elif ui.size(f"{count}  /  {hint}", "xs")[0] <= hint_width:
                hint = f"{count}  /  {hint}"
            else:
                hint = f"{count}  /  {mouse_name or focus_name}"
        ui.text(hint, (hint_x, hint_y), "xs", "text", "center")
        if last_page:
            y = hint_y + 17
            first = self.agent_page * page_size + 1
            label = f"{first}–{first + len(keys) - 1} of {result_count}"
            shortcut = "PgUp / PgDn"
            offset = max(ui.size(label, "xs")[0], ui.size(shortcut, "xs")[0]) // 2 + 10
            ui.button(pygame.Rect(hint_x - offset - 30, y, 30, 22), "<", "agent_page:-1",
                      enabled=self.agent_page > 0, size="xs")
            ui.button(pygame.Rect(hint_x + offset, y, 30, 22), ">", "agent_page:1",
                      enabled=self.agent_page < last_page, size="xs")
            ui.text(label, (hint_x, y - 2), "xs", "text", "center")
            ui.text(shortcut, (hint_x, y + 9), "xs", "muted", "center")
        if self.mode == "client":
            if self.client and self.client.connected:
                ui.text("Waiting for the host to start …", (center, self.h - 52), "s", "muted", "center", upper=True)
        else:
            label = "Open range" if self.practice else "Start match" if self.session else "Lock in"
            button = pygame.Rect(center - 150, self.h - 61, 300, 45)
            ui.button(button, label, "start", primary=True, size="l")
            ui.text("Enter", (button.right - 14, button.bottom), "xs", "text", "right", bold=True)




    def draw_rules_panel(self, box: pygame.Rect) -> None:
        """Toggles and round count; cheats only matter (and are only clickable) while cheats are allowed."""
        ui, lobby = self.kit, self.match.cfg.lobby
        edit = self.can_edit_rules()
        compact = self.w < 1000
        ui.panel(box, "panel", edge="top")
        ui.text("Lobby rules", (box.x + 20, box.y + (10 if compact else 18)), "s" if compact else "m",
                "text", upper=True, bold=True)
        if not edit:
            ui.text("set by the host", (box.right - 20, box.y + (10 if compact else 20)), "xs", "muted", "right", upper=True)
        else:
            hint = "Arrows / Enter / Esc" if self.rule_focus else "F7: focus rules"
            ui.text(hint, (box.right - 20, box.y + (10 if compact else 20)), "xs", "muted", "right")
        y = box.y + (30 if compact else 56)
        if self.match.mode == "standard":
            ui.text("Win rounds", (box.x + 20, y + (4 if compact else 10)), "s", "muted", upper=True)
            for i, n in enumerate((5, 9, 13)):
                ui.button(pygame.Rect(box.right - 20 - (3 - i) * 52, y, 46, 22 if compact else 36), str(n), f"rounds:{n}",
                          selected=lobby.win_rounds == n, enabled=edit)
            y += 28 if compact else 52

        def toggle(name: str, label: str, enabled: bool, indent: int = 0) -> None:
            nonlocal y
            on = bool(getattr(lobby, name))
            size = 15 if compact else 24
            r = pygame.Rect(box.x + 20 + indent, y, size, size)
            ui.checkbox(r, on, f"rule:{name}") if enabled else ui.outline(r, "line")
            if on and not enabled:
                pygame.draw.rect(self.screen, color("muted"), r.inflate(-8, -8))
            ui.text(label, (r.right + 12, y + (1 if compact else 4)), "s", "text" if enabled else "muted")
            y += 17 if compact else 34

        for name, label in RULES:
            if (name == "overtime" and self.match.mode != "standard"
                    or name == "play_all_rounds" and self.match.mode == "deathmatch"):
                continue
            toggle(name, label, edit)
        y += 3 if compact else 8
        ui.line((box.x + 20, y), (box.right - 20, y))
        y += 6 if compact else 14
        toggle("allow_cheats", "Allow cheats", edit)
        for name, label in CHEATS:
            toggle(name, label, edit and lobby.allow_cheats, indent=24)
        if edit and self.rule_focus:
            focused = next((hit for hit in ui.hits if hit.enabled and hit.action == self.rule_focus), None)
            if focused:
                ui.outline(focused.rect.inflate(4, 2), "text", 2)
