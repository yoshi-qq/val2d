from gameplay.kit.dsl import ability, agent, dps, on, spawn, status, step, thing

AGENT = agent(
    "Viper", role="Controller", order=10, sprites={"ability_poses": True},
    C=ability("Snake Bite", target="throw", range=22, radius=4.5, price=300, preview="zone",
              landing_preview=True, sound="cast_throw_light", bot="offense",
              desc="Launch acid that damages and makes players Vulnerable for two seconds after contact.",
              place=thing("blast", lasts=0.55, thrown=True, sprite="viper_canister", triggers=[
                  on("expire", [spawn(thing("zone", lasts=6.5, radius=4.5, sprite="viper_acid",
                      triggers=[on("tick", [status("viper_vulnerable", 2), dps(12.5, cover_mult=0.5)],
                                   who="everyone", sight="walls")]))]) ])),
    Q=ability("Poison Cloud", target="throw", range=22, radius=4.5, price=200, preview="smoke",
              landing_preview=True, instant_with_status="viper_cloud", free_with_status="viper_cloud",
              desc="Throw an emitter. Press Q again to toggle toxic smoke using shared fuel. Interact nearby during Buy to reclaim it.",
              do=[step("viper_emitter", mode="cloud")],
              alt={"name": "Short lob", "range": 8, "throw_factor": 0.45}),
    E=ability("Toxic Screen", target="self", start=1, preview="wave", length=60, width=1.4,
              instant_with_status="viper_screen", free_with_status="viper_screen",
              desc="Deploy a line of emitters through terrain. Press E again to toggle the toxic screen.",
              do=[step("viper_emitter", mode="screen")]),
    X=ability("Viper's Pit", target="aim", range=7.25, radius=9, cost=9, preview="smoke",
              instant_with_status="viper_pit", free_with_status="viper_pit",
              desc="Deploy a toxic cloud. Return before its integrity expires, or press X again to collapse it.",
              do=[step("viper_pit")]),
)
