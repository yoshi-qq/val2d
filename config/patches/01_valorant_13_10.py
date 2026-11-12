"""PC standard-mode balance verified through VALORANT patch 13.10."""

VERSION = "VALORANT 13.10"
NOTES = "Updated the eight playable agent kits against Riot's PC patch notes."

PATCH = {
    "agents": {
        # 4.04 for deploy range, 8.09 for radius (Riot publishes centimetres).
        "brimstone": {"E": {"range": 55, "radius": 4.15, "cast_team_only": True, "cast_radius": 12.5,
                            "place": {"radius": 4.15, "delay": 1}}},
        # 11.08 for Dark Cover recharge. 4.04 for the 64 m/s smoke projectile.
        "omen": {"E": {"recharge": 40, "cast_team_only": True, "cast_radius": 12.5,
                       "place": {"travel_speed": 64}}},
        # 7.04 for the one Updraft charge.
        "jett": {"Q": {"max": 1}},
        # 13.00 for the signature cooldown.
        "sova": {"E": {"recharge": 50}},
        # 11.04 for cast ranges, 11.08 for Barrier price and 9.10 for Resurrection cost.
        "sage": {"C": {"price": 300, "range": 15}, "X": {"range": 12, "cost": 7}},
        # 5.10 for cast range and 9.10 for ultimate cost.
        "cypher": {"X": {"range": 18, "cost": 7}},
        # 11.00 for Curveball windup, 13.02 for Run It Back cost.
        "phoenix": {"E": {"fuse": 0.6}, "X": {"cost": 7}},
    },
    "statuses": {
        # 11.08 and 13.09 for the standardized Brimstone buffs.
        "stim": {"fire_rate": 1.10, "reload": 1 / 1.10, "equip": 1 / 1.10, "recovery": 1.10},
        "haste": {"speed": 1.10},
        # 0.50 and 9.10 for Sage's Slow Orb.
        "sage_slow": {"speed": 0.5, "dash_speed": 0.5, "icon": "slow"},
        "concuss": {"dash_speed": 0.5},
        # 11.08 for the movement penalty while chained.
        "tripwire_slow": {"speed": 0.5, "icon": "slow"},
        "detain": {"no_abilities": True, "no_fire": True, "dash_speed": 0.0},
    },
}
