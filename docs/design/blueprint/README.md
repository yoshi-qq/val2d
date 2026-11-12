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
| `weapons/weapon_buy.png` | [example](examples/weapon_buy.example.png) | `assets/weapons/val2d/{key}_kauf.png` | 64×24 | 1 | still | buy-menu icon, 64 × 24, centred, lit automatically with outline (docs/design/sprites_buy_hd.py) |
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
| `ui/ability_icon.png` | [example](examples/ability_icon.example.png) | `assets/ui/faehigkeit_{agent}_{C|Q|E}.png` | 32×32 | 1 | still | ability icon: dark plate, 24 × 24 glyph in white with the agent's accent colour |
| `ui/ability_icon_ult.png` | [example](examples/ability_icon_ult.example.png) | `assets/ui/faehigkeit_{agent}_X.png` | 32×32 | 1 | still | ultimate icon: as above with a gold frame and corner highlights |
| `ui/hud_icon.png` | [example](examples/hud_icon.example.png) | `assets/ui/hud/{name}.png` | 16×16 | 1 | still | HUD icon: leben, schild, credits, munition, kopfschuss, spike_klein, uhr, tot |
| `ui/status_icon.png` | [example](examples/status_icon.example.png) | `assets/ui/status/{status}.png` | 16×16 | 1 | still | status icon: nearsight, concuss, slow, vulnerable, decay, suppress, detain, deaf, stim |
| `ui/minimap_icon.png` | [example](examples/minimap_icon.example.png) | `assets/ui/minimap/{name}.png` | 12×12 | 1 | still | minimap: selbst (arrow points up), verbuendet, feind, tot, spike, dunst, bann, schleier |
| `ui/frame_nine_slice.png` | [example](examples/frame_nine_slice.example.png) | `assets/ui/hud/rahmen.png, rahmen_aktiv.png` | 24×24 | 1 | still | nine-slice frame, 8 px corners, centre stretches |
| `ui/bar.png` | [example](examples/bar.example.png) | `assets/ui/hud/balken_{leben|schild|fortschritt|leer}.png` | 96×12 | 1 | still | bar, stretched horizontally; fill drawn over balken_leer |
| `ui/banner.png` | [example](examples/banner.example.png) | `assets/ui/banner/{name}.png` | 160×32 | 1 | still | round banner, height 32, width = text + 40 px, game font fixed_sys at 16 px without smoothing |
| `ui/logo.png` | [example](examples/logo.example.png) | `assets/logo.png (+ icon.ico 16/32/48)` | 48×48 | 1 | still | game logo, also program icon |
| `ui/player_card.png` | [example](examples/player_card.example.png) | `assets/menu/lobby/playercard.png` | 64×128 | 1 | still | lobby player card with logo at (8, 10) |

## Interface: menus

| Template | Example | Target file | Frame size | Frames | Speed | Purpose |
|---|---|---|---|---|---|---|
| `ui_menu/button.png` | [example](examples/button.example.png) | `assets/ui/menu/button.png` | 16×16 | 1 | still | button |
| `ui_menu/button_disabled.png` | [example](examples/button_disabled.example.png) | `assets/ui/menu/button_disabled.png` | 16×16 | 1 | still | button disabled |
| `ui_menu/button_hover.png` | [example](examples/button_hover.example.png) | `assets/ui/menu/button_hover.png` | 16×16 | 1 | still | button hover |
| `ui_menu/button_pressed.png` | [example](examples/button_pressed.example.png) | `assets/ui/menu/button_pressed.png` | 16×16 | 1 | still | button pressed |
| `ui_menu/checkbox.png` | [example](examples/checkbox.example.png) | `assets/ui/menu/checkbox.png` | 8×8 | 1 | still | checkbox |
| `ui_menu/checkbox_on.png` | [example](examples/checkbox_on.example.png) | `assets/ui/menu/checkbox_on.png` | 8×8 | 1 | still | checkbox on |
| `ui_menu/cursor.png` | [example](examples/cursor.example.png) | `assets/ui/menu/cursor.png` | 12×13 | 1 | still | cursor |
| `ui_menu/panel.png` | [example](examples/panel.example.png) | `assets/ui/menu/panel.png` | 24×24 | 1 | still | panel |
| `ui_menu/slider_fill.png` | [example](examples/slider_fill.example.png) | `assets/ui/menu/slider_fill.png` | 16×6 | 1 | still | slider fill |
| `ui_menu/slider_knob.png` | [example](examples/slider_knob.example.png) | `assets/ui/menu/slider_knob.png` | 6×6 | 1 | still | slider knob |
| `ui_menu/slider_track.png` | [example](examples/slider_track.example.png) | `assets/ui/menu/slider_track.png` | 16×6 | 1 | still | slider track |
| `ui_menu/tab.png` | [example](examples/tab.example.png) | `assets/ui/menu/tab.png` | 16×16 | 1 | still | tab |
| `ui_menu/tab_active.png` | [example](examples/tab_active.example.png) | `assets/ui/menu/tab_active.png` | 16×16 | 1 | still | tab active |
| `ui_menu/textfield.png` | [example](examples/textfield.example.png) | `assets/ui/menu/textfield.png` | 16×16 | 1 | still | textfield |
| `ui_menu/title_background.png` | [example](examples/title_background.example.png) | `assets/ui/menu/title_background.png` | 480×270 | 1 | still | menu background, full native screen 480 × 270, left 200 px darker for the menu buttons |

## Interface: icons

| Template | Example | Target file | Frame size | Frames | Speed | Purpose |
|---|---|---|---|---|---|---|
| `ui_icons/arrow_down.png` | [example](examples/arrow_down.example.png) | `assets/ui/icons/arrow_down.png` | 8×8 | 1 | still | arrow down |
| `ui_icons/arrow_left.png` | [example](examples/arrow_left.example.png) | `assets/ui/icons/arrow_left.png` | 8×8 | 1 | still | arrow left |
| `ui_icons/arrow_right.png` | [example](examples/arrow_right.example.png) | `assets/ui/icons/arrow_right.png` | 8×8 | 1 | still | arrow right |
| `ui_icons/arrow_up.png` | [example](examples/arrow_up.example.png) | `assets/ui/icons/arrow_up.png` | 8×8 | 1 | still | arrow up |
| `ui_icons/check.png` | [example](examples/check.example.png) | `assets/ui/icons/check.png` | 8×8 | 1 | still | check |
| `ui_icons/close.png` | [example](examples/close.example.png) | `assets/ui/icons/close.png` | 8×8 | 1 | still | close |
| `ui_icons/credits_large.png` | [example](examples/credits_large.example.png) | `assets/ui/icons/credits_large.png` | 12×12 | 1 | still | credits large |
| `ui_icons/gear.png` | [example](examples/gear.example.png) | `assets/ui/icons/gear.png` | 8×8 | 1 | still | gear |
| `ui_icons/lock.png` | [example](examples/lock.example.png) | `assets/ui/icons/lock.png` | 8×8 | 1 | still | lock |
| `ui_icons/mic.png` | [example](examples/mic.example.png) | `assets/ui/icons/mic.png` | 8×8 | 1 | still | mic |
| `ui_icons/minus.png` | [example](examples/minus.example.png) | `assets/ui/icons/minus.png` | 8×8 | 1 | still | minus |
| `ui_icons/person.png` | [example](examples/person.example.png) | `assets/ui/icons/person.png` | 8×8 | 1 | still | person |
| `ui_icons/ping_0.png` | [example](examples/ping_0.example.png) | `assets/ui/icons/ping_0.png` | 8×8 | 1 | still | ping 0 |
| `ui_icons/ping_1.png` | [example](examples/ping_1.example.png) | `assets/ui/icons/ping_1.png` | 8×8 | 1 | still | ping 1 |
| `ui_icons/ping_2.png` | [example](examples/ping_2.example.png) | `assets/ui/icons/ping_2.png` | 8×8 | 1 | still | ping 2 |
| `ui_icons/ping_3.png` | [example](examples/ping_3.example.png) | `assets/ui/icons/ping_3.png` | 8×8 | 1 | still | ping 3 |
| `ui_icons/plus.png` | [example](examples/plus.example.png) | `assets/ui/icons/plus.png` | 8×8 | 1 | still | plus |
| `ui_icons/role_controller.png` | [example](examples/role_controller.example.png) | `assets/ui/icons/role_controller.png` | 16×16 | 1 | still | role controller |
| `ui_icons/role_duelist.png` | [example](examples/role_duelist.example.png) | `assets/ui/icons/role_duelist.png` | 16×16 | 1 | still | role duelist |
| `ui_icons/role_initiator.png` | [example](examples/role_initiator.example.png) | `assets/ui/icons/role_initiator.png` | 16×16 | 1 | still | role initiator |
| `ui_icons/role_sentinel.png` | [example](examples/role_sentinel.example.png) | `assets/ui/icons/role_sentinel.png` | 16×16 | 1 | still | role sentinel |
| `ui_icons/round_empty.png` | [example](examples/round_empty.example.png) | `assets/ui/icons/round_empty.png` | 6×6 | 1 | still | round empty |
| `ui_icons/round_loss.png` | [example](examples/round_loss.example.png) | `assets/ui/icons/round_loss.png` | 6×6 | 1 | still | round loss |
| `ui_icons/round_win.png` | [example](examples/round_win.example.png) | `assets/ui/icons/round_win.png` | 6×6 | 1 | still | round win |
| `ui_icons/side_attack.png` | [example](examples/side_attack.example.png) | `assets/ui/icons/side_attack.png` | 16×16 | 1 | still | side attack |
| `ui_icons/side_defense.png` | [example](examples/side_defense.example.png) | `assets/ui/icons/side_defense.png` | 16×16 | 1 | still | side defense |
| `ui_icons/skull.png` | [example](examples/skull.example.png) | `assets/ui/icons/skull.png` | 8×8 | 1 | still | skull |
| `ui_icons/sound_off.png` | [example](examples/sound_off.example.png) | `assets/ui/icons/sound_off.png` | 8×8 | 1 | still | sound off |
| `ui_icons/sound_on.png` | [example](examples/sound_on.example.png) | `assets/ui/icons/sound_on.png` | 8×8 | 1 | still | sound on |
| `ui_icons/trophy.png` | [example](examples/trophy.example.png) | `assets/ui/icons/trophy.png` | 8×8 | 1 | still | trophy |

## Interface: buy menu

| Template | Example | Target file | Frame size | Frames | Speed | Purpose |
|---|---|---|---|---|---|---|
| `ui_buy/cat_abilities.png` | [example](examples/cat_abilities.example.png) | `assets/ui/buy/cat_abilities.png` | 16×16 | 1 | still | cat abilities |
| `ui_buy/cat_armor.png` | [example](examples/cat_armor.example.png) | `assets/ui/buy/cat_armor.png` | 16×16 | 1 | still | cat armor |
| `ui_buy/cat_heavy.png` | [example](examples/cat_heavy.example.png) | `assets/ui/buy/cat_heavy.png` | 16×16 | 1 | still | cat heavy |
| `ui_buy/cat_rifle.png` | [example](examples/cat_rifle.example.png) | `assets/ui/buy/cat_rifle.png` | 16×16 | 1 | still | cat rifle |
| `ui_buy/cat_shotgun.png` | [example](examples/cat_shotgun.example.png) | `assets/ui/buy/cat_shotgun.png` | 16×16 | 1 | still | cat shotgun |
| `ui_buy/cat_sidearm.png` | [example](examples/cat_sidearm.example.png) | `assets/ui/buy/cat_sidearm.png` | 16×16 | 1 | still | cat sidearm |
| `ui_buy/cat_smg.png` | [example](examples/cat_smg.example.png) | `assets/ui/buy/cat_smg.png` | 16×16 | 1 | still | cat smg |
| `ui_buy/cat_sniper.png` | [example](examples/cat_sniper.example.png) | `assets/ui/buy/cat_sniper.png` | 16×16 | 1 | still | cat sniper |
| `ui_buy/vest_heavy.png` | [example](examples/vest_heavy.example.png) | `assets/ui/buy/vest_heavy.png` | 64×24 | 1 | still | vest heavy |
| `ui_buy/vest_light.png` | [example](examples/vest_light.example.png) | `assets/ui/buy/vest_light.png` | 64×24 | 1 | still | vest light |

## Map tiles: common set

| Template | Example | Target file | Frame size | Frames | Speed | Purpose |
|---|---|---|---|---|---|---|
| `maps_common/door_closed.png` | [example](examples/door_closed.example.png) | `assets/maps/common/door_closed.png` | 32×32 | 1 | still | door closed |
| `maps_common/door_open.png` | [example](examples/door_open.example.png) | `assets/maps/common/door_open.png` | 32×32 | 1 | still | door open |
| `maps_common/fence_chainlink.png` | [example](examples/fence_chainlink.example.png) | `assets/maps/common/fence_chainlink.png` | 32×32 | 1 | still | fence chainlink |
| `maps_common/fence_wood.png` | [example](examples/fence_wood.example.png) | `assets/maps/common/fence_wood.png` | 32×32 | 1 | still | fence wood |
| `maps_common/floor_asphalt.png` | [example](examples/floor_asphalt.example.png) | `assets/maps/common/floor_asphalt.png` | 32×32 | 1 | still | floor asphalt |
| `maps_common/floor_carpet.png` | [example](examples/floor_carpet.example.png) | `assets/maps/common/floor_carpet.png` | 32×32 | 1 | still | floor carpet |
| `maps_common/floor_cobble.png` | [example](examples/floor_cobble.example.png) | `assets/maps/common/floor_cobble.png` | 32×32 | 1 | still | floor cobble |
| `maps_common/floor_concrete.png` | [example](examples/floor_concrete.example.png) | `assets/maps/common/floor_concrete.png` | 32×32 | 1 | still | floor concrete |
| `maps_common/floor_dirt.png` | [example](examples/floor_dirt.example.png) | `assets/maps/common/floor_dirt.png` | 32×32 | 1 | still | floor dirt |
| `maps_common/floor_grass.png` | [example](examples/floor_grass.example.png) | `assets/maps/common/floor_grass.png` | 32×32 | 1 | still | floor grass |
| `maps_common/floor_grate.png` | [example](examples/floor_grate.example.png) | `assets/maps/common/floor_grate.png` | 32×32 | 1 | still | floor grate |
| `maps_common/floor_gravel.png` | [example](examples/floor_gravel.example.png) | `assets/maps/common/floor_gravel.png` | 32×32 | 1 | still | floor gravel |
| `maps_common/floor_metal_plate.png` | [example](examples/floor_metal_plate.example.png) | `assets/maps/common/floor_metal_plate.png` | 32×32 | 1 | still | floor metal plate |
| `maps_common/floor_planks.png` | [example](examples/floor_planks.example.png) | `assets/maps/common/floor_planks.png` | 32×32 | 1 | still | floor planks |
| `maps_common/floor_sand.png` | [example](examples/floor_sand.example.png) | `assets/maps/common/floor_sand.png` | 32×32 | 1 | still | floor sand |
| `maps_common/floor_stone_cracked.png` | [example](examples/floor_stone_cracked.example.png) | `assets/maps/common/floor_stone_cracked.png` | 32×32 | 1 | still | floor stone cracked |
| `maps_common/floor_tiles.png` | [example](examples/floor_tiles.example.png) | `assets/maps/common/floor_tiles.png` | 32×32 | 1 | still | floor tiles |
| `maps_common/floor_tiles_dark.png` | [example](examples/floor_tiles_dark.example.png) | `assets/maps/common/floor_tiles_dark.png` | 32×32 | 1 | still | floor tiles dark |
| `maps_common/platform_edge.png` | [example](examples/platform_edge.example.png) | `assets/maps/common/platform_edge.png` | 32×4 | 1 | still | platform edge |
| `maps_common/spawn_barrier.png` | [example](examples/spawn_barrier.example.png) | `assets/maps/common/spawn_barrier.png` | 32×32 | 2 | 4 fps | spawn barrier |
| `maps_common/wall_brick.png` | [example](examples/wall_brick.example.png) | `assets/maps/common/wall_brick.png` | 32×32 | 1 | still | wall brick |
| `maps_common/wall_concrete.png` | [example](examples/wall_concrete.example.png) | `assets/maps/common/wall_concrete.png` | 32×32 | 1 | still | wall concrete |
| `maps_common/wall_container.png` | [example](examples/wall_container.example.png) | `assets/maps/common/wall_container.png` | 32×32 | 1 | still | wall container |
| `maps_common/wall_hedge.png` | [example](examples/wall_hedge.example.png) | `assets/maps/common/wall_hedge.png` | 32×32 | 1 | still | wall hedge |
| `maps_common/wall_jersey_barrier.png` | [example](examples/wall_jersey_barrier.example.png) | `assets/maps/common/wall_jersey_barrier.png` | 32×32 | 1 | still | wall jersey barrier |
| `maps_common/wall_metal_sheet.png` | [example](examples/wall_metal_sheet.example.png) | `assets/maps/common/wall_metal_sheet.png` | 32×32 | 1 | still | wall metal sheet |
| `maps_common/wall_sandbags.png` | [example](examples/wall_sandbags.example.png) | `assets/maps/common/wall_sandbags.png` | 32×32 | 1 | still | wall sandbags |
| `maps_common/wall_shadow.png` | [example](examples/wall_shadow.example.png) | `assets/maps/common/wall_shadow.png` | 32×8 | 1 | still | wall shadow |
| `maps_common/wall_stone.png` | [example](examples/wall_stone.example.png) | `assets/maps/common/wall_stone.png` | 32×32 | 1 | still | wall stone |
| `maps_common/window_glass.png` | [example](examples/window_glass.example.png) | `assets/maps/common/window_glass.png` | 32×32 | 1 | still | window glass |

## Map props

| Template | Example | Target file | Frame size | Frames | Speed | Purpose |
|---|---|---|---|---|---|---|
| `maps_common_props/barrel.png` | [example](examples/barrel.example.png) | `assets/maps/common/props/barrel.png` | 12×12 | 1 | still | barrel |
| `maps_common_props/bench.png` | [example](examples/bench.example.png) | `assets/maps/common/props/bench.png` | 32×8 | 1 | still | bench |
| `maps_common_props/boxes_cardboard.png` | [example](examples/boxes_cardboard.example.png) | `assets/maps/common/props/boxes_cardboard.png` | 16×12 | 1 | still | boxes cardboard |
| `maps_common_props/bush.png` | [example](examples/bush.example.png) | `assets/maps/common/props/bush.png` | 16×16 | 1 | still | bush |
| `maps_common_props/car.png` | [example](examples/car.example.png) | `assets/maps/common/props/car.png` | 64×32 | 1 | still | car |
| `maps_common_props/chair.png` | [example](examples/chair.example.png) | `assets/maps/common/props/chair.png` | 8×8 | 1 | still | chair |
| `maps_common_props/cone.png` | [example](examples/cone.example.png) | `assets/maps/common/props/cone.png` | 10×6 | 1 | still | cone |
| `maps_common_props/container_large.png` | [example](examples/container_large.example.png) | `assets/maps/common/props/container_large.png` | 96×32 | 1 | still | container large |
| `maps_common_props/crate_small.png` | [example](examples/crate_small.example.png) | `assets/maps/common/props/crate_small.png` | 12×12 | 1 | still | crate small |
| `maps_common_props/crate_stack.png` | [example](examples/crate_stack.example.png) | `assets/maps/common/props/crate_stack.png` | 24×24 | 1 | still | crate stack |
| `maps_common_props/debris.png` | [example](examples/debris.example.png) | `assets/maps/common/props/debris.png` | 10×7 | 1 | still | debris |
| `maps_common_props/dumpster.png` | [example](examples/dumpster.example.png) | `assets/maps/common/props/dumpster.png` | 32×20 | 1 | still | dumpster |
| `maps_common_props/generator.png` | [example](examples/generator.example.png) | `assets/maps/common/props/generator.png` | 24×16 | 1 | still | generator |
| `maps_common_props/ladder.png` | [example](examples/ladder.example.png) | `assets/maps/common/props/ladder.png` | 16×32 | 1 | still | ladder |
| `maps_common_props/lamp.png` | [example](examples/lamp.example.png) | `assets/maps/common/props/lamp.png` | 16×16 | 1 | still | lamp |
| `maps_common_props/pallet.png` | [example](examples/pallet.example.png) | `assets/maps/common/props/pallet.png` | 16×9 | 1 | still | pallet |
| `maps_common_props/pillar.png` | [example](examples/pillar.example.png) | `assets/maps/common/props/pillar.png` | 16×16 | 1 | still | pillar |
| `maps_common_props/pipe.png` | [example](examples/pipe.example.png) | `assets/maps/common/props/pipe.png` | 32×8 | 1 | still | pipe |
| `maps_common_props/plant.png` | [example](examples/plant.example.png) | `assets/maps/common/props/plant.png` | 10×8 | 1 | still | plant |
| `maps_common_props/rock.png` | [example](examples/rock.example.png) | `assets/maps/common/props/rock.png` | 16×12 | 1 | still | rock |
| `maps_common_props/table.png` | [example](examples/table.example.png) | `assets/maps/common/props/table.png` | 24×16 | 1 | still | table |
| `maps_common_props/trash_bin.png` | [example](examples/trash_bin.example.png) | `assets/maps/common/props/trash_bin.png` | 8×8 | 1 | still | trash bin |
| `maps_common_props/tree.png` | [example](examples/tree.example.png) | `assets/maps/common/props/tree.png` | 32×32 | 1 | still | tree |
| `maps_common_props/vending_machine.png` | [example](examples/vending_machine.example.png) | `assets/maps/common/props/vending_machine.png` | 16×12 | 1 | still | vending machine |
| `maps_common_props/warning_sign.png` | [example](examples/warning_sign.example.png) | `assets/maps/common/props/warning_sign.png` | 12×12 | 1 | still | warning sign |

## Map decals

| Template | Example | Target file | Frame size | Frames | Speed | Purpose |
|---|---|---|---|---|---|---|
| `maps_common_decals/arrow.png` | [example](examples/arrow.example.png) | `assets/maps/common/decals/arrow.png` | 16×16 | 1 | still | arrow |
| `maps_common_decals/crack.png` | [example](examples/crack.example.png) | `assets/maps/common/decals/crack.png` | 32×32 | 1 | still | crack |
| `maps_common_decals/drain.png` | [example](examples/drain.example.png) | `assets/maps/common/decals/drain.png` | 16×9 | 1 | still | drain |
| `maps_common_decals/footprints.png` | [example](examples/footprints.example.png) | `assets/maps/common/decals/footprints.png` | 16×16 | 1 | still | footprints |
| `maps_common_decals/grass_tuft.png` | [example](examples/grass_tuft.example.png) | `assets/maps/common/decals/grass_tuft.png` | 8×4 | 1 | still | grass tuft |
| `maps_common_decals/hazard_stripe.png` | [example](examples/hazard_stripe.example.png) | `assets/maps/common/decals/hazard_stripe.png` | 32×8 | 1 | still | hazard stripe |
| `maps_common_decals/leaves.png` | [example](examples/leaves.example.png) | `assets/maps/common/decals/leaves.png` | 32×32 | 1 | still | leaves |
| `maps_common_decals/manhole.png` | [example](examples/manhole.example.png) | `assets/maps/common/decals/manhole.png` | 16×16 | 1 | still | manhole |
| `maps_common_decals/oil_stain.png` | [example](examples/oil_stain.example.png) | `assets/maps/common/decals/oil_stain.png` | 32×32 | 1 | still | oil stain |
| `maps_common_decals/paint_line.png` | [example](examples/paint_line.example.png) | `assets/maps/common/decals/paint_line.png` | 32×4 | 1 | still | paint line |
| `maps_common_decals/paint_x.png` | [example](examples/paint_x.example.png) | `assets/maps/common/decals/paint_x.png` | 16×16 | 1 | still | paint x |
| `maps_common_decals/puddle.png` | [example](examples/puddle.example.png) | `assets/maps/common/decals/puddle.png` | 32×32 | 1 | still | puddle |
| `maps_common_decals/scorch.png` | [example](examples/scorch.example.png) | `assets/maps/common/decals/scorch.png` | 32×32 | 1 | still | scorch |
| `maps_common_decals/site_a.png` | [example](examples/site_a.example.png) | `assets/maps/common/decals/site_a.png` | 16×16 | 1 | still | site a |
| `maps_common_decals/site_b.png` | [example](examples/site_b.example.png) | `assets/maps/common/decals/site_b.png` | 16×16 | 1 | still | site b |
| `maps_common_decals/site_c.png` | [example](examples/site_c.example.png) | `assets/maps/common/decals/site_c.png` | 16×16 | 1 | still | site c |
| `maps_common_decals/tire_marks.png` | [example](examples/tire_marks.example.png) | `assets/maps/common/decals/tire_marks.png` | 32×32 | 1 | still | tire marks |

## Ability sprites (generic)

| Template | Example | Target file | Frame size | Frames | Speed | Purpose |
|---|---|---|---|---|---|---|
| `fx_ability/anchor_marker.png` | [example](examples/anchor_marker.example.png) | `assets/fx/ability/anchor_marker.png` | 10×8 | 2 | 4 fps | anchor marker |
| `fx_ability/arc_dot.png` | [example](examples/arc_dot.example.png) | `assets/fx/ability/arc_dot.png` | 3×3 | 1 | still | arc dot |
| `fx_ability/beacon.png` | [example](examples/beacon.example.png) | `assets/fx/ability/beacon.png` | 16×16 | 2 | 4 fps | beacon |
| `fx_ability/decoy_step.png` | [example](examples/decoy_step.example.png) | `assets/fx/ability/decoy_step.png` | 8×8 | 1 | still | decoy step |
| `fx_ability/grenade.png` | [example](examples/grenade.example.png) | `assets/fx/ability/grenade.png` | 6×5 | 1 | still | grenade |
| `fx_ability/heal.png` | [example](examples/heal.example.png) | `assets/fx/ability/heal.png` | 16×32 | 3 | 10 fps | heal |
| `fx_ability/immunity_aura.png` | [example](examples/immunity_aura.example.png) | `assets/fx/ability/immunity_aura.png` | 16×32 | 2 | 4 fps | immunity aura |
| `fx_ability/impact_puff.png` | [example](examples/impact_puff.example.png) | `assets/fx/ability/impact_puff.png` | 16×16 | 3 | 10 fps | impact puff |
| `fx_ability/mine.png` | [example](examples/mine.example.png) | `assets/fx/ability/mine.png` | 8×6 | 2 | 4 fps | mine |
| `fx_ability/projectile_dart.png` | [example](examples/projectile_dart.example.png) | `assets/fx/ability/projectile_dart.png` | 8×5 | 1 | still | projectile dart |
| `fx_ability/projectile_orb.png` | [example](examples/projectile_orb.example.png) | `assets/fx/ability/projectile_orb.png` | 6×6 | 2 | 4 fps | projectile orb |
| `fx_ability/reveal_marker.png` | [example](examples/reveal_marker.example.png) | `assets/fx/ability/reveal_marker.png` | 7×7 | 2 | 4 fps | reveal marker |
| `fx_ability/revive.png` | [example](examples/revive.example.png) | `assets/fx/ability/revive.png` | 16×32 | 4 | 10 fps | revive |
| `fx_ability/shield_shell.png` | [example](examples/shield_shell.example.png) | `assets/fx/ability/shield_shell.png` | 16×32 | 3 | 10 fps | shield shell |
| `fx_ability/teleport.png` | [example](examples/teleport.example.png) | `assets/fx/ability/teleport.png` | 16×32 | 4 | 10 fps | teleport |

## Interface: crosshair

| Template | Example | Target file | Frame size | Frames | Speed | Purpose |
|---|---|---|---|---|---|---|
| `ui_crosshair/arm.png` | [example](examples/arm.example.png) | `assets/ui/crosshair/arm.png` | 2×8 | 1 | still | arm |
| `ui_crosshair/arm_hit.png` | [example](examples/arm_hit.example.png) | `assets/ui/crosshair/arm_hit.png` | 2×8 | 1 | still | arm hit |
| `ui_crosshair/dot.png` | [example](examples/dot.example.png) | `assets/ui/crosshair/dot.png` | 4×4 | 1 | still | dot |
| `ui_crosshair/dot_hit.png` | [example](examples/dot_hit.example.png) | `assets/ui/crosshair/dot_hit.png` | 4×4 | 1 | still | dot hit |

## Interface: scoreboard

| Template | Example | Target file | Frame size | Frames | Speed | Purpose |
|---|---|---|---|---|---|---|
| `ui_scoreboard/header_team_a.png` | [example](examples/header_team_a.example.png) | `assets/ui/scoreboard/header_team_a.png` | 24×24 | 1 | still | header team a |
| `ui_scoreboard/header_team_b.png` | [example](examples/header_team_b.example.png) | `assets/ui/scoreboard/header_team_b.png` | 24×24 | 1 | still | header team b |
| `ui_scoreboard/row.png` | [example](examples/row.example.png) | `assets/ui/scoreboard/row.png` | 24×24 | 1 | still | row |
| `ui_scoreboard/row_self.png` | [example](examples/row_self.example.png) | `assets/ui/scoreboard/row_self.png` | 24×24 | 1 | still | row self |

## Interface and effects: extras

| Template | Example | Target file | Frame size | Frames | Speed | Purpose |
|---|---|---|---|---|---|---|
| `extra/tracer.png` | [example](examples/tracer.example.png) | `assets/fx/tracer.png` | 16×2 | 1 | still | tracer |
| `extra/tracer_own.png` | [example](examples/tracer_own.example.png) | `assets/fx/tracer_own.png` | 16×2 | 1 | still | tracer own |
| `extra/sound_ring.png` | [example](examples/sound_ring.example.png) | `assets/fx/sound_ring.png` | 64×64 | 3 | 5 fps | sound ring |
| `extra/radius_ring.png` | [example](examples/radius_ring.example.png) | `assets/fx/radius_ring.png` | 64×64 | 1 | still | radius ring |
| `extra/facing_marker.png` | [example](examples/facing_marker.example.png) | `assets/fx/facing_marker.png` | 8×8 | 1 | still | facing marker |
| `extra/frame.png` | [example](examples/frame.example.png) | `assets/ui/minimap/frame.png` | 24×24 | 1 | still | frame |
| `extra/wall.png` | [example](examples/wall.example.png) | `assets/ui/minimap/wall.png` | 4×4 | 1 | still | wall |
| `extra/crate.png` | [example](examples/crate.example.png) | `assets/ui/minimap/crate.png` | 4×4 | 1 | still | crate |
| `extra/killfeed_row.png` | [example](examples/killfeed_row.example.png) | `assets/ui/hud/killfeed_row.png` | 24×24 | 1 | still | killfeed row |
| `extra/killfeed_row_self.png` | [example](examples/killfeed_row_self.example.png) | `assets/ui/hud/killfeed_row_self.png` | 24×24 | 1 | still | killfeed row self |
| `extra/score_panel.png` | [example](examples/score_panel.example.png) | `assets/ui/hud/score_panel.png` | 24×24 | 1 | still | score panel |
| `extra/weapon_panel.png` | [example](examples/weapon_panel.example.png) | `assets/ui/hud/weapon_panel.png` | 24×24 | 1 | still | weapon panel |
| `extra/ability_panel.png` | [example](examples/ability_panel.example.png) | `assets/ui/hud/ability_panel.png` | 24×24 | 1 | still | ability panel |
| `extra/carrier_hint.png` | [example](examples/carrier_hint.example.png) | `assets/ui/hud/carrier_hint.png` | 16×16 | 1 | still | carrier hint |

## Map keys (config/materials.py)

Map files refer to sprites by key. Draw a new material or object with the template of its kind,
then add the key with its tile to config/materials.py (or ask the coding session).

### Walls

| Key | Tile | Penetration | Blocks sight | Height |
|---|---|---|---|---|
| `concrete` | `assets/maps/common/wall_concrete.png` | 3 | yes | 2 |
| `brick` | `assets/maps/common/wall_brick.png` | 2 | yes | 2 |
| `wood_fence` | `assets/maps/common/fence_wood.png` | 0 | yes | 2 |
| `glass` | `assets/maps/common/window_glass.png` | 0 | no | 2 |
| `crate_metal` | `assets/maps/werkhof/kiste_metall.png` | 1 | no | 1 |
| `werkhof_thick` | `assets/maps/werkhof/wand.png` | 2 | yes | 2 |
| `werkhof_thin` | `assets/maps/werkhof/wand_duenn.png` | 0 | yes | 2 |
| `metal_sheet` | `assets/maps/common/wall_metal_sheet.png` | 1 | yes | 2 |
| `sandbags` | `assets/maps/common/wall_sandbags.png` | 1 | no | 1 |
| `stone` | `assets/maps/common/wall_stone.png` | 3 | yes | 2 |
| `container` | `assets/maps/common/wall_container.png` | 2 | yes | 2 |
| `chainlink` | `assets/maps/common/fence_chainlink.png` | 0 | no | 2 |
| `hedge` | `assets/maps/common/wall_hedge.png` | 0 | yes | 2 |
| `jersey_barrier` | `assets/maps/common/wall_jersey_barrier.png` | 2 | no | 1 |

### Floors

| Key | Tile |
|---|---|
| `stone` | `assets/maps/werkhof/boden_stein.png` |
| `concrete` | `assets/maps/common/floor_concrete.png` |
| `grate` | `assets/maps/common/floor_grate.png` |
| `tiles` | `assets/maps/common/floor_tiles.png` |
| `sand` | `assets/maps/common/floor_sand.png` |
| `dirt` | `assets/maps/common/floor_dirt.png` |
| `stone_cracked` | `assets/maps/common/floor_stone_cracked.png` |
| `asphalt` | `assets/maps/common/floor_asphalt.png` |
| `metal_plate` | `assets/maps/common/floor_metal_plate.png` |
| `planks` | `assets/maps/common/floor_planks.png` |
| `carpet` | `assets/maps/common/floor_carpet.png` |
| `grass` | `assets/maps/common/floor_grass.png` |
| `gravel` | `assets/maps/common/floor_gravel.png` |
| `tiles_dark` | `assets/maps/common/floor_tiles_dark.png` |
| `cobble` | `assets/maps/common/floor_cobble.png` |

### Objects

| Key | Tile | Size in game | Pixels at 16 px/m | Blocks |
|---|---|---|---|---|
| `door` | `assets/maps/common/door_closed.png` | 2 × 2 m | 32 × 32 | yes |
| `spawn_barrier` | `assets/maps/common/spawn_barrier.png` | 2 × 2 m | 32 × 32 | yes |
| `barrel` | `assets/maps/common/props/barrel.png` | 0.75 × 0.75 m | 12 × 12 | yes |
| `crate_small` | `assets/maps/common/props/crate_small.png` | 0.75 × 0.75 m | 12 × 12 | yes |
| `pallet` | `assets/maps/common/props/pallet.png` | 1 × 0.56 m | 16 × 9 | no |
| `cone` | `assets/maps/common/props/cone.png` | 0.62 × 0.38 m | 10 × 6 | no |
| `plant` | `assets/maps/common/props/plant.png` | 0.62 × 0.5 m | 10 × 8 | yes |
| `lamp` | `assets/maps/common/props/lamp.png` | 1 × 1 m | 16 × 16 | no |
| `bench` | `assets/maps/common/props/bench.png` | 2 × 0.5 m | 32 × 8 | yes |
| `debris` | `assets/maps/common/props/debris.png` | 0.62 × 0.44 m | 10 × 7 | no |
| `container_large` | `assets/maps/common/props/container_large.png` | 6 × 2 m | 96 × 32 | yes |
| `car` | `assets/maps/common/props/car.png` | 4 × 2 m | 64 × 32 | yes |
| `generator` | `assets/maps/common/props/generator.png` | 1.5 × 1 m | 24 × 16 | yes |
| `dumpster` | `assets/maps/common/props/dumpster.png` | 2 × 1.25 m | 32 × 20 | yes |
| `crate_stack` | `assets/maps/common/props/crate_stack.png` | 1.5 × 1.5 m | 24 × 24 | yes |
| `vending_machine` | `assets/maps/common/props/vending_machine.png` | 1 × 0.75 m | 16 × 12 | yes |
| `table` | `assets/maps/common/props/table.png` | 1.5 × 1 m | 24 × 16 | yes |
| `chair` | `assets/maps/common/props/chair.png` | 0.5 × 0.5 m | 8 × 8 | no |
| `tree` | `assets/maps/common/props/tree.png` | 2 × 2 m | 32 × 32 | yes |
| `bush` | `assets/maps/common/props/bush.png` | 1 × 1 m | 16 × 16 | no |
| `rock` | `assets/maps/common/props/rock.png` | 1 × 0.75 m | 16 × 12 | yes |
| `pipe` | `assets/maps/common/props/pipe.png` | 2 × 0.5 m | 32 × 8 | yes |
| `pillar` | `assets/maps/common/props/pillar.png` | 1 × 1 m | 16 × 16 | yes |
| `boxes_cardboard` | `assets/maps/common/props/boxes_cardboard.png` | 1 × 0.75 m | 16 × 12 | yes |
| `trash_bin` | `assets/maps/common/props/trash_bin.png` | 0.5 × 0.5 m | 8 × 8 | yes |
| `ladder` | `assets/maps/common/props/ladder.png` | 1 × 2 m | 16 × 32 | no |
| `warning_sign` | `assets/maps/common/props/warning_sign.png` | 0.75 × 0.75 m | 12 × 12 | no |

### Decals (never block)

| Key | Tile | Size in game | Tiled |
|---|---|---|---|
| `crack` | `assets/maps/common/decals/crack.png` | 2 × 2 m | no |
| `oil_stain` | `assets/maps/common/decals/oil_stain.png` | 2 × 2 m | no |
| `scorch` | `assets/maps/common/decals/scorch.png` | 2 × 2 m | no |
| `arrow` | `assets/maps/common/decals/arrow.png` | 1 × 1 m | no |
| `drain` | `assets/maps/common/decals/drain.png` | 1 × 0.56 m | no |
| `hazard_stripe` | `assets/maps/common/decals/hazard_stripe.png` | 2 × 0.5 m | yes |
| `site_a` | `assets/maps/common/decals/site_a.png` | 1 × 1 m | no |
| `site_b` | `assets/maps/common/decals/site_b.png` | 1 × 1 m | no |
| `site_c` | `assets/maps/common/decals/site_c.png` | 1 × 1 m | no |
| `puddle` | `assets/maps/common/decals/puddle.png` | 2 × 2 m | no |
| `tire_marks` | `assets/maps/common/decals/tire_marks.png` | 2 × 2 m | no |
| `paint_line` | `assets/maps/common/decals/paint_line.png` | 2 × 0.25 m | yes |
| `footprints` | `assets/maps/common/decals/footprints.png` | 1 × 1 m | no |
| `grass_tuft` | `assets/maps/common/decals/grass_tuft.png` | 0.5 × 0.25 m | no |
| `manhole` | `assets/maps/common/decals/manhole.png` | 1 × 1 m | no |
| `leaves` | `assets/maps/common/decals/leaves.png` | 2 × 2 m | no |
| `paint_x` | `assets/maps/common/decals/paint_x.png` | 1 × 1 m | no |
