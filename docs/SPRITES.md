# Sprites: handover coding ↔ design

The coding session enters what is needed, the design session enters status and file.
Status: needed · in progress · done · integrated

The interface kit is generated with `python docs/design/sprites_ui.py` (Pillow), using the palette from
`config/client/theme.py`. Menu controls use nine-slice frames with 4 px corners (6 px for the large menu panel).
The agent ability icons are separately authored 32×32 transparent pixel sprites in
`assets/ui/ability_{agent}_{C,Q,E,X}.png`. They follow the official glyphs for the ability assigned to each
slot in the game's agent config. [VALORANT agent references](https://playvalorant.com/en-us/agents/)
Round banner sprites are 32 px high, and the circular minimap frame is 104×104. The game draws both at 2×
at the default resolution. The configurable in-game crosshair
is drawn at the selected size, gap and colour.

Agent art priority: Jett → Sova → Sage → Cypher → Phoenix → Killjoy.

Ascent's native 32×32 map tiles, props and decals are in `assets/maps/ascent/` and registered for editor use. See the [Ascent handover](design/ASCENT.md) for the draft, placement notes and outstanding map mechanics.

The 21 configured weapons share transparent, right-facing 32×16 sprites for the hand, HUD and buy menu in `assets/weapons/val2d/`. The normal and `_buy` files contain identical pixels. The sprites are drawn directly on the pixel grid with a limited palette, using the [VALORANT Arsenal](https://playvalorant.com/en-us/arsenal/) and the [Warden standard model](https://wiki.playvalorant.com/en-us/File:Warden.png) as silhouette references. Weapon IDs and filenames use the VALORANT names.

| Val2d keys | VALORANT models in the same order |
|---|---|
| `tactical_knife` | Tactical Knife |
| `classic`, `shorty`, `frenzy`, `ghost`, `bandit`, `sheriff` | Classic, Shorty, Frenzy, Ghost, Bandit, Sheriff |
| `stinger`, `spectre` | Stinger, Spectre |
| `bucky`, `judge` | Bucky, Judge |
| `bulldog`, `guardian`, `phantom`, `vandal`, `warden` | Bulldog, Guardian, Phantom, Vandal, Warden |
| `marshal`, `outlaw`, `operator` | Marshal, Outlaw, Operator |
| `ares`, `odin` | Ares, Odin |

Killjoy's character, enemy variants, and 16×32 ability animations are in `assets/agents/killjoy/`. C tosses the Nanoswarm grenade, Q lowers the Alarmbot to the ground, E deploys the Turret, and X places the Lockdown device. The [official UI glyphs](https://playvalorant.com/en-us/agents/killjoy/) were adapted to 32×32 icons. The devices use 16×16 effect frames, and the Nanoswarm field and Lockdown pulse use 64×64.

Phoenix's character, enemy variants, and 16×32 ability animations are in `assets/agents/phoenix/`. C sweeps out Blaze, Q flicks Curveball, E throws Hot Hands, and X adjusts the collar and ignites for Run It Back. The [official UI glyphs](https://playvalorant.com/en-us/agents/phoenix/) were adapted to 32×32 icons. The Blaze tile and projectiles use 16×16 FX frames, the flash, fire pool and return marker use 64×64, and the return overlay uses 16×32.

Cypher's character, enemy variants, and 16×32 ability animations are in `assets/agents/cypher/`. C places a Trapwire anchor, Q tosses the Cyber Cage emitter, E deploys the Spycam and transitions to camera control, and X lifts and throws the hat for Neural Theft. The [official UI glyphs](https://playvalorant.com/en-us/agents/cypher/) were adapted to 32×32 icons. Devices use 16×16 FX frames, the wire uses a 16×4 repeating tile, and the cage and scan use 64×64 frames.

Sage's character, enemy variants, and 16×32 ability animations are in `assets/agents/sage/`. C raises the Barrier, Q throws the Slow Orb, E casts Healing Orb, and X channels Resurrection. The [official UI glyphs](https://playvalorant.com/en-us/agents/sage/) were adapted to 32×32 icons. Barrier segments and the Slow Orb projectile use 16×16 frames, the slow field uses 64×64, and heal and revive overlays use 16×32.

Sova's character, enemy variants, and 16×32 ability animations are in `assets/agents/sova/`. C deploys the Owl Drone, Q/E draw and release the bow, and X charges and releases Hunter's Fury. The [official UI glyphs](https://playvalorant.com/en-us/agents/sova/) were adapted to 32×32 icons. Drone and bolt effects use 16×16 frames. Pulse, impact and beam effects use 64×64 frames.

Jett's redrawn character and FX pack is in the project. The original asset sizes and frame counts are preserved. The 16×32 cast/channel frames show C forming and throwing Cloudburst, Q rising into Updraft, E bracing and dashing with Tailwind, and X drawing and releasing the Blade Storm kunai. The 32×32 icons are adapted from the [official Jett page](https://playvalorant.com/en-us/agents/jett/).

The original Val2d character design now has movement, combat, objective, and separate cast/channel strips for C Shrouded Step, Q Paranoia, E Dark Cover, and X From the Shadows. The PNGs in `assets/agents/omen/` use the blueprint's native cells. The matching 32×32 icons are in `assets/ui/`, and the 64×64 effect frames are in `assets/fx/`.

The 16×32 cast/channel frames in `assets/agents/brimstone/` show C holding and throwing the Stim Beacon, Q raising and firing the Incendiary launcher, and E/X projecting the orange tactical map from the forearm. The projection stays orange over the enemy outline. Use `check_agent_sprites.py brimstone --no-enemy` to validate the custom enemy frames. The 32×32 icons and native-size ability effects are in `assets/ui/` and `assets/fx/`.

| Name | Size (px) | Purpose | Animations | Placeholder | Status | File |
|---|---|---|---|---|---|---|
| weapon_{key} | 32×16 | Weapons from config/content/weapons.py, held in hand and shown in the HUD | – | name only in the HUD | done | assets/weapons/val2d/{key}.png, knife: tactical_knife.png |
| buy_{key} | 32×16 | Weapon icons in the buy menu, identical to the corresponding hand sprites | – | text buttons | done | assets/weapons/val2d/{key}_buy.png |
| spike | 16×16 | Spike carried, planted | Blink 2 | red square | done | assets/fx/spike.png (strip 2×16×16: on, off) |
| stone_floor, wall, metal_crate | 32×32 | Workyard tiles | – | single-color areas | done | assets/maps/workyard/{stone_floor,wall,wall_thin,metal_crate,platform,ramp,site_border}.png |
| fx_muzzle_flash | 8×8 | Muzzle flash | 3 | yellow tracer | done | assets/fx/muzzle_flash.png (strip 3×8×8) |
| hud_* | icons 16×16, bars 96×12, frames 24×24 (nine-slice, 4 px corners) | Health, shield, ammo, credits, time, score, killfeed | – | themed text and shapes | integrated | assets/ui/hud/*.png |
| logo, icon, playercard | 48×48, 64×128 | Logo, window icon, player card | – | – | done | assets/logo.png, assets/icon.ico (16/32/48), assets/menu/lobby/playercard.png (crosshair) |
| minimap_* | 12×12 | Minimap: you, ally, enemy, eliminated, Spike, Smoke, Slow field, Vapor wall | – | – | done | assets/ui/minimap/{self,ally,enemy,eliminated,spike,smoke,slow_field,vapor_wall}.png |
| banner_* | width per text × 32 | Victory, Defeat, Switching sides, Bomb planted, Bomb defused, Overtime | – | text in the HUD | integrated | assets/ui/banner/{victory,defeat,switching_sides,bomb_planted,bomb_defused,overtime}.png |
| fx_animations | per effect | smoke_forming 4×64, slow_field_pulse 3×64, sensor_pulse 3×32, flash_burst 3×16, dash_trail 3×16×32, hop_dust 3×16×8, vapor_wall_forming 3×16, spike_explosion 6×64, wall_impact 3×8, body_hit 3×8 | see purpose | – | done | assets/fx/*.png, horizontal strips |
| fx_zone, fx_blast, fx_tripwire, fx_alarm, fx_wave | 64×64 / 16×16 | Generic effects of the new building blocks: area zone (tinted per status), blast ring, tripwire line tile, alarm device, wave along a line | 3–6 each | circles and lines | done | assets/fx/zone.png (3×64, white, tint in code), blast.png (6×64, scale to radius), tripwire.png (16×4 tile), tripwire_node.png (6×6), alarm.png (2×16 blink), wave.png (3×16 tile along the line) |
| status_{nearsight,concuss,slow,vulnerable,decay,suppress,detain,deaf,stim} | 16×16 | Status icons for the HUD | – | text | done | assets/ui/status/{key}.png |
| ui_menu_* | 16×16 / 24×24 nine-slice, 480×270 | Menu kit offered by design: button (normal, hover, pressed, disabled), panel, textfield, tab (+ active), checkbox (+ on), slider track/fill/knob, mouse cursor, title background | – | – | done | assets/ui/menu/*.png; nine-slice corners 4 px (panel 6 px) |
| ui_icons_* | 8×8 / 16×16 | Interface icons offered by design: close, arrows, check, plus, minus, lock, gear, sound on/off, mic, person, trophy, skull, ping_0–3, round_win/loss/empty, credits_large (12×12), role_{duelist,initiator,controller,sentinel}, side_{attack,defense} | – | – | done | assets/ui/icons/*.png |
| ui_buy_* | 16×16, vests 64×24 | Buy menu offered by design: category icons cat_{sidearm,smg,shotgun,rifle,sniper,heavy,armor,abilities}, vest_light, vest_heavy | – | – | done | assets/ui/buy/*.png |
| maps_common_* | 32×32 | Common tile set offered by design: floor_{concrete,grate,tiles,sand,dirt,stone_cracked}, wall_{brick,concrete}, fence_wood, window_glass, door_{closed,open}, spawn_barrier (2 frames), wall_shadow (32×8), platform_edge (32×4) | – | – | done | assets/maps/common/*.png |
| maps_props_*, maps_decals_* | 6–32 px | Props: barrel, crate_small, pallet, cone, plant, lamp, debris, bench. Decals (alpha): crack, oil_stain, arrow, site_{a,b,c}, hazard_stripe, drain, scorch | – | – | done | assets/maps/common/props/*.png, assets/maps/common/decals/*.png |
| fx_ability_* | 3–16 px, 16×32 | Generic ability sprites: projectile_orb (2), projectile_dart, grenade, arc_dot, mine (2), beacon (2, reveal_all), anchor_marker (2), decoy_step, reveal_marker (2), impact_puff (3); on the figure, 16×32 cell like agents: teleport (4), heal (3), revive (4), shield_shell (3), immunity_aura (2) | – | – | done | assets/fx/ability/*.png |
| extras_batch4 | see file column | Everything the game still drew as shapes (list of 12.11.2026) | sound_ring 3 frames | shapes, text | done | fx/tracer.png, tracer_own.png (16×2, tile along the shot), fx/sound_ring.png (3×64, white, tint), fx/radius_ring.png (64×64 dashed, white, tint), fx/facing_marker.png (8×8, points up, white, tint); ui/crosshair/dot.png, dot_hit.png (4×4), arm.png, arm_hit.png (2×8, points up); ui/minimap/frame.png (24×24 nine-slice, 8 px corners, semi-transparent), wall.png, crate.png (4×4); ui/hud/killfeed_row.png, killfeed_row_self.png, score_panel.png, weapon_panel.png, ability_panel.png (24×24 nine-slice, 8 px corners); ui/scoreboard/row.png, row_self.png, header_team_a.png (teal), header_team_b.png (red) (24×24 nine-slice); ui/hud/carrier_hint.png (16×16) |
| maps_common_set2 | 32×32 tiles, props various | Map elements offered by design. Floors: floor_{asphalt,metal_plate,planks,carpet,grass,gravel,tiles_dark,cobble}. Walls: wall_{metal_sheet,sandbags,stone,container,hedge,jersey_barrier}, fence_chainlink (see-through). Props: container_large 96×32, car 64×32, generator 24×16, dumpster 32×20, crate_stack 24×24, vending_machine 16×12, table 24×16, chair 8×8, tree 32×32, bush 16×16, rock 16×12, pipe 32×8, pillar 16×16, boxes_cardboard 16×12, trash_bin 8×8, ladder 16×32, warning_sign 12×12. Decals: puddle, tire_marks, paint_line (32×4, tiled), footprints, grass_tuft, manhole, leaves, paint_x | – | – | done | assets/maps/common/*.png, props/*.png, decals/*.png; source docs/design/sprites_world2.py |

## Directional figures

All eight selectable agents have back and right-profile strips for the 24 movement, combat, objective,
ability and victory states. Every strip has 16×32 cells and the frame count of its front equivalent.
Red-outline variants use the `_enemy` suffix. See the [figure view guide](design/FIGURE_VIEWS.md).

The [custom roster archive](../archive/custom-agents/README.md) contains the retired agents and their source assets.
