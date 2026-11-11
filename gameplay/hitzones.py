"""Trefferzonen in 2D nach docs/VISION.md, Abschnitt „Trefferzonen in 2D“.

Querabstand zur tatsächlichen Schusslinie entscheidet über die Breite der Zone,
der Tiefenabstand zwischen Cursor und Ziel entlang der Zielrichtung über die Höhe am Körper.
"""
from __future__ import annotations

from dataclasses import dataclass

from gameplay.data import HitZoneConfig
from gameplay.geometry import Vec


@dataclass(frozen=True)
class ZoneResult:
    zone: str | None  # "head", "body", "legs" oder None (verfehlt)
    lateral: float
    along: float


def resolve_zone(
    shooter: Vec,
    shot_dir: Vec,
    aim_dir: Vec,
    cursor_depth: float,
    target: Vec,
    same_level: bool,
    cursor_on_target_level: bool,
    cfg: HitZoneConfig,
) -> ZoneResult:
    """Zone eines Treffers.

    shot_dir: tatsächliche Flugrichtung (mit Streuung), aim_dir: Zielrichtung ohne Streuung,
    cursor_depth: Abstand des Cursors vor dem Schützen entlang aim_dir (Meter).
    """
    rel = target - shooter
    along = rel.dot(shot_dir)
    lateral = abs(shot_dir.cross(rel))
    if along <= 0 or not same_level or not cursor_on_target_level:
        return ZoneResult(None, lateral, along)
    if lateral > cfg.body_half_width:
        return ZoneResult(None, lateral, along)

    depth_error = abs(rel.dot(aim_dir) - cursor_depth)
    if depth_error <= cfg.head_depth_tolerance:
        wanted = "head"
    elif depth_error <= cfg.body_depth_tolerance:
        wanted = "body"
    else:
        wanted = "legs"

    if wanted == "head":
        zone = "head" if lateral <= cfg.head_half_width else "body"
    elif wanted == "body":
        zone = "body"
    else:
        zone = "legs"
    return ZoneResult(zone, lateral, along)
