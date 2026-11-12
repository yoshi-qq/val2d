"""Round minimap in the top-left corner: centred on the player, turning with the view (or north up), walls, sites,
team, seen enemies, bomb, smokes, the field of view and the own noise circle (how far your footsteps and shots are
heard, like the sound circle of a real tactical shooter). Values: config/client/hud.py."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)
from client.ui import color


class MinimapMixin:
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
        pygame.draw.rect(panel, (36, 46, 56, 255), floor)
        for site in wm.sites:
            x0, y0 = pad + site.rect.x0 * k, pad + (wm.height - site.rect.y1) * k
            pygame.draw.rect(panel, (70, 62, 40, 255), (x0, y0, (site.rect.x1 - site.rect.x0) * k, (site.rect.y1 - site.rect.y0) * k))
        for w in wm.walls:
            if w.rect.x0 < -0.5 or w.rect.y0 < -0.5 or w.rect.x1 > wm.width + 0.5 or w.rect.y1 > wm.height + 0.5:
                continue
            x0, y0 = pad + w.rect.x0 * k, pad + (wm.height - w.rect.y1) * k
            rect = pygame.Rect(round(x0), round(y0), max(1, round((w.rect.x1 - w.rect.x0) * k)), max(1, round((w.rect.y1 - w.rect.y0) * k)))
            pygame.draw.rect(panel, (150, 160, 168, 255) if w.height > 1 else (84, 104, 116, 255), rect)
        return panel

    def draw_minimap(self, me: PlayerState) -> None:
        m, wm, s = self.match, self.match.world, self.screen
        r = int(HUD["minimap_radius"])
        k = self.minimap_scale()
        rotate = bool(HUD["minimap_rotate"])
        cx, cy = 20 + r, 20 + r
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

        # field of view and own noise circle
        fov = 360.0 if m.cfg.lobby.all_around_sight else m.fov
        if fov < 359:
            cone = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
            reach = r * 1.5
            pts = [(r, r)]
            for i in range(13):
                a = math.radians(me.facing - fov / 2 + fov * i / 12)
                rel = Vec(math.sin(a), math.cos(a))
                if rotate:
                    rel = rel.rotated(-me.facing)
                pts.append((r + rel.x * reach, r - rel.y * reach))
            pygame.draw.polygon(cone, (236, 232, 225, 26), pts)
            view.blit(cone, (0, 0))
        for e in m.effects:
            if e.kind in ("smoke", "zone") and e.radius > 0:
                col = (160, 170, 190, 150) if e.kind == "smoke" else (255, 70, 85, 70)
                pygame.draw.circle(view, col, pt(e.pos), max(2, e.radius * k))
            elif e.kind == "wall" and e.a is not None and e.b is not None:
                pygame.draw.line(view, (160, 170, 190, 200), pt(e.a), pt(e.b), 3)
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
        if m.spike_pos is not None:
            x, y = pt(m.spike_pos)
            pygame.draw.rect(view, color("enemy"), (x - 4, y - 4, 8, 8))
        for p in m.players.values():
            if p.pid == me.pid:
                continue
            if p.team == me.team:
                self._mini_dot(view, pt(p.pos), color("ally") if p.alive else color("muted"), p.facing - (me.facing if rotate else 0), p.alive)
            elif p.alive and (p.visible if self.mode == "client" else m.can_see(me, p)):
                self._mini_dot(view, pt(p.pos), color("enemy"), p.facing - (me.facing if rotate else 0), True)
        self._mini_dot(view, (r, r), color("text"), 0.0 if rotate else me.facing, True, big=True)
        mask = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (r, r), r)
        view.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        s.blit(view, (cx - r, cy - r))
        pygame.draw.circle(s, color("line"), (cx, cy), r, 1)
        if not rotate:
            self.kit.text("N", (cx, cy - r + 4), "xs", "muted", "center", bold=True)

    def _mini_dot(self, surf: pygame.Surface, at: tuple[float, float], col: pygame.Color, angle: float, alive: bool,
                  big: bool = False) -> None:
        x, y = at
        size = 6 if big else 4
        if not alive:
            pygame.draw.line(surf, col, (x - 3, y - 3), (x + 3, y + 3), 2)
            pygame.draw.line(surf, col, (x - 3, y + 3), (x + 3, y - 3), 2)
            return
        a = math.radians(angle)
        tip = (x + math.sin(a) * (size + 4), y - math.cos(a) * (size + 4))
        left = (x + math.sin(a - 2.5) * size, y - math.cos(a - 2.5) * size)
        right = (x + math.sin(a + 2.5) * size, y - math.cos(a + 2.5) * size)
        pygame.draw.polygon(surf, col, [tip, left, right])
        pygame.draw.circle(surf, col, (x, y), size - 1)
