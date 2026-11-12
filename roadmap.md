# Roadmap
Status 12.11.2026. Items marked "(new core)" are done in the new gameplay core (`gameplay/`, `play.py`) instead of the old path (`main.py`, `handlers/`).

## Bugs
(- [x] Switch from Agent Select to In-Game-Player only happens sometimes) – old path; the new lobby/agent select replaces it
(- [x] Connection randomly closed) – old path; networking now via netplay (keepalive, timeouts, host-lost event)
- [ ] Not yet played with a window: game feel and balance unchecked
- [ ] Bot balance one-sided on Harbour (defenders win) and Gasse 1v1 (attackers win)

## Refactoring
- [x] Crouch door -> Crouching needed to fit under any low surface – replaced: doors open with F, low cover has height 1
- [ ] Decide: drawing through graphy or pygame-ce directly (see docs/ENTSCHEIDUNGEN.md)
- [ ] Decide: remove the old game path (main.py, handlers/, classes/, mapEditor.py)

## Next
- [x] Lobby
- [x] Agent Select
- [x] Moving (Running)
- [x] Turning 
- [x] Walking
- [x] Crouching
- [x] local calculation for Walk & Crouch
- [x] correct Speed from Game
- [x] Jumping
- [x] Map
    ### Editing
    - [x] moving
    - [x] turning
    - [x] saving and loading of map files
    - [x] display of current object in top-left corner
    - [x] display of current data in top-left corner
    - [x] resizing of objects
    - [x] placing of new objects (automatic IDs)
    - [x] deleting objects
    - [x] changing textures in editor (name or file select)
    - [x] changing penetrationLevel – new map_editor.py: material per wall sets penetration, sight, height
    - [ ] changing linked ID (switch-door) – doors exist (F), linked switches not
    - [ ] changing TP-Destination (maybe as own momevable)
    - [x] changing Callout (selector? tkinter) – map_editor.py tool C (name editing in the JSON)
    - [x] changing spawn team-id – map_editor.py key T
    - [ ] multi-select with ctrl
    - [ ] automatic abyss spawning
    ### Gameplay
    - [x] objects (new core: props, doors, spawn barriers, decals)
    - [x] collision (new core)
- [x] Guns (new core, 20 weapons + knife, config/weapons.py)
    - [x] raycasting (sort of)
    - [x] wall Penetration (by material)
    - [x] damaging (by zone and distance)
    - [x] spread, spray pattern, alternate fire (zoom, burst, spread shot, spin-up)
- [x] Abilities (new core: 21 building blocks, 10 statuses, 30 agents in config/agents.py)
- [x] Worlds (standing in smoke -> only seeing inside smoke, standing outside -> only see outside)
- [x] Stats (scoreboard: kills, deaths, credits, ping; range: accuracy and headshots)
- [x] Buy Menu
- [x] Phases (Gamemode): buy, live, planted, round end, side switch, overtime
- [x] Spike (named "bomb" in game): plant, defuse with checkpoint, detonation
- [x] Ping request for round trip display with last trip time for host

## Extras
- [x] better console (stacking messages with counts)
- [ ] replace ALL Strings with Enums (debug messages included, split into: problem, reason, details)
- [ ] Dev-Tools (noclip, speed, in-game coordinate display, etc.)
- [ ] Integration instead of numerical accel, velocity, pos
- [x] Main Menu
- [x] Animations – character sheet states from docs/design (graphy Aseprite export still open in graphy)
- [x] small adjustments from local to server tolerance – client prediction with reconciliation
- [ ] AFKing and Rejoins (a disconnected player is taken over by a bot; rejoin missing)
- [ ] Replay System :>

## Can Wait
- [x] Button hovering – menu kit with hover/pressed sprites
- [x] Join IP+Port choosing – join by LAN address, join code or LAN search

## Additions
- [x] Replace all DEFAULTS with settings, config, etc. (config/*.py, config/game_config.json, ~/.val2d/settings.json)
- [x] More Weapons (20)
- [x] More Agents (30)
- [ ] More Gamemodes
- [x] More Maps (Werkhof, Gasse, Harbour)
- [x] The Range

## Open
- [ ] Real sounds (synthetic placeholders today)
- [ ] Internet test across two real networks (Pakete/netplay/TESTING.md)
- [ ] Relay for players behind strict routers
- [ ] Rejoin after disconnect

## Maybe
- [ ] Client sort of waiting for server response
- [ ] Shop (Skins)
