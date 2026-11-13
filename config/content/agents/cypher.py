from gameplay.kit.dsl import ability, agent, damage, on, reveal, spawn, status, step, thing

AGENT = agent("Cypher", role="Sentinel", order=-3, sprites={"ability_poses": True},
    # 5.10 and 5.12: 15 m max length and 20 HP. 11.08 and 13.00: chain, then zap.
    C=ability("Trapwire", price=200, max=2, range=3, preview="wall", length=15, bot="place",
              place=thing("tripwire", lasts=180, shape="line", length=15, clip_ends=True,
                          hp=20, hit_radius=0.24, detect_range=3, recall_recharge=0, owner_range=float("inf"),
                          triggers=[on("tripwire_chain", [damage(5), status("tripwire_slow", 1), reveal(1)],
                                       windup=0.7, break_distance=4, rearm=2, first=True)])),
    Q=ability("Cyber Cage", target="throw", price=100, max=2, range=12, preview="smoke", bot="place",
              place=thing("blast", lasts=0.35, thrown=True, sprite="cypher_cyber_cage_puck",
                          triggers=[on("expire", [spawn(thing("alarm", lasts=180, manual="Cyber Cage",
                              bot_trigger_radius=3.5, sprite="cypher_cyber_cage_puck",
                              triggers=[on("activate", [spawn(thing("smoke", lasts=7.25, radius=3.5,
                                  sprite="cypher_cyber_cage"))])]))])])),
    # 13.10: 20 s on recall, 45 s after destruction.
    E=ability("Spycam", start=1, range=14, preview="sensor", radius=11, bot="place",
              place=thing("sensor", lasts=180, radius=11, hp=1, hit_radius=0.26, destroy_recharge=45,
                          recall_recharge=20, owner_range=float("inf"), hidden="enemies", detect_range=8,
                          sprite="cypher_spycam", device_vision=True,
                          triggers=[on("every", [reveal(1.2)], seconds=3, sight="walls", first=True)])),
    X=ability("Neural Theft", target="enemy_corpse", range=6, cost=7, preview="zone", radius=1, bot="offense",
              cast_radius=0, cast_announcement={"ally": "ab_reveal", "enemy": "cast_place_trap"},
              place=thing("zone", lasts=6.2, sprite="cypher_neural_theft",
                          # 5.10: two reveals, four seconds apart.
                          triggers=[on("every", [step("snapshot", seconds=1.2)], area="everywhere",
                                       offset=2, seconds=4, count=2)])),
)
