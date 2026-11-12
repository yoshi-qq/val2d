"""Statuses: what each one does while it lasts. Edit freely; a new status is one new entry, no code.

Abilities apply them by name (status effect, `status=` of the presets). Values: estimates by Claude Code,
11.11.2026 (the first ten) and 12.11.2026 (haste and below).

Modifiers (all optional):
  speed, damage_taken, damage_dealt, fire_rate, reload    factors; several statuses multiply
  spread_add                                              extra spread in degrees; several statuses add up
  hp_per_second                                           health per second (negative drains, never below 1 unless lethal)
  sight_range                                             metres the player can still see (smallest counts)
  seen_within                                             enemies see the player only this close (smallest counts)
  blind, deaf, no_abilities, revealed, lethal             switches (True)
  decay, decay_regen                                      health drained per second (never below 1), given back after
  positive                                                a buff: immunity does not block it, cleanse keeps it
  icon, note                                              for the interface and for you
"""

STATUSES = {
    "blind":      dict(blind=True, note="screen goes white, sees no one"),
    "nearsight":  dict(sight_range=5.0),
    "concuss":    dict(speed=0.6, spread_add=6.0),
    "slow":       dict(speed=0.55),
    "vulnerable": dict(damage_taken=1.5),
    "decay":      dict(decay=15.0, decay_regen=10.0),
    "suppress":   dict(no_abilities=True),
    "detain":     dict(speed=0.0),
    "deaf":       dict(deaf=True, note="hears no footsteps"),
    "stim":       dict(fire_rate=1.12, reload=0.8, positive=True),
    # ready for new abilities
    "haste":      dict(speed=1.25, positive=True),
    "cloak":      dict(seen_within=4.0, positive=True),
    "fortify":    dict(damage_taken=0.7, positive=True),
    "empower":    dict(damage_dealt=1.2, positive=True),
    "regen":      dict(hp_per_second=8.0, positive=True),
    "burn":       dict(hp_per_second=-10.0, lethal=True),
    "weaken":     dict(damage_dealt=0.8),
    "marked":     dict(revealed=True),
    "jammed":     dict(no_abilities=True, spread_add=3.0),
}
