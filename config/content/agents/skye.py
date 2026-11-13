from gameplay.kit.dsl import ability, agent, step

AGENT = agent(
    "Skye", role="Initiator", order=8, sprites={"ability_poses": True},
    C=ability("Regrowth", target="self", preview="heal", price=150, radius=18,
              desc="Equip and hold fire to heal visible allies. Release to save the rest of the 100-point pool.",
              free_with_status="skye_heal_pool", do=[step("skye_regrowth")]),
    Q=ability("Trailblazer", target="self", preview="zone", price=300, radius=0.6,
              desc="Send out and steer the tiger. Fire to leap, bite an enemy on contact and concuss nearby players.",
              sound="cast_deploy", do=[step("skye_tiger")]),
    E=ability("Guiding Light", target="self", preview="sensor", radius=36, aim_cone=20,
              price=250, start=1, max=2, recharge=50, bot="offense",
              instant_with_status="skye_hawk", free_with_status="skye_hawk",
              desc="Send a hawk. Hold fire to steer it and press E again to flash. It also flashes on expiry.",
              do=[step("skye_hawk")]),
    X=ability("Seekers", target="self", cost=8, sound="cast_deploy",
              desc="Send up to three destroyable Seekers after different enemies. Contact nearsights and slows.",
              do=[step("skye_seekers")]),
)
