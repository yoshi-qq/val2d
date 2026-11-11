# Val2d sprite blueprints

Every kind of sprite the game uses, as an empty template at its exact size and frame count.
Open a template in Aseprite, put it on a locked `guides` layer, draw on a layer above, hide the guides and export to the target path.
Rules: `STYLE_GUIDE.md` in this folder. Agents in detail: `../CHARACTER_SHEETS.md`. Colours: `palette.png`.
Frames sit side by side in one strip without spacing; the template always has the maximum number of frames.
Every template has a finished example in `examples/` (Kestrel and the Workyard set), drawn over the guides.
Regenerate this folder with `python docs/design/build_blueprint_folder.py`.

Guide colours: red = head zone, gold = body zone or grip/fill area, teal = leg zone or accent line,
white cross = centre/anchor, white line = ground row, white ring = maximum radius, light/dark edge = light from the top left.


## Agents

| Template | Example | Target file | Frame size | Frames | Speed | Purpose |
|---|---|---|---|---|---|---|
| `agents/agent_idle.png` | [example](examples/agent_idle.example.png) | `assets/agents/{key}/{key}_idle.png` | 16×32 | 4 | 4 fps | standing still; 1 frame is fine, 2–4 for breathing (required; 1–4 frames, template has the maximum) |
| `agents/agent_walk.png` | [example](examples/agent_walk.example.png) | `assets/agents/{key}/{key}_walk.png` | 16×32 | 6 | 8 fps | moving; the game scales the rate with speed (run, walk) (required; 4–6 frames, template has the maximum) |
| `agents/agent_crouch.png` | [example](examples/agent_crouch.example.png) | `assets/agents/{key}/{key}_crouch.png` | 16×32 | 2 | 4 fps | crouched and still; upper body about 3 px lower (required; 1–2 frames, template has the maximum) |
| `agents/agent_crouch_walk.png` | [example](examples/agent_crouch_walk.example.png) | `assets/agents/{key}/{key}_crouch_walk.png` | 16×32 | 4 | 6 fps | moving while crouched (optional, falls back to crouch; 4–4 frames, template has the maximum) |
| `agents/agent_jump.png` | [example](examples/agent_jump.example.png) | `assets/agents/{key}/{key}_jump.png` | 16×32 | 2 | 8 fps | rising; legs tucked (required; 1–2 frames, template has the maximum) |
| `agents/agent_fall.png` | [example](examples/agent_fall.example.png) | `assets/agents/{key}/{key}_fall.png` | 16×32 | 2 | 8 fps | falling or dropping a level (optional, falls back to jump; 1–2 frames, template has the maximum) |
| `agents/agent_land.png` | [example](examples/agent_land.example.png) | `assets/agents/{key}/{key}_land.png` | 16×32 | 2 | 12 fps | touch-down, knees bent (optional, falls back to idle; 1–2 frames, template has the maximum) |
| `agents/agent_shoot.png` | [example](examples/agent_shoot.example.png) | `assets/agents/{key}/{key}_shoot.png` | 16×32 | 3 | 12 fps | one recoil per shot; weapon and muzzle flash are drawn by the game (required; 2–3 frames, template has the maximum) |
| `agents/agent_reload.png` | [example](examples/agent_reload.example.png) | `assets/agents/{key}/{key}_reload.png` | 16×32 | 6 | stretched | stretched to the weapon's reload time (required; 4–6 frames, template has the maximum) |
| `agents/agent_equip.png` | [example](examples/agent_equip.example.png) | `assets/agents/{key}/{key}_equip.png` | 16×32 | 3 | stretched | drawing a weapon; stretched to the equip time (optional, falls back to idle; 2–3 frames, template has the maximum) |
| `agents/agent_melee.png` | [example](examples/agent_melee.example.png) | `assets/agents/{key}/{key}_melee.png` | 16×32 | 4 | 12 fps | knife slash (optional, falls back to shoot; 3–4 frames, template has the maximum) |
| `agents/agent_flinch.png` | [example](examples/agent_flinch.example.png) | `assets/agents/{key}/{key}_flinch.png` | 16×32 | 2 | 12 fps | hit reaction, short (optional, falls back to idle; 2–2 frames, template has the maximum) |
| `agents/agent_plant.png` | [example](examples/agent_plant.example.png) | `assets/agents/{key}/{key}_plant.png` | 16×32 | 2 | 4 fps | kneeling, hands on the bomb; loops while planting (optional, falls back to crouch; 2–2 frames, template has the maximum) |
| `agents/agent_defuse.png` | [example](examples/agent_defuse.example.png) | `assets/agents/{key}/{key}_defuse.png` | 16×32 | 2 | 4 fps | kneeling, working on the bomb; loops while defusing (optional, falls back to crouch; 2–2 frames, template has the maximum) |
| `agents/agent_cast_c.png` | [example](examples/agent_cast_c.example.png) | `assets/agents/{key}/{key}_cast_c.png` | 16×32 | 4 | 8 fps | ability C, own pose (e.g. throw) (required; 3–4 frames, template has the maximum) |
| `agents/agent_cast_q.png` | [example](examples/agent_cast_q.example.png) | `assets/agents/{key}/{key}_cast_q.png` | 16×32 | 4 | 8 fps | ability Q, own pose (e.g. place on the ground) (required; 3–4 frames, template has the maximum) |
| `agents/agent_cast_e.png` | [example](examples/agent_cast_e.example.png) | `assets/agents/{key}/{key}_cast_e.png` | 16×32 | 4 | 8 fps | ability E (signature), own pose (required; 3–4 frames, template has the maximum) |
| `agents/agent_cast_x.png` | [example](examples/agent_cast_x.example.png) | `assets/agents/{key}/{key}_cast_x.png` | 16×32 | 6 | 8 fps | ultimate; may use the whole cell incl. columns 0 and 15 for glow (required; 4–6 frames, template has the maximum) |
| `agents/agent_channel_c.png` | [example](examples/agent_channel_c.example.png) | `assets/agents/{key}/{key}_channel_c.png` | 16×32 | 4 | 6 fps | held version of C (aiming, charging); loops (optional, falls back to cast_c; 2–4 frames, template has the maximum) |
| `agents/agent_channel_q.png` | [example](examples/agent_channel_q.example.png) | `assets/agents/{key}/{key}_channel_q.png` | 16×32 | 4 | 6 fps | held version of Q; loops (optional, falls back to cast_q; 2–4 frames, template has the maximum) |
| `agents/agent_channel_e.png` | [example](examples/agent_channel_e.example.png) | `assets/agents/{key}/{key}_channel_e.png` | 16×32 | 4 | 6 fps | held version of E; loops (optional, falls back to cast_e; 2–4 frames, template has the maximum) |
| `agents/agent_channel_x.png` | [example](examples/agent_channel_x.example.png) | `assets/agents/{key}/{key}_channel_x.png` | 16×32 | 4 | 6 fps | held or active ultimate; loops while it runs (optional, falls back to cast_x; 2–4 frames, template has the maximum) |
| `agents/agent_cast.png` | [example](examples/agent_cast.example.png) | `assets/agents/{key}/{key}_cast.png` | 16×32 | 3 | 8 fps | shared fallback pose for older sprites only (optional, falls back to idle; 3–3 frames, template has the maximum) |
| `agents/agent_dying.png` | [example](examples/agent_dying.example.png) | `assets/agents/{key}/{key}_dying.png` | 16×32 | 4 | 10 fps | falling over; ends in the dead pose (optional, falls back to dead; 3–4 frames, template has the maximum) |
| `agents/agent_dead.png` | [example](examples/agent_dead.example.png) | `assets/agents/{key}/{key}_dead.png` | 32×16 | 1 | still | lying, 32x16 cell, figure rotated to the left (required; 1–1 frames, template has the maximum) |
| `agents/agent_victory.png` | [example](examples/agent_victory.example.png) | `assets/agents/{key}/{key}_victory.png` | 16×32 | 4 | 4 fps | end-of-match pose (optional, falls back to idle; 2–4 frames, template has the maximum) |
| `agents/agent_portrait.png` | [example](examples/agent_portrait.example.png) | `assets/agents/{key}/{key}_portrait.png` | 32×32 | 1 | still | agent select, scoreboard; head and shoulders (required; 1–1 frames, template has the maximum) |
| `agents/agent_killfeed.png` | [example](examples/agent_killfeed.example.png) | `assets/agents/{key}/{key}_killfeed.png` | 16×16 | 1 | still | head only, for kill feed and minimap list (optional, falls back to portrait; 1–1 frames, template has the maximum) |
| `agents/agent_select.png` | [example](examples/agent_select.example.png) | `assets/agents/{key}/{key}_select.png` | 32×64 | 1 | still | large agent-select figure (optional, falls back to portrait; 1–1 frames, template has the maximum) |
| `agents/agent_mech_NAME.png` | [example](examples/agent_mech_NAME.example.png) | `assets/agents/{key}/{key}_mech_{name}.png` | 16×32 | 6 | 6 fps | extra state for a special mechanic (glide, hover, carry); 1–6 frames, loops, falls back to idle |
| `agents/agent@FORM_idle.png` | [example](examples/agent@FORM_idle.example.png) | `assets/agents/{key}/{key}@{form}_{state}.png` | 16×32 | 4 | as the state | form: replaces a state while the form is active; draw at least idle and walk |
| `agents/agent_overlay_NAME.png` | [example](examples/agent_overlay_NAME.example.png) | `assets/agents/{key}/{key}_overlay_{name}.png` | 16×32 | 4 | as walk | overlay on top of every state (glowing eyes, shield shell); 1 frame or as many as walk |

## Weapons

| Template | Example | Target file | Frame size | Frames | Speed | Purpose |
|---|---|---|---|---|---|---|
| `weapons/weapon_hand.png` | [example](examples/weapon_hand.example.png) | `assets/weapons/val2d/{key}.png` | 16×8 | 1 | still | weapon in hand, side view, muzzle right; keys: spatz, stachel, hornisse, lynx, kite, bulle, wespe, sirene, brecher, faecher, falke, lanze, speer, hammer, heron, elster, crane, adler, muehle, walze |
| `weapons/weapon_buy.png` | [example](examples/weapon_buy.example.png) | `assets/weapons/val2d/{key}_kauf.png` | 32×12 | 1 | still | buy-menu icon, same weapon larger, with outline |
| `weapons/knife.png` | [example](examples/knife.example.png) | `assets/weapons/val2d/messer.png` | 16×8 | 1 | still | knife, blade right |

## Map tiles

| Template | Example | Target file | Frame size | Frames | Speed | Purpose |
|---|---|---|---|---|---|---|
| `tiles/tile_floor.png` | [example](examples/tile_floor.example.png) | `assets/maps/{map}/boden_stein.png` | 32×32 | 1 | still | walkable floor, 2 × 2 m, tiles seamlessly |
| `tiles/tile_wall_thick.png` | [example](examples/tile_wall_thick.example.png) | `assets/maps/{map}/wand.png` | 32×32 | 1 | still | thick wall top (penetration 2–3) |
| `tiles/tile_wall_thin.png` | [example](examples/tile_wall_thin.example.png) | `assets/maps/{map}/wand_duenn.png` | 32×32 | 1 | still | thin wall top (penetration 0–1), visibly lighter material |
| `tiles/tile_crate.png` | [example](examples/tile_crate.example.png) | `assets/maps/{map}/kiste_metall.png` | 32×32 | 1 | still | crate seen from above, height 1 level, can be climbed |
| `tiles/tile_platform.png` | [example](examples/tile_platform.example.png) | `assets/maps/{map}/plattform.png` | 32×32 | 1 | still | raised floor (level 1) |
| `tiles/tile_ramp.png` | [example](examples/tile_ramp.example.png) | `assets/maps/{map}/rampe.png` | 32×32 | 1 | still | ramp between levels, steps run across the direction of travel |
| `tiles/tile_site_border.png` | [example](examples/tile_site_border.example.png) | `assets/maps/{map}/platz_rand.png` | 32×32 | 1 | still | bomb site border, transparent centre, laid over the floor |

## Effects

| Template | Example | Target file | Frame size | Frames | Speed | Purpose |
|---|---|---|---|---|---|---|
| `effects/fx_bomb.png` | [example](examples/fx_bomb.example.png) | `assets/fx/spike.png` | 16×16 | 2 | 4 fps | bomb carried and planted: LED on, off |
| `effects/fx_muzzle_flash.png` | [example](examples/fx_muzzle_flash.example.png) | `assets/fx/muendung.png` | 8×8 | 3 | 15 fps | muzzle flash, once per shot |
| `effects/fx_wall_impact.png` | [example](examples/fx_wall_impact.example.png) | `assets/fx/einschlag_wand.png` | 8×8 | 3 | 15 fps | bullet hits a wall |
| `effects/fx_body_hit.png` | [example](examples/fx_body_hit.example.png) | `assets/fx/treffer_koerper.png` | 8×8 | 3 | 15 fps | bullet hits a body (no gore) |
| `effects/fx_bomb_explosion.png` | [example](examples/fx_bomb_explosion.example.png) | `assets/fx/spike_explosion.png` | 64×64 | 6 | 10 fps | bomb explosion, scaled to the blast radius |
| `effects/fx_smoke.png` | [example](examples/fx_smoke.example.png) | `assets/fx/dunst.png` | 64×64 | 1 | still | smoke sphere, scaled to the radius |
| `effects/fx_smoke_forming.png` | [example](examples/fx_smoke_forming.example.png) | `assets/fx/dunst_aufbau.png` | 64×64 | 4 | 8 fps | smoke forming, then smoke |
| `effects/fx_zone.png` | [example](examples/fx_zone.example.png) | `assets/fx/zone.png` | 64×64 | 3 | 4 fps | generic area (white, tinted per status in code) |
| `effects/fx_slow_field.png` | [example](examples/fx_slow_field.example.png) | `assets/fx/bann.png` | 64×64 | 1 | still | agent-specific field |
| `effects/fx_slow_field_pulse.png` | [example](examples/fx_slow_field_pulse.example.png) | `assets/fx/bann_puls.png` | 64×64 | 3 | 4 fps | field pulse, loops |
| `effects/fx_blast.png` | [example](examples/fx_blast.example.png) | `assets/fx/blast.png` | 64×64 | 6 | 12 fps | generic blast ring, scaled to the radius |
| `effects/fx_sensor.png` | [example](examples/fx_sensor.example.png) | `assets/fx/lauscher.png` | 6×6 | 1 | still | small device lying on the ground |
| `effects/fx_sensor_pulse.png` | [example](examples/fx_sensor_pulse.example.png) | `assets/fx/lauscher_puls.png` | 32×32 | 3 | 6 fps | sensor pulse ring |
| `effects/fx_flash.png` | [example](examples/fx_flash.example.png) | `assets/fx/funke.png` | 16×16 | 1 | still | flash projectile |
| `effects/fx_flash_burst.png` | [example](examples/fx_flash_burst.example.png) | `assets/fx/funke_explosion.png` | 16×16 | 3 | 10 fps | flash going off |
| `effects/fx_vapor_wall.png` | [example](examples/fx_vapor_wall.example.png) | `assets/fx/schleier.png` | 16×16 | 1 | still | wall segment, tiled along the wall |
| `effects/fx_vapor_wall_forming.png` | [example](examples/fx_vapor_wall_forming.example.png) | `assets/fx/schleier_aufbau.png` | 16×16 | 3 | 8 fps | wall forming |
| `effects/fx_dash_trail.png` | [example](examples/fx_dash_trail.example.png) | `assets/fx/gleiten_spur.png` | 16×32 | 3 | 12 fps | trail behind a dashing figure (same cell as the figure) |
| `effects/fx_hop_dust.png` | [example](examples/fx_hop_dust.example.png) | `assets/fx/satz_staub.png` | 16×8 | 3 | 10 fps | dust under the feet at take-off |
| `effects/fx_tripwire.png` | [example](examples/fx_tripwire.example.png) | `assets/fx/tripwire.png` | 16×4 | 1 | still | wire, tiled along its length |
| `effects/fx_tripwire_node.png` | [example](examples/fx_tripwire_node.example.png) | `assets/fx/tripwire_node.png` | 6×6 | 1 | still | wire anchor at both ends |
| `effects/fx_alarm.png` | [example](examples/fx_alarm.example.png) | `assets/fx/alarm.png` | 16×16 | 2 | 3 fps | alarm device blinking |
| `effects/fx_wave.png` | [example](examples/fx_wave.example.png) | `assets/fx/wave.png` | 16×16 | 3 | 10 fps | wave band, tiled along the line |

## Interface

| Template | Example | Target file | Frame size | Frames | Speed | Purpose |
|---|---|---|---|---|---|---|
| `ui/ability_icon.png` | [example](examples/ability_icon.example.png) | `assets/ui/faehigkeit_{agent}_{C|Q|E}.png` | 16×16 | 1 | still | ability icon; glyph inside the 12 × 12 safe area |
| `ui/ability_icon_ult.png` | [example](examples/ability_icon_ult.example.png) | `assets/ui/faehigkeit_{agent}_X.png` | 16×16 | 1 | still | ultimate icon with gold frame |
| `ui/hud_icon.png` | [example](examples/hud_icon.example.png) | `assets/ui/hud/{name}.png` | 8×8 | 1 | still | HUD icon: leben, schild, credits, munition, kopfschuss, spike_klein, uhr, tot |
| `ui/status_icon.png` | [example](examples/status_icon.example.png) | `assets/ui/status/{status}.png` | 8×8 | 1 | still | status icon: nearsight, concuss, slow, vulnerable, decay, suppress, detain, deaf, stim |
| `ui/minimap_icon.png` | [example](examples/minimap_icon.example.png) | `assets/ui/minimap/{name}.png` | 8×8 | 1 | still | minimap: selbst (arrow points up), verbuendet, feind, tot, spike, dunst, bann, schleier |
| `ui/frame_nine_slice.png` | [example](examples/frame_nine_slice.example.png) | `assets/ui/hud/rahmen.png, rahmen_aktiv.png` | 12×12 | 1 | still | nine-slice frame, 4 px corners, centre stretches |
| `ui/bar.png` | [example](examples/bar.example.png) | `assets/ui/hud/balken_{leben|schild|fortschritt|leer}.png` | 48×6 | 1 | still | bar, stretched horizontally; fill drawn over balken_leer |
| `ui/banner.png` | [example](examples/banner.example.png) | `assets/ui/banner/{name}.png` | 96×21 | 1 | still | round banner, width follows the text (12 px padding each side), 5 × 7 pixel font |
| `ui/logo.png` | [example](examples/logo.example.png) | `assets/logo.png (+ icon.ico 16/32/48)` | 48×48 | 1 | still | game logo, also program icon |
| `ui/player_card.png` | [example](examples/player_card.example.png) | `assets/menu/lobby/playercard.png` | 64×128 | 1 | still | lobby player card with logo at (8, 10) |
