"""Crosshair drawing shared by the game and the settings preview, on whole pixels so all four arms are exactly
symmetric: a centre block of `thickness` pixels, arms of `length` pixels at `gap` pixels from the block."""
from __future__ import annotations

import pygame

DEFAULT_LENGTH = 7     # arm length at size 1.0, pixels
DEFAULT_THICKNESS = 2  # arm and dot thickness, pixels


def shape(center: tuple[float, float], size: float, gap: float, dot: bool,
          thickness: int = DEFAULT_THICKNESS) -> list[pygame.Rect]:
    """Rectangles of the crosshair. Every value is rounded once, so left/right and up/down mirror each other."""
    t = max(1, int(thickness))
    length = max(1, round(DEFAULT_LENGTH * size))
    g = max(0, round(gap))
    x0 = round(center[0]) - t // 2  # top-left of the centre block
    y0 = round(center[1]) - t // 2
    rects = [
        pygame.Rect(x0 + t + g, y0, length, t),          # right
        pygame.Rect(x0 - g - length, y0, length, t),     # left
        pygame.Rect(x0, y0 + t + g, t, length),          # down
        pygame.Rect(x0, y0 - g - length, t, length),     # up
    ]
    if dot:
        rects.append(pygame.Rect(x0, y0, t, t))
    return rects


def draw(surface: pygame.Surface, center: tuple[float, float], color: pygame.Color | tuple, size: float, gap: float,
         dot: bool, thickness: int = DEFAULT_THICKNESS, outline: bool = True) -> None:
    """Draws the crosshair; outline adds a one-pixel dark border so it stays visible on bright floors."""
    rects = shape(center, size, gap, dot, thickness)
    if outline:
        for r in rects:
            pygame.draw.rect(surface, (8, 10, 14), r.inflate(2, 2))
    for r in rects:
        pygame.draw.rect(surface, color, r)
