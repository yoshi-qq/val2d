from gameplay.kit.dsl import ability, agent, step

AGENT = agent(
    "Yoru", role="Duelist", order=12, sprites={"ability_poses": True},
    C=ability("Fakeout", target="self", price=200, preview="zone", radius=0.5, bot="offense",
              desc="Send a moving clone. Right click to leave a marker, then aim at it and interact to activate. Enemy fire triggers its flash.",
              do=[step("yoru_clone")], alt={"name": "Place marker", "do": [step("yoru_clone", marker=True)]}),
    Q=ability("Blindside", target="self", price=250, preview="flash", radius=0.5, bot="offense",
              desc="Bounce a fragment off terrain. It flashes anyone looking at it after a short fuse.",
              do=[step("yoru_blindside")]),
    E=ability("Gatecrash", target="self", start=1, max=2, price=150, kills_to_recharge=2,
              instant_with_status="yoru_gate", free_with_status="yoru_gate",
              desc="Send a moving tether or right click to place it. Press E to teleport, or aim at the tether and interact to fake.",
              do=[step("yoru_gate")], alt={"name": "Stationary tether", "do": [step("yoru_gate", stationary=True)]}),
    X=ability("Dimensional Drift", target="self", cost=8, preview="zone", radius=0.5,
              instant_with_status="yoru_drift", free_with_status="yoru_drift",
              desc="Enter the rift for ten seconds. Press X again to leave early.",
              do=[step("yoru_drift")]),
)
