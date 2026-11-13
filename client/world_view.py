"""Drawing the world: map, objects, effects, players, tracers, sight cone."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)
from gameplay.kit.engine import aimed_device
from gameplay.world import Deck, Wall


class WorldViewMixin:
    def piloted_owl_drone(self, me: PlayerState) -> Effect | None:
        if me.pid != self.me or me.channel_until <= self.match.time:
            return None
        return next((e for e in self.match.effects if e.owner == me.pid
                     and e.props.get("sprite") == "sova_owl_drone" and not e.props.get("ended")
                     and e.start <= self.match.time < e.until), None)

    def to_screen(self, p: Vec, me: PlayerState) -> tuple[float, float]:
        center, (cx, cy) = self.camera(me)
        rel = (p - center).rotated(-me.facing)
        return cx + rel.x * self.scale, cy - rel.y * self.scale

    def weapon_art(self, key: str) -> str:
        """Sprite name of a weapon (its `art`, else the key)."""
        d = self.match.weapons.get(key)
        return d.art if d is not None and d.art else key

    def camera(self, me: PlayerState) -> tuple[Vec, tuple[float, float]]:
        """World point the camera looks at and where it sits on screen. Aiming down sights moves the view toward the
        crosshair (a scope all the way: the crosshair is the screen centre and the view follows it)."""
        if self.shadow_view and (ab := self.shadow_ability(me)):
            return self.shadow_target(me, ab), (self.w / 2, self.h / 2)
        normal = (self.w / 2, self.h * (0.5 + self.camera_push * 0.5))
        if me.pid == self.me and me.channel_until > self.match.time:
            for effect in self.match.effects:
                if (effect.owner == me.pid and effect.props.get("sprite") in ("gekko_thrash", "skye_tiger", "sova_owl_drone", "tejo_drone")
                        and not effect.props.get("ended")
                        and (effect.props.get("sprite") != "sova_owl_drone" or effect.start <= self.match.time)):
                    return effect.pos, normal
        pull = self.camera_aim_pull(me)
        if not pull:
            return me.pos, normal
        center = me.pos + heading(me.facing) * (self.cursor_depth * pull)
        return center, (normal[0], normal[1] + (self.h / 2 - normal[1]) * pull)

    def camera_aim_pull(self, me: PlayerState) -> float:
        if not self.zoom_level or me.pid != self.me:
            return 0.0
        return 1.0 if self.scoped else 0.45

    def scope_radius(self) -> int:
        return int(self.h * 0.44)

    def in_view(self, point: tuple[float, float], me: PlayerState) -> bool:
        x, y = point
        if not (0 <= x < self.w and 0 <= y < self.h):
            return False
        return (not self.scoped or me.pid != self.me
                or math.hypot(x - self.w // 2, y - self.h // 2) < self.scope_radius())

    def sees_enemy(self, me: PlayerState, enemy: PlayerState) -> bool:
        return (self.mode != "client" or enemy.visible) and self.match.can_see(me, enemy)

    def player_screen(self, player: PlayerState, me: PlayerState) -> tuple[float, float]:
        x, y = self.to_screen(player.pos, me)
        return x, y - (player.ground + player.z) * self.scale * HEIGHT_DRAW

    def deck_view_upper(self, deck: Deck, me: PlayerState) -> bool:
        """Prefer the floor of a visible enemy nearest the centre of this view."""
        own_upper = me.ground >= deck.level
        enemies = []
        if me.alive and me.blind_until <= self.match.time:
            for p in self.match.players.values():
                if p.team == me.team or not deck.rect.contains(p.pos) or not self.sees_enemy(me, p):
                    continue
                x, y = self.player_screen(p, me)
                if self.in_view((x, y), me):
                    upper = p.ground >= deck.level
                    enemies.append((math.hypot(x - self.w / 2, y - self.h / 2), upper != own_upper, p.pid, upper))
        return min(enemies)[-1] if enemies else own_upper

    def poly(self, rect, me: PlayerState) -> list[tuple[float, float]]:
        return [self.to_screen(Vec(x, y), me) for x, y in ((rect.x0, rect.y0), (rect.x1, rect.y0), (rect.x1, rect.y1), (rect.x0, rect.y1))]

    def draw(self) -> None:
        m, s = self.match, self.screen
        me = m.players.get(self.me)
        if me is None or m.phase == "lobby":
            self.draw_lobby()
            return
        me = self.view_player(me)
        shadow_aim = self.shadow_ability(me)
        if shadow_aim and self.shadow_view:
            self.draw_shadow_view(me, shadow_aim)
            if self.client is not None and not self.client.connected:
                self.draw_match_status()
            return
        s.fill(C_BG)
        wm = m.world
        deck_views = {deck: self.deck_view_upper(deck, me) for deck in wm.decks}
        if me.duel_bounds is not None:
            points = self.poly(me.duel_bounds, me)
            pygame.draw.polygon(s, (39, 27, 61), points)
            pygame.draw.polygon(s, (169, 106, 218), points, 3)
        elif self.map_surface is not None:
            self.draw_map_texture(me)
        else:
            self.draw_map_placeholder(me)
        self.draw_deck_cutaways(me, deck_views)
        self.draw_live_objects(me)
        for site in wm.sites:
            sx, sy = self.to_screen(site.rect.center, me)
            lbl = self.pixel_text(site.name, C_SITE, 3)
            s.blit(lbl, (sx - lbl.get_width() / 2, sy - lbl.get_height() / 2))
        can_show_interaction = (me.pid == self.me and me.alive and not self.aiming
                                and not self.ui.buy_open and not self.overlay
                                and not abilities.flag(m, me, "no_interact"))
        action = self.priority_interaction(me) if can_show_interaction else ""
        nearby_weapon = self.draw_ground_weapons(me, deck_views, highlight=can_show_interaction and not action)
        if can_show_interaction and not action and not nearby_weapon and not self.spike_blocks_interaction(me):
            action = self.door_interaction(me)
        self.ui.scorches = [(pos, until) for pos, until in self.ui.scorches if until > m.time]
        for pos, until in self.ui.scorches:
            d = round(3 * self.scale)
            mark = self.bank.scaled("maps/common/decals/scorch.png", (d, d))
            if mark is not None:
                mark = mark.copy()
                mark.set_alpha(int(255 * min(1.0, (until - m.time) / 5)))
                x, y = self.to_screen(pos, me)
                s.blit(mark, (x - d / 2, y - d / 2))
        for orb in m.orbs:  # ultimate orbs: a pale yellow diamond that pulses
            ox, oy = self.to_screen(orb, me)
            size = self.scale * (0.32 + 0.04 * math.sin(m.time * 5))
            pts = [(ox, oy - size), (ox + size * 0.7, oy), (ox, oy + size), (ox - size * 0.7, oy)]
            pygame.draw.polygon(s, (247, 240, 168), pts)
            pygame.draw.polygon(s, (120, 110, 60), pts, 2)
        for orb in m.recovery_orbs:
            ox, oy = self.to_screen(orb, me)
            size = max(5, round(self.scale * 0.32))
            pygame.draw.circle(s, (27, 84, 69), (ox, oy), size)
            half = size // 2
            pygame.draw.line(s, C_ALLY, (ox - half, oy), (ox + half, oy), 2)
            pygame.draw.line(s, C_ALLY, (ox, oy - half), (ox, oy + half), 2)
        for e in m.effects:
            if self.mode != "client" and not m._effect_visible(e, me):
                continue
            ground = e.props.get("settled_ground")
            if ground is not None and (deck := wm.deck_at(e.pos)) in deck_views:
                if (ground >= deck.level) != deck_views[deck]:
                    continue
            self.draw_effect(e, me)
            remaining = self.smoke_warning(e)
            if remaining:
                diameter = max(1, round(2 * e.radius * self.scale))
                ring = pygame.Rect(0, 0, diameter, diameter)
                x, y = self.to_screen(e.pos, me)
                ring.center = x, y - (ground or 0) * self.scale * HEIGHT_DRAW
                pygame.draw.arc(s, C_TEXT, ring, math.pi / 2, math.pi / 2 + math.tau * remaining, 2)
        if m.spike_pos is not None:
            px, py = self.to_screen(m.spike_pos, me)
            blink = m.phase != "planted" or int(m.time * (2 + 6 * (1 - m.spike_time_left() / 45))) % 2 == 0
            size = round(self.scale)
            img = self.bank.scaled("fx/spike.png", (size, size), 0 if blink else 1, 16)
            if img is not None:
                s.blit(img, (px - size / 2, py - size / 2))
            else:
                pygame.draw.rect(s, C_ENEMY if blink else (90, 40, 40), (px - 6, py - 6, 12, 12))
        ground_sight = self.draw_sight(me)
        for e in m.effects:
            if e.kind == "snapshot" and e.team == me.team and m.time < e.until:
                center = self.to_screen(e.pos, me)
                pygame.draw.circle(s, (247, 240, 168), center, max(4, round(self.scale * 0.26)), 2)
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
            if tr.until - m.time > 0.1:  # long-lived cheat tracer: no muzzle flash after the first moment
                continue
            size = max(1, round(self.scale * 0.5))
            muzzle = self.bank.scaled("fx/muzzle_flash.png", (size, size), frame, 8) if tr.muzzle else None
            if muzzle is not None and (tr.b - tr.a).length() > 0.7:
                mx, my = self.to_screen(tr.a + (tr.b - tr.a).normalized() * 0.6, me)
                s.blit(muzzle, (mx - size / 2, my - size / 2))
        opaque_walls = [w for w in m.combat_walls() if w.full and w.blocks_sight and m.wall_active(w)]
        players = sorted(m.players.values(), key=lambda p: self.on_deck_view(p, deck_views)) if deck_views else m.players.values()
        for p in players:
            if p.pid != me.pid and me.status.get("waylay_refract_transit", 0) > m.time:
                continue
            if p.pid != me.pid and p.team == me.team and not self.on_deck_view(p, deck_views):
                continue
            if not p.alive:
                if p.visible or self.mode != "client":
                    bx, by = self.to_screen(p.pos, me)
                    body = self.character_frame(p, me)
                    if body is not None:
                        s.blit(body, (bx - body.get_width() / 2, by - body.get_height() / 2))
                continue
            if p.team != me.team and not self.sees_enemy(me, p):
                continue
            px, py = self.to_screen(p.pos, me)
            if p.status.get("waylay_refract_transit", 0) > m.time:
                diameter = max(1, round(self.scale * 0.9))
                mote = self.bank.scaled("fx/waylay_mote.png", (diameter, diameter))
                if mote is not None:
                    s.blit(mote, mote.get_rect(center=(px, py - p.ground * self.scale * HEIGHT_DRAW)))
                continue
            r = 0.4 * self.scale
            col = C_ALLY if p.team == me.team else C_ENEMY
            intangible = p.status.get("dismiss", 0) > m.time
            if not intangible:
                self.draw_facing_marker(p, me, col)
            img = self.character_frame(p, me)
            # height on screen: ground (ramps, platforms) plus jump, one continuous scale, so nothing pops
            lift_ground, lift = p.ground * self.scale * HEIGHT_DRAW, (p.ground + p.z) * self.scale * HEIGHT_DRAW
            if lift > 0.5:
                shadow_w = max(4, round(self.scale * (0.9 - min(p.z, 1.5) * 0.25)))
                shadow = pygame.Surface((shadow_w, max(2, shadow_w // 3)), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow, (0, 0, 0, 110 if p.z > 0.01 else 70), shadow.get_rect())
                feet_y = py + (img.get_height() / 2 if img else r) - shadow.get_height()
                s.blit(shadow, (px - shadow_w / 2, feet_y - lift_ground))
                py -= lift
            if img is not None:
                if intangible:
                    img = img.copy()
                    img.fill((225, 104, 255, 145), special_flags=pygame.BLEND_RGBA_MULT)
                bounds = img.get_rect(center=(round(px), round(py)))
                s.blit(self.clip_figure(img, bounds, me, p, opaque_walls), bounds)
                if not intangible:
                    self.draw_held(p, me, (px, py), img.get_height())
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
                s.blit(self.pixel_text("^", C_TEXT), (px + r, py - r))
            if p.pid != self.me:
                name = self.pixel_text(p.name, col)
                s.blit(name, (px - name.get_width() / 2, py - r - 22))
        self.draw_bursts(me)
        if getattr(self, "scoped", False) and me.pid == self.me:
            self.draw_scope()
        own_player = m.players.get(self.me)
        tactical = (self.tactical_ability(own_player) if own_player is not None and self.aiming
                    and (own_player.alive or m.can_cast_dead(own_player, self.aiming)) else None)
        if shadow_aim:
            self.draw_shadow_marker(me, shadow_aim)
        elif self.aiming and me.pid == self.me and me.alive and not tactical:
            self.draw_aim_preview(me, self.aiming)
        if not shadow_aim:
            self.draw_crosshair(me)
        sight_range = m.sight_range(me)
        if sight_range is not None:
            fog = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            fog.fill((10, 8, 14, 225))
            cx, cy = self.to_screen(me.pos, me)
            pygame.draw.circle(fog, (0, 0, 0, 0), (cx, cy), sight_range * self.scale)
            s.blit(fog, (0, 0))
        self.draw_flash(me)
        self.draw_hud(me, ground_sight, sight_range)
        if tactical and self.aiming:
            self.draw_tactical_map(own_player, tactical, self.aiming)
        elif own_player and m.can_cast_dead(own_player, "X"):
            key = next((pygame.key.name(k).upper() for k, slot in self.ability_keys.items() if slot == "X"), "X")
            self.ability_hint(f"{key} · Not Dead Yet", C_ALLY)
        elif action:
            key = pygame.key.name(self.keys["interact"]).upper()
            self.ability_hint(f"{key} · {action}", C_TEXT)
        elif nearby_weapon:
            self.ability_hint(nearby_weapon, C_ALLY)
        if self.ui.buy_open:
            self.draw_buy(me)
        own = m.players.get(self.me)
        if own is not None and (not own.alive or m.phase == "end") and m.phase in ("live", "planted", "end") \
                and not self.ui.show_scores and m.mode != "deathmatch":
            self.draw_damage_report(own)
        if self.ui.show_scores or m.phase == "over":
            self.draw_scores()
        if self.client is not None and not self.client.connected:
            self.draw_match_status()

    def spike_blocks_interaction(self, me: PlayerState) -> bool:
        m = self.match
        return ((m.spike_carrier == me.pid and m.world.site_at(me.pos, me.level) is not None)
                or (m.phase == "planted" and m.side(me.team) == "defense" and m._can_reach_planted_spike(me)))

    def door_interaction(self, me: PlayerState, aim: Vec | None = None) -> str:
        door = self.match.interactable_door(me, aim)
        if door is None:
            return ""
        if self.client and door.rect in self.match.world.timed_doors and door.rect in self.match.open_doors:
            return ""
        return "Close door" if door.rect in self.match.open_doors else "Open door"

    def priority_interaction(self, me: PlayerState) -> str:
        m = self.match
        if m.phase not in ("live", "planted"):
            return ""
        if me.zipline is not None:
            return "Leave zipline"
        if self.spike_blocks_interaction(me):
            return ""
        if m.zipline_endpoint_in_reach(me) is not None:
            return "Use zipline"
        if not abilities.flag(m, me, "no_abilities") and (device := aimed_device(m, me, self.cursor_depth)):
            return f"Activate {device.props['manual']}" if device.props.get("manual") else "Recall utility"
        if m.mode != "deathmatch":
            return self.door_interaction(me, me.pos + heading(me.facing) * self.cursor_depth)
        return ""

    def draw_ground_weapons(self, me: PlayerState, deck_views: dict[Deck, bool], *, highlight: bool = True) -> str:
        m, s = self.match, self.screen
        target = None
        automatic = None
        alternatives = []
        if me.alive and m.mode == "deathmatch":
            target = m._deathmatch_station_in_reach(me) if m.phase == "live" else None
        elif me.alive:
            candidates = [drop for drop in m.drops if drop.key in m.weapons and m.drop_in_reach(me, drop)]
            aim = me.pos + heading(me.facing) * self.cursor_depth
            if m.time - me.dropped_at >= 1.0:
                automatic = min((drop for drop in candidates if m.weapons[drop.key].slot not in me.weapons),
                                key=lambda drop: (drop.pos - me.pos).length(), default=None)
            target = automatic
            if target is None and not self.spike_blocks_interaction(me):
                candidates.sort(key=lambda drop: ((drop.pos - aim).length(), (drop.pos - me.pos).length()))
                if candidates:
                    target, *alternatives = candidates
        size = (round(2 * self.scale), round(self.scale))
        for drop in sorted(m.drops, key=lambda drop: drop is target):
            ground = m.drop_ground(drop)
            deck = m.world.deck_at(drop.pos) if deck_views else None
            if deck in deck_views and drop is not target and (ground >= deck.level) != deck_views[deck]:
                continue
            gun = self.bank.weapon(self.weapon_art(drop.key), size, drop.skin)
            x, y = self.to_screen(drop.pos, me)
            y -= ground * float(m._mv["level_height"]) * self.scale * HEIGHT_DRAW
            rect = gun.get_rect(center=(x, y)) if gun is not None else pygame.Rect(round(x) - 8, round(y) - 3, 16, 6)
            if highlight and drop is target:
                pygame.draw.rect(s, C_BG, rect.inflate(8, 8), border_radius=3)
                pygame.draw.rect(s, C_ALLY, rect.inflate(8, 8), 2, border_radius=3)
            if gun is not None:
                s.blit(gun, rect)
            else:
                pygame.draw.rect(s, C_MUTED, rect)
        if not highlight or target is None or target.key not in m.weapons:
            return ""
        weapon = m.weapons[target.key]
        if target is automatic:
            return f"Auto-pickup · {weapon.name}"
        key = pygame.key.name(self.keys["interact"]).upper()
        verb = "Swap for" if m.mode != "deathmatch" and weapon.slot in me.weapons else "Pick up"
        label = f"{key} · {verb} {weapon.name}"
        if alternatives:
            label += f" · Also: {m.weapons[alternatives[0].key].name}"
            if len(alternatives) > 1:
                label += f" +{len(alternatives) - 1}"
        return label

    def draw_shadow_view(self, me: PlayerState, ab: dict) -> None:
        self.screen.fill((16, 12, 28))
        if self.map_surface is None:
            self.draw_map_placeholder(me)
        else:
            self.draw_map_texture(me)
        decks = {deck: self.deck_view_upper(deck, me) for deck in self.match.world.decks}
        if (deck := self.match.world.deck_at(self.shadow_target(me, ab))) is not None:
            decks[deck] = not self.aim_alt
        self.draw_deck_cutaways(me, decks)
        self.draw_live_objects(me)
        self.screen.fill((92, 75, 141), special_flags=pygame.BLEND_RGB_MULT)
        for enemy in self.match.players.values():
            if enemy.team != me.team and self.sees_enemy(me, enemy) and me.blind_until <= self.match.time:
                pygame.draw.circle(self.screen, C_ENEMY, self.player_screen(enemy, me), max(3, round(0.4 * self.scale)), 2)
        self.draw_flash(me)
        self.draw_hud(me, [], None)
        self.draw_shadow_marker(me, ab)

    def draw_flash(self, me: PlayerState) -> None:
        remaining = me.blind_until - self.match.time
        if self.match.paranoia_warning(me):
            warning = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            pygame.draw.rect(warning, (106, 72, 163, 135), warning.get_rect(), max(4, self.h // 35))
            self.screen.blit(warning, (0, 0))
        plasma = me.status.get("gekko_plasma_blind", 0) - self.match.time
        if plasma > 0:
            stain = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            pygame.draw.ellipse(stain, (28, 126, 215, int(min(1, plasma) * 235)),
                                (self.w * 0.14, self.h * 0.12, self.w * 0.72, self.h * 0.76))
            self.screen.blit(stain, (0, 0))
        if remaining > 0:
            flash = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            flash.fill((255, 255, 255, int(min(1.0, remaining / 0.6) * 245)))
            self.screen.blit(flash, (0, 0))

    def draw_shadow_marker(self, me: PlayerState, ab: dict) -> None:
        target = self.shadow_target(me, ab)
        world = self.match.world
        ground, height = world.smoke_target_heights(target, self.aim_alt, self.shadow_lift)
        distance = self.match.smoke_target_distance(me, target, height)
        out_of_range = distance > float(ab["range"]) + 1e-9
        x, y = self.to_screen(target, me)
        y -= height * self.scale * HEIGHT_DRAW
        if y < 16:
            pygame.draw.polygon(self.screen, C_ALLY, [(x, 12), (x - 7, 24), (x + 7, 24)])
        else:
            self.radius_ring(target, float(ab["radius"]), C_ENEMY if out_of_range else (118, 178, 255), me, height)
            if height > ground:
                self.radius_ring(target, float(ab["radius"]), C_MUTED, me, ground)
        cast = pygame.key.name(self.keys[f"ability_{self.aiming.lower()}"]).upper()
        toggle = pygame.key.name(self.keys["reload"]).upper()
        floor = "No landing surface" if world.drop_recovery(target) is not None else f"Floor {ground:g}"
        if out_of_range:
            floor += " · Out of range"
        if height > ground:
            floor += f" · Drop {height - ground:g} m"
        deck = " · Scroll to select floor" if world.deck_at(target) is not None else ""
        self.ability_hint(f"Dark Cover · {distance:.1f} m · {floor}{deck} · Hold LMB/RMB for distance · Ctrl+scroll height · "
                          f"{cast} cast · {toggle} switch view",
                          C_TEXT)

    def on_deck_view(self, player: PlayerState, deck_views: dict[Deck, bool]) -> bool:
        deck = self.match.world.deck_at(player.pos) if deck_views else None
        return deck is None or (player.ground >= deck.level) == deck_views[deck]

    def draw_deck_cutaways(self, me: PlayerState, deck_views: dict[Deck, bool]) -> None:
        for deck, upper in deck_views.items():
            if not upper and not deck.closed_below:
                outline = self.poly(deck.rect, me)
                pygame.draw.polygon(self.screen, (71, 65, 63), outline)
                pygame.draw.polygon(self.screen, (97, 83, 76), outline, 1)

    def clip_figure(self, image: pygame.Surface, bounds: pygame.Rect, me: PlayerState,
                    player: PlayerState, walls: list[Wall]) -> pygame.Surface:
        """Keep billboard pixels from drawing over a solid wall next to the player."""
        reach = max(bounds.size) / self.scale
        mask = None
        for wall in walls:
            rect = wall.rect
            if (wall.on_deck and wall.base > player.level
                    or rect.x0 > player.pos.x + reach or rect.x1 < player.pos.x - reach
                    or rect.y0 > player.pos.y + reach or rect.y1 < player.pos.y - reach):
                continue
            poly = self.poly(rect, me)
            xs, ys = zip(*poly)
            if min(xs) >= bounds.right or max(xs) < bounds.left or min(ys) >= bounds.bottom or max(ys) < bounds.top:
                continue
            if mask is None:
                mask = pygame.Surface(bounds.size, pygame.SRCALPHA)
                mask.fill((255, 255, 255, 255))
            pygame.draw.polygon(mask, (255, 255, 255, 0), [(x - bounds.left, y - bounds.top) for x, y in poly])
        if mask is None:
            return image
        image = image.copy()
        image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        return image

    def draw_facing_marker(self, p: PlayerState, me: PlayerState, col: tuple[int, int, int]) -> None:
        """Exact view direction on the ground: a dotted line from the feet and an arrow head at its end."""
        length = float(VIEW["facing_marker"])
        aim = heading(p.facing)
        side = aim.rotated(90)
        layer_pts = [self.to_screen(p.pos + aim * (0.45 + i * 0.16), me) for i in range(int((length - 0.45) / 0.16))]
        dot = max(2, round(self.scale / 16))  # one sprite pixel
        for x, y in layer_pts[::2]:
            pygame.draw.rect(self.screen, col, (round(x - dot / 2), round(y - dot / 2), dot, dot))
        tip = p.pos + aim * length
        head = [self.to_screen(tip, me), self.to_screen(tip - aim * 0.28 + side * 0.17, me), self.to_screen(tip - aim * 0.28 - side * 0.17, me)]
        pygame.draw.polygon(self.screen, col, head)

    def draw_scope(self) -> None:
        """Sniper scope: black outside a circle around the screen centre, thin reticle lines."""
        r = self.scope_radius()
        cx, cy = self.w // 2, self.h // 2
        if getattr(self, "_scope_mask", None) is None or self._scope_mask.get_size() != (self.w, self.h):
            mask = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            mask.fill((4, 6, 8, 255))
            pygame.draw.circle(mask, (0, 0, 0, 0), (cx, cy), r)
            for i in range(14):  # soft dark rim inside the lens
                pygame.draw.circle(mask, (4, 6, 8, 150 - i * 10), (cx, cy), r - i, 1)
            self._scope_mask = mask
        self.screen.blit(self._scope_mask, (0, 0))
        line = (10, 12, 14)
        pygame.draw.line(self.screen, line, (cx - r, cy), (cx - 18, cy), 2)
        pygame.draw.line(self.screen, line, (cx + 18, cy), (cx + r, cy), 2)
        pygame.draw.line(self.screen, line, (cx, cy + 18), (cx, cy + r), 2)
        pygame.draw.line(self.screen, line, (cx, cy - r), (cx, cy - 18), 1)

    def draw_sight(self, me: PlayerState) -> list[Vec]:
        """Darkens everything the player cannot see: outside the field of view, behind walls and smokes."""
        from client.vision import body_circle, sight_polygon
        m = self.match
        if not me.alive:
            return []
        fov = 360.0 if m.cfg.lobby.all_around_sight else m.fov
        reach = float(rule_value("sight", "view_distance", 60.0))
        rays = int(VIEW["sight_rays"])
        pts = sight_polygon(m, me, fov, reach, rays)
        low = sight_polygon(m, me, fov, reach, rays, low=True)
        shade = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        shade.fill((4, 6, 10, int(VIEW["outside_darkness"])))
        clear = (0, 0, 0, 0)
        # behind head-high cover only taller things (jumping players, platforms) can be seen: drawn grey
        pygame.draw.polygon(shade, (40, 46, 54, int(VIEW["behind_cover_grey"])), [self.to_screen(p, me) for p in pts])
        pygame.draw.polygon(shade, clear, [self.to_screen(p, me) for p in low])
        pygame.draw.polygon(shade, clear, [self.to_screen(p, me) for p in body_circle(me.pos, float(VIEW["body_sight"]))])
        self.screen.blit(shade, (0, 0))
        return low

    def projectile_point(self, start: Vec, end: Vec, progress: float, me: PlayerState) -> tuple[float, float]:
        x, y = self.to_screen(start + (end - start) * progress, me)
        return x, y - math.sin(progress * math.pi) * self.scale * 0.8

    def draw_projectile(self, e: Effect, me: PlayerState) -> bool:
        """Thrown ability in flight: moves from the thrower to the target on a small arc. True while flying."""
        assert e.a is not None
        from gameplay.geometry import projectile_progress

        progress = projectile_progress(self.match.time, e.start, e.until,
                                       lands_at_expiry=bool(e.props.get("bolt_path")) or e.props.get("sprite") == "sova_recon_bolt")
        if progress >= 1.0:
            return False
        if path := e.props.get("bolt_path"):
            points = [Vec(*point) for point in path]
            segments = [(a, (b - a)) for a, b in zip(points, points[1:])]
            distance = progress * sum(delta.length() for _, delta in segments)
            point = e.pos
            for start, delta in segments:
                length = delta.length()
                if length and distance <= length:
                    point = start + delta * (distance / length)
                    break
                distance -= length
            x, y = self.to_screen(point, me)
        else:
            x, y = self.projectile_point(e.a, e.pos, progress, me)
        rel, size_m = ("fx/ability/grenade.png", (6 / 16, 5 / 16)) if e.kind == "blast" else ("fx/ability/projectile_orb.png", (12 / 16, 6 / 16))
        size = (max(1, round(size_m[0] * self.scale)), max(1, round(size_m[1] * self.scale)))
        img = self.effect_sprite(e, size[0]) or self.bank.scaled(rel, size)
        if img is not None:
            self.screen.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2))
        else:
            pygame.draw.circle(self.screen, C_SITE, (x, y), 4)
        dot = self.bank.scaled("fx/ability/arc_dot.png", (3, 3))
        if dot is not None and not path:
            for i in range(1, 6):  # remaining path as dots
                q = progress + (1 - progress) * i / 6
                dx, dy = self.projectile_point(e.a, e.pos, q, me)
                self.screen.blit(dot, (dx - 1, dy - 1))
        return True

    def radius_ring(self, pos: Vec, radius: float, color: tuple[int, int, int], me: PlayerState, ground: float = 0.0) -> None:
        x, y = self.to_screen(pos, me)
        y -= ground * self.scale * HEIGHT_DRAW
        d = max(2, round(2 * radius * self.scale))
        img = self.bank.tinted("fx/radius_ring.png", (d, d), 0, 0, color)
        if img is not None:
            self.screen.blit(img, (x - d / 2, y - d / 2))
        else:
            pygame.draw.circle(self.screen, color, (x, y), d / 2, 1)

    def panel(self, rel: str, rect: pygame.Rect) -> None:
        """Semi-transparent 9-slice HUD panel (8 px corners, drawn at 1x)."""
        draw_nine_slice(self.screen, self.bank, rel, rect, 8, 1)

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
                trail = self.bank.strip_frame("fx/dash_trail.png", size, (t * 10) % 1.0, 16)
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
        center, (cx, cy) = self.camera(me)
        radius = math.ceil(math.hypot(max(cx, self.w - cx), max(cy, self.h - cy))) + 2
        base = self.w / VIEW_METERS          # scale of the cached map image
        zoom = self.scale / base
        src_r = math.ceil(radius / zoom) + 1  # crop radius in map-image pixels
        size = 2 * src_r
        if self._crop is None or self._crop.get_width() != size:
            self._crop = pygame.Surface((size, size)).convert()
        self._crop.fill(C_BG)
        mx = center.x * base
        my = (self.match.world.height - center.y) * base
        self._crop.blit(self.map_surface, (src_r - mx, src_r - my))
        crop = self._crop if abs(zoom - 1.0) < 1e-6 else pygame.transform.scale(self._crop, (round(size * zoom), round(size * zoom)))
        rotated = pygame.transform.rotate(crop, me.facing)
        self.screen.blit(rotated, (cx - rotated.get_width() / 2, cy - rotated.get_height() / 2))

    def draw_live_objects(self, me: PlayerState) -> None:
        """Animated or phase-dependent map objects, rotated with the camera."""
        for cable in self.match.world.ziplines:
            start, end = self.to_screen(cable.start, me), self.to_screen(cable.end, me)
            pygame.draw.line(self.screen, (219, 173, 86), start, end, 2)
            for point in (start, end):
                pygame.draw.circle(self.screen, (238, 199, 118), point, 3)
            if cable.lower is not None:
                pygame.draw.circle(self.screen, (238, 199, 118), end, 6, 1)
        from gameplay.world import load_things
        objects = load_things()[0]
        for o in self.match.world.objects:
            spec = objects.get(o.key, {})
            if spec.get("door") or spec.get("hp"):
                self.draw_dynamic_cover(o, spec, me)
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

    def draw_dynamic_cover(self, o: object, spec: dict, me: PlayerState) -> None:
        """Door or destructible sprite rotated with the camera."""
        rect = o.rect  # type: ignore[attr-defined]
        is_open = rect in self.match.open_doors
        if rect in self.match.broken_cover:
            rel = str(spec.get("broken_tile", ""))
        else:
            rel = str(spec.get("open_tile" if is_open else "tile", ""))
        if not rel:
            return
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

    def effect_sprite(self, e: Effect, diameter: int, warning: bool = False) -> pygame.Surface | None:
        sprite = e.props.get("warning_sprite" if warning else "sprite")
        if not sprite:
            return None
        path = f"fx/{sprite}.png"
        raw = self.bank.raw(path)
        if raw is None:
            return None
        width = min(raw.get_width(), int((None if warning else e.props.get("sprite_width")) or raw.get_height()))
        if warning and raw.get_height() <= 16:
            diameter = max(1, round(self.scale))
        height = max(1, round(diameter * raw.get_height() / width))
        if warning:
            return self.bank.strip_frame(path, (diameter, height), 1 - (e.start - self.match.time) / 0.5, width)
        age = max(0.0, self.match.time - e.start)
        return self.bank.scaled(path, (diameter, height), int(age * 8) % self.bank.frames_in(path, width), width)

    def smoke_warning(self, effect: Effect) -> float:
        """Fraction of the visible expiry countdown still remaining."""
        now = self.match.time
        window = float(VIEW.get("smoke_warning_seconds", 2.0))
        if effect.kind != "smoke" or effect.radius <= 0 or not effect.start <= now < effect.until or window <= 0:
            return 0.0
        left = effect.until - now
        return left / window if left <= window else 0.0

    def draw_effect(self, e: Effect, me: PlayerState) -> None:
        s = self.screen
        ex, ey = self.to_screen(e.pos, me)
        if e.props.get("sprite") == "fade_trail" and e.a is not None and e.b is not None:
            if me.team == e.team:
                pygame.draw.line(s, (118, 72, 164), self.to_screen(e.a, me), self.to_screen(e.b, me), 2)
            return
        if e.props.get("clone_facing") is not None:
            enemy = e.team != me.team
            img = self.chars.frame("yoru", "walk", enemy, self.scale, self.match.time)
            if img is not None:
                s.blit(img, img.get_rect(center=(ex, ey)))
            return
        ground = e.props.get("flight_height")
        if ground is None:
            ground = e.props.get("settled_ground") or 0
        ey -= (ground + e.fall_offset(self.match.time)) * self.scale * HEIGHT_DRAW
        if e.kind in ("tdm_recovery", "tdm_ultimate"):
            tint = C_ENEMY if e.team != me.team else (247, 240, 168) if e.kind == "tdm_ultimate" else C_ALLY
            pygame.draw.circle(s, tint, (ex, ey), max(1, round(e.radius * self.scale)), 2)
            return
        if cone := e.props.get("cone"):
            aim = Vec(*e.props["aim"])
            points = [(ex, ey)] + [
                self.to_screen(e.pos + aim.rotated(cone * (i / 16 - 0.5)) * e.radius, me)
                for i in range(17)
            ]
            layer = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            warmup = self.match.time < e.start
            pygame.draw.polygon(layer, (239, 163, 87, 45 if warmup else 135), points)
            pygame.draw.polygon(layer, (255, 211, 124, 180), points, 2)
            s.blit(layer, (0, 0))
            return
        if e.props.get("devour_tether"):
            owner = self.match.players.get(e.owner)
            if owner is not None and owner.alive:
                pygame.draw.line(s, (168, 78, 218), (ex, ey), self.to_screen(owner.pos, me), 3)
            return
        diameter = max(1, round(2 * e.radius * self.scale))
        if (wall := e.props.get("barrier")) is not None:
            points = self.poly(wall.rect, me)
            pygame.draw.polygon(s, (45, 122, 139), points)
            art = self.effect_sprite(e, max(1, round(self.scale)))
            if art is not None:
                s.blit(art, (ex - art.get_width() / 2, ey - art.get_height() / 2))
            pygame.draw.polygon(s, (120, 233, 217), points, 2)
            return
        if e.kind == "zone" and e.a is not None and e.b is not None:
            warmup = self.match.time < e.start
            width = max(2, round(e.radius * self.scale * 2))
            layer = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            start, end = self.to_screen(e.a, me), self.to_screen(e.b, me)
            if e.props.get("status") == "waylay_hinder":
                direction = (e.b - e.a).normalized().rotated(90)
                fraction = 1 if warmup else min(4, 1 + int((self.match.time - e.start) / 0.125)) / 4
                side = direction * e.radius * fraction
                corners = (e.a + side, e.b + side, e.b - side, e.a - side)
                points = [self.to_screen(point, me) for point in corners]
                pygame.draw.polygon(layer, (248, 148, 215, 45 if warmup else 130), points)
                pygame.draw.polygon(layer, (255, 214, 135, 175), points, 2)
                pygame.draw.line(layer, (155, 255, 229, 220), start, end, 1 if warmup else 4)
                s.blit(layer, (0, 0))
                return
            if e.props.get("sprite") == "veto_beam":
                pygame.draw.line(s, (118, 240, 171), start, end, 3)
                pygame.draw.line(s, (222, 255, 230), start, end, 1)
                return
            if e.props.get("sprite") == "tejo_strike":
                side = (e.b - e.a).normalized().rotated(90) * e.radius
                points = [self.to_screen(point, me) for point in (e.a - side, e.a + side, e.b + side, e.b - side)]
                pygame.draw.polygon(layer, (255, 94, 38, 32 if warmup else 130), points)
                pygame.draw.polygon(layer, (255, 171, 83, 125 if warmup else 245), points, 2)
                s.blit(layer, (0, 0))
                return
            tint = (119, 212, 125) if e.props.get("sprite") == "viper_emitter" else (84, 179, 255)
            if e.props.get("status") == "fade_nightfall":
                tint = (140, 71, 183)
            pygame.draw.line(layer, (*tint, 68 if warmup else 190), start, end, width)
            pygame.draw.line(layer, (209, 240, 255, 175), start, end, 1 if warmup else max(2, width // 5))
            s.blit(layer, (0, 0))
            return
        if e.start > self.match.time:
            if e.radius > 0:
                self.radius_ring(e.pos, e.radius, C_MUTED, me)
            warning = self.effect_sprite(e, diameter, warning=True)
            if warning is not None:
                s.blit(warning, (ex - warning.get_width() / 2, ey - warning.get_height() / 2))
            return
        if e.kind in ("blast", "flash") and e.a is not None and e.until > e.start:
            if self.draw_projectile(e, me):
                return
        if e.kind == "flash":
            return  # a flash without flight data is not drawn (it pops with its own effect)
        if e.kind == "blast":
            left = max(0.0, e.until - self.match.time)
            self.radius_ring(e.pos, e.radius, C_ENEMY if e.team != me.team else C_SITE, me)
            nade = self.effect_sprite(e, max(1, round(self.scale * 6 / 16))) or self.bank.scaled(
                "fx/ability/grenade.png", (max(1, round(self.scale * 6 / 16)), max(1, round(self.scale * 5 / 16))))
            if nade is not None:
                s.blit(nade, (ex - nade.get_width() / 2, ey - nade.get_height() / 2))
            else:
                pygame.draw.circle(s, C_SITE, (ex, ey), 4 + int(left * 6) % 4)
            return
        if e.kind in ("zone", "smoke", "sensor", "alarm") and e.props.get("sprite"):
            size = max(1, round(self.scale)) if e.kind in ("sensor", "alarm") else max(diameter, round(self.scale))
            sprite = self.effect_sprite(e, size)
            if sprite is not None:
                s.blit(sprite, (ex - size / 2, ey + size / 2 - sprite.get_height()))
                if e.kind in ("sensor", "alarm") and e.radius > 0:
                    self.radius_ring(e.pos, e.radius, (60, 140, 140), me)
                if e.props.get("carrying_spike") or e.data.get("carrying"):
                    pygame.draw.polygon(s, (240, 198, 250), [(ex, ey - 13), (ex + 5, ey - 8),
                                                            (ex, ey - 3), (ex - 5, ey - 8)])
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
            img = self.bank.strip_frame("fx/smoke_forming.png", (d, d), (self.match.time - e.start) / 0.5, 64)
            if img is not None:
                s.blit(img, (ex - d / 2, ey - d / 2))
                return
        art = {"smoke": "fx/smoke.png"}.get(e.kind)
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
            pulse = self.bank.strip_frame("fx/sensor_pulse.png", (pulse_d, pulse_d), (self.match.time % 1.0), 32)
            if pulse is not None:
                s.blit(pulse, (ex - pulse_d / 2, ey - pulse_d / 2))
            size = max(1, round(self.scale * 0.6))
            img = self.bank.scaled("fx/sensor.png", (size, size))
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
            tile = (self.bank.strip_frame("fx/vapor_wall_forming.png", (tile_px, tile_px), (self.match.time - e.start) / 0.4, 16)
                    if building and not e.props.get("sprite") else None) or self.bank.scaled(
                        f"fx/{e.props.get('sprite') or 'vapor_wall'}.png", (tile_px, tile_px))
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

    def view_player(self, me: PlayerState) -> PlayerState:
        """While dead in a live round, the camera and HUD follow a living teammate (click = next)."""
        if me.alive or self.match.phase not in ("live", "planted"):
            return me
        mates = sorted((p for p in self.match.players.values() if p.team == me.team and p.alive and p.pid != me.pid),
                       key=lambda p: p.pid)
        if not mates:
            return me
        return self.spectator_camera(mates[self.spectate_index % len(mates)])

    def spectator_camera(self, target: PlayerState) -> PlayerState:
        """A smoothed copy of the watched teammate for the camera: bots and remote players turn in jumps from tick to
        tick, and rotating the whole screen with every jump looks like lag. The copy turns and moves smoothly toward
        the real player (the real one is still drawn where it is)."""
        from dataclasses import replace
        now = self.match.time
        state = getattr(self, "_spec", None)
        if state is None or state[0] != target.pid or now < state[3] or now - state[3] > 1.0:
            self._spec = (target.pid, target.facing, target.pos, now)  # new target: start where it is
            return replace(target)
        _, facing, pos, last = state
        dt = now - last
        turn = (target.facing - facing + 540.0) % 360.0 - 180.0
        facing = (facing + turn * min(1.0, dt * 9.0)) % 360.0
        pos = pos + (target.pos - pos) * min(1.0, dt * 14.0)
        self._spec = (target.pid, facing, pos, now)
        return replace(target, facing=facing, pos=pos)
