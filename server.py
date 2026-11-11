"""Val2d as a dedicated server process (no window).

Usage:  python server.py [--map werkhof] [--team-size 5] [--rounds 13] [--players 2] [--port 9009]
The match starts once --players humans have joined or --start-after seconds have passed;
bots fill free slots. Players join with  python play.py --join <address>.
"""
from __future__ import annotations

import argparse
import time
import warnings

from gameplay.data import LobbySettings, load_config
from gameplay.match import Match
from gameplay.net import DEFAULT_PORT
from gameplay.session import HostSession
from gameplay.world import load_map

TICK_RATE = 64.0


def build_match(map_key: str, rounds: int, team_size: int, all_around: bool, sound_rings: bool) -> Match:
    base = load_config()
    lobby = LobbySettings(all_around_sight=all_around or base.lobby.all_around_sight,
                          sound_rings=sound_rings or base.lobby.sound_rings,
                          win_rounds=rounds, overtime=base.lobby.overtime, team_size=team_size)
    return Match(load_map(map_key), type(base)(hit_zones=base.hit_zones, lobby=lobby, player=base.player))


def main() -> None:
    ap = argparse.ArgumentParser(description="Val2d server without a window")
    ap.add_argument("--map", default="werkhof")
    ap.add_argument("--team-size", type=int, default=5, choices=range(1, 6))
    ap.add_argument("--rounds", type=int, default=13)
    ap.add_argument("--players", type=int, default=2, help="Start once this many humans have joined")
    ap.add_argument("--start-after", type=float, default=0.0, help="Start after this many seconds at the latest (0 = never)")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--all-around", action="store_true", help="Lobby rule: all-around sight")
    ap.add_argument("--sound-rings", action="store_true", help="Lobby rule: sound rings")
    args = ap.parse_args()

    match = build_match(args.map, args.rounds, args.team_size, args.all_around, args.sound_rings)
    try:
        session = HostSession(match, "Val2d-Server", args.port)
    except OSError as exc:
        print(f"Server cannot start: port {args.port} is in use or blocked ({exc}).")
        return
    print(f"Val2d server on port {args.port}, map {match.world.name}. Waiting for {args.players} players …")
    opened = time.monotonic()
    last = time.monotonic()
    known = 0
    try:
        while True:
            now = time.monotonic()
            dt, last = now - last, now
            if not session.started:
                humans = [p for p in match.players.values() if not p.is_bot]
                if len(humans) != known:
                    known = len(humans)
                    print(f"Joined: {', '.join(p.name for p in humans) or '—'}")
                late = args.start_after > 0 and now - opened >= args.start_after and humans
                if len(humans) >= args.players or late:
                    session.start(args.team_size)
                    print("Match starts.")
            for e in session.step(dt):
                if e.kind == "round_end":
                    print(f"Round {match.round_no}: team {e.data['winner'] + 1} ({e.data['reason']}), score {e.data['score'][0]}:{e.data['score'][1]}")
            if match.phase == "over":
                print(f"Match over: team {(match.match_winner or 0) + 1} wins.")
                time.sleep(5)
                break
            time.sleep(max(0.0, 1.0 / TICK_RATE - (time.monotonic() - now)))
    except KeyboardInterrupt:
        print("Server stopped.")
    except Exception as exc:  # report as non-fatal, close the server cleanly
        warnings.warn(f"Server error: {exc}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
