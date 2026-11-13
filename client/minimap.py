"""Round minimap in the top-left corner: centred on the player, turning with the view (or north up), walls, sites,
team, seen enemies, bomb, smokes, the field of view and the own noise circle (how far your footsteps and shots are
heard, like the sound circle of a real tactical shooter). Values: config/client/hud.py."""
from __future__ import annotations

from collections.abc import Callable

from client.common import *  # noqa: F403  (pygame, colours, types)
from client.ui import color


class MinimapMixin:
    def tactical_layout(self) -> tuple[pygame.Rect, float]:
        wm = self.match.world
        scale = min(self.w * 0.72 / wm.width, self.h * 0.72 / wm.height)
        rect = pygame.Rect(0, 0, round(wm.width * scale), round(wm.height * scale))
        rect.center = (self.w // 2, self.h // 2)
        return rect, scale

    def tactical_point(self, mouse: tuple[int, int]) -> Vec | None:
        rect, scale = self.tactical_layout()
        if not rect.collidepoint(mouse):
            return None
        return Vec((mouse[0] - rect.left) / scale, self.match.world.height - (mouse[1] - rect.top) / scale)

    def draw_tactical_map(self, me: PlayerState, ab: dict, slot: str) -> None:
        rect, scale = self.tactical_layout()
        if self._tactical_static is None or self._tactical_static[0] != scale:
            self._tactical_static = (scale, self.build_minimap_static(scale))
        shade = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        shade.fill((9, 17, 24, 220))
        self.screen.blit(shade, (0, 0))
        pad = int(HUD["minimap_radius"]) * 2
        self.screen.blit(self._tactical_static[1], rect.topleft, (pad, pad, rect.width, rect.height))

        def project(point: Vec) -> tuple[float, float]:
            return rect.left + point.x * scale, rect.top + (self.match.world.height - point.y) * scale

        clip = self.screen.get_clip()
        self.screen.set_clip(rect)
        self.draw_minimap_barriers(self.screen, project)
        if not ab.get("global_target"):
            origin = project(me.pos)
            radius = float(ab.get("dead_range", ab["range"]) if not me.alive else ab["range"]) * scale
            mask = pygame.Surface(rect.size, pygame.SRCALPHA)
            mask.fill((9, 17, 24, 150))
            pygame.draw.circle(mask, (0, 0, 0, 0), (origin[0] - rect.left, origin[1] - rect.top), radius)
            self.screen.blit(mask, rect.topleft)
            pygame.draw.circle(self.screen, color("ally"), origin, radius, 1)
        for site in self.match.world.sites:
            self.kit.text(site.name, project(site.rect.center), "s", "gold", "center", bold=True)
        for p in self.match.players.values():
            if p.alive and p.team == me.team:
                if p.pid == me.pid:
                    self._mini_icon(self.screen, project(p.pos), "self", "text", 17, p.facing)
                else:
                    self._mini_icon(self.screen, project(p.pos), "ally", "ally", 12, p.facing)
        for effect in self.match.effects:
            if ab.get("astral_form") and effect.owner == me.pid and effect.props.get("sprite") == "astra_star":
                pygame.draw.circle(self.screen, color("gold"), project(effect.pos), 4, 1)
            if effect.kind == "smoke":
                pygame.draw.circle(self.screen, color("muted"), project(effect.pos), effect.radius * scale, 1)
        radius = float(ab["radius"]) * scale
        for i, point in enumerate(self.multi_points, 1):
            pos = Vec(*point)
            valid = self.match.valid_tactical_point(me, ab, pos)
            pygame.draw.circle(self.screen, color("gold" if valid else "enemy"), project(pos), radius, 2)
            self.kit.text(str(i), project(pos), "xs", "text", "center")
        limit = self.placement_limit(me, ab, slot)
        target = self.tactical_point(pygame.mouse.get_pos())
        if target is not None and self.multi_points and ab.get("tactical_line"):
            origin = Vec(*self.multi_points[0])
            axis = (target - origin).normalized()
            side = axis.rotated(90) * (float(ab["width"]) / 2)
            end = origin + axis * float(ab["length"])
            if axis.length():
                pygame.draw.polygon(self.screen, color("gold"),
                                    [project(p) for p in (origin - side, origin + side, end + side, end - side)], 2)
        elif target is not None and len(self.multi_points) < limit and self.match.valid_tactical_point(me, ab, target):
            pygame.draw.circle(self.screen, color("ally"), project(target), radius, 2)
        self.screen.set_clip(clip)
        pygame.draw.rect(self.screen, color("line"), rect, 1)
        self.text(ab["name"], (rect.centerx, rect.top - 34), center=True)
        hint = (f"Left click marks or removes ({len(self.multi_points)}/{limit}) · right click confirms"
                if int(ab.get("multi", 1)) > 1 else "Left click casts")
        if ab.get("astral_form") and not self.aim_alt:
            hint = "Left click places or recalls a star · right click aims Cosmic Divide"
        elif ab.get("tactical_line"):
            hint = "Left click sets origin and direction · right click clears origin"
        self.text(hint + " · Esc cancels", (rect.centerx, rect.bottom + 14), center=True)

    def minimap_scale(self) -> float:
        return 2 * int(HUD["minimap_radius"]) / float(HUD["minimap_meters"])

    def build_minimap_static(self, k: float) -> pygame.Surface:
        """Walls and crates of the whole map at scale k (pixels per metre), north up, with a margin so crops near the
        edge stay inside; drawn once per map."""
        wm = self.match.world
        pad = int(HUD["minimap_radius"]) * 2
        panel = pygame.Surface((round(wm.width * k) + 2 * pad, round(wm.height * k) + 2 * pad), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 0))
        floor = pygame.Rect(pad, pad, round(wm.width * k), round(wm.height * k))
        pygame.draw.rect(panel, (39, 54, 63, 255), floor)
        for rect in (rect for site in wm.sites for rect in site.plant_rects):
            x0, y0 = pad + rect.x0 * k, pad + (wm.height - rect.y1) * k
            bounds = (x0, y0, (rect.x1 - rect.x0) * k, (rect.y1 - rect.y0) * k)
            pygame.draw.rect(panel, (81, 77, 60, 255), bounds)
            pygame.draw.rect(panel, (147, 129, 86, 255), bounds, 1)
        for w in wm.walls:
            if (w.buy_phase_only or w.rect.x0 < -0.5 or w.rect.y0 < -0.5
                    or w.rect.x1 > wm.width + 0.5 or w.rect.y1 > wm.height + 0.5):
                continue
            x0, y0 = pad + w.rect.x0 * k, pad + (wm.height - w.rect.y1) * k
            rect = pygame.Rect(round(x0), round(y0), max(1, round((w.rect.x1 - w.rect.x0) * k)), max(1, round((w.rect.y1 - w.rect.y0) * k)))
            art = self.bank.scaled("ui/minimap/wall.png" if w.height > 1 else "ui/minimap/crate.png", rect.size)
            if art is not None:
                panel.blit(art, rect.topleft)
            else:
                pygame.draw.rect(panel, (150, 160, 168, 255) if w.height > 1 else (84, 104, 116, 255), rect)
        return panel

    def draw_minimap_barriers(self, surface: pygame.Surface, project: Callable[[Vec], tuple[float, float]]) -> None:
        if self.match.phase != "buy":
            return
        for wall in self.match.world.walls:
            if wall.buy_phase_only:
                rect = wall.rect
                corners = ((rect.x0, rect.y0), (rect.x1, rect.y0), (rect.x1, rect.y1), (rect.x0, rect.y1))
                pygame.draw.polygon(surface, (105, 187, 219), [project(Vec(x, y)) for x, y in corners])

    def draw_minimap(self, me: PlayerState, ground_sight: list[Vec], sight_range: float | None) -> None:
        m, wm, s = self.match, self.match.world, self.screen
        r = int(HUD["minimap_radius"])
        k = self.minimap_scale()
        rotate = bool(HUD["minimap_rotate"])
        cx, cy = 20 + r, 20 + r
        if m.minimap_obscured(me):
            pygame.draw.circle(s, (15, 12, 23), (cx, cy), r)
            pygame.draw.circle(s, color("line"), (cx, cy), r, 1)
            self.kit.text("MINIMAP OBSCURED", (cx, cy), "xs", "muted", "center", bold=True)
            return
        if self._minimap_static is None:
            self._minimap_static = self.build_minimap_static(k)
        static = self._minimap_static
        pad = 2 * r
        size = int(r * 2 * 1.5)
        mx, my = pad + me.pos.x * k, pad + (wm.height - me.pos.y) * k
        crop = pygame.Surface((size, size), pygame.SRCALPHA)
        crop.blit(static, (size / 2 - mx, size / 2 - my))
        if rotate:
            crop = pygame.transform.rotate(crop, me.facing)
        view = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
        view.fill((15, 25, 35, 225))
        view.blit(crop, (r - crop.get_width() / 2, r - crop.get_height() / 2))

        def pt(v: Vec) -> tuple[float, float]:
            rel = v - me.pos
            if rotate:
                rel = rel.rotated(-me.facing)
            return r + rel.x * k, r - rel.y * k

        self.draw_minimap_barriers(view, pt)

        sight = pygame.Surface(view.get_size(), pygame.SRCALPHA)
        white = (255, 255, 255, 255)
        if ground_sight and me.blind_until <= m.time:
            pygame.draw.polygon(sight, white, [pt(p) for p in ground_sight])
            camera, (screen_x, screen_y) = self.camera(me)

            def screen_point(x: float, y: float) -> tuple[float, float]:
                offset = Vec((x - screen_x) / self.scale, (screen_y - y) / self.scale)
                return pt(camera + offset.rotated(me.facing))

            clip = pygame.Surface(view.get_size(), pygame.SRCALPHA)
            if self.scoped and me.pid == self.me:
                pygame.draw.circle(clip, white, screen_point(self.w // 2, self.h // 2),
                                   self.scope_radius() * k / self.scale)
            else:
                pygame.draw.polygon(clip, white, [screen_point(x, y) for x, y in
                                                  ((0, 0), (self.w, 0), (self.w, self.h), (0, self.h))])
            sight.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            if sight_range is not None:
                clip.fill((0, 0, 0, 0))
                pygame.draw.circle(clip, white, (r, r), sight_range * k)
                sight.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            clip.fill((236, 232, 225, 26))
            clip.blit(sight, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            view.blit(clip, (0, 0))

        contacts = pygame.Surface(view.get_size(), pygame.SRCALPHA)
        for e in m.effects:
            if self.mode != "client" and not m._effect_visible(e, me):
                continue
            layer = view if e.team == me.team else contacts
            if e.kind == "snapshot" and e.team == me.team and m.time < e.until:
                pygame.draw.circle(view, color("ult"), pt(e.pos), 4, 1)
            elif e.kind in ("smoke", "zone") and e.radius > 0:
                col = (160, 170, 190, 150) if e.kind == "smoke" else (255, 70, 85, 70)
                pygame.draw.circle(layer, col, pt(e.pos), max(2, e.radius * k))
            elif e.kind == "wall" and e.a is not None and e.b is not None:
                pygame.draw.line(layer, (160, 170, 190, 200), pt(e.a), pt(e.b), 3)
        for orb in m.orbs:
            x, y = pt(orb)
            pygame.draw.polygon(contacts, color("ult"), [(x, y - 4), (x + 3, y), (x, y + 4), (x - 3, y)])
        if m.spike_pos is not None:
            self._mini_icon(contacts, pt(m.spike_pos), "spike", "enemy", 12)
        contacts.blit(sight, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        view.blit(contacts, (0, 0))
        noise_life = float(HUD["sound_circle_seconds"])
        self.ui.noise = [(rad, t0) for rad, t0 in getattr(self.ui, "noise", []) if m.time - t0 < noise_life]
        if self.ui.noise:
            rad, t0 = max(self.ui.noise, key=lambda n: n[0])
            fade = 1.0 - (m.time - t0) / noise_life
            pygame.draw.circle(view, (236, 232, 225, int(170 * fade)), (r, r), max(2, rad * k), 1)
        for site in wm.sites:
            x, y = pt(site.rect.center)
            lbl = self.kit.font("s", bold=True).render(site.name, True, color("gold"))
            view.blit(lbl, (x - lbl.get_width() / 2, y - lbl.get_height() / 2))
        for p in m.players.values():
            if p.pid == me.pid or me.status.get("waylay_refract_transit", 0) > m.time:
                continue
            heading = p.facing - (me.facing if rotate else 0)
            if p.team == me.team:
                self._mini_icon(view, pt(p.pos), "ally" if p.alive else "eliminated", "ally" if p.alive else "muted",
                                12, heading if p.alive else None)
            elif p.alive and self.minimap_sees_enemy(me, p):
                self.ui.last_seen[p.pid] = (p.pos, m.time)
                self._mini_icon(view, pt(p.pos), "enemy", "enemy", 12, heading)
            elif p.alive and p.pid in self.ui.last_seen and m.time - self.ui.last_seen[p.pid][1] < 5.0:
                x, y = pt(self.ui.last_seen[p.pid][0])  # last known position: a faded question mark
                mark = self.kit.font("xs", bold=True).render("?", False, color("enemy"))
                mark.set_alpha(int(220 * (1 - (m.time - self.ui.last_seen[p.pid][1]) / 5.0)))
                view.blit(mark, (x - mark.get_width() / 2, y - mark.get_height() / 2))
        self._mini_icon(view, (r, r), "self", "text", 17, 0.0 if rotate else me.facing)
        mask = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (r, r), r)
        view.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        s.blit(view, (cx - r, cy - r))
        if not self.kit.sprite("minimap/frame", pygame.Rect(cx - r, cy - r, 2 * r, 2 * r)):
            pygame.draw.circle(s, color("line"), (cx, cy), r, 1)
        if not rotate:
            self.kit.text("N", (cx, cy - r + 4), "xs", "muted", "center", bold=True)

    def minimap_sees_enemy(self, me: PlayerState, enemy: PlayerState) -> bool:
        if not me.alive or me.blind_until > self.match.time or not self.sees_enemy(me, enemy):
            return False
        return self.in_view(self.player_screen(enemy, me), me)

    def _mini_icon(self, surf: pygame.Surface, at: tuple[float, float], key: str, fallback: str,
                   size: int, angle: float | None = None) -> None:
        icon = self.bank.scaled(f"ui/minimap/{key}.png", (size, size))
        if angle is not None and key != "self":
            radians = math.radians(angle)
            x, y = at
            pygame.draw.line(surf, color(fallback), at, (x + 8 * math.sin(radians), y - 8 * math.cos(radians)), 2)
        if icon is not None:
            if angle and key == "self":
                icon = pygame.transform.rotate(icon, -angle)
            surf.blit(icon, icon.get_rect(center=at))
        else:
            pygame.draw.circle(surf, color(fallback), at, size // 3)
