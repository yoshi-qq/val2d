# Handover: figures from behind and from the side

Request from the coding session to the design session, 12.11.2026. Status rows go into docs/SPRITES.md, section "Request 12.11.2026 (coding session): figures from several sides".

## What the game does

Since commit 0e5ca04 the game chooses the side of a figure the camera sees. The camera always looks the way the own player looks (up on screen = the own facing direction). For every figure it compares that figure's facing with the camera's:

| Figure looks … | View | File |
|---|---|---|
| the same way as the camera (within 45°): away from the camera, up on screen | back | `{key}_{state}_back.png` |
| to the right on screen (45°–135°) | side | `{key}_{state}_side.png` |
| toward the camera (135°–225°): down on screen | front | `{key}_{state}.png` (today's sprites) |
| to the left on screen (225°–315°) | side, mirrored by the game | `{key}_{state}_side.png` |

- **The own figure is always seen from behind.** Today it shows its face while walking away, so the back view of the own team's figures is the most visible new sprite.
- Enemies and teammates turn freely, so they need all three views.
- A missing back or side file falls back to the front view of the same state. Nothing breaks if only part of a set arrives.
- Forms (`{key}@{form}_{state}.png`) keep their front view for now.

## What we need

Per agent, in `assets/agents/{key}/`. Same cell size, frame count and frame order as the existing front strip of the same state, so the animation timing from docs/design/character_sheet_spec.py stays valid.

| Priority | States | Files per state |
|---|---|---|
| 1 | idle, walk, crouch, crouch_walk | `_back`, `_side`, `_back_feind`, `_side_feind` |
| 2 | jump, fall, land, shoot, reload, equip, flinch, melee | same |
| 3 | plant, defuse, cast_c, cast_q, cast_e, cast_x, channel_c/q/e/x, cast, victory | same |
| not needed | dead, dying (lying on the floor, seen from above), portrait, killfeed, select (screen pictures) | – |

Drawing rules:
- **back**: the figure seen from behind. Hair, back of the head, back of the outfit; the hands and weapon are hidden by the body or show only at the edges.
- **side**: profile looking **right**. The game mirrors it for left, so nothing asymmetric that must stay on one side (e.g. a logo with text) should sit on the visible side.
- **_feind**: the same frame with the enemy outline, exactly as for the front sprites.
- The game draws the held weapon separately at the figure's side, so the sprites need no weapon.

## Agents

The 30 Val2d agents with sprites in the repository, in this order (start with the first two to check the look in the game before doing the rest):

kestrel, marrow, juniper, harrow, nyx, okoro, rook, sable, tamsin, vesper, brann, quill, sorrel, dace, mako, wren, odile, pike, lark, rhea, fen, thorne, moraine, sloane, tove, garrick, ilse, basil, cato, ulric

That is 30 × 4 files for priority 1 (120 strips), 30 × 4 × 8 for priority 2 and 30 × 4 × 12 for priority 3.

## Check

When the files are in place: start a match, walk away from a teammate and around them. Your own figure should show its back, the teammate should turn through back, side and front, and the side view should flip when the figure turns from right to left. `python -m pytest tests/test_sprites.py` covers the file choice.
