from gameplay.data import WeaponDef
from gameplay.kit.dsl import ability, agent, on, preset, spawn, thing

# Val2d controls and depth-based hit zones, using Blade Storm's five knives and damage values.
BLADES = WeaponDef(key="blade_storm", name="Blade Storm", slot="sidearm", price=0, auto=False,
                   rate=3.5, mag=5, reserve=0, reload=0, equip=0.35, speed_mod=1, penetration=-1,
                   pellets=1, range=35, damage=((35, 150, 50, int(50 * 0.85)),), spread_first=0, spread_run=0,
                   spray_step=0, spray_max=0, spray_recovery=0)

AGENT = agent("Jett", role="Duelist", order=-6, sprites={"ability_poses": True},
    C=ability("Cloudburst", target="throw", price=200, max=2, range=20, preview="smoke", bot="place",
              place=thing("blast", lasts=0.28, thrown=True, sprite="jett_cloudburst",
                          triggers=[on("expire", [spawn(thing("smoke", lasts=2.5, radius=3,
                                                              sprite="jett_cloudburst"))])])),
    Q=preset("hop", "Updraft", price=150, velocity=9),
    E=preset("dash", "Tailwind", start=1, distance=9, duration=0.22, kills_to_recharge=2,
             arm_delay=1, arm_duration=7.5, desc="Press once to prepare. Press again to dash."),
    X=ability("Blade Storm", target="self", cost=8, blade_weapon=BLADES, fan_degrees=8, bot="buff",
              desc="Left click throws one knife. Right click throws all remaining knives. Single-knife kills refill the set."),
)

# 9.10: holding jump can only glide while Jett can use abilities. Fall speed is tuned for Val2d's vertical scale.
AGENT["drift_fall_speed"] = 2.0
