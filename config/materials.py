"""Map materials of Val2d. Edit freely; maps refer to these keys.

Walls in a map file:  {"rect": [x0, y0, x1, y1], "mat": "brick"}   (pen/sight/height may still be given per wall)
Floors in a map file: "floor": "concrete" (whole map) and "floors": [{"rect": [...], "mat": "grate"}, ...]

WALLS fields:
  tile    image under assets/ (32x32 = 2 m, tiled)
  pen     penetration level: 0 thin, 1 medium, 2 thick, 3 impenetrable
  sight   True = blocks sight
  height  levels: 2 = full wall, 1 = crate/low cover you can climb onto
FLOORS: key -> tile image.
OBJECTS (map file: "objects": [{"key": "barrel", "pos": [x, y], "rot": 0}] or with "rect" instead of "pos"):
  tile     image under assets/; size  (w, h) in metres at rot 0; rot in 90° steps
  blocks   blocks movement and bullets; pen, sight, height as for walls
  frames, fps   animation strip (optional); tiled  repeat over the rect instead of stretching
  buy_phase_only  blocks only during the buy phase (spawn barrier)
DECALS (map file: "decals": [{"key": "crack", "rect": [...]}] or {"key": "arrow", "pos": [x, y], "rot": 90}):
  tile, size (w, h) metres, tiled; never block, drawn under objects and figures.
Source: own design by Claude Code, 12.11.2026; tiles by the design session (docs/SPRITES.md).
"""

WALLS: dict[str, dict] = {
    "concrete": dict(tile="maps/common/wall_concrete.png", pen=3, sight=True, height=2),
    "brick": dict(tile="maps/common/wall_brick.png", pen=2, sight=True, height=2),
    "wood_fence": dict(tile="maps/common/fence_wood.png", pen=0, sight=True, height=2),
    "glass": dict(tile="maps/common/window_glass.png", pen=0, sight=False, height=2),
    "crate_metal": dict(tile="maps/werkhof/kiste_metall.png", pen=1, sight=False, height=1),
    "werkhof_thick": dict(tile="maps/werkhof/wand.png", pen=2, sight=True, height=2),
    "werkhof_thin": dict(tile="maps/werkhof/wand_duenn.png", pen=0, sight=True, height=2),
}

FLOORS: dict[str, str] = {
    "stone": "maps/werkhof/boden_stein.png",
    "concrete": "maps/common/floor_concrete.png",
    "grate": "maps/common/floor_grate.png",
    "tiles": "maps/common/floor_tiles.png",
    "sand": "maps/common/floor_sand.png",
    "dirt": "maps/common/floor_dirt.png",
    "stone_cracked": "maps/common/floor_stone_cracked.png",
}

OBJECTS: dict[str, dict] = {
    "door": dict(tile="maps/common/door_closed.png", size=(2.0, 2.0), blocks=True, pen=1, sight=True, height=2),
    "spawn_barrier": dict(tile="maps/common/spawn_barrier.png", size=(2.0, 2.0), blocks=True, pen=3, sight=False, height=2,
                          frames=2, fps=4, tiled=True, buy_phase_only=True),
    "barrel": dict(tile="maps/common/props/barrel.png", size=(0.75, 0.75), blocks=True, pen=1, sight=True, height=1),
    "crate_small": dict(tile="maps/common/props/crate_small.png", size=(0.75, 0.75), blocks=True, pen=1, sight=False, height=1),
    "pallet": dict(tile="maps/common/props/pallet.png", size=(1.0, 0.56), blocks=False),
    "cone": dict(tile="maps/common/props/cone.png", size=(0.62, 0.38), blocks=False),
    "plant": dict(tile="maps/common/props/plant.png", size=(0.62, 0.5), blocks=True, pen=0, sight=True, height=1),
    "lamp": dict(tile="maps/common/props/lamp.png", size=(1.0, 1.0), blocks=False),
    "bench": dict(tile="maps/common/props/bench.png", size=(2.0, 0.5), blocks=True, pen=0, sight=False, height=1),
    "debris": dict(tile="maps/common/props/debris.png", size=(0.62, 0.44), blocks=False),
}

DECALS: dict[str, dict] = {
    "crack": dict(tile="maps/common/decals/crack.png", size=(2.0, 2.0)),
    "oil_stain": dict(tile="maps/common/decals/oil_stain.png", size=(2.0, 2.0)),
    "scorch": dict(tile="maps/common/decals/scorch.png", size=(2.0, 2.0)),
    "arrow": dict(tile="maps/common/decals/arrow.png", size=(1.0, 1.0)),
    "drain": dict(tile="maps/common/decals/drain.png", size=(1.0, 0.56)),
    "hazard_stripe": dict(tile="maps/common/decals/hazard_stripe.png", size=(2.0, 0.5), tiled=True),
    "site_a": dict(tile="maps/common/decals/site_a.png", size=(1.0, 1.0)),
    "site_b": dict(tile="maps/common/decals/site_b.png", size=(1.0, 1.0)),
    "site_c": dict(tile="maps/common/decals/site_c.png", size=(1.0, 1.0)),
}
