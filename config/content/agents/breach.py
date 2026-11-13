from gameplay.kit.dsl import ability, agent, damage, event, on, status, step, thing

# The seismic areas begin 8 m ahead. Range includes that gap.
AFTERSHOCK_RADIUS = 3
SEISMIC_START = 8
FAULT_LINE_MIN, FAULT_LINE_MAX = SEISMIC_START + 8, SEISMIC_START + 56
ROLLING_THUNDER_END = SEISMIC_START + 32

AGENT = agent(
    "Breach", role="Initiator", order=1, sprites={"ability_poses": True},
    C=ability("Aftershock", target="wall_exit", preview="zone", bot="offense", price=200, max=1,
              range=35, wall_depth=10, radius=AFTERSHOCK_RADIUS,
              desc="Fire into a wall to release two delayed bursts on its far side. Each burst deals 80 damage.",
              place=thing("zone", delay=2.2, lasts=0.8, radius=AFTERSHOCK_RADIUS, shape="line", along=True,
                          forward=True, length=10, triggers=[on("every", [damage(80), event("blast")],
                              who="everyone", area="strip", width=2 * AFTERSHOCK_RADIUS,
                              offset=0, seconds=0.6, count=2)])),
    Q=ability("Flashpoint", target="wall_exit", preview="flash", bot="offense", price=250, max=2,
              range=35, wall_depth=10, radius=0.6,
              desc="Fire into a wall to flash players on the far side. Turning away shortens the flash.",
              place=thing("flash", lasts=0.5, radius=0.6, travel_speed=24,
                          triggers=[on("start", [step("sound", key="cast_charge_up", radius=28,
                                                      range_filtered=True)]),
                                    on("expire", [step("breach_flash", seconds=2.25), event("flash")],
                                       who="everyone", radius=28, sight="all")])),
    E=ability("Fault Line", target="aim_free", preview="wave", bot="offense", start=1, recharge=50,
              range=FAULT_LINE_MAX, length=FAULT_LINE_MAX, width=8, wave_start=SEISMIC_START,
              min_range=FAULT_LINE_MIN, charge_time=1,
              desc="Hold fire to extend the quake. Release to concuss players in the line, including through walls.",
              do=[step("seismic_wave", windup=1.1, concuss=2.5)]),
    X=ability("Rolling Thunder", target="ahead", preview="wave", bot="offense", cost=8,
              range=ROLLING_THUNDER_END, length=ROLLING_THUNDER_END, width=18, wave_start=SEISMIC_START,
              cast_radius=0, cast_announcement={"ally": "ult_cast", "enemy": "cast_earth"},
              desc="Send a series of quakes through terrain. Players caught in the wave are concussed and knocked back.",
              do=[step("seismic_wave", windup=1.2, concuss=4, knockback=7, segments=8, interval=0.255)]),
)
