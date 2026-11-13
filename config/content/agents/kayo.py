from gameplay.kit.dsl import ability, agent, event, on, spawn, step, thing


def flash(fuse):
    return thing("flash", lasts=fuse, thrown=True, sprite="kayo_flash", radius=0.3,
                 triggers=[on("expire", [step("kayo_flash"), event("flash", radius=35)],
                              who="everyone", radius=35, sight="all")])


AGENT = agent(
    "KAY/O", role="Initiator", order=9, sprites={"ability_poses": True},
    C=ability("FRAG/ment", target="throw", price=200, range=22, radius=4, preview="zone",
              landing_preview=True, bot="offense", sound="cast_throw_light",
              desc="Throw a fragment that deals four pulses of damage through terrain. Right click lobs.",
              place=thing("blast", lasts=0.55, thrown=True, sprite="kayo_frag",
                          triggers=[on("expire", [spawn(thing("zone", delay=0.5, lasts=4, radius=4, sprite="kayo_field",
                              triggers=[on("every", [step("kayo_frag"), step("kayo_frag_cover"), event("blast")], offset=0, seconds=1,
                                           count=4, who="everyone")]))])]),
              alt={"name": "Short lob", "range": 8, "throw_factor": 0.45}),
    Q=ability("FLASH/drive", target="throw", price=250, max=2, range=24, preview="flash",
              sound="cast_throw_light", bot="offense", desc="Throw a flash. Right click for a short, faster underhand throw.",
              place=flash(1.6), alt={"name": "Underhand flash", "range": 9, "throw_factor": 0.45, "place": flash(1)}),
    E=ability("ZERO/point", target="throw", start=1, recharge=50, range=26, radius=15,
              preview="zone", landing_preview=True, bot="offense", sound="cast_throw_light",
              desc="Throw a destructible blade that identifies and suppresses enemies through terrain for eight seconds.",
              place=thing("blast", lasts=0.45, thrown=True, sprite="kayo_knife",
                          triggers=[on("expire", [spawn(thing("sensor", lasts=1, radius=0.4, hp=20, hit_radius=0.4,
                              sprite="kayo_knife", triggers=[on("expire", [step("kayo_suppress", radius=15, seconds=8)])]))])])),
    X=ability("NULL/cmd", target="self", cost=8, bot="buff",
              cast_radius=0, cast_announcement={"ally": "cast_tech", "enemy": "cast_electric"},
              desc="Overload with Combat Stim and five suppression pulses. If downed, an ally can hold interact to stabilize you.",
              do=[step("kayo_overload"), step("sound", key="cast_charge_up", radius=30, at_owner=True)]),
)
