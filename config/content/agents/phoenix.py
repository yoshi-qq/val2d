from gameplay.kit.dsl import ability, agent, dps, heal, on, preset, spawn, thing

# 9.10: touching either own fire starts a heal that continues after leaving it.
HEAL_FROM_FIRE = heal(50, over=5)

AGENT = agent("Phoenix", role="Duelist", order=-2, sprites={"ability_poses": True},
    C=ability("Blaze", price=150, range=9, preview="wall", length=12, bot="place",
              place=thing("wall", lasts=8, shape="line", length=12, along=True, clip_ends=True,
                          triggers=[on("tick", [dps(30, cover_mult=0.5)], who="others", area="line"),
                                    on("tick", [HEAL_FROM_FIRE], who="self", area="line", once_per_player=True)])),
    Q=ability("Hot Hands", target="throw", price=200, range=17, preview="zone", radius=3.2,
              alt={"name": "Lob", "throw_factor": 0.5}, bot="offense",
              place=thing("blast", lasts=0.45, thrown=True, sprite="phoenix_hot_hands_projectile",
                          triggers=[on("expire", [spawn(thing("zone", lasts=4, radius=3.2,
                              sprite="phoenix_hot_hands_pool", triggers=[
                                  on("tick", [dps(60, cover_mult=0.5)], who="others", sight="walls"),
                                  on("tick", [HEAL_FROM_FIRE], who="self", sight="walls", once_per_player=True)]))])])), 
    E=preset("flash", "Curveball", price=250, max=2, start=1, kills_to_recharge=2,
             range=8, fuse=0.55, blind=1.5, cone=105, curve_angle=-45, desc="Left click curves the flash left.",
             alt={"name": "Curve right", "curve_angle": 45}, sprite="phoenix_curveball"),
    X=ability("Run It Back", target="self", cost=7, bot="buff",
              cast_radius=0, cast_announcement={"ally": "cast_fire", "enemy": "cast_burst"},
              place=thing("zone", lasts=10, radius=0.6, sprite="phoenix_run_it_back_marker", return_on_lethal=True)),
)
