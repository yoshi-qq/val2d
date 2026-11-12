# Handover: Ascent accuracy (12.11.2026)

From the Claude Code session "Ascent Map 3D accuracy" to the next coder (Codex). Christian's feedback on the first
version (commit 4d637ef on dev): some heights are wrong, you can walk through windows, some things are boxes that
should be other sprites. He does not answer questions this iteration: check against real screenshots yourself.

## Where things are

- Map: `gameplay/data/maps/ascent.py`. `GRID` = one char per square metre, `#` wall, digit = floor level in metres.
  All feature positions are in pixels of the reference tactical map (`ref(...)`), official minimap projection
  1656 px = 142.86 m. The reference is Christian's callout map image (tracker.gg style, 1656×1656); it is not in the
  repo.
- Height model (engine): `gameplay/world.py` (Wall.base/top/full, Platform.mat, ramps as dicts with rise/low/high),
  `gameplay/match.py` (movement, bullets, cover use `w.top`), `gameplay/nav.py` (bots: step up ≤ 0.3 per cell,
  drops free), `gameplay/mapkit.py` (`MapBuilder.stairs`, `platform(mat="floor")`), `sprite_bank.py` (platform art).
- Tests: `tests/test_ascent.py` (levels, stairs, Heaven not jumpable, B Main windows, cover on raised floors,
  bot paths, every stair continuous), `tests/test_heights.py`.
- Decisions: `docs/DECISIONS.md` (12.11.2026 · Maps and · World entries), notes `docs/design/ASCENT.md`.

## Done after the feedback, NOT committed (working tree, all Ascent tests green)

Researched with screenshots (beebom A site/A Main/B entry, gamerant B overviews, thesportsrush B Lobby/Heaven/Pizza,
immortalboost B site):

1. **A site was inverted.** From A Main the stairs go *down* onto the site; Tree door, A Switch and A Main sit on the
   higher front. Now: A site 1, front/A Main/Tree/Cubby 2, Garden + window landing 3 (stairs up from Tree, ramp from
   the A connector), Heaven 4 (three metres over the site, not jumpable), A Lobby 1 with a ramp up into A Main.
2. **B site is below B Lane.** Now: B site + Boathouse 0, Lane/back site/B Main/B Lobby 1, Market platform and Market
   2 (Market is level with Pizza, so the whole defender side and Mid north moved up one level), stairs from the
   B site's north-east corner up to the back site.
3. **B Main windows.** Of the three openings from B Main to B Lane only the east one is a passage; the two western
   ones are now walls with material `ascent_window` (full height, `low=True`: block walking, not sight or shots).
   `parse_map` reads `low` from wall data/material for this.
4. **Props.** A Garden and A Lobby boxes are now `ascent_planter`; the B Lobby crate stack is now a stoop (level-2
   platform with a steps decal) in front of a house door.

Not yet run after these changes: the full pytest suite, the self-test, the headless 5v5 match. Run them before
committing (`python -m pytest -q`, `self_test.run()`, a `Game(args(map="ascent", team_size=5))` match).

## Open problems

1. **Heights still unverified** where no screenshot was found: B Main and B Lobby (assumed level with B Lane), A Lobby
   ramp position (A Main leg, x 92–102.5 m, top 69–77 m), position of the B site stairs (x 28–31, top 26–30), Garden
   corridor ramp (x 81–89, top 22–28), Mid Link vs Courtyard (same level now), attacker spawn vs Mid Top (ramp at the
   spawn barrier). Compare each with in-game screenshots.
2. **Other windows.** Christian only named B Main. Check the whole map for openings the tactical map draws as
   walkable but which are windows in the game (e.g. Market, Boathouse, Mid Courtyard/Link panels).
3. **Wrong sprites.** Only Lobbies/Garden were named. Check every entry of `COVER` against screenshots: A Bricks
   (brick pallets, not crates), A site east boxes, box on Heaven, Mid Bottom boxes (the Kench bench is there), Mid
   Courtyard/Cubby/Mid Top boxes, B back/front boxes, B site stack. Missing sprites (planter variants, bench, bricks,
   open window frame, stoop) go to the design session via `docs/SPRITES.md`, placeholders until then.
4. **`ascent_window` uses the glass tile as a placeholder**; needs an open-frame sprite from the design session.
5. **Known deviations** (in DECISIONS.md): Hell is the site floor under the Heaven edge (one walkable floor per
   point); A Window glass does not break; both bomb doors use Val2d's reversible F door instead of one-way closing
   and 500 HP; the Courtyard/Link destructible panels are missing.
6. **Bots**: path search now covers the whole grid (up to ~0.3 s for the longest Ascent paths, repath every 3 s per
   bot). Watch performance with 10 bots.

## Working-tree caution

Other sessions work in the same tree (agents, weapons, assets). Stage only the Ascent files by explicit path:
`gameplay/data/maps/ascent.py gameplay/world.py config/content/materials.py tests/test_ascent.py
docs/ASCENT_HANDOVER.md` (plus whatever you change). Branch: `dev` only.
