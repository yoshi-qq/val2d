"""Map editor for the gameplay map format (gameplay/data/maps/*.json, materials in config/content/materials.py).

Usage:  python map_editor.py <map_key>        (new file if it does not exist)
Mouse:  left drag  draw a rect with the current tool, left click  place (objects, decals, spawn points)
        right click  delete the topmost thing under the cursor, middle drag  pan, wheel  zoom
Keys:   1 wall  2 floor  3 object  4 decal  5 crate  6 platform  7 ramp  8 site  9 spawn zone  0 spawn point  C callout
        Q / E  previous / next material, object or decal   R  rotate object/decal 90°   T  toggle team (0 attack, 1 defense)
        G  toggle grid snap (0.5 m)   Ctrl+S  save   Ctrl+Z  undo   Esc  quit
The old editor mapEditor.py edits the old map format and is left unchanged.
"""
from __future__ import annotations

import copy
import json
import sys
import warnings
from pathlib import Path
from typing import Any

import pygame

from gameplay.world import DEFAULT_MAP, MAP_DIR, load_map_raw, load_materials, load_things, parse_map
from sprite_bank import SpriteBank, build_map_surface

TOOLS = {pygame.K_1: "wall", pygame.K_2: "floor", pygame.K_3: "object", pygame.K_4: "decal", pygame.K_5: "crate",
         pygame.K_6: "platform", pygame.K_7: "ramp", pygame.K_8: "site", pygame.K_9: "spawn_zone", pygame.K_0: "spawn",
         pygame.K_c: "callout"}
C_BG, C_TEXT, C_MUTED, C_ACCENT, C_SEL = (22, 21, 28), (232, 230, 239), (155, 152, 170), (224, 180, 55), (79, 214, 200)
EMPTY_MAP: dict[str, Any] = {"name": "New map", "source": "", "width": 40, "height": 40, "floor": "concrete",
                             "walls": [], "crates": [], "platforms": [], "ramps": [], "sites": [], "spawns": {"0": [], "1": []},
                             "spawn_zones": {}, "callouts": [], "floors": [], "objects": [], "decals": []}


class Editor:
    def __init__(self, key: str) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 800), pygame.RESIZABLE)
        pygame.display.set_caption(f"Val2d map editor – {key}")
        self.font = pygame.font.Font(None, 22)
        self.key = key
        self.path = Path(MAP_DIR) / f"{key}.json"
        try:
            self.data: dict[str, Any] = load_map_raw(key) if self.path.exists() or (Path(MAP_DIR) / f"{key}.py").exists() \
            else copy.deepcopy(EMPTY_MAP)  # a Python map is saved as .json next to it, which then wins
        except (OSError, json.JSONDecodeError) as exc:
            warnings.warn(f"{self.path.name} unreadable ({exc}); starting empty.")
            self.data = copy.deepcopy(EMPTY_MAP)
        for k, v in EMPTY_MAP.items():
            self.data.setdefault(k, copy.deepcopy(v))
        self.walls, self.floors = (sorted(t) for t in load_materials())
        self.objects, self.decals = (sorted(t) for t in load_things())
        self.choice = {"wall": 0, "floor": 0, "object": 0, "decal": 0}
        self.tool, self.rot, self.team, self.snap = "wall", 0, 0, True
        self.zoom, self.offset = 20.0, [40.0, 40.0]
        self.drag_start: tuple[float, float] | None = None
        self.panning = False
        self.history: list[dict[str, Any]] = []
        self.status = f"Loaded {self.path.name}" if self.path.exists() else f"New map {self.path.name}"
        self.bank = SpriteBank()
        self.surface: pygame.Surface | None = None
        self.dirty = True

    # ------------------------------------------------------------ coordinates
    def to_world(self, pos: tuple[int, int]) -> tuple[float, float]:
        x = (pos[0] - self.offset[0]) / self.zoom
        y = self.data["height"] - (pos[1] - self.offset[1]) / self.zoom
        if self.snap:
            x, y = round(x * 2) / 2, round(y * 2) / 2
        return max(0.0, min(float(self.data["width"]), x)), max(0.0, min(float(self.data["height"]), y))

    def to_screen(self, x: float, y: float) -> tuple[float, float]:
        return self.offset[0] + x * self.zoom, self.offset[1] + (self.data["height"] - y) * self.zoom

    def current(self, kind: str) -> str:
        names = {"wall": self.walls, "floor": self.floors, "object": self.objects, "decal": self.decals}[kind]
        return names[self.choice[kind] % len(names)] if names else ""

    # ------------------------------------------------------------ editing
    def remember(self) -> None:
        self.history.append(copy.deepcopy(self.data))
        self.history = self.history[-50:]
        self.dirty = True

    def add_rect(self, a: tuple[float, float], b: tuple[float, float]) -> None:
        rect = [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]
        if rect[2] - rect[0] < 0.25 or rect[3] - rect[1] < 0.25:
            return
        self.remember()
        d, t = self.data, self.tool
        if t == "wall":
            d["walls"].append({"rect": rect, "mat": self.current("wall")})
        elif t == "floor":
            d["floors"].append({"rect": rect, "mat": self.current("floor")})
        elif t == "crate":
            d["crates"].append(rect)
        elif t == "platform":
            d["platforms"].append(rect)
        elif t == "ramp":
            d["ramps"].append(rect)
        elif t == "site":
            used = {s["name"] for s in d["sites"]}
            name = next(c for c in "ABCDEFGH" if c not in used)
            d["sites"].append({"name": name, "rect": rect})
        elif t == "spawn_zone":
            d["spawn_zones"][str(self.team)] = rect
        elif t == "callout":
            d["callouts"].append({"name": f"Area {len(d['callouts']) + 1}", "rect": rect})
        elif t == "decal":
            d["decals"].append({"key": self.current("decal"), "rect": rect, "rot": self.rot})
        elif t == "object":
            d["objects"].append({"key": self.current("object"), "rect": rect, "rot": self.rot})

    def place(self, p: tuple[float, float]) -> None:
        self.remember()
        if self.tool == "object":
            self.data["objects"].append({"key": self.current("object"), "pos": list(p), "rot": self.rot})
        elif self.tool == "decal":
            self.data["decals"].append({"key": self.current("decal"), "pos": list(p), "rot": self.rot})
        elif self.tool == "spawn":
            self.data["spawns"].setdefault(str(self.team), []).append(list(p))

    def things(self) -> list[tuple[str, int, list[float]]]:
        """(list name, index, rect) for everything with an area, topmost last."""
        out: list[tuple[str, int, list[float]]] = []
        for name in ("floors", "decals", "ramps", "platforms", "crates", "walls", "objects", "sites", "callouts"):
            for i, item in enumerate(self.data.get(name, [])):
                rect = item if isinstance(item, list) else item.get("rect")
                if rect is None and "pos" in item:
                    x, y = item["pos"]
                    rect = [x - 0.5, y - 0.5, x + 0.5, y + 0.5]
                if rect:
                    out.append((name, i, rect))
        return out

    def delete_at(self, p: tuple[float, float]) -> None:
        for name, pts in self.data.get("spawns", {}).items():
            for i, (x, y) in enumerate(pts):
                if abs(x - p[0]) < 0.6 and abs(y - p[1]) < 0.6:
                    self.remember()
                    del pts[i]
                    return
        for name, i, r in reversed(self.things()):
            if r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3]:
                self.remember()
                del self.data[name][i]
                self.status = f"Deleted from {name}"
                return

    def save(self) -> None:
        try:
            self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            self.status = f"Saved {self.path.name}"
        except OSError as exc:
            self.status = f"Saving failed: {exc}"
            warnings.warn(self.status)

    # ------------------------------------------------------------ drawing
    def rebuild(self) -> None:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                world = parse_map(self.key, self.data)
            self.surface = build_map_surface(world, self.bank, self.zoom)
        except Exception as exc:  # a broken edit must not crash the editor
            self.status = f"Preview failed: {exc}"
            self.surface = None
        self.dirty = False

    def draw(self) -> None:
        s = self.screen
        s.fill(C_BG)
        if self.dirty:
            self.rebuild()
        if self.surface is not None:
            s.blit(self.surface, self.offset)
        d = self.data
        for name, col in (("sites", C_ACCENT), ("callouts", C_MUTED)):
            for item in d[name]:
                x0, y0, x1, y1 = item["rect"]
                a, b = self.to_screen(x0, y1), self.to_screen(x1, y0)
                pygame.draw.rect(s, col, (a[0], a[1], b[0] - a[0], b[1] - a[1]), 1)
                s.blit(self.font.render(item["name"], True, col), (a[0] + 3, a[1] + 3))
        for team, rect in d["spawn_zones"].items():
            x0, y0, x1, y1 = rect
            a, b = self.to_screen(x0, y1), self.to_screen(x1, y0)
            pygame.draw.rect(s, (79, 214, 200) if team == "0" else (238, 76, 74), (a[0], a[1], b[0] - a[0], b[1] - a[1]), 2)
        for team, pts in d["spawns"].items():
            for x, y in pts:
                pygame.draw.circle(s, (79, 214, 200) if team == "0" else (238, 76, 74), self.to_screen(x, y), max(3, self.zoom * 0.4))
        for teleporter in d.get("teleporters", []):
            x0, y0, x1, y1 = teleporter["entry"]
            a, b = self.to_screen(x0, y1), self.to_screen(x1, y0)
            entry = self.to_screen((x0 + x1) / 2, (y0 + y1) / 2)
            destination = self.to_screen(*teleporter["exit"])
            pygame.draw.rect(s, C_SEL, (a[0], a[1], b[0] - a[0], b[1] - a[1]), 2)
            pygame.draw.line(s, C_SEL, entry, destination, 1)
            pygame.draw.circle(s, C_SEL, destination, 5, 2)
        if self.drag_start is not None:
            a = self.to_screen(*self.drag_start)
            b = self.to_screen(*self.to_world(pygame.mouse.get_pos()))
            pygame.draw.rect(s, C_SEL, (min(a[0], b[0]), min(a[1], b[1]), abs(b[0] - a[0]), abs(b[1] - a[1])), 2)
        mx, my = self.to_world(pygame.mouse.get_pos())
        detail = self.current(self.tool) if self.tool in self.choice else ""
        info = [f"Tool: {self.tool}{' – ' + detail if detail else ''}   rot {self.rot}°   team {self.team}   snap {'on' if self.snap else 'off'}",
                f"Cursor {mx:.1f}, {my:.1f} m   map {d['width']}×{d['height']} m   1–9/0/C tools · Q/E choose · R rotate · T team · G snap · Ctrl+S save · Ctrl+Z undo",
                self.status]
        pygame.draw.rect(s, (12, 12, 18), (0, s.get_height() - 70, s.get_width(), 70))
        for i, line in enumerate(info):
            s.blit(self.font.render(line, True, C_TEXT if i == 0 else C_MUTED), (12, s.get_height() - 64 + i * 20))
        pygame.display.flip()

    # ------------------------------------------------------------ loop
    def run(self) -> None:
        clock = pygame.time.Clock()
        running = True
        while running:
            clock.tick(60)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    ctrl = pygame.key.get_mods() & pygame.KMOD_CTRL
                    if ev.key == pygame.K_ESCAPE:
                        running = False
                    elif ctrl and ev.key == pygame.K_s:
                        self.save()
                    elif ctrl and ev.key == pygame.K_z and self.history:
                        self.data = self.history.pop()
                        self.dirty = True
                    elif ev.key in TOOLS:
                        self.tool = TOOLS[ev.key]
                    elif ev.key in (pygame.K_q, pygame.K_e) and self.tool in self.choice:
                        self.choice[self.tool] += 1 if ev.key == pygame.K_e else -1
                    elif ev.key == pygame.K_r:
                        self.rot = (self.rot + 90) % 360
                    elif ev.key == pygame.K_t:
                        self.team = 1 - self.team
                    elif ev.key == pygame.K_g:
                        self.snap = not self.snap
                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    if ev.button == 1:
                        self.drag_start = self.to_world(ev.pos)
                    elif ev.button == 3:
                        self.delete_at(self.to_world(ev.pos))
                    elif ev.button == 2:
                        self.panning = True
                elif ev.type == pygame.MOUSEBUTTONUP:
                    if ev.button == 1 and self.drag_start is not None:
                        end = self.to_world(ev.pos)
                        if abs(end[0] - self.drag_start[0]) < 0.25 and abs(end[1] - self.drag_start[1]) < 0.25:
                            if self.tool in ("object", "decal", "spawn"):
                                self.place(end)
                        else:
                            self.add_rect(self.drag_start, end)
                        self.drag_start = None
                    elif ev.button == 2:
                        self.panning = False
                elif ev.type == pygame.MOUSEMOTION and self.panning:
                    self.offset[0] += ev.rel[0]
                    self.offset[1] += ev.rel[1]
                elif ev.type == pygame.MOUSEWHEEL:
                    old = self.zoom
                    self.zoom = max(4.0, min(64.0, self.zoom * (1.15 if ev.y > 0 else 1 / 1.15)))
                    mx, my = pygame.mouse.get_pos()
                    self.offset[0] = mx - (mx - self.offset[0]) * self.zoom / old
                    self.offset[1] = my - (my - self.offset[1]) * self.zoom / old
                    self.dirty = True
            self.draw()
        pygame.quit()


def main() -> None:
    key = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MAP
    if not key.replace("_", "").isalnum():
        print("Map key: letters, digits and _ only")
        return
    Editor(key).run()


if __name__ == "__main__":
    main()
