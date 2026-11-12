"""HUD: score, bars, abilities, crosshair, aim preview, feed, banners."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)


class HudMixin:
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

    AIM_KINDS = {"smoke", "wall", "vapor_wall", "flash", "zone", "slow_field", "blast", "wave", "sensor", "alarm",
                 "tripwire", "teleport", "heal", "shield", "revive"}

    def needs_aim(self, me: PlayerState, slot: str) -> bool:
        ab = self.match.agents.get(me.agent, {}).get("abilities", {}).get(slot, {})
        return self.preview_kind(ab) in self.AIM_KINDS

    @staticmethod
    def preview_kind(ab: dict) -> str:
        """Composed abilities name the preset their aim preview looks like (preview=...)."""
        return str(ab.get("preview") or ab.get("kind", "")) if ab.get("kind") == "custom" else str(ab.get("kind", ""))

    def draw_aim_preview(self, me: PlayerState, slot: str) -> None:
        """Where the held ability will land: ring, line or arc, clipped at walls like the real throw."""
        m, s = self.match, self.screen
        ab = m.agents.get(me.agent, {}).get("abilities", {}).get(slot, {})
        kind = self.preview_kind(ab)
        aim = heading(me.facing)
        reach = min(self.cursor_depth, float(ab.get("range", self.cursor_depth)))
        free_target = me.pos + aim * reach
        clip = not (kind == "smoke" and ab.get("remote")) and not (kind == "flash" and ab.get("through_walls")) \
            and ab.get("target") != "aim_free"
        target = m._clip_to_walls(me.pos, free_target, me.level) if clip else free_target
        color = (120, 255, 200)
        tx, ty = self.to_screen(target, me)
        if kind == "wave":
            length, width = float(ab.get("length", 10)), float(ab.get("width", 1))
            side = aim.rotated(90) * (width / 2)
            corners = [me.pos + side, me.pos - side, me.pos - side + aim * length, me.pos + side + aim * length]
            pygame.draw.polygon(s, color, [self.to_screen(c, me) for c in corners], 1)
        elif kind in ("wall", "vapor_wall", "tripwire"):
            if kind == "tripwire":
                target = m._clip_to_walls(me.pos, me.pos + aim * min(3.0, self.cursor_depth), me.level)
            half = aim.rotated(90) * (float(ab.get("length", 6)) / 2)
            pygame.draw.line(s, color, self.to_screen(target - half, me), self.to_screen(target + half, me), 3)
        else:
            radius = float(ab.get("radius", 0.6 if kind in ("teleport", "heal", "shield", "revive") else 1.0))
            self.radius_ring(target, radius, color, me)
        if kind in ("blast", "flash"):  # throw arc
            dot = self.bank.scaled("fx/ability/arc_dot.png", (3, 3))
            for i in range(1, 10):
                q = i / 10
                x, y = self.to_screen(me.pos + (target - me.pos) * q, me)
                y -= math.sin(q * math.pi) * self.scale * 0.8
                if dot is not None:
                    s.blit(dot, (x - 1, y - 1))
                else:
                    pygame.draw.circle(s, color, (x, y), 1)
        pygame.draw.circle(s, color, (tx, ty), 3)
        label = f"{slot} {ab.get('name', '')} – release to use, right click cancels"
        self.text(label, (self.w / 2, self.h - 130), color, center=True)

    def draw_crosshair(self, me: PlayerState) -> None:
        cx, cy = self.to_screen(me.pos + heading(me.facing) * self.cursor_depth, me)
        col = C_ENEMY if self.match.time < self.ui.hit_marker else (120, 255, 200)
        d = self.match.weapons.get(me.weapon.key) if me.weapon else None
        gap = 4 + (self.match.current_spread(me, d) * self.cursor_depth * math.pi / 180 * self.scale if d else 0)
        hit = "_hit" if self.match.time < self.ui.hit_marker else ""
        ch = self.crosshair
        gap += float(ch.get("crosshair_gap", 4.0)) - 4.0
        size = float(ch.get("crosshair_size", 1.0))
        custom = str(ch.get("crosshair_color", "#78ffc8")).lower() != "#78ffc8" or abs(size - 1.0) > 1e-6
        if custom or not ch.get("crosshair_dot", True):
            color = C_ENEMY if hit else pygame.Color(str(ch.get("crosshair_color", "#78ffc8")))
            length = 7 * size
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                pygame.draw.line(self.screen, color, (cx + dx * gap, cy + dy * gap), (cx + dx * (gap + length), cy + dy * (gap + length)), 2)
            if ch.get("crosshair_dot", True):
                pygame.draw.circle(self.screen, color, (cx, cy), 2)
            return
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
        if m.mode == "deathmatch" and not m.practice:
            left = max(0.0, m.dm_ends_at - m.time)
            self.text(f"{mine}  {int(left) // 60}:{int(left) % 60:02d}  {theirs}", (self.w / 2, 12), big=True, center=True)
            limit = int(rule_value("modes", "deathmatch", {}).get("kill_limit", 40))
            self.text(f"Team deathmatch · first to {limit} kills · B buys anywhere", (self.w / 2, 54), C_MUTED, center=True)
        elif m.practice:
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
