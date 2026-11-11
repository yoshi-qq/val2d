"""Val2d spielen: Übungspartie gegen Bots auf dem eigenen Spielkern (gameplay).

Aufruf:  python play.py [--agent kestrel|marrow] [--team-size 1..5] [--rounds 13] [--map werkhof|gasse]
                        [--all-around] [--sound-rings]
Im Netz:  python play.py --host            Partie öffnen (Host = Spieler 1), Enter startet
          python play.py --find            Partie im lokalen Netz suchen und beitreten
          python play.py --join 192.168.1.20[:9009]
Eigener Server-Prozess: python server.py (siehe dort).
Steuerung: WASD laufen, Umschalt gehen, Strg ducken, Leertaste springen, Maus links schießen,
Maus waagerecht drehen, Maus senkrecht Zieltiefe, R nachladen, 1/2/3 Waffe, C/Q/E/X Fähigkeiten,
F halten Spike legen/entschärfen, B Kaufmenü, Tab Punktestand, Esc beenden.
Grafik: Platzhalter (Kreise und Flächen), bis die Design-Sitzung Sprites liefert (docs/SPRITES.md).
"""
from __future__ import annotations

import argparse
import math
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import pygame

from gameplay.bots import BotDirector
from gameplay.data import LobbySettings, load_config
from gameplay.geometry import Vec, heading
from gameplay.match import Command, GameEvent, Match, PlayerState
from gameplay.net import DEFAULT_PORT, Client, apply_snapshot, discover, events_from_json
from gameplay.session import HostSession
from gameplay.world import load_map

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
    feed: list[tuple[float, str]] = field(default_factory=list)
    banner: tuple[float, str] = (0.0, "")
    hit_marker: float = 0.0


class Sound:
    """Synthetische Platzhalter-Töne mit Stereo-Panorama und Entfernungsdämpfung."""

    def __init__(self) -> None:
        self.ok = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
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
        except Exception as exc:  # Ton ist nicht spielentscheidend
            warnings.warn(f"Ton deaktiviert: {exc}")

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
            ch.set_volume(left, right)


class Game:
    def __init__(self, args: argparse.Namespace) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720))
        pygame.display.set_caption("Val2d")
        self.w, self.h = self.screen.get_size()
        self.scale = self.w / VIEW_METERS
        try:
            self.font = pygame.font.Font(str(FONT_PATH), 18)
            self.big = pygame.font.Font(str(FONT_PATH), 36)
        except (OSError, FileNotFoundError):
            warnings.warn("Schrift fixed_sys.ttf fehlt; nutze Standardschrift.")
            self.font = pygame.font.Font(None, 22)
            self.big = pygame.font.Font(None, 44)
        base = load_config()
        lobby = LobbySettings(all_around_sight=args.all_around or base.lobby.all_around_sight,
                              sound_rings=args.sound_rings or base.lobby.sound_rings,
                              win_rounds=args.rounds, overtime=base.lobby.overtime, team_size=args.team_size)
        cfg = type(base)(hit_zones=base.hit_zones, lobby=lobby, player=base.player)
        self.team_size = args.team_size
        self.mode = "local"
        self.session: HostSession | None = None
        self.client: Client | None = None
        self.status = ""
        if args.join:
            self.mode = "client"
            address, _, port = args.join.partition(":")
            self.client = Client(address, int(port or DEFAULT_PORT), args.name, args.agent)
            self.match = Match(load_map(self.client.map_key), cfg)
            self.me = self.client.pid
        elif args.host:
            self.mode = "host"
            self.match = Match(load_map(args.map), cfg)
            self.session = HostSession(self.match, args.name, args.port)
            self.me = self.match.add_player(args.name, 0, args.agent).pid
        else:
            self.match = Match(load_map(args.map), cfg)
            self.me = self.match.add_player("Du", 0, args.agent).pid
            others = [a for a in self.match.agents if a != args.agent] or [args.agent]
            for i in range(args.team_size - 1):
                self.match.add_player(f"Bot {i + 1}", 0, others[i % len(others)], is_bot=True)
            for i in range(args.team_size):
                self.match.add_player(f"Gegner {i + 1}", 1, list(self.match.agents)[i % len(self.match.agents)], is_bot=True)
        self.bots = BotDirector(self.match)
        self.local_facing = 0.0
        self.seen_round = -1
        self.ui = UiState()
        self.sound = Sound()
        self.cursor_depth = 8.0
        self.sens = base.player.sensitivity
        self.camera_push = base.player.camera_push
        self.clock = pygame.time.Clock()
        self.grab(True)
        if self.mode == "local":
            self.match.start()

    def grab(self, on: bool) -> None:
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
            if me is None:  # Client vor dem ersten Abbild
                me = PlayerState(pid=self.me, name="", team=0, agent="kestrel")
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_RETURN and self.session and not self.session.started:
                        self.session.start(self.team_size)
                    elif ev.key == pygame.K_b:
                        self.ui.buy_open = not self.ui.buy_open
                        self.grab(not self.ui.buy_open)
                    elif ev.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                        cmd.slot = {pygame.K_1: "primary", pygame.K_2: "sidearm", pygame.K_3: "melee"}[ev.key]
                    elif ev.key == pygame.K_r:
                        cmd.reload = True
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
            events = self.step(dt, cmd)
            if self.match.round_no != self.seen_round and self.me in self.match.players:
                self.seen_round = self.match.round_no  # neue Runde: Blick vom Spawn übernehmen
                self.local_facing = self.match.players[self.me].facing
            self.handle_events(events)
            self.draw()
            if self.client and not self.client.connected:
                self.status = "Verbindung zum Host verloren"
        if self.session:
            self.session.close()
        if self.client:
            self.client.close()
        pygame.quit()

    def step(self, dt: float, cmd: Command) -> list[GameEvent]:
        if self.mode == "local":
            commands = self.bots.commands(dt)
            commands[self.me] = cmd
            return self.match.tick(dt, commands)
        if self.session:
            return self.session.step(dt, {self.me: cmd})
        assert self.client is not None
        if self.client.connected:
            self.client.send(cmd)
        events: list[GameEvent] = []
        for msg in self.client.take():
            if msg.get("type") == "state":
                try:
                    apply_snapshot(self.match, msg["snap"], self.me)
                    events += events_from_json(msg.get("events", []))
                except (KeyError, TypeError, ValueError) as exc:
                    warnings.warn(f"Abbild vom Host unlesbar: {exc}")
        return events

    def handle_events(self, events: list[GameEvent]) -> None:
        m, t = self.match, self.match.time
        me = m.players.get(self.me)
        if me is None:
            return
        for e in events:
            d = e.data
            if e.kind == "shot":
                self.ui.tracers.append(Tracer(Vec(*d["from"]), Vec(*d["to"]), t + 0.08, d["pid"] == self.me))
            elif e.kind == "sound":
                pos = Vec(*d["pos"])
                self.sound.play(d["kind"], me, pos, d["radius"])
                if m.cfg.lobby.sound_rings and d["pid"] != self.me:
                    self.ui.rings.append(Ring(pos, min(d["radius"], 6.0), t))
            elif e.kind == "hit" and d["by"] == self.me:
                self.ui.hit_marker = t + 0.15
            elif e.kind == "kill":
                killer = m.players.get(d["by"]) if d["by"] else None
                victim = m.players.get(d["pid"])
                by = killer.name if killer else "Spike"
                self.ui.feed.append((t + 5, f"{by} → {victim.name if victim else '?'}{' (Kopf)' if d['head'] else ''}"))
                self.sound.play("kill", None, None)
            elif e.kind == "plant":
                self.ui.banner = (t + 2.5, f"Spike gelegt auf {d['site']}")
                self.sound.play("plant", None, None)
            elif e.kind == "ability":
                self.sound.play("ability", me, Vec(*d["pos"]), 30)
            elif e.kind == "round_end":
                won = d["winner"] == me.team
                self.ui.banner = (t + 5, f"{'Runde gewonnen' if won else 'Runde verloren'}: {d['reason']}  {d['score'][0]}:{d['score'][1]}")

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
        s.fill(C_BG)
        wm = m.world
        from gameplay.geometry import Rect
        pygame.draw.polygon(s, C_FLOOR, self.poly(Rect(0, 0, wm.width, wm.height), me))
        for site in wm.sites:
            pygame.draw.polygon(s, (70, 62, 40), self.poly(site.rect, me))
            sx, sy = self.to_screen(site.rect.center, me)
            lbl = self.big.render(site.name, True, C_SITE)
            s.blit(lbl, (sx - lbl.get_width() / 2, sy - lbl.get_height() / 2))
        for r in wm.ramps:
            pygame.draw.polygon(s, C_RAMP, self.poly(r, me))
        for w in wm.walls:
            if w.rect.x0 < -0.5 or w.rect.y0 < -0.5 or w.rect.x1 > wm.width + 0.5 or w.rect.y1 > wm.height + 0.5:
                continue
            col = C_CRATE if w.height == 1 and w.blocks_sight is False else (C_WALL_THIN if w.penetration == 0 else C_WALL)
            if any(pl.rect == w.rect for pl in wm.platforms):
                col = C_PLATFORM
            pygame.draw.polygon(s, col, self.poly(w.rect, me))
        for e in m.effects:
            ex, ey = self.to_screen(e.pos, me)
            if e.kind == "smoke":
                pygame.draw.circle(s, C_SMOKE, (ex, ey), e.radius * self.scale)
            elif e.kind == "slow_field":
                pygame.draw.circle(s, (120, 80, 170), (ex, ey), e.radius * self.scale, 3)
            elif e.kind == "sensor":
                pygame.draw.circle(s, C_ALLY if e.team == me.team else C_ENEMY, (ex, ey), 5)
                pygame.draw.circle(s, (60, 90, 90), (ex, ey), e.radius * self.scale, 1)
            elif e.kind == "vapor_wall" and e.a and e.b:
                pygame.draw.line(s, (180, 190, 210), self.to_screen(e.a, me), self.to_screen(e.b, me), 8)
        if m.spike_pos is not None:
            px, py = self.to_screen(m.spike_pos, me)
            blink = m.phase != "planted" or int(m.time * (2 + 6 * (1 - m.spike_time_left() / 45))) % 2 == 0
            pygame.draw.rect(s, C_ENEMY if blink else (90, 40, 40), (px - 6, py - 6, 12, 12))
        # Sichtkegel: Außenbereich abdunkeln
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
            pygame.draw.circle(s, C_MUTED, (rx, ry), max(1, ring.radius * self.scale * age / 0.6), 1)
        for tr in list(self.ui.tracers):
            if m.time > tr.until:
                self.ui.tracers.remove(tr)
                continue
            pygame.draw.line(s, (255, 230, 140), self.to_screen(tr.a, me), self.to_screen(tr.b, me), 2 if tr.own else 1)
        for p in m.players.values():
            if not p.alive:
                continue
            seen = p.visible if self.mode == "client" else m.can_see(me, p)
            if p.team != me.team and not seen:
                continue
            px, py = self.to_screen(p.pos, me)
            r = 0.4 * self.scale
            col = C_ALLY if p.team == me.team else C_ENEMY
            if p.team != me.team:
                pygame.draw.circle(s, C_ENEMY, (px, py), r + 3, 3)
            pygame.draw.circle(s, (80, 90, 94) if p.pid != self.me else (110, 120, 124), (px, py), r)
            fx, fy = self.to_screen(p.pos + heading(p.facing) * 0.6, me)
            pygame.draw.line(s, col, (px, py), (fx, fy), 3)
            if p.level:
                s.blit(self.font.render("▲", True, C_TEXT), (px + r, py - r))
            if p.pid != self.me:
                name = self.font.render(p.name, True, col)
                s.blit(name, (px - name.get_width() / 2, py - r - 22))
        self.draw_crosshair(me)
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

    def draw_lobby(self) -> None:
        s = self.screen
        s.fill(C_BG)
        title = {"host": "Lobby – du bist Host", "client": "Lobby – beigetreten"}.get(self.mode, "Lobby")
        self.text(title, (self.w / 2, 80), C_TEXT, big=True, center=True)
        self.text(f"Karte {self.match.world.name}", (self.w / 2, 130), C_MUTED, center=True)
        y = 190
        for team in (0, 1):
            self.text(f"Team {team + 1}", (self.w / 2 - 300 + team * 340, y), C_ALLY if team == 0 else C_ENEMY)
            row = y + 34
            for p in (p for p in self.match.players.values() if p.team == team):
                self.text(f"{p.name}  ({self.match.agents.get(p.agent, {}).get('name', p.agent)})", (self.w / 2 - 300 + team * 340, row))
                row += 26
        if self.mode == "host":
            hint = f"Enter startet · freie Plätze bis {self.team_size} je Team füllen Bots · Port {self.session.net.port if self.session else ''}"
        else:
            hint = "Warte auf den Start durch den Host …"
        self.text(hint, (self.w / 2, self.h - 90), C_SITE, center=True)
        if self.status:
            self.text(self.status, (self.w / 2, self.h - 60), C_ENEMY, center=True)

    def draw_crosshair(self, me: PlayerState) -> None:
        cx, cy = self.to_screen(me.pos + heading(me.facing) * self.cursor_depth, me)
        col = C_ENEMY if self.match.time < self.ui.hit_marker else (120, 255, 200)
        d = self.match.weapons.get(me.weapon.key) if me.weapon else None
        gap = 4 + (self.match.current_spread(me, d) * self.cursor_depth * math.pi / 180 * self.scale if d else 0)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            pygame.draw.line(self.screen, col, (cx + dx * gap, cy + dy * gap), (cx + dx * (gap + 7), cy + dy * (gap + 7)), 2)
        pygame.draw.circle(self.screen, col, (cx, cy), 2)

    def text(self, msg: str, pos: tuple[float, float], col=C_TEXT, big: bool = False, center: bool = False) -> None:
        img = (self.big if big else self.font).render(msg, True, col)
        x, y = pos
        if center:
            x -= img.get_width() / 2
        self.screen.blit(img, (x, y))

    def draw_hud(self, me: PlayerState) -> None:
        m = self.match
        left = m.phase_time_left()
        phase = {"buy": "Kaufphase", "live": "", "planted": "Spike", "end": "Rundenende", "over": "Partie vorbei"}.get(m.phase, "")
        mine, theirs = m.score[me.team], m.score[1 - me.team]
        self.text(f"{mine}  {int(left) // 60}:{int(left) % 60:02d}  {theirs}", (self.w / 2, 12), big=True, center=True)
        side = "Angriff" if m.side(me.team) == "attack" else "Verteidigung"
        self.text(f"Runde {m.round_no} · {side} {('· ' + phase) if phase else ''}", (self.w / 2, 54), C_MUTED, center=True)
        self.text(f"Leben {max(me.hp, 0)}   Schild {me.armor}", (20, self.h - 40))
        if me.weapon:
            d = m.weapons.get(me.weapon.key)
            name = d.name if d else me.weapon.key
            ammo = "" if not d or not d.is_gun else f"  {me.weapon.mag} / {me.weapon.reserve}"
            self.text(f"{name}{ammo}{'  lädt…' if me.reload_until > m.time else ''}", (self.w - 320, self.h - 40))
        self.text(f"{me.credits} ¤", (self.w - 320, self.h - 70), C_SITE)
        abil = m.agents[me.agent]["abilities"]
        parts = [f"{k} {abil[k]['name']} ×{me.charges.get(k, 0)}" for k in ("C", "Q", "E")]
        parts.append(f"X {abil['X']['name']} {me.ult_points}/{abil['X']['cost']}")
        self.text("   ".join(parts), (20, self.h - 70), C_MUTED)
        self.text(f"{m.agents[me.agent]['name']} · {m.world.callout_at(me.pos)}", (20, 16), C_MUTED)
        if m.spike_carrier == self.me:
            self.text("Du trägst den Spike (F auf A oder B halten)", (20, 40), C_SITE)
        prog = me.plant_progress / 4.0 if me.plant_progress else me.defuse_progress / 7.0
        if prog > 0:
            pygame.draw.rect(self.screen, C_MUTED, (self.w / 2 - 100, self.h / 2 + 60, 200, 10), 1)
            pygame.draw.rect(self.screen, C_SITE, (self.w / 2 - 100, self.h / 2 + 60, 200 * min(prog, 1), 10))
        y = 90
        for until, msg in list(self.ui.feed):
            if m.time > until:
                self.ui.feed.remove((until, msg))
                continue
            self.text(msg, (self.w - 360, y))
            y += 22
        if self.status:
            self.text(self.status, (self.w / 2, self.h / 2 - 110), C_ENEMY, center=True)
        if m.time < self.ui.banner[0]:
            self.text(self.ui.banner[1], (self.w / 2, self.h / 3), C_SITE, big=True, center=True)
        if not me.alive and m.phase in ("live", "planted"):
            self.text("Ausgeschaltet – warte auf die nächste Runde", (self.w / 2, self.h / 2 - 80), C_ENEMY, center=True)
        if m.phase == "buy":
            self.text("B: Kaufmenü", (20, 64), C_MUTED)

    def buy_layout(self) -> list[tuple[pygame.Rect, str, str]]:
        m = self.match
        items: list[tuple[str, str]] = []
        for key, d in sorted(m.weapons.items(), key=lambda kv: (kv[1].slot != "sidearm", kv[1].price)):
            if d.slot != "melee":
                items.append((key, f"{d.name}  {d.price}"))
        for key, a in m.armor.items():
            items.append((key, f"{a.name}  {a.price}"))
        me = m.players.get(self.me)
        for k in (("C", "Q") if me else ()):
            ab = m.agents[me.agent]["abilities"][k]
            items.append((k, f"{k} {ab['name']}  {ab['price']}"))
        out = []
        cols = 3
        for i, (key, label) in enumerate(items):
            r = pygame.Rect(140 + (i % cols) * 340, 120 + (i // cols) * 46, 320, 38)
            out.append((r, key, label))
        return out

    def buy_item_at(self, pos: tuple[int, int]) -> str | None:
        for r, key, _ in self.buy_layout():
            if r.collidepoint(pos):
                return key
        return None

    def draw_buy(self, me: PlayerState) -> None:
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((10, 10, 16, 215))
        self.screen.blit(overlay, (0, 0))
        open_ = self.match.phase == "buy"
        self.text("Kaufmenü" + ("" if open_ else " (nur in der Kaufphase im Spawn)"), (140, 70), C_TEXT, big=True)
        mouse = pygame.mouse.get_pos()
        for r, key, label in self.buy_layout():
            hover = r.collidepoint(mouse)
            pygame.draw.rect(self.screen, (60, 58, 72) if hover else (36, 35, 45), r)
            pygame.draw.rect(self.screen, C_MUTED, r, 1)
            self.text(label, (r.x + 10, r.y + 9))
        self.text(f"Guthaben {me.credits} ¤ · Klick kauft · B schließt", (140, self.h - 60), C_SITE)

    def draw_scores(self) -> None:
        m = self.match
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((10, 10, 16, 200))
        self.screen.blit(overlay, (0, 0))
        title = "Partie vorbei" if m.phase == "over" else "Punktestand"
        if m.phase == "over":
            me = m.players[self.me]
            title += ": gewonnen" if m.match_winner == me.team else ": verloren"
        self.text(f"{title}   {m.score[0]} : {m.score[1]}", (self.w / 2, 80), C_TEXT, big=True, center=True)
        y = 150
        for team in (0, 1):
            for p in sorted((p for p in m.players.values() if p.team == team), key=lambda p: -p.kills):
                col = C_ALLY if team == m.players[self.me].team else C_ENEMY
                self.text(f"{p.name:<12} {m.agents[p.agent]['name']:<10} {p.kills:>3} / {p.deaths:<3} {p.credits:>6} ¤", (self.w / 2 - 260, y), col)
                y += 26
            y += 20


def main() -> None:
    ap = argparse.ArgumentParser(description="Val2d gegen Bots spielen")
    ap.add_argument("--agent", default="kestrel", choices=["kestrel", "marrow"])
    ap.add_argument("--team-size", type=int, default=5, choices=range(1, 6))
    ap.add_argument("--rounds", type=int, default=13)
    ap.add_argument("--map", default="werkhof")
    ap.add_argument("--all-around", action="store_true", help="Lobby-Regel Rundumsicht")
    ap.add_argument("--sound-rings", action="store_true", help="Lobby-Regel Schallringe")
    ap.add_argument("--name", default="Spieler", help="Name in der Partie (bis 16 Zeichen)")
    net = ap.add_mutually_exclusive_group()
    net.add_argument("--host", action="store_true", help="Partie im Netz öffnen (Host = Spieler 1)")
    net.add_argument("--join", metavar="ADRESSE[:PORT]", help="Einer Partie beitreten")
    net.add_argument("--find", action="store_true", help="Partie im lokalen Netz suchen und beitreten")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args()
    if args.find:
        print("Suche Partien im lokalen Netz …")
        found = discover()
        if not found:
            print("Keine Partie gefunden. Läuft beim Host play.py --host oder server.py, und sind beide im selben Netz?")
            return
        for address, port, host_name in found:
            print(f"  {host_name}  {address}:{port}")
        address, port, host_name = found[0]
        print(f"Trete {host_name} bei …")
        args.join = f"{address}:{port}"
    try:
        game = Game(args)
    except (OSError, ConnectionError) as exc:
        print(f"Keine Verbindung: {exc}")
        pygame.quit()
        return
    game.run()


if __name__ == "__main__":
    main()
