"""Example of a new mechanic without touching the game code: every file here is loaded at start.

Registers the effect "swap" (trade places with the target player) and the trigger "low_light"
(fires for players of the set standing inside the area while they are not moving).
Use them in an agent like any built-in: step("swap", who="enemies", first=True) or on("low_light", do=[...]).
"""
from gameplay.kit.builtins import select
from gameplay.kit.registry import effect, trigger


@effect("swap")
def swap(ctx, target, step):
    """Owner and target trade places."""
    if ctx.owner is None or target is None:
        return
    ctx.owner.pos, target.pos = target.pos, ctx.owner.pos


@trigger("low_light")
def low_light(ctx, spec):
    """Players of the set inside the area who stand still."""
    still = [t for t in select(ctx, spec) if t.vel.length() < 0.3]
    return still or None
