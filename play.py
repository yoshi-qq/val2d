"""Play Val2d: practice match against bots on the own game core (gameplay).

Usage:  python play.py [--agent kestrel|marrow] [--team-size 1..5] [--rounds 13] [--map werkhof|gasse]
                        [--all-around] [--sound-rings]
Network:  python play.py --host            open a match (host = player 1), Enter starts
          python play.py --find            find a match on the local network and join
          python play.py --join 192.168.1.20[:9009]
Dedicated server process: python server.py (see there).
Controls: WASD run, Shift walk, Ctrl crouch, Space jump, left mouse shoot,
mouse horizontal turn, mouse vertical aim depth, R reload, 1/2/3 weapon, C/Q/E/X abilities,
hold F plant/defuse the bomb, B buy menu, Tab scoreboard, Esc pause menu, Alt+F4 quit (asks first).
Graphics: sprites from the design session (docs/SPRITES.md); placeholders where a file is missing.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import pygame

from client.common import FONT_PATH, display_mode
from client.game import Game
from gameplay.netgame import DEFAULT_PORT, discover


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--self-test":  # used by build.py on the finished .exe
        import self_test
        report = Path(sys.argv[2]) if len(sys.argv) >= 3 else None
        sys.exit(0 if self_test.run(report) else 1)
    ap = argparse.ArgumentParser(description="Play Val2d against bots or online")
    ap.add_argument("--agent", default="kestrel", help="agent key (file name in config/content/agents/)")
    ap.add_argument("--team-size", type=int, default=5, choices=range(1, 6))
    ap.add_argument("--rounds", type=int, default=13)
    ap.add_argument("--map", default="werkhof")
    ap.add_argument("--all-around", action="store_true", help="Lobby rule: all-around sight")
    ap.add_argument("--sound-rings", action="store_true", help="Lobby rule: sound rings")
    ap.add_argument("--name", default="Player", help="Name in the match (up to 16 characters)")
    net = ap.add_mutually_exclusive_group()
    net.add_argument("--host", action="store_true", help="Open a network match (host = player 1)")
    net.add_argument("--host-online", action="store_true", help="Open an internet match with a join code")
    net.add_argument("--join", metavar="CODE|ADDRESS[:PORT]", help="Join a match by join code or LAN address")
    net.add_argument("--find", action="store_true", help="Find a match on the local network and join")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-menu", action="store_true", help="Start the practice match directly, without the main menu")
    ap.add_argument("--range", dest="practice", action="store_true", help="Practice range instead of a match")
    ap.add_argument("--mode", default="standard", choices=["standard", "quick", "deathmatch"])
    args = ap.parse_args()
    args.online = bool(args.host_online)
    if args.host_online:
        args.host = True
    if not (args.host or args.join or args.find or args.no_menu):
        run_menu(args)
        return
    if args.find:
        print("Looking for matches on the local network …")
        found = discover()
        if not found:
            print("No match found. Is the host running play.py --host or server.py, and are both on the same network?")
            return
        for address, port, host_name in found:
            print(f"  {host_name}  {address}:{port}")
        address, port, host_name = found[0]
        print(f"Joining {host_name} …")
        args.join = f"{address}:{port}"
    try:
        game = Game(args)
    except (OSError, ConnectionError) as exc:
        print(f"No connection: {exc}")
        pygame.quit()
        return
    game.run()
    pygame.quit()




def run_menu(args: argparse.Namespace) -> None:
    """Main menu loop: each match returns to the menu; quitting the menu ends the program."""
    from menu import MainMenu
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption("Val2d")
    try:
        font, big = pygame.font.Font(str(FONT_PATH), 18), pygame.font.Font(str(FONT_PATH), 36)
    except (OSError, FileNotFoundError):
        font, big = pygame.font.Font(None, 22), pygame.font.Font(None, 44)
    menu = MainMenu(screen, font, big, args)
    while True:
        chosen = menu.run()
        if chosen is None:
            break
        try:
            game = Game(chosen)
            game.run()
            if game.quit_program:
                break
        except (OSError, ConnectionError) as exc:
            menu.status = f"No connection: {exc}"
            warnings.warn(menu.status)
        screen = display_mode(bool(getattr(menu.args, "fullscreen", False)))
        menu.screen = screen
    pygame.quit()


if __name__ == "__main__":
    main()
