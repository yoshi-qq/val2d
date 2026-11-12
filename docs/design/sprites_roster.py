"""Second sprite batch: eight new agents, ability icons by building block, new weapons,
generic effects and status icons. In the Val2d style.

Usage: python docs/design/sprites_roster.py
Reads agent and weapon keys from config/agents.py and config/weapons.py.
"""
from __future__ import annotations

import math
import runpy
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sprites as base  # noqa: E402

ROOT = base.ROOT
CLEAR = base.CLEAR

# ------------------------------------------------------------------ figure building blocks
HEADS: dict[str, list[str]] = {
    "short": ["................", "................", "......HHHH......", ".....HHHHHH.....", "....HHHHHHHh....",
              "....HSSSSSSh....", "....SEESSEEs....", "....SSSSSSSs....", "....SSSssSSs....", ".....SSSSSs.....",
              "......ssss......", "......ssss......"],
    "long": ["................", "................", "......HHHH......", ".....HHHHHH.....", "....HHHHHHHh....",
             "...HHSSSSSShh...", "...HSEESSEEsh...", "...HSSSSSSSsh...", "...HSSSssSSsh...", "...HhSSSSSshh...",
             "...Hh.ssss.hh...", "...hh.ssss.hh..."],
    "bun_headset": ["................", ".......HH.......", "......HHHh......", ".....HAAAAH.....", "....HHHHHHHh....",
                    "....HSSSSSSh....", "...ASEESSEEsA...", "...aSSSSSSSsa...", "....SSSssSSs....", ".....SSSSSs.....",
                    "......ssss......", "......ssss......"],
    "helmet": ["................", "......HHHH......", "....HHHHHHHH....", "...HHHHHHHHHh...", "...HHHHHHHHHh...",
               "...HVVVVVVVVh...", "...HVVVVVVVVh...", "...HhSSSSSShh...", "....hSSssSSh....", ".....SSSSSs.....",
               "......ssss......", "......ssss......"],
    "goggles_up": ["................", "................", "......HHHH......", ".....HHHHHH.....", "....HAAHHAAh....",
                   "....HSSSSSSh....", "....SEESSEEs....", "....SSSSSSSs....", "....SSSssSSs....", ".....SSSSSs.....",
                   "......ssss......", "......ssss......"],
    "cap_beard": ["................", "................", "......HHHH......", ".....HHHHHH.....", "....HHHHHHHh....",
                  "...hhhhhhhhhh...", "....SEESSEEs....", "....SSSSSSSs....", "....DSSssSSD....", ".....DDDDDD.....",
                  "......DDDD......", "......ssss......"],
    "mohawk": ["................", ".......HH.......", ".......HH.......", ".....SSHHSS.....", "....SSSHHSSs....",
               "....SSSSSSSs....", "....SEESSEEs....", "....SASSSSSs....", "....SSSssSSs....", ".....SSSSSs.....",
               "......ssss......", "......ssss......"],
    "headband": ["................", "................", "......HHHH......", ".....HHHHHH.....", "....AAAAAAAa....",
                 "....HSSSSSSh....", "....SEESSEEs....", "....SSSSSSSs....", "....SSSssSSs....", ".....SSSSSs.....",
                 "......ssss......", "......ssss......"],
}

_LOWER = ["..JJ.KKKKKK.Jj..", "..SS.PPPPPP.Ss..", "..ss.PPPPPP.ss..", ".....PPPPPP....."]
TORSOS: dict[str, list[str]] = {
    "jacket": ["..JJJJGGJJJJjj..", "..JJjJGgJjJJjj..", "..JJJJJGJJJJjj..", "..JJ.JJJJJJ.Jj..", "..JJ.JJJJJJ.Jj.."] + _LOWER,
    "vest": ["..JJGGGGGGGGJj..", "..JJGgAGGAgGJj..", "..JJGGGGGGGGJj..", "..JJ.GGGGGG.Jj..", "..JJ.GgGGgG.Jj.."] + _LOWER,
    "coat": ["..JJJJjJJJJJjj..", "..JJAJjJJAJJjj..", "..JJJJjJJJJJjj..", "..JJ.JjJJJJ.Jj..", "..JJ.JjJJJJ.Jj..",
             "..JJ.KKKKKK.Jj..", "..SS.JjJJJJ.Ss..", "..ss.JjJJJJ.ss..", ".....JjJJJj....."],
    "armor": ["..GGGJJJJJGGGg..", "..GgGJAAAJGgGg..", "..JJJJAAAJJJJj..", "..JJ.JJJJJJ.Jj..", "..JJ.JJJJJJ.Jj.."] + _LOWER,
    "hivis": ["..JJJJGGJJJJjj..", "..JJjJGgJjJJjj..", "..AAAAAAAAAAAa..", "..JJ.JJJJJJ.Jj..", "..AA.AAAAAA.Aa.."] + _LOWER,
    "medic": ["..JJGGGGGGGGJj..", "..JJGGGAAGGGJj..", "..JJGGAAAAGGJj..", "..JJ.GGAAGG.Jj..", "..JJ.GgGGgG.Jj.."] + _LOWER,
}

COMMON = {"E": "#1b1a1a", "K": "#2a2622", "P": "#2d2c31", "p": "#1f1e23", "B": "#1b1a1a"}

AGENT_LOOKS: dict[str, dict[str, object]] = {
    "vesper":  {"head": "long", "torso": "jacket", "glow": "#b48ce0",
                "pal": {"H": "#3b2a4a", "h": "#261b31", "S": "#e3b896", "s": "#b98a6c", "J": "#2f6f6a", "j": "#1f4d49", "G": "#d8d2c4", "g": "#a8a294"}},
    "rook":    {"head": "helmet", "torso": "armor", "glow": "#ffb060",
                "pal": {"H": "#6b5a3a", "h": "#4a3e28", "V": "#e08a2a", "S": "#c48a62", "s": "#946446", "J": "#5a5f66", "j": "#3e4248", "G": "#8a8f96", "g": "#62666c", "A": "#e08a2a", "P": "#3a3b44", "p": "#26272e"}},
    "tamsin":  {"head": "bun_headset", "torso": "vest", "glow": "#9ad0ff",
                "pal": {"H": "#d8c070", "h": "#a8903e", "A": "#3a3d44", "a": "#24262b", "S": "#edc4a0", "s": "#c0957a", "J": "#4a5a7a", "j": "#334058", "G": "#6a7a9a", "g": "#4a5878"}},
    "okoro":   {"head": "goggles_up", "torso": "vest", "glow": "#ffe08a",
                "pal": {"H": "#1e1b1a", "h": "#121010", "A": "#8fb3bd", "a": "#4f6b73", "S": "#6b4530", "s": "#4a2f20", "J": "#3e3a2e", "j": "#2a271f", "G": "#8a7a4a", "g": "#63582f", "P": "#3a3b44", "p": "#26272e"}},
    "juniper": {"head": "long", "torso": "coat", "glow": "#9ad48a", "hip": "CCCCCc", "coat_rows": 2,
                "pal": {"H": "#8a4a2a", "h": "#5e311b", "S": "#f0c8a8", "s": "#c49a7c", "J": "#3e5a3a", "j": "#2a3e27", "C": "#3e5a3a", "c": "#2a3e27", "A": "#c9a227", "K": "#1f1c1a"}},
    "nyx":     {"head": "mohawk", "torso": "coat", "glow": "#9a7ad8", "hip": "CCCCCc", "coat_rows": 2,
                "pal": {"H": "#d8dce6", "h": "#9ea2ac", "S": "#9a6a50", "s": "#6e4a36", "A": "#7a5ab0", "J": "#2a2638", "j": "#1b1824", "C": "#2a2638", "c": "#1b1824", "K": "#1f1c1a"}},
    "harrow":  {"head": "cap_beard", "torso": "hivis", "glow": "#ffd75e",
                "pal": {"H": "#3a4a5a", "h": "#26313c", "D": "#5a3a26", "S": "#d9a07a", "s": "#a8735a", "J": "#b8682a", "j": "#8a4c1c", "G": "#e8e6ef", "g": "#b8b6bf", "A": "#e8e6a0", "a": "#b8b67a", "P": "#2d3a4a", "p": "#1f2834"}},
    "sable":   {"head": "headband", "torso": "medic", "glow": "#9ad48a",
                "pal": {"H": "#2a2a30", "h": "#1a1a20", "A": "#6fbf73", "a": "#4a8a4e", "S": "#c8916c", "s": "#9a6a4e", "J": "#6a6e76", "j": "#4a4e56", "G": "#c8ccd0", "g": "#9a9ea4", "P": "#3a3b44", "p": "#26272e"}},
}


def make_agents() -> None:
    for key, look in AGENT_LOOKS.items():
        top = HEADS[str(look["head"])] + TORSOS[str(look["torso"])]
        assert len(top) == 21, (key, len(top))
        pal = {**COMMON, **look["pal"]}  # type: ignore[dict-item]
        hip = str(look.get("hip", "PPPPPp"))
        coat = int(look.get("coat_rows", 0))  # type: ignore[arg-type]
        frames = base.agent_frames(top, pal, hip, coat)
        frames.update(base.action_frames(top, pal, hip, coat, str(look["glow"])))
        for state, imgs in frames.items():
            im = imgs[0] if len(imgs) == 1 else base.strip(imgs)
            base.save(im, f"agents/{key}/{key}_{state}.png")
            base.save(base.enemy_variant(im) if state != "dead" else im, f"agents/{key}/{key}_{state}_feind.png")
        base.save(base.portrait(top, pal), f"agents/{key}/{key}_portrait.png")


# ------------------------------------------------------------------ ability icons by building block
GLYPHS: dict[str, list[str]] = {
    "flash":      ["...W...W...W", "....W..W..W.", ".....WWWWW..", "..WWWWYYYWWW", ".....WWWWW..", "....W..W..W.", "...W...W...W", "............"],
    "hop":        [".....W......", "....WWW.....", "...WWWWW....", "..WW.W.WW...", ".....W......", ".....W......", "...YYYYY....", "..YYYYYYY..."],
    "dash":       ["......WW....", ".W...WWWW...", "W...WWWWWW..", "WWWWWWWWWWW.", "W...WWWWWW..", ".W...WWWW...", "......WW....", "............"],
    "overdrive":  ["...YYYYY....", "..Y.WWW.Y...", ".Y.WW.W..Y..", ".Y.WWWWW.Y..", ".Y..W.WW.Y..", "..Y.WWW.Y...", "...YYYYY....", "............"],
    "sensor":     ["....WWWW....", "..WW....WW..", ".W..WWWW..W.", "W..W.YY.W..W", ".W..WWWW..W.", "..WW....WW..", "....WWWW....", "............"],
    "wall":       ["W..W..W..W..", "W..W..W..W..", "WWWWWWWWWW..", "WWWWWWWWWW..", "W..W..W..W..", "W..W..W..W..", "............", "............"],
    "smoke":      ["....WWWW....", "..WWWWWWWW..", ".WWWWWWWWWW.", ".WWWWWWWWWW.", ".WWWWWWWWWW.", "..WWWWWWWW..", "....WWWW....", "............"],
    "zone":       ["...W.W.W....", "..W.....W...", ".W...Y...W..", "W...YYY...W.", ".W...Y...W..", "..W.....W...", "...W.W.W....", "............"],
    "decoy":      ["..WW........", ".WWWW.......", ".WWWW...WW..", "..WW...WWWW.", "........WWWW", "........WW..", "............", "............"],
    "teleport":   ["....W.W.....", "..W.....W...", ".W..WWW..W..", "...W...W....", ".W..WWW..W..", "..W.....W...", "....W.W.....", "............"],
    "blast":      ["...WWWWW....", "..W.....W...", ".W..YYY..W..", ".W..YYY..W..", ".W..YYY..W..", "..W.....W...", "...WWWWW....", "............"],
    "immunity":   [".WW...WW....", "WWWW.WWWW...", "WWWWWWWWW...", ".WWWWWWW....", "..WWWWW.....", "...WWW......", "....W.......", "............"],
    "shield":     ["WWWWWWWWW...", "WYWWWWWYW...", "WWWWWWWWW...", "WWWWWWWWW...", ".WWWWWWW....", "..WWWWW.....", "....W.......", "............"],
    "wave":       ["............", ".WW....WW...", "W..W..W..W..", "....WW....WW", "............", ".YY....YY...", "Y..Y..Y..Y..", "....YY....YY"],
    "tripwire":   ["............", "WW........WW", "WWYYYYYYYYWW", "WW........WW", "............", "............", "............", "............"],
    "alarm":      ["....WW......", "...WWWW.....", "..WWWWWW....", "..WWWWWW....", ".WWWWWWWW...", "WWWWWWWWWW..", "....YY......", "............"],
    "revive":     ["....WWW.....", "....WWW.....", "..WWWWWWW...", "..WWWWWWW...", "....WWW.....", "....WWW.....", "..YYYYYYY...", "............"],
    "anchor":     ["....WWW.....", "...W...W....", "...W...W....", "....WWW.....", ".....W......", ".....W......", "...YYYYY....", "............"],
    "heal":       ["....YYY.....", "....YYY.....", "..YYYYYYY...", "..YYYYYYY...", "....YYY.....", "....YYY.....", "............", "............"],
    "reveal_all": ["..WWWWWWWW..", ".W........W.", "W...WWWW...W", "W..WYYYYW..W", "W...WWWW...W", ".W........W.", "..WWWWWWWW..", "............"],
}


def icon(kind: str, ult: bool) -> Image.Image:
    rows = GLYPHS.get(kind)
    if rows is None:
        rows = GLYPHS["zone"]
        print("warning: no glyph for kind", kind, "- using zone")
    glyph = base.from_rows([r.ljust(12, ".")[:12] for r in rows], {"W": "#e8e6ef", "Y": "#e0b437"})
    im = Image.new("RGBA", (16, 16), CLEAR)
    if ult:
        px = im.load()
        for i in range(16):
            for p in ((i, 0), (i, 15), (0, i), (15, i)):
                if not (p[0] in (0, 15) and p[1] in (0, 15)):
                    px[p] = base.hexc("#e0b437")
    im.alpha_composite(glyph, (2, 4))
    return im


def _config(name: str, probe: str) -> dict:
    if name == "agents":  # one file per agent in config/agents/ since 12.11.2026
        import sys as _sys
        _sys.path.insert(0, str(ROOT))
        from gameplay.match import load_agents
        return dict(load_agents())
    data = runpy.run_path(str(ROOT / "config" / f"{name}.py"))
    for value in data.values():
        if isinstance(value, dict) and probe in value:
            return value
    raise SystemExit(f"config/{name}.py: no dict containing {probe!r}")


def make_icons() -> None:
    agents = _config("agents", "kestrel")
    for key, info in agents.items():
        for slot, ab in info["abilities"].items():
            base.save(icon(str(ab["kind"]), slot == "X"), f"ui/faehigkeit_{key}_{slot}.png")


# ------------------------------------------------------------------ weapons
NEW_GUNS: dict[str, dict[str, object]] = {
    "hornisse": {"len": 10, "barrel": 2, "mag": "stick",  "stock": None,   "scope": False, "accent": "#c9a227"},
    "lynx":     {"len": 11, "barrel": 4, "mag": "pistol", "stock": None,   "scope": False, "accent": "#4f6b73", "silencer": True},
    "kite":     {"len": 11, "barrel": 5, "mag": "pistol", "stock": None,   "scope": False, "accent": "#8a5a43", "sight": True},
    "heron":    {"len": 15, "barrel": 4, "mag": "curve",  "stock": "full", "scope": True,  "accent": "#5a6b7a"},
    "crane":    {"len": 16, "barrel": 7, "mag": None,     "stock": "full", "scope": True,  "accent": "#6b4a2e", "double": True},
}


def make_weapons() -> None:
    for key, spec in NEW_GUNS.items():
        for w, h, suffix in ((16, 8, ""), (32, 12, "_kauf")):
            im = base.draw_gun(spec, w, h)
            px = im.load()
            u = w / 16.0
            if spec.get("double"):
                for x in range(int((16 - int(spec["barrel"])) * u), w):  # type: ignore[arg-type]
                    y = int(5 * h / 8)
                    px[x, min(y, h - 1)] = base.hexc("#232228")
            if spec.get("sight"):
                for x in range(int(11 * u), int(13 * u) + 1):
                    px[min(x, w - 1), max(0, int(1.5 * h / 8))] = base.hexc("#232228")
            if suffix and (spec.get("double") or spec.get("sight")):
                im = base.outline(im.copy().crop((0, 0, w, h))) if False else im
            base.save(im, f"weapons/val2d/{key}{suffix}.png")


# ------------------------------------------------------------------ generic effects
def make_fx() -> None:
    import random
    rng = random.Random(21)

    def zone_frame(alpha_ring: int, alpha_fill: int, phase: int) -> Image.Image:
        im = Image.new("RGBA", (64, 64), CLEAR)
        p = im.load()
        for y in range(64):
            for x in range(64):
                d = math.hypot(x - 31.5, y - 31.5)
                if 30 <= d <= 31.8 and (int(math.degrees(math.atan2(y - 31.5, x - 31.5)) + phase * 6) // 12) % 2 == 0:
                    p[x, y] = (255, 255, 255, alpha_ring)
                elif d < 30 and (x + y + phase) % 5 == 0:
                    p[x, y] = (255, 255, 255, alpha_fill)
        return im

    base.save(base.strip([zone_frame(230, 70, i) for i in range(3)]), "fx/zone.png")

    blast = []
    for i in range(6):
        im = Image.new("RGBA", (64, 64), CLEAR)
        p = im.load()
        r = 6 + i * 5.2
        for y in range(64):
            for x in range(64):
                d = math.hypot(x - 31.5, y - 31.5)
                if r - 2.5 <= d <= r and rng.random() < 1.0 - i * 0.12:
                    p[x, y] = (255, 251, 232, 240 - i * 35) if d > r - 1.2 else (200, 196, 210, 200 - i * 30)
        blast.append(im)
    base.save(base.strip(blast), "fx/blast.png")

    wire = Image.new("RGBA", (16, 4), CLEAR)
    wp = wire.load()
    for x in range(16):
        wp[x, 1] = (255, 120, 110, 230)
        wp[x, 2] = (160, 60, 56, 200) if x % 4 else (255, 180, 170, 230)
    base.save(wire, "fx/tripwire.png")
    node = base.from_rows([".oooo.", "oMMMMo", "oMRRMo", "oMRRMo", "oMMMMo", ".oooo."],
                          {"o": "#16151b", "M": "#6b7480", "R": "#ff5a4f"})
    base.save(node, "fx/tripwire_node.png")

    bell_rows = ["................", "......oooo......", ".....oMMMMo.....", "....oMmmmmMo....", "....oMmLLmMo....",
                 "....oMmLLmMo....", "...oMMmmmmMMo...", "...oooooooooo...", "......oYYo......", ".......oo.......",
                 "................", "................", "................", "................", "................", "................"]
    bpal = {"o": "#16151b", "M": "#7d8790", "m": "#545c64", "Y": "#e0b437"}
    base.save(base.strip([base.from_rows(bell_rows, {**bpal, "L": "#ff5a4f"}), base.from_rows(bell_rows, {**bpal, "L": "#5a2a2a"})]), "fx/alarm.png")

    wave = []
    for f in range(3):
        im = Image.new("RGBA", (16, 16), CLEAR)
        p = im.load()
        for x in range(16):
            y = int(7.5 + 3 * math.sin((x + f * 5) / 16 * 2 * math.pi))
            for dy in (-1, 0, 1):
                a = 240 if dy == 0 else 120
                p[x, max(0, min(15, y + dy))] = (255, 255, 255, a)
        wave.append(im)
    base.save(base.strip(wave), "fx/wave.png")


STATUS: dict[str, tuple[list[str], dict[str, str]]] = {
    "nearsight": (["........", ".WWWWW..", "W.ggg.W.", "W.g.g.W.", "W.ggg.W.", ".WWWWW..", "........", "........"], {"W": "#e8e6ef", "g": "#545c64"}),
    "concuss":   (["Y.....Y.", ".Y...Y..", "...W....", "..WWW...", "...W....", ".Y...Y..", "Y.....Y.", "........"], {"Y": "#e0b437", "W": "#e8e6ef"}),
    "slow":      (["WWWWWW..", ".W..W...", "..WW....", "..WW....", ".W..W...", "WWWWWW..", "........", "........"], {"W": "#9a7ad8"}),
    "vulnerable": (["RRRRRR..", "RR.RRR..", "RRR.RR..", "RR.RRR..", ".RR.R...", "..RR....", "........", "........"], {"R": "#ee4c4a"}),
    "decay":     ([".GG.GG..", "GGGGGGG.", "GGG.GGG.", ".GG.GG..", "..G.G...", "...G....", "...g....", "...g...."], {"G": "#9a7ad8", "g": "#6a4aa8"}),
    "suppress":  (["R....R..", ".R..YR..", "..RYR...", "..YR....", ".YR.R...", "YR...R..", "R.....R.", "........"], {"R": "#ee4c4a", "Y": "#e0b437"}),
    "detain":    (["..WWW...", ".W...W..", ".W...W..", "WWWWWWW.", "WWW.WWW.", "WWW.WWW.", "WWWWWWW.", "........"], {"W": "#c7ccd2"}),
    "deaf":      ([".WWW..R.", "W...WR..", "W..WR...", ".W.R....", "..R.W...", ".R.WW...", "R.......", "........"], {"W": "#e8e6ef", "R": "#ee4c4a"}),
    "stim":      (["...G....", "..GGG...", ".G.G.G..", "...G....", "..GGG...", ".G.G.G..", "...G....", "........"], {"G": "#6fbf73"}),
}


def make_status() -> None:
    for key, (rows, pal) in STATUS.items():
        base.save(base.from_rows(rows, pal), f"ui/status/{key}.png")


def main() -> None:
    make_agents()
    make_icons()
    make_weapons()
    make_fx()
    make_status()


if __name__ == "__main__":
    main()
