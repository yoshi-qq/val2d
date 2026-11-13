"""Helpers for Val2d networking: command validation, snapshots, events, length-prefixed JSON frames.

Interim solution until netplay: the host runs the Match, clients send Commands,
the host sends per-viewer filtered snapshots (Match.snapshot) and events.
Message = 4-byte length (big endian) + JSON in UTF-8, at most MAX_MESSAGE bytes.
"""
from __future__ import annotations

import json
import math
import socket
import struct
from typing import Any

from gameplay.geometry import MAX_DRONE_PITCH, Rect, Vec
from gameplay.match import Command, Drop, Effect, GameEvent, Match, PlayerState, WeaponState
from gameplay.skins import skin_choice
from gameplay.world import Wall

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
_BOOL = ("fire", "alt_fire", "walk", "crouch", "jump", "reload", "interact", "use_spike", "drop")


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
    pitch = raw.get("drone_pitch")
    if type(pitch) in (int, float) and -MAX_DRONE_PITCH <= pitch <= MAX_DRONE_PITCH:
        cmd.drone_pitch = float(pitch)
    for key in _BOOL:
        setattr(cmd, key, bool(raw.get(key, False)))
    slot = raw.get("slot")
    cmd.slot = slot if slot in ("primary", "sidearm", "melee", "spike") else None
    actions = raw.get("equipment_actions")
    if isinstance(actions, list):
        cmd.equipment_actions = [action for action in actions[:32]
                                 if action in ("primary", "sidearm", "melee", "spike", "drop", "reload")]
        if cmd.equipment_actions:
            cmd.drop = "drop" in cmd.equipment_actions
            cmd.reload = "reload" in cmd.equipment_actions
            cmd.slot = next((action for action in reversed(cmd.equipment_actions)
                             if action not in ("drop", "reload")), None)
    ab = raw.get("ability")
    cmd.ability = ab if ab in ("C", "Q", "E", "X") else None
    cmd.ability_alt = bool(raw.get("ability_alt", False)) and cmd.ability is not None
    bounces = raw.get("bounces")
    if cmd.ability and type(bounces) is int and 0 <= bounces <= 2:
        cmd.bounces = bounces
    lift = raw.get("target_lift")
    if cmd.ability and type(lift) in (int, float) and 0 <= lift <= 120:
        cmd.target_lift = float(lift)
    pts = raw.get("points", [])
    if isinstance(pts, list) and cmd.ability:
        cmd.points = [(float(point[0]), float(point[1])) for point in pts[:8]
                      if isinstance(point, (list, tuple)) and len(point) == 2
                      and all(isinstance(v, (int, float)) and -1e6 <= v <= 1e6 and math.isfinite(v) for v in point)]
    buy = raw.get("buy", [])
    cmd.buy = [b for b in buy if isinstance(b, str) and len(b) <= 64][:8] if isinstance(buy, list) else []
    req = raw.get("request")
    cmd.request = req if isinstance(req, str) and len(req) <= 24 else None
    clicks = raw.get("request_clicks")
    if isinstance(clicks, list):
        cmd.request_clicks = [key for key in clicks[:16] if isinstance(key, str) and 0 < len(key) <= 24]
    return cmd


def merge_commands(old: Command | None, new: Command) -> Command:
    """Do not lose one-shot inputs between two host ticks."""
    if old is None:
        return new
    new.buy = old.buy + new.buy
    new.equipment_actions = old.ordered_equipment() + new.ordered_equipment()
    new.reload = new.reload or old.reload
    new.drop = new.drop or old.drop
    new.request = new.request if new.request is not None else old.request
    new.request_clicks = old.request_clicks + new.request_clicks
    new.slot = new.slot or old.slot
    if not new.ability:
        new.ability, new.ability_alt, new.points = old.ability, old.ability_alt, old.points
        new.target_lift = old.target_lift
        new.bounces = old.bounces
        if old.ability:
            new.facing, new.cursor_depth = old.facing, old.cursor_depth
    return new


def event_to_json(e: GameEvent) -> dict[str, Any]:
    return {"kind": e.kind, "t": e.t, "data": e.data}


# ------------------------------------------------------------------ Applying snapshots
def validate_snapshot_agents(m: Match, snap: dict[str, Any]) -> None:
    for rows in (snap.get("roster", []), snap["players"]):
        for row in rows:
            agent = row["agent"]
            if not isinstance(agent, str) or agent not in m.agents:
                raise ValueError(f"Snapshot contains unavailable agent {agent!r}.")


def apply_snapshot(m: Match, snap: dict[str, Any], own_pid: int, predict_own: bool = False,
                   server_pos: dict[int, Vec] | None = None) -> None:
    """Copies a host snapshot into a shadow match for drawing.

    predict_own: keep the client's own predicted position; the host's goes to server_pos[own_pid].
    server_pos: if given, every player's host position is stored there (for smoothing), not applied directly.
    """
    validate_snapshot_agents(m, snap)
    new_round = int(snap["round"]) != m.round_no
    rules = snap.get("rules")
    if isinstance(rules, dict):  # the host's lobby rules, shown and used for drawing on the client
        from dataclasses import replace
        known = {k: v for k, v in rules.items() if k in m.RULE_NAMES and isinstance(v, (bool, int))}
        m.cfg = replace(m.cfg, lobby=replace(m.cfg.lobby, **known))
    m.time = float(snap["time"])
    m.phase = snap["phase"]
    m.remote_minimap_obscured = bool(snap.get("minimap_obscured", False))
    m.remote_paranoia_warning = bool(snap.get("paranoia_warning", False))
    left = float(snap["phase_left"])
    m.phase_until = m.time + left
    if m.phase == "planted":
        m.spike_planted_at = m.time + left - float(m._spike["fuse_time"])
    m.round_no = int(snap["round"])
    mode = str(snap.get("mode", "standard"))
    if mode != m.mode or (mode == "standard" and (m.win_rounds, m.overtime) != (m.cfg.lobby.win_rounds, m.cfg.lobby.overtime)):
        m.set_mode(mode)
    m.dm_ends_at = m.time + float(snap.get("dm_left", 0.0))
    m.dm_timer_paused = bool(snap.get("dm_timer_paused", False))
    m.dm_stage = int(snap.get("dm_stage", 0))
    m.score = list(snap["score"])
    m.attacking_team = int(snap["attacking_team"])
    m.match_winner = snap["winner"]
    m.round_winner = snap["round_winner"]
    m.round_reason = snap["round_reason"]
    sp = snap["spike"]
    m.spike_carrier = sp["carrier"]
    m.spike_pos = Vec(*sp["pos"]) if sp["pos"] else None
    m.spike_ground = float(sp.get("ground", 0.0))
    m.spike_site = sp["site"]
    m.effects = [Effect(e["kind"], e.get("owner", 0), e["team"], Vec(e["x"], e["y"]), float(e.get("until", m.time + 1.0)), e["r"],
                        Vec(*e["a"]) if e["a"] else None, Vec(*e["b"]) if e["b"] else None,
                        start=float(e.get("start", 0.0)),
                        props={key: e.get(key) for key in ("status", "sprite", "sprite_width", "warning_sprite", "warning_start", "manual",
                                                          "recall_recharge", "soul_orb", "devour_tether", "cone", "aim",
                                                          "carrying_spike", "settled_ground", "fall", "clone_facing",
                                                          "flight_height", "bolt_path")})
                 for e in snap["effects"]]
    for effect, row in zip(m.effects, snap["effects"]):
        effect.props["source_level"] = row.get("source_level", 0)
        effect.props["blocks_sound"] = row.get("blocks_sound", False)
        effect.props["duel_id"] = row.get("duel_id", 0)
        if "blocks_sight" in row:
            effect.props["blocks_sight"] = bool(row["blocks_sight"])
        if row.get("barrier"):
            rect = Rect(*row["barrier"])
            if row.get("barrier_movement_only"):
                level = effect.props["source_level"]
                effect.props["barrier"] = Wall(rect, 0, blocks_sight=False, base=level, on_deck=level > 0,
                                               ceiling=level + 2, movement_only=True)
            else:
                effect.props["barrier"] = Wall(rect, 3)
    m.drops = [Drop(d["key"], 0, 0, Vec(d["x"], d["y"]), skin_choice(d["key"], d.get("skin")), d.get("ground"))
               for d in snap.get("drops", [])]
    m.history = [(int(w), str(r)) for w, r in snap.get("history", []) if isinstance(r, str)]
    m.orbs = [Vec(float(x), float(y)) for x, y in snap.get("orbs", [])]
    m.dm_recovery_orbs = {Vec(float(x), float(y)): m.time for x, y in snap.get("recovery_orbs", [])}
    m.remote_report = [r for r in snap.get("report", []) if isinstance(r, dict)]
    m.broken_cover = {Rect(*r) for r in snap.get("cover_broken", []) if isinstance(r, list) and len(r) == 4}
    m.open_doors = {Rect(*r) for r in snap.get("doors_open", []) if isinstance(r, list) and len(r) == 4}
    previously_visible = {p.pid for p in m.players.values() if p.visible}
    previous_lives = {p.pid: (p.alive, p.deaths) for p in m.players.values()} if mode == "deathmatch" else {}
    if "roster" in snap:
        present = {int(row["pid"]) for row in snap["roster"]}
        for pid in m.players.keys() - present:
            del m.players[pid]
            if server_pos is not None:
                server_pos.pop(pid, None)
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
        previous_life = previous_lives.get(pid)
        respawned = row["alive"] and previous_life is not None and previous_life != (True, row["deaths"])
        return_at = float(row.get("ability_return_at", -99.0))
        returned = return_at > p.ability_return_at
        p.ability_return_at = return_at
        duel_id = int(row.get("duel_id", 0))
        ghost = bool(row.get("dm_ghost", False))
        reset_motion = respawned or returned or p.duel_id != duel_id or p.dm_ghost != ghost
        if server_pos is not None:
            server_pos[pid] = host_pos
            if (pid not in previously_visible or (p.pos - host_pos).length() > 6.0 or new_round or reset_motion
                    or p.zipline != row.get("zipline")):
                p.pos = host_pos
        else:
            p.pos = host_pos
        if reset_motion or not (predict_own and pid == own_pid):
            p.vel = Vec(row.get("vx", 0.0), row.get("vy", 0.0))
        if reset_motion:
            p.vz = 0.0
        p.duel_id = duel_id
        p.duel_bounds = Rect(*row["duel_bounds"]) if row.get("duel_bounds") else None
        p.died_at = float(row.get("died_at", p.died_at))
        if p.agent == "clove":
            p.passive_state["clove_revived_round"] = bool(row.get("clove_revived_round"))
        p.z, p.level = row["z"], row["level"]
        p.ground = float(row.get("ground", p.level))
        p.zipline = row.get("zipline")
        p.quiet_landing_at = float(row.get("quiet_landing_at", -99.0))
        if pid != own_pid or new_round:
            p.facing = row["facing"]
        p.alive, p.hp, p.armor = row["alive"], row["hp"], row["armor"]
        p.overheal = int(row.get("overheal", 0))
        p.armor_key = str(row.get("armor_key", ""))
        p.armor_reserve = int(row.get("armor_reserve", 0))
        if row["credits"] is not None:
            p.credits = row["credits"]
        p.slot = row["slot"]
        p.dm_loadout = list(row.get("dm_loadout", []))
        p.dm_ghost = ghost
        p.dm_stage_equip_until = float(row.get("dm_stage_equip_until", 0.0))
        p.dm_spawn_protected_until = float(row.get("dm_spawn_protected_until", 0.0))
        p.dm_next_spawn_damage = float(row.get("dm_next_spawn_damage", 0.0))
        key = row["weapon"]
        p.weapons = {row["slot"]: WeaponState(key, row["mag"], row["reserve"], skin_choice(key, row.get("skin")),
                                             from_station=bool(row.get("from_station")))} if key else {}
        for slot, item in row.get("inventory", {}).items():
            key = item["key"]
            p.weapons[slot] = WeaponState(key, item["mag"], item["reserve"], skin_choice(key, item.get("skin")),
                                          from_station=bool(item.get("from_station")))
        p.charges = dict(row["charges"])
        p.ult_points = row["ult"]
        p.kills, p.deaths = row["kills"], row["deaths"]
        p.assists = int(row.get("assists", p.assists) or 0)
        p.crouching = bool(row.get("crouch", False))
        p.orb_progress = float(row.get("orb", 0.0) or 0.0)
        p.remote_sellable = list(row.get("sellable", []) or []) if pid == own_pid else []
        if pid == own_pid:
            p.dropped_at = float(row.get("dropped_at", -99.0))
        p.spray = row.get("spray", 0.0)
        p.blind_until = m.time + 0.3 if row["blind"] else 0.0
        p.revealed_until = float(row.get("revealed_until", 0.0))
        p.reload_until = m.time + 0.3 if row["reloading"] else 0.0
        p.plant_progress, p.defuse_progress = row["plant"], row["defuse"]
        p.defusing = bool(row.get("defusing", p.defuse_progress > 0))
        p.spike_equipped = bool(row.get("spike_equipped"))
        p.status = {k: m.time + 0.3 for k in row.get("status", [])}
        if "owl_drone_spotted_at" in row:
            p.passive_state["owl_drone_spotted_at"] = float(row["owl_drone_spotted_at"])
        else:
            p.passive_state.pop("owl_drone_spotted_at", None)
        if "kayo_downed_until" in row:
            p.passive_state["kayo_downed_until"] = float(row["kayo_downed_until"])
        else:
            p.passive_state.pop("kayo_downed_until", None)
        if row.get("viper_fuel") is not None:
            p.passive_state["viper_fuel"] = row["viper_fuel"]
        for key in ("neon_battery", "neon_ammo"):
            if row.get(key) is not None:
                p.passive_state[key] = row[key]
        p.request = str(row.get("request", "") or "")
        p.request_revision = int(row.get("request_revision", 0))
        anchor = row.get("anchor")
        p.anchor = Vec(*anchor) if isinstance(anchor, list) and len(anchor) == 2 else None
        p.anchor_until = m.time + 1.0 if p.anchor is not None else 0.0
        p.dash_until = m.time + 0.1 if row.get("dashing") else 0.0
        p.dash_armed_at = float(row.get("dash_armed_at", 0.0))
        p.dash_armed_until = float(row.get("dash_armed_until", 0.0))
        p.channel_until = float(row.get("channel_until", 0.0))
        if "omen_shade" in p.status:
            p.status["omen_shade"] = p.channel_until
        p.blade_count = int(row.get("blade_count", 0))
        p.blades_equipped = bool(row.get("blades_equipped"))
        p.repeat_shots = int(row.get("repeat_shots", 0))
        p.repeat_until = float(row.get("repeat_until", 0.0))
        p.repeat_next = float(row.get("repeat_next", 0.0))


def events_from_json(rows: list[dict[str, Any]]) -> list[GameEvent]:
    out = []
    for r in rows:
        if isinstance(r, dict) and isinstance(r.get("data"), dict):
            out.append(GameEvent(str(r.get("kind", "")), float(r.get("t", 0.0)), r["data"]))
    return out
