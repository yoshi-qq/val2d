"""Sight area of the own player: rays across the field of view, stopped by sight-blocking walls and smokes.

Everything outside the area is drawn dark, so the screen shows what the player really sees (corners hide
what is behind them). Uses numpy: all rays against all walls at once.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from gameplay.geometry import Vec

if TYPE_CHECKING:
    from gameplay.match import Match, PlayerState


def _wall_arrays(m: Match, level: int, origin: Vec, reach: float, low: bool = False) -> np.ndarray:
    """Sight-blocking walls near the eye; low=True also head-high cover (crates, platform edges) above the eye."""
    rects = []
    walls = [w for w in m.world.walls if w.top > level and m.wall_active(w, for_sight=True)] if low \
        else m.active_sight_walls(level)
    for w in walls:
        r = w.rect
        if r.x1 < origin.x - reach or r.x0 > origin.x + reach or r.y1 < origin.y - reach or r.y0 > origin.y + reach:
            continue
        rects.append((r.x0, r.y0, r.x1, r.y1))
    return np.array(rects, dtype=float).reshape(-1, 4)


def _smokes(m: Match, origin: Vec, reach: float) -> np.ndarray:
    out = []
    for e in m.effects:
        blocks = e.props.get("blocks_sight", e.kind in ("smoke", "wall"))
        if blocks and e.a is None and e.radius > 0 and e.start <= m.time and (e.pos - origin).length() < reach + e.radius:
            out.append((e.pos.x, e.pos.y, e.radius))
    return np.array(out, dtype=float).reshape(-1, 3)


def _lines(m: Match) -> np.ndarray:
    out = []
    for e in m.effects:
        if e.a is not None and e.b is not None and e.kind != "tripwire" and e.props.get("blocks_sight", e.kind == "wall") \
                and e.start <= m.time:
            out.append((e.a.x, e.a.y, e.b.x, e.b.y))
    return np.array(out, dtype=float).reshape(-1, 4)


def sight_polygon(m: Match, me: PlayerState, fov: float, reach: float, rays: int, low: bool = False) -> list[Vec]:
    """World points of the visible area: the eye first, then the ray ends from the left to the right edge.
    low=True: head-high cover blocks too (the area where even the ground is visible)."""
    origin = me.pos
    full = fov >= 359.0
    n = max(8, int(rays * (1.0 if full else fov / 103.0)))
    start = me.facing - fov / 2
    angles = np.radians(start + np.arange(n + (0 if full else 1)) * (fov / n))
    dx, dy = np.sin(angles), np.cos(angles)  # compass: 0 = +y, 90 = +x
    dist = np.full(angles.shape, reach)
    walls = _wall_arrays(m, me.level, origin, reach, low)
    if len(walls):
        ox, oy = origin.x, origin.y
        with np.errstate(divide="ignore", invalid="ignore"):
            inv_x = 1.0 / np.where(np.abs(dx) < 1e-9, 1e-9, dx)
            inv_y = 1.0 / np.where(np.abs(dy) < 1e-9, 1e-9, dy)
            tx1 = (walls[None, :, 0] - ox) * inv_x[:, None]
            tx2 = (walls[None, :, 2] - ox) * inv_x[:, None]
            ty1 = (walls[None, :, 1] - oy) * inv_y[:, None]
            ty2 = (walls[None, :, 3] - oy) * inv_y[:, None]
        t_near = np.maximum(np.minimum(tx1, tx2), np.minimum(ty1, ty2))
        t_far = np.minimum(np.maximum(tx1, tx2), np.maximum(ty1, ty2))
        hit = (t_far >= np.maximum(t_near, 0.0)) & (t_near > 0.0)
        cand = np.where(hit, t_near, np.inf)
        dist = np.minimum(dist, cand.min(axis=1))
    smokes = _smokes(m, origin, reach)
    for cx, cy, r in smokes:
        fx, fy = origin.x - cx, origin.y - cy
        c = fx * fx + fy * fy - r * r
        b = fx * dx + fy * dy
        disc = b * b - c
        root = np.sqrt(np.maximum(disc, 0.0))
        if c <= 0:  # standing inside: sight ends at the edge of the smoke
            dist = np.minimum(dist, -b + root)
        else:
            t = -b - root
            dist = np.where((disc > 0) & (t > 0), np.minimum(dist, t), dist)
    lines = _lines(m)
    for ax, ay, bx, by in lines:
        ex, ey = bx - ax, by - ay
        denom = dx * ey - dy * ex
        with np.errstate(divide="ignore", invalid="ignore"):
            t = ((ax - origin.x) * ey - (ay - origin.y) * ex) / denom
            u = ((ax - origin.x) * dy - (ay - origin.y) * dx) / denom
        ok = (np.abs(denom) > 1e-9) & (t > 0) & (u >= 0) & (u <= 1)
        dist = np.where(ok, np.minimum(dist, t), dist)
    pts = [Vec(origin.x + float(x) * float(d), origin.y + float(y) * float(d)) for x, y, d in zip(dx, dy, dist)]
    return pts if full else [origin] + pts


def body_circle(origin: Vec, radius: float, steps: int = 20) -> list[Vec]:
    return [Vec(origin.x + math.sin(a) * radius, origin.y + math.cos(a) * radius)
            for a in (2 * math.pi * i / steps for i in range(steps))]
