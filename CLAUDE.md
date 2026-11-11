# Val2d – Kontext für Claude Code

VALORANT in 2D, Python + pygame. Lies vor jeder Arbeit:
- docs/VISION.md – was Val2d sein soll (verbindlich)
- docs/ENTSCHEIDUNGEN.md – getroffene Entscheidungen; neue mit Datum, wer, Bereich anhängen
- roadmap.md – alter Arbeitsstand

## Arbeitsteilung
Du bist die **Coding-Sitzung**. Grafik kommt aus der **Design-Sitzung** mit Christian (Chat in claude.ai). Übergabe über docs/SPRITES.md, Einzelheiten in docs/VISION.md, Abschnitt „Zwei Sitzungen“.

## Regeln
- Möglichst nah an Valorant. Weicht etwas ab, Begründung in docs/ENTSCHEIDUNGEN.md.
- Spielwerte nie im Code verstreuen: Datendatei mit Patchnummer und Quelle je Wert.
- Werte, die Christian einstellt (z. B. Treffer-Toleranzen), gehören in die Game-Config.
- Keine Riot-Inhalte nachbauen, auch nicht umbenannt: keine Valorant-Agents oder ihre Kits, keine Valorant-Maps, keine Namen von Agents, Maps oder Waffen. Systeme, Regeln und Waffenzahlen dürfen dem Original folgen. Agents laufen über config/agents.json mit Fähigkeiten-Bausteinen.
- Grafik und Sprites liefert die Design-Sitzung mit Christian. Bis dahin Platzhalter, klar als solche benannt. Keine Riot-Grafiken, -Sounds oder -Logos.
- graphy und networking kommen aus den Paketen (keine lokalen Kopien). Netzwerk im Spiel über den Wrapper netplay (Arbeitsname).
- Neuer Code: snake_case, Type Hints, keine TODOs im fertigen Code. Nicht-fatale Fehler warnen, nie abstürzen. Zeit intern UTC.
- Nie als geprüft melden, was nicht lief.
