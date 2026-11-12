"""Ability library: ready-made abilities any agent can use with library("name", ...overrides) in its file.
Values: estimates by Claude Code, 12.11.2026. Edit freely, or add more files with an ABILITIES dict.
Cast sounds ("sound"): any cast_* sound in assets/sounds (list in docs/MODDING.md).
"""
from gameplay.kit.dsl import (ability, damage, dps, event, heal, on, preset, pull, push, reveal, shield, status, step,
                              thing)

ABILITIES = {
    # -------------------------------------------------------------- classics as presets with a fitting sound
    "smoke_orb": preset("smoke", "Smoke Orb", price=200, max=2, range=30.0, radius=2.8, duration=15.0, sound="cast_deploy"),
    "flashbang": preset("flash", "Flashbang", price=250, max=2, range=14.0, fuse=0.5, blind=1.5, cone=120.0,
                        sound="cast_throw_light"),
    "healing_orb": preset("heal", "Healing Orb", price=0, max=1, start=1, amount=60, duration=4.0, range=12.0,
                          recharge=40.0, sound="cast_heal"),
    "recon_dart": preset("sensor", "Recon Dart", price=0, max=1, start=1, range=30.0, radius=8.0, duration=4.0, pulse=1.0,
                         recharge=40.0, sound="cast_tech"),
    "tripwire": preset("tripwire", "Tripwire", price=200, max=2, length=6.0, duration=120.0, status="detain",
                       status_time=2.0, sound="cast_place_trap"),
    "sonic_pulse": preset("wave", "Sonic Pulse", price=250, max=1, length=14.0, width=3.0, damage=0, status="concuss",
                          status_time=2.0, sound="cast_sonic"),
    "earth_wall": preset("wall", "Earth Wall", price=300, max=1, range=20.0, length=12.0, duration=12.0, sound="cast_earth"),
    "poison_cloud": preset("zone", "Poison Cloud", price=200, max=1, range=18.0, radius=3.0, duration=7.0, status="decay",
                           status_time=1.0, sound="cast_poison"),
    # -------------------------------------------------------------- compositions with newer effects and statuses
    "firebomb": ability(
        "Firebomb", price=200, max=1, target="aim", range=14.0, preview="zone", bot="offense", sound="cast_fire",
        desc="Throws a firebomb that bursts and leaves a burning patch for 4 s.",
        place=thing("blast", lasts=0.8, radius=3.0, thrown=True, triggers=[
            on("expire", who="enemies", sight="walls", do=[damage(40, falloff=0.5), event("blast"), step("sound", key="cast_fire"),
                                                            step("spawn", place=thing("zone", lasts=4.0, radius=3.0, triggers=[
                                                                on("tick", who="enemies", do=[dps(20), status("burn", 0.5)])]))]),
        ])),
    "knockback_blast": ability(
        "Knockback", price=200, max=2, target="aim", range=12.0, preview="blast", bot="offense", sound="cast_burst",
        desc="A charge that bursts after half a second, hits for 20 and throws enemies 3 m away.",
        place=thing("blast", lasts=0.5, radius=3.0, thrown=True, triggers=[
            on("expire", who="enemies", sight="walls", do=[damage(20), push(3.0), event("blast")])])),
    "gravity_well": ability(
        "Gravity Well", price=250, max=1, target="aim", range=20.0, preview="zone", bot="offense", sound="cast_dark",
        desc="A field for 3 s that pulls enemies to its centre and slows them.",
        place=thing("zone", lasts=3.0, radius=4.0, triggers=[
            on("tick", who="enemies", do=[pull(0.12), status("slow", 0.3)])])),
    "frost_field": ability(
        "Frost Field", price=200, max=1, target="aim", range=18.0, preview="zone", bot="offense", sound="cast_ice",
        desc="Freezes the ground for 6 s: enemies inside are slowed and take 4 damage per second.",
        place=thing("zone", lasts=6.0, radius=3.5, triggers=[on("tick", who="enemies", do=[status("slow", 0.5), dps(4)])])),
    "shock_dart": ability(
        "Shock Dart", price=250, max=1, target="aim", range=16.0, preview="blast", bot="offense", sound="cast_electric",
        desc="A dart that sparks after 0.6 s: 30 damage and no abilities (jammed) for 3 s.",
        place=thing("blast", lasts=0.6, radius=2.5, thrown=True, triggers=[
            on("expire", who="enemies", sight="walls", do=[damage(30), status("jammed", 3.0), event("blast")])])),
    "cloak_step": ability(
        "Cloak Step", price=0, max=1, start=1, target="self", bot="escape", sound="cast_wind", recharge=35.0,
        desc="A short dash; enemies see you only within 4 m for 3 s.",
        do=[step("dash", distance=5.0, duration=0.2), status("cloak", 3.0, who="self")]),
    "haste_aura": ability(
        "Haste Aura", price=200, max=1, target="self", bot="buff", sound="cast_buff",
        desc="You and allies within 6 m run faster for 6 s.",
        do=[status("haste", 6.0, who="team", radius=6.0)]),
    "fortify_self": ability(
        "Fortify", price=150, max=1, target="self", bot="buff", sound="cast_shield_up",
        desc="25 armor and a third less damage taken for 6 s.",
        do=[shield(25, who="self"), status("fortify", 6.0, who="self")]),
    "marked_shot": ability(
        "Marking Shot", cost=7, target="ahead", range=40.0, preview="wave", bot="offense", sound="cast_beam",
        desc="A 40 m beam through walls: enemies hit are marked (visible to everyone) for 4 s.",
        do=[reveal(4.0, who="enemies", area="beam", length=40.0, width=1.5),
            status("marked", 4.0, who="enemies", area="beam", length=40.0, width=1.5)]),
    "healing_rain": ability(
        "Healing Rain", cost=7, target="aim", range=25.0, preview="zone", bot="heal", sound="cast_magic",
        desc="A 6 m area for 8 s that heals allies 15 per second.",
        place=thing("zone", lasts=8.0, radius=6.0, triggers=[on("tick", who="team", do=[step("heal_rate", per_second=15.0)])])),
}
