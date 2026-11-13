from gameplay.kit.dsl import ability, agent, step

AGENT = agent(
    "Hush", role="Duelist", order=22, sprites={"ability_poses": True},
    C=ability("Flow", target="aim", range=10, price=200, sound="cast_wind",
              desc="Set an anchor and propel toward it after a brief delay. Hover briefly if airborne.",
              do=[step("hush_flow")]),
    Q=ability("Flashbulb", target="self", preview="wave", length=18, width=4, price=250, max=2,
              alt={"prepare": True}, instant_with_status="hush_flash", free_with_status="hush_flash",
              desc="Throw a flash or right-click to prepare it. Press Q again to redirect it.",
              do=[step("hush_projectile", mode="flash")]),
    E=ability("Displacement", target="self", preview="wave", length=18, width=4, start=1, kills_to_recharge=2,
              alt={"prepare": True}, instant_with_status="hush_pull", free_with_status="hush_pull",
              desc="Throw or prepare an orb. Recast to redirect it. The burst pulls players and concusses on collision.",
              do=[step("hush_projectile", mode="pull")]),
    X=ability("Suspension", target="self", cost=8, free_with_status="hush_ult",
              desc="Prepare a steerable orb. Fire to launch. Press X or fire again to lift players around it.",
              do=[step("hush_projectile", mode="ult")]),
)

AGENT["interact_bonus"] = 2.5
