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
| hud_* | Oberfläche | Leben, Schild, Munition, Credits, Zeit, Punktestand, Killfeed | – | Text in fixed_sys | benötigt | |
| logo, icon, playercard | 48×48, 64×128 | Ersatz für Riot-Logo | – | – | Entwürfe, Wahl offen | docs/design/logo-entwurf/ |
