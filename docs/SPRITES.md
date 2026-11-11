# Sprites: Übergabe Coding ↔ Design

Coding-Sitzung trägt Bedarf ein, Design-Sitzung trägt Status und Datei ein.
Status: benötigt · in Arbeit · fertig · eingebaut

| Name | Größe (px) | Zweck | Animationen | Platzhalter | Status | Datei |
|---|---|---|---|---|---|---|
| figur_kestrel | 16×32 | Agent Kestrel (Duellant), eigene Figur | Stehen, Laufen 4, Ducken, Springen, Tot 32×16 | play.py: grauer Kreis mit Blickstrich | benötigt | |
| figur_marrow | 16×32 | Agent Marrow (Kontrolleur), eigene Figur | Stehen, Laufen 4, Ducken, Springen, Tot 32×16 | play.py: grauer Kreis mit Blickstrich | benötigt | |
| waffe_{key} | 16×8 | 16 Waffen aus gameplay/data/weapons.json in der Hand | – | nur Name im HUD | benötigt | |
| kauf_{key} | 32×12 | Waffen-Symbole im Kaufmenü | – | Textknöpfe | benötigt | |
| spike | 16×16 | Spike getragen, gelegt | Blinken 2 | rotes Quadrat | benötigt | |
| boden_stein, wand, kiste_metall | 32×32 | Kacheln Werkhof | – | einfarbige Flächen | benötigt (Entwurf im Sprite-Konzept) | |
| fx_muendung | 8×8 | Mündungsfeuer | 3 | gelbe Leuchtspur | benötigt (Entwurf im Sprite-Konzept) | |
| fx_dunst, fx_schleier, fx_bann, fx_lauscher, fx_funke | 64×64 | Fähigkeiten Marrow und Kestrel | je 3–6 | Kreise und Linien | benötigt | |
| icon_faehigkeit_{agent}_{C,Q,E,X} | 16×16 | Fähigkeitenleiste | – | Text | benötigt | |
| hud_* | Oberfläche | Leben, Schild, Munition, Credits, Zeit, Punktestand, Killfeed | – | Text in fixed_sys | benötigt | |
| logo, icon, playercard | 48×48, 64×128 | Ersatz für Riot-Logo | – | – | in Arbeit (docs/design/logo_entwurf.py) | |
