"""Balance patches in config/patches change agents, abilities, weapons, armor, statuses, rules and maps."""
from __future__ import annotations

from pathlib import Path

import pytest

from gameplay import patches

PATCH = '''
VERSION = "9.99"
NOTES = "test patch"
PATCH = {
    "agents": {"kestrel": {"C": {"blind": 0.5}, "role": "Initiator"}, "marrow": {"Q": {"alt": None}}},
    "weapons": {"hammer": {"price": 1234}},
    "armor": {"schwer": {"price": 999}},
    "statuses": {"slow": {"speed": 0.9}, "frozen": {"speed": 0.1}},
    "rules": {"economy": {"start": 4321}},
    "maps": {"workyard": {"set": {"name": "Patched Yard"}, "add": {"crates": [[1, 1, 2, 2]]}}},
}
'''


@pytest.fixture()
def patched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "01_test.py").write_text(PATCH, encoding="utf-8")
    (tmp_path / "_ignored.py").write_text("PATCH = {'weapons': {'hammer': {'price': 1}}}", encoding="utf-8")
    monkeypatch.setattr(patches, "PATCH_DIR", tmp_path)
    patches.reload_all()
    yield
    monkeypatch.undo()
    patches.reload_all()


def test_patch_changes_every_kind_of_content(patched: None) -> None:
    from gameplay.data import load_armor, load_rules, load_weapons
    from gameplay.kit.statuses import load_statuses
    from gameplay.match import load_agents
    from gameplay.world import load_map_raw
    agents = load_agents()
    assert agents["kestrel"]["abilities"]["C"]["blind"] == 0.5 and agents["kestrel"]["role"] == "Initiator"
    assert "alt" not in agents["marrow"]["abilities"]["Q"]
    assert load_weapons()["hammer"].price == 1234 and load_armor()["schwer"].price == 999
    st = load_statuses()
    assert st["slow"]["speed"] == 0.9 and st["frozen"]["speed"] == 0.1
    assert load_rules()["economy"]["start"] == 4321
    raw = load_map_raw("workyard")
    assert raw["name"] == "Patched Yard" and [1, 1, 2, 2] in raw["crates"]
    assert patches.notes() == [("9.99", "test patch")]


def test_without_patches_nothing_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(patches, "PATCH_DIR", tmp_path)
    patches.reload_all()
    from gameplay.data import load_weapons
    assert load_weapons()["hammer"].price == 2900
    monkeypatch.undo()
    patches.reload_all()
