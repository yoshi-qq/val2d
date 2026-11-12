"""The game client: input, simulation step (local, host or client), composed from the drawing and HUD parts."""
from __future__ import annotations

import user_settings

from client.common import *  # noqa: F403
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
from gameplay.world import load_playable_map


class Game(OverlaysMixin, EventsMixin, CharactersMixin, WorldViewMixin, LobbyMixin, HudMixin, MinimapMixin, BuyMixin, ScoreboardMixin):
    def __init__(self, args: argparse.Namespace) -> None:
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
        if args.join:
            self.mode = "client"
            self.join_target, self.join_name, self.join_agent = args.join, args.name, args.agent
            self.client = NetClient(args.join, args.name, args.agent, weapon_skins=self.weapon_skins)
            try:
                world = load_playable_map(self.client.map_key)
            except (OSError, ValueError):
                self.client.close()
                raise
        self.match = Match(world, cfg, agent_roster=playable_agents())
        if self.client is not None:
            self.me = self.client.pid
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
        self.multi_points: list[tuple[float, float]] = []  # points marked for a multi-placement ability
        self.swallow_buttons: set[int] = set()  # mouse buttons that cast an ability: no shot until released
        self._next_beep = 0.0
        self._last_phase = ""
        self.server_pos: dict[int, Vec] = {}  # client: host positions, smoothed towards each frame
        self.ui = UiState()
        self.sound = Sound()
        self.cursor_depth = 8.0
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
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    if self.ui.buy_open:
                        self.ui.buy_open = False
                    elif self.aiming:
                        self.set_aim(None)
                    else:
                        self.open_overlay("pause")
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN and self.match.phase == "over":
                    running = False  # back to the menu
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.screen_button(ev.pos) == "to_menu":
                    running = False
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.screen_button(ev.pos) == "rejoin":
                    self.rejoin()
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_RETURN and self.client is not None and not self.client.connected:
                        self.rejoin()
                    elif ev.key == pygame.K_RETURN and self.match.phase == "lobby":
                        self.start_from_lobby()
                    elif ev.key == self.keys["buy"]:
                        self.set_aim(None)
                        self.ui.buy_open = not self.ui.buy_open
                        self.grab(not self.ui.buy_open)
                    elif ev.key in self.ability_keys and me.alive and not self.ui.buy_open:
                        slot = self.ability_keys[ev.key]
                        if self.aiming == slot:
                            self.set_aim(None)
                        elif self.needs_aim(me, slot) and me.channel_until <= self.match.time:
                            self.set_aim(slot)
                            self.sound.play("ability_equip", gain=0.5)
                        else:
                            self.set_aim(None)
                            cmd.ability = slot
                    elif ev.key in (self.keys["primary"], self.keys["sidearm"], self.keys["melee"]):
                        self.select_weapon(cmd, next(slot for slot in SLOTS if self.keys[slot] == ev.key))
                    elif ev.key == self.keys["reload"]:
                        cmd.reload = True
                    elif ev.key == self.keys["drop"]:
                        cmd.drop = True
                elif ev.type == pygame.MOUSEWHEEL and me.alive and not self.ui.buy_open \
                        and not self.tactical_ability(me) and self.match.phase in ("buy", "live", "planted"):
                    self.scroll_weapons(me, cmd, ev.y)
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button in (1, 3) and self.aiming and me.alive \
                        and not self.ui.buy_open and self.match.phase in ("buy", "live", "planted"):
                    self.aim_click(me, cmd, ev.button, ev.pos)
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.match.phase == "lobby":
                    self.pick_agent_at(ev.pos)
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and not me.alive:
                    self.spectate_index += 1
                elif ev.type == pygame.MOUSEBUTTONDOWN and self.ui.buy_open and ev.button == 3:
                    item = self.buy_item_at(ev.pos)
                    if item in ("C", "Q", "E") and self.item_sellable(me, item):
                        cmd.buy.append(f"sell:{item}")
                    elif item and item in self.match.weapons and self.match.weapons[item].slot == "primary":
                        cmd.request = "" if me.request == item else item  # right click: ask the team (again = withdraw)
                        self.sound.play("ui_click", gain=0.6)
                elif ev.type == pygame.MOUSEBUTTONDOWN and self.ui.buy_open and ev.button == 1 and self.request_at(ev.pos):
                    cmd.buy.append(self.request_at(ev.pos) or "")
                    self.sound.play("ui_buy", gain=0.6)
                elif ev.type == pygame.MOUSEBUTTONDOWN and self.ui.buy_open and ev.button == 1:
                    item = self.buy_item_at(ev.pos)
                    if item:
                        cmd.buy.append(item)
                        self.sound.play("ui_buy", gain=0.6)
            keys = pygame.key.get_pressed()
            buttons = pygame.mouse.get_pressed()
            self.ui.show_scores = keys[self.keys["scoreboard"]]
            self.help_held = bool(keys[self.help_key]) and not self.overlay
            if not self.ui.buy_open and not self.overlay and self.grabbed and not self.tactical_ability(me):
                dx, dy = pygame.mouse.get_rel()
                self.local_facing = (self.local_facing + dx * self.sens) % 360
                me.facing = self.local_facing
                self.move_cursor(me, dy)
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
            events = self.step(dt, cmd)
            me_now = self.match.players.get(self.me)
            if me_now is None or me_now.slot == self._requested_slot or self.match.time - self._switched_at > 0.5 \
                    or self.match.round_no != self.seen_round:
                self._requested_slot = None
            if me_now is None or not me_now.alive or self.match.phase not in ("buy", "live", "planted") \
                    or self.match.round_no != self.seen_round:
                self.set_aim(None)
            elif self.aiming == "X" and me_now.repeat_until and me_now.repeat_until <= self.match.time \
                    and not self.ability_ready(me_now, "X"):
                self.set_aim(None)
            if me_now is not None:
                self.apply_zoom(me_now, cmd.alt_fire and not self.ui.buy_open)
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
            self.handle_events(events)
            if self.match.players.get(self.me) is not None:
                self.audio_tick(self.match.players[self.me])
            if self.match.phase == "over" and not self.recorded and self.me in self.match.players:
                from client import history
                history.record(self.match, self.me, self.score_of)  # for the Career page
                self.recorded = True
            self.draw()
            self.draw_overlay()
            pygame.display.flip()
            if self.client and not self.client.connected:
                self.status = "Lost connection to host"
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
        self.multi_points.clear()

    def tactical_ability(self, me: PlayerState) -> dict | None:
        ab = self.match.agents.get(me.agent, {}).get("abilities", {}).get(self.aiming, {})
        return ab if ab.get("tactical") else None

    def aim_click(self, me: PlayerState, cmd: Command, button: int, mouse: tuple[int, int]) -> None:
        slot = self.aiming
        if slot is None:
            return
        self.swallow_buttons.add(button)
        ab = self.match.agents[me.agent]["abilities"][slot]
        multi = int(ab.get("multi", 1)) > 1
        tactical = bool(ab.get("tactical"))
        if multi and button == 3:
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
        cmd.ability, cmd.ability_alt = slot, button == 3 and not multi
        cmd.facing, cmd.cursor_depth = me.facing, self.cursor_depth
        if not ab.get("repeat_shots"):
            self.set_aim(None)

    def screen_button(self, pos: tuple[int, int]) -> str | None:
        """Action of a button drawn this frame on the match screen (back to menu, rejoin), if one is under pos."""
        hit = self.kit.hit_at(pos)
        return hit.action if hit is not None and hit.action in ("to_menu", "rejoin") else None

    def apply_zoom(self, me: PlayerState, holding_alt: bool) -> None:
        """Camera zoom while a zoom weapon's alternate fire is held; map image cached per zoom level."""
        d = self.match.weapons.get(me.weapon.key) if me.weapon else None
        if d is None or not me.alive or me.blades_equipped or me.reload_until > self.match.time:
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
        """Connect again after a drop; the host gives the old slot back (same token or name)."""
        old = self.client
        assert old is not None
        try:
            client = NetClient(self.join_target, self.join_name, self.join_agent, token=old.token,
                               weapon_skins=self.weapon_skins)
            if client.map_key != self.match.world.key:
                client.close()
                raise ConnectionError("The host is running a different map.")
        except ConnectionError as exc:
            self.status = f"Rejoin failed: {exc}"
            return
        self.client = client
        self.me = self.client.pid
        self.status = "" if self.client.rejoined else "Joined as a new player"

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
        if self.client.connected:
            self.client.send(cmd)
        self.predict_own(dt, cmd)
        events: list[GameEvent] = []
        for msg in self.client.take():
            try:
                if msg.get("type") == "events":
                    events += events_from_json(msg.get("events", []))
                elif msg.get("type") == "state":
                    apply_snapshot(self.match, msg["snap"], self.me, predict_own=True, server_pos=self.server_pos)
            except (KeyError, TypeError, ValueError) as exc:
                warnings.warn(f"Snapshot from host unreadable: {exc}")
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
        if me.channel_until > self.match.time:
            wish = Vec(0, 0)
        if wish.length() > 1:
            wish = wish.normalized()
        target = wish.rotated(me.facing) * speed
        diff = target - me.vel
        rate = float(self.match._mv["accel"] if wish.length() > 0 else self.match._mv["decel"]) * dt
        me.vel = target if diff.length() <= rate else me.vel + diff.normalized() * rate
        self.match._physics(me, dt, hold_jump=cmd.jump)

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
