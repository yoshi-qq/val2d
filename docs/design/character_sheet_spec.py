"""Single source for the character sprite sheet blueprint (docs/design/CHARACTER_SHEETS.md).

Every state is one Aseprite tag and one exported strip assets/agents/{key}/{key}_{state}.png.
play.py reads STATES at start: keep the State fields tag, fps, loop and fallback stable
(add new states or fields, but don't rename or remove them without telling the coding session).
"""
from __future__ import annotations

from dataclasses import dataclass

CELL_W, CELL_H = 16, 32
PIXELS_PER_METRE = 16

# Hit-zone columns and rows inside a 16x32 cell (x0, x1 inclusive). Widths match config/game_config.json.
ZONES = {
    "head": {"x": (4, 11), "y": (2, 10)},   # 8 px = 0.50 m
    "body": {"x": (2, 13), "y": (11, 20)},  # 12 px = 0.75 m
    "legs": {"x": (5, 11), "y": (21, 30)},  # 7 px = 0.44 m
}
ANCHOR = (8, 16)  # cell centre = player position in the world
GROUND_ROW = 30   # lowest row the boots may use
RESERVED = {"teal": "#4fd6c8", "red": "#ee4c4a"}  # team/enemy colours, keep off large areas
MAX_COLOURS = 20


@dataclass(frozen=True)
class State:
    tag: str
    frames: tuple[int, int]  # allowed frame count (min, max)
    fps: float | None        # None = stretched to a game duration
    loop: bool
    required: bool
    fallback: str | None
    group: str
    note: str
    size: tuple[int, int] = (CELL_W, CELL_H)


STATES: list[State] = [
    # movement
    State("idle", (1, 4), 4, True, True, None, "Movement", "standing still; 1 frame is fine, 2–4 for breathing"),
    State("walk", (4, 6), 8, True, True, "idle", "Movement", "moving; the game scales the rate with speed (run, walk)"),
    State("crouch", (1, 2), 4, True, True, "idle", "Movement", "crouched and still; upper body about 3 px lower"),
    State("crouch_walk", (4, 4), 6, True, False, "crouch", "Movement", "moving while crouched"),
    State("jump", (1, 2), 8, False, True, "idle", "Movement", "rising; legs tucked"),
    State("fall", (1, 2), 8, False, False, "jump", "Movement", "falling or dropping a level"),
    State("land", (1, 2), 12, False, False, "idle", "Movement", "touch-down, knees bent"),
    # combat
    State("shoot", (2, 3), 12, False, True, "idle", "Combat", "one recoil per shot; weapon and muzzle flash are drawn by the game"),
    State("reload", (4, 6), None, False, True, "idle", "Combat", "stretched to the weapon's reload time"),
    State("equip", (2, 3), None, False, False, "idle", "Combat", "drawing a weapon; stretched to the equip time"),
    State("melee", (3, 4), 12, False, False, "shoot", "Combat", "knife slash"),
    State("flinch", (2, 2), 12, False, False, "idle", "Combat", "hit reaction, short"),
    # objective
    State("plant", (2, 2), 4, True, False, "crouch", "Bomb", "kneeling, hands on the bomb; loops while planting"),
    State("defuse", (2, 2), 4, True, False, "crouch", "Bomb", "kneeling, working on the bomb; loops while defusing"),
    # abilities: one own animation per ability slot is required
    State("cast_c", (3, 4), 8, False, True, "cast", "Abilities", "ability C, own pose (e.g. throw)"),
    State("cast_q", (3, 4), 8, False, True, "cast", "Abilities", "ability Q, own pose (e.g. place on the ground)"),
    State("cast_e", (3, 4), 8, False, True, "cast", "Abilities", "ability E (signature), own pose"),
    State("cast_x", (4, 6), 8, False, True, "cast", "Abilities", "ultimate; may use the whole cell incl. columns 0 and 15 for glow"),
    State("channel_c", (2, 4), 6, True, False, "cast_c", "Abilities", "held version of C (aiming, charging); loops"),
    State("channel_q", (2, 4), 6, True, False, "cast_q", "Abilities", "held version of Q; loops"),
    State("channel_e", (2, 4), 6, True, False, "cast_e", "Abilities", "held version of E; loops"),
    State("channel_x", (2, 4), 6, True, False, "cast_x", "Abilities", "held or active ultimate; loops while it runs"),
    State("cast", (3, 3), 8, False, False, "idle", "Abilities", "shared fallback pose for older sprites only"),
    # end of life and screens
    State("dying", (3, 4), 10, False, False, "dead", "Death", "falling over; ends in the dead pose"),
    State("dead", (1, 1), None, False, True, None, "Death", "lying, 32x16 cell, figure rotated to the left", (32, 16)),
    State("victory", (2, 4), 4, True, False, "idle", "Screens", "end-of-match pose"),
    State("portrait", (1, 1), None, False, True, None, "Screens", "agent select, scoreboard; head and shoulders", (32, 32)),
    State("killfeed", (1, 1), None, False, False, "portrait", "Screens", "head only, for kill feed and minimap list", (16, 16)),
    State("select", (1, 1), None, False, False, "portrait", "Screens", "large agent-select figure", (32, 64)),
]

STATE_BY_TAG = {s.tag: s for s in STATES}

# Special mechanics (section 5 of CHARACTER_SHEETS.md). Agents declare which ones they use.
MECHANIC_PREFIX = "mech_"      # extra state: {key}_mech_{name}.png, 16x32, 1-6 frames, falls back to idle
FORM_SEPARATOR = "@"           # form: {key}@{form}_{state}.png replaces the normal state while the form is active
OVERLAY_PREFIX = "overlay_"    # overlay: {key}_overlay_{name}.png, drawn on top of every state, 1 frame or same count as walk

