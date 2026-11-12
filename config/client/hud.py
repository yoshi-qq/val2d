"""HUD layout. Edit freely; read when the game starts. Most of the HUD sits at the bottom and the sides, so the
view ahead (the upper middle of the screen) stays free."""

HUD = {
    "minimap_radius": 104,       # pixels
    "minimap_meters": 46.0,      # metres across the minimap
    "minimap_rotate": True,      # True: turns with you (ahead is up, like the view); False: north up
    "sound_circle_seconds": 0.8, # how long the own noise circle stays on the minimap
    "feed_seconds": 5.0,
    "help_key": "f1",            # hold for ability descriptions
}
