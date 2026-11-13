from gameplay.data import WeaponDef
from gameplay.kit.dsl import ability, agent, on, step

BEAM = WeaponDef("neon_beam", "Overdrive", "ability", 0, True, 20, 40, 0, 0, 0.333, 1, -1, 1, 120,
                 ((20, 54, 18, 15), (25, 48, 16, 13), (31, 42, 14, 11),
                  (37, 36, 12, 10), (120, 30, 10, 8)), 0, 7 / 1.5, 0, 0, 5)

AGENT = agent(
    "Neon", role="Duelist", order=11, sprites={"ability_poses": True},
    passives=[on("kill", [step("neon_refill")])],
    C=ability("Fast Lane", target="self", price=300, bot="place", sound="cast_electric",
              desc="Send out two parallel walls of electricity that block vision for four seconds.",
              do=[step("neon_lane")]),
    Q=ability("Relay Bolt", target="self", range=26, price=200, bot="offense", sound="cast_electric",
              desc="Fire a bolt that bounces once, creating a delayed Concuss zone at each impact.",
              do=[step("neon_bolt")]),
    E=ability("High Gear", target="self", start=1, kills_to_recharge=2, always_available=True,
              desc="Press E to toggle sprint. While sprinting, move and right click to spend a slide charge.",
              do=[step("neon_sprint")]),
    X=ability("Overdrive", target="self", cost=8, registered_weapon=BEAM,
              cast_radius=0, cast_announcement={"ally": "cast_electric", "enemy": "cast_burst"},
              desc="Equip a lightning beam, refill Battery and refresh your slide. Enemy kills refill Battery.",
              do=[step("neon_overdrive")]),
)
