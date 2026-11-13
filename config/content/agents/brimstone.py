from gameplay.kit.dsl import ability, agent, dps, on, spawn, status, step, thing

SMOKE_RADIUS = 3.0  # Legacy baseline. The active 13.10 balance patch applies Riot's 8.09 radius.

AGENT = agent("Brimstone", role="Controller", order=-8, sprites={"ability_poses": True},
    C=ability("Stim Beacon", target="throw", price=200, range=8, preview="zone", landing_preview=True,
              radius=3.5, bot="buff",
              place=thing("blast", lasts=0.45, thrown=True, sprite="brimstone_stim_beacon",
                          triggers=[on("expire", [spawn(thing("zone", lasts=12, radius=3.5,
                              sprite="brimstone_stim_field", triggers=[on("tick", [
                                  status("stim", 2), status("haste", 2)], who="team")]))])])),
    Q=ability("Incendiary", target="throw", price=250, range=22, preview="zone", landing_preview=True,
              radius=3.2, bot="offense",
              place=thing("blast", lasts=0.75, thrown=True, sprite="brimstone_incendiary_grenade",
                          triggers=[on("expire", [spawn(thing("zone", lasts=7, radius=3.2,
                              sprite="brimstone_incendiary_burning",
                                  # 9.03: ground fire must not hurt players through solid walls.
                                  triggers=[on("tick", [dps(60, cover_mult=0.5)], who="everyone", sight="walls")]))])])), 
    E=ability("Sky Smoke", target="aim_free", price=100, max=3, start=1, range=55, tactical=True, multi=3,
              preview="smoke", radius=SMOKE_RADIUS, bot="place",
              place=thing("smoke", delay=0.65, lasts=19.25, radius=SMOKE_RADIUS, sprite="brimstone_sky_smoke",
                          warning_sprite="brimstone_sky_smoke_forming",
                          fade_sound={"key": "cast_whoosh", "lead": 1.5, "radius": 12.5})),
    X=ability("Orbital Strike", target="aim_free", cost=8, range=65, tactical=True, preview="zone", radius=6, bot="offense",
              cast_radius=0, cast_announcement={"ally": "cast_tech", "enemy": "cast_beam"},
              do=[step("sound", key="cast_charge_up", radius=28, range_filtered=True)],
              place=thing("zone", delay=1.5, lasts=3, radius=6, sprite="brimstone_orbital_strike_beam",
                          sprite_width=64, warning_sprite="brimstone_orbital_strike_targeting",
                          triggers=[on("start", [step("sound", key="ab_blast", radius=28, range_filtered=True)]),
                                    on("tick", [dps(120, cover_mult=1)], who="everyone")])),
)
