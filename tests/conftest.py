from pathlib import Path
from runpy import run_path

import pytest

from gameplay.match import load_agents


@pytest.fixture
def archived_agents(monkeypatch):
    """Exercise legacy ability recipes only in the tests that still cover them."""
    root = Path(__file__).resolve().parents[1]
    configs = root / "archive/custom-agents/config/content/agents"
    roster = {**load_agents(), **{
        key: run_path(str(configs / f"{key}.py"))["AGENT"]
        for key in ("harrow", "juniper", "kestrel", "marrow", "okoro", "rook", "sable", "tamsin")
    }}
    monkeypatch.setattr("gameplay.match.load_agents", lambda: roster)
    return roster
