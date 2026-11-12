"""Val2D weapon cosmetics and loadout validation, shared by clients and hosts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SkinLine:
    name: str
    palette: tuple[str, str, str, str, str]
    pattern: tuple[str, ...]
    weapons: frozenset[str]


# Palettes run from outline to highlight, with the accent last. The patterns pick out
# accents on the body of the existing side-view sprites, preserving their outlines.
SKIN_LINES = {
    "prime": SkinLine("Prime", ("#27203a", "#655172", "#c19944", "#fff1c4", "#a878fc"),
                      ("....##", "...##.", "..##.."),
                      frozenset("classic frenzy spectre guardian vandal bucky phantom odin tactical_knife".split())),
    "reaver": SkinLine("Reaver", ("#211329", "#492c60", "#8a53ac", "#f4d4ff", "#e569f5"),
                       ("#....#", ".#..#.", "..##..", "......"),
                       frozenset("ghost sheriff spectre guardian vandal phantom operator odin tactical_knife".split())),
    "oni": SkinLine("Oni", ("#311620", "#6c2b30", "#be4144", "#ffd6ac", "#57d4ab"),
                    ("..##..", ".#..#.", "......", "..##.."),
                    frozenset("shorty frenzy bucky bulldog guardian phantom vandal ares tactical_knife".split())),
    "rgx": SkinLine("RGX 11z Pro", ("#192625", "#394b48", "#5d8375", "#ddffb9", "#a7ff42"),
                    ("######", "......", "#..#..", "......"),
                    frozenset("classic frenzy sheriff stinger spectre phantom vandal operator outlaw tactical_knife".split())),
    "kuronami": SkinLine("Kuronami", ("#1a2031", "#374761", "#829bb2", "#e3f7ff", "#86edfc"),
                         ("#.....", ".#....", "..##..", "....#."),
                         frozenset("ghost bandit sheriff spectre judge bulldog vandal warden marshal tactical_knife".split())),
}


def skin_options(weapon: str) -> tuple[str, ...]:
    """Available line IDs. Custom weapons can use the Prime palette by default."""
    return tuple(key for key, line in SKIN_LINES.items() if weapon in line.weapons) or ("prime",)


def skin_choice(weapon: str, value: object) -> str:
    return value if isinstance(value, str) and value in skin_options(weapon) else ""


def clean_loadout(raw: object, weapons: Iterable[str]) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {key: skin for key in weapons if (skin := skin_choice(key, raw.get(key)))}
