from gameplay.kit.dsl import ability, agent, step

AGENT = agent(
    "Astra", role="Controller", order=21, sprites={"ability_poses": True},
    C=ability("Gravity Well", target="astra_star", always_available=True, requires_target=True,
              desc="Activate a star to pull players inward, then make them vulnerable.",
              do=[step("astra_activate", mode="well")]),
    Q=ability("Nova Pulse", target="astra_star", always_available=True, requires_target=True,
              desc="Activate a star to concuss players after a short windup.",
              do=[step("astra_activate", mode="nova")]),
    E=ability("Nebula / Dissipate", target="astra_star", price=150, max=5, start=1,
              always_available=True, requires_target=True,
              desc="Activate a star as smoke. Interact with a star to recall it. Purchased charges are stars.",
              do=[step("astra_activate", mode="smoke")]),
    X=ability("Astral Form / Cosmic Divide", target="aim_free", tactical=True, tactical_line=True, astral_form=True,
              global_target=True, range=300, radius=1, width=1, length=300, multi=2, cost=7,
              desc="Open Astral Form to place stars anywhere. Right-click to aim Cosmic Divide.",
              do=[step("astra_divide")]),
)
