"""Drawing the world: map, objects, effects, players, tracers, sight cone."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)


class WorldViewMixin:
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
        normal = (self.w / 2, self.h * (0.5 + self.camera_push * 0.5))
        if not getattr(self, "zoom_level", 0) or me.pid != self.me:
            return me.pos, normal
        pull = 1.0 if getattr(self, "scoped", False) else 0.45
        center = me.pos + heading(me.facing) * (self.cursor_depth * pull)
        return center, (normal[0], normal[1] + (self.h / 2 - normal[1]) * pull)

    def poly(self, rect, me: PlayerState) -> list[tuple[float, float]]:
        return [self.to_screen(Vec(x, y), me) for x, y in ((rect.x0, rect.y0), (rect.x1, rect.y0), (rect.x1, rect.y1), (rect.x0, rect.y1))]

    def draw(self) -> None:
        m, s = self.match, self.screen
        me = m.players.get(self.me)
        if me is None or m.phase == "lobby":
            self.draw_lobby()
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
            lbl = self.pixel_text(site.name, C_SITE, 3)
            s.blit(lbl, (sx - lbl.get_width() / 2, sy - lbl.get_height() / 2))
        for drop in m.drops:  # weapons lying on the ground, hand sprite at 2x the world scale
            size = (round(2 * self.scale), round(self.scale))
            gun = self.bank.scaled(f"weapons/val2d/{self.weapon_art(drop.key)}.png", size)
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
        for orb in m.orbs:  # ultimate orbs: a pale yellow diamond that pulses
            ox, oy = self.to_screen(orb, me)
            size = self.scale * (0.32 + 0.04 * math.sin(m.time * 5))
            pts = [(ox, oy - size), (ox + size * 0.7, oy), (ox, oy + size), (ox - size * 0.7, oy)]
            pygame.draw.polygon(s, (247, 240, 168), pts)
            pygame.draw.polygon(s, (120, 110, 60), pts, 2)
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
        self.draw_sight(me)
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
            muzzle = self.bank.scaled("fx/muendung.png", (size, size), frame, 8) if tr.muzzle else None
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
                s.blit(img, (px - img.get_width() / 2, py - img.get_height() / 2))
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
        if self.aiming and me.pid == self.me and me.alive:
            self.draw_aim_preview(me, self.aiming)
        self.draw_crosshair(me)
        sight_range = abilities.lowest(m, me, "sight_range")
        if sight_range is not None:
            fog = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            fog.fill((10, 8, 14, 225))
            cx, cy = self.to_screen(me.pos, me)
            pygame.draw.circle(fog, (0, 0, 0, 0), (cx, cy), sight_range * self.scale)
            s.blit(fog, (0, 0))
        if me.blind_until > m.time:
            flash = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            flash.fill((255, 255, 255, int(min(1.0, (me.blind_until - m.time) / 0.6) * 245)))
            s.blit(flash, (0, 0))
        self.draw_hud(me)
        if self.ui.buy_open:
            self.draw_buy(me)
        own = m.players.get(self.me)
        if own is not None and (not own.alive or m.phase == "end") and m.phase in ("live", "planted", "end") \
                and not self.ui.show_scores and m.mode != "deathmatch":
            self.draw_damage_report(own)
        if self.ui.show_scores or m.phase == "over":
            self.draw_scores()

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
        r = int(self.h * 0.44)
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

    def draw_sight(self, me: PlayerState) -> None:
        """Darkens everything the player cannot see: outside the field of view, behind walls and smokes."""
        from client.vision import body_circle, sight_polygon
        m = self.match
        if not me.alive:
            return
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
        center = self.camera(me)[0]
        cx, cy = self.to_screen(center, me)
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
        nx, ny = self.to_screen(me.pos + Vec(0, 1), me)
        north = math.degrees(math.atan2(-(ny - cy), nx - cx))
        rotated = pygame.transform.rotate(crop, north - 90)
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
