"""Breach's wall charges and seismic lines."""
from __future__ import annotations

from gameplay.geometry import angle_diff, angle_of, heading
from gameplay.kit import statuses
from gameplay.kit.dsl import knock_up, on, push, status, thing
from gameplay.kit.engine import place
from gameplay.kit.registry import effect, target


@target("wall_exit")
def wall_exit(match, player, spec):
    """Resolve the far face of the first wall, including contiguous pieces of that wall."""
    aim = heading(player.facing)
    hits = []
    for wall in match.combat_walls():
        if wall.low or wall.buy_phase_only or wall.top <= player.level or not match.wall_active(wall):
            continue
        if wall.on_deck and wall.base > player.level:
            continue
        interval = wall.rect.ray_interval(player.pos, aim)
        if interval is not None and interval[1] > 0:
            hits.append(interval)
    if not hits:
        return None
    hits.sort()
    entry, exit_at = hits[0]
    if entry > spec["range"]:
        return None
    for next_entry, next_exit in hits[1:]:
        if next_entry > exit_at + 1e-6:
            break
        exit_at = max(exit_at, next_exit)
    if exit_at - entry > spec["wall_depth"]:
        return None
    point = player.pos + aim * (exit_at + 0.05)
    return point if 0 < point.x < match.world.width and 0 < point.y < match.world.height else None


@effect("breach_flash")
def breach_flash(ctx, player, spec):
    if player is None:
        return
    angle = abs(angle_diff(player.facing, angle_of(ctx.point - player.pos)))
    # Val2d approximation of the brief off-screen flash documented in Riot 1.07.
    minimum = 0.25
    strength = max(0.0, 1.0 - angle / 90.0)
    duration = minimum + strength * (float(spec["seconds"]) - minimum)
    statuses.apply_status(ctx.m, player, "blind", duration)


@effect("seismic_wave", per_player=False)
def seismic_wave(ctx, _target, spec):
    start = float(ctx.ability["wave_start"])
    end = max(float(ctx.ability.get("min_range", start)), (ctx.point - ctx.source).length())
    width = float(ctx.ability["width"])
    segments = int(spec.get("segments", 1))
    length = (end - start) / segments
    steps = [status("concuss", spec["concuss"])]
    if "knockback" in spec:
        steps += [knock_up(4.2), push(spec["knockback"], along_aim=True)]
    trigger = on("start", steps, who="others", area="strip", width=width, once_per_player=True)
    hit = set()
    for segment in range(segments):
        origin = ctx.source + ctx.aim * (start + segment * length)
        section = place(ctx, thing("zone", lasts=0.17, shape="line", along=True, forward=True,
                                   delay=spec["windup"] + segment * float(spec.get("interval", 0)),
                                   length=length, radius=width / 2, triggers=[trigger]), origin)
        section.data[f"hit:{id(trigger)}"] = hit
