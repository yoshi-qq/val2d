# Val2d – Vision

As of: 11.11.2026 · Christian Abel · Source: vision sheet and follow-up questions in the chat

## Core

Val2d is a tactical 2D shooter that plays like VALORANT. **Rules, systems, weapon balance and game feel as close to the original as possible.** We only deviate where 2D truly makes a mechanic impossible; then there is a 2D solution whose result comes as close to the original as possible (example: hit zones, see below).


What has to feel like Valorant:
- Gunplay: first-shot accuracy, counter-strafing, spray
- Abilities and utility
- Economy (credits, eco, force and full buy)
- Sound as information
- Round structure with a bomb
- Agent selection and team composition

Who it's for: friends on LAN, friends over the internet, solo against bots. No public matchmaking with strangers planned.

Non-commercial. Sprites are made in our own pixel-art style.

## Presentation

- **Perspective:** top-down, with height levels (z). Crates, stairs and jumps matter for gameplay.
- **Characters:** sprites are drawn as if the characters were lying on the ground (front view laid flat onto the map): head at the top of the sprite, legs at the bottom.
- **Vision:** vision cone in the facing direction, the rest hidden (default). Can be switched to all-round vision as a lobby rule (walls still block sight).
- **Camera:** pushed forward in the aim direction; strength as a player setting.
- **Style:** pixel art in the style of the existing Aseprite files. New designs are made together with Christian; he checks every sprite for style consistency.
- **Input:** keyboard and mouse.

## Two sessions

Val2d is built in two separate sessions:

- **Coding session** (Claude Code, locally on the PC): code, game logic, networking, game values, tests. Uses existing assets or clearly named placeholders for graphics and does not create final sprites.
- **Design session** (chat in claude.ai with Christian): sprites, animations and interfaces in our own pixel-art style. Christian checks every design for style consistency. The result is files in `assets/`.

**Handover between the two:** `docs/SPRITES.md`. The coding session enters what is needed (name, size in pixels, purpose, animations, placeholder path). The design session enters the status and the path of the finished file. The coding session then replaces the placeholder.

## Gunplay

- **Spread like Valorant:** standing still, the first bullet is exact; moving, jumping and spraying spread randomly within a fixed range. Spray patterns roughly as in the original (in Valorant deliberately not fully learnable as a constant pattern). Only someone who shoots wrong should get lucky.
- **Hits and zones: pure precision**, see "Hit zones in 2D".
- **Wall penetration** according to the material's penetration level, as in Valorant.
- **Scale:** real meters. Movement speeds, ranges and damage falloff according to the real values.
- **Weapon values:** numbers from the official Valorant patch notes (damage, fire rate, magazine, prices, spread), with patch number and source in a data file. Weapons use their VALORANT names.

### Hit zones in 2D

The zone (head, body, legs) is determined along two axes relative to the line of fire, with different scaling:

- **Across the line of fire (x):** exactly the widths of the zones in the sprite. Aiming off to the side misses, or misses the narrower zone.
- **Along the line of fire (y, depth):** decides the height on the body. What counts is whether the mouse cursor was *on* the target or in front of or behind it. The center point is the head. The further in front of or behind the target the cursor was, the lower on the body the hit. The allowed deviation is considerably larger than the sprite, because the bullet keeps flying in the direction of fire.
- **Condition:** cursor and target are on the same height level (z).
- **At least legs:** if cursor and target are on the same level and the line of fire passes through the enemy (lateral distance within the largest sprite width), at least a leg hit is always possible, even outside any depth tolerance or off to the side of the zone that the depth indicates.
- **View:** the camera rotates with the mouse; on screen you always aim straight up. x and y are therefore the screen axes. Enemy sprites stand upright on the screen and do not rotate with the world.
- **Head narrowly missed:** depth matches the head, off to the side but within the body width: body hit.
- **Different level:** if the cursor is on a different height level than the target: miss.
- **Demo:** the artifact "Val2d-Trefferlogik" (claude.ai) shows the logic interactively.
- **Adjustable:** the allowed deviations per zone are in the game config and are tuned by Christian, not fixed in the code.

## Game flow

- **Teams:** flexible from 1 vs 1 to 5 vs 5.
- **Bots:** fill empty slots. First version: simple bots (move, aim, plant and defuse the bomb). Good bots are a separate expansion step.
- **Match length:** adjustable, default as in the original (13 winning rounds, overtime).
- **Sound:** real stereo spatial sound. Visible sound rings as a lobby setting, applies to everyone or no one, off by default.
- **Host:** both possible. A player hosts and plays along (default if nothing else is set: host = player 1), or a dedicated server process.

## Agents and abilities

- **Defined in `config/agents.json`**, editable by Christian: per agent name, role, sprite set and four abilities (keys Q, E, C, X). Per ability: building block, parameters (e.g. radius, duration, range), cost, charges, cooldown; for X the ultimate points.
- **Building blocks:** an ability is assembled from three freely combinable parts, each with parameters in the config:
  - **Trigger:** throw (with bouncing, flight time), place, aim via the tactical map, on oneself, as a projectile, as a trap with a trigger.
  - **Shape:** circle, wall or line, cone, point; size, height level, duration.
  - **Effect (also several):** block vision, blind, slow, damage over time or instant, heal, reveal, movement (dash, jump, teleport), shield or barrier, make noise.
  New parts are added as code, new abilities only via the config. Technical names in the code, displayed names in the config.
- **Modeled on Valorant:** roles (Duelist, Initiator, Controller, Sentinel), design principles (every ability has counterplay, is readable at a glance, costs credits or has charges and a cooldown; teams need info, vision block, entry and site protection) and the game feel of a round.
- Errors in the config (unknown building block, missing value) are reported at startup and the agent is skipped; the game does not crash.

## First finished version

- Mode: Unrated
- Maps: one standard map following the familiar layout (two bomb sites, mid, attacker and defender spawn, callouts) and a simple 1 vs 1 map; both editable in the map editor
- Agents: two example agents (one Controller, one Duelist), defined in `config/agents.json`
- Ability building blocks for both kits, extensible
- All weapons (real numbers), buy menu, economy, bomb, rounds
- Networking via the new wrapper (LAN and internet)

## After that

Expansion in this order: more agents, more modes, more maps.
