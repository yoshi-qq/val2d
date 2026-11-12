# Character views

Brimstone, Omen, Jett, Sova, Sage, Cypher, Phoenix and Killjoy each have back and right-profile sprites under
`assets/agents/{key}/`. The game chooses a view by comparing the agent's facing direction with the camera.

| Figure faces | View | Strip |
| --- | --- | --- |
| Up, away from the camera | Back | `{key}_{state}_back.png` |
| Right | Right profile | `{key}_{state}_side.png` |
| Down, toward the camera | Front | `{key}_{state}.png` |
| Left | Mirrored right profile | `{key}_{state}_side.png` |

The player's own agent appears from behind. Enemy versions add `_enemy` before `.png` and use a red outline.
Forms use their own front strips. Missing views fall back to the front view.

| Priority | States |
| --- | --- |
| 1 | `idle`, `walk`, `crouch`, `crouch_walk` |
| 2 | `jump`, `fall`, `land`, `shoot`, `reload`, `equip`, `flinch`, `melee` |
| 3 | `plant`, `defuse`, `cast_c`, `cast_q`, `cast_e`, `cast_x`, `channel_c`, `channel_q`, `channel_e`, `channel_x`, `cast`, `victory` |

The 768 directional strips retain the front strips' 16×32 cells, frame count and order. Death animations and
screen portraits use their existing views. Held items are rendered separately.

Run `python docs/design/sprites_figure_views.py` to export missing directional strips. Use
`python -m pytest tests/test_sprites.py` to check view selection. In a match, walk away from a teammate and
circle them to see the front, back, and both mirrored profile directions.
