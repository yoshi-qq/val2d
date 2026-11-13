from gameplay.kit.dsl import ability, agent, damage, on, sound, spawn, step, thing

MOSH = thing("zone", lasts=3.35, radius=6.2, sprite="gekko_pit", triggers=[
    on("every", [damage(1, cover_mult=0.5)], offset=0.1, seconds=0.1, count=30, who="everyone", sight="walls"),
    on("every", [step("gekko_mosh_hit")], offset=3, seconds=0.1, count=3, who="everyone", sight="walls"),
    on("every", [sound("ab_blast")], offset=3, seconds=1, count=1),
    on("expire", [step("gekko_globule")]),
])

AGENT = agent(
    "Gekko", role="Initiator", order=5, sprites={"ability_poses": True},
    C=ability("Mosh Pit", target="throw", price=250, range=22, radius=6.2, preview="zone",
              landing_preview=True, bot="offense", sound="cast_throw_light",
              desc="Throw Mosh into a damaging pool that bursts after three seconds. Right click lobs it.",
              place=thing("blast", lasts=0.55, thrown=True, sprite="gekko_mosh",
                          triggers=[on("expire", [spawn(MOSH)])]),
              alt={"name": "Short lob", "range": 8, "throw_factor": 0.45}),
    Q=ability("Wingman", target="self", price=300, preview="zone", bot="offense", sound="cast_deploy",
              desc="Send Wingman to chase and concuss. Aim at a site with the Spike, or at the planted Spike on defense, and right click to plant or defuse.",
              do=[step("gekko_wingman")],
              alt={"name": "Plant or defuse", "target": "gekko_spike", "do": [step("gekko_wingman", objective=True)]}),
    E=ability("Dizzy", target="throw", start=1, range=18, preview="zone", bot="offense", sound="cast_throw_light",
              desc="Throw Dizzy to splash visible enemies with blinding plasma. Hold interact near a globule to reclaim it.",
              do=[step("gekko_dizzy")]),
    X=ability("Thrash", target="self", cost=8, max=1, preview="zone", free_with_status="gekko_thrash_ready",
              sound="cast_deploy",
              desc="Guide Thrash with your aim. Hold back to stop, fire to lunge and fire again to detonate. Press X to cancel. Reclaim once per round.",
              do=[step("gekko_thrash")]),
)
