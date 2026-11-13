"""Val2d over netplay: host and client for LAN (TCP, discoverable) and internet (UDP, join code).

The host runs the Match; clients send Commands and receive per-viewer snapshots (Match.snapshot).
State goes out unreliable (newest wins), events and everything else reliable. No pickle.
"""
from __future__ import annotations

import secrets
import threading
import time
import warnings
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

import netplay

from gameplay import abilities
from gameplay.match import Command, GameEvent, Match, PlayerState
from gameplay.net import command_from_json, event_to_json, merge_commands

DEFAULT_PORT = netplay.DEFAULT_PORT
GAME_PROTOCOL = 10


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
        self.generation = 0
        self.sequence = 0
        self.pending: dict[int, Command] = {}
        self.pid_of: dict[int, int] = {}  # lobby player id -> match pid
        self.tokens: dict[str, int] = {}  # rejoin token -> match pid
        self.dropped: dict[int, str] = {}  # match pid -> original name, while a bot plays for them
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
            with self.lock:
                if ev.kind == "left" and ev.player in self.pid_of:
                    pid = self.pid_of.pop(ev.player)
                    self.pending.pop(pid, None)
                    if self.match.phase == "lobby":
                        self.match.players.pop(pid, None)
                        self.tokens = {token: player for token, player in self.tokens.items() if player != pid}
                    elif (p := self.match.players.get(pid)) is not None:
                        self.dropped[pid] = p.name
                        p.request = ""
                        if p.dm_ghost:
                            self.match._toggle_deathmatch_ghost(p)
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
            if self._rejoin(lid, msg):
                return
            if not self.accepting:
                self.lobby.send({"t": "error", "reason": "The match has already started."}, to=lid)
                return
            name = self.lobby.players[lid].name if lid in self.lobby.players else "Guest"
            agent = str(msg.get("agent", ""))
            with self.lock:
                count = [sum(1 for p in self.match.players.values() if p.team == t) for t in (0, 1)]
                team = 0 if count[0] <= count[1] else 1
                p = self.match.add_player(name, team, agent, weapon_skins=msg.get("weapon_skins"))
                self.pid_of[lid] = p.pid
            token = secrets.token_hex(8)
            self.tokens[token] = p.pid
            self.lobby.send({"t": "welcome", "pid": p.pid, "map": self.match.world.key, "team": team,
                             "token": token, "game": self.generation}, to=lid)
        elif t == "cmd" and lid in self.pid_of:
            if msg.get("game") != self.generation or self.match.phase in ("lobby", "over"):
                return
            cmd = command_from_json(msg.get("cmd", {}) if isinstance(msg.get("cmd"), dict) else {})
            pid = self.pid_of[lid]
            with self.lock:
                self.pending[pid] = merge_commands(self.pending.get(pid), cmd)
        elif t == "agent" and lid in self.pid_of and msg.get("game") == self.generation:
            self.choose_agent(self.pid_of[lid], msg.get("agent"))
        elif t == "team" and lid in self.pid_of and msg.get("game") == self.generation:
            self.choose_team(self.pid_of[lid], msg.get("team"))

    def _rejoin(self, lid: int, msg: dict[str, Any]) -> bool:
        """Give a dropped player their slot back: by token, or by the same name if the game was restarted."""
        token = str(msg.get("token", ""))
        pid = self.tokens.get(token) if token else None
        if pid is None or pid not in self.dropped:
            name = self.lobby.players[lid].name if lid in self.lobby.players else ""
            pid = next((d for d, original in self.dropped.items() if original == name), None)
        if pid is None:
            return False
        with self.lock:
            p = self.match.players.get(pid)
            if p is None:
                return False
            p.is_bot = False
            p.name = self.dropped.pop(pid)
            self.pid_of[lid] = pid
        new_token = secrets.token_hex(8)
        self.tokens = {t: v for t, v in self.tokens.items() if v != pid}
        self.tokens[new_token] = pid
        self.lobby.send({"t": "welcome", "pid": pid, "map": self.match.world.key, "team": p.team, "token": new_token,
                         "rejoined": True, "game": self.generation}, to=lid)
        return True

    def choose_agent(self, pid: int, agent: object) -> bool:
        with self.lock:
            p = self.match.players.get(pid)
            if p is None or self.match.phase != "lobby" or not isinstance(agent, str) or agent not in self.match.agents:
                return False
            p.agent = agent
            return True

    def choose_team(self, pid: int, team: object) -> bool:
        with self.lock:
            p = self.match.players.get(pid)
            if p is None or self.match.phase != "lobby" or type(team) is not int or team not in (0, 1):
                return False
            if p.team != team and sum(other.team == team for other in self.match.players.values()) >= 5:
                return False
            p.team = team
            return True

    def take_commands(self) -> dict[int, Command]:
        with self.lock:
            cmds, self.pending = self.pending, {}
        return cmds

    # ------------------------------------------------------------ outgoing
    def broadcast(self, events: list[GameEvent]) -> None:
        self.sequence += 1
        for lid, pid in list(self.pid_of.items()):
            viewer = self.match.players.get(pid)
            if viewer is None:
                continue
            try:
                visible = [event_to_json(e) for e in events if self._event_visible(viewer, e)]
                if visible:
                    self.lobby.send({"t": "events", "game": self.generation, "events": visible}, to=lid)
                self.lobby.send({"t": "state", "game": self.generation, "seq": self.sequence, "map": self.match.world.key,
                                 "snap": self.match.snapshot(pid)}, to=lid, reliable=False)
            except (OSError, netplay.WireError, netplay.LobbyError) as exc:
                warnings.warn(f"Sending to player {pid} failed: {exc}")

    def _event_visible(self, viewer: PlayerState, e: GameEvent) -> bool:
        if e.kind in ("jump", "land"):
            from gameplay.geometry import Vec

            lander = self.match.players.get(e.data["pid"])
            if lander is not None and (viewer.pid == lander.pid or self.match.can_see(viewer, lander)):
                return True
            if e.data.get("quiet"):
                return False
            listeners = [viewer]
            if not viewer.alive and self.match.phase in ("live", "planted"):
                listeners = [p for p in self.match.players.values() if p.alive and p.team == viewer.team] or listeners
            origin = Vec(*e.data["pos"])
            radius = 12 if e.kind == "jump" else 18
            return any((p.pos - origin).length() < radius and not self.match.sound_blocked(p.pos, origin)
                       and not abilities.flag(self.match, p, "deaf") for p in listeners)
        if e.kind in ("sound", "sound_fx") and (pos := e.data.get("pos")) is not None:
            from gameplay.geometry import Vec

            data = e.data
            world_sound = e.kind == "sound"
            if data.get("range_filtered") and data.get("team", viewer.team) != viewer.team:
                return False
            listeners = [viewer]
            if (not viewer.alive and (world_sound or data.get("pid") != viewer.pid)
                    and self.match.phase in ("live", "planted")):
                listeners = [p for p in self.match.players.values() if p.alive and p.team == viewer.team] or listeners
            origin = Vec(*pos)
            if world_sound:
                return any(not self.match.sound_blocked(p.pos, origin)
                           and not abilities.flag(self.match, p, "deaf")
                           and ("shot_facing" not in data or e.within_sound_range(p.pos))
                           for p in listeners)
            return any(not self.match.sound_blocked(p.pos, origin)
                       and (not data.get("range_filtered") or
                            (not abilities.flag(self.match, p, "deaf")
                             and (data.get("pid") == viewer.pid or e.within_sound_range(p.pos))))
                       for p in listeners)
        if e.kind == "kayo_scan":
            return e.data.get("team") == viewer.team
        if e.kind in ("ability_return", "assist", "device_hit_audio", "owl_dart_hit",
                      "neon_battery_low", "neon_battery_empty", "neon_battery_insufficient"):
            return e.data.get("pid") == viewer.pid
        if e.kind in ("lockdown_destroyed", "lockdown_result"):
            return e.data["team"] == viewer.team
        if e.kind in ("shot", "hit"):
            shooter = self.match.players.get(e.data.get("pid") if e.kind == "shot" else e.data.get("by"))
            return shooter is None or self.match.can_see(viewer, shooter) or e.data.get("by") == viewer.pid
        if e.kind == "buy":
            buyer = self.match.players.get(e.data.get("pid"))
            return buyer is not None and buyer.team == viewer.team
        return True

    def ping(self, pid: int) -> float | None:
        lid = next((l for l, p in self.pid_of.items() if p == pid), None)
        return self.lobby.ping(lid) if lid is not None else None

    def announce_party_closed(self) -> None:
        with self.lock:
            recipients = tuple(self.pid_of)
            generation = self.generation
        for lid in recipients:
            try:
                self.lobby.send({"t": "party_closed", "game": generation}, to=lid)
            except (ConnectionError, OSError, netplay.WireError, netplay.LobbyError):
                continue

    def close(self) -> None:
        self.running = False
        if self._thread is not threading.current_thread():
            self._thread.join(timeout=1.0)
        self.lobby.close()


class NetClient:
    """Joins a Val2d host by join code (internet) or "address[:port]" (LAN)."""

    def __init__(self, target: str, name: str, agent: str, timeout: float = 8.0, token: str = "", *,
                 weapon_skins: dict[str, str] | None = None) -> None:
        host, sep, port = target.strip().partition(":")
        if host.lower() == "localhost":
            target = "127.0.0.1" + sep + port
        try:
            self.lobby = netplay.join_lobby(target, name)
        except (OSError, ValueError, netplay.LobbyError, netplay.CodeError) as exc:
            raise ConnectionError(str(exc)) from exc
        self.lobby.send({"t": "hello", "agent": agent, "protocol": GAME_PROTOCOL, "token": token,
                         "weapon_skins": weapon_skins or {}})
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
        self.token = str(welcome.get("token", ""))
        self.rejoined = bool(welcome.get("rejoined", False))
        self.generation = int(welcome["game"])
        self.state_sequence = -1
        self.previous_lobby_generation: int | None = None
        self.connected = True
        self.party_closed = False
        self.status = ""

    def send(self, cmd: Command) -> None:
        try:
            self.lobby.send({"t": "cmd", "game": self.generation, "cmd": asdict(cmd)})
        except (ConnectionError, netplay.WireError, OSError) as exc:
            warnings.warn(f"Sending failed: {exc}")
            self.connected = False

    def choose_agent(self, agent: str) -> None:
        try:
            self.lobby.send({"t": "agent", "game": self.generation, "agent": agent})
        except (ConnectionError, OSError) as exc:
            warnings.warn(f"Sending failed: {exc}")

    def choose_team(self, team: int) -> None:
        try:
            self.lobby.send({"t": "team", "game": self.generation, "team": team})
        except (ConnectionError, OSError) as exc:
            warnings.warn(f"Sending failed: {exc}")

    def take(self, *, validate_state: Callable[[dict[str, Any]], None] | None = None) -> list[dict[str, Any]]:
        """Messages since the last call; only the newest state is kept, events are all kept."""
        msgs, self.inbox = self.inbox, []
        for ev in self.lobby.poll():
            if ev.kind == "message" and ev.message:
                msgs.append(ev.message)
            elif ev.kind == "host_lost":
                self.connected = False
                self.status = ev.reason
        out: list[dict[str, Any]] = []
        previous_generation = self.generation
        newest = (previous_generation, self.state_sequence)
        state = None
        for msg in msgs:
            if (msg.get("t") == "state" and type(msg.get("game")) is int and type(msg.get("seq")) is int
                    and isinstance(msg.get("snap"), dict) and isinstance(msg.get("map"), str)):
                stamp = (msg["game"], msg["seq"])
                if stamp > newest:
                    if validate_state is not None:
                        try:
                            validate_state(msg)
                        except (KeyError, OSError, TypeError, ValueError) as exc:
                            warnings.warn(f"Snapshot from host unreadable: {exc}")
                            continue
                    newest, state = stamp, msg
        self.generation, self.state_sequence = newest
        if state is not None:
            if state["snap"].get("phase") != "lobby":
                self.previous_lobby_generation = None
            elif previous_generation < self.generation:
                self.previous_lobby_generation = previous_generation
        for msg in msgs:
            if msg.get("t") == "party_closed" and msg.get("game") == self.generation:
                self.party_closed = True
                self.connected = False
            if msg.get("t") == "events" and type(msg.get("game")) is int and isinstance(msg.get("events"), list):
                if msg["game"] == self.generation:
                    out.append({"type": "events", "events": msg["events"]})
                elif msg["game"] == self.previous_lobby_generation:
                    results = [event for event in msg["events"]
                               if isinstance(event, dict) and event.get("kind") == "round_end"]
                    if results:
                        out.append({"type": "events", "events": results})
                elif msg["game"] > self.generation:
                    self.inbox.append(msg)
        if state is not None:
            self.map_key = state["map"]
            out.append({"type": "state", "snap": state["snap"], "map": self.map_key, "game": self.generation})
        return out

    def ping(self) -> float | None:
        return self.lobby.ping()

    def close(self) -> None:
        self.connected = False
        self.lobby.close()


def discover(timeout: float = 2.5) -> list[tuple[str, int, str]]:
    """Val2d LAN games: (address, port, host name)."""
    return netplay.discover_lan(timeout)
