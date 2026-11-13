from gameplay.kit.dsl import ability, agent, on, step, thing

AGENT = agent(
    "Vyse", role="Sentinel", order=16, sprites={"ability_poses": True},
    C=ability("Razorvine", target="throw", preview="zone", radius=6.25, range=25, price=150, max=2,
              landing_preview=True, bot="place", sound="cast_throw_light",
              desc="Throw a hidden nest. Aim at it and interact to activate vines that hurt moving players.",
              place=thing("blast", lasts=0.65, thrown=True, sprite="vyse_nest",
                          triggers=[on("expire", [step("vyse_nest")])])),
    Q=ability("Shear", target="aim", preview="sensor", range=15, price=200, bot="place", sound="cast_deploy",
              desc="Place a hidden wall trap. When an enemy enters and leaves its trigger zone, the wall rises.",
              do=[step("vyse_shear")]),
    E=ability("Arc Rose", target="aim", preview="sensor", range=20, start=1, bot="place", aim_equip=0.8,
              alt={"through_surface": True}, instant_with_status="vyse_rose_ready", free_with_status="vyse_rose_ready",
              desc="Place a rose on a surface. Right-click places it on the far side. Press E again to flash or interact to recall.",
              do=[step("vyse_rose")]),
    X=ability("Steel Garden", target="self", preview="zone", radius=28, cost=8, aim_equip=0.7,
              bot="offense", sound="cast_charge_up",
              desc="After a windup, jam enemy primary weapons in the area for eight seconds.",
              place=thing("zone", delay=4.4, lasts=0.4, radius=28, sprite="vyse_garden", warning_sprite="vyse_garden",
                          triggers=[on("start", [step("vyse_jam")], who="enemies")])),
)
