from gameplay.kit.dsl import ability, agent, on, status, step, thing

AGENT = agent(
    "Iso", role="Duelist", order=17, sprites={"ability_poses": True},
    C=ability("Contingency", target="self", preview="wave", length=32.5, width=8, price=200,
              aim_equip=0.8, bot="offense", sound="cast_arcane", alt={"slow_wall": True},
              desc="Send an indestructible moving screen that stops bullets. Right-click sends it at half speed.",
              do=[step("iso_screen")]),
    Q=ability("Undercut", target="self", preview="wave", length=34.875, width=6, price=300,
              aim_equip=0.8, bot="offense", sound="cast_dark",
              desc="Fire a bolt through terrain that suppresses and makes players vulnerable for four seconds.",
              place=thing("zone", lasts=1.55, radius=3, move=22.5, move_through_walls=True, sprite="iso_bolt",
                          triggers=[on("tick", [status("suppress", 4), status("iso_vulnerable", 4)],
                                       who="others", area="sweep", once_per_player=True)])),
    E=ability("Double Tap", target="self", start=1, bot="offense", sound="cast_charge_up",
              desc="Focus for twelve seconds and block one hit. Shoot energy orbs from kills or assists to refresh the shield.",
              do=[step("iso_focus")]),
    X=ability("Kill Contract", target="self", preview="wave", length=36, width=15, cost=7,
              aim_equip=1.1, bot="offense", sound="cast_dark",
              desc="Capture the first enemy in the column and fight them in an isolated arena.",
              place=thing("zone", shape="line", along=True, forward=True, length=36, radius=7.5,
                          delay=0.9, lasts=0.2, sprite="iso_column",
                          triggers=[on("start", [step("iso_capture")])])),
)
