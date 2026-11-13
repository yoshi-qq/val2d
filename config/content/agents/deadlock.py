from gameplay.kit.dsl import ability, agent, on, step, thing

AGENT = agent(
    "Deadlock", role="Sentinel", order=15, sprites={"ability_poses": True},
    C=ability("Barrier Mesh", target="throw", range=20, price=300, radius=10, preview="zone",
              landing_preview=True, bot="place", sound="cast_tech",
              desc="Throw a mesh with destructible nodes. The mesh stops movement and lets bullets through.",
              place=thing("blast", thrown=True, lasts=0.65, sprite="deadlock_mesh",
                          triggers=[on("expire", [step("deadlock_mesh")])])),
    Q=ability("Sonic Sensor", target="aim", range=14, radius=4, preview="sensor", price=200, max=2,
              bot="place", sound="cast_deploy",
              desc="Place a sensor on a wall. Enemy noise triggers a concuss. Aim at it and interact to recall it.",
              do=[step("deadlock_sensor")]),
    E=ability("GravNet", target="throw", range=25, radius=6.5, preview="zone", start=1, recharge=50,
              landing_preview=True, alt={"throw_factor": 0.4, "range": 10}, bot="offense",
              sound="cast_throw_light", desc="Net players on impact, forcing them to crouch. Hold interact to remove the net.",
              place=thing("blast", thrown=True, lasts=0.6, sprite="deadlock_net",
                          triggers=[on("expire", [step("deadlock_net_land")])])),
    X=ability("Annihilation", target="self", cost=7, bot="offense", sound="cast_tech",
              free_with_status="deadlock_accelerator_ready",
              desc="Equip the Nanowire Accelerator for ten seconds. Fire a bouncing pulse that captures the first enemy in a destructible cocoon.",
              do=[step("deadlock_accelerator")]),
)
