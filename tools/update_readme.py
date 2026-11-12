"""Refresh the README content inventory from the game data and sprite files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gameplay.data import load_armor, load_weapons
from gameplay.match import PLAYABLE_AGENT_KEYS, load_agents, playable_agents
from gameplay.world import DEFAULT_MAP, PLAYABLE_MAP_KEYS, load_map_raw, map_keys

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
START = "<!-- BEGIN GAME CONTENT -->"
END = "<!-- END GAME CONTENT -->"


def sprite(path: str, label: str, width: int | None = None) -> str:
    if not (ROOT / path).is_file():
        return "Missing"
    if width is not None:
        return f'<img src="{path}" alt="{label}" width="{width}">'
    return f"![{label}]({path})"


def content() -> str:
    lines = [
        "### Maps", "",
        "| Icon | Map | Availability |", "| --- | --- | --- |",
    ]
    for key in sorted(map_keys(), key=lambda key: (key != DEFAULT_MAP, key)):
        name = load_map_raw(key)["name"]
        availability = "Default" if key == DEFAULT_MAP else "Playable" if key in PLAYABLE_MAP_KEYS else "Map editor"
        icon = sprite(f"assets/maps/{key}/icon.png", f"{name} map icon")
        lines.append(f"| {icon} | {name} | {availability} |")

    agents = load_agents()
    playable = playable_agents()
    lines.extend([
        "", "### Agents", "",
        f"{len(playable)} selectable in the current build.",
        "", "| Portrait | In game | Agent | Role | C / Q / E / X |",
        "| --- | --- | --- | --- | --- |",
    ])
    for key in PLAYABLE_AGENT_KEYS:
        agent = agents.get(key, {})
        name = agent.get("name", key.title())
        portrait = sprite(f"assets/agents/{key}/{key}_portrait.png", f"{name} portrait")
        idle = sprite(f"assets/agents/{key}/{key}_idle.png", f"{name} idle sprite")
        abilities = " ".join(
            sprite(f"assets/ui/ability_{key}_{slot}.png", f"{name} {slot}", width=20) for slot in "CQEX"
        )
        role = agent.get("role") or "Unknown"
        lines.append(f"| {portrait} | {idle} | {name} | {role} | {abilities} |")
    unavailable = [agents.get(key, {}).get("name", key.title()) for key in PLAYABLE_AGENT_KEYS if key not in playable]
    if unavailable:
        lines.extend(["", f"Unavailable in the current build: {', '.join(unavailable)}."])

    weapons = load_weapons()
    categories = {
        "melee": "Melee", "sidearm": "Sidearm", "smg": "SMG", "shotgun": "Shotgun",
        "rifle": "Rifle", "sniper": "Sniper", "heavy": "Heavy",
    }
    lines.extend([
        "", "### Weapons and armor", "",
        f"{len(weapons)} configured weapons, including melee.",
        "", "| Category | Item | Sprite | Cost |", "| --- | --- | --- | --- |",
    ])
    for weapon in weapons.values():
        image = sprite(f"assets/weapons/val2d/{weapon.art}.png", f"{weapon.name} sprite")
        cost = "Starting loadout" if weapon.slot == "melee" else f"{weapon.price:,} credits" if weapon.price else "Free"
        lines.append(f"| {categories.get(weapon.category, weapon.category)} | {weapon.name} | {image} | {cost} |")
    vest_art = {"light_armor": "vest_light", "heavy_armor": "vest_heavy"}
    for key, armor in load_armor().items():
        buy = sprite(f"assets/ui/buy/{vest_art.get(key, key)}.png", f"{armor.name} buy sprite", width=48)
        lines.append(f"| Armor | {armor.name} | {buy} | {armor.price:,} credits |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the README inventory is out of date.")
    args = parser.parse_args()
    current = README.read_text(encoding="utf-8")
    before, end = current.split(START)
    _, after = end.split(END)
    updated = f"{before}{START}\n\n{content()}\n\n{END}{after}"
    if current != updated:
        if args.check:
            print("README content is stale. Run python -m tools.update_readme.", file=sys.stderr)
            return 1
        README.write_text(updated, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
