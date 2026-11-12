"""Third roster: twenty more agents, so Val2d has thirty. Same building blocks and states as the others.

Usage: python docs/design/sprites_roster2.py
Writes every required state (idle, walk, crouch, jump, dead, shoot, reload, cast, cast_c/q/e/x, portrait,
killfeed, select). Enemy variants: python docs/design/check_agent_sprites.py <key>.
Names and roles are proposals for config/agents.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sprites as base  # noqa: E402
import sprites_casts as casts  # noqa: E402
import sprites_roster as roster  # noqa: E402
import sprites_screens as screens  # noqa: E402

FACE = ["....SEESSEEs....", "....SSSSSSSs....", "....SSSssSSs....", ".....SSSSSs.....", "......ssss......", "......ssss......"]
FACE_GLASSES = ["....SAASSAAs....", "....SSSSSSSs....", "....SSSssSSs....", ".....SSSSSs.....", "......ssss......", "......ssss......"]
FACE_BEARD = ["....SEESSEEs....", "....SSSSSSSs....", "....DSSssSSD....", ".....DDDDDD.....", "......DDDD......", "......ssss......"]
FACE_MASK = ["....SEESSEEs....", "....SSSSSSSs....", "....AAAAAAAa....", ".....AAAAAa.....", "......ssss......", "......ssss......"]
FACE_VISOR = ["....AAAAAAAa....", "....SSSSSSSs....", "....SSSssSSs....", ".....SSSSSs.....", "......ssss......", "......ssss......"]

TOPS: dict[str, list[str]] = {
    "buzz": ["................", "................", "................", ".....hhhhhh.....", "....hSSSSSSh....", "....SSSSSSSs...."],
    "spiky": ["......H.H.H.....", ".....HHHHHHH....", "....HHHHHHHH....", "....HHHHHHHh....", "....HHHHHHHh....", "....HSSSSSSh...."],
    "afro": ["................", "....HHHHHHHH....", "...HHHHHHHHHH...", "...HHHHHHHHHh...", "...HHHHHHHHHh...", "...hHSSSSSShh..."],
    "beanie": ["................", "................", "......AAAA......", ".....AAAAAA.....", "....AAAAAAAa....", "....aaaaaaaa...."],
    "bob": ["................", "......HHHH......", ".....HHHHHH.....", "....HHHHHHHh....", "...HHHHHHHHhh...", "...HHSSSSSShh..."],
    "wide_hat": ["................", "......HHHH......", ".....HHHHHH.....", "...hhhhhhhhhh...", "....SSSSSSSs....", "....SSSSSSSs...."],
    "bald": ["................", "................", "......SSSS......", ".....SSSSSS.....", "....SSSSSSSs....", "....SSSSSSSs...."],
    "twin_buns": ["....HH....HH....", "...HHHH..HHHH...", "....HHHHHHHH....", "....HHHHHHHh....", "....HHHHHHHh....", "....HSSSSSSh...."],
    "cap_back": ["................", "................", "......HHHH......", ".....HHHHHH.....", "....HHHHHHHhhh..", "....HSSSSSSh...."],
    "side_shave": ["................", "......HHHH......", ".....HHHHHH.....", "....HHHHHHss....", "....HHHHHSSs....", "....HSSSSSSs...."],
    "ponytail": ["................", "......HHHH......", ".....HHHHHH.....", "....HHHHHHHhH...", "....HHHHHHHhHH..", "....HSSSSSShHh.."],
    "long": ["................", "......HHHH......", ".....HHHHHH.....", "....HHHHHHHh....", "...HHHHHHHHhh...", "...HHSSSSSShh..."],
}
SIDE_HAIR_ROWS = {"bob": 2, "long": 5, "ponytail": 3}  # rows of the face that get hair at the sides


def head(top: str, face: list[str]) -> list[str]:
    rows = TOPS[top] + list(face)
    n = SIDE_HAIR_ROWS.get(top, 0)
    for i in range(6, 6 + n):
        r = list(rows[i])
        if top == "ponytail":
            r[12], r[13] = "H", "h"
        else:
            r[3], r[12] = "H", "h"
        rows[i] = "".join(r)
    return rows


L = ["..JJ.KKKKKK.Jj..", "..SS.PPPPPP.Ss..", "..ss.PPPPPP.ss..", ".....PPPPPP....."]
TORSOS: dict[str, list[str]] = {
    "hoodie": ["..JJJGGGGJJJjj..", "..JJJJGGJJJJjj..", "..JJJJJJJJJJjj..", "..JJ.JAAAAJ.Jj..", "..JJ.JAAAAJ.Jj.."] + L,
    "tank": ["..SSJJJJJJJSss..", "..SSJJJJJJJSss..", "..SSJJJJJJJSss..", "..SS.JJJJJJ.Ss..", "..SS.JJJJJJ.Ss.."] + L,
    "trench": ["..JJGGJJGGJJjj..", "..JJJGJJGJJJjj..", "..JJJJJJJJJJjj..", "..JJ.JJJJJJ.Jj..", "..JJ.KKKKKK.Jj..",
               "..JJ.JjJJJJ.Jj..", "..SS.JjJJJJ.Ss..", "..ss.JjJJJJ.ss..", ".....JjJJJj....."],
    "tactical": ["..JJAAJJAAJJjj..", "..JJAaJJAaJJjj..", "..JJJJJJJJJJjj..", "..JJ.AAJJAA.Jj..", "..JJ.AaJJAa.Jj.."] + L,
    "sweater": ["..JJJJJJJJJJjj..", "..GGGGGGGGGGgg..", "..JJJJJJJJJJjj..", "..GG.GGGGGG.Gg..", "..JJ.JJJJJJ.Jj.."] + L,
    "poncho": ["..JJJJJJJJJJjj..", "..JJJJGJJJJJjj..", "..JJJJJJJJJJjj..", "..JJJJJJJJJJjj..", "..jjjjjjjjjjjj..",
               "..SS.KKKKKK.Ss..", "..ss.PPPPPP.ss..", ".....PPPPPP.....", ".....PPPPPP....."],
    "jacket": roster.TORSOS["jacket"], "vest": roster.TORSOS["vest"], "armor": roster.TORSOS["armor"],
    "coat": roster.TORSOS["coat"],
}
COAT_TORSOS = {"trench", "coat"}

COMMON = {**roster.COMMON, "D": "#4a3020", "A": "#3a3d44", "a": "#24262b", "G": "#c8ccd0", "g": "#9a9ea4",
          "V": "#8fb3bd"}

# key: (name, role, top, face, torso, glow, palette)
AGENTS: dict[str, tuple[str, str, str, list[str], str, str, dict[str, str]]] = {
    "brann": ("Brann", "Duelist", "spiky", FACE, "jacket", "#ff8a5a",
              {"H": "#e8e0d0", "h": "#b8b0a0", "S": "#e6b896", "s": "#b98a6c", "J": "#8a2f3a", "j": "#5e1f27", "G": "#d8d2c4", "g": "#a8a294"}),
    "quill": ("Quill", "Duelist", "ponytail", FACE, "tactical", "#ffd75e",
              {"H": "#2a1a14", "h": "#1a100c", "S": "#d9a07a", "s": "#a8735a", "J": "#3e4a5a", "j": "#2a3240", "A": "#c9a227", "a": "#8a6a1a"}),
    "sorrel": ("Sorrel", "Duelist", "afro", FACE, "tank", "#ffb060",
               {"H": "#3a2414", "h": "#24160c", "S": "#7a4e35", "s": "#583624", "J": "#c8682a", "j": "#8a4a1c"}),
    "dace": ("Dace", "Duelist", "buzz", FACE, "armor", "#c8a0ff",
             {"H": "#5a4a3a", "h": "#3e3228", "S": "#e0b090", "s": "#b08066", "J": "#6a5a7a", "j": "#4a3e56", "G": "#8a8a9a", "g": "#62626e", "A": "#c8a0ff"}),
    "mako": ("Mako", "Duelist", "side_shave", FACE, "hoodie", "#9ad48a",
             {"H": "#5a8a3a", "h": "#3e6228", "S": "#c48a62", "s": "#946446", "J": "#2d2c31", "j": "#1f1e23", "G": "#46454d", "g": "#323138", "A": "#7a5ab0"}),
    "wren": ("Wren", "Initiator", "bob", FACE_GLASSES, "vest", "#ffe08a",
             {"H": "#b84a2a", "h": "#86331c", "S": "#f0c8a8", "s": "#c49a7c", "J": "#4a4a3a", "j": "#33332a", "G": "#6a6a4a", "g": "#4e4e36", "A": "#2a2622"}),
    "odile": ("Odile", "Initiator", "twin_buns", FACE, "sweater", "#ff9ab0",
              {"H": "#1e1b1a", "h": "#121010", "S": "#e8c0a0", "s": "#bc9478", "J": "#d8d2c4", "j": "#a8a294", "G": "#8a3a4a", "g": "#5e2832"}),
    "pike": ("Pike", "Initiator", "wide_hat", FACE_BEARD, "poncho", "#e0c878",
             {"H": "#6b4a2e", "h": "#4a321e", "S": "#c8916c", "s": "#9a6a4e", "J": "#8a7a4a", "j": "#635830", "G": "#a8503a", "D": "#5a3a26"}),
    "lark": ("Lark", "Initiator", "beanie", FACE_MASK, "jacket", "#8fd0ff",
             {"A": "#c9a227", "a": "#8a6a1a", "S": "#9a6a50", "s": "#6e4a36", "J": "#3a4a6a", "j": "#28334a", "G": "#c8ccd0", "g": "#9a9ea4"}),
    "rhea": ("Rhea", "Initiator", "long", FACE, "trench", "#ffcf8a",
             {"H": "#3a2418", "h": "#26170f", "S": "#b07a5a", "s": "#845840", "J": "#a89a7a", "j": "#7a6e56", "C": "#a89a7a", "c": "#7a6e56", "G": "#c8b896", "K": "#4a3a2a"}),
    "fen": ("Fen", "Controller", "bald", FACE_BEARD, "coat", "#8adcc8",
            {"S": "#d8a888", "s": "#a87c62", "D": "#6a6a6a", "J": "#2f3e4a", "j": "#1f2a33", "C": "#2f3e4a", "c": "#1f2a33", "A": "#8fb3bd", "K": "#1f1c1a"}),
    "thorne": ("Thorne", "Controller", "spiky", FACE, "trench", "#ff6a6a",
               {"H": "#1a1a1a", "h": "#0e0e0e", "S": "#e0c0a8", "s": "#b4947e", "J": "#3a1e22", "j": "#261416", "C": "#3a1e22", "c": "#261416", "G": "#5a2e32", "K": "#1a1416"}),
    "moraine": ("Moraine", "Controller", "long", FACE, "poncho", "#c8d8ff",
                {"H": "#c8ccd0", "h": "#9a9ea4", "S": "#e8c4a4", "s": "#bc987c", "J": "#3e4a5a", "j": "#2a3240", "G": "#8fb3bd"}),
    "sloane": ("Sloane", "Controller", "bob", FACE, "coat", "#d8a8ff",
               {"H": "#8a6a3a", "h": "#644c28", "S": "#f0d0b0", "s": "#c4a488", "J": "#4a3a5a", "j": "#33283e", "C": "#4a3a5a", "c": "#33283e", "A": "#c9a227", "K": "#1f1c1a"}),
    "tove": ("Tove", "Controller", "beanie", FACE_VISOR, "hoodie", "#b0f0a0",
             {"A": "#5a6a3a", "a": "#3e4a28", "S": "#e6b896", "s": "#b98a6c", "J": "#5a6a3a", "j": "#3e4a28", "G": "#7a8a5a", "g": "#5a6a40"}),
    "garrick": ("Garrick", "Sentinel", "buzz", FACE_VISOR, "tactical", "#a0d8ff",
                {"H": "#4a5a4a", "h": "#334033", "A": "#8fb3bd", "a": "#4f6b73", "S": "#c48a62", "s": "#946446", "J": "#4a5a4a", "j": "#334033"}),
    "ilse": ("Ilse", "Sentinel", "ponytail", FACE, "armor", "#fff0a0",
             {"H": "#e0c890", "h": "#b09a66", "S": "#f0c8a8", "s": "#c49a7c", "J": "#7a7a8a", "j": "#565664", "G": "#a0a0b0", "g": "#787888", "A": "#c9a227"}),
    "basil": ("Basil", "Sentinel", "cap_back", FACE_BEARD, "vest", "#ffc080",
              {"H": "#6a2a2a", "h": "#4a1c1c", "S": "#8a5a43", "s": "#63402f", "D": "#2a1a14", "J": "#3a3b44", "j": "#26272e", "G": "#6a5a3a", "g": "#4e4228", "A": "#2a2622"}),
    "cato": ("Cato", "Sentinel", "cap_back", FACE_GLASSES, "tank", "#90e0ff",
             {"H": "#2a2a30", "h": "#1a1a20", "S": "#6b4530", "s": "#4a2f20", "A": "#c8ccd0", "J": "#4a6a8a", "j": "#33495e"}),
    "ulric": ("Ulric", "Sentinel", "buzz", FACE_BEARD, "sweater", "#e8e0c0",
              {"H": "#8a8a8a", "h": "#626262", "S": "#e0b8a0", "s": "#b48e78", "D": "#8a8a8a", "J": "#3e5a4a", "j": "#2a3e33", "G": "#c8ccd0", "g": "#9a9ea4"}),
}


def build(key: str) -> None:
    name, role, top, face, torso, glow, pal = AGENTS[key]
    rows = head(top, face) + TORSOS[torso]
    assert len(rows) == 21 and all(len(r) == 16 for r in rows), (key, [len(r) for r in rows])
    palette = {**COMMON, **pal}
    coat = 2 if torso in COAT_TORSOS else 0
    hip = "CCCCCc" if coat else "PPPPPp"
    if coat:
        palette.setdefault("C", palette["J"])
        palette.setdefault("c", palette["j"])
    frames = base.agent_frames(rows, palette, hip, coat)
    frames.update(base.action_frames(rows, palette, hip, coat, glow))
    frames.update(casts.casts(rows, palette, hip, coat, glow))
    for state, imgs in frames.items():
        base.save(imgs[0] if len(imgs) == 1 else base.strip(imgs), f"agents/{key}/{key}_{state}.png")
    base.save(base.portrait(rows, palette), f"agents/{key}/{key}_portrait.png")
    screens.make(key)


def main() -> None:
    for key in AGENTS:
        build(key)


if __name__ == "__main__":
    main()
