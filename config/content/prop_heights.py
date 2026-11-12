"""Real heights of props in metres. Anything lower than head_height in config/rules/senses.py is low cover: players
see and shoot over it (it still blocks walking; jump onto it). Props not listed count as full height.
Estimates by Claude Code, 12.11.2026. Edit freely."""

HEIGHTS = {
    "barrel": 0.9, "crate_small": 0.75, "plant": 0.8, "bench": 0.5, "car": 1.4, "generator": 1.0, "dumpster": 1.3,
    "table": 0.8, "rock": 0.7, "pipe": 0.5, "boxes_cardboard": 0.6, "trash_bin": 0.8, "chair": 0.5, "pallet": 0.15,
    "cone": 0.5, "debris": 0.3,
    "container_large": 2.6, "crate_stack": 2.0, "vending_machine": 1.9, "pillar": 3.0, "tree": 4.0, "door": 2.2,
    "spawn_barrier": 2.5,
}
