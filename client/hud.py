"""HUD: bottom centre vitals and abilities, bottom right weapon, left minimap and score, right kill feed, F1 ability
help; crosshair and ability aim preview. Layout values: config/client/hud.py."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)
from client.ui import color
from gameplay.kit.describe import alt_text


class HudMixin:
    # ------------------------------------------------------------ layout
    def hud_cfg(self) -> dict:
        return HUD

    def draw_hud(self, me: PlayerState) -> None:
        """Valorant layout, with the top bar moved: minimap top left, kill feed top right, own team down the left side,
        enemies down the right side, timer and score bottom centre above health and abilities, weapon bottom right."""
        ui = self.kit
        ui.begin()
        self.draw_bottom_shade()
        self.draw_minimap(me)
        self.draw_team_column(me, own=True)
        self.draw_team_column(me, own=False)
        self.draw_score_box(me)
        self.draw_vitals(me)
        self.draw_ability_bar(me)
        self.draw_weapon_box(me)
        self.draw_feed(me)
        self.draw_statuses(me)
        self.draw_damage_direction(me)
        self.draw_messages(me)
        if getattr(self, "help_held", False):
            self.draw_ability_help(me)

    def draw_bottom_shade(self) -> None:
        """Dark gradient behind the bottom HUD instead of boxes (cached per screen size)."""
        if getattr(self, "_bottom_shade", None) is None or self._bottom_shade.get_width() != self.w:
            h = 150
            shade = pygame.Surface((self.w, h), pygame.SRCALPHA)
            base = color("bg")
            for y in range(0, h, 2):
                pygame.draw.rect(shade, (base.r, base.g, base.b, int(200 * (y / h) ** 1.6)), (0, y, self.w, 2))
            self._bottom_shade = shade
        self.screen.blit(self._bottom_shade, (0, self.h - self._bottom_shade.get_height()))

    def draw_team_column(self, me: PlayerState, own: bool) -> None:
        """Portraits of one team down a screen side: allies left (with health), enemies right. Dead players greyed
        and crossed out; a gold mark when the ultimate is ready (allies only, like the real top bar)."""
        m, ui, s = self.match, self.kit, self.screen
        team = me.team if own else 1 - me.team
        players = sorted((p for p in m.players.values() if p.team == team and not p.dummy), key=lambda p: p.pid)
        if not players or m.practice:
            return
        size, gap = 34, 6
        if own:
            x, y = 16, 24 + 2 * int(HUD["minimap_radius"]) + 18
        else:
            x, y = self.w - 16 - size, 24 + 6 * 32 + 18
        team_col = color("ally" if own else "enemy")
        for p in players:
            r = pygame.Rect(x, y, size, size)
            ui.fill(r, "panel")
            pic = self.bank.scaled(f"agents/{p.agent}/{p.agent}_killfeed.png", (size - 4, size - 4))
            if pic is not None:
                if not p.alive:
                    pic = pic.copy()
                    pic.fill((70, 70, 70, 255), special_flags=pygame.BLEND_RGBA_MULT)
                s.blit(pic, (r.x + 2, r.y + 2))
            pygame.draw.rect(s, team_col if p.alive else color("muted"), (r.x, r.bottom - 3, r.w, 3))
            if own and p.alive:
                pygame.draw.rect(s, color("text"), (r.x, r.bottom - 3, round(r.w * max(0, p.hp) / 100), 3))
            if not p.alive:
                pygame.draw.line(s, color("enemy"), (r.x + 6, r.y + 6), (r.right - 6, r.bottom - 8), 3)
            ab = m.agents.get(p.agent, {}).get("abilities", {}).get("X", {})
            if own and p.alive and p.ult_points >= int(ab.get("cost", 99)):
                cx = r.right + 6 if own else r.x - 6
                pygame.draw.polygon(s, color("ult"), [(cx, r.y + 4), (cx + 4, r.y + 8), (cx, r.y + 12), (cx - 4, r.y + 8)])
            if p.pid == self.me:
                ui.outline(r.inflate(4, 4), "gold")
            y += size + gap

    def draw_score_box(self, me: PlayerState) -> None:
        """Bottom centre above the abilities: own score, timer (or the planted bomb), enemy score, round and side."""
        m, ui, s = self.match, self.kit, self.screen
        cx, top = self.w // 2, self.h - 152
        if m.practice:
            st = self.stats
            acc = 100 * st["hits"] / st["shots"] if st["shots"] else 0
            heads = 100 * st["heads"] / st["hits"] if st["hits"] else 0
            ui.text(f"Range · {st['hits']}/{st['shots']} hits · {acc:.0f} % · {heads:.0f} % head", (cx, top + 8), "s",
                    "text", "center", upper=True)
            return
        mine, theirs = m.score[me.team], m.score[1 - me.team]
        left = max(0.0, m.dm_ends_at - m.time) if m.mode == "deathmatch" else m.phase_time_left()
        clock = f"{int(left) // 60}:{int(left) % 60:02d}"
        mid = pygame.Rect(cx - 56, top, 112, 34)
        ui.fill(mid, "panel")
        for value, rect, col in ((mine, pygame.Rect(mid.x - 46, top, 46, 34), "ally"),
                                 (theirs, pygame.Rect(mid.right, top, 46, 34), "enemy")):
            ui.fill(rect, "panel")
            pygame.draw.rect(s, color(col), (rect.x, rect.bottom - 3, rect.w, 3))
            ui.text(str(value), (rect.centerx, rect.y + 2), "l", col, "center", bold=True, kind="numbers")
        if m.phase == "planted":
            spike = self.bank.scaled("ui/hud/carrier_hint.png", (26, 26))
            if spike is not None and int(m.time * 2) % 2 == 0:
                s.blit(spike, (mid.centerx - 13, mid.y + 4))
        else:
            hurry = left <= 10 and m.phase == "live"
            ui.text(clock, (mid.centerx, mid.y + 2), "l", "enemy" if hurry else "text", "center", bold=True, kind="numbers")
        phase = {"buy": "buy phase", "end": "round over", "over": "match over", "planted": "spike planted"}.get(m.phase, "")
        side = "attack" if m.side(me.team) == "attack" else "defense"
        sub = f"first to {int(rule_value('modes', 'deathmatch', {}).get('kill_limit', 40))}" if m.mode == "deathmatch" \
            else f"round {m.round_no} · {phase or side}"
        ui.text(sub, (cx, mid.bottom + 4), "xs", "muted", "center", upper=True)
        if m.cfg.lobby.allow_cheats:
            on = [n.replace("_", " ") for n in ("infinite_ammo", "infinite_abilities", "invincibility", "bullet_tracers")
                  if m.cheat(n)]
            ui.text("cheats: " + (", ".join(on) if on else "allowed"), (cx, top - 18), "xs", "gold", "center", upper=True)

    def draw_vitals(self, me: PlayerState) -> None:
        """Left of the abilities: armor (shield and number) and health in large numbers over a thin bar, no box."""
        ui, s = self.kit, self.screen
        right, y = self.w // 2 - 170, self.h - 82
        low = me.hp <= 30
        ui.text(str(max(0, me.hp)), (right, y), "xl", "enemy" if low else "text", "right", bold=True, kind="numbers")
        if me.armor:
            shield = self.bank.scaled("ui/hud/schild.png", (14, 14))
            ax = right - 118
            if shield is not None:
                s.blit(shield, (ax, y + 14))
            ui.text(str(me.armor), (ax + 18, y + 12), "m", "muted", bold=True, kind="numbers")
        bar = pygame.Rect(right - 140, y + 52, 140, 4)
        ui.fill(bar, "line")
        pygame.draw.rect(s, color("enemy" if low else "text"), (bar.x, bar.y, round(bar.w * max(0, me.hp) / 100), bar.h))
        if me.armor:
            pygame.draw.rect(s, color("muted"), (bar.x, bar.y + 6, round(bar.w * me.armor / 50), 2))

    def ability_ready(self, me: PlayerState, slot: str) -> bool:
        ab = self.match.agents[me.agent]["abilities"][slot]
        return me.ult_points >= int(ab["cost"]) if slot == "X" else me.charges.get(slot, 0) > 0

    def draw_ability_bar(self, me: PlayerState) -> None:
        """C Q E X in the bottom centre like the real HUD: icon, key below, charges as bars above, the ultimate with
        point dots and a gold frame when ready. The ability in hand is underlined."""
        m, ui, s = self.match, self.kit, self.screen
        abil = m.agents[me.agent]["abilities"]
        keys = {"C": "ability_c", "Q": "ability_q", "E": "ability_e", "X": "ability_x"}
        x0, y = self.w // 2 - 140, self.h - 86
        for i, slot in enumerate(("C", "Q", "E", "X")):
            ab = abil[slot]
            r = pygame.Rect(x0 + i * 62 + (18 if slot == "X" else 0), y, 52, 52)
            ready = self.ability_ready(me, slot)
            icon = self.bank.scaled(f"ui/faehigkeit_{me.agent}_{slot}.png", (40, 40))
            if icon is not None:
                if not ready:
                    icon = icon.copy()
                    icon.fill((90, 90, 90, 255), special_flags=pygame.BLEND_RGBA_MULT)
                s.blit(icon, (r.centerx - 20, r.y + 6))
            else:
                ui.text(ab["name"][:2], (r.centerx, r.y + 16), "m", "text" if ready else "muted", "center", upper=True)
            if slot == "X":
                cost = int(ab["cost"])
                pts = min(me.ult_points, cost)
                for j in range(cost):
                    px = r.centerx - (cost - 1) * 4 + j * 8
                    pygame.draw.rect(s, color("ult" if j < pts else "line"), (px - 2, r.y - 4, 4, 4))
                if ready:
                    ui.outline(r.inflate(-4, -2), "ult")
            else:
                count, top = me.charges.get(slot, 0), int(ab.get("max", 1))
                for j in range(top):
                    px = r.centerx - (top - 1) * 6 + j * 12 - 4
                    pygame.draw.rect(s, color("text" if j < count else "line"), (px, r.y - 3, 8, 3))
            if self.aiming == slot:
                pygame.draw.rect(s, color("text"), (r.x + 6, r.bottom + 14, r.w - 12, 2))
            name = pygame.key.name(self.keys.get(keys[slot], 0)) if self.keys.get(keys[slot]) else slot
            ui.text(name.upper() if len(name) <= 3 else slot, (r.centerx, r.bottom - 2), "xs", "text" if ready else "muted",
                    "center", bold=True)

    def draw_weapon_box(self, me: PlayerState) -> None:
        """Bottom right: weapon picture, magazine large and reserve small; the inventory list for a moment after
        switching; credits during the buy phase."""
        m, ui, s = self.match, self.kit, self.screen
        right, y = self.w - 24, self.h - 86
        if me.weapon:
            d = m.weapons.get(me.weapon.key)
            gun = self.bank.scaled(f"weapons/val2d/{me.weapon.key}.png", (72, 36))
            if gun is not None:
                s.blit(gun, (right - 250, y + 6))
            if d and d.is_gun:
                ui.text(f"/ {me.weapon.reserve}", (right, y + 18), "m", "muted", "right", kind="numbers")
                mag_w = ui.size(f"/ {me.weapon.reserve}", "m")[0] + 10
                ui.text(str(me.weapon.mag), (right - mag_w, y), "xl", "enemy" if me.weapon.mag == 0 else "text", "right",
                        bold=True, kind="numbers")
                if me.reload_until > m.time:
                    ui.text("reloading", (right, y + 50), "xs", "gold", "right", upper=True, bold=True)
            else:
                ui.text(d.name if d else me.weapon.key, (right, y + 14), "m", "text", "right", upper=True, bold=True)
        switched = m.time - getattr(self, "_switched_at", -9.0) < 2.0
        if switched or self.ui.buy_open or m.phase == "buy":
            slots = [sl for sl in ("primary", "sidearm", "melee") if sl in me.weapons]
            yy = y - 30 - 26 * len(slots)
            for i, sl in enumerate(slots):
                ws = me.weapons[sl]
                dd = m.weapons.get(ws.key)
                row = pygame.Rect(right - 200, yy + i * 26, 200, 22)
                active = me.slot == sl
                ui.fill(row, "panel_light" if active else "panel")
                ui.text(str(i + 1), (row.x + 8, row.y + 3), "xs", "muted")
                ui.text(dd.name if dd else ws.key, (row.right - 8, row.y + 3), "xs", "text" if active else "muted", "right",
                        upper=True, bold=active)
        if m.phase == "buy" or self.ui.buy_open or m.mode == "deathmatch":
            ui.text(f"{me.credits}", (right, y - 26), "l", "text", "right", bold=True, kind="numbers")
            coin = self.bank.scaled("ui/hud/credits.png", (16, 16))
            if coin is not None:
                s.blit(coin, (right - ui.size(str(me.credits), "l", bold=True, kind="numbers")[0] - 22, y - 20))

    def draw_feed(self, me: PlayerState) -> None:
        """Top right: kill rows tinted by who got the kill (teal for your team, red for the enemy), killer, weapon,
        victim, headshot mark; your own kills get a gold edge."""
        m, ui, s = self.match, self.kit, self.screen
        y = 20
        self.ui.feed = [f for f in self.ui.feed if m.time <= f[0]]
        for until, msg, killer, victim, head, *rest in self.ui.feed[-6:]:
            weapon = rest[0] if rest else ""
            killer_team = rest[1] if len(rest) > 1 else None
            wallbang = bool(rest[2]) if len(rest) > 2 else False
            mine = bool(me.name) and msg.startswith(me.name + " ")
            left_name, _, right_name = msg.partition(" → ")
            names = [left_name, right_name] if right_name else [msg]
            widths = [ui.size(n, "s", bold=True)[0] for n in names]
            gun = self.bank.scaled(f"weapons/val2d/{weapon}.png", (40, 20)) if weapon in m.weapons else None
            w = sum(widths) + 2 * 28 + (48 if gun else 16) + (22 if head else 0) + 26
            r = pygame.Rect(self.w - 16 - w, y, w, 28)
            tint = "ally" if killer_team == me.team else "enemy" if killer_team is not None else "muted"
            ui.fill(r, "panel")
            band = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            c = color(tint)
            band.fill((c.r, c.g, c.b, 60))
            s.blit(band, r.topleft)
            pygame.draw.rect(s, color("gold" if mine else tint), (r.x, r.y, 3, r.h))
            x = r.x + 10
            for i, name in enumerate(names):
                agent = (killer, victim)[i] if len(names) == 2 else victim
                icon = self.bank.scaled(f"agents/{agent}/{agent}_killfeed.png", (22, 22)) if agent else None
                if icon is not None:
                    s.blit(icon, (x, r.y + 3))
                x += 26
                ui.text(name, (x, r.y + 6), "s", "text", bold=True)
                x += widths[i] + 6
                if i == 0 and len(names) == 2:
                    if gun is not None:
                        s.blit(gun, (x, r.y + 4))
                        x += 46
                    if wallbang:  # shot through a wall: two bars like a wall section
                        for bx in (x - 4, x + 1):
                            pygame.draw.rect(s, color("muted"), (bx, r.y + 7, 3, 14))
                        x += 10
                    else:
                        pygame.draw.polygon(s, color("muted"), [(x, r.y + 9), (x + 8, r.y + 14), (x, r.y + 19)])
                        x += 14
            if head:
                mark = self.bank.scaled("ui/hud/kopfschuss.png", (14, 14))
                if mark is not None:
                    s.blit(mark, (r.right - 22, r.y + 7))
            y += 32

    def draw_statuses(self, me: PlayerState) -> None:
        """Active statuses in a row above health and abilities."""
        m, ui = self.match, self.kit
        x, y = self.w // 2 - 310, self.h - 112
        for k in sorted(k for k, until in me.status.items() if until > m.time and k != "blind"):
            icon = self.bank.scaled(f"ui/status/{k}.png", (18, 18))
            left = me.status[k] - m.time
            positive = bool(m.statuses.get(k, {}).get("positive")) if hasattr(m, "statuses") else False
            if icon is not None:
                self.screen.blit(icon, (x, y))
            label = f"{k} {left:.0f}"
            ui.text(label, (x + 22, y + 2), "xs", "ally" if positive else "enemy", upper=True, bold=True)
            x += 32 + ui.size(label, "xs", upper=True, bold=True)[0]

    def draw_messages(self, me: PlayerState) -> None:
        """Round banners, bomb hints, plant progress, spectating and connection messages."""
        m, ui = self.match, self.kit
        cx, base = self.w // 2, self.h - 190
        if m.spike_carrier == self.me:
            ui.text("Spike · hold F on a site", (self.w // 2 - 310, self.h - 132), "xs", "gold", upper=True, bold=True)
        orb_time = float(rule_value("orbs", "pickup_time", 1.0))
        if me.orb_progress > 0:
            bar = pygame.Rect(cx - 90, base - 10, 180, 6)
            ui.fill(bar, "panel")
            pygame.draw.rect(self.screen, color("ult"), (bar.x, bar.y, round(bar.w * min(1.0, me.orb_progress / orb_time)), bar.h))
            ui.text("ultimate orb", (cx, base - 30), "xs", "ult", "center", upper=True, bold=True)
        elif any((o - me.pos).length() <= float(rule_value("orbs", "reach", 1.2)) for o in m.orbs) and me.alive:
            ui.text("hold F: ultimate orb", (cx, base - 30), "xs", "ult", "center", upper=True, bold=True)
        until, kills = self.ui.kill_flash
        if m.time < until and kills:
            for k in range(kills):  # kill counter like the real kill banner: one mark per kill this round
                mx = cx - (kills - 1) * 14 + k * 28
                pygame.draw.polygon(self.screen, color("enemy"), [(mx, base - 96), (mx + 9, base - 84), (mx, base - 72), (mx - 9, base - 84)])
        until, title, ours = self.ui.title_banner
        if m.time < until and title:
            tw = ui.size(title, "xl", upper=True, bold=True, kind="title")[0]
            y = int(self.h * 0.20)
            ui.fill(pygame.Rect(cx - tw // 2 - 40, y - 8, tw + 80, 62), "#0f1923cc")
            ui.text(title, (cx, y), "xl", "ult" if ours else "enemy", "center", upper=True, bold=True, kind="title")
        prog = me.plant_progress / 4.0 if me.plant_progress else me.defuse_progress / 7.0
        if prog > 0:
            bar = pygame.Rect(cx - 120, base - 10, 240, 8)
            ui.fill(bar, "panel")
            pygame.draw.rect(self.screen, color("gold"), (bar.x, bar.y, round(bar.w * min(prog, 1.0)), bar.h))
            ui.text("planting" if me.plant_progress else "defusing", (cx, base - 34), "s", "gold", "center", upper=True, bold=True)
        if m.time < self.ui.banner[0]:
            text = self.ui.banner[1]
            won = self.ui.banner_art in ("sieg", "entschaerft")
            tw = ui.size(text, "xl", upper=True, bold=True, kind="title")[0]
            y = int(self.h * 0.28)
            band = pygame.Rect(0, y - 10, self.w, 76)
            ui.fill(band, "#0f192399")
            pygame.draw.rect(self.screen, color("ally" if won else "accent"), (cx - tw // 2 - 30, band.y, tw + 60, 3))
            ui.text(text, (cx, y), "xl", "ally" if won else "text", "center", upper=True, bold=True, kind="title")
        own = m.players.get(self.me)
        if own is not None and not own.alive and m.phase in ("live", "planted"):
            watching = f"Spectating {me.name} · click: next teammate" if me.pid != own.pid else "Eliminated · next round soon"
            ui.text(watching, (cx, base + 10), "s", "muted", "center", upper=True)
        if self.status:
            ui.text(self.status, (cx, base - 60), "s", "enemy", "center")
        if self.client is not None and not self.client.connected:
            ui.button(pygame.Rect(cx - 120, base - 30, 240, 44), "Rejoin", "rejoin", primary=True)
        if m.phase == "buy" and not self.ui.buy_open:
            ui.text("B: buy", (self.w - 24, self.h - 140 - 26 * 3), "xs", "muted", "right", upper=True)


    def pixel_text(self, msg: str, col: tuple | pygame.Color, k: int = 1) -> pygame.Surface:
        """Pixel font at its native size without smoothing, enlarged k times (nearest neighbour)."""
        img = self.font.render(msg, False, col)
        return img if k == 1 else pygame.transform.scale(img, (img.get_width() * k, img.get_height() * k))

    def draw_damage_direction(self, me: PlayerState) -> None:
        """Red arcs around the own figure pointing to where recent hits came from."""
        m = self.match
        self.ui.damage_from = [(pos, t0) for pos, t0 in self.ui.damage_from if m.time - t0 < 1.2]
        if not self.ui.damage_from or me.pid != self.me:
            return
        cx, cy = self.to_screen(me.pos, me)
        layer = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        for pos, t0 in self.ui.damage_from:
            rel = (pos - me.pos).rotated(-me.facing)
            angle = math.atan2(rel.y, rel.x)  # screen: x right, y up
            fade = 1.0 - (m.time - t0) / 1.2
            r = 92
            rect = pygame.Rect(cx - r, cy - r, 2 * r, 2 * r)
            pygame.draw.arc(layer, (255, 70, 85, int(220 * fade)), rect, angle - 0.35, angle + 0.35, 6)
        self.screen.blit(layer, (0, 0))









    def draw_ability_help(self, me: PlayerState) -> None:
        """Held F1: one card per ability above the ability bar with key, name, cost and what it does."""
        from gameplay.kit.describe import cost_text, describe
        m, ui = self.match, self.kit
        abil = m.agents[me.agent]["abilities"]
        card_w, gap = 290, 10
        x0 = self.w // 2 - (4 * card_w + 3 * gap) // 2
        texts = {s: ui.wrap(describe(abil[s]), "xs", card_w - 24) for s in abil}
        costs = {s: ui.wrap(cost_text(s, abil[s]), "xs", card_w - 24) for s in abil}
        extra = 16 * (max(len(c) for c in costs.values()) - 1)
        height = 70 + extra + 16 * max(len(t) for t in texts.values())
        y = self.h - 110 - height
        for i, slot in enumerate(("C", "Q", "E", "X")):
            ab = abil[slot]
            r = pygame.Rect(x0 + i * (card_w + gap), y, card_w, height)
            ui.panel(r, "bg", edge="top", edge_col="gold" if slot == "X" else "accent")
            ui.keycap((r.x + 12, r.y + 14), slot, "s")
            ui.text(ab["name"], (r.x + 46, r.y + 14), "m", "text", upper=True, bold=True)
            for j, ln in enumerate(costs[slot]):
                ui.text(ln, (r.x + 12, r.y + 42 + j * 16), "xs", "gold" if slot == "X" else "muted")
            for j, ln in enumerate(texts[slot]):
                ui.text(ln, (r.x + 12, r.y + 62 + extra + j * 16), "xs", "text")

    AIM_KINDS = {"smoke", "wall", "vapor_wall", "flash", "zone", "slow_field", "blast", "wave", "sensor", "alarm",
                 "tripwire", "teleport", "heal", "shield", "revive"}

    @staticmethod
    def is_throwable(ab: dict) -> bool:
        """Thrown abilities show only a throw cursor, never where they will land (judging the throw is a skill)."""
        from gameplay.kit import expand
        try:
            return str(expand(ab).get("target", "aim")) == "throw"
        except (KeyError, TypeError, ValueError):
            return False

    def needs_aim(self, me: PlayerState, slot: str) -> bool:
        ab = self.match.agents.get(me.agent, {}).get("abilities", {}).get(slot, {})
        return self.preview_kind(ab) in self.AIM_KINDS or bool(ab.get("alt")) or int(ab.get("multi", 1)) > 1  # a right-click choice needs the ability in hand

    @staticmethod
    def preview_kind(ab: dict) -> str:
        """Composed abilities name the preset their aim preview looks like (preview=...)."""
        return str(ab.get("preview") or ab.get("kind", "")) if ab.get("kind") == "custom" else str(ab.get("kind", ""))

    def draw_aim_preview(self, me: PlayerState, slot: str) -> None:
        """Where the held ability will land: ring, line or arc, clipped at walls like the real throw."""
        m, s = self.match, self.screen
        ab = m.agents.get(me.agent, {}).get("abilities", {}).get(slot, {})
        if int(ab.get("multi", 1)) > 1:
            self.draw_multi_preview(me, ab, slot)
            return
        if self.is_throwable(ab):
            self.draw_throw_cursor(me, ab, slot)
            return
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
        alt = " · right click: " + alt_text(ab) if ab.get("alt") else ""
        label = f"{ab.get('name', '')}: left click{alt} · {slot} again, 1/2/3 or Esc: put away"
        self.text(label, (self.w / 2, self.h - 150), color, center=True)

    def draw_multi_preview(self, me: PlayerState, ab: dict, slot: str) -> None:
        """Multi-placement: rings on the marked points and at the cursor, count and how to confirm."""
        radius = float(ab.get("radius", 1.0))
        limit = int(ab["multi"]) if slot == "X" else min(int(ab["multi"]), max(1, me.charges.get(slot, 0)))
        for x, y in self.multi_points:
            self.radius_ring(Vec(x, y), radius, (255, 220, 120), me)
        if len(self.multi_points) < limit:
            self.radius_ring(self.multi_target(me, ab), radius, (120, 255, 200), me)
        label = (f"{ab.get('name', '')}: left click marks ({len(self.multi_points)}/{limit}) · right click confirms · "
                 f"{slot} again or Esc: put away")
        self.text(label, (self.w / 2, self.h - 150), (236, 232, 225), center=True)

    def draw_throw_cursor(self, me: PlayerState, ab: dict, slot: str) -> None:
        """Throw cursor at the crosshair: four corner brackets, no landing point, no arc."""
        cx, cy = self.to_screen(me.pos + heading(me.facing) * self.cursor_depth, me)
        col = (236, 232, 225)
        r, arm, t = 14, 6, 2
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            x, y = round(cx + sx * r), round(cy + sy * r)
            pygame.draw.rect(self.screen, col, (min(x, x - sx * arm), y - (t // 2), arm, t))
            pygame.draw.rect(self.screen, col, (x - (t // 2), min(y, y - sy * arm), t, arm))
        alt = " · right click: " + alt_text(ab) if ab.get("alt") else ""
        self.text(f"{ab.get('name', '')}: left click throws{alt} · {slot} again, 1/2/3 or Esc: put away",
                  (self.w / 2, self.h - 150), col, center=True)

    def draw_crosshair(self, me: PlayerState) -> None:
        cx, cy = self.to_screen(me.pos + heading(me.facing) * self.cursor_depth, me)
        if getattr(self, "scoped", False):
            pygame.draw.circle(self.screen, (255, 70, 85), (cx, cy), 2)  # scoped: just a dot, the reticle is the scope
            return
        col = C_ENEMY if self.match.time < self.ui.hit_marker else (120, 255, 200)
        d = self.match.weapons.get(me.weapon.key) if me.weapon else None
        gap = 4 + (self.match.current_spread(me, d) * self.cursor_depth * math.pi / 180 * self.scale if d else 0)
        from client import crosshair
        ch = self.crosshair
        hit = self.match.time < self.ui.hit_marker
        color = C_ENEMY if hit else pygame.Color(str(ch.get("crosshair_color", "#78ffc8")))
        spread_px = gap - 4  # the arms open up with the weapon's current spread
        crosshair.draw(self.screen, (cx, cy), color, float(ch.get("crosshair_size", 1.0)),
                       float(ch.get("crosshair_gap", 4.0)) + spread_px, bool(ch.get("crosshair_dot", True)))

    def text(self, msg: str, pos: tuple[float, float], col=C_TEXT, big: bool = False, center: bool = False) -> None:
        img = self.pixel_text(msg, col, 2 if big else 1)
        x, y = pos
        if center:
            x -= img.get_width() / 2
        self.screen.blit(img, (x, y))
