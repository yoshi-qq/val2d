from gameplay.kit.dsl import ability, agent, step

AGENT = agent(
    "Tejo", role="Initiator", order=19, sprites={"ability_poses": True},
    C=ability("Stealth Drone", target="self", preview="sensor", radius=16, price=400,
              aim_equip=0.8, sound="cast_deploy",
              desc="Pilot a stealth drone. Fire to reveal and suppress enemies with a pulse. Press C to leave it.",
              do=[step("tejo_drone")]),
    Q=ability("Special Delivery", target="self", preview="wave", length=28, width=3, price=200,
              aim_equip=0.5, bot="offense", alt={"bounce": True}, sound="cast_throw_heavy",
              desc="Launch a sticky grenade that damages and concusses. Right-click to bounce it once.",
              do=[step("tejo_grenade")]),
    E=ability("Guided Salvo", target="aim_free", preview="zone", tactical=True, multi=2, range=45, radius=4.5,
              price=150, max=2, start=1, aim_equip=0.7, bot="offense", sound="cast_tech",
              desc="Mark up to two missile targets and right-click to confirm. Each missile detonates three times.",
              do=[step("tejo_salvo")]),
    X=ability("Armageddon", target="aim_free", preview="zone", tactical=True, tactical_line=True,
              multi=2, range=52.5, length=32, width=12, radius=6, cost=9, aim_equip=0.6,
              bot="offense", sound="cast_charge_up",
              desc="Click to mark the origin and click again to choose the direction of a rolling strike.",
              do=[step("tejo_armageddon")]),
)
