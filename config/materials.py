"""Map materials of Val2d. Edit freely; maps refer to these keys.

Walls in a map file:  {"rect": [x0, y0, x1, y1], "mat": "brick"}   (pen/sight/height may still be given per wall)
Floors in a map file: "floor": "concrete" (whole map) and "floors": [{"rect": [...], "mat": "grate"}, ...]

WALLS fields:
  tile    image under assets/ (32x32 = 2 m, tiled)
  pen     penetration level: 0 thin, 1 medium, 2 thick, 3 impenetrable
  sight   True = blocks sight
  height  levels: 2 = full wall, 1 = crate/low cover you can climb onto
FLOORS: key -> tile image.
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
