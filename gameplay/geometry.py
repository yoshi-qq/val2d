"""2D-Geometrie in Metern. Winkel in Grad, 0° = Norden (+y), im Uhrzeigersinn."""
from __future__ import annotations

import math
from dataclasses import dataclass

MAX_DRONE_PITCH = 60.0


@dataclass(frozen=True)
class Vec:
    x: float
    y: float

    def __add__(self, o: "Vec") -> "Vec":
        return Vec(self.x + o.x, self.y + o.y)

    def __sub__(self, o: "Vec") -> "Vec":
        return Vec(self.x - o.x, self.y - o.y)

    def __mul__(self, f: float) -> "Vec":
        return Vec(self.x * f, self.y * f)

    def dot(self, o: "Vec") -> float:
        return self.x * o.x + self.y * o.y

    def cross(self, o: "Vec") -> float:
        return self.x * o.y - self.y * o.x

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def normalized(self) -> "Vec":
        n = self.length()
        return Vec(0.0, 0.0) if n == 0 else Vec(self.x / n, self.y / n)

    def rotated(self, degrees: float) -> "Vec":
        """Dreht im Uhrzeigersinn (Kompass-Sinn)."""
        r = math.radians(degrees)
        c, s = math.cos(r), math.sin(r)
        return Vec(self.x * c + self.y * s, -self.x * s + self.y * c)


def heading(degrees: float) -> Vec:
    """Unit vector for a compass angle (0° = +y, 90° = +x)."""
    r = math.radians(degrees)
    return Vec(math.sin(r), math.cos(r))


def projectile_progress(now: float, start: float, until: float, *, lands_at_expiry: bool = False) -> float:
    """Progress along the visible flight, which lands shortly before the effect expires."""
    duration = until - start
    flight = duration if lands_at_expiry else min(0.6, duration * 0.8)
    return (now - start) / max(flight, 1e-6)


def angle_of(v: Vec) -> float:
    return math.degrees(math.atan2(v.x, v.y)) % 360.0


def angle_diff(a: float, b: float) -> float:
    """Kleinster vorzeichenbehafteter Unterschied b - a in Grad (-180, 180]."""
    d = (b - a + 180.0) % 360.0 - 180.0
    return 180.0 if d == -180.0 else d


@dataclass(frozen=True)
class Rect:
    """Achsenparalleles Rechteck: x0 < x1, y0 < y1."""
    x0: float
    y0: float
    x1: float
    y1: float

    def contains(self, p: Vec) -> bool:
        return self.x0 <= p.x <= self.x1 and self.y0 <= p.y <= self.y1

    @property
    def center(self) -> Vec:
        return Vec((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)

    def ray_interval(self, origin: Vec, direction: Vec) -> tuple[float, float] | None:
        """Entry and exit distance of a ray (slab method), None if it misses."""
        t_min, t_max = -math.inf, math.inf
        for o, d, lo, hi in ((origin.x, direction.x, self.x0, self.x1), (origin.y, direction.y, self.y0, self.y1)):
            if abs(d) < 1e-12:
                if o < lo or o > hi:
                    return None
                continue
            t1, t2 = (lo - o) / d, (hi - o) / d
            if t1 > t2:
                t1, t2 = t2, t1
            t_min, t_max = max(t_min, t1), min(t_max, t2)
            if t_min > t_max:
                return None
        if t_max < 0:
            return None
        return max(t_min, 0.0), t_max

    def circle_push(self, p: Vec, radius: float) -> Vec | None:
        """Offset that pushes a circle out of the rectangle, None without overlap."""
        cx = min(max(p.x, self.x0), self.x1)
        cy = min(max(p.y, self.y0), self.y1)
        dx, dy = p.x - cx, p.y - cy
        dist2 = dx * dx + dy * dy
        if dist2 >= radius * radius:
            return None
        if dist2 > 1e-12:
            dist = math.sqrt(dist2)
            return Vec(dx / dist * (radius - dist), dy / dist * (radius - dist))
        # centre inside the rectangle: shortest way out
        options = [
            Vec(self.x0 - radius - p.x, 0.0), Vec(self.x1 + radius - p.x, 0.0),
            Vec(0.0, self.y0 - radius - p.y), Vec(0.0, self.y1 + radius - p.y),
        ]
        return min(options, key=lambda v: v.length())


def segment_circle_hit(a: Vec, b: Vec, center: Vec, radius: float) -> bool:
    ab = b - a
    t = 0.0 if ab.dot(ab) == 0 else max(0.0, min(1.0, (center - a).dot(ab) / ab.dot(ab)))
    closest = a + ab * t
    return (center - closest).length() <= radius


def segments_intersect(a: Vec, b: Vec, c: Vec, d: Vec) -> bool:
    def orient(p: Vec, q: Vec, r: Vec) -> float:
        return (q - p).cross(r - p)
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    return (o1 * o2 < 0) and (o3 * o4 < 0)
