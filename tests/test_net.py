"""Network tests over localhost: host session and client in one process, real sockets."""
from __future__ import annotations

import socket
import sys
import time
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from gameplay.match import Command, Match
from gameplay.net import Client, apply_snapshot, command_from_json, recv_msg, send_msg
from gameplay.session import HostSession
from gameplay.world import load_map


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("", 0))
        return int(probe.getsockname()[1])


def _wait(condition: Callable[[], bool], session: HostSession | None = None, timeout: float = 5.0) -> None:
    end = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > end:
            raise TimeoutError("condition not met")
        if session:
            session.step(1 / 64)
        time.sleep(0.005)


@pytest.fixture
def session() -> HostSession:
    s = HostSession(Match(load_map("werkhof"), seed=1), "Test host", _free_port())
    yield s
    s.close()


def test_command_from_json_clamps_and_drops_junk() -> None:
    cmd = command_from_json({"move_x": 9, "move_y": "x", "facing": 725, "cursor_depth": -3, "fire": 1,
                             "slot": "rakete", "ability": "Z", "buy": ["speer", 5, "x" * 40] + ["a"] * 20})
    assert cmd.move_x == 1.0 and cmd.move_y == 0.0
    assert cmd.facing == pytest.approx(5.0)
    assert cmd.cursor_depth == 0.0 and cmd.fire is True
    assert cmd.slot is None and cmd.ability is None
    assert cmd.buy[0] == "speer" and len(cmd.buy) == 8


def test_client_joins_receives_snapshot_and_moves(session: HostSession) -> None:
    client = Client("127.0.0.1", session.net.port, "Guest", "marrow")
    try:
        assert client.map_key == "werkhof"
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        shadow = Match(load_map(client.map_key))
        _wait(lambda: any(m.get("type") == "state" for m in client.inbox), session)
        for msg in client.take():
            if msg["type"] == "state":
                apply_snapshot(shadow, msg["snap"], client.pid)
        assert client.pid in shadow.players
        assert shadow.phase == "buy"
        # skip the buy phase, then walk forward
        session.match.phase_until = session.match.time
        start = session.match.players[client.pid].pos
        for _ in range(40):
            client.send(Command(move_y=1.0, facing=session.match.players[client.pid].facing))
            session.step(1 / 64)
            time.sleep(0.004)
        assert (session.match.players[client.pid].pos - start).length() > 0.3
    finally:
        client.close()


def test_held_input_continues_between_client_messages(session: HostSession) -> None:
    client = Client("127.0.0.1", session.net.port, "Guest", "kestrel")
    try:
        _wait(lambda: client.pid in session.match.players, session)
        session.start(team_size=1)
        session.match.phase_until = session.match.time
        session.step(1 / 64)
        client.send(Command(move_y=1.0, facing=session.match.players[client.pid].facing, buy=["speer"]))
        _wait(lambda: client.pid in session.last, session)
        before = session.match.players[client.pid].pos
        for _ in range(20):  # no new messages: the last held command keeps applying
            session.step(1 / 64)
        assert (session.match.players[client.pid].pos - before).length() > 0.3
        assert session.last[client.pid].buy == []
    finally:
        client.close()


def test_disconnected_player_becomes_bot(session: HostSession) -> None:
    client = Client("127.0.0.1", session.net.port, "Guest", "kestrel")
    _wait(lambda: client.pid in session.match.players, session)
    client.close()
    _wait(lambda: session.match.players[client.pid].is_bot, session)
    assert session.match.players[client.pid].name.endswith("(Bot)")


def test_join_rejected_after_start(session: HostSession) -> None:
    session.start(team_size=1)
    with pytest.raises(ConnectionError):
        Client("127.0.0.1", session.net.port, "Late", "kestrel")


def test_oversized_message_is_refused() -> None:
    a, b = socket.socketpair()
    try:
        a.sendall((10_000_000).to_bytes(4, "big"))
        with pytest.raises(ValueError):
            recv_msg(b)
        with pytest.raises(ValueError):
            send_msg(a, {"x": "y" * 600_000})
    finally:
        a.close()
        b.close()


def test_fill_bots_balances_teams(session: HostSession) -> None:
    session.match.add_player("Host", 0, "kestrel")
    session.start(team_size=3)
    assert session.team_counts() == [3, 3]
    assert session.match.phase == "buy"
