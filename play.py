"""Play Val2d: practice match against bots on the own game core (gameplay).

Usage:  python play.py [--agent kestrel|marrow] [--team-size 1..5] [--rounds 13] [--map werkhof|gasse]
                        [--all-around] [--sound-rings]
Network:  python play.py --host            open a match (host = player 1), Enter starts
          python play.py --find            find a match on the local network and join
          python play.py --join 192.168.1.20[:9009]
Dedicated server process: python server.py (see there).
Controls: WASD run, Shift walk, Ctrl crouch, Space jump, left mouse shoot,
mouse horizontal turn, mouse vertical aim depth, R reload, 1/2/3 weapon, C/Q/E/X abilities,
hold F plant/defuse the bomb, B buy menu, Tab scoreboard, Esc quit.
Graphics: sprites from the design session (docs/SPRITES.md); placeholders where a file is missing.
"""
from __future__ import annotations

import argparse
import math
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import pygame

from gameplay import abilities
from gameplay.bots import BotDirector
from gameplay.data import LobbySettings, load_config
from gameplay.geometry import Vec, heading
from gameplay.match import Command, Effect, GameEvent, Match, PlayerState
from gameplay.net import apply_snapshot, events_from_json
from gameplay.netgame import DEFAULT_PORT, NetClient, discover
from gameplay.session import HostSession
from gameplay.world import load_map
from sprite_bank import CharacterSprites, SpriteBank, build_map_surface, draw_nine_slice

ROOT = Path(__file__).resolve().parent
FONT_PATH = ROOT / "font" / "fixed_sys.ttf"
VIEW_METERS = 30.0

C_BG = (22, 21, 28)
C_FLOOR = (52, 50, 60)
C_WALL = (110, 106, 120)
C_WALL_THIN = (138, 120, 96)
C_CRATE = (77, 106, 119)
C_PLATFORM = (70, 68, 82)
C_RAMP = (90, 86, 100)
C_SITE = (224, 180, 55)
C_ALLY = (79, 214, 200)
C_ENEMY = (238, 76, 74)
C_TEXT = (232, 230, 239)
C_MUTED = (155, 152, 170)
C_SMOKE = (150, 150, 170)


@dataclass
class Tracer:
    a: Vec
    b: Vec
    until: float
    own: bool


@dataclass
class Ring:
    pos: Vec
    radius: float
    start: float


@dataclass
class UiState:
    buy_open: bool = False
    show_scores: bool = False
    tracers: list[Tracer] = field(default_factory=list)
    rings: list[Ring] = field(default_factory=list)
    feed: list[tuple[float, str, str | None, str | None, bool]] = field(default_factory=list)  # until, text, killer agent, victim agent, head
    banner: tuple[float, str] = (0.0, "")
    banner_art: str = ""  # file name under assets/ui/banner/ shown above the banner text
    hit_marker: float = 0.0
    last_shot: dict[int, float] = field(default_factory=dict)
    last_cast: dict[int, tuple[float, str]] = field(default_factory=dict)  # pid -> (time, slot)
    last_hit: dict[int, float] = field(default_factory=dict)
    died_at: dict[int, float] = field(default_factory=dict)
    landed_at: dict[int, float] = field(default_factory=dict)
    prev_z: dict[int, float] = field(default_factory=dict)
    blasts: list[tuple[Vec, float, float]] = field(default_factory=list)  # pos, radius, start
    oneshots: list[tuple[str, Vec, float, float, int, tuple[float, float]]] = field(default_factory=list)
    # (file, world pos, start, duration, frame width in px, size in metres)
    scorches: list[tuple[Vec, float]] = field(default_factory=list)       # pos, until
    figure_fx: list[tuple[int, str, float, float]] = field(default_factory=list)  # pid, fx file, start, duration
    waves: list[tuple[int, Vec, float]] = field(default_factory=list)      # pid, end point, start


STATUS_TINT = {"slow": (150, 110, 220), "decay": (120, 200, 90), "vulnerable": (230, 120, 80), "deaf": (120, 160, 230),
               "suppress": (200, 80, 160), "nearsight": (90, 80, 120), "concuss": (230, 210, 90), "detain": (200, 200, 200),
               "stim": (90, 220, 160)}


class Sound:
    """Synthetic placeholder sounds with stereo panning and distance attenuation."""

    def __init__(self) -> None:
        self.ok = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.volume = 0.8
        try:
            import numpy as np
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
            rate = 44100

            def tone(freq: float, dur: float, noise: float, decay: float) -> pygame.mixer.Sound:
                t = np.linspace(0, dur, int(rate * dur), False)
                wave = (np.sin(2 * np.pi * freq * t) * (1 - noise) + np.random.uniform(-1, 1, t.size) * noise) * np.exp(-t * decay)
                data = (wave * 12000).astype(np.int16)
                return pygame.sndarray.make_sound(np.column_stack([data, data]))

            self.sounds = {"shot": tone(140, 0.18, 0.8, 22), "step": tone(70, 0.06, 0.6, 50),
                           "plant": tone(880, 0.25, 0.0, 6), "kill": tone(520, 0.12, 0.1, 18), "ability": tone(320, 0.3, 0.4, 8)}
            self.ok = True
        except Exception as exc:  # sound is not essential to play
            warnings.warn(f"Sound disabled: {exc}")

    def play(self, kind: str, listener: PlayerState | None, pos: Vec | None, radius: float = 40.0) -> None:
        if not self.ok or kind not in self.sounds:
            return
        left = right = 0.6
        if listener and pos:
            rel = (pos - listener.pos).rotated(-listener.facing)
            dist = rel.length()
            vol = max(0.0, 1.0 - dist / max(radius, 1.0))
            pan = max(-1.0, min(1.0, rel.x / max(dist, 1.0)))
            left, right = vol * (1 - max(0.0, pan)), vol * (1 + min(0.0, pan))
        if left + right < 0.02:
            return
        ch = self.sounds[kind].play()
        if ch:
            ch.set_volume(left * self.volume, right * self.volume)


class Game:
    def __init__(self, args: argparse.Namespace) -> None:
        pygame.init()
        self.screen = display_mode(bool(getattr(args, "fullscreen", False)))
        pygame.display.set_caption("Val2d")
        self.w, self.h = self.screen.get_size()
        self.scale = self.w / VIEW_METERS
        try:
            self.font = pygame.font.Font(str(FONT_PATH), 18)
            self.big = pygame.font.Font(str(FONT_PATH), 36)
        except (OSError, FileNotFoundError):
            warnings.warn("Font fixed_sys.ttf missing; using the default font.")
            self.font = pygame.font.Font(None, 22)
            self.big = pygame.font.Font(None, 44)
        base = load_config()
        lobby = LobbySettings(all_around_sight=args.all_around or base.lobby.all_around_sight,
                              sound_rings=args.sound_rings or base.lobby.sound_rings,
                              win_rounds=args.rounds, overtime=base.lobby.overtime, team_size=args.team_size)
        cfg = type(base)(hit_zones=base.hit_zones, lobby=lobby, player=base.player)
        self.team_size = args.team_size
        self.mode = "local"
        self.practice = bool(getattr(args, "practice", False))
        self.dummy_moves: dict[int, float] = {}
        self.stats = {"shots": 0, "hits": 0, "heads": 0, "kills": 0}
        self.session: HostSession | None = None
        self.client: Client | None = None
        self.status = ""
        if args.join:
            self.mode = "client"
            self.client = NetClient(args.join, args.name, args.agent)
            self.match = Match(load_map(self.client.map_key), cfg)
            self.me = self.client.pid
        elif args.host:
            self.mode = "host"
            self.match = Match(load_map(args.map), cfg)
            online = bool(getattr(args, "online", False))
            self.session = HostSession(self.match, args.name, None if online else args.port,
                                       mode="internet" if online else "lan")
            self.me = self.match.add_player(args.name, 0, args.agent).pid
        elif getattr(args, "practice", False):
            self.match = Match(load_map("range"), cfg)
            self.me = self.match.add_player("You", 0, args.agent).pid
            for i, (pos, move) in enumerate(self.match.world.practice_targets):
                d = self.match.add_player(f"Target {i + 1}", 1, args.agent, is_bot=True)
                d.dummy, d.home = True, pos
                self.dummy_moves[d.pid] = move
        else:
            self.match = Match(load_map(args.map), cfg)
            self.me = self.match.add_player("You", 0, args.agent).pid
            others = [a for a in self.match.agents if a != args.agent] or [args.agent]
            for i in range(args.team_size - 1):
                self.match.add_player(f"Bot {i + 1}", 0, others[i % len(others)], is_bot=True)
            for i in range(args.team_size):
                self.match.add_player(f"Enemy {i + 1}", 1, list(self.match.agents)[i % len(self.match.agents)], is_bot=True)
        self.bots = BotDirector(self.match)
        self.bank = SpriteBank()
        self.chars = CharacterSprites(self.bank)
        self.map_surface = build_map_surface(self.match.world, self.bank, self.scale)
        self.map_cache: dict[float, pygame.Surface | None] = {round(self.scale, 3): self.map_surface}
        self._crop: pygame.Surface | None = None
        self._minimap_static: pygame.Surface | None = None
        self.local_facing = 0.0
        self.seen_round = -1
        self.spectate_index = 0
        self.server_pos: dict[int, Vec] = {}  # client: host positions, smoothed towards each frame
        self.ui = UiState()
        self.sound = Sound()
        self.cursor_depth = 8.0
        self.sens = float(getattr(args, "sensitivity", base.player.sensitivity))
        self.camera_push = float(getattr(args, "camera_push", base.player.camera_push))
        self.sound.volume = float(getattr(args, "volume", 0.8))
        self.clock = pygame.time.Clock()
        self.grab(False)
        self.agent_cards: list[tuple[pygame.Rect, str]] = []

    def grab(self, on: bool) -> None:
        self.grabbed = on
        pygame.event.set_grab(on)
        pygame.mouse.set_visible(not on)
        pygame.mouse.get_rel()

    # ------------------------------------------------------------ Schleife
    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(120) / 1000.0
            cmd = Command()
            me = self.match.players.get(self.me)
            if me is None:  # client before the first snapshot
                me = PlayerState(pid=self.me, name="", team=0, agent="kestrel")
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN and self.match.phase == "over":
                    running = False  # back to the menu
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_RETURN and self.match.phase == "lobby":
                        if self.session:
                            self.session.start(self.team_size)
                        elif self.mode == "local" and self.practice:
                            self.match.start_practice()
                            for d in self.match.players.values():
                                if d.dummy:
                                    d.pos, d.facing = d.home, 180.0
                        elif self.mode == "local":
                            self.match.start()
                    elif ev.key == pygame.K_b:
                        self.ui.buy_open = not self.ui.buy_open
                        self.grab(not self.ui.buy_open)
                    elif ev.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                        cmd.slot = {pygame.K_1: "primary", pygame.K_2: "sidearm", pygame.K_3: "melee"}[ev.key]
                    elif ev.key == pygame.K_r:
                        cmd.reload = True
                    elif ev.key == pygame.K_g:
                        cmd.drop = True
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.match.phase == "lobby":
                    self.pick_agent_at(ev.pos)
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and not me.alive:
                    self.spectate_index += 1
                elif ev.type == pygame.MOUSEBUTTONDOWN and self.ui.buy_open and ev.button == 1:
                    item = self.buy_item_at(ev.pos)
                    if item:
                        cmd.buy.append(item)
            keys = pygame.key.get_pressed()
            buttons = pygame.mouse.get_pressed()
            self.ui.show_scores = keys[pygame.K_TAB]
            if not self.ui.buy_open:
                dx, dy = pygame.mouse.get_rel()
                self.local_facing = (self.local_facing + dx * self.sens) % 360
                me.facing = self.local_facing
                self.cursor_depth = max(0.5, min(VIEW_METERS, self.cursor_depth - dy * 0.03))
                cmd.fire = buttons[0]
                cmd.alt_fire = buttons[2]
            cmd.facing = me.facing
            cmd.cursor_depth = self.cursor_depth
            cmd.move_y = (1 if keys[pygame.K_w] else 0) - (1 if keys[pygame.K_s] else 0)
            cmd.move_x = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
            cmd.walk = keys[pygame.K_LSHIFT]
            cmd.crouch = keys[pygame.K_LCTRL]
            cmd.jump = keys[pygame.K_SPACE]
            cmd.interact = keys[pygame.K_f]
            for key, ab in ((pygame.K_c, "C"), (pygame.K_q, "Q"), (pygame.K_e, "E"), (pygame.K_x, "X")):
                if keys[key]:
                    cmd.ability = ab
            self.apply_zoom(me, cmd.alt_fire and not self.ui.buy_open)
            events = self.step(dt, cmd)
            if self.match.phase != "lobby" and not self.grabbed and not self.ui.buy_open:
                self.grab(True)
            if self.match.round_no != self.seen_round and self.seen_round > 0 and self.me in self.match.players:
                half = int(self.match._r["half_after"])
                if self.match.round_no == half + 1:
                    self.ui.banner, self.ui.banner_art = (self.match.time + 3, "Sides switched"), "seitenwechsel"
                elif self.match.round_no == 2 * half + 1:
                    self.ui.banner, self.ui.banner_art = (self.match.time + 3, "Overtime"), "verlaengerung"
            if self.match.round_no != self.seen_round and self.me in self.match.players:
                self.seen_round = self.match.round_no  # new round: take the facing from the spawn
                self.local_facing = self.match.players[self.me].facing
            self.handle_events(events)
            self.draw()
            if self.client and not self.client.connected:
                self.status = "Lost connection to host"
        if self.session:
            self.session.close()
        if self.client:
            self.client.close()

    def apply_zoom(self, me: PlayerState, holding_alt: bool) -> None:
        """Camera zoom while a zoom weapon's alternate fire is held; map image cached per zoom level."""
        d = self.match.weapons.get(me.weapon.key) if me.weapon else None
        factor = float(d.alt_get("factor", 1.0)) if d and holding_alt and d.alt_get("kind") == "zoom" and me.alive else 1.0
        scale = self.w / (VIEW_METERS / factor)
        if abs(scale - self.scale) < 1e-6:
            return
        self.scale = scale
        key = round(scale, 3)
        if key not in self.map_cache:
            self.map_cache[key] = build_map_surface(self.match.world, self.bank, scale)
        self.map_surface = self.map_cache[key]
        self._crop = None

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
        if wish.length() > 1:
            wish = wish.normalized()
        target = wish.rotated(me.facing) * speed
        diff = target - me.vel
        rate = float(self.match._mv["accel"] if wish.length() > 0 else self.match._mv["decel"]) * dt
        me.vel = target if diff.length() <= rate else me.vel + diff.normalized() * rate
        self.match._physics(me, dt)

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

    def handle_events(self, events: list[GameEvent]) -> None:
        m, t = self.match, self.match.time
        me = m.players.get(self.me)
        if me is None:
            return
        for e in events:
            d = e.data
            if e.kind == "shot":
                self.ui.last_shot[d["pid"]] = t
                if d["pid"] == self.me:
                    self.stats["shots"] += 1
                if d.get("stop") == "wall":
                    self.ui.oneshots.append(("fx/einschlag_wand.png", Vec(*d["to"]), t, 0.25, 8, (0.5, 0.5)))
                self.ui.tracers.append(Tracer(Vec(*d["from"]), Vec(*d["to"]), t + 0.08, d["pid"] == self.me))
            elif e.kind == "sound":
                if me.status.get("deaf", 0.0) > t:
                    continue
                pos = Vec(*d["pos"])
                self.sound.play(d["kind"], me, pos, d["radius"])
                if m.cfg.lobby.sound_rings and d["pid"] != self.me:
                    self.ui.rings.append(Ring(pos, min(d["radius"], 6.0), t))
            elif e.kind == "hit":
                self.ui.last_hit[d["pid"]] = t
                if d.get("by") == self.me:
                    self.stats["hits"] += 1
                    self.stats["heads"] += 1 if d.get("zone") == "head" else 0
                victim = m.players.get(d["pid"])
                if victim is not None:
                    self.ui.oneshots.append(("fx/treffer_koerper.png", victim.pos, t, 0.25, 8, (0.5, 0.5)))
                if d["by"] == self.me:
                    self.ui.hit_marker = t + 0.15
            elif e.kind == "kill":
                self.ui.died_at[d["pid"]] = t
                killer = m.players.get(d["by"]) if d["by"] else None
                victim = m.players.get(d["pid"])
                by = killer.name if killer else "Bomb"
                self.ui.feed.append((t + 5, f"{by} → {victim.name if victim else '?'}", killer.agent if killer else None,
                                     victim.agent if victim else None, bool(d["head"])))
                self.sound.play("kill", None, None)
            elif e.kind == "plant":
                self.ui.banner = (t + 2.5, f"Bomb planted on {d['site']}")
                self.ui.banner_art = "spike_gelegt"
                self.sound.play("plant", None, None)
            elif e.kind == "blast":
                self.sound.play("shot", me, Vec(*d["pos"]), 40)
                self.ui.blasts.append((Vec(*d["pos"]), float(d["radius"]), t))
                self.ui.scorches.append((Vec(*d["pos"]), t + 20.0))
            elif e.kind == "revive":
                self.ui.figure_fx.append((d["pid"], "revive", t, 0.6))
                revived = m.players.get(d["pid"])
                self.ui.feed.append((t + 4, f"{revived.name if revived else '?'} revived", None, revived.agent if revived else None, False))
            elif e.kind == "ability" and d.get("kind") == "wave":
                self.ui.last_cast[d["pid"]] = (t, str(d.get("key", "C")))
                self.ui.waves.append((d["pid"], Vec(*d["pos"]), t))
            elif e.kind == "ability":
                self.ui.last_cast[d["pid"]] = (t, str(d.get("key", "C")))
                kind, at = str(d.get("kind")), Vec(*d["pos"])
                caster = m.players.get(d["pid"])
                if kind == "hop" and caster is not None:
                    self.ui.oneshots.append(("fx/satz_staub.png", caster.pos, t, 0.35, 16, (1.0, 0.5)))
                elif kind == "reveal_all" and caster is not None:
                    self.ui.oneshots.append(("fx/ability/beacon.png", caster.pos, t, 1.5, 16, (1.0, 1.0)))
                elif kind in ("zone", "sensor", "alarm", "tripwire", "blast", "smoke"):
                    self.ui.oneshots.append(("fx/ability/impact_puff.png", at, t, 0.3, 16, (1.0, 1.0)))
                fx = {"teleport": ("teleport", 0.4), "shield": ("shield_shell", 0.6), "anchor": ("teleport", 0.4)}.get(str(d.get("kind")))
                if fx:
                    self.ui.figure_fx.append((d["pid"], fx[0], t, fx[1]))
                self.sound.play("ability", me, Vec(*d["pos"]), 30)
            elif e.kind == "round_end":
                won = d["winner"] == me.team
                self.ui.banner = (t + 5, f"{d['reason']}  {d['score'][me.team]}:{d['score'][1 - me.team]}")
                self.ui.banner_art = "sieg" if won else "niederlage"
                if d.get("reason") == "Bomb defused":
                    self.ui.banner_art = "entschaerft" if won else "niederlage"
            elif e.kind == "explode":
                self.ui.oneshots.append(("fx/spike_explosion.png", Vec(*d["pos"]), t, 1.0, 64, (24.0, 24.0)))
                self.ui.scorches.append((Vec(*d["pos"]), t + 30.0))
                self.sound.play("shot", me, Vec(*d["pos"]), 80)
            elif e.kind == "flash":
                self.ui.oneshots.append(("fx/funke_explosion.png", Vec(*d["pos"]), t, 0.3, 16, (1.0, 1.0)))
            elif e.kind == "door":
                self.sound.play("step", me, Vec(*d["pos"]), 15)
            elif e.kind == "defuse":
                self.sound.play("plant", None, None)

    # ------------------------------------------------------------ Zeichnen
    def to_screen(self, p: Vec, me: PlayerState) -> tuple[float, float]:
        rel = (p - me.pos).rotated(-me.facing)
        cx, cy = self.w / 2, self.h * (0.5 + self.camera_push * 0.5)
        return cx + rel.x * self.scale, cy - rel.y * self.scale

    def poly(self, rect, me: PlayerState) -> list[tuple[float, float]]:
        return [self.to_screen(Vec(x, y), me) for x, y in ((rect.x0, rect.y0), (rect.x1, rect.y0), (rect.x1, rect.y1), (rect.x0, rect.y1))]

    def draw(self) -> None:
        m, s = self.match, self.screen
        me = m.players.get(self.me)
        if me is None or m.phase == "lobby":
            self.draw_lobby()
            pygame.display.flip()
            return
        me = self.view_player(me)
        s.fill(C_BG)
        wm = m.world
        if self.map_surface is not None:
            self.draw_map_texture(me)
        else:
            self.draw_map_placeholder(me)
        self.draw_live_objects(me)
        for site in wm.sites:
            sx, sy = self.to_screen(site.rect.center, me)
            lbl = self.big.render(site.name, True, C_SITE)
            s.blit(lbl, (sx - lbl.get_width() / 2, sy - lbl.get_height() / 2))
        for drop in m.drops:  # weapons lying on the ground, hand sprite at 2x the world scale
            size = (round(2 * self.scale), round(self.scale))
            gun = self.bank.scaled(f"weapons/val2d/{drop.key}.png", size)
            dx, dy = self.to_screen(drop.pos, me)
            if gun is not None:
                s.blit(gun, (dx - size[0] / 2, dy - size[1] / 2))
            else:
                pygame.draw.rect(s, C_MUTED, (dx - 8, dy - 3, 16, 6))
        self.ui.scorches = [(pos, until) for pos, until in self.ui.scorches if until > m.time]
        for pos, until in self.ui.scorches:
            d = round(3 * self.scale)
            mark = self.bank.scaled("maps/common/decals/scorch.png", (d, d))
            if mark is not None:
                mark = mark.copy()
                mark.set_alpha(int(255 * min(1.0, (until - m.time) / 5)))
                x, y = self.to_screen(pos, me)
                s.blit(mark, (x - d / 2, y - d / 2))
        for e in m.effects:
            self.draw_effect(e, me)
        if m.spike_pos is not None:
            px, py = self.to_screen(m.spike_pos, me)
            blink = m.phase != "planted" or int(m.time * (2 + 6 * (1 - m.spike_time_left() / 45))) % 2 == 0
            size = round(self.scale)
            img = self.bank.scaled("fx/spike.png", (size, size), 0 if blink else 1, 16)
            if img is not None:
                s.blit(img, (px - size / 2, py - size / 2))
            else:
                pygame.draw.rect(s, C_ENEMY if blink else (90, 40, 40), (px - 6, py - 6, 12, 12))
        # sight cone: darken everything outside
        if not m.cfg.lobby.all_around_sight and me.alive:
            shade = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 150))
            cx, cy = self.to_screen(me.pos, me)
            half = math.radians(m.fov / 2)
            far = 3000
            pygame.draw.polygon(shade, (0, 0, 0, 0), [(cx, cy), (cx - math.sin(half) * far, cy - math.cos(half) * far), (cx + math.sin(half) * far, cy - math.cos(half) * far)])
            s.blit(shade, (0, 0))
        for ring in list(self.ui.rings):
            age = m.time - ring.start
            if age > 0.6:
                self.ui.rings.remove(ring)
                continue
            rx, ry = self.to_screen(ring.pos, me)
            d = max(2, round(2 * ring.radius * self.scale * age / 0.6))
            img = self.bank.tinted("fx/sound_ring.png", (d, d), min(2, int(age / 0.2)), 64, C_MUTED)
            if img is not None:
                s.blit(img, (rx - d / 2, ry - d / 2))
            else:
                pygame.draw.circle(s, C_MUTED, (rx, ry), max(1, d / 2), 1)
        for tr in list(self.ui.tracers):
            if m.time > tr.until:
                self.ui.tracers.remove(tr)
                continue
            self.tile_line("fx/tracer_own.png" if tr.own else "fx/tracer.png", self.to_screen(tr.a, me),
                           self.to_screen(tr.b, me), 16, 0.0, (255, 230, 140), 2 if tr.own else 1)
            frame = max(0, min(2, int((0.08 - (tr.until - m.time)) / 0.08 * 3)))
            size = max(1, round(self.scale * 0.5))
            muzzle = self.bank.scaled("fx/muendung.png", (size, size), frame, 8)
            if muzzle is not None and (tr.b - tr.a).length() > 0.7:
                mx, my = self.to_screen(tr.a + (tr.b - tr.a).normalized() * 0.6, me)
                s.blit(muzzle, (mx - size / 2, my - size / 2))
        for p in m.players.values():
            if not p.alive:
                if p.visible or self.mode != "client":
                    bx, by = self.to_screen(p.pos, me)
                    body = self.character_frame(p, me)
                    if body is not None:
                        s.blit(body, (bx - body.get_width() / 2, by - body.get_height() / 2))
                continue
            seen = p.visible if self.mode == "client" else m.can_see(me, p)
            if p.team != me.team and not seen:
                continue
            px, py = self.to_screen(p.pos, me)
            r = 0.4 * self.scale
            col = C_ALLY if p.team == me.team else C_ENEMY
            fx, fy = self.to_screen(p.pos + heading(p.facing) * 0.9, me)
            size = max(1, round(self.scale / 2))
            marker = self.bank.tinted("fx/facing_marker.png", (size, size), 0, 0, col)
            if marker is not None:
                screen_angle = math.degrees(math.atan2(fx - px, -(fy - py)))
                marker = pygame.transform.rotate(marker, -screen_angle)
                s.blit(marker, (fx - marker.get_width() / 2, fy - marker.get_height() / 2))
            else:
                pygame.draw.line(s, col, (px, py), (fx, fy), 2)
            img = self.character_frame(p, me)
            if img is not None:
                s.blit(img, (px - img.get_width() / 2, py - img.get_height() / 2))
                walk_index = int(m.time * 8)
                for layer in self.chars.overlays(p.agent, list(self.sprite_cfg(p).get("overlays", [])), p.team != me.team,
                                                 self.scale, walk_index):
                    s.blit(layer, (px - layer.get_width() / 2, py - layer.get_height() / 2))
                self.draw_figure_fx(p, (px, py))
                if p.team != me.team and p.revealed_until > m.time:
                    mark = self.bank.scaled("fx/ability/reveal_marker.png", (round(self.scale * 14 / 16), round(self.scale * 7 / 16)))
                    if mark is not None:
                        s.blit(mark, (px - mark.get_width() / 2, py - img.get_height() / 2 - mark.get_height() - 4))
                r = img.get_height() / 2
            else:
                if p.team != me.team:
                    pygame.draw.circle(s, C_ENEMY, (px, py), r + 3, 3)
                pygame.draw.circle(s, (80, 90, 94) if p.pid != self.me else (110, 120, 124), (px, py), r)
            if p.level:
                s.blit(self.font.render("▲", True, C_TEXT), (px + r, py - r))
            if p.pid != self.me:
                name = self.font.render(p.name, True, col)
                s.blit(name, (px - name.get_width() / 2, py - r - 22))
        self.draw_bursts(me)
        self.draw_crosshair(me)
        if me.status.get("nearsight", 0.0) > m.time:
            fog = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            fog.fill((10, 8, 14, 225))
            cx, cy = self.to_screen(me.pos, me)
            pygame.draw.circle(fog, (0, 0, 0, 0), (cx, cy), abilities.rule(m, "nearsight_range") * self.scale)
            s.blit(fog, (0, 0))
        if me.blind_until > m.time:
            flash = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            flash.fill((255, 255, 255, int(min(1.0, (me.blind_until - m.time) / 0.6) * 245)))
            s.blit(flash, (0, 0))
        self.draw_hud(me)
        if self.ui.buy_open:
            self.draw_buy(me)
        if self.ui.show_scores or m.phase == "over":
            self.draw_scores()
        pygame.display.flip()

    def sprite_cfg(self, p: PlayerState) -> dict:
        return dict(self.match.agents.get(p.agent, {}).get("sprites", {}))

    def slot_active(self, p: PlayerState, slot: str) -> bool:
        """An ability counts as active for its duration after use; X also while overdrive or immunity runs."""
        t = self.match.time
        if slot == "X" and (p.overdrive_until > t or p.immune_until > t):
            return True
        cast_t, cast_slot = self.ui.last_cast.get(p.pid, (-99.0, ""))
        if cast_slot != slot:
            return False
        ab = self.match.agents.get(p.agent, {}).get("abilities", {}).get(slot, {})
        return t - cast_t < float(ab.get("duration", 0.0)) and float(ab.get("duration", 0.0)) <= 15.0

    def character_state(self, p: PlayerState, me: PlayerState) -> tuple[str, float, float]:
        """(state, clock, speed factor) after the priority list of CHARACTER_SHEETS.md."""
        m, t, enemy = self.match, self.match.time, p.team != me.team
        if not p.alive:
            since = t - self.ui.died_at.get(p.pid, -99.0)
            dying = self.chars.duration(p.agent, "dying", enemy)
            return ("dying", since, 1.0) if since < dying else ("dead", 0.0, 1.0)
        if m.phase == "over" and m.match_winner == p.team:
            return "victory", t, 1.0
        if p.plant_progress > 0:
            return "plant", t, 1.0
        if p.defuse_progress > 0:
            return "defuse", t, 1.0
        cfg = self.sprite_cfg(p)
        for slot, name in dict(cfg.get("mechanics", {})).items():
            if self.slot_active(p, slot):
                return f"mech_{name}", t, 1.0
        cast_t, slot = self.ui.last_cast.get(p.pid, (-99.0, ""))
        if slot:
            tag = f"cast_{slot.lower()}"
            since = t - cast_t
            if since < self.chars.duration(p.agent, tag, enemy):
                return tag, since, 1.0
            if self.slot_active(p, slot):
                return f"channel_{slot.lower()}", since, 1.0
        weapon = m.weapons.get(p.weapon.key) if p.weapon else None
        if p.reload_until > t and weapon:
            return "reload", 1 - (p.reload_until - t) / max(weapon.reload, 0.01), 1.0
        if p.equip_until > t and weapon:
            return "equip", 1 - (p.equip_until - t) / max(weapon.equip, 0.01), 1.0
        shot = t - self.ui.last_shot.get(p.pid, -99.0)
        if shot < self.chars.duration(p.agent, "shoot", enemy):
            return ("melee" if weapon and weapon.slot == "melee" else "shoot"), shot, 1.0
        hit = t - self.ui.last_hit.get(p.pid, -99.0)
        if hit < self.chars.duration(p.agent, "flinch", enemy):
            return "flinch", hit, 1.0
        prev_z = self.ui.prev_z.get(p.pid, 0.0)
        self.ui.prev_z[p.pid] = p.z
        if prev_z > 0.05 and p.z <= 0.001:
            self.ui.landed_at[p.pid] = t
        if p.z > 0.001:
            return ("jump" if p.vz > 0 else "fall"), t, 1.0
        landed = t - self.ui.landed_at.get(p.pid, -99.0)
        if landed < self.chars.duration(p.agent, "land", enemy):
            return "land", landed, 1.0
        speed = p.vel.length()
        run = float(m._mv["run_speed"])
        if p.crouching:
            return ("crouch_walk" if speed > 0.3 else "crouch"), t, 1.0
        if speed > 0.5:
            return "walk", t, max(0.4, min(1.0, speed / run))
        return "idle", t, 1.0

    def character_frame(self, p: PlayerState, me: PlayerState) -> pygame.Surface | None:
        state, clock, speed = self.character_state(p, me)
        form = None
        for slot, name in dict(self.sprite_cfg(p).get("forms", {})).items():
            if self.slot_active(p, slot):
                form = str(name)
        return self.chars.frame(p.agent, state, p.team != me.team, self.scale, clock, form=form, speed=speed)

    def draw_projectile(self, e: Effect, me: PlayerState) -> bool:
        """Thrown ability in flight: moves from the thrower to the target on a small arc. True while flying."""
        assert e.a is not None
        flight = min(0.6, (e.until - e.start) * 0.8)  # lands shortly before it goes off
        progress = (self.match.time - e.start) / max(flight, 1e-6)
        if progress >= 1.0:
            return False
        pos = e.a + (e.pos - e.a) * progress
        x, y = self.to_screen(pos, me)
        y -= math.sin(progress * math.pi) * self.scale * 0.8  # lift on screen to read as a throw
        rel, size_m = ("fx/ability/grenade.png", (6 / 16, 5 / 16)) if e.kind == "blast" else ("fx/ability/projectile_orb.png", (12 / 16, 6 / 16))
        size = (max(1, round(size_m[0] * self.scale)), max(1, round(size_m[1] * self.scale)))
        img = self.bank.scaled(rel, size)
        if img is not None:
            self.screen.blit(img, (x - size[0] / 2, y - size[1] / 2))
        else:
            pygame.draw.circle(self.screen, C_SITE, (x, y), 4)
        dot = self.bank.scaled("fx/ability/arc_dot.png", (3, 3))
        if dot is not None:
            for i in range(1, 6):  # remaining path as dots
                q = progress + (1 - progress) * i / 6
                dx, dy = self.to_screen(e.a + (e.pos - e.a) * q, me)
                self.screen.blit(dot, (dx - 1, dy - 1 - math.sin(q * math.pi) * self.scale * 0.8))
        return True

    def radius_ring(self, pos: Vec, radius: float, color: tuple[int, int, int], me: PlayerState) -> None:
        x, y = self.to_screen(pos, me)
        d = max(2, round(2 * radius * self.scale))
        img = self.bank.tinted("fx/radius_ring.png", (d, d), 0, 0, color)
        if img is not None:
            self.screen.blit(img, (x - d / 2, y - d / 2))
        else:
            pygame.draw.circle(self.screen, color, (x, y), d / 2, 1)

    def panel(self, rel: str, rect: pygame.Rect) -> None:
        """Semi-transparent 9-slice HUD panel (8 px corners, drawn at 1x)."""
        draw_nine_slice(self.screen, self.bank, rel, rect, 8, 1)

    def draw_figure_fx(self, p: PlayerState, at: tuple[float, float]) -> None:
        """Effects in the 16x32 figure cell, centred on the player: one-shots from events, loops while active."""
        t = self.match.time
        size = (round(self.scale), round(2 * self.scale))
        active: list[tuple[str, float]] = []
        keep = []
        for pid, name, start, duration in self.ui.figure_fx:
            if t - start > duration:
                continue
            keep.append((pid, name, start, duration))
            if pid == p.pid:
                active.append((name, (t - start) / duration))
        self.ui.figure_fx = keep
        if p.heal_left > 0:
            active.append(("heal", (t * 6 % 3) / 3))
        if p.immune_until > t:
            active.append(("immunity_aura", (t * 4 % 2) / 2))
        for name, progress in active:
            img = self.bank.strip_frame(f"fx/ability/{name}.png", size, progress, 16)
            if img is not None:
                self.screen.blit(img, (at[0] - size[0] / 2, at[1] - size[1] / 2))

    def draw_bursts(self, me: PlayerState) -> None:
        """Short-lived explosions, wave lines, one-shot effects, dash trails and anchor markers."""
        s, t = self.screen, self.match.time
        live = []
        for rel, pos, start, duration, frame_w, size_m in self.ui.oneshots:
            age = t - start
            if age > duration or age < 0:
                continue
            live.append((rel, pos, start, duration, frame_w, size_m))
            size = (max(1, round(size_m[0] * self.scale)), max(1, round(size_m[1] * self.scale)))
            img = self.bank.strip_frame(rel, size, age / duration, frame_w)
            if img is not None:
                x, y = self.to_screen(pos, me)
                s.blit(img, (x - size[0] / 2, y - size[1] / 2))
        self.ui.oneshots = live[-200:]
        for p in self.match.players.values():
            if p.alive and p.dash_until > t and p.vel.length() > 0.5:
                back = p.pos - p.vel.normalized() * 0.8
                size = (round(self.scale), round(2 * self.scale))
                trail = self.bank.strip_frame("fx/gleiten_spur.png", size, (t * 10) % 1.0, 16)
                if trail is not None:
                    x, y = self.to_screen(back, me)
                    s.blit(trail, (x - size[0] / 2, y - size[1] / 2))
            if p.anchor is not None and p.anchor_until > t and p.team == me.team:
                size = (round(self.scale * 20 / 16), round(self.scale * 8 / 16))
                mark = self.bank.scaled("fx/ability/anchor_marker.png", size)
                if mark is not None:
                    x, y = self.to_screen(p.anchor, me)
                    s.blit(mark, (x - size[0] / 2, y - size[1] / 2))
        keep = []
        for pos, radius, start in self.ui.blasts:
            age = t - start
            if age > 0.5:
                continue
            keep.append((pos, radius, start))
            d = max(1, round(2 * radius * self.scale))
            img = self.bank.strip_frame("fx/blast.png", (d, d), age / 0.5, 64)
            x, y = self.to_screen(pos, me)
            if img is not None:
                s.blit(img, (x - d / 2, y - d / 2))
            else:
                pygame.draw.circle(s, C_SITE, (x, y), max(2, radius * self.scale * age / 0.5), 2)
        self.ui.blasts = keep
        waves = []
        for pid, end, start in self.ui.waves:
            age = t - start
            owner = self.match.players.get(pid)
            if age > 0.4 or owner is None:
                continue
            waves.append((pid, end, start))
            a, b = self.to_screen(owner.pos, me), self.to_screen(end, me)
            self.tile_line("fx/wave.png", a, b, 16, age / 0.4, (200, 220, 255), 4)
        self.ui.waves = waves

    def tile_line(self, rel: str, a: tuple[float, float], b: tuple[float, float], frame_w: int, progress: float,
                  fallback: tuple[int, int, int], width: int) -> None:
        """Tiles an effect strip along a screen line a→b (one tile = 1 m)."""
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        tile_px = max(1, round(self.scale))
        img = self.bank.raw(rel)
        if img is None or length < 1:
            pygame.draw.line(self.screen, fallback, a, b, width)
            return
        height = max(1, round(img.get_height() * self.scale / 16))
        tile = self.bank.strip_frame(rel, (tile_px, height), progress, frame_w)
        assert tile is not None
        strip = pygame.Surface((max(1, round(length)), height), pygame.SRCALPHA)
        for x in range(0, strip.get_width(), tile_px):
            strip.blit(tile, (x, 0))
        rotated = pygame.transform.rotate(strip, math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0])))
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        self.screen.blit(rotated, (mid[0] - rotated.get_width() / 2, mid[1] - rotated.get_height() / 2))

    def draw_map_texture(self, me: PlayerState) -> None:
        """Cut the map image around the player and rotate it with the camera."""
        assert self.map_surface is not None
        cx, cy = self.to_screen(me.pos, me)
        radius = math.ceil(math.hypot(max(cx, self.w - cx), max(cy, self.h - cy))) + 2
        size = 2 * radius
        if self._crop is None or self._crop.get_width() != size:
            self._crop = pygame.Surface((size, size)).convert()
        self._crop.fill(C_BG)
        mx = me.pos.x * self.scale
        my = (self.match.world.height - me.pos.y) * self.scale
        self._crop.blit(self.map_surface, (radius - mx, radius - my))
        nx, ny = self.to_screen(me.pos + Vec(0, 1), me)
        north = math.degrees(math.atan2(-(ny - cy), nx - cx))
        rotated = pygame.transform.rotate(self._crop, north - 90)
        self.screen.blit(rotated, (cx - rotated.get_width() / 2, cy - rotated.get_height() / 2))

    def draw_live_objects(self, me: PlayerState) -> None:
        """Animated or phase-dependent map objects (spawn barrier), rotated with the camera."""
        from gameplay.world import load_things
        objects = load_things()[0]
        for o in self.match.world.objects:
            spec = objects.get(o.key, {})
            if spec.get("door"):
                self.draw_door(o, spec, me)
                continue
            if not (int(spec.get("frames", 1)) > 1 or spec.get("buy_phase_only")):
                continue
            if spec.get("buy_phase_only") and self.match.phase != "buy":
                continue
            frames = int(spec.get("frames", 1))
            index = int(self.match.time * float(spec.get("fps", 4))) % frames
            w_m, h_m = spec.get("size", (1.0, 1.0))
            tile = self.bank.scaled(str(spec.get("tile", "")), (max(1, round(w_m * self.scale)), max(1, round(h_m * self.scale))),
                                    index, self.bank.raw(str(spec.get("tile", ""))).get_width() // frames if self.bank.raw(str(spec.get("tile", ""))) else 0)
            if tile is None:
                continue
            w_px = max(1, round((o.rect.x1 - o.rect.x0) * self.scale))
            h_px = max(1, round((o.rect.y1 - o.rect.y0) * self.scale))
            strip = pygame.Surface((w_px, h_px), pygame.SRCALPHA)
            for y in range(0, h_px, tile.get_height()):
                for x in range(0, w_px, tile.get_width()):
                    strip.blit(tile, (x, y))
            cx, cy = self.to_screen(me.pos, me)
            nx, ny = self.to_screen(me.pos + Vec(0, 1), me)
            north = math.degrees(math.atan2(-(ny - cy), nx - cx))
            rotated = pygame.transform.rotate(strip, north - 90)
            ox, oy = self.to_screen(o.rect.center, me)
            self.screen.blit(rotated, (ox - rotated.get_width() / 2, oy - rotated.get_height() / 2))

    def draw_door(self, o: object, spec: dict, me: PlayerState) -> None:
        """Door sprite (open or closed) rotated with the camera."""
        rect = o.rect  # type: ignore[attr-defined]
        is_open = rect in self.match.open_doors
        rel = str(spec.get("open_tile" if is_open else "tile", ""))
        img = self.bank.raw(rel)
        w_px = max(1, round((rect.x1 - rect.x0) * self.scale))
        h_px = max(1, round((rect.y1 - rect.y0) * self.scale))
        if img is None:
            surf = pygame.Surface((w_px, h_px), pygame.SRCALPHA)
            surf.fill((90, 110, 120, 120 if is_open else 255))
        else:
            rot = int(o.rot)  # type: ignore[attr-defined]
            src = pygame.transform.rotate(img, -rot) if rot else img
            surf = pygame.transform.scale(src, (w_px, h_px))
        cx, cy = self.to_screen(me.pos, me)
        nx, ny = self.to_screen(me.pos + Vec(0, 1), me)
        rotated = pygame.transform.rotate(surf, math.degrees(math.atan2(-(ny - cy), nx - cx)) - 90)
        ox, oy = self.to_screen(rect.center, me)
        self.screen.blit(rotated, (ox - rotated.get_width() / 2, oy - rotated.get_height() / 2))

    def draw_map_placeholder(self, me: PlayerState) -> None:
        from gameplay.geometry import Rect
        s, wm = self.screen, self.match.world
        pygame.draw.polygon(s, C_FLOOR, self.poly(Rect(0, 0, wm.width, wm.height), me))
        for site in wm.sites:
            pygame.draw.polygon(s, (70, 62, 40), self.poly(site.rect, me))
        for r in wm.ramps:
            pygame.draw.polygon(s, C_RAMP, self.poly(r, me))
        for w in wm.walls:
            if w.rect.x0 < -0.5 or w.rect.y0 < -0.5 or w.rect.x1 > wm.width + 0.5 or w.rect.y1 > wm.height + 0.5:
                continue
            col = C_CRATE if w.height == 1 and w.blocks_sight is False else (C_WALL_THIN if w.penetration == 0 else C_WALL)
            if any(pl.rect == w.rect for pl in wm.platforms):
                col = C_PLATFORM
            pygame.draw.polygon(s, col, self.poly(w.rect, me))

    def draw_effect(self, e: Effect, me: PlayerState) -> None:
        s = self.screen
        ex, ey = self.to_screen(e.pos, me)
        if e.kind == "zone" and e.start > self.match.time:
            self.radius_ring(e.pos, e.radius, C_MUTED, me)
            return
        if e.kind in ("blast", "flash") and e.a is not None and e.until > e.start:
            if self.draw_projectile(e, me):
                return
        if e.kind == "flash":
            return  # a flash without flight data is not drawn (it pops with its own effect)
        if e.kind == "blast":
            left = max(0.0, e.until - self.match.time)
            self.radius_ring(e.pos, e.radius, C_ENEMY if e.team != me.team else C_SITE, me)
            nade = self.bank.scaled("fx/ability/grenade.png", (max(1, round(self.scale * 6 / 16)), max(1, round(self.scale * 5 / 16))))
            if nade is not None:
                s.blit(nade, (ex - nade.get_width() / 2, ey - nade.get_height() / 2))
            else:
                pygame.draw.circle(s, C_SITE, (ex, ey), 4 + int(left * 6) % 4)
            return
        if e.kind == "alarm":
            size = max(1, round(self.scale))
            img = self.bank.scaled("fx/alarm.png", (size, size), int(self.match.time * 2) % 2, 16)
            if img is not None:
                s.blit(img, (ex - size / 2, ey - size / 2))
            else:
                pygame.draw.circle(s, C_ALLY, (ex, ey), 5)
            self.radius_ring(e.pos, e.radius, (60, 140, 140), me)
            return
        if e.kind == "tripwire" and e.a and e.b:
            a, b = self.to_screen(e.a, me), self.to_screen(e.b, me)
            self.tile_line("fx/tripwire.png", a, b, 16, 0.0, C_ALLY, 1)
            node_px = max(1, round(self.scale * 6 / 16))
            node = self.bank.scaled("fx/tripwire_node.png", (node_px, node_px))
            if node is not None:
                for x, y in (a, b):
                    s.blit(node, (x - node_px / 2, y - node_px / 2))
            return
        if e.kind == "zone":
            d = max(1, round(2 * e.radius * self.scale))
            status = str(e.props.get("status") or "")
            frame = int(self.match.time * 6) % 3
            img = self.bank.tinted("fx/zone.png", (d, d), frame, 64, STATUS_TINT.get(status, (200, 200, 200)))
            if img is not None:
                s.blit(img, (ex - d / 2, ey - d / 2))
            else:
                pygame.draw.circle(s, (120, 80, 170), (ex, ey), e.radius * self.scale, 3)
            return
        if e.kind == "smoke" and 0 < self.match.time - e.start < 0.5:
            d = max(1, round(2 * e.radius * self.scale))
            img = self.bank.strip_frame("fx/dunst_aufbau.png", (d, d), (self.match.time - e.start) / 0.5, 64)
            if img is not None:
                s.blit(img, (ex - d / 2, ey - d / 2))
                return
        art = {"smoke": "fx/dunst.png"}.get(e.kind)
        if art:
            d = max(1, round(2 * e.radius * self.scale))
            img = self.bank.scaled(art, (d, d))
            if img is not None:
                s.blit(img, (ex - d / 2, ey - d / 2))
            elif e.kind == "smoke":
                pygame.draw.circle(s, C_SMOKE, (ex, ey), e.radius * self.scale)
            else:
                pygame.draw.circle(s, (120, 80, 170), (ex, ey), e.radius * self.scale, 3)
        elif e.kind == "sensor":
            pulse_d = max(1, round(2 * self.scale))
            pulse = self.bank.strip_frame("fx/lauscher_puls.png", (pulse_d, pulse_d), (self.match.time % 1.0), 32)
            if pulse is not None:
                s.blit(pulse, (ex - pulse_d / 2, ey - pulse_d / 2))
            size = max(1, round(self.scale * 0.6))
            img = self.bank.scaled("fx/lauscher.png", (size, size))
            if img is not None:
                s.blit(img, (ex - size / 2, ey - size / 2))
            else:
                pygame.draw.circle(s, C_ALLY if e.team == me.team else C_ENEMY, (ex, ey), 5)
            self.radius_ring(e.pos, e.radius, (60, 140, 140), me)
        elif e.kind == "wall" and e.a and e.b:
            a, b = self.to_screen(e.a, me), self.to_screen(e.b, me)
            length = math.hypot(b[0] - a[0], b[1] - a[1])
            tile_px = max(1, round(self.scale))
            building = 0 < self.match.time - e.start < 0.4
            tile = (self.bank.strip_frame("fx/schleier_aufbau.png", (tile_px, tile_px), (self.match.time - e.start) / 0.4, 16)
                    if building else None) or self.bank.scaled("fx/schleier.png", (tile_px, tile_px))
            if tile is None or length < 1:
                pygame.draw.line(s, (180, 190, 210), a, b, 8)
                return
            strip = pygame.Surface((max(1, round(length)), tile_px), pygame.SRCALPHA)
            for x in range(0, strip.get_width(), tile_px):
                strip.blit(tile, (x, 0))
            angle = math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0]))
            rotated = pygame.transform.rotate(strip, angle)
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            s.blit(rotated, (mid[0] - rotated.get_width() / 2, mid[1] - rotated.get_height() / 2))

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

    def view_player(self, me: PlayerState) -> PlayerState:
        """While dead in a live round, the camera and HUD follow a living teammate (click = next)."""
        if me.alive or self.match.phase not in ("live", "planted"):
            return me
        mates = sorted((p for p in self.match.players.values() if p.team == me.team and p.alive and p.pid != me.pid),
                       key=lambda p: p.pid)
        if not mates:
            return me
        return mates[self.spectate_index % len(mates)]

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

    def draw_score_pips(self, me: PlayerState) -> None:
        """Round pips left (own wins) and right (enemy wins) of the timer, up to the rounds needed to win."""
        m = self.match
        need = max(1, m.win_rounds)
        px = 12
        mine, theirs = m.score[me.team], m.score[1 - me.team]
        for side, won, name in ((-1, mine, "round_win"), (1, theirs, "round_loss")):
            for i in range(need):
                rel = f"ui/icons/{name if i < won else 'round_empty'}.png"
                img = self.bank.scaled(rel, (px, px))
                x = self.w / 2 + side * (130 + i * (px + 3)) - (px if side < 0 else 0)
                if img is not None:
                    self.screen.blit(img, (x, 26))
                else:
                    pygame.draw.rect(self.screen, C_ALLY if side < 0 and i < won else C_ENEMY if i < won else C_MUTED,
                                     (x, 26, px, px), 0 if i < won else 1)

    def draw_bar(self, icon: str, fill: str, value: int, top: int, pos: tuple[int, int]) -> None:
        """HUD bar: icon (16x16), empty bar, fill clipped to value/top (96x12), number; native size at k = 2."""
        x, y = pos
        k = 2
        sym = self.bank.scaled(f"ui/hud/{icon}.png", (8 * k, 8 * k))
        empty = self.bank.scaled("ui/hud/balken_leer.png", (48 * k, 6 * k))
        full = self.bank.scaled(f"ui/hud/{fill}.png", (48 * k, 6 * k))
        if sym is None or empty is None or full is None:
            self.text(f"{icon.title()} {value}", (x, y))
            return
        self.screen.blit(sym, (x, y))
        self.screen.blit(empty, (x + 30, y + 3))
        width = round(full.get_width() * max(0.0, min(1.0, value / max(top, 1))))
        if width > 0:
            self.screen.blit(full, (x + 30, y + 3), (0, 0, width, full.get_height()))
        self.text(str(value), (x + 36 + empty.get_width(), y))

    def build_minimap_static(self, k: float) -> pygame.Surface:
        """Walls, crates and site letters of the minimap; drawn once per map."""
        wm = self.match.world
        panel = pygame.Surface((round(wm.width * k), round(wm.height * k)), pygame.SRCALPHA)
        if self.bank.raw("ui/minimap/frame.png") is None:
            panel.fill((20, 20, 28, 190))

        def pt(v: Vec) -> tuple[float, float]:
            return v.x * k, (wm.height - v.y) * k

        wall_tile = self.bank.scaled("ui/minimap/wall.png", (4, 4))
        crate_tile = self.bank.scaled("ui/minimap/crate.png", (4, 4))
        for w in wm.walls:
            if w.rect.x0 < -0.5 or w.rect.y0 < -0.5 or w.rect.x1 > wm.width + 0.5 or w.rect.y1 > wm.height + 0.5:
                continue
            x0, y1 = pt(Vec(w.rect.x0, w.rect.y0))
            x1, y0 = pt(Vec(w.rect.x1, w.rect.y1))
            rect = pygame.Rect(round(x0), round(y0), max(1, round(x1 - x0)), max(1, round(y1 - y0)))
            tile = wall_tile if w.height > 1 else crate_tile
            if tile is not None:
                panel.set_clip(rect)
                for ty in range(rect.y - rect.y % 4, rect.bottom, 4):
                    for tx in range(rect.x - rect.x % 4, rect.right, 4):
                        panel.blit(tile, (tx, ty))
                panel.set_clip(None)
            else:
                pygame.draw.rect(panel, (120, 116, 132, 255) if w.height > 1 else (80, 96, 108, 255), rect)
        for site in wm.sites:
            x, y = pt(site.rect.center)
            lbl = self.font.render(site.name, True, C_SITE)
            panel.blit(lbl, (x - lbl.get_width() / 2, y - lbl.get_height() / 2))

        return panel

    def draw_minimap(self, me: PlayerState) -> None:
        """North-up overview in the top-left corner: walls, own team, visible enemies, bomb, smokes."""
        m, wm = self.match, self.match.world
        size = 190
        k = size / max(wm.width, wm.height)
        ox, oy = 12, 44
        if self._minimap_static is None:
            self._minimap_static = self.build_minimap_static(k)
        panel = self._minimap_static.copy()
        framed = self.bank.raw("ui/minimap/frame.png") is not None
        if framed:
            draw_nine_slice(self.screen, self.bank, "ui/minimap/frame.png", pygame.Rect(ox - 6, oy - 6, panel.get_width() + 12, panel.get_height() + 12), 8, 1)

        def pt(v: Vec) -> tuple[float, float]:
            return v.x * k, (wm.height - v.y) * k

        def icon(name: str, at: Vec, px: int = 12, angle: float | None = None) -> None:
            img = self.bank.scaled(f"ui/minimap/{name}.png", (px, px))
            x, y = pt(at)
            if img is None:
                pygame.draw.circle(panel, C_TEXT, (x, y), 3)
                return
            if angle is not None:
                img = pygame.transform.rotate(img, -angle)
            panel.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2))

        for e in m.effects:
            name = {"smoke": "dunst", "zone": "bann", "wall": "schleier"}.get(e.kind)
            if name:
                icon(name, e.pos, max(8, round(2 * max(e.radius, 1.0) * k)))
        if m.spike_pos is not None:
            icon("spike", m.spike_pos)
        for p in m.players.values():
            if p.pid == self.me:
                continue
            if p.team == me.team:
                icon("verbuendet" if p.alive else "tot", p.pos)
            elif p.alive and (p.visible if self.mode == "client" else m.can_see(me, p)):
                icon("feind", p.pos)
        icon("selbst", me.pos, 14, me.facing)
        self.screen.blit(panel, (ox, oy))

    def draw_crosshair(self, me: PlayerState) -> None:
        cx, cy = self.to_screen(me.pos + heading(me.facing) * self.cursor_depth, me)
        col = C_ENEMY if self.match.time < self.ui.hit_marker else (120, 255, 200)
        d = self.match.weapons.get(me.weapon.key) if me.weapon else None
        gap = 4 + (self.match.current_spread(me, d) * self.cursor_depth * math.pi / 180 * self.scale if d else 0)
        hit = "_hit" if self.match.time < self.ui.hit_marker else ""
        dot = self.bank.scaled(f"ui/crosshair/dot{hit}.png", (8, 8))
        arm = self.bank.scaled(f"ui/crosshair/arm{hit}.png", (4, 16))
        if dot is None or arm is None:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                pygame.draw.line(self.screen, col, (cx + dx * gap, cy + dy * gap), (cx + dx * (gap + 7), cy + dy * (gap + 7)), 2)
            pygame.draw.circle(self.screen, col, (cx, cy), 2)
            return
        for angle, (dx, dy) in ((0, (0, -1)), (90, (-1, 0)), (180, (0, 1)), (270, (1, 0))):
            img = pygame.transform.rotate(arm, angle)
            ax = cx + dx * (gap + 8) - img.get_width() / 2
            ay = cy + dy * (gap + 8) - img.get_height() / 2
            self.screen.blit(img, (ax, ay))
        self.screen.blit(dot, (cx - 4, cy - 4))

    def text(self, msg: str, pos: tuple[float, float], col=C_TEXT, big: bool = False, center: bool = False) -> None:
        img = (self.big if big else self.font).render(msg, True, col)
        x, y = pos
        if center:
            x -= img.get_width() / 2
        self.screen.blit(img, (x, y))

    def draw_hud(self, me: PlayerState) -> None:
        m = self.match
        self.panel("ui/hud/score_panel.png", pygame.Rect(self.w / 2 - 330, 4, 660, 76))
        self.panel("ui/hud/ability_panel.png", pygame.Rect(8, self.h - 160, 330, 154))
        self.panel("ui/hud/weapon_panel.png", pygame.Rect(self.w - 340, self.h - 84, 330, 78))
        left = m.phase_time_left()
        phase = {"buy": "Buy phase", "live": "", "planted": "Bomb planted", "end": "Round over", "over": "Match over"}.get(m.phase, "")
        mine, theirs = m.score[me.team], m.score[1 - me.team]
        if m.practice:
            st = self.stats
            acc = 100 * st["hits"] / st["shots"] if st["shots"] else 0
            heads = 100 * st["heads"] / st["hits"] if st["hits"] else 0
            self.text("Practice range", (self.w / 2, 12), big=True, center=True)
            self.text(f"shots {st['shots']} · hits {st['hits']} ({acc:.0f} %) · head {heads:.0f} % · B buys anywhere",
                      (self.w / 2, 54), C_MUTED, center=True)
        else:
            self.text(f"{mine}  {int(left) // 60}:{int(left) % 60:02d}  {theirs}", (self.w / 2, 12), big=True, center=True)
            self.draw_score_pips(me)
            side = "Attack" if m.side(me.team) == "attack" else "Defense"
            self.text(f"Round {m.round_no} · {side} {('· ' + phase) if phase else ''}", (self.w / 2, 54), C_MUTED, center=True)
        self.draw_bar("leben", "balken_leben", max(me.hp, 0), 100, (20, self.h - 40))
        self.draw_bar("schild", "balken_schild", me.armor, 50, (250, self.h - 40))
        self.draw_minimap(me)
        if me.weapon:
            d = m.weapons.get(me.weapon.key)
            name = d.name if d else me.weapon.key
            ammo = "" if not d or not d.is_gun else f"  {me.weapon.mag} / {me.weapon.reserve}"
            self.text(f"{name}{ammo}{'  reloading…' if me.reload_until > m.time else ''}", (self.w - 320, self.h - 40))
        self.text(f"{me.credits} ¤", (self.w - 320, self.h - 70), C_SITE)
        abil = m.agents[me.agent]["abilities"]
        parts = [f"{k} {abil[k]['name']} ×{me.charges.get(k, 0)}" for k in ("C", "Q", "E")]
        parts.append(f"X {abil['X']['name']} {me.ult_points}/{abil['X']['cost']}")
        icon_px = 32
        x = 20
        for k in ("C", "Q", "E", "X"):
            icon = self.bank.scaled(f"ui/faehigkeit_{me.agent}_{k}.png", (icon_px, icon_px))
            if icon is None:
                break
            ready = me.ult_points >= int(abil["X"]["cost"]) if k == "X" else me.charges.get(k, 0) > 0
            if not ready:
                icon = icon.copy()
                icon.fill((90, 90, 90, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(icon, (x, self.h - 112))
            label = f"{min(me.ult_points, int(abil['X']['cost']))}/{abil['X']['cost']}" if k == "X" else str(me.charges.get(k, 0))
            self.text(f"{k} {label}", (x, self.h - 76), C_MUTED)
            x += icon_px + 40
        else:
            x = -1
        if x != -1:
            self.text("   ".join(parts), (20, self.h - 70), C_MUTED)
        active = sorted(k for k, until in me.status.items() if until > m.time and k != "blind")
        sx = 20
        for k in active:
            icon = self.bank.scaled(f"ui/status/{k}.png", (24, 24))
            if icon is not None:
                self.screen.blit(icon, (sx, self.h - 150))
            self.text(k, (sx + 28, self.h - 147), C_ALLY if k == "stim" else C_ENEMY)
            sx += 28 + self.font.size(k)[0] + 16
        self.text(f"{m.agents[me.agent]['name']} · {m.world.callout_at(me.pos)}", (20, 16), C_MUTED)
        if m.spike_carrier == self.me:
            hint = self.bank.scaled("ui/hud/carrier_hint.png", (32, 32))
            if hint is not None:
                self.screen.blit(hint, (20, 242))
            self.text("You carry the bomb (hold F on A or B)", (60 if hint else 20, 248), C_SITE)
        prog = me.plant_progress / 4.0 if me.plant_progress else me.defuse_progress / 7.0
        if prog > 0:
            empty = self.bank.scaled("ui/hud/balken_leer.png", (192, 24))
            full = self.bank.scaled("ui/hud/balken_fortschritt.png", (192, 24))
            x0, y0 = self.w / 2 - 96, self.h / 2 + 60
            if empty is not None and full is not None:
                self.screen.blit(empty, (x0, y0))
                self.screen.blit(full, (x0, y0), (0, 0, round(192 * min(prog, 1)), 24))
            else:
                pygame.draw.rect(self.screen, C_MUTED, (x0, y0, 192, 10), 1)
                pygame.draw.rect(self.screen, C_SITE, (x0, y0, 192 * min(prog, 1), 10))
        y = 90
        self.ui.feed = [f for f in self.ui.feed if m.time <= f[0]]
        for _, msg, killer, victim, head in self.ui.feed:
            x = self.w - 420
            mine = me.name and me.name in msg
            width = 28 * 2 + 16 + self.font.size(msg)[0] + (28 if head else 0)
            self.panel("ui/hud/killfeed_row_self.png" if mine else "ui/hud/killfeed_row.png", pygame.Rect(x - 8, y - 6, width, 32))
            for agent in (killer, victim):
                icon = self.bank.scaled(f"agents/{agent}/{agent}_killfeed.png", (24, 24)) if agent else None
                if icon is not None:
                    self.screen.blit(icon, (x, y - 2))
                x += 28
            self.text(msg, (x + 4, y))
            if head:
                mark = self.bank.scaled("ui/hud/kopfschuss.png", (16, 16))
                if mark is not None:
                    self.screen.blit(mark, (x + 8 + self.font.size(msg)[0], y + 2))
            y += 28
        if self.status:
            self.text(self.status, (self.w / 2, self.h / 2 - 110), C_ENEMY, center=True)

        if m.time < self.ui.banner[0]:
            art = self.bank.raw(f"ui/banner/{self.ui.banner_art}.png") if self.ui.banner_art else None
            y = 96
            if art is not None:
                k = 2  # banners are 32 px high
                img = self.bank.scaled(f"ui/banner/{self.ui.banner_art}.png", (art.get_width() * k, art.get_height() * k))
                if img is not None:
                    self.screen.blit(img, (self.w / 2 - img.get_width() / 2, y))
                    y += img.get_height() + 8
            self.text(self.ui.banner[1], (self.w / 2, y), C_SITE, big=art is None, center=True)
        own = m.players.get(self.me)
        if own is not None and not own.alive and m.phase in ("live", "planted"):
            watching = f"Watching {me.name} – click for the next teammate" if me.pid != own.pid else "Eliminated – waiting for the next round"
            self.text(watching, (self.w / 2, self.h / 2 - 80), C_ENEMY, center=True)
        if m.phase == "buy":
            self.text("B: buy menu", (20, 272), C_MUTED)

    BUY_COLUMNS = (("sidearm", "Sidearms"), ("smg", "SMGs"), ("shotgun", "Shotguns"), ("rifle", "Rifles"),
                   ("sniper", "Snipers"), ("heavy", "Heavy"), ("gear", "Gear"))

    def buy_layout(self) -> list[tuple[pygame.Rect, str, str]]:
        """Cards per column: weapons by category, then armor and the agent's buyable abilities under Gear."""
        m = self.match
        columns: dict[str, list[tuple[str, str]]] = {c: [] for c, _ in self.BUY_COLUMNS}
        for key, d in sorted(m.weapons.items(), key=lambda kv: kv[1].price):
            if d.slot != "melee":
                columns.setdefault(d.category if d.category in columns else "rifle", []).append((key, f"{d.name}  {d.price}"))
        for key, a in m.armor.items():
            columns["gear"].append((key, f"{a.name}  {a.price}"))
        me = m.players.get(self.me)
        for k in (("C", "Q") if me else ()):
            ab = m.agents[me.agent]["abilities"][k]
            columns["gear"].append((k, f"{k} {ab['name']}  {ab['price']}"))
        out = []
        col_w, card_h, gap = 158, 76, 8
        left = (self.w - len(self.BUY_COLUMNS) * (col_w + gap) + gap) / 2
        for ci, (cat, _) in enumerate(self.BUY_COLUMNS):
            for ri, (key, label) in enumerate(columns.get(cat, [])):
                out.append((pygame.Rect(left + ci * (col_w + gap), 150 + ri * (card_h + gap), col_w, card_h), key, label))
        return out

    def buy_item_at(self, pos: tuple[int, int]) -> str | None:
        for r, key, _ in self.buy_layout():
            if r.collidepoint(pos):
                return key
        return None

    def item_price(self, me: PlayerState, key: str) -> int:
        m = self.match
        if key in m.weapons:
            return m.weapons[key].price
        if key in m.armor:
            return m.armor[key].price
        return int(m.agents[me.agent]["abilities"].get(key, {}).get("price", 0))

    def item_owned(self, me: PlayerState, key: str) -> bool:
        m = self.match
        if key in m.weapons:
            return any(ws.key == key for ws in me.weapons.values())
        if key in m.armor:
            return me.armor >= m.armor[key].points
        ab = m.agents[me.agent]["abilities"].get(key, {})
        return me.charges.get(key, 0) >= int(ab.get("max", 1))

    def item_picture(self, me: PlayerState, key: str) -> pygame.Surface | None:
        if key in self.match.weapons:
            return self.bank.scaled(f"weapons/val2d/{key}_kauf.png", (128, 48))
        if key in self.match.armor:
            return self.bank.scaled(f"ui/buy/{ {'leicht': 'vest_light', 'schwer': 'vest_heavy'}.get(key, key)}.png", (128, 48))
        return self.bank.scaled(f"ui/faehigkeit_{me.agent}_{key}.png", (36, 36))

    def draw_buy(self, me: PlayerState) -> None:
        s = self.screen
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((10, 10, 16, 200))
        s.blit(overlay, (0, 0))
        panel = pygame.Rect(30, 40, self.w - 60, self.h - 80)
        draw_nine_slice(s, self.bank, "ui/menu/panel.png", panel, 6, 3)
        open_ = self.match.phase == "buy"
        self.text("Buy menu" + ("" if open_ else " (only in the buy phase, in spawn)"), (70, 64), C_TEXT, big=True)
        credits_icon = self.bank.scaled("ui/icons/credits_large.png", (32, 32))
        if credits_icon is not None:
            s.blit(credits_icon, (self.w - 260, 66))
        self.text(f"{me.credits}", (self.w - 220, 70), C_SITE, big=True)
        layout = self.buy_layout()
        col_w, gap = 158, 8
        left = (self.w - len(self.BUY_COLUMNS) * (col_w + gap) + gap) / 2
        for ci, (cat, title) in enumerate(self.BUY_COLUMNS):
            x = left + ci * (col_w + gap)
            icon = self.bank.scaled(f"ui/buy/cat_{'abilities' if cat == 'gear' else cat}.png", (32, 32))
            if icon is not None:
                s.blit(icon, (x, 112))
            self.text(title, (x + 38, 118), C_MUTED)
        mouse = pygame.mouse.get_pos()
        for r, key, label in layout:
            price = self.item_price(me, key)
            owned = self.item_owned(me, key)
            affordable = me.credits >= price and open_
            state = "button_disabled" if not affordable and not owned else \
                "button_pressed" if owned else "button_hover" if r.collidepoint(mouse) else "button"
            if not draw_nine_slice(s, self.bank, f"ui/menu/{state}.png", r, 4, 2):
                pygame.draw.rect(s, (60, 58, 72) if state == "button_hover" else (36, 35, 45), r)
                pygame.draw.rect(s, C_MUTED, r, 1)
            pic = self.item_picture(me, key)
            if pic is not None:
                s.blit(pic, (r.centerx - pic.get_width() / 2, r.y + 4))
            name = label.rsplit("  ", 1)[0]
            self.text(name, (r.x + 10, r.bottom - 22), C_TEXT if affordable or owned else C_MUTED)
            cost = self.font.render(str(price), True, C_SITE if affordable else C_MUTED)
            s.blit(cost, (r.right - cost.get_width() - 10, r.bottom - 22))
        self.text("Click buys · B closes", (70, self.h - 76 + 10), C_MUTED)

    def draw_scores(self) -> None:
        m = self.match
        me = m.players.get(self.me)
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((10, 10, 16, 200))
        self.screen.blit(overlay, (0, 0))
        title = "Match over" if m.phase == "over" else "Scoreboard"
        if m.phase == "over":
            self.text("Enter or Esc: back to the menu", (self.w / 2, self.h - 40), C_SITE, center=True)
        if m.phase == "over" and me is not None:
            title += ": won" if m.match_winner == me.team else ": lost"
        self.text(f"{title}   {m.score[0]} : {m.score[1]}", (self.w / 2, 92), C_TEXT, big=True, center=True)
        x, w, y = self.w / 2 - 320, 640, 146
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


def main() -> None:
    ap = argparse.ArgumentParser(description="Play Val2d against bots or online")
    ap.add_argument("--agent", default="kestrel", help="agent key from config/agents.py")
    ap.add_argument("--team-size", type=int, default=5, choices=range(1, 6))
    ap.add_argument("--rounds", type=int, default=13)
    ap.add_argument("--map", default="werkhof")
    ap.add_argument("--all-around", action="store_true", help="Lobby rule: all-around sight")
    ap.add_argument("--sound-rings", action="store_true", help="Lobby rule: sound rings")
    ap.add_argument("--name", default="Player", help="Name in the match (up to 16 characters)")
    net = ap.add_mutually_exclusive_group()
    net.add_argument("--host", action="store_true", help="Open a network match (host = player 1)")
    net.add_argument("--host-online", action="store_true", help="Open an internet match with a join code")
    net.add_argument("--join", metavar="CODE|ADDRESS[:PORT]", help="Join a match by join code or LAN address")
    net.add_argument("--find", action="store_true", help="Find a match on the local network and join")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-menu", action="store_true", help="Start the practice match directly, without the main menu")
    ap.add_argument("--range", dest="practice", action="store_true", help="Practice range instead of a match")
    args = ap.parse_args()
    args.online = bool(args.host_online)
    if args.host_online:
        args.host = True
    if not (args.host or args.join or args.find or args.no_menu):
        run_menu(args)
        return
    if args.find:
        print("Looking for matches on the local network …")
        found = discover()
        if not found:
            print("No match found. Is the host running play.py --host or server.py, and are both on the same network?")
            return
        for address, port, host_name in found:
            print(f"  {host_name}  {address}:{port}")
        address, port, host_name = found[0]
        print(f"Joining {host_name} …")
        args.join = f"{address}:{port}"
    try:
        game = Game(args)
    except (OSError, ConnectionError) as exc:
        print(f"No connection: {exc}")
        pygame.quit()
        return
    game.run()
    pygame.quit()


def display_mode(fullscreen: bool) -> pygame.Surface:
    """1280x720 game area; fullscreen scales it to the monitor (nearest, keeps the pixel look)."""
    flags = (pygame.FULLSCREEN | pygame.SCALED) if fullscreen else 0
    try:
        return pygame.display.set_mode((1280, 720), flags)
    except pygame.error as exc:
        warnings.warn(f"Fullscreen not available ({exc}); using a window.")
        return pygame.display.set_mode((1280, 720))


def run_menu(args: argparse.Namespace) -> None:
    """Main menu loop: each match returns to the menu; quitting the menu ends the program."""
    from menu import MainMenu
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption("Val2d")
    try:
        font, big = pygame.font.Font(str(FONT_PATH), 18), pygame.font.Font(str(FONT_PATH), 36)
    except (OSError, FileNotFoundError):
        font, big = pygame.font.Font(None, 22), pygame.font.Font(None, 44)
    menu = MainMenu(screen, font, big, args)
    while True:
        chosen = menu.run()
        if chosen is None:
            break
        try:
            Game(chosen).run()
        except (OSError, ConnectionError) as exc:
            menu.status = f"No connection: {exc}"
            warnings.warn(menu.status)
        screen = display_mode(bool(getattr(menu.args, "fullscreen", False)))
        menu.screen = screen
    pygame.quit()


if __name__ == "__main__":
    main()
