# config

Every value the game uses, as Python files you can edit. The game reads them at start; a broken file is
reported with a warning and its defaults apply. Files starting with `_` are templates and are never loaded.

| Folder | What | Files |
|---|---|---|
| `rules/` | Game rules, the same for everyone in a match | `movement.py` (speed, jumps, steps, falls), `combat.py` (health, armor, ultimate points), `economy.py`, `rounds.py` (rounds, bomb, modes), `senses.py` (field of view `fov`, sight distance, sound radii) |
| `settings/` | Values Christian tunes | `hit_zones.py`, `lobby.py` (lobby defaults), `player.py` (defaults of each player's own settings) |
| `content/` | What the game contains | `agents/` (one file per agent), `mechanics/` (own effects and triggers), `statuses.py`, `weapons.py`, `materials.py` |
| `client/` | Look and feel of the game window | `theme.py` (colours, fonts), `hud.py` (HUD layout, minimap, help key), `view.py` (camera, sight shading), `sound.py` (mixing, direction) |

Each file in `rules/` and `settings/` holds a part of one big table (`RULES` or `CONFIG`); files are merged, so a
section may move to another file. How to build agents, abilities, statuses and maps: `docs/MODDING.md`.

`config.json`, `constants.py`, `localSettings.json` and `serverSettings.json` belong to the old game path
(`main.py`, `handlers/`) and are not read by the new game.
