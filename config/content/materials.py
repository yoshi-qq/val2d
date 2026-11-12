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
  door, open_tile  F within reach opens/closes it; open doors block nothing (all doors close at round start)
  trunk    only this share of the size blocks (centred), e.g. trees; sight_only  blocks sight but not movement (bushes)
DECALS (map file: "decals": [{"key": "crack", "rect": [...]}] or {"key": "arrow", "pos": [x, y], "rot": 90}):
  tile, size (w, h) metres, tiled; never block, drawn under objects and figures.
Source: Claude Code, 12.11.2026; tiles by the design session (docs/SPRITES.md).
"""

WALLS: dict[str, dict] = {
    "concrete": dict(tile="maps/common/wall_concrete.png", pen=3, sight=True, height=2),
    "brick": dict(tile="maps/common/wall_brick.png", pen=2, sight=True, height=2),
    "wood_fence": dict(tile="maps/common/fence_wood.png", pen=0, sight=True, height=2),
    "glass": dict(tile="maps/common/window_glass.png", pen=0, sight=False, height=2),
    "crate_metal": dict(tile="maps/werkhof/kiste_metall.png", pen=1, sight=False, height=1),
    "werkhof_thick": dict(tile="maps/werkhof/wand.png", pen=2, sight=True, height=2),
    "werkhof_thin": dict(tile="maps/werkhof/wand_duenn.png", pen=0, sight=True, height=2),
    "metal_sheet": dict(tile="maps/common/wall_metal_sheet.png", pen=1, sight=True, height=2),
    "sandbags": dict(tile="maps/common/wall_sandbags.png", pen=1, sight=False, height=1),
    "stone": dict(tile="maps/common/wall_stone.png", pen=3, sight=True, height=2),
    "container": dict(tile="maps/common/wall_container.png", pen=2, sight=True, height=2),
    "chainlink": dict(tile="maps/common/fence_chainlink.png", pen=0, sight=False, height=2),
    "hedge": dict(tile="maps/common/wall_hedge.png", pen=0, sight=True, height=2),
    "jersey_barrier": dict(tile="maps/common/wall_jersey_barrier.png", pen=2, sight=False, height=1),
    "ascent_stucco": dict(tile="maps/ascent/tiles/stucco.png", pen=2, sight=True, height=2),
    "ascent_brick": dict(tile="maps/ascent/tiles/brick.png", pen=2, sight=True, height=2),
    "ascent_limestone": dict(tile="maps/ascent/tiles/limestone.png", pen=3, sight=True, height=2),
    "ascent_plaster": dict(tile="maps/ascent/tiles/plaster.png", pen=2, sight=True, height=2),
    "ascent_metal": dict(tile="maps/ascent/tiles/metal.png", pen=1, sight=True, height=2),
    "ascent_roof": dict(tile="maps/ascent/tiles/roof.png", pen=3, sight=True, height=2),
}

FLOORS: dict[str, str] = {
    "stone": "maps/werkhof/boden_stein.png",
    "concrete": "maps/common/floor_concrete.png",
    "grate": "maps/common/floor_grate.png",
    "tiles": "maps/common/floor_tiles.png",
    "sand": "maps/common/floor_sand.png",
    "dirt": "maps/common/floor_dirt.png",
    "stone_cracked": "maps/common/floor_stone_cracked.png",
    "asphalt": "maps/common/floor_asphalt.png",
    "metal_plate": "maps/common/floor_metal_plate.png",
    "planks": "maps/common/floor_planks.png",
    "carpet": "maps/common/floor_carpet.png",
    "grass": "maps/common/floor_grass.png",
    "gravel": "maps/common/floor_gravel.png",
    "tiles_dark": "maps/common/floor_tiles_dark.png",
    "cobble": "maps/common/floor_cobble.png",
    "ascent_cobble": "maps/ascent/tiles/cobble.png",
    "ascent_courtyard": "maps/ascent/tiles/courtyard.png",
    "ascent_terracotta": "maps/ascent/tiles/terracotta.png",
    "ascent_market": "maps/ascent/tiles/market.png",
    "ascent_timber": "maps/ascent/tiles/timber.png",
    "ascent_garden": "maps/ascent/tiles/garden.png",
    "ascent_canal": "maps/ascent/tiles/canal.png",
}

OBJECTS: dict[str, dict] = {
    "door": dict(tile="maps/common/door_closed.png", open_tile="maps/common/door_open.png", size=(2.0, 2.0),
                 blocks=True, pen=1, sight=True, height=2, door=True),
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
    "container_large": dict(tile="maps/common/props/container_large.png", size=(6.0, 2.0), blocks=True, pen=2, sight=True, height=2),
    "car": dict(tile="maps/common/props/car.png", size=(4.0, 2.0), blocks=True, pen=1, sight=False, height=1),
    "generator": dict(tile="maps/common/props/generator.png", size=(1.5, 1.0), blocks=True, pen=1, sight=False, height=1),
    "dumpster": dict(tile="maps/common/props/dumpster.png", size=(2.0, 1.25), blocks=True, pen=1, sight=False, height=1),
    "crate_stack": dict(tile="maps/common/props/crate_stack.png", size=(1.5, 1.5), blocks=True, pen=1, sight=True, height=2),
    "vending_machine": dict(tile="maps/common/props/vending_machine.png", size=(1.0, 0.75), blocks=True, pen=1, sight=True, height=2),
    "table": dict(tile="maps/common/props/table.png", size=(1.5, 1.0), blocks=True, pen=0, sight=False, height=1),
    "chair": dict(tile="maps/common/props/chair.png", size=(0.5, 0.5), blocks=False),
    "tree": dict(tile="maps/common/props/tree.png", size=(2.0, 2.0), blocks=True, pen=2, sight=False, height=2, trunk=0.3),
    "bush": dict(tile="maps/common/props/bush.png", size=(1.0, 1.0), blocks=False, sight_only=True),
    "rock": dict(tile="maps/common/props/rock.png", size=(1.0, 0.75), blocks=True, pen=3, sight=False, height=1),
    "pipe": dict(tile="maps/common/props/pipe.png", size=(2.0, 0.5), blocks=True, pen=2, sight=False, height=1),
    "pillar": dict(tile="maps/common/props/pillar.png", size=(1.0, 1.0), blocks=True, pen=3, sight=True, height=2),
    "boxes_cardboard": dict(tile="maps/common/props/boxes_cardboard.png", size=(1.0, 0.75), blocks=True, pen=0, sight=False, height=1),
    "trash_bin": dict(tile="maps/common/props/trash_bin.png", size=(0.5, 0.5), blocks=True, pen=0, sight=False, height=1),
    "ladder": dict(tile="maps/common/props/ladder.png", size=(1.0, 2.0), blocks=False),
    "warning_sign": dict(tile="maps/common/props/warning_sign.png", size=(0.75, 0.75), blocks=False),
    "ascent_radianite_crate": dict(tile="maps/ascent/props/radianite_crate.png", size=(2, 2),
                                   blocks=True, pen=1, sight=False, height=1),
    "ascent_radianite_half": dict(tile="maps/ascent/props/radianite_half.png", size=(1.5, 1.5),
                                  blocks=True, pen=1, sight=False, height=1),
    "ascent_radianite_stack": dict(tile="maps/ascent/props/radianite_stack.png", size=(3, 2.625),
                                   blocks=True, pen=1, sight=True, height=2),
    "ascent_generator": dict(tile="maps/ascent/props/generator.png", size=(3, 1.5),
                              blocks=True, pen=2, sight=True, height=2),
    "ascent_wood_crate": dict(tile="maps/ascent/props/wood_crate.png", size=(1.5, 1.5),
                               blocks=True, pen=0, sight=False, height=1),
    "ascent_boat_crate": dict(tile="maps/ascent/props/boat_crate.png", size=(2, 1.5),
                               blocks=True, pen=0, sight=False, height=1),
    "ascent_site_door": dict(tile="maps/ascent/props/site_door_closed.png",
                            open_tile="maps/ascent/props/site_door_open.png", size=(2.5, 0.5),
                            blocks=True, pen=1, sight=True, height=2, door=True),
    "ascent_site_door_broken": dict(tile="maps/ascent/props/site_door_broken.png", size=(2.5, 0.5)),
    "ascent_door_switch": dict(tile="maps/ascent/props/door_switch.png", size=(0.75, 0.625)),
    "ascent_stone_arch": dict(tile="maps/ascent/props/stone_arch.png", size=(2.5, 0.75)),
    "ascent_market_awning": dict(tile="maps/ascent/props/market_awning.png", size=(3, 1)),
    "ascent_market_stall": dict(tile="maps/ascent/props/market_stall.png", size=(2.5, 1.25),
                                 blocks=True, pen=0, sight=False, height=1),
    "ascent_boathouse_skiff": dict(tile="maps/ascent/props/boathouse_skiff.png", size=(3, 1.5)),
    "ascent_market_sign": dict(tile="maps/ascent/props/market_sign.png", size=(3, 0.875)),
    "ascent_pizza_sign": dict(tile="maps/ascent/props/pizza_sign.png", size=(2.125, 0.875)),
    "ascent_planter": dict(tile="maps/ascent/props/planter.png", size=(2.625, 1),
                            blocks=True, pen=1, sight=False, height=1),
    "ascent_olive_tree": dict(tile="maps/ascent/props/olive_tree.png", size=(2.75, 2.5),
                               blocks=True, pen=2, sight=False, height=2, trunk=0.25),
    "ascent_fountain": dict(tile="maps/ascent/props/fountain.png", size=(2, 2),
                             blocks=True, pen=2, sight=False, height=1),
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
    "puddle": dict(tile="maps/common/decals/puddle.png", size=(2.0, 2.0)),
    "tire_marks": dict(tile="maps/common/decals/tire_marks.png", size=(2.0, 2.0)),
    "paint_line": dict(tile="maps/common/decals/paint_line.png", size=(2.0, 0.25), tiled=True),
    "footprints": dict(tile="maps/common/decals/footprints.png", size=(1.0, 1.0)),
    "grass_tuft": dict(tile="maps/common/decals/grass_tuft.png", size=(0.5, 0.25)),
    "manhole": dict(tile="maps/common/decals/manhole.png", size=(1.0, 1.0)),
    "leaves": dict(tile="maps/common/decals/leaves.png", size=(2.0, 2.0)),
    "paint_x": dict(tile="maps/common/decals/paint_x.png", size=(1.0, 1.0)),
    "ascent_paint_a": dict(tile="maps/ascent/decals/paint_a.png", size=(1, 1)),
    "ascent_paint_b": dict(tile="maps/ascent/decals/paint_b.png", size=(1, 1)),
    "ascent_ivy": dict(tile="maps/ascent/decals/ivy.png", size=(2, 1)),
    "ascent_drain": dict(tile="maps/ascent/decals/drain.png", size=(1, 1)),
    "ascent_site_line": dict(tile="maps/ascent/decals/site_line.png", size=(2, 0.5), tiled=True),
    "ascent_rafters": dict(tile="maps/ascent/tiles/rafters.png", size=(2, 2), tiled=True),
    "ascent_steps": dict(tile="maps/ascent/tiles/steps.png", size=(2, 2), tiled=True),
}
