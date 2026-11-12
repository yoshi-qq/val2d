from gameplay.kit.dsl import ability, agent, damage, on, reveal, spawn, thing

AGENT = agent("Sova", role="Initiator", order=-5, sprites={"ability_poses": True},
    C=ability("Owl Drone", target="self", price=400, bot="place",
              place=thing("sensor", lasts=7, radius=8, move=4, sprite="sova_owl_drone",
                          triggers=[on("every", [reveal(2)], seconds=1.4, sight="walls", first=True)])),
    Q=ability("Shock Bolt", target="throw", price=150, max=2, range=28, preview="blast", radius=4, bot="offense",
              place=thing("blast", lasts=0.55, radius=4, thrown=True, sprite="sova_shock_bolt",
                          triggers=[on("expire", [damage(75, falloff=0.8, cover_mult=1)], who="everyone", sight="walls")])),
    E=ability("Recon Bolt", target="throw", max=1, start=1, recharge=40, range=30, preview="sensor", radius=12,
              bot="place",
              place=thing("blast", lasts=0.6, thrown=True, sprite="sova_recon_bolt",
                          triggers=[on("expire", [spawn(thing("sensor", lasts=3.2, radius=12,
                              # 5.12: 20 HP. 7.04: two scans, timed from impact.
                              hp=20, hit_radius=0.24, sprite="sova_recon_bolt",
                              triggers=[on("every", [reveal(1.2)], offset=0.67, seconds=1.6,
                                           count=2, sight="walls")]))])])), 
    X=ability("Hunter's Fury", target="self", cost=8, preview="wave", length=45, width=1.6, bot="offense",
              repeat_shots=3, repeat_window=6.5, repeat_delay=0.9,
              do=[spawn(thing("zone", delay=0.7, lasts=0.22, shape="line", along=True,
                              length=45, forward=True, radius=0.8, sprite="sova_hunters_fury",
                              triggers=[on("start", [damage(80, cover_mult=1, cover_through_walls=True), reveal(1.2)], who="enemies",
                                           area="beam", length=45, width=1.6)]))]),
)
