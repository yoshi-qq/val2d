"""Match history for the Career page: every finished match (not the range) is stored in ~/.val2d/history.json with
the final scoreboard. Times are UTC."""
from __future__ import annotations

import json
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HISTORY_PATH = Path.home() / ".val2d" / "history.json"
KEEP = 100  # newest matches kept


def load() -> list[dict[str, Any]]:
    try:
        if HISTORY_PATH.exists():
            data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict)]
    except (OSError, json.JSONDecodeError) as exc:
        warnings.warn(f"Match history unreadable ({exc}); starting a new one.")
    return []


def record(match: Any, me_pid: int, score_of: Any) -> dict[str, Any] | None:
    """Stores the finished match seen by player me_pid; score_of(p) gives a player's combat score."""
    me = match.players.get(me_pid)
    if me is None or match.practice:
        return None
    mine, theirs = match.score[me.team], match.score[1 - me.team]
    entry = {
        "when": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "map": match.world.key, "map_name": match.world.name, "mode": getattr(match, "mode", "standard"),
        "agent": me.agent, "won": None if match.match_winner is None else match.match_winner == me.team,
        "score": [mine, theirs], "rounds": len(match.history),
        "history": [[w == me.team, reason] for w, reason in match.history],
        "players": [{"name": p.name, "agent": p.agent, "own_team": p.team == me.team, "me": p.pid == me_pid, "bot": p.is_bot,
                     "kills": p.kills, "deaths": p.deaths, "score": score_of(p)}
                    for p in sorted(match.players.values(), key=lambda p: -score_of(p)) if not p.dummy],
    }
    data = load()
    data.append(entry)
    try:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_PATH.write_text(json.dumps(data[-KEEP:], indent=1), encoding="utf-8")
    except OSError as exc:
        warnings.warn(f"Match history not saved: {exc}")
    return entry


def summary(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Totals over the stored matches: played, wins, win rate, kills, deaths, K/D, most played agent."""
    played = len(data)
    wins = sum(1 for d in data if d.get("won"))
    mine = [p for d in data for p in d.get("players", []) if p.get("me")]
    kills, deaths = sum(p.get("kills", 0) for p in mine), sum(p.get("deaths", 0) for p in mine)
    agents: dict[str, int] = {}
    for d in data:
        agents[d.get("agent", "")] = agents.get(d.get("agent", ""), 0) + 1
    return {"played": played, "wins": wins, "win_rate": 100 * wins / played if played else 0.0, "kills": kills,
            "deaths": deaths, "kd": kills / deaths if deaths else float(kills), "favourite": max(agents, key=agents.get) if agents else ""}
