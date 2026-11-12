from gameplay.kit.dsl import ability, agent, damage, dps, on, spawn, status, thing

AGENT = agent("Killjoy", role="Sentinel", order=-1, sprites={"ability_poses": True},
    C=ability("Nanoswarm", target="throw", price=200, max=2, range=16, preview="zone", bot="offense",
              place=thing("blast", lasts=0.7, thrown=True, sprite="killjoy_nanoswarm_grenade",
                          triggers=[on("expire", [spawn(thing("alarm", lasts=180, manual="Nanoswarm",
                              bot_trigger_radius=3.5, sprite="killjoy_nanoswarm_grenade",
                              hp=20, hit_radius=0.24, detect_range=5.25, owner_range=float("inf"),
                              # 13.00: 5 s. 5.12: 20 HP. 6.08: detection at 5.25 m.
                              triggers=[on("activate", [spawn(thing("zone", delay=0.5, lasts=5, radius=3.5,
                                  sprite="killjoy_nanoswarm_field",
                                  triggers=[on("tick", [dps(45, cover_mult=0.5)], who="everyone")]))])]))])])),
    Q=ability("Alarmbot", price=200, range=6, preview="zone", radius=3, bot="place",
              place=thing("alarm", lasts=180, radius=3, sprite="killjoy_alarmbot",
                          hp=20, hit_radius=0.3, detect_range=7, recall_recharge=20, owner_range=40, reactivate=2,
                          # 13.00: +50% pursuit speed. The top-down travel speed is tuned locally.
                          triggers=[on("chase", [status("vulnerable", 4)], sight="walls", speed=7.5,
                                       blast_radius=3, first=True, consume=True)])),
    E=ability("Turret", start=1, range=7, preview="sensor", radius=18, aim_cone=100, bot="place",
              place=thing("sensor", lasts=180, radius=18, sprite="killjoy_turret",
                          hp=100, hit_radius=0.4, destroy_recharge=45, recall_recharge=20,
                          owner_range=40, reactivate=2,
                          # 13.00: +50% fire rate. Val2d still represents the burst with a single hit.
                          triggers=[on("every", [damage(8), status("tripwire_slow", 0.35)],
                                       seconds=0.85 / 1.5, sight="walls", first=True)])), 
    X=ability("Lockdown", target="self", cost=9, bot="offense",
              place=thing("zone", delay=13.15, lasts=0.35, radius=20, sprite="killjoy_lockdown_pulse",
                          hp=200, hit_radius=0.42,
                          warning_sprite="killjoy_lockdown_device",
                          triggers=[on("start", [status("detain", 8)])])),
)
