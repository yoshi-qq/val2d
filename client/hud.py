"""HUD: bottom centre vitals and abilities, bottom right weapon, left minimap and score, right kill feed, F1 ability
help; crosshair and ability aim preview. Layout values: config/client/hud.py."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)
from client.ui import color


class HudMixin:
    # ------------------------------------------------------------ layout
    def hud_cfg(self) -> dict:
        return HUD

    def draw_hud(self, me: PlayerState) -> None:
        """Bottom centre: health, armor, abilities. Bottom right: weapon, ammo, credits. Left side: minimap, score,
        timer. Right side: kill feed. The upper middle stays free for the view ahead."""
        m, ui = self.match, self.kit
        ui.begin()
        self.draw_minimap(me)
        self.draw_score_box(me)
        self.draw_vitals(me)
        self.draw_ability_bar(me)
        self.draw_weapon_box(me)
        self.draw_feed(me)
        self.draw_statuses(me)
        self.draw_messages(me)
        if getattr(self, "help_held", False):
            self.draw_ability_help(me)

    def draw_score_box(self, me: PlayerState) -> None:
        """Left side under the minimap: own score, timer (or bomb), enemy score, round and side."""
        m, ui = self.match, self.kit
        r = int(HUD["minimap_radius"])
        box = pygame.Rect(16, 24 + 2 * r + 14, 2 * r + 8, 74)
        ui.panel(box, "panel")
        mine, theirs = m.score[me.team], m.score[1 - me.team]
        if m.mode == "deathmatch" and not m.practice:
            left = max(0.0, m.dm_ends_at - m.time)
        else:
            left = m.phase_time_left()
        clock = f"{int(left) // 60}:{int(left) % 60:02d}"
        if m.practice:
            st = self.stats
            acc = 100 * st["hits"] / st["shots"] if st["shots"] else 0
            heads = 100 * st["heads"] / st["hits"] if st["hits"] else 0
            ui.text("Range", (box.centerx, box.y + 8), "m", "text", "center", upper=True, bold=True)
            ui.text(f"{st['hits']}/{st['shots']} hits · {acc:.0f} %", (box.centerx, box.y + 32), "s", "muted", "center")
            ui.text(f"{heads:.0f} % head", (box.centerx, box.y + 52), "s", "muted", "center")
            return
        ui.text(str(mine), (box.x + 22, box.y + 10), "xl", "ally", "center", bold=True, kind="numbers")
        ui.text(str(theirs), (box.right - 22, box.y + 10), "xl", "enemy", "center", bold=True, kind="numbers")
        if m.phase == "planted":
            spike = self.bank.scaled("ui/hud/carrier_hint.png", (30, 30))
            if spike is not None:
                self.screen.blit(spike, (box.centerx - 15, box.y + 10))
            ui.text("planted", (box.centerx, box.y + 44), "xs", "enemy", "center", upper=True, bold=True)
        else:
            ui.text(clock, (box.centerx, box.y + 8), "l", "text" if left > 10 or m.phase != "live" else "enemy", "center",
                    bold=True, kind="numbers")
            phase = {"buy": "buy phase", "end": "round over", "over": "match over"}.get(m.phase, "")
            side = "attack" if m.side(me.team) == "attack" else "defense"
            sub = f"dm · first to {int(rule_value('modes', 'deathmatch', {}).get('kill_limit', 40))}" if m.mode == "deathmatch" \
                else f"round {m.round_no} · {phase or side}"
            ui.text(sub, (box.centerx, box.y + 48), "xs", "muted", "center", upper=True)

    def draw_vitals(self, me: PlayerState) -> None:
        """Health and armor left of the ability bar."""
        ui = self.kit
        x, y = self.w // 2 - 330, self.h - 92
        box = pygame.Rect(x, y, 170, 76)
        ui.panel(box, "panel", edge="bottom", edge_col="ally" if me.hp > 30 else "enemy")
        ui.text(str(max(0, me.hp)), (x + 14, y + 6), "xl", "text" if me.hp > 30 else "enemy", bold=True, kind="numbers")
        if me.armor:
            ui.text(str(me.armor), (x + 112, y + 16), "m", "muted", bold=True, kind="numbers")
            shield = self.bank.scaled("ui/hud/schild.png", (14, 14))
            if shield is not None:
                self.screen.blit(shield, (x + 94, y + 20))
        bar = pygame.Rect(x + 14, y + 58, 142, 4)
        ui.fill(bar, "line")
        pygame.draw.rect(self.screen, color("text" if me.hp > 30 else "enemy"), (bar.x, bar.y, round(bar.w * max(0, me.hp) / 100), bar.h))
        if me.armor:
            pygame.draw.rect(self.screen, color("muted"), (bar.x, bar.y + 6, round(bar.w * me.armor / 50), 2))

    def ability_ready(self, me: PlayerState, slot: str) -> bool:
        ab = self.match.agents[me.agent]["abilities"][slot]
        return me.ult_points >= int(ab["cost"]) if slot == "X" else me.charges.get(slot, 0) > 0

    def draw_ability_bar(self, me: PlayerState) -> None:
        """Four slots in the bottom centre: icon, key, charges as pips, ultimate points as dots."""
        m, ui = self.match, self.kit
        abil = m.agents[me.agent]["abilities"]
        keys = {"C": "ability_c", "Q": "ability_q", "E": "ability_e", "X": "ability_x"}
        x0, y = self.w // 2 - 150, self.h - 92
        for i, slot in enumerate(("C", "Q", "E", "X")):
            ab = abil[slot]
            r = pygame.Rect(x0 + i * 76, y, 68, 76)
            ready = self.ability_ready(me, slot)
            ui.panel(r, "panel", edge="bottom" if ready else "", edge_col="gold" if slot == "X" else "text")
            icon = self.bank.scaled(f"ui/faehigkeit_{me.agent}_{slot}.png", (34, 34))
            if icon is not None:
                if not ready:
                    icon = icon.copy()
                    icon.fill((80, 80, 80, 255), special_flags=pygame.BLEND_RGBA_MULT)
                self.screen.blit(icon, (r.centerx - 17, r.y + 14))
            else:
                ui.text(ab["name"][:2], (r.centerx, r.y + 20), "m", "text" if ready else "muted", "center", upper=True)
            if slot == "X":
                cost = int(ab["cost"])
                pts = min(me.ult_points, cost)
                for j in range(cost):
                    cx = r.centerx - (cost - 1) * 4 + j * 8
                    pygame.draw.circle(self.screen, color("gold" if j < pts else "line"), (cx, r.y + 7), 2)
            else:
                count = me.charges.get(slot, 0)
                for j in range(int(ab.get("max", 1))):
                    px = r.centerx - (int(ab.get("max", 1)) - 1) * 5 + j * 10 - 3
                    pygame.draw.rect(self.screen, color("text" if j < count else "line"), (px, r.y + 5, 6, 3))
            name = pygame.key.name(self.keys.get(keys[slot], 0)) if self.keys.get(keys[slot]) else slot
            ui.keycap((r.centerx - 10, r.bottom - 22), name if len(name) <= 3 else slot, "xs")
        hint = pygame.key.name(self.help_key).upper() if getattr(self, "help_key", None) else "F1"
        ui.text(f"hold {hint}: ability info", (x0 + 4 * 76 - 8, y - 18), "xs", "muted", "right", upper=True)

    def draw_weapon_box(self, me: PlayerState) -> None:
        """Bottom right: current weapon, magazine and reserve, other carried weapons, credits."""
        m, ui = self.match, self.kit
        x, y = self.w - 260, self.h - 92
        box = pygame.Rect(x, y, 244, 76)
        ui.panel(box, "panel")
        if me.weapon:
            d = m.weapons.get(me.weapon.key)
            name = d.name if d else me.weapon.key
            gun = self.bank.scaled(f"weapons/val2d/{me.weapon.key}.png", (64, 32))
            if gun is not None:
                self.screen.blit(gun, (x + 12, y + 8))
            ui.text(name, (x + 12, y + 50), "xs", "muted", upper=True)
            if d and d.is_gun:
                reloading = me.reload_until > m.time
                ui.text(str(me.weapon.mag), (box.right - 70, y + 4), "xl", "enemy" if me.weapon.mag == 0 else "text", "right",
                        bold=True, kind="numbers")
                ui.text(f"/ {me.weapon.reserve}", (box.right - 12, y + 18), "m", "muted", "right", kind="numbers")
                if reloading:
                    ui.text("reloading", (box.right - 12, y + 52), "xs", "gold", "right", upper=True, bold=True)
        slots = [s for s in ("primary", "sidearm", "melee") if s in me.weapons]
        for i, slot in enumerate(slots):
            ws = me.weapons[slot]
            d = m.weapons.get(ws.key)
            ui.text(d.name if d else ws.key, (box.right - 4, y - 22 - (len(slots) - 1 - i) * 18), "xs",
                    "text" if me.slot == slot else "muted", "right", upper=True, bold=me.slot == slot)
        if m.phase == "buy" or self.ui.buy_open or m.mode == "deathmatch":
            ui.text(f"{me.credits}", (box.right - 4, y - 24 - len(slots) * 18), "m", "gold", "right", bold=True, kind="numbers")

    def draw_feed(self, me: PlayerState) -> None:
        """Right side: kill feed rows."""
        m, ui = self.match, self.kit
        y = 20
        self.ui.feed = [f for f in self.ui.feed if m.time <= f[0]]
        for _, msg, killer, victim, head in self.ui.feed[-6:]:
            mine = bool(me.name) and me.name in msg
            w = ui.size(msg, "s")[0] + 2 * 28 + 28 + (20 if head else 0)
            r = pygame.Rect(self.w - 16 - w, y, w, 28)
            ui.panel(r, "panel", edge="left" if mine else "", edge_col="gold")
            x = r.x + 8
            for agent in (killer, victim):
                icon = self.bank.scaled(f"agents/{agent}/{agent}_killfeed.png", (22, 22)) if agent else None
                if icon is not None:
                    self.screen.blit(icon, (x, r.y + 3))
                x += 26
            ui.text(msg, (x + 4, r.y + 5), "s", "text")
            if head:
                mark = self.bank.scaled("ui/hud/kopfschuss.png", (14, 14))
                if mark is not None:
                    self.screen.blit(mark, (r.right - 22, r.y + 7))
            y += 32

    def draw_statuses(self, me: PlayerState) -> None:
        """Active statuses above the vitals."""
        m, ui = self.match, self.kit
        x, y = self.w // 2 - 330, self.h - 124
        for k in sorted(k for k, until in me.status.items() if until > m.time and k != "blind"):
            icon = self.bank.scaled(f"ui/status/{k}.png", (20, 20))
            left = me.status[k] - m.time
            positive = bool(m.statuses.get(k, {}).get("positive")) if hasattr(m, "statuses") else False
            if icon is not None:
                self.screen.blit(icon, (x, y))
            ui.text(f"{k} {left:.0f}", (x + 24, y + 2), "xs", "ally" if positive else "enemy", upper=True, bold=True)
            x += 34 + ui.size(f"{k} {left:.0f}", "xs", upper=True, bold=True)[0]

    def draw_messages(self, me: PlayerState) -> None:
        """Banners, bomb hints, plant progress, spectating and connection messages, all above the bottom HUD."""
        m, ui = self.match, self.kit
        cx, base = self.w // 2, self.h - 150
        if m.spike_carrier == self.me:
            ui.text("You carry the bomb · hold F on a site", (self.w // 2 - 330, base - 10), "xs", "gold", upper=True, bold=True)
        prog = me.plant_progress / 4.0 if me.plant_progress else me.defuse_progress / 7.0
        if prog > 0:
            bar = pygame.Rect(cx - 120, base - 30, 240, 8)
            ui.fill(bar, "panel")
            pygame.draw.rect(self.screen, color("gold"), (bar.x, bar.y, round(bar.w * min(prog, 1.0)), bar.h))
            ui.text("planting" if me.plant_progress else "defusing", (cx, base - 54), "s", "gold", "center", upper=True, bold=True)
        if m.time < self.ui.banner[0]:
            text = self.ui.banner[1]
            tw = ui.size(text, "l", upper=True, bold=True, kind="title")[0] + 80
            r = pygame.Rect(cx - tw // 2, int(self.h * 0.62), tw, 56)
            won = self.ui.banner_art in ("sieg", "entschaerft")
            ui.panel(r, "panel", edge="top", edge_col="ally" if won else "accent")
            ui.text(text, (cx, r.y + 12), "l", "text", "center", upper=True, bold=True, kind="title")
        own = m.players.get(self.me)
        if own is not None and not own.alive and m.phase in ("live", "planted"):
            watching = f"Spectating {me.name} · click: next teammate" if me.pid != own.pid else "Eliminated · next round soon"
            ui.text(watching, (cx, base + 4), "s", "muted", "center", upper=True)
        if self.status:
            ui.text(self.status, (cx, base - 80), "s", "enemy", "center")
        if m.phase == "buy" and not self.ui.buy_open:
            ui.text("B: buy", (self.w - 16, self.h - 140), "xs", "muted", "right", upper=True)

    def draw_ability_help(self, me: PlayerState) -> None:
        """Held F1: one card per ability above the ability bar with key, name, cost and what it does."""
        from gameplay.kit.describe import cost_text, describe
        m, ui = self.match, self.kit
        abil = m.agents[me.agent]["abilities"]
        card_w, gap = 290, 10
        x0 = self.w // 2 - (4 * card_w + 3 * gap) // 2
        texts = {s: ui.wrap(describe(abil[s]), "xs", card_w - 24) for s in abil}
        height = 70 + 16 * max(len(t) for t in texts.values())
        y = self.h - 110 - height
        for i, slot in enumerate(("C", "Q", "E", "X")):
            ab = abil[slot]
            r = pygame.Rect(x0 + i * (card_w + gap), y, card_w, height)
            ui.panel(r, "bg", edge="top", edge_col="gold" if slot == "X" else "accent")
            ui.keycap((r.x + 12, r.y + 14), slot, "s")
            ui.text(ab["name"], (r.x + 46, r.y + 14), "m", "text", upper=True, bold=True)
            ui.text(cost_text(slot, ab), (r.x + 12, r.y + 42), "xs", "gold" if slot == "X" else "muted")
            for j, ln in enumerate(texts[slot]):
                ui.text(ln, (r.x + 12, r.y + 62 + j * 16), "xs", "text")

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
