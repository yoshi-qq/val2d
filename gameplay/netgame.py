"""Val2d over netplay: host and client for LAN (TCP, discoverable) and internet (UDP, join code).

The host runs the Match; clients send Commands and receive per-viewer snapshots (Match.snapshot).
State goes out unreliable (newest wins), events and everything else reliable. No pickle.
"""
from __future__ import annotations

import threading
import time
import warnings
from dataclasses import asdict
from typing import Any

import netplay

from gameplay.match import Command, GameEvent, Match, PlayerState
from gameplay.net import command_from_json, event_to_json, merge_commands

DEFAULT_PORT = netplay.DEFAULT_PORT
GAME_PROTOCOL = 2


class NetHost:
    """Lobby host for a Match. mode: "lan" or "internet"."""

    def __init__(self, match: Match, host_name: str, mode: str = "lan", port: int | None = None) -> None:
        self.match = match
        self.mode = mode
        try:
            self.lobby = netplay.host_lobby(host_name, mode=mode, port=port, playing=False)
        except (OSError, netplay.LobbyError) as exc:
            raise ConnectionError(str(exc)) from exc
        self.join_code = self.lobby.join_code
        self.warning = str(getattr(self.lobby, "warning", ""))
        self.port = int(getattr(self.lobby, "port", 0) or 0)
        self.lock = threading.RLock()
        self.accepting = True
        self.pending: dict[int, Command] = {}
        self.pid_of: dict[int, int] = {}  # lobby player id -> match pid
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="val2d-host")
        self._thread.start()

    def _loop(self) -> None:
        """Joins, agent picks and commands are handled here, independent of the game loop."""
        while self.running:
            try:
                self.pump()
            except Exception as exc:  # one bad message must not stop the host
                warnings.warn(f"Host: message handling failed: {exc}")
            time.sleep(0.005)

    # ------------------------------------------------------------ incoming
    def pump(self) -> None:
        for ev in self.lobby.poll():
            if ev.kind == "left" and ev.player in self.pid_of:
                with self.lock:
                    p = self.match.players.get(self.pid_of.pop(ev.player))
                    if p:  # a bot takes over a disconnected player
                        p.is_bot = True
                        p.name += " (Bot)"
            elif ev.kind == "message" and ev.player is not None and ev.message is not None:
                self._message(ev.player, ev.message)

    def _message(self, lid: int, msg: dict[str, Any]) -> None:
        t = msg.get("t")
        if t == "hello":
            if lid in self.pid_of:
                return
            if msg.get("protocol") != GAME_PROTOCOL:
                self.lobby.send({"t": "error", "reason": "Different Val2d version."}, to=lid)
                return
            if not self.accepting:
                self.lobby.send({"t": "error", "reason": "The match has already started."}, to=lid)
                return
            name = self.lobby.players[lid].name if lid in self.lobby.players else "Guest"
            agent = str(msg.get("agent", ""))
            with self.lock:
                count = [sum(1 for p in self.match.players.values() if p.team == t) for t in (0, 1)]
                team = 0 if count[0] <= count[1] else 1
                p = self.match.add_player(name, team, agent if agent in self.match.agents else "kestrel")
                self.pid_of[lid] = p.pid
            self.lobby.send({"t": "welcome", "pid": p.pid, "map": self.match.world.key, "team": team}, to=lid)
        elif t == "cmd" and lid in self.pid_of:
            cmd = command_from_json(msg.get("cmd", {}) if isinstance(msg.get("cmd"), dict) else {})
            pid = self.pid_of[lid]
            with self.lock:
                self.pending[pid] = merge_commands(self.pending.get(pid), cmd)
        elif t == "agent" and lid in self.pid_of:
            self.choose_agent(self.pid_of[lid], msg.get("agent"))

    def choose_agent(self, pid: int, agent: object) -> bool:
        with self.lock:
            p = self.match.players.get(pid)
            if p is None or self.match.phase != "lobby" or not isinstance(agent, str) or agent not in self.match.agents:
                return False
            p.agent = agent
            return True

    def take_commands(self) -> dict[int, Command]:
        with self.lock:
            cmds, self.pending = self.pending, {}
        return cmds

    # ------------------------------------------------------------ outgoing
    def broadcast(self, events: list[GameEvent]) -> None:
        for lid, pid in list(self.pid_of.items()):
            viewer = self.match.players.get(pid)
            if viewer is None:
                continue
            try:
                visible = [event_to_json(e) for e in events if self._event_visible(viewer, e)]
                if visible:
                    self.lobby.send({"t": "events", "events": visible}, to=lid)
                self.lobby.send({"t": "state", "snap": self.match.snapshot(pid)}, to=lid, reliable=False)
            except (ConnectionError, netplay.WireError, netplay.LobbyError) as exc:
                warnings.warn(f"Sending to player {pid} failed: {exc}")

    def _event_visible(self, viewer: PlayerState, e: GameEvent) -> bool:
        if e.kind in ("shot", "hit"):
            shooter = self.match.players.get(e.data.get("pid") if e.kind == "shot" else e.data.get("by"))
            return shooter is None or self.match.can_see(viewer, shooter) or e.data.get("by") == viewer.pid
        if e.kind == "sound" and viewer.status.get("deaf", 0.0) > self.match.time:
            return False
        if e.kind == "buy":
            buyer = self.match.players.get(e.data.get("pid"))
            return buyer is not None and buyer.team == viewer.team
        return True

    def ping(self, pid: int) -> float | None:
        lid = next((l for l, p in self.pid_of.items() if p == pid), None)
        return self.lobby.ping(lid) if lid is not None else None

    def close(self) -> None:
        self.running = False
        if self._thread is not threading.current_thread():
            self._thread.join(timeout=1.0)
        self.lobby.close()


class NetClient:
    """Joins a Val2d host by join code (internet) or "address[:port]" (LAN)."""

    def __init__(self, target: str, name: str, agent: str, timeout: float = 8.0) -> None:
        try:
            self.lobby = netplay.join_lobby(target, name)
        except (OSError, netplay.LobbyError, netplay.CodeError) as exc:
            raise ConnectionError(str(exc)) from exc
        self.lobby.send({"t": "hello", "agent": agent, "protocol": GAME_PROTOCOL})
        self.inbox: list[dict[str, Any]] = []
        deadline = time.monotonic() + timeout
        welcome = None
        while welcome is None and time.monotonic() < deadline:
            for ev in self.lobby.poll():
                if ev.kind == "message" and ev.message:
                    if ev.message.get("t") == "welcome":
                        welcome = ev.message
                    elif ev.message.get("t") == "error":
                        self.lobby.close()
                        raise ConnectionError(f"Join refused: {ev.message.get('reason', '')}")
                    else:
                        self.inbox.append(ev.message)
                elif ev.kind == "host_lost":
                    raise ConnectionError(f"Lost connection to host: {ev.reason}")
            time.sleep(0.01)
        if welcome is None:
            self.lobby.close()
            raise ConnectionError("The host did not answer.")
        self.pid = int(welcome["pid"])
        self.map_key = str(welcome["map"])
        self.connected = True
        self.status = ""

    def send(self, cmd: Command) -> None:
        try:
            self.lobby.send({"t": "cmd", "cmd": asdict(cmd)})
        except (ConnectionError, netplay.WireError, OSError) as exc:
            warnings.warn(f"Sending failed: {exc}")
            self.connected = False

    def choose_agent(self, agent: str) -> None:
        try:
            self.lobby.send({"t": "agent", "agent": agent})
        except (ConnectionError, OSError) as exc:
            warnings.warn(f"Sending failed: {exc}")

    def take(self) -> list[dict[str, Any]]:
        """Messages since the last call; only the newest state is kept, events are all kept."""
        msgs, self.inbox = self.inbox, []
        for ev in self.lobby.poll():
            if ev.kind == "message" and ev.message:
                msgs.append(ev.message)
            elif ev.kind == "host_lost":
                self.connected = False
                self.status = ev.reason
        out: list[dict[str, Any]] = []
        newest_state = None
        for m in msgs:
            if m.get("t") == "state":
                newest_state = m
            elif m.get("t") == "events":
                out.append({"type": "events", "events": m.get("events", [])})
        if newest_state is not None:
            out.append({"type": "state", "snap": newest_state.get("snap", {}), "events": []})
        return out

    def ping(self) -> float | None:
        return self.lobby.ping()

    def close(self) -> None:
        self.connected = False
        self.lobby.close()


def discover(timeout: float = 2.5) -> list[tuple[str, int, str]]:
    """Val2d LAN games: (address, port, host name)."""
    return netplay.discover_lan(timeout)
