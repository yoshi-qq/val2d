from gameplay.kit.dsl import ability, agent, on, status, step, thing

# 11.08: 25 m at 20 m/s. The transverse size is the existing Val2d adaptation.
PARANOIA_DISTANCE, PARANOIA_SPEED, PARANOIA_RADIUS = 25, 20, 1.35
AGENT = agent("Omen", role="Controller", order=-7, sprites={"ability_poses": True},
    C=ability("Shrouded Step", target="teleport_aim", price=100, max=2, range=15, preview="teleport", bot="place",
              do=[step("channel_teleport", seconds=0.7, sprite="omen_shrouded_step_arrival")]),
    Q=ability("Paranoia", target="self", price=250, preview="wave", range=PARANOIA_DISTANCE,
              length=PARANOIA_DISTANCE, width=2 * PARANOIA_RADIUS, bot="offense",
              place=thing("zone", lasts=PARANOIA_DISTANCE / PARANOIA_SPEED, radius=PARANOIA_RADIUS,
                          move=PARANOIA_SPEED, move_through_walls=True, sprite="omen_paranoia_travel",
                          spawn_ahead=PARANOIA_RADIUS + 0.5,  # 4.04: nearby players beside Omen are outside the spawn.
                          triggers=[on("tick", [status("nearsight", 2.2), status("deaf", 2.2)],
                                       who="others", area="sweep", once_per_player=True)])),
    E=ability("Dark Cover", target="aim_free", price=150, max=2, start=1, recharge=30, range=65, tactical=True,
              preview="smoke", radius=4, bot="place",
              place=thing("smoke", lasts=15, radius=4, sprite="omen_dark_cover_loop",
                          warning_sprite="omen_dark_cover_forming")),
    X=ability("From the Shadows", target="aim_free", cost=7, range=115, global_target=True, tactical=True, radius=0.8,
              preview="teleport", bot="place",
              do=[step("channel_teleport", seconds=2.5, cancel_channel=True, sprite="omen_from_the_shadows")]),
)
