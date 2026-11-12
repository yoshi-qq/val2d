"""Minimap."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)


class MinimapMixin:
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
