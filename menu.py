"""Main menu of Val2d: play against bots, host or join a network match, browse agents, settings.

Returns the chosen settings as an argparse.Namespace for client.game.Game, or None to quit.
Esc closes whatever is open (dialog, settings, a tab) and never quits; closing the window (Alt+F4) asks first,
a second Alt+F4 quits at once.
"""
from __future__ import annotations

import argparse
from ipaddress import IPv4Address
from concurrent.futures import Future
from pathlib import Path

import pygame

import user_settings
from client.agent_details import AGENT_PASSIVES, AGENT_ROLES, draw_role_picker
from client.connection import run_network_task
from client.inventory import Inventory
from client.map_picker import MapPicker, map_name
from client.settings_panel import SettingsPanel
from client.ui import Ui, color
from gameplay.kit.describe import cost_text, describe
from gameplay.match import DEFAULT_AGENT, playable_agents
from gameplay.netgame import DEFAULT_PORT, discover
from gameplay.world import DEFAULT_MAP, PLAYABLE_MAP_KEYS
from sprite_bank import ASSETS, SpriteBank

MODES = (("standard", "Standard", "13 rounds to win, sides switch after 12. Plant or defuse the bomb."),
         ("quick", "Quick", "First to 5, with Swiftplay economy."),
         ("deathmatch", "Team deathmatch", "Four loadout stages, fast respawns, first team to 100 kills."))
TABS = (("agents", "Agents", -148), ("play", "Play", 0), ("inventory", "Collection", 140), ("career", "Career", 275))
TOP_BAR_ACTIONS = (*("tab:" + key for key, _, _ in TABS), "settings", "quit")
PLAY_MODES = (("standard", "Unrated", "13 rounds to win, sides switch after 12. Plant or defuse the spike."),
              ("quick", "Swiftplay", "First to 5 rounds. Switch sides after four."),
              ("deathmatch", "Team deathmatch", "Four loadout stages, fast respawns, first team to 100 kills."),
              ("custom", "Custom", "Host or join a match with friends on your network or over the internet."))
ROLE_ORDER = AGENT_ROLES[1:]
AGENT_COLUMNS = 6
LAN_PAGE_SIZE = 3


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
        self.map_picker: MapPicker | None = None
        if self.args.map not in self.maps:
            self.args.map = DEFAULT_MAP
        if self.args.agent not in self.agents():
            self.args.agent = DEFAULT_AGENT
        self.address = str(getattr(self.args, "join", "") or "")
        self.address_anchor: int | None = None
        self.address_undo: list[tuple[str, int | None, int | None]] = []
        self.address_redo: list[tuple[str, int | None, int | None]] = []
        self.address_caret: int | None = None
        self.address_visible_start = 0
        self.address_drag_field: pygame.Rect | None = None
        self.typing = False
        self.status = ""
        self.custom_status = ""
        self.lan_error_lines: list[str] = []
        self.lan_error_line_starts: list[int] = []
        self.lan_error_width = 0
        self.lan_error_text = ""
        self.lan_error_copy_status = ""
        self.lan_error_offset = 0
        self.lan_error_focus = ""
        self.join_cleanup_notice: Future[None] | None = None
        self.found: list[tuple[str, int, str]] = []
        self.lan_page = 0
        self.lan_scan: Future[list[tuple[str, int, str]]] | None = None
        self.lan_scan_cancelled = False
        self.tab = "play"
        self.top_bar_focus: str | None = None
        self.custom_focus: str | None = None
        self.view = "main"
        self.play_mode = self.args.mode
        self.mode_focus = 0
        self.dialog = ""              # "" or "quit"
        self.panel = SettingsPanel(self.ui)
        self.settings = self.panel.settings
        self.address = self.address or self.settings["last_join"]
        self.career_match: int | None = None  # match shown in detail on the Career page
        self.agent_view = self.args.agent
        self.agent_keyboard_focus = False
        self.agent_query = ""
        self.agent_role = 0
        self.role_picker_open = False
        self.agent_searching = False
        self.agent_ability_slot: str | None = None
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
            self.finish_lan_scan()
            self.draw()
            pygame.display.flip()

    def handle(self, ev: pygame.event.Event) -> argparse.Namespace | bool | None:
        """One input event. Returns a Namespace to start a match, False to quit, None to stay."""
        if ev.type == pygame.QUIT:
            if self.dialog == "quit":
                return False  # second Alt+F4: quit at once
            self.dialog = "quit"
            return None
        if self.lan_error_lines and not self.dialog:
            self.handle_lan_error(ev)
            return None
        if (ev.type == pygame.KEYDOWN and ev.key == pygame.K_F1
                and any(hit.action == "lan_error_details" for hit in self.ui.hits[self.ui.modal_from:])):
            self.open_lan_error()
            return None
        if self.lan_scan is not None and not self.lan_scan_cancelled and not self.dialog:
            if (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
                    or ev.type == pygame.MOUSEBUTTONUP and ev.button == 1
                    and (hit := self.ui.hit_at(ev.pos)) and hit.action == "cancel_lan_scan"):
                self.lan_scan_cancelled = True
                self.custom_status = "LAN search cancelled"
                self.custom_focus = "field:address"
            return None
        if self.view == "settings" and not self.dialog:
            if self.panel.handle(ev) == "closed":
                self.settings = self.panel.settings
                self.apply_settings()
                self.view = "main"
            return None
        if ev.type == pygame.KEYDOWN and self.map_picker is not None and not self.dialog:
            if action := self.map_picker.key_action(ev.key, self.screen.get_width()):
                self.activate(action)
            return None
        if ev.type == pygame.KEYDOWN and self.role_picker_open and not self.dialog:
            if ev.key == pygame.K_ESCAPE:
                self.activate("role_back")
            elif pygame.K_1 <= ev.key <= pygame.K_5:
                self.activate(f"role_pick:{ev.key - pygame.K_1}")
            return None
        if ev.type == pygame.KEYDOWN and self.agent_ability_slot is not None and not self.dialog:
            if ev.key in (pygame.K_ESCAPE, pygame.K_F1):
                self.agent_ability_slot = None
            elif ev.key in (pygame.K_UP, pygame.K_DOWN):
                slots = ("C", "Q", "E", "X")
                step = -1 if ev.key == pygame.K_UP else 1
                self.agent_ability_slot = slots[(slots.index(self.agent_ability_slot) + step) % len(slots)]
            return None
        if ev.type == pygame.KEYDOWN and self.tab == "agents" and self.view == "main" and not self.dialog:
            if (ev.key == pygame.K_DELETE and getattr(ev, "mod", 0) & pygame.KMOD_CTRL
                    and self.top_bar_focus is None and (self.agent_query or self.agent_role)):
                return self.activate("agent_filters_reset")
            if self.agent_searching:
                if ev.key == pygame.K_ESCAPE:
                    self.set_agent_query("")
                    self.agent_searching = False
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
                    self.agent_searching = False
                    self.agent_keyboard_focus = bool(self.filtered_agents())
                elif ev.key == pygame.K_BACKSPACE:
                    self.set_agent_query(self.agent_query[:-1])
                elif (value := getattr(ev, "unicode", "")) and value.isprintable():
                    self.set_agent_query((self.agent_query + value)[:24])
                return None
            if ev.key == pygame.K_SLASH and self.top_bar_focus is None:
                return self.activate("agent_search")
            modifiers = getattr(ev, "mod", 0)
            if ev.key == pygame.K_r and modifiers & pygame.KMOD_CTRL and self.top_bar_focus is None:
                return self.activate("agent_role")
            if (ev.key == pygame.K_r and self.top_bar_focus is None
                    and not modifiers & (pygame.KMOD_CTRL | pygame.KMOD_ALT | pygame.KMOD_GUI)):
                self.cycle_agent_role(-1 if modifiers & pygame.KMOD_SHIFT else 1)
                return None
        if (ev.type == pygame.KEYDOWN and ev.key == pygame.K_F1 and self.tab == "agents"
                and self.view == "main" and not self.dialog):
            self.agent_ability_slot = "C"
            return None
        if ev.type == pygame.KEYDOWN and self.typing:
            self.address_drag_field = None
            if ev.key == pygame.K_TAB:
                self.typing = False
                self.custom_focus = "field:address"
                self.move_custom_focus(bool(getattr(ev, "mod", 0) & pygame.KMOD_SHIFT))
                return None
            if ev.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_KP_ENTER):
                self.typing = False
                if ev.key != pygame.K_ESCAPE and self.address:
                    return self.activate("join")
                return None
            caret = len(self.address) if self.address_caret is None else self.address_caret
            modifiers = getattr(ev, "mod", 0)
            start, end = self.address_selection()
            if ev.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_HOME, pygame.K_END):
                positions = {pygame.K_LEFT: caret - 1, pygame.K_RIGHT: caret + 1,
                             pygame.K_HOME: 0, pygame.K_END: len(self.address)}
                if modifiers & pygame.KMOD_SHIFT:
                    if self.address_anchor is None:
                        self.address_anchor = caret
                else:
                    if start != end:
                        positions.update({pygame.K_LEFT: start, pygame.K_RIGHT: end})
                    self.address_anchor = None
                self.address_caret = max(0, min(len(self.address), positions[ev.key]))
            elif ev.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
                if start != end:
                    self.replace_address_text("")
                else:
                    start = max(0, caret - 1) if ev.key == pygame.K_BACKSPACE else caret
                    end = caret if ev.key == pygame.K_BACKSPACE else caret + 1
                    self.apply_address_edit(self.address[:start] + self.address[end:], start)
            elif modifiers & pygame.KMOD_CTRL and ev.key in (pygame.K_z, pygame.K_y):
                redo = ev.key == pygame.K_y or bool(modifiers & pygame.KMOD_SHIFT)
                self.restore_address_edit(redo)
            elif modifiers & pygame.KMOD_CTRL and ev.key == pygame.K_a:
                self.address_anchor = 0
                self.address_caret = len(self.address)
            elif modifiers & pygame.KMOD_CTRL and ev.key in (pygame.K_c, pygame.K_x):
                if start != end:
                    try:
                        pygame.scrap.put_text(self.address[start:end])
                    except pygame.error:
                        self.custom_status = "Clipboard unavailable"
                    else:
                        if ev.key == pygame.K_x:
                            self.replace_address_text("")
                        self.custom_status = "Selection cut" if ev.key == pygame.K_x else "Selection copied"
            elif modifiers & pygame.KMOD_CTRL and ev.key == pygame.K_v:
                try:
                    pasted = (pygame.scrap.get_text() or "").strip()
                except pygame.error:
                    pasted = ""
                if pasted and all(c.isalnum() or c in ".:-[]_" for c in pasted):
                    if self.address_caret is None:
                        self.address_anchor = 0
                    self.replace_address_text(pasted)
            elif ev.unicode and (ev.unicode.isalnum() or ev.unicode in ".:-[]_"):
                self.replace_address_text(ev.unicode)
            return None
        if ev.type == pygame.KEYDOWN and self.view == "main" and not self.dialog:
            if ev.key == pygame.K_F6:
                self.top_bar_focus = None if self.top_bar_focus else f"tab:{self.tab}"
                return None
            if self.top_bar_focus is not None:
                if ev.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                    reverse = ev.key == pygame.K_LEFT or (ev.key == pygame.K_TAB
                                                          and getattr(ev, "mod", 0) & pygame.KMOD_SHIFT)
                    index = TOP_BAR_ACTIONS.index(self.top_bar_focus)
                    self.top_bar_focus = TOP_BAR_ACTIONS[(index + (-1 if reverse else 1)) % len(TOP_BAR_ACTIONS)]
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    action, self.top_bar_focus = self.top_bar_focus, None
                    return self.activate(action)
                elif ev.key == pygame.K_ESCAPE:
                    self.top_bar_focus = None
                return None
        if ev.type == pygame.KEYDOWN and self.tab == "agents" and self.view == "main" and not self.dialog:
            if self.handle_agent_grid_key(ev.key):
                return None
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            if self.custom_focus is not None and not self.dialog and self.view == "main":
                self.custom_focus = None
                return None
            self.close_top()
            return None
        if ev.type == pygame.KEYDOWN and self.view == "mode_select" and not self.dialog:
            self.handle_mode_key(ev.key, getattr(ev, "mod", 0))
            return None
        if ev.type == pygame.KEYDOWN and self.tab == "play" and self.view == "main" and not self.dialog:
            if ev.key == pygame.K_v:
                return self.activate("choose_mode")
            if ev.key == pygame.K_m:
                return self.activate("choose_map")
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.play_mode != "custom":
                return self.activate("start")
            if self.play_mode == "custom":
                if (ev.key == pygame.K_c and getattr(ev, "mod", 0) & pygame.KMOD_CTRL
                        and self.custom_focus and self.custom_focus.startswith(("lan:", "lan_edit:"))):
                    self.copy_lan_address(int(self.custom_focus.partition(":")[2]))
                elif ev.key == pygame.K_F2 and self.custom_focus and self.custom_focus.startswith("lan:"):
                    self.edit_lan_address(int(self.custom_focus.removeprefix("lan:")))
                elif ev.key == pygame.K_TAB:
                    self.move_custom_focus(bool(getattr(ev, "mod", 0) & pygame.KMOD_SHIFT))
                elif ev.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                    self.turn_lan_page(-1 if ev.key == pygame.K_PAGEUP else 1)
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and self.custom_focus:
                    action, self.custom_focus = self.custom_focus, None
                    return self.activate(action)
        if ev.type == pygame.MOUSEWHEEL and self.tab == "inventory" and not self.dialog:
            self.inventory.turn_page(-ev.y)
            return None
        if ev.type == pygame.KEYDOWN and self.tab == "inventory" and self.view == "main" and not self.dialog:
            action = self.inventory.keyboard_action(ev.key, bool(getattr(ev, "mod", 0) & pygame.KMOD_SHIFT),
                                                    self.settings["weapon_skins"])
            if action:
                return self.activate(action)
        if (ev.type == pygame.MOUSEBUTTONUP and ev.button == 3 and self.tab == "play"
                and self.play_mode == "custom" and self.view == "main" and not self.dialog
                and self.map_picker is None):
            for hit in self.ui.hits[self.ui.modal_from:]:
                if hit.action.startswith("lan:") and hit.rect.collidepoint(ev.pos):
                    self.copy_lan_address(int(hit.action.removeprefix("lan:")))
                    break
            return None
        if self.address_drag_field is not None and (
                ev.type == pygame.MOUSEMOTION or (ev.type == pygame.MOUSEBUTTONUP and ev.button == 1)):
            self.address_caret = self.address_index_at(ev.pos[0], self.address_drag_field)
            if ev.type == pygame.MOUSEBUTTONUP:
                self.address_drag_field = None
            return None
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            hit = self.ui.hit_at(ev.pos)
            action, self.ui.pressed = self.ui.pressed, None
            if hit and action == hit.action:
                return self.activate(action)
            return None
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.address_drag_field = None
            self.agent_keyboard_focus = False
            self.agent_searching = False
            self.top_bar_focus = None
            self.custom_focus = None
            hit = self.ui.hit_at(ev.pos)
            self.typing = False
            if hit is None:
                return None
            if self.map_picker is not None and not self.dialog and not hit.action.startswith(("map_pick:", "map_back")):
                return None
            if hit.action == "field:address":
                self.activate(hit.action)
                self.address_caret = self.address_index_at(ev.pos[0], hit.rect)
                self.address_anchor = self.address_caret
                self.address_drag_field = hit.rect.copy()
                return None
            self.ui.pressed = hit.action
        return None

    def address_index_at(self, screen_x: int, field: pygame.Rect) -> int:
        offset = min(self.address_visible_start, len(self.address))
        x = screen_x - field.x - 12
        if x < 0:
            return max(0, offset - 1)
        return min(range(offset, len(self.address) + 1),
                   key=lambda i: abs(self.ui.size(self.address[offset:i], "s")[0] - x))

    def address_selection(self) -> tuple[int, int]:
        caret = len(self.address) if self.address_caret is None else self.address_caret
        anchor = caret if self.address_anchor is None else self.address_anchor
        return min(anchor, caret), max(anchor, caret)

    def replace_address_text(self, value: str) -> None:
        start, end = self.address_selection()
        before, after = self.address[:start], self.address[end:]
        inserted = value[:max(0, 128 - len(before) - len(after))]
        self.apply_address_edit(before + inserted + after, len(before) + len(inserted))

    def apply_address_edit(self, text: str, caret: int) -> None:
        if text != self.address:
            self.address_undo.append((self.address, self.address_caret, self.address_anchor))
            self.address_redo.clear()
        self.address = text
        self.address_caret = caret
        self.address_anchor = None

    def restore_address_edit(self, redo: bool) -> None:
        source, destination = (self.address_redo, self.address_undo) if redo else (self.address_undo, self.address_redo)
        if source:
            destination.append((self.address, self.address_caret, self.address_anchor))
            self.address, self.address_caret, self.address_anchor = source.pop()

    def restore_join_focus(self, target: str) -> None:
        self.apply_address_edit(target, len(target))
        self.address_drag_field = None
        self.custom_focus = None
        self.activate("field:address")

    def move_custom_focus(self, reverse: bool) -> None:
        actions = ["host", "host_online", "choose_map", "field:address"]
        if self.address and not self.join_address_error() and not self.join_cleanup_pending():
            actions.append("join")
        if self.lan_scan is None:
            actions.append("find")
        first = self.lan_page * LAN_PAGE_SIZE
        join_pending = self.join_cleanup_pending()
        last = min(first + LAN_PAGE_SIZE, len(self.found))
        for i in range(first, last):
            if not join_pending:
                actions.append(f"lan:{i}")
            actions.append(f"lan_edit:{i}")
        if first > 0:
            actions.append("lan_page:-1")
        if last < len(self.found):
            actions.append("lan_page:1")
        if any(hit.action == "lan_error_details" for hit in self.ui.hits[self.ui.modal_from:]):
            actions.append("lan_error_details")
        if self.custom_focus in actions:
            index = actions.index(self.custom_focus) + (-1 if reverse else 1)
        else:
            index = -1 if reverse else 0
        self.custom_focus = actions[index % len(actions)]

    def turn_lan_page(self, step: int) -> None:
        last = max(0, (len(self.found) - 1) // LAN_PAGE_SIZE)
        page = max(0, min(last, self.lan_page + step))
        if page != self.lan_page:
            self.lan_page = page
            lan_action = "lan_edit" if self.join_cleanup_pending() else "lan"
            self.custom_focus = f"{lan_action}:{page * LAN_PAGE_SIZE}"

    def join_cleanup_pending(self) -> bool:
        return self.join_cleanup_notice is not None and not self.join_cleanup_notice.done()

    def join_address_error(self) -> str:
        host, separator, port = self.address.partition(":")
        if "." in host and all(char in "0123456789." for char in host):
            try:
                IPv4Address(host)
            except ValueError:
                return "Enter a valid IPv4 address."
        if separator and (not port.isascii() or not port.isdecimal() or not 1 <= int(port) <= 65535):
            return "Enter a port from 1 to 65535."
        if separator and "." not in host and host.lower() != "localhost":
            return "Use an IP address or full hostname with a port."
        return ""

    def copy_lan_address(self, index: int) -> None:
        if not 0 <= index < len(self.found):
            return
        address, port, _ = self.found[index]
        try:
            pygame.scrap.put_text(f"{address}:{port}")
        except pygame.error:
            self.custom_status = "Copy unavailable. Use the address shown in the list."
        else:
            self.custom_status = "LAN address copied"

    def edit_lan_address(self, index: int) -> None:
        if 0 <= index < len(self.found):
            address, port, _ = self.found[index]
            endpoint = f"{address}:{port}"
            self.apply_address_edit(endpoint, len(endpoint))
            self.custom_focus = None
            self.activate("field:address")

    def handle_mode_key(self, key: int, modifiers: int) -> None:
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.activate(f"mode:{PLAY_MODES[self.mode_focus][0]}")
        elif key == pygame.K_TAB:
            step = -1 if modifiers & pygame.KMOD_SHIFT else 1
            self.mode_focus = (self.mode_focus + step) % len(PLAY_MODES)
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            row = self.mode_focus // 2
            self.mode_focus = row * 2 + int(key == pygame.K_RIGHT)
        elif key in (pygame.K_UP, pygame.K_DOWN):
            column = self.mode_focus % 2
            self.mode_focus = column + (2 if key == pygame.K_DOWN else 0)

    def close_top(self) -> None:
        """Esc: closes the topmost thing that is open; on the home tab nothing happens."""
        if self.dialog:
            self.dialog = ""
        elif self.view == "settings":
            self.panel.close()
            self.settings = self.panel.settings
            self.apply_settings()
            self.view = "main"
        elif self.view == "mode_select":
            self.view = "main"
        elif self.career_match is not None:
            self.career_match = None
        elif self.tab != "play":
            self.tab = "play"
        elif self.play_mode == "custom":
            self.play_mode = self.args.mode


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
            self.custom_focus = None
            if self.tab == "inventory":
                self.inventory.focus = None
                self.inventory.open(self.settings["weapon_skins"])
        elif action.startswith("inventory:"):
            if self.inventory.activate(action, self.settings["weapon_skins"]):
                saved = user_settings.load()
                saved["weapon_skins"] = self.settings["weapon_skins"]
                user_settings.save(saved)
        elif action == "settings":
            self.panel = SettingsPanel(self.ui)
            self.view = "settings"
        elif action == "choose_mode":
            self.custom_focus = None
            self.mode_focus = next(i for i, (key, _, _) in enumerate(PLAY_MODES) if key == self.play_mode)
            self.view = "mode_select"
        elif action == "mode_back":
            self.view = "main"
        elif action == "choose_map":
            self.map_picker = MapPicker(self.map_names, a.map)
        elif action == "map_back":
            self.map_picker = None
        elif action == "field:address":
            self.typing = True
            self.address_anchor = None
            self.address_caret = len(self.address)
        elif action.startswith("map_pick:"):
            key = action.removeprefix("map_pick:")
            if self.map_picker is not None and key in self.map_names:
                a.map = key
                self.map_picker = None
        elif action == "local":
            a.host, a.join, a.practice = False, None, False
            return a
        elif action == "host":
            self.custom_status = ""
            a.host, a.join, a.online = True, None, False
            return a
        elif action == "host_online":
            self.custom_status = ""
            a.host, a.join, a.online = True, None, True
            return a
        elif action == "join" and self.address:
            if self.join_address_error() or self.join_cleanup_pending():
                self.typing = True
                return None
            lan = "." in self.address or self.address.lower() == "localhost"
            target = f"{self.address}:{DEFAULT_PORT}" if lan and ":" not in self.address else self.address
            self.custom_status = ""
            a.host, a.join, a.online = False, target, False
            return a
        elif action == "lan_error_details":
            self.open_lan_error()
        elif action == "find":
            if self.lan_scan is None:
                self.lan_scan = run_network_task(lambda: discover(2.0))
                self.lan_scan_cancelled = False
                self.custom_status = ""
        elif action.startswith("lan_page:"):
            self.turn_lan_page(int(action.removeprefix("lan_page:")))
        elif action.startswith("lan_edit:"):
            self.edit_lan_address(int(action.removeprefix("lan_edit:")))
        elif action.startswith("lan:"):
            if self.join_cleanup_pending():
                return None
            address, port, _ = self.found[int(action[4:])]
            self.custom_status = ""
            a.host, a.join = False, f"{address}:{port}"
            return a
        elif action.startswith("mode:"):
            self.play_mode = action[5:]
            self.view = "main"
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
            key = action[6:]
            if key in self.agents():
                self.agent_view = key
        elif action == "agent_search":
            self.agent_searching = True
            self.agent_keyboard_focus = False
        elif action == "agent_search_clear":
            self.set_agent_query("")
        elif action == "agent_filters_reset":
            self.agent_role = 0
            self.agent_searching = False
            self.agent_view = self.args.agent
            self.set_agent_query("")
            self.agent_keyboard_focus = bool(self.filtered_agents())
        elif action == "agent_role":
            self.role_picker_open = True
        elif action == "role_back":
            self.role_picker_open = False
        elif action.startswith("role_pick:"):
            self.agent_role = int(action.removeprefix("role_pick:"))
            self.set_agent_query(self.agent_query)
            self.role_picker_open = False
        elif action.startswith("agent_page:"):
            self.turn_agent_page(int(action.removeprefix("agent_page:")))
        elif action.startswith("agent_ability:"):
            self.agent_ability_slot = action.removeprefix("agent_ability:")
        elif action == "agent_ability_close":
            self.agent_ability_slot = None
        elif action == "pick_agent":
            agent = self.agents().get(self.agent_view)
            if agent is not None:
                a.agent = self.agent_view
                self.status = f"{agent['name']} selected"
        return None

    # ------------------------------------------------------------ drawing
    def finish_lan_scan(self) -> None:
        if self.lan_scan is None or not self.lan_scan.done():
            return
        scan, self.lan_scan = self.lan_scan, None
        if self.lan_scan_cancelled:
            return
        try:
            self.found = scan.result()
        except OSError as exc:
            self.custom_status = f"LAN search failed: {exc}"
            self.custom_focus = "find"
            return
        self.lan_page = 0
        self.custom_focus = "find"
        if self.found:
            self.custom_focus = "lan_edit:0" if self.join_cleanup_pending() else "lan:0"
        self.custom_status = f"{len(self.found)} match(es) found" if self.found else "No match found on this network"

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
        in_custom = self.tab == "play" and self.play_mode == "custom"
        status = self.custom_status if in_custom else self.status
        if self.join_cleanup_notice is not None and self.join_cleanup_notice.done():
            self.join_cleanup_notice = None
        notices = []
        if in_custom and self.join_cleanup_notice is not None:
            notices.append("Finishing the previous connection attempt…")
        if in_custom and self.lan_scan_cancelled and self.lan_scan is not None:
            notices.append("Finishing the previous LAN search…")
        waiting = "\n".join(notices)
        if (status or waiting) and self.view == "main" and self.map_picker is None and not self.dialog:
            self.draw_status(status, w, h, waiting)
        if self.view == "settings":
            self.panel.draw()
        elif self.view == "mode_select":
            self.draw_mode_select(w, h)
        if self.map_picker is not None:
            self.map_picker.draw(ui)
        if self.agent_ability_slot is not None:
            self.draw_agent_ability_dialog(w)
        if self.role_picker_open:
            draw_role_picker(ui, self.agent_role)
        if self.lan_scan is not None and not self.lan_scan_cancelled:
            ui.dialog("Finding LAN matches", "Searching the local network",
                      [("Cancel [Enter / Esc]", "cancel_lan_scan", False)])
            ui.outline(ui.hits[-1].rect.inflate(4, 4), "text", 2)
        if self.lan_error_lines:
            self.draw_lan_error(w, h)
        if self.dialog == "quit":
            ui.dialog("Quit Val2d?", "Alt+F4 again quits at once.", [("Cancel", "quit_no", False), ("Quit", "quit_yes", True)])

    def draw_status(self, status: str, w: int, h: int, waiting: str = "") -> None:
        ui = self.ui
        width = w - 80
        waiting_lines = ui.wrap(waiting, "s", width) if waiting else []
        lines = ui.wrap(status, "s", width) if status else []
        details = status.startswith("LAN search failed:") and (
            len(lines) + len(waiting_lines) > 3 or any(ui.size(line, "s")[0] > width for line in lines))
        if details:
            width -= 148
            lines = ui.wrap(status, "s", width)
            waiting_lines = ui.wrap(waiting, "s", width) if waiting else []
        shown = lines[:max(0, 3 - len(waiting_lines))]
        for i, line in enumerate(shown):
            if ui.size(line, "s")[0] > width or (i == len(shown) - 1 and len(lines) > len(shown)):
                while line and ui.size(line + "…", "s")[0] > width:
                    line = line[:-1]
                shown[i] = line.rstrip() + "…"
        line_height = ui.size("Ag", "s")[1] + 3
        row_count = len(shown) + len(waiting_lines)
        y = h - 34 - (row_count - 1) * line_height
        if row_count > 1:
            ui.fill(pygame.Rect(32, y - 4, w - 64, row_count * line_height + 8), "bg")
        error = status.startswith(("No match", "No connection", "LAN search failed"))
        for i, line in enumerate(shown):
            ui.text(line, (40, y + i * line_height), "s", "enemy" if error else "gold")
        for i, line in enumerate(waiting_lines, start=len(shown)):
            ui.text(line, (40, y + i * line_height), "s", "gold")
        if details:
            button = pygame.Rect(w - 176, h - 38, 136, 30)
            ui.button(button, "Details [F1]", "lan_error_details", size="s")
            if self.custom_focus == "lan_error_details":
                ui.outline(button.inflate(4, 4), "text", 2)

    def open_lan_error(self) -> None:
        if not self.custom_status.startswith("LAN search failed:"):
            return
        if not self.typing:
            self.custom_focus = "lan_error_details"
        self.lan_error_text = self.custom_status
        self.lan_error_copy_status = ""
        self.lan_error_line_starts = []
        self.lan_error_offset = 0
        self.lan_error_focus = ""
        self.wrap_lan_error(min(900, self.screen.get_width() - 48) - 48)

    def wrap_lan_error(self, width: int) -> None:
        anchor = self.lan_error_line_starts[self.lan_error_offset] if self.lan_error_line_starts else 0
        self.lan_error_width = width
        self.lan_error_lines = []
        self.lan_error_line_starts = []
        position = 0
        offset = 0
        for paragraph in self.lan_error_text.split("\n"):
            line = ""
            self.lan_error_line_starts.append(position)
            for char in paragraph:
                if line and self.ui.size(line + char, "s")[0] > width:
                    split = line.rfind(" ") + 1
                    if split and self.ui.size(line[split:] + char, "s")[0] <= width:
                        self.lan_error_lines.append(line[:split])
                        line = line[split:]
                    else:
                        self.lan_error_lines.append(line)
                        line = ""
                    self.lan_error_line_starts.append(position - len(line))
                line += char
                position += 1
            self.lan_error_lines.append(line)
            position += 1
        for index, start in enumerate(self.lan_error_line_starts):
            if start > anchor:
                break
            offset = index
        self.lan_error_offset = offset

    def handle_lan_error(self, ev: pygame.event.Event) -> None:
        page = self.lan_error_page_size()
        step = 0
        action = ""
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_c and getattr(ev, "mod", 0) & pygame.KMOD_CTRL:
                self.copy_lan_error()
                return
            if ev.key in (pygame.K_ESCAPE, pygame.K_F1):
                self.lan_error_lines.clear()
            if ev.key == pygame.K_TAB:
                actions = self.lan_error_actions(page)
                reverse = bool(getattr(ev, "mod", 0) & pygame.KMOD_SHIFT)
                if self.lan_error_focus in actions:
                    index = actions.index(self.lan_error_focus) + (-1 if reverse else 1)
                else:
                    index = -1 if reverse else 0
                self.lan_error_focus = actions[index % len(actions)]
                return
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                if self.lan_error_focus in self.lan_error_actions(page):
                    action = self.lan_error_focus
            step = {pygame.K_UP: -1, pygame.K_DOWN: 1, pygame.K_PAGEUP: -page,
                    pygame.K_PAGEDOWN: page, pygame.K_HOME: -len(self.lan_error_lines),
                    pygame.K_END: len(self.lan_error_lines)}.get(ev.key, 0)
        elif ev.type == pygame.MOUSEWHEEL:
            step = -ev.y * 3
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and (hit := self.ui.hit_at(ev.pos)):
            action = hit.action
        if action == "lan_error_copy":
            self.copy_lan_error()
            return
        if action == "lan_error_close":
            self.lan_error_lines.clear()
        step = {"lan_error_prev": -page, "lan_error_next": page}.get(action, step)
        self.lan_error_offset = max(0, min(self.lan_error_offset + step, len(self.lan_error_lines) - page))

    def lan_error_actions(self, page: int) -> list[str]:
        actions = []
        if self.lan_error_offset > 0:
            actions.append("lan_error_prev")
        if self.lan_error_offset + page < len(self.lan_error_lines):
            actions.append("lan_error_next")
        return actions + ["lan_error_copy", "lan_error_close"]

    def copy_lan_error(self) -> None:
        try:
            pygame.scrap.put_text(self.lan_error_text)
        except pygame.error:
            self.lan_error_copy_status = "Clipboard unavailable"
        else:
            self.lan_error_copy_status = "Error details copied"

    def lan_error_page_size(self) -> int:
        height = min(520, self.screen.get_height() - 48)
        return max(1, (height - 120) // (self.ui.size("Ag", "s")[1] + 4))

    def draw_lan_error(self, w: int, h: int) -> None:
        ui = self.ui
        ui.shade()
        panel = pygame.Rect(0, 0, min(900, w - 48), min(520, h - 48))
        panel.center = (w // 2, h // 2)
        if panel.w - 48 != self.lan_error_width:
            self.wrap_lan_error(panel.w - 48)
        ui.panel(panel, "bg", edge="top")
        ui.text("LAN search error", (panel.x + 24, panel.y + 20), "l")
        if self.lan_error_copy_status:
            ui.text(self.lan_error_copy_status, (panel.right - 24, panel.y + 24), "s", "muted", "right")
        page = self.lan_error_page_size()
        self.lan_error_offset = min(self.lan_error_offset, max(0, len(self.lan_error_lines) - page))
        start = self.lan_error_offset
        end = min(start + page, len(self.lan_error_lines))
        line_height = ui.size("Ag", "s")[1] + 4
        for row, line in enumerate(self.lan_error_lines[start:end]):
            ui.text(line, (panel.x + 24, panel.y + 62 + row * line_height), "s")
        y = panel.bottom - 48
        ui.button(pygame.Rect(panel.x + 24, y, 118, 30), "Prev [PgUp]", "lan_error_prev", enabled=start > 0, size="xs")
        ui.button(pygame.Rect(panel.x + 150, y, 126, 30), "Next [PgDn]", "lan_error_next",
                  enabled=end < len(self.lan_error_lines), size="xs")
        ui.button(pygame.Rect(panel.x + 284, y, 132, 30), "Copy [Ctrl+C]", "lan_error_copy", size="xs")
        if len(self.lan_error_lines) > page:
            position = f"Lines {start + 1}–{end} of {len(self.lan_error_lines)}"
            ui.text(position, (panel.right - 154, y + 7), "xs", "muted", "right")
        ui.button(pygame.Rect(panel.right - 142, y, 118, 30), "Close [Esc]", "lan_error_close", size="xs")
        actions = self.lan_error_actions(page)
        if self.lan_error_focus and self.lan_error_focus not in actions:
            self.lan_error_focus = actions[0]
        for hit in ui.hits[ui.modal_from:]:
            if hit.action == self.lan_error_focus:
                ui.outline(hit.rect.inflate(4, 4), "text", 2)
                break

    def draw_top_bar(self, w: int) -> None:
        """Main tabs around Play, with the profile controls on the right."""
        ui, s = self.ui, self.screen
        bar = pygame.Rect(0, 0, w, 64)
        ui.fill(bar, "#0f1923e6")
        pygame.draw.rect(s, color("line"), (0, 63, w, 1))
        logo = self.bank.scaled("logo.png", (36, 36))
        if logo is not None:
            s.blit(logo, (24, 14))
        compact = w < 1024
        if not compact:
            ui.text("VAL2D", (68 if logo else 24, 22), "m", "text", bold=True, kind="title")
        cx = (w - 152) // 2 if compact else w // 2
        for key, label, offset in TABS:
            big = key == "play"
            size = "s" if compact else "l" if big else "m"
            tw = ui.size(label, size, upper=True, bold=True)[0]
            x = cx + (offset * 2 // 3 if compact else offset) - tw // 2
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
        if not compact:
            ui.text(self.settings["name"], (w - 196, 24), "s", "text", "right", bold=True)
        ui.button(pygame.Rect(w - 180, 14, 96, 36), "Settings", "settings", size="xs")
        ui.button(pygame.Rect(w - 76, 14, 56, 36), "X", "quit", size="s")
        ui.text("F6: menu", (80 if compact else 135, 27), "xs", "muted")
        if self.top_bar_focus is not None:
            hit = next((hit for hit in ui.hits if hit.action == self.top_bar_focus), None)
            if hit:
                ui.outline(hit.rect.clip(bar.inflate(0, -8)), "text", 2)

    def draw_play(self, w: int, h: int) -> None:
        """Keep the current mode and party together on the Play hub."""
        ui, a = self.ui, self.args
        _, mode_name, _ = next(mode for mode in PLAY_MODES if mode[0] == self.play_mode)
        mode_button = pygame.Rect(w // 2 - 160, 84, 320, 44)
        ui.button(mode_button, f"Mode  /  {mode_name}  [V]", "choose_mode", size="m")
        x, y = mode_button.right - 22, mode_button.centery
        ui.line((x - 5, y - 2), (x, y + 3), "text", 2)
        ui.line((x, y + 3), (x + 5, y - 2), "text", 2)
        if self.play_mode == "custom":
            self.draw_custom(w, h)
            return
        self.draw_party(w, h)
        ui.button(pygame.Rect(w // 2 - 170, h - 148, 340, 36),
                  f"Map  /  {self.map_names[a.map]}  [M]", "choose_map", size="s")
        ui.button(pygame.Rect(w // 2 - 170, h - 96, 340, 64), "Play vs bots", "start", primary=True, size="l")
        ui.text("Enter to start", (w // 2, h - 24), "xs", "text", "center")

    def draw_mode_select(self, w: int, h: int) -> None:
        ui = self.ui
        ui.shade()
        panel = pygame.Rect(0, 0, min(780, w - 24), min(384, h - 24))
        panel.center = (w // 2, h // 2)
        ui.panel(panel, "bg", edge="top", edge_col="accent")
        ui.text("Select mode", (panel.x + 28, panel.y + 24), "l", bold=True, upper=True, kind="title")
        ui.button(pygame.Rect(panel.right - 124, panel.y + 21, 96, 38), "Back", "mode_back", size="s")
        card_w, card_h, gap = (panel.w - 72) // 2, (panel.h - 116) // 2, 16
        mouse = pygame.mouse.get_pos()
        for i, (key, label, description) in enumerate(PLAY_MODES):
            rect = pygame.Rect(panel.x + 28 + (i % 2) * (card_w + gap),
                               panel.y + 78 + (i // 2) * (card_h + gap), card_w, card_h)
            selected = key == self.play_mode
            ui.skin("menu/tab_active" if selected else "menu/button_hover" if rect.collidepoint(mouse) else "menu/tab", rect)
            if i == self.mode_focus:
                ui.outline(rect, "text", 2)
            ui.text(label, (rect.x + 18, rect.y + 19), "m", bold=True, upper=True, kind="title")
            for row, line in enumerate(ui.wrap(description, "s", card_w - 36)):
                ui.text(line, (rect.x + 18, rect.y + 55 + row * 19), "s", "muted")
            ui.area(rect, f"mode:{key}")
        ui.text("Arrows / Tab to focus   Enter to select   Esc to go back",
                (panel.centerx, panel.bottom - 26), "xs", "muted", "center")

    def draw_party(self, w: int, h: int) -> None:
        """Five player-card slots like a party: you in the middle, bots of your team around you; click + to add a bot,
        a bot card to remove it (team size)."""
        ui, a, s = self.ui, self.args, self.screen
        card_w, card_h, gap = min(150, (w - 96) // 5), min(300, h - 322), 12
        slots = 5
        left = w // 2 - (slots * card_w + (slots - 1) * gap) // 2
        mates = a.team_size - 1
        bot_slots = [1, 3, 0, 4][:mates]
        for i in range(slots):
            r = pygame.Rect(left + i * (card_w + gap), 148, card_w, card_h)
            if i == 2:
                if not ui.sprite("menu/party_self", r):
                    ui.panel(r, "panel", edge="top")
                art_h = max(1, min(240, card_h - 52))
                art = self.bank.scaled(f"agents/{a.agent}/{a.agent}_select.png", (max(1, art_h // 2), art_h))
                if art is not None:
                    s.blit(art, art.get_rect(midbottom=(r.centerx, r.bottom - 44)))
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
        width = min(440, (w - 60) // 2)
        top = min(160, h - 300)
        host = pygame.Rect(w // 2 - width - 12, top, width, 280)
        ui.panel(host, "panel", edge="top")
        ui.text("Host", (host.x + 24, host.y + 20), "l", "text", upper=True, bold=True, kind="title")
        mode = next(name for key, name, _ in PLAY_MODES if key == self.args.mode)
        ui.text(f"Starting mode: {mode}", (host.x + 24, host.y + 66), "s", "muted")
        ui.button(pygame.Rect(host.x + 24, host.y + 110, width - 48, 48), "Host party by IP", "host", primary=True)
        ui.button(pygame.Rect(host.x + 24, host.y + 170, width - 48, 48), "Host online (join code)", "host_online")
        ui.button(pygame.Rect(host.x + 24, host.y + 228, host.w - 48, 36),
                  f"Map  /  {self.map_names[self.args.map]}  [M]", "choose_map", size="s")
        join = pygame.Rect(w // 2 + 12, top, width, 280)
        ui.panel(join, "panel", edge="top")
        ui.text("Join", (join.x + 24, join.y + 20), "l", "text", upper=True, bold=True, kind="title")
        join_width = min(108, width // 5)
        field = pygame.Rect(join.x + 24, join.y + 70, width - 60 - join_width, 44)
        ui.textfield(field, self.typing)
        caret = self.address_caret if self.typing and self.address_caret is not None else len(self.address)
        start = min(self.address_visible_start, caret) if self.address_drag_field is not None else 0
        end = len(self.address)
        available = field.w - 26
        while start < caret and ui.size(self.address[start:caret], "s")[0] > available:
            start += 1
        while end > caret and ui.size(self.address[start:end], "s")[0] > available:
            end -= 1
        self.address_visible_start = start
        shown = self.address[start:end]
        if self.typing:
            selected_start, selected_end = self.address_selection()
            selected_start, selected_end = max(start, selected_start), min(end, selected_end)
            if selected_start < selected_end:
                left = ui.size(self.address[start:selected_start], "s")[0]
                right = ui.size(self.address[start:selected_end], "s")[0]
                ui.fill(pygame.Rect(field.x + 12 + left, field.y + 10, right - left, 24), "#365868")
        placeholder = "IP or code" if field.w < 220 else "IP address or join code"
        ui.text(shown or ("" if self.typing else placeholder), (field.x + 12, field.y + 14),
                "s", "text" if self.address else "muted")
        if self.typing:
            x = field.x + 12 + ui.size(self.address[start:caret], "s")[0]
            ui.line((x, field.y + 11), (x, field.bottom - 11), "text")
        ui.area(field, "field:address")
        address_error = self.join_address_error()
        join_pending = self.join_cleanup_pending()
        if address_error:
            ui.text(address_error, (field.x, field.bottom + 2), "xs", "enemy")
        ui.button(pygame.Rect(field.right + 12, field.y, join_width, 44), "Join", "join",
                  primary=True, enabled=bool(self.address) and not address_error and not join_pending)
        ui.button(pygame.Rect(join.x + 24, join.y + 130, 220, 40), "Find LAN match", "find",
                  enabled=self.lan_scan is None, size="s")
        first = self.lan_page * LAN_PAGE_SIZE
        last = min(first + LAN_PAGE_SIZE, len(self.found))
        hovered_name = focused_name = ""
        hovered_result = focused_result = False
        mouse = pygame.mouse.get_pos()
        for row, i in enumerate(range(first, last)):
            address, port, host_name = self.found[i]
            endpoint = f"{address}:{port}"
            rect = pygame.Rect(join.x + 24, join.y + 175 + row * 26, width - 100, 24)
            name = host_name
            if ui.size(f"{name}  {endpoint}", "xs", upper=True)[0] > rect.w - 16:
                while name and ui.size(f"{name}…  {endpoint}", "xs", upper=True)[0] > rect.w - 16:
                    name = name[:-1]
                name = name.rstrip() + "…" if name else ""
            label = f"{name}  {endpoint}" if name else endpoint
            action = f"lan:{i}"
            ui.button(rect, label, action, enabled=not join_pending, size="xs")
            edit = pygame.Rect(rect.right + 4, rect.y, 48, rect.h)
            edit_action = f"lan_edit:{i}"
            ui.button(edit, "Edit", edit_action, size="xs")
            row_focused = self.custom_focus in (action, edit_action)
            hovered_result |= rect.collidepoint(mouse)
            focused_result |= row_focused
            if name != host_name:
                if rect.collidepoint(mouse):
                    hovered_name = host_name
                if row_focused:
                    focused_name = host_name
        if len(self.found) > LAN_PAGE_SIZE:
            y = join.y + 254
            ui.button(pygame.Rect(join.x + 24, y, 30, 22), "<", "lan_page:-1", enabled=first > 0, size="xs")
            ui.text(f"{first + 1}–{last} of {len(self.found)} · PgUp / PgDn",
                    (join.centerx, y + 3), "xs", "muted", "center")
            ui.button(pygame.Rect(join.right - 54, y, 30, 22), ">", "lan_page:1",
                      enabled=last < len(self.found), size="xs")
        if self.custom_focus is not None:
            hit = next((hit for hit in ui.hits if hit.enabled and hit.action == self.custom_focus), None)
            if hit is not None:
                ui.outline(hit.rect.inflate(4, 4), "text", 2)
        hint = "Tab / Shift+Tab to focus   Enter to activate"
        if hovered_result or focused_result:
            hint = "Right-click / Ctrl+C: copy"
            if self.custom_focus and self.custom_focus.startswith("lan_edit:"):
                hint = "Enter: edit address   " + hint
            elif not join_pending:
                hint = "Enter: join   F2: edit address   " + hint
        ui.text(hint, (w // 2, host.bottom + 5), "xs", "text", "center")
        if full_name := hovered_name or focused_name:
            ui.text(full_name, (w // 2, top - 19), "xs", "text", "center", bold=True)

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







    @staticmethod
    def ordered_agents(agents: dict[str, dict]) -> list[tuple[str, dict]]:
        return sorted(agents.items(), key=lambda item: (
            ROLE_ORDER.index(item[1]["role"]) if item[1]["role"] in ROLE_ORDER else len(ROLE_ORDER),
            item[1]["name"],
        ))

    def filtered_agents(self, agents: dict[str, dict] | None = None) -> list[tuple[str, dict]]:
        query = self.agent_query.strip().casefold()
        ordered = self.ordered_agents(self.agents() if agents is None else agents)
        return [(key, info) for key, info in ordered if query in info["name"].casefold()
                and (not self.agent_role or info["role"] == AGENT_ROLES[self.agent_role])]

    def cycle_agent_role(self, step: int) -> None:
        self.agent_role = (self.agent_role + step) % len(AGENT_ROLES)
        self.set_agent_query(self.agent_query)

    def set_agent_query(self, query: str) -> None:
        self.agent_query = query
        matches = self.filtered_agents()
        if not matches:
            self.agent_keyboard_focus = False
        if matches and not any(key == self.agent_view for key, _ in matches):
            self.agent_view = matches[0][0]

    @staticmethod
    def agent_grid_metrics(w: int, h: int) -> tuple[int, int, int, int]:
        x, y, cell = (24, 130, 42) if w < 1000 or h < 580 else (40, 170, 64)
        rows = max(1, (h - y - 64) // (cell + 8))
        return x, y, cell, rows * AGENT_COLUMNS

    def turn_agent_page(self, step: int) -> None:
        roster = [key for key, _ in self.filtered_agents()]
        if not roster:
            return
        *_, page_size = self.agent_grid_metrics(*self.screen.get_size())
        index = roster.index(self.agent_view) if self.agent_view in roster else 0
        page = max(0, min((len(roster) - 1) // page_size, index // page_size + step))
        if page != index // page_size:
            self.agent_view = roster[min(len(roster) - 1, page * page_size + index % page_size)]

    def handle_agent_grid_key(self, key: int) -> bool:
        if key == pygame.K_ESCAPE and self.agent_keyboard_focus:
            self.agent_keyboard_focus = False
            return True
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and self.agent_keyboard_focus:
            self.activate("pick_agent")
            return True
        if key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
            self.turn_agent_page(-1 if key == pygame.K_PAGEUP else 1)
            self.agent_keyboard_focus = True
            return True
        steps = {pygame.K_LEFT: -1, pygame.K_RIGHT: 1, pygame.K_UP: -AGENT_COLUMNS,
                 pygame.K_DOWN: AGENT_COLUMNS, pygame.K_TAB: 0}
        if key not in steps and key not in (pygame.K_HOME, pygame.K_END):
            return False
        agents = [agent for agent, _ in self.filtered_agents()]
        if not agents:
            return False
        index = agents.index(self.agent_view) if self.agent_view in agents else 0
        if key == pygame.K_HOME:
            index = 0
        elif key == pygame.K_END:
            index = len(agents) - 1
        else:
            index = max(0, min(len(agents) - 1, index + steps[key]))
        self.agent_view = agents[index]
        self.agent_keyboard_focus = True
        return True

    def draw_agents(self, w: int, h: int) -> None:
        ui = self.ui
        agents = self.agents()
        ui.text("Agents", (40, 84), "xl", "text", upper=True, bold=True, kind="title")
        compact = w < 1000 or h < 580
        x0, y0, cell, page_size = self.agent_grid_metrics(w, h)
        ordered = self.filtered_agents(agents)
        field = pygame.Rect(x0 + 185, 82, 220 if not compact else 144, 29)
        ui.textfield(field, self.agent_searching)
        shown = self.agent_query + ("_" if self.agent_searching else "")
        while shown and ui.size(shown, "xs")[0] > field.w - 16:
            shown = shown[1:]
        ui.text(shown or "Search [/]", (field.x + 8, field.y + 8), "xs", "text")
        ui.area(field, "agent_search")
        if self.agent_query:
            ui.button(pygame.Rect(field.right + 5, field.y, 26, field.h), "X", "agent_search_clear", size="xs")
        role = pygame.Rect(field.right + 36, field.y, 146, field.h)
        ui.button(role,
                  f"{AGENT_ROLES[self.agent_role]} [Ctrl+R]", "agent_role", selected=self.agent_role != 0, size="xs")
        if self.agent_query or self.agent_role:
            ui.button(pygame.Rect(role.right + 8, field.y, 184, field.h),
                      "Reset [Ctrl+Del]", "agent_filters_reset", size="xs")
        if not ordered:
            ui.text("No agents found", (x0, y0 + 12), "s", "muted")
            return
        index = next((i for i, (key, _) in enumerate(ordered) if key == self.agent_view), 0)
        page = index // page_size
        last_page = max(0, (len(ordered) - 1) // page_size)
        for i, (key, info) in enumerate(ordered[page * page_size:(page + 1) * page_size]):
            r = pygame.Rect(x0 + (i % AGENT_COLUMNS) * (cell + 8), y0 + (i // AGENT_COLUMNS) * (cell + 8), cell, cell)
            chosen, viewing = key == self.args.agent, key == self.agent_view
            ui.fill(r, "panel_light" if viewing else "panel")
            pic = self.bank.scaled(f"agents/{key}/{key}_portrait.png", (cell - 8, cell - 8))
            if pic is not None:
                self.screen.blit(pic, (r.x + 4, r.y + 4))
            else:
                ui.text(info["name"][:2], (r.centerx, r.y + 20), "m", "text", "center", upper=True)
            ui.outline(r, "accent" if viewing else "gold" if chosen else "line", 2 if viewing or chosen else 1)
            if viewing and self.agent_keyboard_focus:
                ui.outline(r.inflate(4, 4), "text", 2)
            ui.area(r, f"agent:{key}")
        if last_page:
            y = y0 + (page_size // AGENT_COLUMNS) * (cell + 8)
            ui.button(pygame.Rect(x0, y, 66, 26), "Previous", "agent_page:-1", enabled=page > 0, size="xs")
            first = page * page_size + 1
            last = min(first + page_size - 1, len(ordered))
            center = x0 + AGENT_COLUMNS * (cell + 8) // 2 - 4
            ui.text(f"{first}–{last} of {len(ordered)}", (center, y + 7), "xs", "text", "center")
            ui.text("PgUp / PgDn", (center, y + 29), "xs", "muted", "center")
            ui.button(pygame.Rect(x0 + AGENT_COLUMNS * (cell + 8) - 74, y, 66, 26),
                      "Next", "agent_page:1", enabled=page < last_page, size="xs")
        info = agents.get(self.agent_view)
        if info is None:
            return
        hint = "Arrows: browse   F1: details   Enter: select"
        if self.agent_query or self.agent_role:
            hint = f"{len(ordered)}/{len(agents)} agents   F1: details   Enter: select"
        ui.text(hint, (x0, y0 - 19), "xs", "text")
        px = x0 + AGENT_COLUMNS * (cell + 8) + 30
        panel_top = 124 if compact else 150
        ui.panel(pygame.Rect(px - 16, panel_top, w - px - 8, h - panel_top - 18), "panel")
        art_size = (52, 104) if compact else (120, 240)
        big = self.bank.scaled(f"agents/{self.agent_view}/{self.agent_view}_select.png", art_size)
        if big is not None:
            self.screen.blit(big, (px, panel_top + 20))
            px += art_size[0] + (14 if compact else 30)
        ui.text(info["name"], (px, panel_top + 10), "l" if compact else "xl", "text", upper=True, bold=True, kind="title")
        role = info["role"]
        role_y = panel_top + (44 if compact else 63)
        has_icon = role in ROLE_ORDER and ui.sprite(f"icons/role_{role.lower()}", pygame.Rect(px, role_y, 24, 24))
        ui.text(role, (px + (30 if has_icon else 2), role_y + 1), "m", "accent", upper=True, bold=True)
        y = role_y + 33
        width = w - px - 40
        if passive := AGENT_PASSIVES.get(self.agent_view):
            title, description = passive
            ui.text(f"Passive · {title}", (px, y), "s", "ally", bold=True)
            lines = ui.wrap(description.format(jump=self.settings["keys"]["jump"].upper()), "xs", width)
            for j, line in enumerate(lines):
                ui.text(line, (px, y + 18 + j * 15), "xs", "text")
            y += 25 + 15 * len(lines)
        if compact:
            for slot in ("C", "Q", "E", "X"):
                ab = info["abilities"][slot]
                ui.button(pygame.Rect(px, y, width, 19), f"{slot}  {ab['name']}",
                          f"agent_ability:{slot}", size="xs")
                y += 21
        else:
            self.draw_agent_ability_details(info, px, y, width)
        chosen = self.agent_view == self.args.agent
        ui.button(pygame.Rect(w - 300, h - (56 if compact else 100), 260, 34 if compact else 56),
                  "Selected" if chosen else "Select", "pick_agent", primary=not chosen, enabled=not chosen)

    def draw_agent_ability_details(self, info: dict, px: int, y: int, width: int) -> None:
        ui = self.ui
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

    def draw_agent_ability_dialog(self, w: int) -> None:
        info = self.agents().get(self.agent_view)
        if info is None:
            return
        slot = self.agent_ability_slot
        ability = info["abilities"][slot]
        body = f"{info['name']} · {slot} · {cost_text(slot, ability)}\n\n{describe(ability)}"
        self.ui.dialog(ability["name"], body, [("Close [Esc]", "agent_ability_close", False)], width=min(620, w - 32))


