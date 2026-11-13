"""The game client: input, simulation step (local, host or client), composed from the drawing and HUD parts."""
from __future__ import annotations

from concurrent.futures import Future, wait

import user_settings

from client.common import *  # noqa: F403
from client.connection import discard_connection, run_network_task
from gameplay.geometry import MAX_DRONE_PITCH
from client.events import EventsMixin
from client.characters import CharactersMixin
from client.world_view import WorldViewMixin
from client.lobby import LobbyMixin
from client.hud import HudMixin
from client.minimap import MinimapMixin
from client.buy import BuyMixin
from client.scoreboard import ScoreboardMixin
from client.overlays import NO_KEYS, OverlaysMixin
from client.ui import Ui
from gameplay.match import DEFAULT_AGENT, SLOTS, playable_agents
from gameplay.net import validate_snapshot_agents
from gameplay.world import PLAYABLE_MAP_KEYS, load_playable_map


class Game(OverlaysMixin, EventsMixin, CharactersMixin, WorldViewMixin, LobbyMixin, HudMixin, MinimapMixin, BuyMixin, ScoreboardMixin):
    def __init__(self, args: argparse.Namespace, *, joined_client: Client | None = None) -> None:
        self.practice = bool(getattr(args, "practice", False)) and not (args.join or args.host)
        if not args.join:
            world = load_playable_map("range" if self.practice else args.map)
        pygame.init()
        self.screen = display_mode(bool(getattr(args, "fullscreen", False)))
        pygame.display.set_caption("Val2d")
        self.w, self.h = self.screen.get_size()
        self.scale = self.w / VIEW_METERS
        try:
            self.font = pygame.font.Font(str(FONT_PATH), 16)  # native size of the pixel font
            self.big = pygame.font.Font(str(FONT_PATH), 16)   # enlarged x2 by pixel_text
        except (OSError, FileNotFoundError):
            warnings.warn("Font fixed_sys.ttf missing; using the default font.")
            self.font = pygame.font.Font(None, 22)
            self.big = pygame.font.Font(None, 44)
        base = load_config()
        from dataclasses import replace
        lobby = replace(base.lobby, all_around_sight=args.all_around or base.lobby.all_around_sight,  # lobby defaults
                        sound_rings=args.sound_rings or base.lobby.sound_rings, win_rounds=args.rounds,
                        team_size=args.team_size)
        cfg = type(base)(hit_zones=base.hit_zones, lobby=lobby, player=base.player)
        self.team_size = args.team_size
        saved = user_settings.load()
        self.weapon_skins = saved["weapon_skins"]
        self.mode = "local"
        self.dummy_moves: dict[int, float] = {}
        self.stats = {"shots": 0, "hits": 0, "heads": 0, "kills": 0}
        self.session: HostSession | None = None
        self.client: Client | None = None
        self.status = ""
        self.rejoin_error = ""
        self.rejoin_detail_lines: list[str] = []
        self.rejoin_detail_text = ""
        self.rejoin_detail_copy_status = ""
        self.rejoin_detail_offset = 0
        self.rejoin_detail_width = 0
        self.rejoin_detail_focus = "rejoin_details_close"
        self.rejoin_details_focused = False
        self.rejoin_attempt: Future[Client] | None = None
        self.cancelled_rejoin: Future[None] | None = None
        if args.join:
            self.mode = "client"
            self.join_target, self.join_name, self.join_agent = args.join, args.name, args.agent
            self.client = joined_client or NetClient(args.join, args.name, args.agent, weapon_skins=self.weapon_skins)
            try:
                world = load_playable_map(self.client.map_key)
            except (OSError, ValueError):
                self.client.close()
                raise
            if saved["last_join"] != args.join:
                saved["last_join"] = args.join
                user_settings.save(saved)
        self.match = Match(world, cfg, agent_roster=playable_agents())
        if self.client is not None:
            self.me = self.client.pid
            self.net_generation = self.client.generation
            self.restore_spike_audio = True
        elif args.host:
            self.mode = "host"
            online = bool(getattr(args, "online", False))
            self.session = HostSession(self.match, args.name, None if online else args.port,
                                       mode="internet" if online else "lan")
            self.me = self.match.add_player(args.name, 0, args.agent, weapon_skins=self.weapon_skins).pid
        elif self.practice:
            self.me = self.match.add_player("You", 0, args.agent, weapon_skins=self.weapon_skins).pid
            for i, (pos, move) in enumerate(self.match.world.practice_targets):
                d = self.match.add_player(f"Target {i + 1}", 1, args.agent, is_bot=True)
                d.dummy, d.home = True, pos
                self.dummy_moves[d.pid] = move
        else:
            self.me = self.match.add_player("You", 0, args.agent, weapon_skins=self.weapon_skins).pid
            own_agent = self.match.players[self.me].agent
            others = [a for a in self.match.agents if a != own_agent] or [own_agent]
            for i in range(args.team_size - 1):
                self.match.add_player(f"Bot {i + 1}", 0, others[i % len(others)], is_bot=True)
            for i in range(args.team_size):
                self.match.add_player(f"Enemy {i + 1}", 1, list(self.match.agents)[i % len(self.match.agents)], is_bot=True)
        self.match.set_mode(str(getattr(args, "mode", "standard")))
        self.bots = BotDirector(self.match)
        self.bank = SpriteBank()
        self.chars = CharacterSprites(self.bank)
        self.map_surface = build_map_surface(self.match.world, self.bank, self.scale)
        self.map_cache: dict[float, pygame.Surface | None] = {round(self.scale, 3): self.map_surface}
        self._crop: pygame.Surface | None = None
        self._minimap_static: pygame.Surface | None = None
        self._tactical_static: tuple[float, pygame.Surface] | None = None
        self.local_facing = 0.0
        self.seen_round = -1
        self.spectate_index = 0
        self.keys = key_codes(dict(getattr(args, "keys", saved["keys"])))
        self.crosshair = dict(getattr(args, "crosshair", {k: saved[k] for k in
                                                          ("crosshair_color", "crosshair_size", "crosshair_gap", "crosshair_dot")}))
        self.ability_keys = {self.keys["ability_c"]: "C", self.keys["ability_q"]: "Q", self.keys["ability_e"]: "E",
                             self.keys["ability_x"]: "X"}
        self.aiming: str | None = None      # ability in hand (preview shown), cast with a click
        self.aim_ready_at = 0
        self.aim_alt = False
        self.shadow_view = True
        self.shadow_depth = 8.0
        self.shadow_lift = 0.0
        self.charge_started: int | None = None
        self.bounces = 0
        self.multi_points: list[tuple[float, float]] = []  # points marked for a multi-placement ability
        self.swallow_buttons: set[int] = set()  # mouse buttons that cast an ability: no shot until released
        self._next_beep = 0.0
        self._last_phase = ""
        self.server_pos: dict[int, Vec] = {}  # client: host positions, smoothed towards each frame
        self.ui = UiState()
        self.sound = Sound()
        self.cursor_depth = 8.0
        self.drone_pitch = 0.0
        self._requested_slot: str | None = None
        self._switched_at = -9.0
        self.sens = float(getattr(args, "sensitivity", base.player.sensitivity))
        self.camera_push = float(getattr(args, "camera_push", base.player.camera_push))
        self.sound.volume = float(getattr(args, "volume", 0.8))
        self.clock = pygame.time.Clock()
        self.grab(False)
        self.agent_cards: list[tuple[pygame.Rect, str]] = []
        self.kit = Ui(self.screen, self.bank)
        self.overlay = ""          # "", pause, leave or quit
        self.quit_program = False  # True: the player chose to quit the whole game, not just the match
        try:
            self.help_key = pygame.key.key_code(str(HUD["help_key"]))
        except (ValueError, pygame.error):
            warnings.warn(f"Unknown help key {HUD['help_key']!r}; F1 used.")
            self.help_key = pygame.K_F1
        self.help_held = False
        self.zoom_level = 0      # current zoom step of the own weapon (0 = none)
        self.scoped = False      # sniper scope view
        self._prev_alt = False
        self._zoom_weapon = ""
        self._ult_was_ready = True
        self.recorded = False  # the finished match went into the match history  # no ready sound for points carried into the match

    def grab(self, on: bool) -> None:
        self.grabbed = on
        pygame.event.set_grab(on)
        pygame.mouse.set_visible(not on)
        pygame.mouse.get_rel()

    def move_cursor(self, me: PlayerState, dy: float = 0.0) -> None:
        """Clamp the virtual cursor itself, so reversing at the edge responds immediately."""
        pull = self.camera_aim_pull(me)
        origin_y = self.h * (0.5 + self.camera_push * 0.5)
        pixels_per_meter = self.scale * (1 - pull)
        if pull == 1:  # the scope follows the cursor; use the unzoomed view to bound its travel
            pixels_per_meter = self.w / VIEW_METERS
        else:
            origin_y += (self.h / 2 - origin_y) * pull
        max_depth = (origin_y - 1) / pixels_per_meter
        self.cursor_depth = min(max(0.5, self.cursor_depth - dy * 0.03), max_depth)

    def select_weapon(self, cmd: Command, slot: str) -> None:
        cmd.equipment_actions.append(slot)
        self.set_aim(None)
        self._switched_at = self.match.time
        self._requested_slot = cmd.slot = slot

    def scroll_weapons(self, me: PlayerState, cmd: Command, scroll: int) -> None:
        slots = [slot for slot in SLOTS if slot in me.weapons]
        if not slots or not scroll:
            return
        selected = cmd.slot or self._requested_slot
        if selected not in slots:
            selected = me.slot
        index = slots.index(selected) if selected in slots else 0
        self.select_weapon(cmd, slots[(index - scroll) % len(slots)])

    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(120) / 1000.0
            cmd = Command()
            if getattr(self, "_toggle_dm_ghost", False):
                cmd.buy.append("tdm:toggle_ghost")
                self._toggle_dm_ghost = False
            me = self.match.players.get(self.me)
            if me is None:  # client before the first snapshot
                me = PlayerState(pid=self.me, name="", team=0, agent=DEFAULT_AGENT)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:  # window closed or Alt+F4: ask; a second time quits at once
                    if self.overlay == "quit":
                        self.quit_program, running = True, False
                    else:
                        self._from_pause = self.overlay == "pause"
                        self.open_overlay("quit")
                    continue
                if self.overlay:
                    if self.overlay_event(ev) in ("leave", "quit"):
                        running = False
                    continue
                if self.rejoin_detail_lines:
                    self.handle_rejoin_details(ev)
                    continue
                if self.rejoin_attempt is not None:
                    if (ev.type == pygame.KEYDOWN and not getattr(ev, "repeat", False)
                            and ev.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
                            or ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                            and (hit := self.kit.hit_at(ev.pos)) and hit.action == "cancel_rejoin"):
                        self.cancel_rejoin()
                        break
                    continue
                if self.kit.modal_from == 0 and self.rejoin_details_event(ev):
                    continue
                if self.scoreboard_name_event(ev) or self.round_history_event(ev):
                    continue
                if (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
                        and self.client is not None and not self.client.connected
                        and not (self.agent_abilities_open and self.match.phase == "lobby")):
                    if getattr(self.client, "party_closed", False) or (
                            self.match.phase == "over" and getattr(ev, "mod", 0) & pygame.KMOD_SHIFT):
                        running = False
                    else:
                        self.start_rejoin()
                    continue
                if ev.type == pygame.KEYDOWN and self.party_map_key(ev.key):
                    continue
                if ev.type == pygame.KEYDOWN and self.lobby_abilities_key(ev.key):
                    continue
                if ev.type == pygame.KEYDOWN and self.lobby_rule_key(ev.key, getattr(ev, "mod", 0)):
                    continue
                if ev.type == pygame.KEYDOWN and self.lobby_agent_search_key(ev):
                    continue
                if ev.type == pygame.KEYDOWN and self.party_mode_key(ev.key, getattr(ev, "mod", 0)):
                    continue
                if ev.type == pygame.KEYDOWN and self.party_copy_key(ev.key, getattr(ev, "mod", 0)):
                    continue
                if ev.type == pygame.KEYDOWN and self.party_team_key(ev.key):
                    continue
                if ev.type == pygame.KEYDOWN and self.lobby_agent_key(ev.key):
                    continue
                if ev.type == pygame.KEYDOWN and self.buy_request_key(me, ev.key, getattr(ev, "mod", 0), cmd):
                    continue
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    if self.ui.buy_open:
                        self.ui.buy_open = False
                    elif self.aiming:
                        self.set_aim(None)
                    else:
                        self.open_overlay("pause")
                elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.match.phase == "over":
                    if self.session:
                        if getattr(ev, "mod", 0) & pygame.KMOD_SHIFT:
                            self.session.net.announce_party_closed()
                            running = False
                        else:
                            self.return_party()
                    elif self.client is None or self.client.connected:
                        running = False
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.screen_button(ev.pos) == "to_menu":
                    if self.session and self.match.phase == "over":
                        self.session.net.announce_party_closed()
                    running = False
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.screen_button(ev.pos) == "party":
                    self.return_party()
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.screen_button(ev.pos) == "rejoin":
                    self.start_rejoin()
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_RETURN and self.match.phase == "lobby":
                        self.start_from_lobby()
                    elif ev.key == self.keys["buy"]:
                        if (not self.ui.buy_open and self.match.deathmatch_stage_equip_left(me)
                                and not self.match.can_select_deathmatch_loadout(me)):
                            cmd.buy.append(f"tdm:equip:{self.match.dm_stage}")
                            continue
                        if (self.match.mode == "deathmatch" and not self.ui.buy_open
                                and not self.match.can_select_deathmatch_loadout(me)):
                            continue
                        self.set_aim(None)
                        self.ui.buy_open = not self.ui.buy_open
                        self.request_focus = None
                        self.grab(not self.ui.buy_open)
                    elif ev.key in self.ability_keys and not self.ui.buy_open:
                        slot = self.ability_keys[ev.key]
                        if not me.alive and not self.match.can_cast_dead(me, slot):
                            continue
                        if self.aiming == slot:
                            shadow = self.shadow_ability(me)
                            if shadow:
                                self.cast_shadow(me, cmd, slot, shadow)
                            else:
                                self.set_aim(None)
                        elif self.needs_aim(me, slot) and me.channel_until <= self.match.time:
                            self.set_aim(slot)
                            self.sound.play("ability_equip", gain=0.5)
                        else:
                            self.set_aim(None)
                            cmd.ability = slot
                    elif ev.key in (self.keys["primary"], self.keys["sidearm"], self.keys["melee"]):
                        self.select_weapon(cmd, next(slot for slot in SLOTS if self.keys[slot] == ev.key))
                    elif ev.key == self.keys["spike"] and not self.ui.buy_open and me.alive \
                            and self.match.spike_carrier == me.pid:
                        self.set_aim(None)
                        cmd.equipment_actions.append("spike")
                        cmd.slot = "spike"
                    elif ev.key == self.keys["reload"]:
                        if self.shadow_ability(me):
                            self.shadow_view = not self.shadow_view
                        else:
                            cmd.reload = True
                            cmd.equipment_actions.append("reload")
                    elif ev.key == self.keys["drop"]:
                        if self.aiming is None:
                            cmd.drop = True
                            cmd.equipment_actions.append("drop")
                elif ev.type == pygame.MOUSEWHEEL and me.alive and not self.ui.buy_open \
                        and not self.tactical_ability(me) and self.match.phase in ("buy", "live", "planted"):
                    if (shadow := self.shadow_ability(me)) and shadow.get("place", {}).get("settle_on_floor"):
                        if ev.y and pygame.key.get_mods() & pygame.KMOD_CTRL:
                            limit = float(shadow["place"].get("raised_target_lift", 0))
                            self.shadow_lift = max(0.0, min(limit, self.shadow_lift + ev.y * 0.25))
                        elif ev.y:
                            self.aim_alt = ev.y < 0
                    else:
                        self.scroll_weapons(me, cmd, ev.y)
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button in (1, 3) and self.aiming \
                        and (me.alive or self.match.can_cast_dead(me, self.aiming)) \
                        and not self.ui.buy_open and self.match.phase in ("buy", "live", "planted"):
                    self.aim_click(me, cmd, ev.button, ev.pos)
                elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.charge_started is not None:
                    if self.aiming and me.alive and not self.ui.buy_open and self.match.phase in ("buy", "live", "planted"):
                        ab = self.match.agents[me.agent]["abilities"][self.aiming]
                        cmd.ability, cmd.facing = self.aiming, me.facing
                        cmd.cursor_depth = self.charged_depth(ab)
                        cmd.bounces = self.bounces
                        self.set_aim(None)
                    self.charge_started = None
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.match.phase == "lobby":
                    self.pick_agent_at(ev.pos)
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3 and self.match.phase == "lobby":
                    self.preview_agent_at(ev.pos)
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and not me.alive:
                    self.spectate_index += 1
                elif ev.type == pygame.MOUSEBUTTONDOWN and self.ui.buy_open and ev.button == 3:
                    item = self.buy_item_at(ev.pos)
                    if item in ("C", "Q", "E") and self.item_sellable(me, item):
                        cmd.buy.append(f"sell:{item}")
                    elif item and item in self.match.weapons and self.match.weapons[item].slot == "primary":
                        cmd.request_clicks.append(item)
                        self.sound.play("ui_click", gain=0.6)
                elif ev.type == pygame.MOUSEBUTTONDOWN and self.ui.buy_open and ev.button == 1 and self.request_at(ev.pos):
                    cmd.buy.append(self.request_at(ev.pos) or "")
                    self.sound.play("ui_buy", gain=0.6)
                elif ev.type == pygame.MOUSEBUTTONDOWN and self.ui.buy_open and ev.button == 1:
                    item = self.buy_item_at(ev.pos)
                    if item and (action := self.buy_action_at(me, item, ev.pos)):
                        cmd.buy.append(action)
                        self.sound.play("ui_buy", gain=0.6)
            keys = pygame.key.get_pressed()
            buttons = pygame.mouse.get_pressed()
            self.ui.show_scores = keys[self.keys["scoreboard"]]
            self.help_held = bool(keys[self.help_key]) and not self.overlay
            drone = self.piloted_owl_drone(me)
            if drone is None:
                self.drone_pitch = 0.0
            if not self.ui.buy_open and not self.overlay and self.grabbed and not self.tactical_ability(me):
                dx, dy = pygame.mouse.get_rel()
                self.local_facing = (self.local_facing + dx * self.sens) % 360
                me.facing = self.local_facing
                if drone is None:
                    self.move_cursor(me, dy)
                else:
                    self.drone_pitch = max(-MAX_DRONE_PITCH, min(MAX_DRONE_PITCH, self.drone_pitch - dy * self.sens))
                    cmd.drone_pitch = self.drone_pitch
                if shadow := self.shadow_ability(me):
                    self.shadow_depth = max(0.0, min(float(shadow["range"]),
                                                    self.shadow_depth + 25.0 * dt * (buttons[0] - buttons[2])))
                cmd.fire = buttons[0] and self.aiming is None and 1 not in self.swallow_buttons
                cmd.alt_fire = buttons[2] and self.aiming is None and 3 not in self.swallow_buttons
            self.swallow_buttons.intersection_update(b for b in (1, 3) if buttons[b - 1])
            if cmd.facing is None:
                cmd.facing = me.facing
                cmd.cursor_depth = self.cursor_depth
            kb = self.keys
            if self.overlay:  # menus open: stand still, keep facing
                keys = NO_KEYS
            cmd.move_y = (1 if keys[kb["forward"]] else 0) - (1 if keys[kb["back"]] else 0)
            cmd.move_x = (1 if keys[kb["right"]] else 0) - (1 if keys[kb["left"]] else 0)
            cmd.walk = keys[kb["walk"]]
            cmd.crouch = keys[kb["crouch"]]
            cmd.jump = keys[kb["jump"]]
            cmd.interact = keys[kb["interact"]]
            cmd.use_spike = bool(keys[kb["spike"]]) and not self.ui.buy_open and not self.tactical_ability(me)
            events = self.step(dt, cmd)
            me_now = self.match.players.get(self.me)
            if me_now is None or me_now.slot == self._requested_slot or self.match.time - self._switched_at > 0.5 \
                    or self.match.round_no != self.seen_round:
                self._requested_slot = None
            if me_now is None or not me_now.alive or self.match.phase not in ("buy", "live", "planted") \
                    or self.match.round_no != self.seen_round:
                self.set_aim(None)
            elif self.aiming == "X" and me_now.repeat_until \
                    and (not me_now.repeat_shots or me_now.repeat_until <= self.match.time) \
                    and not self.ability_ready(me_now, "X"):
                self.set_aim(None)
            if me_now is not None:
                self.apply_zoom(me_now, cmd.alt_fire and not self.ui.buy_open)
                if (self.ui.buy_open and self.match.mode == "deathmatch"
                        and not self.match.can_select_deathmatch_loadout(me_now)):
                    self.ui.buy_open = False
            needs_mouse = self.match.phase in ("lobby", "over") or self.ui.buy_open or bool(self.overlay) \
                or (me_now is not None and self.tactical_ability(me_now) is not None) \
                or (self.client is not None and not self.client.connected)
            if needs_mouse and self.grabbed:
                self.grab(False)  # buttons to click: show the pointer
            elif not needs_mouse and not self.grabbed:
                self.grab(True)
            if self.match.round_no != self.seen_round and self.seen_round > 0 and self.me in self.match.players:
                half = int(self.match._r["half_after"])
                if self.match.round_no == half + 1:
                    self.ui.banner, self.ui.banner_art = (self.match.time + 3, "Sides switched"), "switching_sides"
                elif self.match.round_no == 2 * half + 1:
                    self.ui.banner, self.ui.banner_art = (self.match.time + 3, "Overtime"), "overtime"
                elif self.match.mode != "deathmatch" and max(self.match.score) == self.match.win_rounds - 1:
                    self.ui.banner, self.ui.banner_art = (self.match.time + 3, "Match point"), ""
                elif half and self.match.round_no == half:
                    self.ui.banner, self.ui.banner_art = (self.match.time + 3, "Last round of the half"), ""
            if self.match.round_no != self.seen_round and self.me in self.match.players:
                self.seen_round = self.match.round_no  # new round: take the facing from the spawn
                self.local_facing = self.match.players[self.me].facing
            listener = self.match.players.get(self.me)
            spike_listener = self.view_player(listener) if listener is not None else None
            self.update_audio_perspective(spike_listener)
            self.handle_events(events, spike_listener=spike_listener)
            if listener is not None:
                self.audio_tick(listener, spike_listener=spike_listener)
            else:
                self.stop_ability_audio()
            if self.match.phase == "over" and not self.recorded and self.me in self.match.players:
                from client import history
                history.record(self.match, self.me, self.score_of)  # for the Career page
                self.recorded = True
            self.update_connection_status()
            self.finish_rejoin()
            self.draw()
            self.draw_overlay()
            if self.rejoin_detail_lines and not self.overlay:
                self.draw_rejoin_details()
            if self.rejoin_attempt is not None and not self.overlay:
                self.kit.connection_dialog("Reconnecting…", self.join_target, "cancel_rejoin")
            pygame.display.flip()
        self.cancel_rejoin()
        self.stop_ability_audio()
        if self.session:
            self.session.close()
        if self.client:
            self.client.close()

    def multi_target(self, me: PlayerState, ab: dict) -> Vec:
        """Map point under the cursor for multi-placement, within the ability's range (walls do not stop it)."""
        reach = min(self.cursor_depth, float(ab.get("range", self.cursor_depth)))
        return me.pos + heading(me.facing) * reach

    def set_aim(self, slot: str | None) -> None:
        self.aiming = slot
        me = self.match.players.get(self.me)
        ability = self.match.agents.get(me.agent, {}).get("abilities", {}).get(slot, {}) if me and slot else {}
        equip_ms = round(float(ability.get("aim_equip", 0.0)) * 1000)
        self.aim_ready_at = pygame.time.get_ticks() + equip_ms if equip_ms else 0
        self.aim_alt = False
        self.shadow_lift = 0.0
        self.shadow_depth = self.cursor_depth
        self.charge_started = None
        self.bounces = 0
        self.multi_points.clear()

    def charged_depth(self, ab: dict) -> float:
        fraction = 0.0
        if self.charge_started is not None:
            elapsed = (pygame.time.get_ticks() - self.charge_started) / 1000
            fraction = min(1.0, elapsed / float(ab["charge_time"]))
        nearest = float(ab["min_range"])
        return nearest + (float(ab["range"]) - nearest) * fraction

    def tactical_ability(self, me: PlayerState) -> dict | None:
        ab = self.match.agents.get(me.agent, {}).get("abilities", {}).get(self.aiming, {})
        return ab if ab.get("tactical") and not ab.get("shadow_targeting") else None

    def shadow_ability(self, me: PlayerState) -> dict | None:
        if self.aiming is None or me.pid != self.me or not me.alive:
            return None
        ab = self.match.agents.get(me.agent, {}).get("abilities", {}).get(self.aiming, {})
        return ab if ab.get("shadow_targeting") else None

    def shadow_target(self, me: PlayerState, ab: dict) -> Vec:
        aim = heading(me.facing)
        world = self.match.world
        limits = [self.shadow_depth, float(ab["range"])]
        for origin, direction, end in ((me.pos.x, aim.x, world.width), (me.pos.y, aim.y, world.height)):
            if abs(direction) > 1e-9:
                limits.append(((end if direction > 0 else 0) - origin) / direction)
        return me.pos + aim * max(0.0, min(limits))

    def cast_shadow(self, me: PlayerState, cmd: Command, slot: str, ab: dict) -> None:
        if pygame.time.get_ticks() < self.aim_ready_at or not self.ability_ready(me, slot):
            return
        target = self.shadow_target(me, ab)
        spec = {**ab, "under_deck": self.aim_alt, "target_lift": self.shadow_lift}
        if not self.match.valid_tactical_point(me, spec, target):
            return
        cmd.ability = slot
        cmd.ability_alt = self.aim_alt
        cmd.target_lift = self.shadow_lift
        cmd.points = [(target.x, target.y)]
        self.swallow_buttons.update((1, 3))
        self.set_aim(None)

    def aim_click(self, me: PlayerState, cmd: Command, button: int, mouse: tuple[int, int]) -> None:
        slot = self.aiming
        if slot is None:
            return
        self.swallow_buttons.add(button)
        ab = self.match.agents[me.agent]["abilities"][slot]
        if pygame.time.get_ticks() < self.aim_ready_at:
            return
        if ab.get("toggle_alt") and button == 3:
            self.aim_alt = not self.aim_alt
            self.sound.play("ui_click", gain=0.5)
            return
        if ab.get("shadow_targeting"):
            return
        if ab.get("charge_time"):
            if button == 3 and (limit := ab.get("max_bounces")):
                self.bounces = (self.bounces + 1) % (limit + 1)
            if button == 1 and self.ability_ready(me, slot):
                self.charge_started = pygame.time.get_ticks()
            return
        if ab.get("target") == "owl_drone_launch" and (button != 1 or not self.ability_ready(me, slot)):
            return
        if ab.get("target") in ("wall_exit", "owl_drone_launch"):
            from gameplay.kit.engine import resolve_target
            if resolve_target(self.match, me, ab) is None:
                return
        multi = int(ab.get("multi", 1)) > 1
        tactical = bool(ab.get("tactical"))
        if ab.get("astral_form") and not self.aim_alt:
            if button == 3:
                if self.ability_ready(me, "X"):
                    self.aim_alt = True
                return
            spot = self.tactical_point(mouse)
            if spot is not None:
                reclaim = any(e.owner == me.pid and e.props.get("sprite") == "astra_star"
                              and (e.pos - spot).length() < 1 for e in self.match.effects)
                if reclaim or me.charges.get("E", 0) > 0 or self.match.cheat("infinite_abilities"):
                    cmd.ability, cmd.points, cmd.ability_alt = slot, [(spot.x, spot.y)], reclaim
            return
        if ab.get("tactical_line"):
            if button == 3:
                if ab.get("astral_form") and not self.multi_points:
                    self.aim_alt = False
                self.multi_points.clear()
                return
            spot = self.tactical_point(mouse)
            if spot is None or not self.placement_limit(me, ab, slot):
                return
            if not self.multi_points:
                if self.match.valid_tactical_point(me, ab, spot):
                    self.multi_points.append((spot.x, spot.y))
                return
            if (spot - Vec(*self.multi_points[0])).length() < 0.25:
                return
            cmd.points = [self.multi_points[0], (spot.x, spot.y)]
        elif multi and button == 3:
            if not self.multi_points or (tactical and not all(
                self.match.valid_tactical_point(me, ab, Vec(*point)) for point in self.multi_points
            )):
                return
            cmd.points = list(self.multi_points)
        elif tactical or multi:
            if button != 1:
                return
            spot = self.tactical_point(mouse) if tactical else self.multi_target(me, ab)
            if spot is None:
                return
            if multi:
                if tactical:
                    for point in self.multi_points:
                        if (Vec(*point) - spot).length() < 0.75:
                            self.multi_points.remove(point)
                            return
            if tactical and not self.match.valid_tactical_point(me, ab, spot):
                return
            if multi:
                if len(self.multi_points) < self.placement_limit(me, ab, slot):
                    self.multi_points.append((spot.x, spot.y))
                    self.sound.play("ui_click", gain=0.5)
                return
            if self.placement_limit(me, ab, slot) == 0:
                return
            cmd.points = [(spot.x, spot.y)]
        elif button == 3 and not ab.get("alt"):
            return
        cmd.ability = slot
        cmd.ability_alt = self.aim_alt if ab.get("toggle_alt") else button == 3 and not multi
        cmd.facing, cmd.cursor_depth = me.facing, self.cursor_depth
        if not ab.get("repeat_shots"):
            self.set_aim(None)

    def screen_button(self, pos: tuple[int, int]) -> str | None:
        """Actions that can be used from the results screen or the disconnected overlay."""
        hit = self.kit.hit_at(pos)
        return hit.action if hit is not None and hit.action in ("party", "to_menu", "rejoin") else None

    def refresh_map_art(self) -> None:
        self.zoom_level, self.scoped = 0, False
        self.scale = self.w / VIEW_METERS
        self.map_surface = build_map_surface(self.match.world, self.bank, self.scale)
        self.map_cache = {round(self.scale, 3): self.map_surface}
        self._crop = self._minimap_static = self._tactical_static = None

    def reset_party_view(self) -> None:
        self.stop_ability_audio()
        for pid in list(self.ui.spike_sounds):
            self.stop_spike_sound(pid)
        self.ui = UiState()
        self.set_aim(None)
        self.swallow_buttons.clear()
        self.server_pos.clear()
        self.spectate_index, self.seen_round = 0, -1
        self._requested_slot, self._switched_at = None, -9.0
        self._next_beep, self._last_phase = 0.0, ""
        self._ult_was_ready = True
        self.stats = dict.fromkeys(self.stats, 0)
        self.recorded = False
        self.status = ""

    def return_party(self) -> None:
        if self.session and self.session.return_to_lobby():
            self.match = self.session.match
            self.bots = self.session.bots
            self.reset_party_view()

    def apply_zoom(self, me: PlayerState, holding_alt: bool) -> None:
        """Camera zoom while a zoom weapon's alternate fire is held; map image cached per zoom level."""
        d = self.match.weapons.get(me.weapon.key) if me.weapon else None
        if d is None or not me.alive or me.blades_equipped or me.reload_until > self.match.time or self.shadow_ability(me):
            level = 0
        elif self.mode == "client":  # the host decides as well; the own view follows the same rule at once
            level = d.zoom_after(getattr(self, "zoom_level", 0), holding_alt, getattr(self, "_prev_alt", False))
        else:
            level = me.zoom_level
        if self.mode == "client" and me.weapon and getattr(self, "_zoom_weapon", "") != me.weapon.key:
            level = 0
        self._prev_alt, self._zoom_weapon = holding_alt, me.weapon.key if me.weapon else ""
        levels = d.zoom_levels() if d else []
        self.zoom_level = level if levels else 0
        self.scoped = bool(self.zoom_level and d is not None and d.alt_get("scope"))
        factor = levels[self.zoom_level - 1] if self.zoom_level else 1.0
        self.scale = self.w / (VIEW_METERS / factor)  # the map image stays at the base scale; zoom crops and enlarges it
        self.move_cursor(me)

    def rejoin(self) -> None:
        """Reconnect synchronously for callers outside the game loop."""
        self.start_rejoin()
        if self.rejoin_attempt is not None:
            wait((self.rejoin_attempt,))
            self.finish_rejoin()

    def start_rejoin(self) -> None:
        """Start connecting without blocking the event loop."""
        old = self.client
        if old is None or self.rejoin_attempt is not None:
            return
        if self.rejoin_cleanup_pending():
            return
        target, name, agent = self.join_target, self.join_name, self.join_agent
        token, skins = old.token, dict(self.weapon_skins)
        self.rejoin_attempt = run_network_task(
            lambda: NetClient(target, name, agent, token=token, weapon_skins=skins)
        )

    def cancel_rejoin(self) -> None:
        attempt, self.rejoin_attempt = self.rejoin_attempt, None
        if attempt is not None:
            self.cancelled_rejoin = discard_connection(attempt)

    def rejoin_cleanup_pending(self) -> bool:
        return self.cancelled_rejoin is not None and not self.cancelled_rejoin.done()

    def draw_rejoin_details_button(self, rect: pygame.Rect, lines: list[str], width: int) -> None:
        if self.client and not self.client.connected and self.status.startswith("Rejoin failed:") and (
                len(lines) > 2 or any(self.kit.size(line, "s")[0] > width for line in lines)):
            self.kit.button(rect, "Details [F1]", "rejoin_details", size="xs")
            if self.rejoin_details_focused:
                self.kit.outline(rect.inflate(4, 4), "text", 2)

    def rejoin_details_event(self, ev: pygame.event.Event) -> bool:
        if not any(hit.action == "rejoin_details" for hit in self.kit.hits):
            self.rejoin_details_focused = False
            return False
        if ev.type == pygame.KEYDOWN:
            if (self.match.phase == "over" and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
                    and getattr(ev, "mod", 0) & pygame.KMOD_SHIFT):
                return False
            if ev.key == pygame.K_TAB:
                self.rejoin_details_focused = not self.rejoin_details_focused
                return True
            if ev.key != pygame.K_F1 and not (
                    self.rejoin_details_focused and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)):
                return False
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            hit = self.kit.hit_at(ev.pos)
            if hit is None or hit.action != "rejoin_details":
                self.rejoin_details_focused = False
                return False
        else:
            return False
        self.rejoin_details_focused = True
        self.rejoin_detail_text = self.status
        self.rejoin_detail_copy_status = ""
        self.rejoin_detail_offset = 0
        self.wrap_rejoin_details(min(860, self.kit.screen.get_width() - 48) - 48)
        self.rejoin_detail_focus = "rejoin_details_close"
        return True

    def wrap_rejoin_details(self, width: int) -> None:
        # The wrapper may move or discard whitespace at line boundaries.
        anchor = sum(len("".join(line.split())) for line in self.rejoin_detail_lines[:self.rejoin_detail_offset])
        self.rejoin_detail_width = width
        self.rejoin_detail_lines = self.kit.wrap(self.rejoin_detail_text, "s", width, break_words=True)
        self.rejoin_detail_offset = 0
        for line in self.rejoin_detail_lines[:-1]:
            length = len("".join(line.split()))
            if anchor == 0 or anchor < length:
                break
            anchor -= length
            self.rejoin_detail_offset += 1

    def rejoin_detail_page(self) -> int:
        height = min(500, self.kit.screen.get_height() - 48)
        return max(1, (height - 120) // (self.kit.size("Ag", "s")[1] + 4))

    def handle_rejoin_details(self, ev: pygame.event.Event) -> None:
        page = self.rejoin_detail_page()
        action = ""
        step = 0
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_TAB:
                actions = [hit.action for hit in self.kit.hits[self.kit.modal_from:]
                           if hit.enabled and hit.action.startswith("rejoin_details_")]
                if actions:
                    direction = -1 if getattr(ev, "mod", 0) & pygame.KMOD_SHIFT else 1
                    if self.rejoin_detail_focus in actions:
                        index = actions.index(self.rejoin_detail_focus) + direction
                    else:
                        index = -1 if direction < 0 else 0
                    self.rejoin_detail_focus = actions[index % len(actions)]
                return
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                action = self.rejoin_detail_focus
            elif ev.key in (pygame.K_ESCAPE, pygame.K_F1):
                action = "rejoin_details_close"
            elif ev.key == pygame.K_c and getattr(ev, "mod", 0) & pygame.KMOD_CTRL:
                action = "rejoin_details_copy"
            step = {pygame.K_UP: -1, pygame.K_DOWN: 1, pygame.K_PAGEUP: -page,
                    pygame.K_PAGEDOWN: page, pygame.K_HOME: -len(self.rejoin_detail_lines),
                    pygame.K_END: len(self.rejoin_detail_lines)}.get(ev.key, 0)
        elif ev.type == pygame.MOUSEWHEEL:
            step = -ev.y * 3
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and (hit := self.kit.hit_at(ev.pos)):
            action = hit.action
        if action == "rejoin_details_close":
            self.rejoin_detail_lines.clear()
            return
        if action == "rejoin_details_copy":
            try:
                pygame.scrap.put_text(self.rejoin_detail_text)
            except pygame.error:
                self.rejoin_detail_copy_status = "Clipboard unavailable"
            else:
                self.rejoin_detail_copy_status = "Error details copied"
            return
        step = {"rejoin_details_prev": -page, "rejoin_details_next": page}.get(action, step)
        self.rejoin_detail_offset = max(0, min(self.rejoin_detail_offset + step, len(self.rejoin_detail_lines) - page))

    def draw_rejoin_details(self) -> None:
        ui = self.kit
        ui.shade()
        width, height = ui.screen.get_size()
        panel = pygame.Rect(0, 0, min(860, width - 48), min(500, height - 48))
        panel.center = ui.screen.get_rect().center
        if panel.w - 48 != self.rejoin_detail_width:
            self.wrap_rejoin_details(panel.w - 48)
        ui.panel(panel, "bg", edge="top")
        ui.text("Reconnect error", (panel.x + 24, panel.y + 20), "l")
        if self.rejoin_detail_copy_status:
            ui.text(self.rejoin_detail_copy_status, (panel.right - 24, panel.y + 24), "s", "muted", "right")
        page = self.rejoin_detail_page()
        total = len(self.rejoin_detail_lines)
        self.rejoin_detail_offset = min(self.rejoin_detail_offset, max(0, total - page))
        start = self.rejoin_detail_offset
        end = min(start + page, total)
        line_height = ui.size("Ag", "s")[1] + 4
        for row, line in enumerate(self.rejoin_detail_lines[start:end]):
            ui.text(line, (panel.x + 24, panel.y + 60 + row * line_height), "s")
        y = panel.bottom - 48
        ui.button(pygame.Rect(panel.x + 24, y, 120, 30), "Prev [PgUp]", "rejoin_details_prev",
                  enabled=start > 0, size="xs")
        ui.button(pygame.Rect(panel.x + 152, y, 120, 30), "Next [PgDn]", "rejoin_details_next",
                  enabled=end < total, size="xs")
        ui.button(pygame.Rect(panel.x + 280, y, 132, 30), "Copy [Ctrl+C]", "rejoin_details_copy", size="xs")
        if total > page:
            ui.text(f"Lines {start + 1}–{end} of {total}", (panel.right - 156, y + 7), "xs", "muted", "right")
        ui.button(pygame.Rect(panel.right - 144, y, 120, 30), "Close [Esc]", "rejoin_details_close", size="xs")
        buttons = ui.hits[ui.modal_from:]
        focused = next((hit for hit in buttons if hit.enabled and hit.action == self.rejoin_detail_focus), buttons[-1])
        self.rejoin_detail_focus = focused.action
        ui.outline(focused.rect.inflate(4, 4), "text", 2)

    def update_connection_status(self) -> None:
        if self.cancelled_rejoin is not None and self.cancelled_rejoin.done():
            self.cancelled_rejoin = None
        if self.client is None or self.client.connected:
            return
        if getattr(self.client, "party_closed", False):
            self.status = "The host closed the party"
        elif self.cancelled_rejoin is not None:
            self.status = "Finishing the previous connection attempt…"
        else:
            self.status = self.rejoin_error or "Lost connection to host"

    def finish_rejoin(self) -> None:
        attempt = self.rejoin_attempt
        if attempt is None or not attempt.done():
            return
        self.rejoin_attempt = None
        old = self.client
        assert old is not None
        client = None
        try:
            client = attempt.result()
            world = load_playable_map(client.map_key) if client.map_key != self.match.world.key else self.match.world
        except (OSError, ValueError) as exc:
            if client is not None:
                client.close()
            self.status = self.rejoin_error = f"Rejoin failed: {exc}"
            return
        if client.generation != self.net_generation or world is not self.match.world:
            self.reset_party_view()
            self.match = Match(world, self.match.cfg, agent_roster=self.match.agents)
            self.refresh_map_art()
        old.close()
        self.stop_ability_audio()
        self.ui.pending_sounds.clear()
        self.ui.landed_at.clear()
        self.client = client
        self.net_generation = client.generation
        for pid in list(self.ui.spike_sounds):
            self.stop_spike_sound(pid)
        self.restore_spike_audio = True
        self.me = self.client.pid
        self._next_beep = None
        self.rejoin_error = ""
        self.status = "" if self.client.rejoined else "Joined as a new player"

    def validate_party_state(self, msg: dict) -> None:
        if msg["map"] not in PLAYABLE_MAP_KEYS:
            raise ValueError(f"Map {msg['map']!r} is disabled.")
        validate_snapshot_agents(self.match, msg["snap"])

    def step(self, dt: float, cmd: Command) -> list[GameEvent]:
        if self.mode == "local":
            commands = self.bots.commands(dt)
            commands[self.me] = cmd
            for pid, travel in self.dummy_moves.items():
                d = self.match.players[pid]
                if d.alive:  # moving targets strafe left and right around their home
                    side = 1.0 if math.sin(self.match.time * 6.0 / max(travel, 1.0)) > 0 else -1.0
                    commands[pid] = Command(facing=180.0, move_x=side if travel else 0.0)
            return self.match.tick(dt, commands)
        if self.session:
            return self.session.step(dt, {self.me: cmd})
        assert self.client is not None
        if self.client.connected and self.match.phase not in ("lobby", "over"):
            self.client.send(cmd)
        self.predict_own(dt, cmd)
        events: list[GameEvent] = []
        for msg in self.client.take(validate_state=self.validate_party_state):
            try:
                if msg.get("type") == "events":
                    events += events_from_json(msg.get("events", []))
                elif msg.get("type") == "state":
                    new_map = msg["map"] != self.match.world.key
                    if new_map or msg["game"] != self.net_generation:
                        world = load_playable_map(msg["map"]) if new_map else self.match.world
                        match = Match(world, self.match.cfg, agent_roster=self.match.agents)
                        positions: dict[int, Vec] = {}
                        apply_snapshot(match, msg["snap"], self.me, predict_own=True, server_pos=positions)
                        self.reset_party_view()
                        self.match = match
                        self.server_pos.update(positions)
                        self.net_generation = msg["game"]
                        if new_map:
                            self.refresh_map_art()
                    else:
                        apply_snapshot(self.match, msg["snap"], self.me, predict_own=True, server_pos=self.server_pos)
                    if getattr(self, "restore_spike_audio", False):
                        self.restore_spike_audio = False
                        self.ui.landed_at.clear()
                        if "spike_audio" in msg["snap"]:
                            events = [event for event in events if event.kind not in
                                      ("plant_start", "defuse_start", "plant_stop", "defuse_stop")]
                            events.extend(GameEvent("spike_audio_restore", action["started"], action)
                                          for action in msg["snap"]["spike_audio"])
            except (KeyError, OSError, TypeError, ValueError) as exc:
                warnings.warn(f"Snapshot from host unreadable: {exc}")
        if getattr(self, "restore_spike_audio", False):
            events = [event for event in events if event.kind not in
                      ("plant_start", "defuse_start", "plant_stop", "defuse_stop")]
        self.smooth_positions(dt)
        return events

    def predict_own(self, dt: float, cmd: Command) -> None:
        """Move the own figure at once with the same rules as the host (no waiting for the round trip)."""
        me = self.match.players.get(self.me)
        if me is None or not me.alive or self.match.phase not in ("buy", "live", "planted"):
            return
        me.walking, me.crouching = cmd.walk, cmd.crouch
        speed = self.match._max_speed(me)
        wish = Vec(cmd.move_x, cmd.move_y)
        if not me.dm_ghost and me.channel_until > self.match.time:
            wish = Vec(0, 0)
        if wish.length() > 1:
            wish = wish.normalized()
        target = wish.rotated(me.facing) * speed
        diff = target - me.vel
        rate = float(self.match._mv["accel"] if wish.length() > 0 else self.match._mv["decel"]) * dt
        me.vel = target if me.dm_ghost or diff.length() <= rate else me.vel + diff.normalized() * rate
        self.match._physics(me, dt, hold_jump=cmd.jump, climb=cmd.move_y)

    def smooth_positions(self, dt: float) -> None:
        """Others glide towards their host position; the own figure is pulled back only when it drifts off."""
        for pid, host_pos in self.server_pos.items():
            p = self.match.players.get(pid)
            if p is None:
                continue
            error = host_pos - p.pos
            if pid == self.me:
                if error.length() > 2.5:
                    p.pos = host_pos  # prediction went wrong (blocked, knocked back): take the host's word
                elif error.length() > 0.05:
                    p.pos = p.pos + error * min(1.0, dt * 4.0)
            else:
                p.pos = p.pos + error * min(1.0, dt * 15.0)
