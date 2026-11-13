"""Iso's shield, energy orbs, moving screen and isolated duel."""
from gameplay.geometry import Rect, Vec
from gameplay.kit import statuses
from gameplay.kit.builtins import e_sound, reequip_weapon, select
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place
from gameplay.kit.registry import Ctx, MATCH_TICKS, effect


@effect("iso_screen", per_player=False)
def screen(ctx, _target, _spec):
    wall = place(ctx, thing("wall", delay=0.4, lasts=5, spawn_ahead=5, sprite="iso_screen",
                            triggers=[on("tick", [step("iso_screen_move")])]), ctx.source)
    side = ctx.aim.rotated(90) * 4
    wall.a, wall.b = wall.pos - side, wall.pos + side
    wall.props["bullet_screen"] = True


@effect("iso_screen_move", per_player=False)
def screen_move(ctx, _target, _spec):
    wall = ctx.obj
    offset = ctx.aim * ((2.75 if ctx.ability.get("slow_wall") else 5.5) * ctx.dt)
    wall.pos, wall.a, wall.b = wall.pos + offset, wall.a + offset, wall.b + offset
    wall.props["source_level"] = ctx.m.world.floor_level(wall.pos, wall.props["source_level"] + 1)


@effect("iso_focus", per_player=False)
def focus(ctx, _target, _spec):
    ctx.owner.equip_until = ctx.m.time + 1
    ctx.owner.reload_until = ctx.owner.burst_left = 0
    statuses.apply_status(ctx.m, ctx.owner, "iso_focusing", 1)
    place(ctx, thing("zone", delay=1, lasts=0.05, sprite="iso_shield",
                     triggers=[on("start", [step("iso_refresh")])]), ctx.source).props["hidden"] = "all"


@effect("iso_refresh", per_player=False)
def refresh(ctx, _target, _spec):
    if ctx.owner is not None and ctx.owner.alive:
        statuses.apply_status(ctx.m, ctx.owner, "iso_flow", 12)
        statuses.apply_status(ctx.m, ctx.owner, "iso_shield", 12)
        e_sound(ctx, None, {"key": "cast_shield_up", "at_owner": True, "radius": 16})


def create_orbs(match):
    for event in list(match.events):
        if event.kind != "kill":
            continue
        victim = match.players.get(event.data["pid"])
        if victim is None:
            continue
        for iso in match.players.values():
            if (iso.agent != "iso" or not iso.alive or iso.team == victim.team
                    or iso.duel_id != victim.duel_id or not statuses.has(match, iso, "iso_flow")):
                continue
            if event.data.get("by") != iso.pid and match.round_damage.get((iso.pid, victim.pid), [0])[0] <= 0:
                continue
            ctx = Ctx(match, iso, iso.team, victim.pos, iso.pos, Vec(0, 1), key="E")
            orb = place(ctx, thing("sensor", lasts=3, radius=0.45, hp=1, hit_radius=0.45,
                                   friendly_fire=True, sprite="iso_orb", on_remove="iso_orb_hit"), victim.pos)
            orb.props.update(source_level=victim.level, duel_id=iso.duel_id)


@effect("iso_orb_hit", per_player=False)
def orb_hit(ctx, _target, spec):
    if spec["reason"] == "destroy" and ctx.obj.data.get("last_attacker") == ctx.obj.owner:
        refresh(ctx, None, {})


@effect("iso_capture", per_player=False)
def capture(ctx, _target, _spec):
    match, iso = ctx.m, ctx.owner
    if iso is None or not iso.alive or iso.dm_ghost or iso.duel_id:
        return
    candidates = [p for p in select(ctx, {"area": "strip", "width": 15})
                  if not p.duel_id and p.immune_until <= match.time and not statuses.flag(match, p, "intangible")]
    enemy = min(candidates, key=lambda p: ((p.pos - ctx.source).length(), p.pid), default=None)
    if enemy is None:
        return
    center = Vec(match.world.width + 48, iso.pid * 48)
    bounds = Rect(center.x - 9, center.y - 15, center.x + 9, center.y + 15)
    for player, sign in ((iso, -1), (enemy, 1)):
        if match.spike_carrier == player.pid:
            match.spike_carrier = None
            match.spike_pos, match.spike_ground = player.pos, match.world.ground_height(player.pos, player.level)
        player.passive_state["iso_return"] = (
            player.pos, player.facing, player.ground, player.level, player.hp, player.hp_frac,
            player.armor, player.armor_reserve, player.overheal, player.overheal_until,
            {slot: (weapon, weapon.mag, weapon.reserve) for slot, weapon in player.weapons.items()
             if not weapon.from_station},
        )
        marker = place(ctx, thing("zone", lasts=17, radius=0.7, sprite="iso_marker"), player.pos)
        marker.data["contract_owner"] = iso.pid
        player.duel_id = iso.pid
        player.duel_bounds = bounds
        player.pos, player.facing = center + Vec(0, sign * 10.5), 0 if sign < 0 else 180
        player.vel, player.ground, player.level, player.z, player.vz = Vec(0, 0), 0, 0, 0, 0
        player.zipline = None
        player.hp, player.hp_frac = match._hp, 0
        player.overheal, player.overheal_until = 0, 0
        player.armor = match.armor[player.armor_key].points if player.armor_key in match.armor else 0
        player.spike_equipped = player.defusing = player.blades_equipped = False
        player.plant_progress = player.defuse_progress = player.dash_until = 0
        player.channel_until = player.equip_until = match.time + 2
        player.next_shot = player.spray = player.tagged_until = 0
        player.zoom_level, player.zoomed = 0, False
        player.reload_until = player.burst_left = 0
        for weapon in player.weapons.values():
            definition = match.weapons[weapon.key]
            if not weapon.from_station and weapon.key not in match.ability_weapons:
                weapon.mag = definition.mag
        statuses.apply_status(match, player, "iso_duel_lock", 15)
    statuses.apply_status(match, iso, "iso_flow", 17)
    iso.passive_state["iso_contract"] = (enemy.pid, match.time + 15)
    for offset, width in ((Vec(0, 7), 5), (Vec(-5.5, -7), 4), (Vec(5.5, -7), 4)):
        wall = place(ctx, thing("wall", lasts=4.5, sprite="iso_screen"), center + offset)
        wall.a, wall.b = wall.pos - Vec(width / 2, 0), wall.pos + Vec(width / 2, 0)
        wall.props.update(duel_id=iso.pid, bullet_screen=True)


def restore(match, player):
    record = player.passive_state.pop("iso_return", None)
    player.duel_id, player.duel_bounds = 0, None
    if record is None:
        return
    (player.pos, player.facing, player.ground, player.level, hp, fraction, armor, reserve,
     overheal, overheal_until, ammunition) = record
    player.vel, player.z, player.vz = Vec(0, 0), 0, 0
    player.channel_until = 0
    player.status.pop("iso_duel_lock", None)
    if player.alive:
        reequip_weapon(match, player)
        player.hp, player.hp_frac, player.armor, player.armor_reserve = hp, fraction, armor, reserve
        player.overheal, player.overheal_until = overheal, overheal_until
        for slot, (weapon, mag, ammo) in ammunition.items():
            if player.weapons.get(slot) is weapon:
                weapon.mag, weapon.reserve = mag, ammo


def tick(match, _commands, _dt):
    create_orbs(match)
    for obj in match.effects:
        owner_id = obj.props.get("duel_id") or obj.data.get("contract_owner")
        if owner_id and owner_id not in match.players:
            obj.props["ended"] = True
    for player in match.players.values():
        if player.duel_id and player.duel_id not in match.players:
            restore(match, player)
    for iso in list(match.players.values()):
        contract = iso.passive_state.get("iso_contract")
        if contract is None:
            continue
        enemy = match.players.get(contract[0])
        fighters = [p for p in (iso, enemy) if p is not None]
        survivors = [p for p in fighters if p.alive]
        if len(survivors) == 2 and match.time < contract[1]:
            continue
        if len(survivors) == 1 and enemy is not None:
            return_at = iso.passive_state.setdefault("iso_return_at", match.time + 2)
            if match.time < return_at:
                continue
        if len(survivors) == 2:
            for player in survivors:
                match._kill(None, player, "ability:Kill Contract", "body")
        for player in fighters:
            restore(match, player)
        for obj in match.effects:
            if obj.props.get("duel_id") == iso.pid or obj.data.get("contract_owner") == iso.pid:
                obj.props["ended"] = True
        iso.passive_state.pop("iso_contract", None)
        iso.passive_state.pop("iso_return_at", None)


MATCH_TICKS["iso"] = tick
