"""Registries of the ability kit: effects, triggers, targets, player sets and presets.

Every mechanic is a small function registered under a name. Ability data (config/content/agents/*.py) only names
them, so a new mechanic is one decorated function, either here in gameplay/kit or in a file in
config/content/mechanics/ (loaded at start, no change to the game code needed).

    @effect("lifesteal")
    def lifesteal(ctx: Ctx, target: PlayerState | None, step: dict) -> bool | None:
        ...

Return False from an effect used directly on use (`do=[...]` of an ability) to cancel the ability
(no charge is spent); any other return value counts as done.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from gameplay.geometry import Vec

if TYPE_CHECKING:
    from gameplay.match import Effect, Match, PlayerState


@dataclass
class Ctx:
    """Everything an effect or trigger needs to know about the moment it runs."""
    m: Match
    owner: PlayerState | None       # who used the ability (None if the owner left)
    team: int
    point: Vec                       # target point of the ability, or the position of the placed object
    source: Vec                      # where the owner stood when using it
    aim: Vec                         # aim direction of the owner at use (unit vector)
    ability: dict[str, Any] = field(default_factory=dict)
    key: str = ""                    # slot C, Q, E or X ("" for passives)
    obj: Effect | None = None        # the placed object a trigger belongs to
    dt: float = 0.0                  # frame time, for per-second effects
    other: PlayerState | None = None  # second player of an event (the victim of a kill, the attacker of a hit)


EffectFn = Callable[[Ctx, "PlayerState | None", dict[str, Any]], Any]
TriggerFn = Callable[[Ctx, dict[str, Any]], "list[tuple[Ctx, list[PlayerState] | None]]"]
TargetFn = Callable[["Match", "PlayerState", dict[str, Any]], "Vec | None"]
WhoFn = Callable[[Ctx, dict[str, Any]], "list[PlayerState]"]
PresetFn = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class EffectDef:
    fn: EffectFn
    per_player: bool          # False: runs once at the point (spawn, noise, movement of the owner)
    who: str                  # default player set when the step names none


EFFECTS: dict[str, EffectDef] = {}
TRIGGERS: dict[str, TriggerFn] = {}
TARGETS: dict[str, TargetFn] = {}
WHO: dict[str, WhoFn] = {}
PRESETS: dict[str, PresetFn] = {}
PASSIVE_TRIGGERS: dict[str, Callable[..., Any]] = {}


def _register(table: dict[str, Any], name: str, value: Any) -> None:
    if name in table:
        warnings.warn(f"Kit: '{name}' registered twice; the later one wins.")
    table[name] = value


def effect(name: str, per_player: bool = True, who: str = "enemies") -> Callable[[EffectFn], EffectFn]:
    def wrap(fn: EffectFn) -> EffectFn:
        _register(EFFECTS, name, EffectDef(fn, per_player, who))
        return fn
    return wrap


def trigger(name: str) -> Callable[[TriggerFn], TriggerFn]:
    def wrap(fn: TriggerFn) -> TriggerFn:
        _register(TRIGGERS, name, fn)
        return fn
    return wrap


def target(name: str) -> Callable[[TargetFn], TargetFn]:
    def wrap(fn: TargetFn) -> TargetFn:
        _register(TARGETS, name, fn)
        return fn
    return wrap


def who(name: str) -> Callable[[WhoFn], WhoFn]:
    def wrap(fn: WhoFn) -> WhoFn:
        _register(WHO, name, fn)
        return fn
    return wrap


def preset(name: str) -> Callable[[PresetFn], PresetFn]:
    def wrap(fn: PresetFn) -> PresetFn:
        _register(PRESETS, name, fn)
        return fn
    return wrap


def passive_trigger(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def wrap(fn: Callable[..., Any]) -> Callable[..., Any]:
        _register(PASSIVE_TRIGGERS, name, fn)
        return fn
    return wrap
