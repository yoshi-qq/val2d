from gameplay.kit.dsl import ability, agent, on, step, thing

AGENT = agent(
    "Fade", role="Initiator", order=13, sprites={"ability_poses": True},
    C=ability("Prowler", target="self", preview="sensor", radius=15, aim_cone=100, price=250, max=2,
              bot="offense", sound="cast_dark",
              desc="Send a Prowler that follows Terror Trails or chases visible enemies. Hold fire to steer before it locks on.",
              do=[step("fade_prowl")]),
    Q=ability("Seize", target="throw", range=24, radius=6.58, preview="zone", price=200, bot="offense",
              landing_preview=True, instant_with_status="fade_seize_air", free_with_status="fade_seize_air",
              desc="Throw a knot that tethers, deafens and decays enemies. Press Q again to drop it early.",
              do=[step("fade_throw", mode="seize")]),
    E=ability("Haunt", target="throw", range=25, radius=30, preview="zone", start=1, recharge=50, bot="offense",
              landing_preview=True, instant_with_status="fade_haunt_air", free_with_status="fade_haunt_air",
              desc="Throw a destroyable watcher that reveals visible enemies and marks their trails. Press E again to drop it early.",
              do=[step("fade_throw", mode="haunt")]),
    X=ability("Nightfall", target="self", preview="wave", length=40, width=20, cost=8, bot="offense", sound="cast_dark",
              desc="Send a wave through terrain that marks, deafens and decays enemies.",
              place=thing("zone", shape="line", length=40, along=True, forward=True, radius=10,
                          delay=0.6, lasts=3.3, status_hint="fade_nightfall",
                          triggers=[on("tick", [step("fade_wave")])])),
)
