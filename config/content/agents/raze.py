from gameplay.kit.dsl import ability, agent, on, step, thing

AGENT = agent(
    "Raze", role="Duelist", order=7, sprites={"ability_poses": True},
    C=ability("Boom Bot", target="self", price=300, preview="sensor", radius=15, aim_cone=110,
              sound="cast_deploy", bot="offense",
              desc="Deploy a bouncing bot that chases visible enemies and explodes when it reaches them.",
              do=[step("raze_bot")]),
    Q=ability("Blast Pack", target="throw", price=200, max=2, range=9, throw_factor=0.85,
              free_with_status="raze_pack_active", sound="cast_throw_light",
              desc="Press Q to toss a pack and press it again to detonate. It launches you and damages enemies once armed.",
              do=[step("raze_pack")]),
    E=ability("Paint Shells", target="throw", range=24, radius=5.5, preview="zone", landing_preview=True,
              start=1, kills_to_recharge=2, sound="cast_throw_light", bot="offense",
              desc="Throw a grenade that bursts into four smaller grenades. Right click lobs. Recharges after two kills.",
              place=thing("blast", lasts=2.25, radius=5.5, thrown=True, sprite="raze_grenade",
                          triggers=[on("expire", [step("raze_cluster")])]),
              alt={"name": "Short lob", "range": 10, "throw_factor": 0.45}),
    X=ability("Showstopper", target="self", cost=8, sound="cast_charge_up",
              desc="Equip a one-shot rocket launcher for ten seconds. Left click fires after the 1.4-second equip.",
              do=[step("raze_showstopper")]),
)
