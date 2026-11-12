"""UI kit for menus, overlays and HUD: theme from config/client/theme.py, text, panels, buttons, tabs, sliders,
check boxes, key caps and dialogs, all in one flat style (dark slate, red accent, upper-case labels)."""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import pygame

from gameplay.data import CONFIG_DIR, _load_py

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_THEME: dict[str, Any] = {
    "colors": {"bg": "#0f1923", "panel": "#0f1923d8", "panel_light": "#1f2d3ae6", "line": "#ece8e133", "text": "#ece8e1",
               "muted": "#8b978f", "accent": "#ff4655", "accent_dark": "#bd3944", "ally": "#4fd6c8", "enemy": "#ff4655",
               "gold": "#f2c94c", "ult": "#f7f0a8", "good": "#5ee38a", "shade": "#000000b4"},
    "fonts": {"ui": "fixed_sys.ttf", "title": "fixed_sys.ttf", "numbers": "fixed_sys.ttf"},
    "pixel": True, "native": 16, "border": 2,
    "sizes": {"xs": 1, "s": 1, "m": 1, "l": 2, "xl": 3, "xxl": 4},
    "smooth_sizes": {"xs": 13, "s": 16, "m": 20, "l": 30, "xl": 46, "xxl": 72},
}


@lru_cache(maxsize=1)
def load_theme() -> dict[str, Any]:
    raw = _load_py(CONFIG_DIR / "client" / "theme.py", "THEME")
    theme = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULT_THEME.items()}
    if isinstance(raw, dict):
        for section, values in raw.items():
            if isinstance(values, dict) and isinstance(theme.get(section), dict):
                theme[section].update(values)
            elif not isinstance(values, dict):
                theme[section] = values
    return theme


def pixel_mode() -> bool:
    return bool(load_theme().get("pixel", True))


def border() -> int:
    return int(load_theme().get("border", 2))


def color(name: str) -> pygame.Color:
    value = load_theme()["colors"].get(name, name)
    try:
        return pygame.Color(value)
    except (ValueError, TypeError):
        warnings.warn(f"Theme colour {name}={value!r} unreadable; white used.")
        return pygame.Color(255, 255, 255)


@dataclass
class Hit:
    """A clickable area drawn this frame."""
    rect: pygame.Rect
    action: str
    enabled: bool = True


class Ui:
    """Draws on one surface. hits collects the clickable areas of the last frame (call begin() first)."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.hits: list[Hit] = []
        self._fonts: dict[tuple[str, int, bool], pygame.font.Font] = {}
        self.pressed: str | None = None
        self.modal_from = 0  # hits before this index lie under a dialog and are not clickable

    # ------------------------------------------------------------ basics
    def begin(self) -> None:
        self.hits = []
        self.modal_from = 0

    def _px(self, size: str) -> tuple[int, int]:
        """(font pixel size, whole-number enlargement) of a size name."""
        th = load_theme()
        if pixel_mode():
            return int(th.get("native", 16)), max(1, int(th["sizes"].get(size, 1)))
        return int(th.get("smooth_sizes", th["sizes"]).get(size, 20)), 1

    def font(self, size: str = "m", kind: str = "ui", bold: bool = False) -> pygame.font.Font:
        px = self._px(size)[0] if isinstance(size, str) else int(size)
        bold = bold and not pixel_mode()  # pixel fonts get bold by a doubled stroke instead
        key = (kind, px, bold)
        if key not in self._fonts:
            name = str(load_theme()["fonts"].get(kind, ""))
            try:
                f = pygame.font.Font(str(ROOT / "font" / name) if name else None, px)
            except (OSError, FileNotFoundError):
                warnings.warn(f"Font {name} missing; built-in font used.")
                f = pygame.font.Font(None, px)
            f.set_bold(bold)
            self._fonts[key] = f
        return self._fonts[key]

    def text(self, msg: str, pos: tuple[float, float], size: str = "m", col: str | tuple = "text", align: str = "left",
             upper: bool = False, bold: bool = False, kind: str = "ui", alpha: int = 255) -> pygame.Rect:
        c = color(col) if isinstance(col, str) else pygame.Color(*col)
        img = self.render(msg.upper() if upper else msg, size, c, bold, kind)
        if alpha < 255:
            img.set_alpha(alpha)
        x, y = pos
        if align == "center":
            x -= img.get_width() / 2
        elif align == "right":
            x -= img.get_width()
        self.screen.blit(img, (x, y))
        return pygame.Rect(round(x), round(y), img.get_width(), img.get_height())

    def render(self, msg: str, size: str, c: pygame.Color, bold: bool = False, kind: str = "ui") -> pygame.Surface:
        """Text surface. Pixel look: native size, no smoothing, bold as a 1-pixel doubled stroke, then enlarged by a
        whole number with nearest-neighbour scaling, so every text pixel is a block like in the sprites."""
        f = self.font(size, kind, bold)
        if not pixel_mode():
            return f.render(msg, True, c)
        base = f.render(msg, False, c)
        if bold:
            wide = pygame.Surface((base.get_width() + 1, base.get_height()), pygame.SRCALPHA)
            wide.blit(base, (0, 0))
            wide.blit(base, (1, 0))
            base = wide
        k = self._px(size)[1]
        return base if k == 1 else pygame.transform.scale(base, (base.get_width() * k, base.get_height() * k))

    def size(self, msg: str, size: str = "m", upper: bool = False, bold: bool = False, kind: str = "ui") -> tuple[int, int]:
        w, h = self.font(size, kind, bold).size(msg.upper() if upper else msg)
        k = self._px(size)[1] if pixel_mode() else 1
        return (w + (1 if bold and pixel_mode() else 0)) * k, h * k

    def fill(self, rect: pygame.Rect, col: str) -> None:
        c = color(col)
        if c.a < 255:
            layer = pygame.Surface(rect.size, pygame.SRCALPHA)
            layer.fill(c)
            self.screen.blit(layer, rect.topleft)
        else:
            pygame.draw.rect(self.screen, c, rect)

    def line(self, a: tuple[float, float], b: tuple[float, float], col: str = "line", width: int = 1) -> None:
        c = color(col)
        if c.a < 255:
            x0, y0 = min(a[0], b[0]), min(a[1], b[1])
            w, h = abs(b[0] - a[0]) + width, abs(b[1] - a[1]) + width
            layer = pygame.Surface((max(1, int(w)), max(1, int(h))), pygame.SRCALPHA)
            pygame.draw.line(layer, c, (a[0] - x0, a[1] - y0), (b[0] - x0, b[1] - y0), width)
            self.screen.blit(layer, (x0, y0))
        else:
            pygame.draw.line(self.screen, c, a, b, width)

    def outline(self, rect: pygame.Rect, col: str = "line", width: int = 0) -> None:
        """Rectangle border; width 0 = the theme's border (whole UI pixels)."""
        width = width or border()
        c = color(col)
        if c.a == 255:
            pygame.draw.rect(self.screen, c, rect, width)
            return
        for a, b in ((rect.topleft, rect.topright), (rect.topright, rect.bottomright),
                     (rect.bottomright, rect.bottomleft), (rect.bottomleft, rect.topleft)):
            self.line(a, b, col, width)

    def shade(self, col: str = "shade") -> None:
        """Dims everything drawn so far; it stops being clickable (modal)."""
        self.fill(self.screen.get_rect(), col)
        self.modal_from = len(self.hits)

    # ------------------------------------------------------------ widgets
    def panel(self, rect: pygame.Rect, col: str = "panel", edge: str = "", edge_col: str = "accent") -> None:
        """Translucent panel; edge "left"/"top"/"bottom" adds an accent bar two UI pixels thick."""
        self.fill(rect, col)
        thick = 2 * border()
        if edge == "left":
            pygame.draw.rect(self.screen, color(edge_col), (rect.x, rect.y, thick, rect.h))
        elif edge == "top":
            pygame.draw.rect(self.screen, color(edge_col), (rect.x, rect.y, rect.w, thick))
        elif edge == "bottom":
            pygame.draw.rect(self.screen, color(edge_col), (rect.x, rect.bottom - thick, rect.w, thick))

    def button(self, rect: pygame.Rect, label: str, action: str, primary: bool = False, enabled: bool = True,
               size: str = "m", selected: bool = False) -> None:
        """Primary: filled red. Secondary: outline that fills on hover. Label upper-case and centred."""
        hover = enabled and rect.collidepoint(pygame.mouse.get_pos())
        down = hover and self.pressed == action
        if primary:
            base = "panel_light" if not enabled else "accent_dark" if down else "accent"
            pygame.draw.rect(self.screen, color(base), rect)
            if hover and not down:
                pygame.draw.rect(self.screen, color("text"), rect.inflate(6, 6), 1)
            text_col = "text"
        else:
            if selected or hover:
                self.fill(rect, "panel_light" if not selected else "accent")
            else:
                self.fill(rect, "panel")
            self.outline(rect, "text" if hover else "line")
            text_col = "text" if enabled else "muted"
        if not enabled:
            text_col = "muted"
        w, h = self.size(label, size, upper=True, bold=primary)
        self.text(label, (rect.centerx, rect.centery - h / 2), size, text_col, "center", upper=True, bold=primary)
        self.hits.append(Hit(rect, action, enabled))

    def tab(self, rect: pygame.Rect, label: str, action: str, active: bool) -> None:
        hover = rect.collidepoint(pygame.mouse.get_pos())
        col = "text" if active or hover else "muted"
        w, h = self.size(label, "m", upper=True, bold=active)
        self.text(label, (rect.centerx, rect.centery - h / 2), "m", col, "center", upper=True, bold=active)
        if active:
            pygame.draw.rect(self.screen, color("accent"), (rect.centerx - w / 2, rect.bottom - 3, w, 3))
        self.hits.append(Hit(rect, action))

    def slider(self, rect: pygame.Rect, frac: float, action: str) -> None:
        frac = max(0.0, min(1.0, frac))
        mid = rect.centery
        b = border()
        self.fill(pygame.Rect(rect.x, mid - b // 2, rect.w, b), "line")
        pygame.draw.rect(self.screen, color("accent"), (rect.x, mid - b // 2, round(rect.w * frac), b))
        knob = pygame.Rect(0, 0, 4 * border(), 8 * border())
        knob.center = (round(rect.x + rect.w * frac), mid)
        pygame.draw.rect(self.screen, color("text"), knob)
        self.hits.append(Hit(rect.inflate(0, 14), action))

    def checkbox(self, rect: pygame.Rect, on: bool, action: str) -> None:
        self.outline(rect, "text" if rect.collidepoint(pygame.mouse.get_pos()) else "line")
        if on:
            pygame.draw.rect(self.screen, color("accent"), rect.inflate(-8, -8))
        self.hits.append(Hit(rect, action))

    def keycap(self, pos: tuple[float, float], key: str, size: str = "xs") -> pygame.Rect:
        """A small key label like [Q] for HUD hints."""
        w, h = self.size(key, size, upper=True, bold=True)
        r = pygame.Rect(round(pos[0]), round(pos[1]), max(h + 6, w + 10), h + 4)
        self.fill(r, "panel_light")
        self.outline(r, "line")
        self.text(key, (r.centerx, r.y + 2), size, "text", "center", upper=True, bold=True)
        return r

    def dialog(self, title: str, body: str, buttons: list[tuple[str, str, bool]], width: int = 520) -> pygame.Rect:
        """Centred dialog over a dimmed screen. buttons: (label, action, primary)."""
        self.shade()
        sw, sh = self.screen.get_size()
        lines = self.wrap(body, "s", width - 64) if body else []
        height = 120 + len(lines) * 22 + 56
        rect = pygame.Rect(0, 0, width, height)
        rect.center = (sw // 2, sh // 2)
        self.panel(rect, "bg", edge="top")
        self.outline(rect, "line")
        self.text(title, (rect.centerx, rect.y + 28), "l", "text", "center", upper=True, bold=True, kind="title")
        for i, ln in enumerate(lines):
            self.text(ln, (rect.centerx, rect.y + 78 + i * 22), "s", "muted", "center")
        bw = (width - 64 - 16 * (len(buttons) - 1)) // max(1, len(buttons))
        for i, (label, action, primary) in enumerate(buttons):
            self.button(pygame.Rect(rect.x + 32 + i * (bw + 16), rect.bottom - 64, bw, 40), label, action, primary)
        return rect

    def wrap(self, text: str, size: str, width: int) -> list[str]:
        out: list[str] = []
        for para in text.split("\n"):
            line = ""
            for word in para.split():
                trial = f"{line} {word}".strip()
                if self.size(trial, size)[0] > width and line:
                    out.append(line)
                    line = word
                else:
                    line = trial
            out.append(line)
        return out

    # ------------------------------------------------------------ input
    def area(self, rect: pygame.Rect, action: str, enabled: bool = True) -> None:
        """Makes a drawn area clickable."""
        self.hits.append(Hit(rect, action, enabled))

    def hit_at(self, pos: tuple[int, int]) -> Hit | None:
        for h in reversed(self.hits[self.modal_from:]):  # topmost first
            if h.enabled and h.rect.collidepoint(pos):
                return h
        return None
