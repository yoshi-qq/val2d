from gameplay.kit.dsl import ability, agent, on, spawn, status, step, thing

# 11.08: each segment fortifies to 600 HP after 2 s. Existing Val2d footprint.
barrier = step("barrier", blocks=4, length=7.5, width=1, hp=400, fortified_hp=600, fortify_after=2,
               duration=30, sprite="sage_barrier_block")

AGENT = agent("Sage", role="Sentinel", order=-4, sprites={"ability_poses": True},
    C=ability("Barrier Orb", price=400, range=6, preview="wall", bot="place", do=[barrier],
              alt={"name": "Rotate wall", "do": [{**barrier, "along": True}]}),
    Q=ability("Slow Orb", target="throw", price=200, max=2, range=20, preview="zone", radius=4, bot="place",
              place=thing("blast", lasts=0.5, thrown=True, sprite="sage_slow_projectile",
                          triggers=[on("expire", [spawn(thing("zone", lasts=7, radius=4,
                              sprite="sage_slow_field", triggers=[on("tick", [status("sage_slow", 0.25)],
                                                                    who="everyone")]))])])),
    E=ability("Healing Orb", target="aim_ally", start=1, recharge=45, range=15, require_sight=True,
              preview="heal", bot="heal", injured=True, cursor_radius=0.75,
              do=[step("heal", who="cursor_ally", amount=100, over=5, require_sight=True, required=True)],
              alt={"name": "Heal yourself", "target": "self",
                   # 13.00: self heal 100 HP. 9.10: same duration as ally heal.
                   "do": [step("heal", who="self", amount=100, over=5, injured=True, required=True)]}),
    X=ability("Resurrection", target="aim_fallen", range=6, require_sight=True, cost=8, preview="revive",
              do=[step("revive", who="cursor_fallen", required=True, require_sight=True,
                       delay=2.0, sprite="sage_resurrection")]),
)
