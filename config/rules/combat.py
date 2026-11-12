"""Health, armor and ultimate points. Estimates by Claude Code, 11.11.2026; units: metres, seconds, credits. Edit freely."""

RULES = {
    'vitals': {'hp': 100, 'armor_absorb': 0.66},
    'ultimate': {'per_kill': 1, 'per_plant': 1, 'per_defuse': 1, 'per_death': 1},
    # throwables (flashes, grenades, target="throw") fly this share of the cursor distance; not shown in game,
    # players learn it. An ability can set its own throw_factor.
    'abilities': {'throw_factor': 0.8},
    # being hit by bullets slows you briefly (tagging); through walls much less
    'tagging': {'slow': 0.725, 'through_walls': 0.25, 'seconds': 0.35},
    # ultimate orbs: points per map (auto between the sites if the map has none), seconds to pick up
    'orbs': {'count': 2, 'pickup_time': 1.0, 'reach': 1.2},
}
