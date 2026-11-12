# Val2d – Context for Claude Code

VALORANT in 2D, Python + pygame. Read before any work:
- docs/VISION.md – what Val2d is meant to be (binding)
- docs/DECISIONS.md – decisions made; append new ones with date, who, area
- roadmap.md – old state of work

## Division of work
You are the **coding session**. Graphics come from the **design session** with Christian (chat in claude.ai). Handover via docs/SPRITES.md, details in docs/VISION.md, section "Two sessions".

## Rules
- As close to Valorant as possible. If something deviates, put the reason in docs/DECISIONS.md.
- Never scatter game values across the code: a data file with patch number and source per value.
- Values that Christian tunes (e.g. hit tolerances) belong in the game config.
- Graphics and sprites are delivered by the design session with Christian. Until then, placeholders, clearly named as such.
- graphy and networking come from the packages (no local copies). Networking in the game goes through the wrapper netplay (working title).
- New code: snake_case, type hints, no TODOs in finished code. Warn on non-fatal errors, never crash. Time is UTC internally.
- Never report as tested what did not run.
