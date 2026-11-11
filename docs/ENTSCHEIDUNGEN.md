# Decisions

Format: date · who · area · wording

- 11.11.2026 · Christian · Principle · Always as close to Valorant as possible; deviate only if 2D truly makes a mechanic impossible.
- 11.11.2026 · Christian · Gunplay · Spread like Valorant: standing still, first bullet exact; moving and spraying random within a fixed range.
- 11.11.2026 · Christian · Gunplay · Hit zones via lateral distance (exact sprite widths) and the cursor's depth distance (head = center point, large allowed deviation), only on the same height level; deviations in the game config.
- 11.11.2026 · Christian · Gunplay · Wall penetration according to penetration level.
- 11.11.2026 · Christian · World · Scale in real meters, values from the patch notes with patch number.
- 11.11.2026 · Christian · Presentation · Top-down with height levels; vision cone as default, all-round vision as a lobby rule; camera pushed forward (player setting); pixel art in our own style.
- 11.11.2026 · Christian · Game flow · Teams 1v1 to 5v5; simple bots in the first version; match length adjustable, default as original; sound rings as a lobby setting, off by default.
- 11.11.2026 · Christian · Networking · Host = player 1 as default, dedicated server process possible. Internet mode peer-to-peer via public STUN servers, initially without relay. pickle only in the old LAN mode.
- 11.11.2026 · Christian · Scope · First version: Unrated, Ascent + simple 1v1 map, Omen + Jett, all weapons. After that: agents, modes, maps.
- 11.11.2026 · Christian · Packages · graphy and networking as GitHub repos under yoshi-qq, installed editable; import names stay the same.
- 11.11.2026 · Christian · Gunplay · Hit logic confirmed in the demo. Same level and line of fire through the enemy: always at least a leg hit. Camera rotates along, aiming always straight up; x/y = screen axes.
- 11.11.2026 · Christian · Gunplay · Head narrowly missed (within body width): body. Cursor on a different level: miss. Enemy sprites stand upright on the screen.
- 11.11.2026 · Christian · Content · Replaces the scope entry above: no Valorant agents, kits, maps or names, not even renamed (Riot's fan content policy forbids IP in games). Agents via config/agents.json (name, role, sprite set, abilities from building blocks). First version: two custom example agents (Controller, Duelist), custom standard map + 1v1 map, weapons with own names and real numbers, bomb instead of Spike.
- 11.11.2026 · Christian · Graphics · Scale 16 px = 1 m (character 16×32, tile 32×32 = 2 m, view 480×270 native, ×4). Light from the top left.
- 11.11.2026 · Christian · Graphics · Outline: outer edge in a dark shade of each material's own color, within the sprite width; hit widths count without the outline.
- 11.11.2026 · Christian · Graphics · Team identification: sprites team-neutral, enemies with a red outline as in Valorant; color later a player setting.
- 11.11.2026 · Christian · Graphics · Shading: two levels per material (base tone, shadow), as in the existing assets. Concept: docs/design/sprite-konzept.html
- 11.11.2026 · Christian · Content · Modeled on Valorant in roles, design principles and game feel; our own agents, kits and maps are not counterparts to specific Valorant content.
- 11.11.2026 · Claude Code · Principle · No recreation of Riot content (agents, abilities, maps, names). Mechanics per VISION.md, content our own: agents Kestrel and Marrow, map Werkhof, 16 custom weapons. Christian sees it differently (VISION.md); open.
- 11.11.2026 · Claude Code · Technology · New game core gameplay/ (without pygame, command-driven, JSON snapshot instead of pickle), playable via play.py against bots. Old path main.py stays unchanged.
- 11.11.2026 · Claude Code · Values · All game values are our own design in gameplay/data/*.json (source per file), hit zones and lobby defaults in config/game_config.json.
- 11.11.2026 · Christian · Graphics · Logo: crosshair design replaces the Riot logo in logo.png, icon.ico and playercard.png (docs/design/logo-entwurf).
- 11.11.2026 · Christian · Content · Our own agents resemble Valorant's in nothing except abilities, which in the video game industry do not belong to Valorant (smoke, flash, dash, teleport, walls, traps and the like). Roles, slots (signature, basic 1/2, ultimate, passive) and effect terms (blind, nearsight, concuss, slow, vulnerable, decay, suppress, root, deafen, combat stim) are used as building blocks.
- 11.11.2026 · Claude Code · Content · Implementation of the entry above: genre-common abilities are used freely, but no agent repeats the complete kit of a specific Valorant agent, and very distinctive one-off mechanics (e.g. a 1v1 arena ultimate, soul orbs from kills, a map-wide cosmic wall) are not used. Names, looks and kit combinations are our own.
- 11.11.2026 · Christian · Language · Everything in English: game text, code, data and docs. Sprite file names stay as they are.
- 11.11.2026 · Christian · Content · Agents, abilities and weapons live in Python config files (config/agents.py, config/weapons.py) that Christian edits directly; they replace gameplay/data/agents.json and weapons.json.
- 11.11.2026 · Christian · Weapons · Roster of 20 guns plus knife from Christian's weapon overview (weapon classes, prices, magazines); own names, other values own estimates.
- 11.11.2026 · Claude Code · Abilities · Abilities are generic building blocks (21 kinds: smoke, wall, flash, zone, blast, wave, sensor, alarm, tripwire, dash, hop, teleport, anchor, heal, stim, shield, revive, reveal_all, overdrive, immunity, decoy) plus ten statuses (blind, nearsight, concuss, slow, vulnerable, decay, suppress, detain, deaf, stim). Agents only combine blocks; the agent overview from Christian (30 kits) is not transcribed, its mechanics exist as blocks.
- 11.11.2026 · Claude Code · Agents · Eight new own agents with own combinations: Vesper, Rook (Duelist), Tamsin, Okoro (Initiator), Juniper, Nyx (Controller), Harrow, Sable (Sentinel); Kestrel and Marrow kept.
- 11.11.2026 · Claude Code · Wording · The objective is called "bomb" in all player-facing text; code identifiers and file names with "spike" stay.
- 12.11.2026 · Claude Code · Maps · Material per wall and floor: config/materials.py (WALLS with tile, penetration, sight, height; FLOORS with tile). Map files use "mat" per wall and "floor"/"floors"; walls without material keep the old Werkhof tiles. Gasse uses the common set.
- 12.11.2026 · Claude Code · Maps · Map objects and decals: config/materials.py OBJECTS and DECALS; map files use "objects" (pos or rect, rot in 90° steps) and "decals". Blocking objects become walls; the spawn barrier blocks only during the buy phase and does not block sight.
