"""Helpers for Val2d networking: command validation, snapshots, events, length-prefixed JSON frames.

Interim solution until netplay: the host runs the Match, clients send Commands,
the host sends per-viewer filtered snapshots (Match.snapshot) and events.
Message = 4-byte length (big endian) + JSON in UTF-8, at most MAX_MESSAGE bytes.
"""
from __future__ import annotations

import json
import socket
import struct
from typing import Any

from gameplay.geometry import Rect, Vec
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
_BOOL = ("fire", "alt_fire", "walk", "crouch", "jump", "reload", "interact", "drop")


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
    cmd.ability_alt = bool(raw.get("ability_alt", False)) and cmd.ability is not None
    buy = raw.get("buy", [])
    cmd.buy = [b for b in buy if isinstance(b, str) and len(b) <= 32][:8] if isinstance(buy, list) else []
    req = raw.get("request")
    cmd.request = req if isinstance(req, str) and len(req) <= 24 else None
    return cmd


def merge_commands(old: Command | None, new: Command) -> Command:
    """Do not lose one-shot inputs between two host ticks."""
    if old is None:
        return new
    new.buy = old.buy + new.buy
    new.reload = new.reload or old.reload
    new.drop = new.drop or old.drop
    new.request = new.request if new.request is not None else old.request
    new.slot = new.slot or old.slot
    if not new.ability:
        new.ability, new.ability_alt = old.ability, old.ability_alt
    return new


def event_to_json(e: GameEvent) -> dict[str, Any]:
    return {"kind": e.kind, "t": e.t, "data": e.data}


# ------------------------------------------------------------------ Applying snapshots
def apply_snapshot(m: Match, snap: dict[str, Any], own_pid: int, predict_own: bool = False,
                   server_pos: dict[int, Vec] | None = None) -> None:
    """Copies a host snapshot into a shadow match for drawing.

    predict_own: keep the client's own predicted position; the host's goes to server_pos[own_pid].
    server_pos: if given, every player's host position is stored there (for smoothing), not applied directly.
    """
    new_round = int(snap["round"]) != m.round_no
    rules = snap.get("rules")
    if isinstance(rules, dict):  # the host's lobby rules, shown and used for drawing on the client
        from dataclasses import replace
        known = {k: v for k, v in rules.items() if k in m.RULE_NAMES and isinstance(v, (bool, int))}
        m.cfg = replace(m.cfg, lobby=replace(m.cfg.lobby, **known))
    m.time = float(snap["time"])
    m.phase = snap["phase"]
    left = float(snap["phase_left"])
    m.phase_until = m.time + left
    if m.phase == "planted":
        m.spike_planted_at = m.time + left - float(m._spike["fuse_time"])
    m.round_no = int(snap["round"])
    m.mode = str(snap.get("mode", "standard"))
    m.dm_ends_at = m.time + float(snap.get("dm_left", 0.0))
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
    m.history = [(int(w), str(r)) for w, r in snap.get("history", []) if isinstance(r, str)]
    m.orbs = [Vec(float(x), float(y)) for x, y in snap.get("orbs", [])]
    m.remote_report = [r for r in snap.get("report", []) if isinstance(r, dict)]
    m.open_doors = {Rect(*r) for r in snap.get("doors_open", []) if isinstance(r, list) and len(r) == 4}
    for row in snap.get("roster", []):
        pid = int(row["pid"])
        p = m.players.get(pid)
        if p is None:
            p = PlayerState(pid=pid, name=row["name"], team=row["team"], agent=row["agent"])
            m.players[pid] = p
        p.name, p.team, p.agent = row["name"], row["team"], row["agent"]
        p.kills, p.deaths, p.alive = row["kills"], row["deaths"], row["alive"]
        p.assists = int(row.get("assists", p.assists) or 0)
        p.is_bot = bool(row.get("bot", p.is_bot))
        p.damage_total = int(row.get("damage", p.damage_total) or 0)
        p.remote_score = int(row.get("score", 0) or 0)
        ping = row.get("ping")
        p.ping_ms = int(ping) if isinstance(ping, (int, float)) else None
        p.visible = False
    for row in snap["players"]:
        pid = int(row["pid"])
        p = m.players.get(pid)
        if p is None:
            p = PlayerState(pid=pid, name=row["name"], team=row["team"], agent=row["agent"])
            m.players[pid] = p
        p.visible = True
        p.is_bot = row["bot"]
        host_pos = Vec(row["x"], row["y"])
        if server_pos is not None:
            server_pos[pid] = host_pos
            if pid not in m.players or (p.pos - host_pos).length() > 6.0 or new_round:
                p.pos = host_pos  # far off or a new round: jump instead of gliding
        else:
            p.pos = host_pos
        if not (predict_own and pid == own_pid):
            p.vel = Vec(row.get("vx", 0.0), row.get("vy", 0.0))
        p.z, p.level = row["z"], row["level"]
        p.ground = float(row.get("ground", p.level))
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
        p.assists = int(row.get("assists", p.assists) or 0)
        p.crouching = bool(row.get("crouch", False))
        p.orb_progress = float(row.get("orb", 0.0) or 0.0)
        p.remote_sellable = list(row.get("sellable", []) or []) if pid == own_pid else []
        p.spray = row.get("spray", 0.0)
        p.blind_until = m.time + 0.3 if row["blind"] else 0.0
        p.reload_until = m.time + 0.3 if row["reloading"] else 0.0
        p.plant_progress, p.defuse_progress = row["plant"], row["defuse"]
        p.status = {k: m.time + 0.3 for k in row.get("status", [])}
        p.request = str(row.get("request", "") or "")
        anchor = row.get("anchor")
        p.anchor = Vec(*anchor) if isinstance(anchor, list) and len(anchor) == 2 else None
        p.anchor_until = m.time + 1.0 if p.anchor is not None else 0.0
        p.dash_until = m.time + 0.1 if row.get("dashing") else 0.0


def events_from_json(rows: list[dict[str, Any]]) -> list[GameEvent]:
    out = []
    for r in rows:
        if isinstance(r, dict) and isinstance(r.get("data"), dict):
            out.append(GameEvent(str(r.get("kind", "")), float(r.get("t", 0.0)), r["data"]))
    return out
