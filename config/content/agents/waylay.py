from gameplay.kit.dsl import ability, agent, on, sound, spawn, status, step, thing

SATURATE_RADIUS = 6
PATH_WIDTH = 13.5
PATH_LENGTH = 36
PATH_START = 3

SATURATE_FIELD = thing(
    "zone", delay=0.6, lasts=0.18, radius=SATURATE_RADIUS, sprite="waylay_saturate_field",
    warning_sprite="waylay_saturate_field",
    triggers=[on("start", [step("waylay_hinder", seconds=3), sound("cast_burst", radius=28)],
                 who="everyone", sight="walls")],
)

AGENT = agent(
    "Waylay", role="Duelist", order=4, sprites={"ability_poses": True},
    C=ability("Saturate", target="throw", price=300, range=22, radius=SATURATE_RADIUS,
              preview="zone", landing_preview=True, bot="offense", sound="cast_throw_light",
              desc="Throw a light cluster. After landing, it bursts and hinders nearby players for 3 seconds.",
              do=[step("waylay_equip_lock", seconds=0.3)],
              place=thing("blast", lasts=0.55, thrown=True, sprite="waylay_saturate",
                          triggers=[on("expire", [spawn(SATURATE_FIELD)])])),
    Q=ability("Lightspeed", target="self", price=300, sound="ab_dash",
              desc="Left click dashes twice. Right click dashes once. Jump as you cast to launch the first dash upward.",
              do=[step("waylay_lightspeed", count=2)],
              alt={"name": "Dash once", "do": [step("waylay_lightspeed", count=1)]}),
    E=ability("Refract", target="self", start=1, kills_to_recharge=2, free_with_status="waylay_refract_ready",
              sound="cast_arcane",
              desc="Press E to place a beacon. After 1 second, press E again within 8 seconds to return as intangible light. Recharges after two kills.",
              do=[step("waylay_refract")]),
    X=ability("Convergent Paths", target="self", cost=8, preview="wave", wave_start=PATH_START,
              length=PATH_START + PATH_LENGTH, width=PATH_WIDTH,
              cast_radius=0, cast_announcement={"ally": "cast_buff", "enemy": "cast_beam"},
              desc="Project an expanding beam that hinders other players for 6 seconds and gives you 10% haste for 7 seconds.",
              do=[step("waylay_convergent_paths"),
                  step("sound", key="cast_charge_up", radius=30, at_owner=True)],
              place=thing("zone", shape="line", along=True, forward=True, spawn_ahead=PATH_START,
                          delay=1, lasts=0.51, length=PATH_LENGTH, radius=PATH_WIDTH / 2,
                          status_hint="waylay_hinder",
                          triggers=[
                              on("start", [status("waylay_haste", 7, who="self"),
                                           step("sound", key="ab_wave", radius=50, range_filtered=True)]),
                              on("waylay_expanding_strip", [step("waylay_hinder", seconds=6)], once_per_player=True),
                          ])),
)
