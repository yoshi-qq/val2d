"""Self test of an installed or built Val2d: every module, config, map, sprite set and sound must load.

Used by build.py on the finished .exe (play --self-test <report file>) so a missing dependency or data file
fails the build instead of a player's game. Runs without a window or sound device.
"""
from __future__ import annotations

import os
import traceback
from pathlib import Path


def run(report: Path | None = None) -> bool:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    lines: list[str] = []
    ok = True

    def check(name: str, fn: object) -> None:
        nonlocal ok
        try:
            detail = fn()  # type: ignore[operator]
            lines.append(f"ok    {name}{(': ' + str(detail)) if detail else ''}")
        except Exception:
            ok = False
            lines.append(f"FAIL  {name}\n{traceback.format_exc()}")

    import pygame

    pygame.init()
    pygame.display.set_mode((64, 64))

    def modules() -> str:
        import netplay  # noqa: F401
        import networking  # noqa: F401
        import menu  # noqa: F401
        import map_editor  # noqa: F401
        import server  # noqa: F401
        import user_settings  # noqa: F401
        from gameplay import abilities, bots, data, match, nav, net, netgame, session, world  # noqa: F401
        return f"pygame {pygame.version.ver}, netplay {netplay.__version__}"

    def configs() -> str:
        from gameplay.data import load_weapons
        from gameplay.match import load_agents
        from gameplay.world import load_materials, load_things
        weapons, agents = load_weapons(), load_agents()
        walls, floors = load_materials()
        objects, decals = load_things()
        assert weapons and agents and walls and floors and objects and decals
        return f"{len(weapons)} weapons, {len(agents)} agents, {len(walls)} walls, {len(objects)} objects"

    def maps() -> str:
        from gameplay.world import load_map, map_keys
        keys = map_keys()
        for key in keys:
            world = load_map(key)
            assert world.key == key and world.walls, key
        return ", ".join(keys)

    def sprites() -> str:
        from gameplay.match import load_agents
        from sprite_bank import CharacterSprites, SpriteBank, build_map_surface
        from gameplay.world import load_map
        bank = SpriteBank()
        chars = CharacterSprites(bank)
        for agent in load_agents():
            assert chars.frame(agent, "idle", False, 32, 0.0) is not None, f"idle sprite of {agent}"
        assert build_map_surface(load_map("werkhof"), bank, 16) is not None
        return f"{len(load_agents())} agent sprite sets"

    def sounds() -> str:
        from client.common import SOUND_DIR
        files = list(SOUND_DIR.glob("*.wav"))
        assert len(files) >= 40, f"only {len(files)} sounds"
        return f"{len(files)} sounds"

    def match_runs() -> str:
        from gameplay.bots import BotDirector
        from gameplay.match import Match
        from gameplay.world import load_map
        m = Match(load_map("gasse"), seed=1)
        m.add_player("A", 0, "kestrel", is_bot=True)
        m.add_player("B", 1, "marrow", is_bot=True)
        bots = BotDirector(m, seed=1)
        m.start()
        for _ in range(64 * 5):
            m.tick(1 / 64, bots.commands(1 / 64))
        return f"phase {m.phase}"

    for name, fn in (("modules", modules), ("configs", configs), ("maps", maps), ("sprites", sprites),
                     ("sounds", sounds), ("match", match_runs)):
        check(name, fn)
    lines.append("SELF-TEST OK" if ok else "SELF-TEST FAILED")
    text = "\n".join(lines)
    if report is not None:
        report.write_text(text, encoding="utf-8")
    else:
        print(text)
    return ok
