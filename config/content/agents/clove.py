from gameplay.kit.dsl import ability, agent, on, step, thing

AGENT = agent(
    "Clove", role="Controller", order=18, sprites={"ability_poses": True},
    C=ability("Pick-me-up", target="self", price=200, sound="cast_buff",
              desc="After a kill or recent damaging assist, gain haste and temporary health.",
              do=[step("clove_pick_me_up")]),
    Q=ability("Meddle", target="throw", range=24, radius=4, price=250, preview="zone",
              landing_preview=True, aim_equip=0.8, bot="offense", sound="cast_throw_light",
              desc="Throw a fragment that bursts after landing and temporarily decays exposed players.",
              place=thing("blast", thrown=True, lasts=0.65, sprite="clove_meddle",
                          triggers=[on("expire", [step("clove_meddle_land")])])),
    E=ability("Ruse", target="aim_free", range=60, dead_range=42.5, radius=4, price=150, max=2,
              start=1, recharge=40, tactical=True, multi=2, cast_while_dead=True,
              aim_equip=0.6, preview="smoke", bot="place", sound="cast_deploy",
              desc="Mark smoke locations on the map and confirm with right-click. After death, cast one shorter smoke at a time.",
              do=[step("clove_smoke")]),
    X=ability("Not Dead Yet", target="self", cost=8, cast_while_dead=True, requires_death=True,
              free_with_status="clove_phase", sound="cast_arcane",
              desc="Revive after death. Secure a kill or damaging assist within ten seconds to stay alive.",
              do=[step("clove_revive")]),
)
