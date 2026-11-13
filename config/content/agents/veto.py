from gameplay.kit.dsl import ability, agent, on, step, thing

AGENT = agent(
    "Veto", role="Sentinel", order=20, sprites={"ability_poses": True},
    C=ability("Crosscut", target="veto_ground", range=20, radius=30, preview="teleport", price=200, max=2,
              aim_equip=0.8, instant_with_status="veto_crosscut_ready", free_with_status="veto_crosscut_ready",
              desc="Place a vortex. Look toward it and press C within 30 meters to teleport. Interact to reclaim it in the buy phase.",
              do=[step("veto_crosscut")]),
    Q=ability("Chokehold", target="throw", range=24, radius=6.58, preview="zone", price=200,
              landing_preview=True, aim_equip=0.8, bot="place", alt={"range": 10, "throw_factor": 0.4},
              sound="cast_throw_light", desc="Throw a hidden snare that tethers, deafens and decays nearby enemies.",
              place=thing("blast", lasts=0.65, thrown=True, sprite="veto_trap",
                          triggers=[on("expire", [step("veto_trap_land")])])),
    E=ability("Interceptor", target="veto_ground", range=7, radius=18, preview="sensor", start=1,
              aim_equip=0.8, instant_with_status="veto_interceptor_ready", free_with_status="veto_interceptor_ready",
              bot="place", desc="Place an Interceptor. Press E again to intercept enemy utility in sight.",
              do=[step("veto_interceptor")]),
    X=ability("Evolution", target="self", cost=7, bot="buff", sound="cast_charge_up",
              desc="Mutate for the rest of the round, gaining regeneration, combat stim and immunity to debuffs and ability damage.",
              do=[step("veto_evolution")]),
)
