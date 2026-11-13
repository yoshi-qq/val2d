"""Viper's emitters, shared fuel and toxin."""
from gameplay.kit import statuses
from gameplay.kit.builtins import select
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place
from gameplay.kit.registry import MATCH_TICKS, effect


@effect("viper_emitter", per_player=False)
def emitter(ctx, _target, spec):
    mode = spec["mode"]
    owner = ctx.owner
    key = f"viper_{mode}"
    device = owner.passive_state.get(key)
    if device is None:
        line = {"shape": "line", "along": True, "forward": True, "length": 60} if mode == "screen" else {}
        device = place(ctx, thing("sensor" if mode == "cloud" else "zone", lasts=3600, radius=0.4,
                                  sprite="viper_emitter", **line),
                       ctx.point if mode == "cloud" else ctx.source)
        owner.passive_state[key] = device
        statuses.apply_status(ctx.m, owner, key, float("inf"))
        return
    if ctx.m.time < device.data.get("ready", 0):
        return False
    active = device.data.get("active")
    if active is not None and not active.props.get("ended"):
        _disable(ctx.m, device)
        return
    if owner.passive_state.get("viper_fuel", 100) < 30:
        return False
    line = {"shape": "line", "along": True, "forward": True, "length": 60} if mode == "screen" else {}
    zone = place(ctx, thing("wall" if line else "smoke", lasts=3600, delay=0.5 if line else 0.75,
                            radius=0.7 if line else 4.5, sprite=key,
                            triggers=[on("tick", [step("viper_toxin")], who="enemies",
                                         **({"area": "strip", "width": 1.4} if line else {}))], **line),
                 device.pos)
    if line:
        zone.a, zone.b = device.a, device.b
    device.data.update(active=zone, ready=zone.start + 2)


def _disable(match, device):
    active = device.data.pop("active", None)
    if active is not None:
        active.props["ended"] = True
    device.data["ready"] = match.time + 5


@effect("viper_toxin")
def toxin(ctx, player, spec):
    if statuses.flag(ctx.m, player, "intangible") or player.immune_until > ctx.m.time:
        return
    if player.passive_state.get("viper_contact_until", 0) < ctx.m.time:
        before = player.hp + player.hp_frac
        after = max(1, before - spec.get("initial", 10))
        player.hp, player.hp_frac = int(after), after - int(after)
        player.decay_pool += before - after
    player.passive_state["viper_contact_until"] = ctx.m.time + max(0.11, 2 * ctx.dt)
    statuses.apply_status(ctx.m, player, "viper_toxin", 0.12)
    statuses.apply_status(ctx.m, player, "viper_decay_hold", 1.5)


@effect("viper_pit", per_player=False)
def pit(ctx, _target, _spec):
    owner = ctx.owner
    if existing := owner.passive_state.get("viper_pit"):
        existing.data.setdefault("collapse_at", ctx.m.time + 1.5)
        return
    cloud = place(ctx, thing("smoke", delay=1, lasts=3600, radius=0.1, sprite="viper_pit",
                             triggers=[on("tick", [step("viper_pit_tick")])]), ctx.point)
    cloud.data["integrity"] = 8.0
    owner.passive_state["viper_pit"] = cloud
    statuses.apply_status(ctx.m, owner, "viper_pit", float("inf"))
    owner.channel_until = cloud.start
    owner.equip_until = cloud.start + 1.35


@effect("viper_pit_tick", per_player=False)
def pit_tick(ctx, _target, _spec):
    obj, match, owner = ctx.obj, ctx.m, ctx.owner
    obj.radius = min(9, 1 + (match.time - obj.start) * 1.6)
    if owner is None:
        obj.props["ended"] = True
        return
    occupants = select(ctx, {"who": "everyone", "radius": obj.radius, "sight": "walls"})
    inside = owner in occupants and owner.alive
    obj.data["integrity"] = min(8, obj.data["integrity"] + (0.32 if inside else -1) * ctx.dt)
    if not owner.alive or obj.data["integrity"] <= 0 or match.time >= obj.data.get("collapse_at", float("inf")):
        _end_pit(owner, obj)
        return
    for player in occupants:
        statuses.apply_status(match, player, "viper_pit_sight", 0.15)
        if player.team != owner.team:
            toxin(ctx, player, {"initial": 30})


def _end_pit(owner, cloud):
    cloud.props["ended"] = True
    owner.passive_state.pop("viper_pit", None)
    owner.status.pop("viper_pit", None)


def tick(match, commands, dt):
    for player in match.players.values():
        if player.agent != "viper":
            continue
        cmd = commands.get(player.pid)
        cloud = player.passive_state.get("viper_cloud")
        if (match.phase == "buy" and cloud is not None and cmd and cmd.interact and player.alive
                and (cloud.pos - player.pos).length() <= 4
                and match._line_clear(player.pos, cloud.pos, player.level, ignore_effects=True)):
            _disable(match, cloud)
            cloud.props["ended"] = True
            player.passive_state.pop("viper_cloud", None)
            player.status.pop("viper_cloud", None)
            player.charges["Q"] = 1
        devices = [player.passive_state.get(f"viper_{mode}") for mode in ("cloud", "screen")]
        active = [e for e in devices if e is not None and e.data.get("active") is not None]
        burning = sum(e.data["active"].start <= match.time for e in active)
        fuel = player.passive_state.get("viper_fuel", 100.0)
        rate = -12.5 if burning == 2 else -100 / 12 if burning else 100 / 30
        fuel = max(0, min(100, fuel + dt * rate))
        player.passive_state["viper_fuel"] = fuel
        if not player.alive or fuel <= 0 or statuses.flag(match, player, "no_abilities"):
            for device in active:
                _disable(match, device)


MATCH_TICKS["viper"] = tick
