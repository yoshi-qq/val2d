# Sprites: Übergabe Coding ↔ Design

Coding-Sitzung trägt Bedarf ein, Design-Sitzung trägt Status und Datei ein.
Status: benötigt · in Arbeit · fertig · eingebaut

| Name | Größe (px) | Zweck | Animationen | Platzhalter | Status | Datei |
|---|---|---|---|---|---|---|
| figur_kestrel | 16×32 | Agent Kestrel (Duellant), eigene Figur | Stehen, Laufen 4, Ducken, Springen, Tot 32×16 | play.py: grauer Kreis mit Blickstrich | fertig | assets/agents/kestrel/kestrel_{idle,walk,crouch,jump,dead,portrait}.png; Gegner: *_feind.png; walk = Streifen 4×16×32 |
| figur_marrow | 16×32 | Agent Marrow (Kontrolleur), eigene Figur | Stehen, Laufen 4, Ducken, Springen, Tot 32×16 | play.py: grauer Kreis mit Blickstrich | fertig | assets/agents/marrow/marrow_{idle,walk,crouch,jump,dead,portrait}.png; Gegner: *_feind.png; walk = Streifen 4×16×32 |
| waffe_{key} | 16×8 | 16 Waffen aus gameplay/data/weapons.json in der Hand | – | nur Name im HUD | fertig | assets/weapons/val2d/{key}.png, Messer: messer.png |
| kauf_{key} | 32×12 | Waffen-Symbole im Kaufmenü | – | Textknöpfe | fertig | assets/weapons/val2d/{key}_kauf.png |
| spike | 16×16 | Spike getragen, gelegt | Blinken 2 | rotes Quadrat | fertig | assets/fx/spike.png (Streifen 2×16×16: an, aus) |
| boden_stein, wand, kiste_metall | 32×32 | Kacheln Werkhof | – | einfarbige Flächen | fertig | assets/maps/werkhof/{boden_stein,wand,wand_duenn,kiste_metall,plattform,rampe,platz_rand}.png |
| fx_muendung | 8×8 | Mündungsfeuer | 3 | gelbe Leuchtspur | fertig | assets/fx/muendung.png (Streifen 3×8×8) |
| fx_dunst, fx_schleier, fx_bann, fx_lauscher, fx_funke | 64×64 | Fähigkeiten Marrow und Kestrel | je 3–6 | Kreise und Linien | fertig | assets/fx/dunst.png 64, bann.png 64, schleier.png 16 (kacheln entlang der Wand), funke.png 16, lauscher.png 6; je 1 Bild |
| icon_faehigkeit_{agent}_{C,Q,E,X} | 16×16 | Fähigkeitenleiste | – | Text | fertig | assets/ui/faehigkeit_{agent}_{C,Q,E,X}.png |
| hud_* | Oberfläche | Leben, Schild, Munition, Credits, Zeit, Punktestand, Killfeed | – | Text in fixed_sys | fertig | assets/ui/hud/: leben, schild, credits, munition, kopfschuss, spike_klein, uhr, tot (8×8); rahmen, rahmen_aktiv (12×12, 9-Teile, Ecken 4 px); balken_leben, balken_schild, balken_fortschritt, balken_leer (48×6, waagerecht dehnbar) |
| logo, icon, playercard | 48×48, 64×128 | Ersatz für Riot-Logo | – | – | fertig | assets/logo.png, assets/icon.ico (16/32/48), assets/menu/lobby/playercard.png (Fadenkreuz) |
| minimap_* | 8×8 | Minimap: Du, Verbündet, Gegner, Ausgeschaltet, Spike, Dunst, Bann, Schleier | – | – | fertig | assets/ui/minimap/{selbst,verbuendet,feind,tot,spike,dunst,bann,schleier}.png |
| banner_* | Breite je Text × 21 | Rundenbanner: Sieg, Niederlage, Seitenwechsel, Spike gelegt, Entschärft, Verlängerung | – | Text im HUD | fertig | assets/ui/banner/{sieg,niederlage,seitenwechsel,spike_gelegt,entschaerft,verlaengerung}.png |
| figur_aktionen | 16×32 je Bild | Schießen (2 Bilder, 12/s), Nachladen (4, 6/s), Fähigkeit wirken (3, 8/s) für Kestrel und Marrow | siehe Zweck | – | fertig | assets/agents/{kestrel,marrow}/{key}_{shoot,reload,cast}.png, Gegner *_feind.png; Streifen waagerecht |
| fx_animationen | je Effekt | dunst_aufbau 4×64, bann_puls 3×64, lauscher_puls 3×32, funke_explosion 3×16, gleiten_spur 3×16×32, satz_staub 3×16×8, schleier_aufbau 3×16, spike_explosion 6×64, einschlag_wand 3×8, treffer_koerper 3×8 | siehe Zweck | – | fertig | assets/fx/*.png, Streifen waagerecht |
