"""Navigation grid and A* path search for bots.

The map is rasterised into CELL-sized squares; a cell is blocked if a wall or crate overlaps it, inflated by
the player radius. Platform sides are not walls here: every cell keeps its ground height, and a step between
cells may go up at most STEP_UP (ramps, stairs) but down any distance (dropping off a ledge). Paths are smoothed
by skipping waypoints that can be reached in a straight line under the same rule.
"""
from __future__ import annotations

import heapq
import math

from gameplay.geometry import Vec
from gameplay.world import PLATFORM, WorldMap

CELL = 0.5
RADIUS = 0.45
STEP_UP = 0.3  # levels a bot may rise between neighbouring cells (walking up a ramp)


class NavGrid:
    def __init__(self, world: WorldMap) -> None:
        self.world = world
        self.cols = max(1, int(math.ceil(world.width / CELL)))
        self.rows = max(1, int(math.ceil(world.height / CELL)))
        self.blocked = [[False] * self.cols for _ in range(self.rows)]
        for w in world.walls:
            if w.height <= 0 or w.buy_phase_only or not w.solid or w.material == PLATFORM:
                continue  # spawn barriers open after the buy phase; closed doors count as walls for bots
            x0 = max(0, int((w.rect.x0 - RADIUS) / CELL))
            x1 = min(self.cols - 1, int((w.rect.x1 + RADIUS) / CELL))
            y0 = max(0, int((w.rect.y0 - RADIUS) / CELL))
            y1 = min(self.rows - 1, int((w.rect.y1 + RADIUS) / CELL))
            for r in range(y0, y1 + 1):
                row = self.blocked[r]
                for c in range(x0, x1 + 1):
                    cx, cy = (c + 0.5) * CELL, (r + 0.5) * CELL
                    if w.rect.x0 - RADIUS < cx < w.rect.x1 + RADIUS and w.rect.y0 - RADIUS < cy < w.rect.y1 + RADIUS:
                        row[c] = True

        self.ground = self._ground_grid(world)

    def _ground_grid(self, world: WorldMap) -> list[list[float]]:
        """Ground height per cell, sampled at cell centres from the parts that raise the floor."""
        grid = [[0.0] * self.cols for _ in range(self.rows)]
        raised = [pl.rect for pl in world.platforms] + [w.rect for w in world.walls if not w.full and w.solid]
        raised += [r for r in world.ramps]
        for rect in raised:
            c0, c1 = max(0, int(rect.x0 / CELL)), min(self.cols - 1, int(rect.x1 / CELL))
            r0, r1 = max(0, int(rect.y0 / CELL)), min(self.rows - 1, int(rect.y1 / CELL))
            for r in range(r0, r1 + 1):
                for c in range(c0, c1 + 1):
                    centre = self.center((c, r))
                    if rect.contains(centre):
                        grid[r][c] = world.ground_height(centre)
        return grid

    def can_step(self, a: tuple[int, int], b: tuple[int, int]) -> bool:
        """Walking from cell a into cell b does not climb more than a ramp step."""
        return self.ground[b[1]][b[0]] <= self.ground[a[1]][a[0]] + STEP_UP

    def cell(self, p: Vec) -> tuple[int, int]:
        return (min(self.cols - 1, max(0, int(p.x / CELL))), min(self.rows - 1, max(0, int(p.y / CELL))))

    def center(self, c: tuple[int, int]) -> Vec:
        return Vec((c[0] + 0.5) * CELL, (c[1] + 0.5) * CELL)

    def free(self, c: tuple[int, int]) -> bool:
        return 0 <= c[0] < self.cols and 0 <= c[1] < self.rows and not self.blocked[c[1]][c[0]]

    def nearest_free(self, c: tuple[int, int]) -> tuple[int, int]:
        if self.free(c):
            return c
        for radius in range(1, 12):
            for dx in range(-radius, radius + 1):
                for dy in (-radius, radius):
                    for cand in ((c[0] + dx, c[1] + dy), (c[0] + dy, c[1] + dx)):
                        if self.free(cand):
                            return cand
        return c

    def line_free(self, a: Vec, b: Vec) -> bool:
        steps = max(1, int((b - a).length() / (CELL * 0.5)))
        prev = self.cell(a)
        for i in range(steps + 1):
            c = self.cell(a + (b - a) * (i / steps))
            if not self.free(c) or (c != prev and not self.can_step(prev, c)):
                return False
            prev = c
        return True

    def path(self, start: Vec, goal: Vec, limit: int = 0) -> list[Vec]:
        """Waypoints from start to goal (excluding start); empty if unreachable. limit: expanded cells (0 = all)."""
        limit = limit or self.cols * self.rows
        s, g = self.nearest_free(self.cell(start)), self.nearest_free(self.cell(goal))
        if s == g:
            return [goal]
        open_heap: list[tuple[float, int, tuple[int, int]]] = [(0.0, 0, s)]
        came: dict[tuple[int, int], tuple[int, int]] = {}
        cost = {s: 0.0}
        counter = 0
        while open_heap and counter < limit:
            _, _, cur = heapq.heappop(open_heap)
            if cur == g:
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nxt = (cur[0] + dx, cur[1] + dy)
                if not self.free(nxt) or not self.can_step(cur, nxt):
                    continue
                if dx and dy and not (self.free((cur[0] + dx, cur[1])) and self.free((cur[0], cur[1] + dy))):
                    continue  # no corner cutting
                step = 1.4142 if dx and dy else 1.0
                new = cost[cur] + step
                if new < cost.get(nxt, 1e18):
                    cost[nxt] = new
                    came[nxt] = cur
                    counter += 1
                    h = math.hypot(nxt[0] - g[0], nxt[1] - g[1])
                    heapq.heappush(open_heap, (new + h, counter, nxt))
        if g not in came:
            return []
        cells = [g]
        while cells[-1] != s:
            cells.append(came[cells[-1]])
        cells.reverse()
        points = [self.center(c) for c in cells[1:]] + [goal]
        # smoothing: keep a waypoint only if the next ones are not directly reachable
        out: list[Vec] = []
        anchor = start
        i = 0
        while i < len(points):
            j = len(points) - 1
            while j > i and not self.line_free(anchor, points[j]):
                j -= 1
            out.append(points[j])
            anchor = points[j]
            i = j + 1
        return out


_GRIDS: dict[int, NavGrid] = {}


def grid_for(world: WorldMap) -> NavGrid:
    """Grid for this map object (built once per map instance)."""
    grid = _GRIDS.get(id(world))
    if grid is None or grid.world is not world:
        grid = _GRIDS[id(world)] = NavGrid(world)
    return grid
