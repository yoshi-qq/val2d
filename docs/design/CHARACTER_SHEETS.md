# Character sprite sheets: blueprint

As of 11.11.2026 · design session · binding for every agent sprite, drawn by hand or generated.
Source of truth for states and frame counts: `docs/design/character_sheet_spec.py`.
Templates: `docs/design/templates/`. Check: `python docs/design/check_agent_sprites.py <agent>`.

## 1. Grid and scale

- 16 px = 1 m. An agent is 1 × 2 m, so one frame is **16 × 32 px**.
- The game always draws figures **upright and front-facing**. They never rotate with the world. A short line shows which way the player faces, so there are no left, right or back views.
- Exceptions to the 16 × 32 cell: `dead` 32 × 16, `portrait` 32 × 32, `killfeed` 16 × 16, `select` 32 × 64.
- The **cell centre (8, 16)** is the player's position in the world. Keep the figure centred; do not shift it inside the cell.
- The boots end at **row 30** at the lowest. Row 31 stays free for the outline below the boots.

## 2. Hit zones are drawn widths

The game decides head, body or leg hits from these widths (`config/game_config.json`). The silhouette has to match them, or hits will feel wrong.

| Zone | Columns (x) | Width | Rows (y) |
|---|---|---|---|
| Head | 4–11 | 8 px = 0.50 m | 2–10 |
| Body (torso and arms) | 2–13 | 12 px = 0.75 m | 11–20 |
| Legs | 5–11 | 7 px = 0.44 m | 21–30 |

- Hair, hats and helmets may sit one pixel outside the head columns. The face itself stays inside them.
- Columns 0 and 15 stay empty so the outline fits. Only ability frames (`cast_*`, `channel_*`) may put glow or props there.
- `character_guides.png` shows the zones as coloured columns. Put it on a locked layer called `guides`.

## 3. Look

- **Outline:** one pixel around the silhouette, in a darker shade of the colour it borders (about 45 % brightness). No black outline.
- **Shading:** two steps per material (base and shadow). Light comes from the top left, so shadow goes right and down.
- **Palette:** at most 20 drawn colours per agent across all states. The outline, the enemy variant and glow in ability frames do not count.
- **Reserved colours:** team teal `#4fd6c8` and enemy red `#ee4c4a` stay off large areas. A few pixels as an accent are fine.
- **Team-neutral:** draw one version only. The red enemy outline is generated (section 6).
- **Darkest colour:** around `#16151b`; never pure black.
- **No props that belong to the game:** the weapon in hand, muzzle flash, bomb, ability effects and status icons are drawn by the game on top of the figure. Draw hands and poses, not guns.

## 4. States

One Aseprite **tag** per state. The tag name is the state name. Required states are needed for a playable agent; optional states make it richer, and the game falls back as shown until they exist.

| Group | State | Frames | Speed | Loops | Needed | Falls back to | What it shows |
|---|---|---|---|---|---|---|---|
| Movement | `idle` | 1–4 | 4 fps | yes | **yes** | – | standing; 2–4 frames for breathing |
| | `walk` | 4–6 | 8 fps | yes | **yes** | idle | moving; the game scales the speed with walk and run |
| | `crouch` | 1–2 | 4 fps | yes | **yes** | idle | crouched and still, upper body about 3 px lower |
| | `crouch_walk` | 4 | 6 fps | yes | no | crouch | moving while crouched |
| | `jump` | 1–2 | 8 fps | no | **yes** | idle | rising, legs tucked |
| | `fall` | 1–2 | 8 fps | no | no | jump | falling, dropping a level |
| | `land` | 1–2 | 12 fps | no | no | idle | touch-down, knees bent |
| Combat | `shoot` | 2–3 | 12 fps | no | **yes** | idle | recoil, played once per shot |
| | `reload` | 4–6 | stretched | no | **yes** | idle | hands to the belt and back; stretched to the reload time |
| | `equip` | 2–3 | stretched | no | no | idle | drawing a weapon; stretched to the equip time |
| | `melee` | 3–4 | 12 fps | no | no | shoot | knife slash |
| | `flinch` | 2 | 12 fps | no | no | idle | short hit reaction |
| Bomb | `plant` | 2 | 4 fps | yes | no | crouch | kneeling, hands on the bomb |
| | `defuse` | 2 | 4 fps | yes | no | crouch | kneeling, working on the bomb |
| Abilities | `cast_c` | 3–4 | 8 fps | no | **yes** | cast | own animation for ability C |
| | `cast_q` | 3–4 | 8 fps | no | **yes** | cast | own animation for ability Q |
| | `cast_e` | 3–4 | 8 fps | no | **yes** | cast | own animation for ability E (signature) |
| | `cast_x` | 4–6 | 8 fps | no | **yes** | cast | ultimate; may use the whole cell incl. columns 0 and 15 for glow |
| | `channel_c` … `channel_x` | 2–4 | 6 fps | yes | no | cast_{slot} | held or running version of an ability (aiming, charging, active ultimate) |
| | `cast` | 3 | 8 fps | no | no | idle | shared fallback for older sprites only |
| Death | `dying` | 3–4 | 10 fps | no | no | dead | falling over, ending in the dead pose |
| | `dead` | 1 | still | – | **yes** | – | lying, **32 × 16**, figure turned to the left (head on the left) |
| Screens | `victory` | 2–4 | 4 fps | yes | no | idle | end-of-match pose |
| | `portrait` | 1 | still | – | **yes** | – | head and shoulders, **32 × 32**, background `#272631` |
| | `killfeed` | 1 | still | – | no | portrait | head only, **16 × 16** |
| | `select` | 1 | still | – | no | portrait | large agent-select figure, **32 × 64** |

Every ability has its own animation: `cast_c`, `cast_q`, `cast_e` and `cast_x` are required. They should differ clearly, e.g. throw, place on the ground, gather at the chest, full-body ultimate. If an ability is held or stays active (aiming a wall, a running ultimate), the game loops `channel_{slot}` and falls back to the last frame of `cast_{slot}`.

Required for a playable agent: idle, walk, crouch, jump, shoot, reload, cast_c, cast_q, cast_e, cast_x, dead, portrait. That is 12 states and about 28 frames.

## 5. Special mechanics: extra states, forms, overlays

Some abilities change how an agent moves or looks. There are three building blocks for that. Which ones an agent uses is entered in `config/agents.py` (coding session) and in `docs/SPRITES.md`.

| Building block | File | Size and frames | Falls back to | Use for |
|---|---|---|---|---|
| Extra state | `{key}_mech_{name}.png` | 16 × 32, 1–6 frames, loops | idle | a pose that exists only for this mechanic: gliding, hovering, carrying, riding a dash, stunned in place |
| Form | `{key}@{form}_{state}.png` | like the normal state | the normal state | the whole look changes while something is active (ultimate transformation, disguise, armoured mode). Draw at least `idle` and `walk`; every state you leave out uses the normal sprite |
| Overlay | `{key}_overlay_{name}.png` | 16 × 32, 1 frame or as many as `walk` | none | a layer on top of every state: glowing eyes, shield shell, mark on an enemy, burning, frozen |

- Names are lower case with underscores, e.g. `kestrel_mech_glide.png`, `nyx@eclipse_walk.png`, `rook_overlay_plating.png`.
- Forms may break the palette budget by up to 8 colours. Overlays keep columns 0 and 15 free unless they are glow.
- See-through, invisible and tinted looks (stealth, damage flash, slow) are done by the game with transparency and tint, so no extra sprites are needed for them.
- Enemy variants for extra states and forms are generated like all others. Overlays get no enemy variant.

## 6. Files and Aseprite setup

```
assets/agents/{key}/{key}.aseprite            16 × 32, all 16 × 32 states as tags
assets/agents/{key}/{key}_dead.aseprite       32 × 16
assets/agents/{key}/{key}_portrait.aseprite   32 × 32  (killfeed 16 × 16 and select 32 × 64 likewise, if drawn)
assets/agents/{key}/{key}_{state}.png         exported strips, frames side by side, no padding
```

- `{key}` is the agent key from `config/agents.py`, in lower case (e.g. `vesper`).
- Layers: `guides` (locked, hidden on export), `body`, and optionally `fx` for glow in ability frames. Forms get their own file `{key}@{form}.aseprite`, overlays `{key}_overlay_{name}.aseprite`.
- Export every tag as a horizontal strip without spacing. Aseprite can do it in one go from the command line, though I haven't tested this exact line:

```bash
aseprite -b assets/agents/vesper/vesper.aseprite --ignore-layer guides --split-tags --sheet-type horizontal --sheet assets/agents/vesper/vesper_{tag}.png
```

  Alternatively, use File › Export Sprite Sheet with "Split Tags" and the file name `vesper_{tag}.png`.

## 7. After exporting

```bash
python docs/design/check_agent_sprites.py vesper
```

- The script checks for each state: size, frame count, free columns 0 and 15, reserved colours and the colour budget.
- It also writes the enemy variants `{key}_{state}_feind.png` with a red outline. Never draw those by hand.
- Extra states, forms and overlays are not checked yet; check them by eye against the guides.
- Missing optional states are only listed, with the state the game uses instead.

## 8. New agent: order of work

1. Write a short description of the look, its silhouette and three main colours. Each agent should be told apart by silhouette alone at 16 px: hair or headgear, shoulders and coat length are the strongest cues.
2. `idle`, then `walk`. Check them in the game; if the figure reads well, the rest follows.
3. `crouch`, `jump`, `shoot`, `reload`, `cast_c`, `cast_q`, `cast_e`, `cast_x`, `dead`, `portrait`.
4. Run the check, commit, and enter the agent as done in `docs/SPRITES.md`.
5. Later: special mechanics the agent needs (section 5), then optional states in this order: `plant`, `defuse`, `channel_*`, `dying`, the rest.

## 9. Originals only

Every agent is an original design. Do not draw characters, outfits or logos from other games, even renamed or changed in small ways.
