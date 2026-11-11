"""Weapons and armor of Val2d. Edit the values here; the game reads this file at start.

Sources:
- PRICE and MAG: Christian's weapon overview (waffen_uebersicht.md, as of 11.11.2026, prices "approx.").
- Everything else (damage, fire rate, spread, reload, speed, range): own estimate by Claude Code,
  11.11.2026, not taken from any official data. Tune freely.

Units: metres, seconds, shots per second, degrees, credits.
Fields per weapon:
  name           shown in the buy menu and HUD
  slot           "sidearm", "primary" or "melee"
  price, mag     credits, rounds per magazine
  reserve        spare rounds
  auto           True = hold to fire
  rate           shots per second
  rate_ramp      optional (max_rate, seconds): fire rate climbs to max_rate while holding fire
  reload, equip  seconds
  speed_mod      running speed factor while holding the weapon
  penetration    0 low, 1 medium, 2 high (wall materials 0 thin, 1 medium, 2 thick, 3 impenetrable)
  pellets        projectiles per shot (shotguns), or rounds per burst if burst=True
  burst          True = one trigger pull fires `pellets` rounds in quick succession
  silenced       True = quieter shots, no muzzle flash for others
  range          metres
  damage         list of steps (up_to_metres, head, body, legs)
  spread_first   spread of the first shot after a pause (0 = exact)
  spread_run     extra spread at full running speed
  spray          (increase per follow-up shot, cap, recovery per second)
"""

WEAPONS: dict[str, dict] = {
    # ---------------------------------------------------------------- melee
    "messer": dict(name="Knife", slot="melee", price=0, mag=0, reserve=0, auto=True, rate=1.6, reload=0, equip=0.5,
                   speed_mod=1.0, penetration=0, pellets=1, range=2.0, damage=[(2, 75, 50, 50)],
                   spread_first=0, spread_run=0, spray=(0, 0, 0)),
    # ---------------------------------------------------------------- sidearms
    "spatz": dict(name="Sparrow", slot="sidearm", price=0, mag=12, reserve=36, auto=False, rate=6.5, reload=1.75,
                  equip=0.75, speed_mod=1.0, penetration=0, pellets=1, range=60,
                  damage=[(30, 78, 26, 22), (60, 66, 22, 18)], spread_first=0.4, spread_run=2.6, spray=(0.9, 4.0, 6.0)),
    "stachel": dict(name="Thorn", slot="sidearm", price=300, mag=2, reserve=10, auto=False, rate=3.0, reload=1.8,
                    equip=0.75, speed_mod=1.0, penetration=0, pellets=8, range=15,
                    damage=[(6, 30, 15, 12), (15, 10, 5, 4)], spread_first=3.4, spread_run=3.4, spray=(0, 3.4, 0)),
    "hornisse": dict(name="Hornet", slot="sidearm", price=450, mag=13, reserve=39, auto=True, rate=10.0, reload=1.5,
                     equip=0.75, speed_mod=1.0, penetration=0, pellets=1, range=50,
                     damage=[(20, 70, 24, 20), (50, 56, 19, 16)], spread_first=0.6, spread_run=1.4, spray=(0.55, 5.0, 8.0)),
    "lynx": dict(name="Lynx", slot="sidearm", price=500, mag=15, reserve=45, auto=False, rate=6.8, reload=1.6,
                 equip=0.75, speed_mod=1.0, penetration=0, pellets=1, range=60, silenced=True,
                 damage=[(30, 105, 30, 26), (60, 88, 25, 21)], spread_first=0.25, spread_run=2.4, spray=(0.7, 3.5, 7.0)),
    "kite": dict(name="Kite", slot="sidearm", price=600, mag=8, reserve=24, auto=False, rate=4.5, reload=1.9,
                 equip=0.8, speed_mod=1.0, penetration=1, pellets=1, range=60,
                 damage=[(25, 152, 42, 36), (60, 118, 35, 30)], spread_first=0.2, spread_run=3.0, spray=(1.1, 4.0, 5.0)),
    "bulle": dict(name="Bull", slot="sidearm", price=800, mag=6, reserve=24, auto=False, rate=2.2, reload=2.2,
                  equip=1.0, speed_mod=1.0, penetration=1, pellets=1, range=60,
                  damage=[(30, 155, 52, 44), (60, 140, 46, 39)], spread_first=0.2, spread_run=3.8, spray=(1.6, 5.0, 4.0)),
    # ---------------------------------------------------------------- submachine guns
    "wespe": dict(name="Wasp", slot="primary", price=1100, mag=20, reserve=60, auto=True, rate=16.0, reload=2.0,
                  equip=0.75, speed_mod=0.95, penetration=0, pellets=1, range=50,
                  damage=[(15, 64, 26, 21), (50, 54, 22, 18)], spread_first=0.6, spread_run=1.6, spray=(0.35, 4.5, 8.0)),
    "sirene": dict(name="Siren", slot="primary", price=1600, mag=30, reserve=90, auto=True, rate=13.0, reload=2.2,
                   equip=0.75, speed_mod=0.95, penetration=0, pellets=1, range=50, silenced=True,
                   damage=[(20, 76, 26, 22), (50, 62, 21, 18)], spread_first=0.35, spread_run=1.2, spray=(0.28, 3.8, 9.0)),
    # ---------------------------------------------------------------- shotguns
    "brecher": dict(name="Breaker", slot="primary", price=850, mag=5, reserve=10, auto=False, rate=1.1, reload=2.6,
                    equip=1.0, speed_mod=0.92, penetration=0, pellets=12, range=20,
                    damage=[(8, 28, 15, 12), (20, 9, 5, 4)], spread_first=2.6, spread_run=2.6, spray=(0, 2.6, 0)),
    "faecher": dict(name="Fan", slot="primary", price=1850, mag=7, reserve=14, auto=True, rate=3.5, reload=2.8,
                    equip=1.0, speed_mod=0.92, penetration=0, pellets=8, range=18,
                    damage=[(8, 24, 12, 10), (18, 8, 5, 4)], spread_first=3.4, spread_run=3.4, spray=(0, 3.4, 0)),
    # ---------------------------------------------------------------- rifles
    "falke": dict(name="Falcon", slot="primary", price=2050, mag=24, reserve=48, auto=True, rate=9.5, reload=2.4,
                  equip=1.0, speed_mod=0.9, penetration=1, pellets=1, range=60,
                  damage=[(60, 115, 35, 30)], spread_first=0.3, spread_run=4.0, spray=(0.45, 4.0, 7.0)),
    "lanze": dict(name="Lance", slot="primary", price=2250, mag=12, reserve=36, auto=False, rate=4.5, reload=2.6,
                  equip=1.0, speed_mod=0.9, penetration=2, pellets=1, range=80,
                  damage=[(80, 165, 65, 55)], spread_first=0.1, spread_run=5.0, spray=(0.8, 3.0, 5.0)),
    "speer": dict(name="Spear", slot="primary", price=2900, mag=30, reserve=60, auto=True, rate=11.0, reload=2.5,
                  equip=1.0, speed_mod=0.9, penetration=1, pellets=1, range=60, silenced=True,
                  damage=[(15, 150, 38, 32), (30, 138, 35, 29), (60, 125, 31, 26)],
                  spread_first=0.2, spread_run=4.2, spray=(0.32, 3.6, 8.0)),
    "hammer": dict(name="Hammer", slot="primary", price=2900, mag=25, reserve=50, auto=True, rate=9.5, reload=2.5,
                   equip=1.0, speed_mod=0.9, penetration=1, pellets=1, range=60,
                   damage=[(60, 156, 39, 33)], spread_first=0.25, spread_run=4.5, spray=(0.42, 4.2, 7.0)),
    "heron": dict(name="Heron", slot="primary", price=2900, mag=18, reserve=54, auto=True, rate=7.5, reload=2.6,
                  equip=1.1, speed_mod=0.88, penetration=1, pellets=1, range=80,
                  damage=[(80, 152, 42, 36)], spread_first=0.15, spread_run=4.8, spray=(0.38, 3.2, 6.5)),
    # ---------------------------------------------------------------- sniper rifles
    "elster": dict(name="Magpie", slot="primary", price=950, mag=5, reserve=15, auto=False, rate=1.3, reload=2.4,
                   equip=1.0, speed_mod=0.92, penetration=1, pellets=1, range=80,
                   damage=[(80, 200, 85, 72)], spread_first=0.0, spread_run=5.5, spray=(2.0, 5.5, 3.0)),
    "crane": dict(name="Crane", slot="primary", price=2400, mag=2, reserve=10, auto=False, rate=3.5, reload=3.2,
                  equip=1.1, speed_mod=0.88, penetration=2, pellets=1, range=90,
                  damage=[(90, 238, 140, 119)], spread_first=0.0, spread_run=6.0, spray=(1.5, 4.0, 3.0)),
    "adler": dict(name="Eagle", slot="primary", price=4700, mag=5, reserve=10, auto=False, rate=0.6, reload=3.5,
                  equip=1.3, speed_mod=0.85, penetration=2, pellets=1, range=100,
                  damage=[(100, 255, 150, 127)], spread_first=0.0, spread_run=7.0, spray=(3.0, 7.0, 2.0)),
    # ---------------------------------------------------------------- heavy weapons
    "muehle": dict(name="Mill", slot="primary", price=1600, mag=50, reserve=100, auto=True, rate=10.0, rate_ramp=(13.0, 1.0),
                   reload=3.2, equip=1.25, speed_mod=0.85, penetration=2, pellets=1, range=50,
                   damage=[(30, 110, 34, 29), (50, 100, 31, 26)], spread_first=0.8, spread_run=5.0, spray=(0.3, 5.0, 6.0)),
    "walze": dict(name="Roller", slot="primary", price=3200, mag=100, reserve=200, auto=True, rate=12.0, rate_ramp=(18.0, 1.5),
                  reload=4.5, equip=1.25, speed_mod=0.82, penetration=2, pellets=1, range=50,
                  damage=[(30, 95, 29, 25), (50, 88, 27, 23)], spread_first=1.0, spread_run=5.5, spray=(0.25, 4.8, 5.0)),
}

ARMOR: dict[str, dict] = {
    "leicht": dict(name="Light Vest", price=400, points=25),
    "schwer": dict(name="Heavy Vest", price=1000, points=50),
}
