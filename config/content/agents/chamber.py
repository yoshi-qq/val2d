from gameplay.data import WeaponDef
from gameplay.kit.dsl import ability, agent, on, step, thing

HEADHUNTER = WeaponDef(
    "headhunter", "Headhunter", "ability", 0, False, 4, 8, 0, 0, 0.3, 1, 2, 1, 120,
    ((120, 159, 55, 46),), 0.25, 3, 0.6, 2.75, 5,
    category="sidearm", alt=(("kind", "zoom"), ("factor", 1.5), ("spread_mult", 0.1)),
)
TOUR_DE_FORCE = WeaponDef(
    "tour_de_force", "Tour De Force", "ability", 0, False, 0.9, 5, 0, 0, 0.667, 0.8, 2, 1, 120,
    ((120, 255, 150, 127),), 0, 10, 0, 0, 5,
    category="sniper", alt=(("kind", "zoom"), ("scope", True), ("levels", (2.5, 5.0)),
                            ("spread_mult", 0.05), ("unscope_after_shot", True)),
    spread_unscoped=5,
)

AGENT = agent(
    "Chamber", role="Sentinel", order=6, sprites={"ability_poses": True},
    passives=[on("chamber_tour_kill", [step("chamber_tour_field")])],
    C=ability("Trademark", target="chamber_ground", range=12, radius=10, price=200, preview="sensor",
              bot="place", sound="cast_place_trap",
              desc="Place a trap that tracks visible enemies and creates a slowing field. Aim at it and interact to recall.",
              place=thing("sensor", delay=2, lasts=300, radius=10, hp=20, hit_radius=0.32, owner_range=50,
                          reactivate=2, recall_recharge=30, sprite="chamber_trademark",
                          warning_sprite="chamber_trademark", triggers=[on("tick", [step("chamber_trademark")])])),
    Q=ability("Headhunter", target="self", price=100, max=8, ability_weapon=HEADHUNTER, weapon_charge_ammo=True,
              shop_name="Q Headhunter round", sound="cast_tech",
              desc="Equip or holster a heavy pistol. Buy up to eight rounds at 100 credits each. Right click aims."),
    E=ability("Rendezvous", target="chamber_ground", range=8.5, radius=18, preview="teleport", start=1,
              instant_with_status="chamber_anchor", free_with_status="chamber_anchor", sound="",
              desc="Place a destructible anchor. Press E again while grounded within 18 m to teleport. Aim at it and interact to recall.",
              do=[step("chamber_rendezvous")]),
    X=ability("Tour De Force", target="self", cost=8, ability_weapon=TOUR_DE_FORCE, weapon_summon_time=2.3,
              weapon_ammo_status="chamber_tour_ammo",
              weapon_empty_equip=1.0, sound="cast_tech",
              desc="Summon or holster a five-round sniper rifle. Kills leave a slowing field. Right click cycles two zoom levels."),
)
