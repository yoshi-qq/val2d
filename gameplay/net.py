"""LAN play over TCP with JSON (no pickle) and game discovery via UDP broadcast.

Interim solution until netplay: the host runs the Match, clients send Commands,
the host sends per-viewer filtered snapshots (Match.snapshot) and events.
Message = 4-byte length (big endian) + JSON in UTF-8, at most MAX_MESSAGE bytes.
"""
from __future__ import annotations

import json
import socket
import struct
import threading
import time
import warnings
from dataclasses import asdict
from typing import Any

from gameplay.geometry import Vec
from gameplay.match import Command, Drop, Effect, GameEvent, Match, PlayerState, WeaponState

DEFAULT_PORT = 9009
DISCOVERY_PORT = 9010
MAX_MESSAGE = 512 * 1024
PROTOCOL = 1


# ------------------------------------------------------------------ Transport
def send_msg(sock: socket.socket, obj: dict[str, Any]) -> None:
    data = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    if len(data) > MAX_MESSAGE:
        raise ValueError(f"Message too large ({len(data)} bytes)")
    sock.sendall(struct.pack(">I", len(data)) + data)


def _recv_exact(sock: socket.socket, n: int) -> bytes | None:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def recv_msg(sock: socket.socket) -> dict[str, Any] | None:
    head = _recv_exact(sock, 4)
    if head is None:
        return None
    (size,) = struct.unpack(">I", head)
    if size > MAX_MESSAGE:
        raise ValueError(f"Message too large ({size} bytes)")
    body = _recv_exact(sock, size)
    if body is None:
        return None
    obj = json.loads(body.decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("Message is not an object")
    return obj


# ------------------------------------------------------------------ Command validation
_BOOL = ("fire", "alt_fire", "walk", "crouch", "jump", "reload", "interact")


def command_from_json(raw: dict[str, Any]) -> Command:
    """Builds a Command from unchecked data; anything invalid is dropped."""
    cmd = Command()
    for key in ("move_x", "move_y"):
        v = raw.get(key, 0.0)
        if isinstance(v, (int, float)):
            setattr(cmd, key, max(-1.0, min(1.0, float(v))))
    f = raw.get("facing")
    if isinstance(f, (int, float)):
        cmd.facing = float(f) % 360.0
    d = raw.get("cursor_depth")
    if isinstance(d, (int, float)):
        cmd.cursor_depth = max(0.0, min(120.0, float(d)))
    for key in _BOOL:
        setattr(cmd, key, bool(raw.get(key, False)))
    slot = raw.get("slot")
    cmd.slot = slot if slot in ("primary", "sidearm", "melee") else None
    ab = raw.get("ability")
    cmd.ability = ab if ab in ("C", "Q", "E", "X") else None
    buy = raw.get("buy", [])
    cmd.buy = [b for b in buy if isinstance(b, str) and len(b) <= 24][:8] if isinstance(buy, list) else []
    return cmd


def merge_commands(old: Command | None, new: Command) -> Command:
    """Do not lose one-shot inputs between two host ticks."""
    if old is None:
        return new
    new.buy = old.buy + new.buy
    new.reload = new.reload or old.reload
    new.slot = new.slot or old.slot
    new.ability = new.ability or old.ability
    return new


# ------------------------------------------------------------------ Host
class Host:
    def __init__(self, match: Match, host_name: str, port: int = DEFAULT_PORT) -> None:
        self.match = match
        self.port = port
        self.host_name = host_name
        self.clients: dict[int, socket.socket] = {}
        self.pending: dict[int, Command] = {}
        self.lobby: list[tuple[int, str]] = []
        self.lock = threading.Lock()
        self.accepting = True
        self.running = True
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("", port))
        self.server.listen()
        threading.Thread(target=self._accept_loop, daemon=True).start()
        threading.Thread(target=self._announce_loop, daemon=True).start()

    def _announce_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        msg = json.dumps({"val2d": PROTOCOL, "name": self.host_name, "port": self.port}).encode()
        while self.running:
            if self.accepting:
                try:
                    sock.sendto(msg, ("<broadcast>", DISCOVERY_PORT))
                except OSError as exc:
                    warnings.warn(f"Game announcement failed: {exc}")
            time.sleep(1.0)

    def _accept_loop(self) -> None:
        while self.running:
            try:
                conn, addr = self.server.accept()
            except OSError:
                return
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            threading.Thread(target=self._client_loop, args=(conn, addr), daemon=True).start()

    def _client_loop(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        pid: int | None = None
        try:
            hello = recv_msg(conn)
            if not hello or hello.get("type") != "hello" or hello.get("protocol") != PROTOCOL:
                send_msg(conn, {"type": "error", "reason": "Wrong version or no greeting"})
                return
            if not self.accepting:
                send_msg(conn, {"type": "error", "reason": "Match already running"})
                return
            name = str(hello.get("name", "Guest"))[:16] or "Guest"
            agent = str(hello.get("agent", "kestrel"))
            with self.lock:
                count = [sum(1 for p in self.match.players.values() if p.team == t) for t in (0, 1)]
                team = 0 if count[0] <= count[1] else 1
                p = self.match.add_player(name, team, agent)
                pid = p.pid
                self.clients[pid] = conn
                self.lobby.append((pid, name))
            send_msg(conn, {"type": "welcome", "pid": pid, "map": self.match.world.key, "team": team})
            while self.running:
                msg = recv_msg(conn)
                if msg is None:
                    break
                if msg.get("type") == "cmd":
                    cmd = command_from_json(msg.get("cmd", {}))
                    with self.lock:
                        self.pending[pid] = merge_commands(self.pending.get(pid), cmd)
                elif msg.get("type") == "agent":
                    self.choose_agent(pid, msg.get("agent"))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            warnings.warn(f"Connection to {addr[0]} closed: {exc}")
        finally:
            with self.lock:
                if pid is not None:
                    self.clients.pop(pid, None)
                    p = self.match.players.get(pid)
                    if p:  # a bot takes over disconnected players
                        p.is_bot = True
                        p.name += " (Bot)"
            try:
                conn.close()
            except OSError:
                pass

    def choose_agent(self, pid: int, agent: object) -> bool:
        """Agent change, only in the lobby and only to a known agent."""
        with self.lock:
            p = self.match.players.get(pid)
            if p is None or self.match.phase != "lobby" or not isinstance(agent, str) or agent not in self.match.agents:
                return False
            p.agent = agent
            return True

    def take_commands(self) -> dict[int, Command]:
        with self.lock:
            cmds = self.pending
            self.pending = {}
        return cmds

    def broadcast(self, events: list[GameEvent]) -> None:
        with self.lock:
            clients = list(self.clients.items())
        for pid, conn in clients:
            viewer = self.match.players.get(pid)
            if viewer is None:
                continue
            evs = [event_to_json(e) for e in events if self._event_visible(viewer, e)]
            try:
                send_msg(conn, {"type": "state", "snap": self.match.snapshot(pid), "events": evs})
            except (OSError, ValueError) as exc:
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

    def close(self) -> None:
        self.running = False
        try:
            self.server.close()
        except OSError:
            pass
        for conn in list(self.clients.values()):
            try:
                conn.close()
            except OSError:
                pass


def event_to_json(e: GameEvent) -> dict[str, Any]:
    return {"kind": e.kind, "t": e.t, "data": e.data}


# ------------------------------------------------------------------ Client
def discover(timeout: float = 3.0) -> list[tuple[str, int, str]]:
    """Looks for games on the local network: list of (address, port, host name)."""
    found: list[tuple[str, int, str]] = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("", DISCOVERY_PORT))
    except OSError as exc:
        warnings.warn(f"Game discovery not possible: {exc}")
        return found
    sock.settimeout(0.3)
    end = time.time() + timeout
    while time.time() < end:
        try:
            data, addr = sock.recvfrom(2048)
            info = json.loads(data.decode())
            if info.get("val2d") == PROTOCOL:
                entry = (addr[0], int(info.get("port", DEFAULT_PORT)), str(info.get("name", "?"))[:24])
                if entry not in found:
                    found.append(entry)
        except (socket.timeout, ValueError, json.JSONDecodeError):
            continue
    sock.close()
    return found


class Client:
    def __init__(self, address: str, port: int, name: str, agent: str) -> None:
        self.sock = socket.create_connection((address, port), timeout=5)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        send_msg(self.sock, {"type": "hello", "protocol": PROTOCOL, "name": name, "agent": agent})
        welcome = recv_msg(self.sock)
        if not welcome or welcome.get("type") != "welcome":
            reason = welcome.get("reason", "no answer") if welcome else "no answer"
            raise ConnectionError(f"Join refused: {reason}")
        self.sock.settimeout(None)
        self.pid = int(welcome["pid"])
        self.map_key = str(welcome["map"])
        self.inbox: list[dict[str, Any]] = []
        self.lock = threading.Lock()
        self.connected = True
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self) -> None:
        try:
            while True:
                msg = recv_msg(self.sock)
                if msg is None:
                    break
                with self.lock:
                    self.inbox.append(msg)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            if self.connected:
                warnings.warn(f"Lost connection to host: {exc}")
        self.connected = False

    def send(self, cmd: Command) -> None:
        try:
            send_msg(self.sock, {"type": "cmd", "cmd": asdict(cmd)})
        except OSError as exc:
            warnings.warn(f"Sending failed: {exc}")
            self.connected = False

    def choose_agent(self, agent: str) -> None:
        try:
            send_msg(self.sock, {"type": "agent", "agent": agent})
        except OSError as exc:
            warnings.warn(f"Sending failed: {exc}")
            self.connected = False

    def take(self) -> list[dict[str, Any]]:
        with self.lock:
            msgs = self.inbox
            self.inbox = []
        return msgs

    def close(self) -> None:
        self.connected = False
        try:
            self.sock.close()
        except OSError:
            pass


# ------------------------------------------------------------------ Applying snapshots
def apply_snapshot(m: Match, snap: dict[str, Any], own_pid: int) -> None:
    """Copies a host snapshot into a shadow match for drawing (no own simulation)."""
    new_round = int(snap["round"]) != m.round_no
    m.time = float(snap["time"])
    m.phase = snap["phase"]
    left = float(snap["phase_left"])
    m.phase_until = m.time + left
    if m.phase == "planted":
        m.spike_planted_at = m.time + left - float(m._spike["fuse_time"])
    m.round_no = int(snap["round"])
    m.score = list(snap["score"])
    m.attacking_team = int(snap["attacking_team"])
    m.match_winner = snap["winner"]
    m.round_winner = snap["round_winner"]
    m.round_reason = snap["round_reason"]
    sp = snap["spike"]
    m.spike_carrier = sp["carrier"]
    m.spike_pos = Vec(*sp["pos"]) if sp["pos"] else None
    m.spike_site = sp["site"]
    m.effects = [Effect(e["kind"], 0, e["team"], Vec(e["x"], e["y"]), float(e.get("until", m.time + 1.0)), e["r"],
                        Vec(*e["a"]) if e["a"] else None, Vec(*e["b"]) if e["b"] else None,
                        start=float(e.get("start", 0.0)), props={"status": e.get("status")}) for e in snap["effects"]]
    m.drops = [Drop(d["key"], 0, 0, Vec(d["x"], d["y"])) for d in snap.get("drops", [])]
    for row in snap.get("roster", []):
        pid = int(row["pid"])
        p = m.players.get(pid)
        if p is None:
            p = PlayerState(pid=pid, name=row["name"], team=row["team"], agent=row["agent"])
            m.players[pid] = p
        p.name, p.team, p.agent = row["name"], row["team"], row["agent"]
        p.kills, p.deaths, p.alive = row["kills"], row["deaths"], row["alive"]
        p.visible = False
    for row in snap["players"]:
        pid = int(row["pid"])
        p = m.players.get(pid)
        if p is None:
            p = PlayerState(pid=pid, name=row["name"], team=row["team"], agent=row["agent"])
            m.players[pid] = p
        p.visible = True
        p.is_bot = row["bot"]
        p.pos = Vec(row["x"], row["y"])
        p.vel = Vec(row.get("vx", 0.0), row.get("vy", 0.0))
        p.z, p.level = row["z"], row["level"]
        if pid != own_pid or new_round:
            p.facing = row["facing"]
        p.alive, p.hp, p.armor = row["alive"], row["hp"], row["armor"]
        if row["credits"] is not None:
            p.credits = row["credits"]
        p.slot = row["slot"]
        p.weapons = {row["slot"]: WeaponState(row["weapon"], row["mag"], row["reserve"])} if row["weapon"] else {}
        p.charges = dict(row["charges"])
        p.ult_points = row["ult"]
        p.kills, p.deaths = row["kills"], row["deaths"]
        p.spray = row.get("spray", 0.0)
        p.blind_until = m.time + 0.3 if row["blind"] else 0.0
        p.reload_until = m.time + 0.3 if row["reloading"] else 0.0
        p.plant_progress, p.defuse_progress = row["plant"], row["defuse"]
        p.status = {k: m.time + 0.3 for k in row.get("status", [])}


def events_from_json(rows: list[dict[str, Any]]) -> list[GameEvent]:
    out = []
    for r in rows:
        if isinstance(r, dict) and isinstance(r.get("data"), dict):
            out.append(GameEvent(str(r.get("kind", "")), float(r.get("t", 0.0)), r["data"]))
    return out
