"""Navigation grid and A* path search for bots.

The map is rasterised into CELL-sized squares; a cell is blocked if a wall or crate overlaps it, inflated by
the player radius. Platform sides are not walls here: every cell keeps its ground height, and a step between
cells may go up at most STEP_UP (ramps, stairs) but down any distance (dropping off a ledge). Paths are smoothed
by skipping waypoints that can be reached in a straight line under the same rule.
"""
from __future__ import annotations

import heapq
import math

from gameplay.geometry import Rect, Vec
from gameplay.world import PLATFORM, Wall, WorldMap

CELL = 0.5
RADIUS = 0.45
STEP_UP = 0.3  # levels a bot may rise between neighbouring cells (walking up a ramp)


class NavGrid:
    def __init__(self, world: WorldMap, inactive: frozenset[Rect] = frozenset(), extra: tuple[Wall, ...] = ()) -> None:
        self.world = world
        self.cols = max(1, int(math.ceil(world.width / CELL)))
        self.rows = max(1, int(math.ceil(world.height / CELL)))
        self.blocked = [[False] * self.cols for _ in range(self.rows)]
        self.lower: dict[tuple[int, int], float] = {}
        self.deck_height: dict[tuple[int, int], float] = {}
        self.lower_blocked: set[tuple[int, int]] = set()
        if world.decks:
            for r in range(self.rows):
                for c in range(self.cols):
                    deck = world.deck_at(self.center((c, r)))
                    if deck is not None:
                        self.lower[c, r] = deck.lower
                        self.deck_height[c, r] = deck.level
        for w in (*world.walls, *extra):
            if w.rect in inactive or w.height <= 0 or w.buy_phase_only or not w.solid or w.material == PLATFORM:
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
                        if not w.on_deck and (c, r) in self.lower:
                            self.lower_blocked.add((c, r))

        self.ground = self._ground_grid(world)

    def _ground_grid(self, world: WorldMap) -> list[list[float]]:
        """Ground height per cell, sampled at cell centres from the parts that raise the floor."""
        grid = [[0.0] * self.cols for _ in range(self.rows)]
        raised = [pl.rect for pl in world.platforms] + [w.rect for w in world.walls if not w.full and w.solid]
        raised += [r for r in world.ramps]
        raised += [deck.rect for deck in world.decks]
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
        return self.height_at(b) <= self.height_at(a) + STEP_UP

    def height_at(self, c: tuple[int, int]) -> float:
        x, y = c
        return self.lower[x, y - self.rows] if y >= self.rows else self.ground[y][x]

    def cell(self, p: Vec, reach: float = float("inf")) -> tuple[int, int]:
        c = min(self.cols - 1, max(0, int(p.x / CELL))), min(self.rows - 1, max(0, int(p.y / CELL)))
        return self.layer_at(c, reach)

    def layer_at(self, c: tuple[int, int], reach: float) -> tuple[int, int]:
        if reach < self.deck_height.get(c, float("-inf")):
            return c[0], c[1] + self.rows
        return c

    def center(self, c: tuple[int, int]) -> Vec:
        return Vec((c[0] + 0.5) * CELL, (c[1] % self.rows + 0.5) * CELL)

    def free(self, c: tuple[int, int]) -> bool:
        if c[1] >= self.rows:
            lower = c[0], c[1] - self.rows
            return lower in self.lower and lower not in self.lower_blocked
        return 0 <= c[0] < self.cols and 0 <= c[1] < self.rows and not self.blocked[c[1]][c[0]]

    def nearest_free(self, c: tuple[int, int]) -> tuple[int, int]:
        if self.free(c):
            return c
        origin = c[0], c[1] % self.rows
        reach = self.height_at(c) if c[1] >= self.rows else float("inf")
        for radius in range(1, 12):
            for dx in range(-radius, radius + 1):
                for dy in (-radius, radius):
                    for x, y in ((origin[0] + dx, origin[1] + dy), (origin[0] + dy, origin[1] + dx)):
                        if not (0 <= x < self.cols and 0 <= y < self.rows):
                            continue
                        cand = self.layer_at((x, y), reach)
                        if self.free(cand):
                            return cand
        return c

    def line_free(self, a: Vec, b: Vec, start_ground: float = float("inf"),
                  goal_ground: float = float("inf")) -> bool:
        steps = max(1, int((b - a).length() / (CELL * 0.5)))
        prev = self.cell(a, start_ground)
        for i in range(steps + 1):
            c = self.cell(a + (b - a) * (i / steps), self.height_at(prev) + STEP_UP)
            if not self.free(c) or (c != prev and not self.can_step(prev, c)):
                return False
            prev = c
        return prev == self.cell(b, goal_ground)

    def path(self, start: Vec, goal: Vec, limit: int = 0, *,
             start_ground: float = float("inf"), goal_ground: float = float("inf")) -> list[Vec]:
        """Waypoints from start to goal (excluding start); empty if unreachable. limit: expanded cells (0 = all)."""
        limit = limit or self.cols * self.rows + len(self.lower)
        s, g = self.nearest_free(self.cell(start, start_ground)), self.nearest_free(self.cell(goal, goal_ground))
        if s == g:
            return [goal]
        open_heap: list[tuple[float, int, tuple[int, int], float]] = [(0.0, 0, s, 0.0)]
        came: dict[tuple[int, int], tuple[int, int]] = {}
        cost = {s: 0.0}
        counter = 0
        gx, gy = g[0], g[1] % self.rows
        while open_heap and counter < limit:
            _, _, cur, paid = heapq.heappop(open_heap)
            if paid != cost[cur]:
                continue
            if cur == g:
                break
            x, y = cur[0], cur[1] % self.rows
            reach = self.height_at(cur) + STEP_UP
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < self.cols and 0 <= ny < self.rows):
                    continue
                nxt = self.layer_at((nx, ny), reach) if self.lower else (nx, ny)
                if not self.free(nxt) or self.height_at(nxt) > reach:
                    continue
                if dx and dy and not (self.free(self.layer_at((nx, y), reach))
                                      and self.free(self.layer_at((x, ny), reach))):
                    continue  # no corner cutting
                step = 1.4142 if dx and dy else 1.0
                new = cost[cur] + step
                if new < cost.get(nxt, 1e18):
                    cost[nxt] = new
                    came[nxt] = cur
                    counter += 1
                    hx, hy = abs(nx - gx), abs(ny - gy)
                    h = max(hx, hy) + 0.4142 * min(hx, hy)
                    heapq.heappush(open_heap, (new + h, counter, nxt, new))
        if g not in came:
            return []
        cells = [g]
        while cells[-1] != s:
            cells.append(came[cells[-1]])
        cells.reverse()
        points = [self.center(c) for c in cells[1:]] + [goal]
        levels = [self.height_at(c) for c in cells[1:]] + [goal_ground]
        # smoothing: keep a waypoint only if the next ones are not directly reachable
        out: list[Vec] = []
        anchor = start
        anchor_ground = start_ground
        i = 0
        while i < len(points):
            j = len(points) - 1
            while j > i and not self.line_free(anchor, points[j], anchor_ground, levels[j]):
                j -= 1
            out.append(points[j])
            anchor = points[j]
            anchor_ground = levels[j]
            i = j + 1
        return out


_GRIDS: dict[int, tuple[frozenset[Rect], tuple[Wall, ...], NavGrid]] = {}


def grid_for(world: WorldMap, inactive: frozenset[Rect] = frozenset(), extra: tuple[Wall, ...] = ()) -> NavGrid:
    """Cache the grid for the current door and breakable-cover state."""
    cached = _GRIDS.get(id(world))
    if cached is None or cached[0] != inactive or cached[1] != extra:
        cached = _GRIDS[id(world)] = (inactive, extra, NavGrid(world, inactive, extra))
    return cached[2]
