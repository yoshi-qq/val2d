# Entscheidungen

Format: Datum · wer · Bereich · Wortlaut

- 11.11.2026 · Christian · Grundsatz · Immer möglichst nah an Valorant; abweichen nur, wenn 2D eine Mechanik wirklich unmöglich macht.
- 11.11.2026 · Christian · Gunplay · Streuung wie Valorant: stehend erste Kugel exakt, Laufen und Spray zufällig in festem Rahmen.
- 11.11.2026 · Christian · Gunplay · Trefferzonen über Querabstand (exakte Sprite-Breiten) und Tiefenabstand des Cursors (Kopf = Mittelpunkt, große erlaubte Abweichung), nur auf gleicher Höhenebene; Abweichungen in der Game-Config.
- 11.11.2026 · Christian · Gunplay · Wanddurchschuss nach Penetrationsstufe.
- 11.11.2026 · Christian · Welt · Maßstab in echten Metern, Werte aus den Patchnotes mit Patchnummer.
- 11.11.2026 · Christian · Darstellung · Von oben mit Höhenebenen; Sichtkegel als Standard, Rundumsicht als Lobby-Regel; Kamera vorgeschoben (Spieler-Einstellung); Pixel-Art im eigenen Stil.
- 11.11.2026 · Christian · Spielablauf · Teams 1v1 bis 5v5; einfache Bots im ersten Stand; Partielänge einstellbar, Standard Original; Schallringe als Lobby-Einstellung, Standard aus.
- 11.11.2026 · Christian · Netzwerk · Host = Spieler 1 als Standard, eigener Server-Prozess möglich. Internet-Modus Peer-to-peer über öffentliche STUN-Server, erst ohne Relay. pickle nur im alten LAN-Modus.
- 11.11.2026 · Christian · Umfang · Erster Stand: Unrated, Ascent + einfache 1v1-Map, Omen + Jett, alle Waffen. Danach: Agents, Modi, Maps.
- 11.11.2026 · Christian · Pakete · graphy und networking als GitHub-Repos unter yoshi-qq, editierbar installiert; Import-Namen bleiben.
- 11.11.2026 · Christian · Gunplay · Trefferlogik in der Demo bestätigt. Gleiche Ebene und Schusslinie durch den Gegner: immer mindestens Beintreffer. Kamera dreht mit, Zielen immer senkrecht nach oben; x/y = Bildschirmachsen.
- 11.11.2026 · Christian · Gunplay · Kopf knapp verfehlt (innerhalb Körperbreite): Körper. Cursor auf anderer Ebene: Fehlschuss. Gegner-Sprites stehen auf dem Bildschirm aufrecht.
- 11.11.2026 · Christian · Inhalte · Ersetzt den Umfang-Eintrag oben: Keine Valorant-Agents, -Kits, -Maps oder -Namen, auch nicht umbenannt (Riots Fan-Richtlinie verbietet IP in Spielen). Agents über config/agents.json (Name, Rolle, Spriteset, Fähigkeiten aus Bausteinen). Erster Stand: zwei eigene Beispiel-Agents (Controller, Duelist), eigene Standard-Map + 1v1-Map, Waffen mit eigenen Namen und echten Zahlen, Bombe statt Spike.
- 11.11.2026 · Christian · Grafik · Maßstab 16 px = 1 m (Figur 16×32, Kachel 32×32 = 2 m, Sicht 480×270 nativ, ×4). Licht von oben links.
- 11.11.2026 · Christian · Grafik · Kontur: Außenkante in dunkler Eigenfarbe je Material, innerhalb der Sprite-Breite; Trefferbreiten zählen ohne Kontur.
- 11.11.2026 · Christian · Grafik · Teamkennung: Sprites teamneutral, Gegner mit rotem Umriss wie in Valorant; Farbe später Spieler-Einstellung.
- 11.11.2026 · Christian · Grafik · Schattierung: zwei Stufen je Material (Grundton, Schatten), wie im Bestand. Konzept: docs/design/sprite-konzept.html
- 11.11.2026 · Christian · Inhalte · Orientierung an Valorant bei Rollen, Designgrundsätzen und Spielgefühl; eigene Agents, Kits und Maps sind keine Gegenstücke zu bestimmten Valorant-Inhalten.
- 11.11.2026 · Claude Code · Grundsatz · Keine Nachbildung von Riot-Inhalten (Agents, Fähigkeiten, Karten, Namen). Mechaniken nach VISION.md, Inhalte eigen: Agents Kestrel und Marrow, Karte Werkhof, 16 eigene Waffen. Christian sieht das anders (VISION.md); offen.
- 11.11.2026 · Claude Code · Technik · Neuer Spielkern gameplay/ (ohne pygame, befehlsgesteuert, JSON-Abbild statt pickle), spielbar über play.py gegen Bots. Alter Pfad main.py bleibt unverändert.
- 11.11.2026 · Claude Code · Werte · Alle Spielwerte eigener Entwurf in gameplay/data/*.json (Quelle je Datei), Trefferzonen und Lobby-Standards in config/game_config.json.
