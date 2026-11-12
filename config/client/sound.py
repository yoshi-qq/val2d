"""How the game client mixes sounds. Edit freely; read when the game starts.

Direction: left/right by panning, front/back by tone (sounds behind you are duller and a little quieter),
through walls by tone and volume. How far a sound carries is a game rule: config/rules/senses.py.
"""

SOUND = {
    "master": 0.8,              # default volume (each player sets their own in the settings)
    "falloff_power": 1.6,       # how fast sounds fade with distance (higher = quieter far away)
    "pan_floor": 0.12,          # share the far ear still gets for a sound fully to one side
    "rear_gain": 0.75,          # volume of a sound straight behind you
    "occluded_gain": 0.55,      # volume through a wall (it is also muffled)
    "muffle_taps": 9,           # strength of the muffling filter for sounds behind you or through walls
    "step_gain": 0.45,          # footsteps
    "channels": 48,
}
