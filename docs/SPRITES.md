# Sprites: handover coding ↔ design

The coding session enters what is needed, the design session enters status and file.
Status: needed · in progress · done · integrated

| Name | Size (px) | Purpose | Animations | Placeholder | Status | File |
|---|---|---|---|---|---|---|
| figur_kestrel | 16×32 | Agent Kestrel (Duelist), custom character | Idle, Walk 4, Crouch, Jump, Dead 32×16 | play.py: grey circle with facing line | done | assets/agents/kestrel/kestrel_{idle,walk,crouch,jump,dead,portrait}.png; enemy: *_feind.png; walk = strip 4×16×32 |
| figur_marrow | 16×32 | Agent Marrow (Controller), custom character | Idle, Walk 4, Crouch, Jump, Dead 32×16 | play.py: grey circle with facing line | done | assets/agents/marrow/marrow_{idle,walk,crouch,jump,dead,portrait}.png; enemy: *_feind.png; walk = strip 4×16×32 |
| waffe_{key} | 16×8 | 16 weapons from gameplay/data/weapons.json, held in hand | – | name only in the HUD | done | assets/weapons/val2d/{key}.png, knife: messer.png |
| kauf_{key} | 32×12 | Weapon icons in the buy menu | – | text buttons | done | assets/weapons/val2d/{key}_kauf.png |
| spike | 16×16 | Spike carried, planted | Blink 2 | red square | done | assets/fx/spike.png (strip 2×16×16: on, off) |
| boden_stein, wand, kiste_metall | 32×32 | Werkhof tiles | – | single-color areas | done | assets/maps/werkhof/{boden_stein,wand,wand_duenn,kiste_metall,plattform,rampe,platz_rand}.png |
| fx_muendung | 8×8 | Muzzle flash | 3 | yellow tracer | done | assets/fx/muendung.png (strip 3×8×8) |
| fx_dunst, fx_schleier, fx_bann, fx_lauscher, fx_funke | 64×64 | Abilities of Marrow and Kestrel | 3–6 each | circles and lines | done | assets/fx/dunst.png 64, bann.png 64, schleier.png 16 (tiles along the wall), funke.png 16, lauscher.png 6; 1 image each |
| icon_faehigkeit_{agent}_{C,Q,E,X} | 16×16 | Ability bar | – | text | done | assets/ui/faehigkeit_{agent}_{C,Q,E,X}.png |
| hud_* | interface | Health, shield, ammo, credits, time, score, killfeed | – | text in fixed_sys | done | assets/ui/hud/: leben, schild, credits, munition, kopfschuss, spike_klein, uhr, tot (8×8); rahmen, rahmen_aktiv (12×12, 9-slice, corners 4 px); balken_leben, balken_schild, balken_fortschritt, balken_leer (48×6, horizontally stretchable) |
| logo, icon, playercard | 48×48, 64×128 | Replacement for the Riot logo | – | – | done | assets/logo.png, assets/icon.ico (16/32/48), assets/menu/lobby/playercard.png (crosshair) |
| minimap_* | 8×8 | Minimap: you, ally, enemy, eliminated, Spike, Dunst, Bann, Schleier | – | – | done | assets/ui/minimap/{selbst,verbuendet,feind,tot,spike,dunst,bann,schleier}.png |
| banner_* | width per text × 21 | Round banners: Victory, Defeat, Switching sides, Bomb planted, Bomb defused, Overtime (English text in image) | – | text in the HUD | done | assets/ui/banner/{sieg,niederlage,seitenwechsel,spike_gelegt,entschaerft,verlaengerung}.png |
| figur_aktionen | 16×32 per frame | Shooting (2 frames, 12/s), reloading (4, 6/s), casting an ability (3, 8/s) for Kestrel and Marrow | see purpose | – | done | assets/agents/{kestrel,marrow}/{key}_{shoot,reload,cast}.png, enemy *_feind.png; horizontal strips |
| fx_animationen | per effect | dunst_aufbau 4×64, bann_puls 3×64, lauscher_puls 3×32, funke_explosion 3×16, gleiten_spur 3×16×32, satz_staub 3×16×8, schleier_aufbau 3×16, spike_explosion 6×64, einschlag_wand 3×8, treffer_koerper 3×8 | see purpose | – | done | assets/fx/*.png, horizontal strips |
