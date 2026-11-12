# Ascent in Val2d

The playable map is [ascent.py](../../gameplay/data/maps/ascent.py). It is traced at real scale from the tactical map in the official minimap projection (1656 px = 142.86 m): `GRID` holds one character per square metre (`#` wall, `.` floor level 0, `1` one storey up, `3` A Heaven). Stairs between levels, doors, the A Window glass, spawn barriers, callouts, floors and cover are listed below the grid; their positions are given in pixels of the reference map, so each can be checked against it.

| Area | Levels |
| --- | --- |
| A | Front (A Main exit, Switch, Bricks) on 0, site plateau on 1 with stairs, Heaven and A Window on 3 (stairs from the A connector, drop to the site), Garden on 1 with stairs down to Tree (0), A door between Tree and the site front |
| Mid | Courtyard and Link on 0, Mid Top, Catwalk and Cubby on 1 (catwalk stairs, steps from Mid Top, steps from Cubby down to Tree), arch stairs up to Mid Bottom (1) |
| B | Site, Boathouse, Workshop and Lane on 0, Market door platform on 1 with log steps, CT stairs up to the B connector (1), Market door between the platform and Mid Market |
| Spawns | Attackers on 0 with steps up to Mid Top, defenders on 1 |

The older blockout [_ascent.py](../../gameplay/data/maps/_ascent.py) stays as an editor draft (`python map_editor.py _ascent`). Deviations from VALORANT are in [ENTSCHEIDUNGEN.md](../ENTSCHEIDUNGEN.md).

References: [Riot Games map gallery](https://playvalorant.com/en-us/maps/#ascent), [Valorant Wiki: Ascent](https://valorant.fandom.com/wiki/Ascent), [B site callouts](https://www.thespike.gg/valorant/maps/ascent).
