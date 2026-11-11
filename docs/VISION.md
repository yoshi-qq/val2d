# Val2d – Vision

Stand: 11.11.2026 · Christian Abel · Quelle: Visionsbogen und Rückfragen im Chat

## Kern

Val2d ist ein taktischer 2D-Shooter, der sich spielt wie VALORANT. **Regeln, Systeme, Waffenbalance und Spielgefühl so nah wie möglich am Original.** Abgewichen wird nur dort, wo 2D eine Mechanik wirklich unmöglich macht; dann gibt es eine 2D-Lösung, die dem Original im Ergebnis möglichst nahekommt (Beispiel: Trefferzonen, siehe unten).

**Inhalte von Riot werden nicht nachgebaut, auch nicht umbenannt:** Agents mit ihren Fähigkeiten-Kits, Maps, Namen von Agents, Maps und Waffen, Grafiken, Sounds, Logos. Riots Fan-Richtlinie verbietet die Nutzung ihrer IP in Spielen ausdrücklich, auch nichtkommerziell. Agents, Fähigkeiten, Maps und Waffennamen sind eigene Entwürfe; Agents werden über eine Config zusammengestellt (siehe „Agents und Fähigkeiten“).

Was sich wie Valorant anfühlen muss:
- Gunplay: First-Shot-Accuracy, Counter-Strafing, Spray
- Fähigkeiten und Utility
- Economy (Credits, Eco-, Force- und Vollkauf)
- Sound als Information
- Rundenstruktur mit Bombe
- Agentenwahl und Teamkomposition

Für wen: Freunde im LAN, Freunde über das Internet, solo gegen Bots. Kein öffentliches Matchmaking mit Fremden geplant.

Nicht kommerziell. Sprites entstehen im eigenen Pixel-Art-Stil.

## Darstellung

- **Perspektive:** von oben, mit Höhenebenen (z). Kisten, Treppen und Sprünge zählen spielerisch.
- **Figuren:** Sprites sind so gezeichnet, als lägen die Figuren auf dem Boden (Vorderansicht flach auf die Map gelegt): oben im Sprite der Kopf, unten die Beine.
- **Sicht:** Sichtkegel in Blickrichtung, Rest verdeckt (Standard). Als Lobby-Regel umschaltbar auf Rundumsicht (Wände verdecken weiterhin).
- **Kamera:** in Zielrichtung vorgeschoben; Stärke als Spieler-Einstellung.
- **Stil:** Pixel-Art im Stil der vorhandenen Aseprite-Dateien. Neue Designs entstehen gemeinsam mit Christian, er prüft jedes Sprite auf Stiltreue.
- **Eingabe:** Tastatur und Maus.

## Zwei Sitzungen

Val2d entsteht in zwei getrennten Sitzungen:

- **Coding-Sitzung** (Claude Code, lokal auf dem PC): Code, Spiellogik, Netzwerk, Spielwerte, Tests. Nutzt für Grafik vorhandene Assets oder klar benannte Platzhalter und erzeugt keine finalen Sprites.
- **Design-Sitzung** (Chat in claude.ai mit Christian): Sprites, Animationen und Oberflächen im eigenen Pixel-Art-Stil. Christian prüft jedes Design auf Stiltreue. Ergebnis sind Dateien in `assets/`.

**Übergabe zwischen beiden:** `docs/SPRITES.md`. Die Coding-Sitzung trägt ein, was gebraucht wird (Name, Größe in Pixeln, Zweck, Animationen, Platzhalter-Pfad). Die Design-Sitzung trägt den Status und den Pfad der fertigen Datei ein. Die Coding-Sitzung ersetzt dann den Platzhalter.

## Gunplay

- **Streuung wie Valorant:** stehend ist die erste Kugel exakt; Laufen, Springen und Spray streuen zufällig in festem Rahmen. Spray-Muster ungefähr wie im Original (in Valorant bewusst nicht vollständig konstant lernbar). Glück soll nur haben, wer falsch schießt.
- **Treffer und Zonen: reine Präzision**, siehe „Trefferzonen in 2D“.
- **Wanddurchschuss** nach Penetrationsstufe des Materials, wie in Valorant.
- **Maßstab:** echte Meter. Laufgeschwindigkeiten, Reichweiten und Schadensabfall nach den echten Werten.
- **Waffenwerte:** Zahlen aus den offiziellen Valorant-Patchnotes (Schaden, Feuerrate, Magazin, Preise, Streuung), mit Patchnummer und Quelle in einer Datendatei. Waffen tragen eigene Namen.

### Trefferzonen in 2D

Die Zone (Kopf, Körper, Beine) wird über zwei Achsen relativ zur Schusslinie bestimmt, mit unterschiedlicher Skalierung:

- **Quer zur Schusslinie (x):** exakt die Breiten der Zonen im Sprite. Wer seitlich daneben zielt, trifft nicht bzw. trifft die schmalere Zone nicht.
- **Entlang der Schusslinie (y, Tiefe):** entscheidet die Höhe am Körper. Maßgeblich ist, ob der Mauszeiger *auf* dem Ziel lag oder davor bzw. dahinter. Der Mittelpunkt ist der Kopf. Je weiter der Cursor davor oder dahinter lag, desto tiefer am Körper der Treffer. Die erlaubte Abweichung ist deutlich größer als der Sprite, weil die Kugel in Schussrichtung weiterfliegt.
- **Bedingung:** Cursor und Ziel liegen auf derselben Höhenebene (z).
- **Mindestens Beine:** Liegen Cursor und Ziel auf derselben Ebene und geht die Schusslinie durch den Gegner (Querabstand innerhalb der größten Sprite-Breite), ist immer mindestens ein Beintreffer möglich, auch außerhalb jeder Tiefentoleranz oder seitlich neben der Zone, die die Tiefe vorgibt.
- **Ansicht:** Die Kamera dreht mit der Maus, gezielt wird auf dem Bildschirm immer senkrecht nach oben. x und y sind damit die Bildschirmachsen. Gegner-Sprites stehen auf dem Bildschirm aufrecht und drehen nicht mit der Welt.
- **Kopf knapp verfehlt:** Tiefe passt zum Kopf, seitlich daneben, aber innerhalb der Körperbreite: Körpertreffer.
- **Andere Ebene:** Liegt der Cursor auf einer anderen Höhenebene als das Ziel: Fehlschuss.
- **Demo:** Artefakt „Val2d-Trefferlogik“ (claude.ai) zeigt die Logik interaktiv.
- **Einstellbar:** Die erlaubten Abweichungen je Zone stehen in der Game-Config und werden von Christian eingestellt, nicht im Code festgelegt.

## Spielablauf

- **Teams:** flexibel von 1 gegen 1 bis 5 gegen 5.
- **Bots:** füllen freie Plätze. Erster Stand: einfache Bots (laufen, zielen, Bombe legen und entschärfen). Gute Bots sind ein eigener Ausbauschritt.
- **Partielänge:** einstellbar, Standard wie im Original (13 Siegrunden, Overtime).
- **Sound:** echter Stereo-Raumklang. Sichtbare Schallringe als Lobby-Einstellung, gilt für alle oder niemanden, standardmäßig aus.
- **Host:** beides möglich. Ein Spieler hostet und spielt mit (Standard, wenn nichts anderes eingestellt ist: Host = Spieler 1), oder ein eigener Server-Prozess.

## Agents und Fähigkeiten

- **Festlegung in `config/agents.json`**, von Christian bearbeitbar: je Agent Name, Rolle, Spriteset und vier Fähigkeiten (Tasten Q, E, C, X). Je Fähigkeit: Baustein, Parameter (z. B. Radius, Dauer, Reichweite), Kosten, Ladungen, Abklingzeit; für X die Ultimate-Punkte.
- **Bausteine:** Eine Fähigkeit wird aus drei frei kombinierbaren Teilen zusammengesetzt, jeweils mit Parametern in der Config:
  - **Auslösung:** werfen (mit Abprallen, Flugzeit), platzieren, über die Taktikkarte zielen, auf sich selbst, als Projektil, als Falle mit Auslöser.
  - **Form:** Kreis, Wand oder Linie, Kegel, Punkt; Größe, Höhenebene, Dauer.
  - **Wirkung (auch mehrere):** Sicht blockieren, blenden, verlangsamen, Schaden über Zeit oder sofort, heilen, aufdecken, Bewegung (Dash, Sprung, Teleport), Schild oder Barriere, Lärm erzeugen.
  Neue Teile kommen als Code dazu, neue Fähigkeiten nur über die Config. Technische Namen im Code, angezeigte Namen in der Config.
- **Orientierung an Valorant:** Rollen (Duelist, Initiator, Controller, Sentinel), Designgrundsätze (jede Fähigkeit hat Gegenspiel, ist auf einen Blick lesbar, kostet Credits oder hat Ladungen und Abklingzeit; Teams brauchen Info, Sichtblock, Einstieg und Absicherung) und das Spielgefühl einer Runde. Einzelne Agents, Kits und Maps sind dabei keine Gegenstücke zu bestimmten Valorant-Inhalten.
- **Mitgeliefert** werden nur eigene Beispiel-Agents mit eigenem Kit. Keine Voreinstellungen, die Kits, Namen oder Werte von Valorant-Agents nachbilden.
- Fehler in der Config (unbekannter Baustein, fehlender Wert) werden beim Start gemeldet, der Agent wird übersprungen; das Spiel stürzt nicht ab.

## Erster fertiger Stand

- Modus: Unrated
- Maps: eine eigene Standard-Map nach dem bekannten Bauplan (zwei Bombenplätze, Mitte, Angreifer- und Verteidiger-Spawn, Callouts) und eine einfache 1-gegen-1-Map; beide im Map-Editor bearbeitbar
- Agents: zwei eigene Beispiel-Agents (ein Controller, ein Duelist) mit eigenem Kit, festgelegt in `config/agents.json`
- Fähigkeiten-Bausteine für beide Kits, erweiterbar
- Alle Waffen (eigene Namen, echte Zahlen), Kaufmenü, Economy, Bombe, Runden
- Netzwerk über den neuen Wrapper (LAN und Internet)

## Danach

Ausbau in dieser Reihenfolge: mehr Agents, weitere Modi, mehr Maps.
