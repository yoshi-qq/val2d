"""Authoritative match: movement, combat, economy, rounds, bomb, abilities.

Controlled only through one Command per player and tick. A host (player 1 or a dedicated
server process) runs Match.tick and sends Match.snapshot() to everyone.
"""
from __future__ import annotations

import math
import random
import warnings
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from gameplay import abilities
from gameplay.data import ROOT, GameConfig, WeaponDef, _load_py, load_armor, load_config, load_weapons, rule
from gameplay.geometry import Rect, Vec, angle_diff, angle_of, heading, segment_circle_hit
from gameplay.hitzones import resolve_zone
from gameplay.world import Wall, WorldMap

SLOTS = ("primary", "sidearm", "melee")
PEN_DAMAGE = {0: 0.8, 1: 0.6, 2: 0.45}  # damage factor after passing through a material (own value)
INTERACT_RANGE = 1.5
DOOR_RANGE = 1.6
PICKUP_RANGE = 1.2


AGENTS_PATH = ROOT / "config" / "agents.py"


@lru_cache(maxsize=1)
def load_agents() -> dict[str, dict[str, Any]]:
    """Agents from config/agents.py; broken entries are skipped with a warning."""
    raw = _load_py(AGENTS_PATH, "AGENTS") or {}
    out: dict[str, dict[str, Any]] = {}
    for key, agent in raw.items():
        try:
            abil = {slot: dict(agent["abilities"][slot]) for slot in ("C", "Q", "E", "X")}
            out[key] = {"name": str(agent["name"]), "role": str(agent.get("role", "")), "abilities": abil,
                        "sprites": dict(agent.get("sprites", {}))}
        except (KeyError, TypeError) as exc:
            warnings.warn(f"Agent {key} skipped: {exc}")
    return out


@lru_cache(maxsize=1)
def load_status_rules() -> dict[str, float]:
    return dict(_load_py(AGENTS_PATH, "STATUS_RULES") or {})


@dataclass
class Command:
    move_x: float = 0.0          # sideways, -1 left … 1 right (relative to facing)
    move_y: float = 0.0          # forward/back, 1 forward
    facing: float | None = None  # compass angle in degrees
    cursor_depth: float = 8.0    # distance of the cursor ahead of the player (metres)
    fire: bool = False
    alt_fire: bool = False       # right mouse button: alternate fire of the weapon
    walk: bool = False
    crouch: bool = False
    jump: bool = False
    reload: bool = False
    slot: str | None = None
    ability: str | None = None   # "C", "Q", "E", "X"
    interact: bool = False       # plant or defuse the bomb (hold)
    buy: list[str] = field(default_factory=list)


@dataclass
class WeaponState:
    key: str
    mag: int
    reserve: int


@dataclass
class PlayerState:
    pid: int
    name: str
    team: int
    agent: str
    is_bot: bool = False
    pos: Vec = Vec(0, 0)
    vel: Vec = Vec(0, 0)
    z: float = 0.0
    vz: float = 0.0
    level: int = 0
    facing: float = 0.0
    cursor_depth: float = 8.0
    alive: bool = True
    hp: int = 100
    armor: int = 0
    credits: int = 800
    weapons: dict[str, WeaponState] = field(default_factory=dict)
    slot: str = "sidearm"
    walking: bool = False
    crouching: bool = False
    next_shot: float = 0.0
    reload_until: float = 0.0
    equip_until: float = 0.0
    spray: float = 0.0
    fire_held: float = 0.0  # seconds of continuous fire (for rate_ramp)
    burst_left: int = 0
    prev_fire: bool = False
    prev_alt: bool = False
    zoomed: bool = False
    burst_gap: float = 0.075
    burst_cool: float = 0.0
    burst_spread: float = 1.0
    charges: dict[str, int] = field(default_factory=dict)
    sig_timer: float = 0.0
    sig_kills: int = 0
    ult_points: int = 0
    kills: int = 0
    deaths: int = 0
    blind_until: float = 0.0
    revealed_until: float = 0.0
    overdrive_until: float = 0.0
    dash_until: float = 0.0
    dash_vel: Vec = Vec(0, 0)
    plant_progress: float = 0.0
    defuse_progress: float = 0.0
    status: dict[str, float] = field(default_factory=dict)  # status -> active until
    immune_until: float = 0.0
    anchor: Vec | None = None
    anchor_until: float = 0.0
    heal_left: float = 0.0
    heal_rate: float = 0.0
    hp_frac: float = 0.0
    decay_pool: float = 0.0
    recharge_timers: dict[str, float] = field(default_factory=dict)
    last_pos: Vec | None = None
    prev_ability: str | None = None
    prev_interact: bool = False
    visible: bool = True  # only meaningful in a client's shadow match

    @property
    def weapon(self) -> WeaponState | None:
        return self.weapons.get(self.slot)


@dataclass
class Drop:
    key: str
    mag: int
    reserve: int
    pos: Vec


@dataclass
class Effect:
    kind: str
    owner: int
    team: int
    pos: Vec
    until: float
    radius: float = 0.0
    a: Vec | None = None
    b: Vec | None = None
    start: float = 0.0
    data: dict[str, float] = field(default_factory=dict)
    props: dict[str, Any] = field(default_factory=dict)


@dataclass
class GameEvent:
    kind: str  # shot, hit, kill, sound, plant, defuse, explode, round_end, ability, buy
    t: float
    data: dict[str, Any]


class Match:
    def __init__(self, world: WorldMap, config: GameConfig | None = None, seed: int | None = None) -> None:
        self.world = world
        self.cfg = config or load_config()
        self.weapons = load_weapons()
        self.armor = load_armor()
        self.agents = load_agents()
        self.status_rules = load_status_rules()
        self.rng = random.Random(seed)
        self.players: dict[int, PlayerState] = {}
        self.effects: list[Effect] = []
        self.drops: list[Drop] = []
        self.events: list[GameEvent] = []
        self.open_doors: set[Rect] = set()
        self.time = 0.0
        self.phase = "lobby"  # lobby, buy, live, planted, end, over
        self.phase_until = 0.0
        self.round_no = 0
        self.score = [0, 0]
        self.attacking_team = 0
        self.loss_streak = [0, 0]
        self.spike_carrier: int | None = None
        self.spike_pos: Vec | None = None
        self.spike_planted_at = 0.0
        self.spike_site = ""
        self.round_winner: int | None = None
        self.round_reason = ""
        self.match_winner: int | None = None
        self.win_rounds = self.cfg.lobby.win_rounds
        self.overtime = self.cfg.lobby.overtime
        self._r = {k: rule("rounds", k, d) for k, d in (("buy_time", 30), ("round_time", 100), ("end_time", 6), ("half_after", 12), ("overtime_margin", 2), ("overtime_credits", 5000))}
        self._mv = {k: rule("movement", k, d) for k, d in (("run_speed", 6.0), ("walk_mod", 0.55), ("crouch_mod", 0.4), ("air_mod", 0.9), ("accel", 60.0), ("decel", 45.0), ("jump_velocity", 4.2), ("gravity", 14.0), ("radius", 0.4), ("level_height", 1.0))}
        self._eco = {k: rule("economy", k, d) for k, d in (("start", 800), ("win", 3000), ("loss", [1800, 2300, 2800]), ("kill", 200), ("plant", 300), ("max", 9000))}
        self._spike = {k: rule("spike", k, d) for k, d in (("plant_time", 4.0), ("fuse_time", 45.0), ("defuse_time", 7.0), ("defuse_checkpoint", 3.5), ("blast_radius", 12.0))}
        self._ult = {k: rule("ultimate", k, d) for k, d in (("per_kill", 1), ("per_plant", 1), ("per_defuse", 1), ("per_death", 1))}
        self.fov = float(rule("sight", "fov", 103.0))
        self._absorb = float(rule("vitals", "armor_absorb", 0.66))
        self._hp = int(rule("vitals", "hp", 100))
        self._sound = {k: rule("sound", k, d) for k, d in (("run_radius", 18.0), ("shot_radius", 45.0), ("silenced_radius", 12.0))}

    # ------------------------------------------------------------------ Setup
    def add_player(self, name: str, team: int, agent: str, is_bot: bool = False) -> PlayerState:
        if agent not in self.agents:
            warnings.warn(f"Unknown agent {agent}; using {next(iter(self.agents), 'kestrel')}.")
            agent = next(iter(self.agents), "kestrel")
        pid = max(self.players, default=0) + 1
        p = PlayerState(pid=pid, name=name, team=team, agent=agent, is_bot=is_bot, credits=int(self._eco["start"]))
        self.players[pid] = p
        return p

    def start(self) -> None:
        self.round_no = 0
        self.score = [0, 0]
        self.match_winner = None
        self.attacking_team = 0
        self._start_round()

    # ------------------------------------------------------------------ Rounds
    def side(self, team: int) -> str:
        return "attack" if team == self.attacking_team else "defense"

    def _is_pistol_round(self) -> bool:
        half = int(self._r["half_after"])
        return self.round_no == 1 or self.round_no == half + 1

    def _in_overtime(self) -> bool:
        return self.round_no > 2 * int(self._r["half_after"])

    def _start_round(self) -> None:
        self.round_no += 1
        half = int(self._r["half_after"])
        if self.round_no == half + 1 or (self._in_overtime() and self.round_no > 1):
            self.attacking_team = 1 - self.attacking_team
        pistol = self._is_pistol_round()
        self.effects.clear()
        self.drops.clear()
        self.open_doors.clear()
        self.round_winner = None
        self.round_reason = ""
        self.spike_pos = None
        self.spike_site = ""
        spawn_idx = {0: 0, 1: 0}
        for p in self.players.values():
            side_idx = 0 if self.side(p.team) == "attack" else 1
            pts = self.world.spawns.get(side_idx) or [self.world.spawn_zones.get(side_idx, Rect(0, 0, 1, 1)).center]
            p.pos = pts[spawn_idx[side_idx] % len(pts)]
            spawn_idx[side_idx] += 1
            enemy_zone = self.world.spawn_zones.get(1 - side_idx)
            p.facing = angle_of(enemy_zone.center - p.pos) if enemy_zone else 0.0
            if pistol or self._in_overtime():
                p.weapons = {}
                p.armor = 0
                p.charges = {}
                p.credits = int(self._r["overtime_credits"]) if self._in_overtime() else int(self._eco["start"])
            if not p.alive:
                p.weapons = {}
                p.armor = 0
            if "sidearm" not in p.weapons:
                p.weapons["sidearm"] = self._new_weapon("spatz")
            p.weapons["melee"] = self._new_weapon("messer")
            for ws in p.weapons.values():
                d = self.weapons.get(ws.key)
                if d:
                    ws.mag, ws.reserve = d.mag, d.reserve
            p.alive = True
            p.hp = self._hp
            p.vel = Vec(0, 0)
            p.z = p.vz = 0.0
            p.level = 0
            p.slot = "primary" if "primary" in p.weapons else "sidearm"
            p.spray = 0.0
            p.blind_until = p.revealed_until = p.overdrive_until = p.dash_until = p.immune_until = 0.0
            p.status = {}
            p.anchor, p.anchor_until = None, 0.0
            p.heal_left = p.heal_rate = p.hp_frac = p.decay_pool = 0.0
            p.recharge_timers = {}
            p.last_pos = None
            p.plant_progress = p.defuse_progress = 0.0
            for key, ab in self.agents[p.agent]["abilities"].items():
                if key == "X":
                    continue
                start = int(ab.get("start", 0))
                p.charges[key] = max(p.charges.get(key, 0), start)
            p.sig_timer = 0.0
            p.sig_kills = 0
        attackers = [p for p in self.players.values() if self.side(p.team) == "attack"]
        humans = [p for p in attackers if not p.is_bot]
        carrier = self.rng.choice(humans or attackers) if attackers else None
        self.spike_carrier = carrier.pid if carrier else None
        self.phase = "buy"
        self.phase_until = self.time + float(self._r["buy_time"])

    def _end_round(self, winner_team: int, reason: str) -> None:
        if self.phase in ("end", "over"):
            return
        self.round_winner = winner_team
        self.round_reason = reason
        self.score[winner_team] += 1
        loser = 1 - winner_team
        self.loss_streak[winner_team] = 0
        self.loss_streak[loser] += 1
        losses = list(self._eco["loss"])
        for p in self.players.values():
            if p.team == winner_team:
                p.credits += int(self._eco["win"])
            else:
                p.credits += int(losses[min(self.loss_streak[loser], len(losses)) - 1])
            p.credits = min(p.credits, int(self._eco["max"]))
        self.events.append(GameEvent("round_end", self.time, {"winner": winner_team, "reason": reason, "score": list(self.score)}))
        if self._match_decided():
            self.match_winner = winner_team
            self.phase = "over"
            return
        self.phase = "end"
        self.phase_until = self.time + float(self._r["end_time"])

    def _match_decided(self) -> bool:
        a, b = self.score
        need = self.win_rounds
        if max(a, b) < need:
            return False
        if not self.overtime:
            return True
        if a >= need - 1 and b >= need - 1:
            return abs(a - b) >= int(self._r["overtime_margin"])
        return True

    # ------------------------------------------------------------------ Buying
    def buy(self, p: PlayerState, item: str) -> bool:
        if self.phase != "buy" or not p.alive:
            return False
        zone = self.world.spawn_zones.get(0 if self.side(p.team) == "attack" else 1)
        if zone and not zone.contains(p.pos):
            return False
        if item in self.weapons:
            d = self.weapons[item]
            if d.slot == "melee" or p.credits < d.price:
                return False
            p.credits -= d.price
            p.weapons[d.slot] = self._new_weapon(item)
            p.slot = d.slot
            p.equip_until = self.time + d.equip
        elif item in self.armor:
            a = self.armor[item]
            if p.credits < a.price or p.armor >= a.points:
                return False
            p.credits -= a.price
            p.armor = a.points
        elif item in ("C", "Q", "E"):
            ab = self.agents[p.agent]["abilities"].get(item)
            if not ab or p.charges.get(item, 0) >= int(ab["max"]) or p.credits < int(ab["price"]) or int(ab["price"]) == 0:
                return False
            p.credits -= int(ab["price"])
            p.charges[item] = p.charges.get(item, 0) + 1
        else:
            warnings.warn(f"Unknown buy request: {item}")
            return False
        self.events.append(GameEvent("buy", self.time, {"pid": p.pid, "item": item}))
        return True

    def _new_weapon(self, key: str) -> WeaponState:
        d = self.weapons.get(key)
        return WeaponState(key, d.mag if d else 0, d.reserve if d else 0)

    # ------------------------------------------------------------------ Tick
    def tick(self, dt: float, commands: dict[int, Command]) -> list[GameEvent]:
        self.events = []
        if self.phase in ("lobby", "over"):
            return self.events
        dt = max(0.0, min(dt, 0.1))
        self.time += dt
        if self.phase == "buy" and self.time >= self.phase_until:
            self.phase = "live"
            self.phase_until = self.time + float(self._r["round_time"])
        elif self.phase == "end" and self.time >= self.phase_until:
            self._start_round()
            return self.events
        for p in self.players.values():
            cmd = commands.get(p.pid, Command())
            if p.alive:
                self._apply_command(p, cmd, dt)
            p.prev_fire = cmd.fire
            p.prev_alt = cmd.alt_fire
            p.prev_ability = cmd.ability
        for p in self.players.values():
            if p.alive:
                self._physics(p, dt)
        self._tick_effects(dt)
        self._tick_spike(dt, commands)
        self._check_round()
        return self.events

    def _check_round(self) -> None:
        if self.phase not in ("live", "planted"):
            return
        att = [p for p in self.players.values() if self.side(p.team) == "attack" and p.alive]
        dfn = [p for p in self.players.values() if self.side(p.team) == "defense" and p.alive]
        has_att = any(self.side(p.team) == "attack" for p in self.players.values())
        has_dfn = any(self.side(p.team) == "defense" for p in self.players.values())
        defense_team = 1 - self.attacking_team
        if self.phase == "live":
            if has_att and not att:
                self._end_round(defense_team, "Attackers eliminated")
            elif has_dfn and not dfn:
                self._end_round(self.attacking_team, "Defenders eliminated")
            elif self.time >= self.phase_until:
                self._end_round(defense_team, "Time ran out")
        elif self.phase == "planted" and has_dfn and not dfn:
            self._end_round(self.attacking_team, "Defenders eliminated")

    # ------------------------------------------------------------------ Commands
    def _apply_command(self, p: PlayerState, cmd: Command, dt: float) -> None:
        if cmd.facing is not None:
            p.facing = cmd.facing % 360.0
        p.cursor_depth = max(0.0, min(cmd.cursor_depth, 120.0))
        p.walking, p.crouching = cmd.walk, cmd.crouch
        for item in cmd.buy:
            self.buy(p, item)
        if cmd.slot in SLOTS and cmd.slot != p.slot and cmd.slot in p.weapons:
            p.slot = cmd.slot
            d = self.weapons.get(p.weapons[cmd.slot].key)
            p.equip_until = self.time + (d.equip if d else 0.5)
            p.reload_until = 0.0
            p.burst_left = 0
        if cmd.reload:
            self._start_reload(p)
        d_now = self._weapon_def(p)
        p.zoomed = bool(cmd.alt_fire and d_now and d_now.alt_get("kind") == "zoom" and p.reload_until <= self.time)
        busy = p.plant_progress > 0 or p.defuse_progress > 0
        # movement
        speed = self._max_speed(p)
        wish = Vec(cmd.move_x, cmd.move_y)
        if wish.length() > 1:
            wish = wish.normalized()
        if busy:
            wish = Vec(0, 0)
        world_wish = wish.rotated(p.facing) * speed  # forward = facing
        if self.time < p.dash_until:
            p.vel = p.dash_vel
        else:
            diff = world_wish - p.vel
            rate = self._mv["accel"] if wish.length() > 0 else self._mv["decel"]
            step = rate * dt
            p.vel = world_wish if diff.length() <= step else p.vel + diff.normalized() * step
        if cmd.jump and p.z <= 0.001 and p.vz == 0:
            p.vz = float(self._mv["jump_velocity"])
        # ability (only on a new key press)
        if cmd.ability and cmd.ability != p.prev_ability and self.phase in ("buy", "live", "planted"):
            self._use_ability(p, cmd.ability)
        # shooting
        if self.time >= p.reload_until > 0:
            self._finish_reload(p)
        if self.phase in ("live", "planted") and not busy:
            self._handle_fire(p, cmd)
        self._pickup(p, cmd)
        recovery = self._weapon_def(p).spray_recovery if self._weapon_def(p) else 5.0
        if not cmd.fire:
            p.spray = max(0.0, p.spray - recovery * dt)
            p.fire_held = 0.0
        else:
            p.fire_held += dt

    def drops_near(self, p: PlayerState) -> bool:
        return any((d.pos - p.pos).length() <= PICKUP_RANGE for d in self.drops)

    def wall_active(self, w: Wall) -> bool:
        """False for open doors and for spawn barriers outside the buy phase."""
        if w.buy_phase_only and self.phase != "buy":
            return False
        return not (w.door and w.rect in self.open_doors)

    def active_sight_walls(self, level: int) -> list[Wall]:
        return [w for w in self.world.sight_walls(level) if self.wall_active(w)]

    def _toggle_door(self, p: PlayerState) -> bool:
        """F press: open or close the nearest door within reach. True if a door moved."""
        best, best_d = None, DOOR_RANGE
        for w in self.world.walls:
            if not w.door:
                continue
            c = w.rect.center
            dx = max(w.rect.x0 - p.pos.x, 0.0, p.pos.x - w.rect.x1)
            dy = max(w.rect.y0 - p.pos.y, 0.0, p.pos.y - w.rect.y1)
            d = (dx * dx + dy * dy) ** 0.5
            if d < best_d:
                best, best_d = w, d
        if best is None:
            return False
        if best.rect in self.open_doors:
            self.open_doors.discard(best.rect)
        else:
            self.open_doors.add(best.rect)
        c = best.rect.center
        self.events.append(GameEvent("door", self.time, {"pos": (c.x, c.y), "open": best.rect in self.open_doors}))
        self.events.append(GameEvent("sound", self.time, {"pid": p.pid, "pos": (c.x, c.y), "radius": 15.0, "kind": "step"}))
        return True

    def _pickup(self, p: PlayerState, cmd: Command) -> None:
        """Empty slot: pick up automatically. F (when not planting or defusing): swap."""
        pressed = cmd.interact and not p.prev_interact
        p.prev_interact = cmd.interact
        busy_with_bomb = self.spike_carrier == p.pid and self.world.site_at(p.pos) is not None
        if pressed and not busy_with_bomb and not self.drops_near(p) and self._toggle_door(p):
            return
        for drop in list(self.drops):
            if (drop.pos - p.pos).length() > PICKUP_RANGE:
                continue
            d = self.weapons.get(drop.key)
            if not d:
                continue
            spike_job = self.spike_carrier == p.pid or (self.phase == "planted" and self.side(p.team) == "defense" and self.spike_pos is not None and (p.pos - self.spike_pos).length() <= INTERACT_RANGE)
            if d.slot not in p.weapons or (pressed and not spike_job):
                old = p.weapons.get(d.slot)
                p.weapons[d.slot] = WeaponState(drop.key, drop.mag, drop.reserve)
                self.drops.remove(drop)
                if old:
                    self.drops.append(Drop(old.key, old.mag, old.reserve, p.pos))
                p.slot = d.slot
                p.equip_until = self.time + d.equip
                self.events.append(GameEvent("pickup", self.time, {"pid": p.pid, "weapon": drop.key}))
                return

    def _max_speed(self, p: PlayerState) -> float:
        d = self._weapon_def(p)
        s = float(self._mv["run_speed"]) * (d.speed_mod if d else 1.0)
        if p.zoomed and d:
            s *= float(d.alt_get("speed_mult", 1.0))
        if p.crouching:
            s *= float(self._mv["crouch_mod"])
        elif p.walking:
            s *= float(self._mv["walk_mod"])
        if p.z > 0.001:
            s *= float(self._mv["air_mod"])
        return s * abilities.speed_factor(self, p)

    def _physics(self, p: PlayerState, dt: float) -> None:
        radius = float(self._mv["radius"])
        lh = float(self._mv["level_height"])
        zone = self.world.spawn_zones.get(0 if self.side(p.team) == "attack" else 1) if self.phase == "buy" else None
        # vertical
        p.vz -= float(self._mv["gravity"]) * dt
        p.z = max(0.0, p.z + p.vz * dt)
        if p.z <= 0.0:
            p.vz = 0.0
        # horizontal, colliding with everything higher than the current height
        height_level = p.level + int(p.z / lh + 0.5)
        new = p.pos + p.vel * dt
        for _ in range(3):
            for w in self.world.walls:
                if w.height <= height_level or not self.wall_active(w):
                    continue
                push = w.rect.circle_push(new, radius)
                if push:
                    new = new + push
        if zone:
            new = Vec(min(max(new.x, zone.x0 + radius), zone.x1 - radius), min(max(new.y, zone.y0 + radius), zone.y1 - radius))
        if dt > 0:
            speed = (new - p.pos).length() / dt
            if speed > float(self._mv["run_speed"]) * 0.7 and p.z <= 0 and int(self.time * 3) != int((self.time - dt) * 3):
                self.events.append(GameEvent("sound", self.time, {"pid": p.pid, "pos": (new.x, new.y), "radius": self._sound["run_radius"], "kind": "step"}))
            if self.time >= p.dash_until:
                p.vel = (new - p.pos) * (1.0 / dt)
        p.pos = new
        # levels: ramp lifts to level 1, landing on crate/platform, falling down
        floor = self.world.floor_level(p.pos)
        if self.world.on_ramp(p.pos):
            p.level = max(1, floor)
        elif floor > p.level and p.z >= lh * 0.5 * (floor - p.level):
            p.z, p.vz, p.level = 0.0, 0.0, floor
        elif floor < p.level:
            p.z += lh * (p.level - floor)
            p.level = floor

    # ------------------------------------------------------------------ Weapons
    def _weapon_def(self, p: PlayerState) -> WeaponDef | None:
        ws = p.weapon
        return self.weapons.get(ws.key) if ws else None

    def _start_reload(self, p: PlayerState) -> None:
        ws, d = p.weapon, self._weapon_def(p)
        if not ws or not d or not d.is_gun or ws.mag >= d.mag or ws.reserve <= 0 or p.reload_until > self.time:
            return
        p.reload_until = self.time + d.reload * (abilities.rule(self, "stim_reload") if abilities.has(self, p, "stim") else 1.0)
        p.burst_left = 0

    def _finish_reload(self, p: PlayerState) -> None:
        ws, d = p.weapon, self._weapon_def(p)
        p.reload_until = 0.0
        if not ws or not d:
            return
        need = d.mag - ws.mag
        take = min(need, ws.reserve)
        ws.mag += take
        ws.reserve -= take

    def _handle_fire(self, p: PlayerState, cmd: Command) -> None:
        d, ws = self._weapon_def(p), p.weapon
        if not d or not ws:
            return
        if self.time < p.equip_until or self.time < p.reload_until or self.time < p.next_shot:
            return
        alt_kind = d.alt_get("kind")
        alt_trigger = (alt_kind == "spin" and cmd.alt_fire) or \
            (alt_kind in ("burst", "spread_shot") and cmd.alt_fire and not p.prev_alt)
        wants = (cmd.fire and (d.auto or not p.prev_fire)) or alt_trigger
        if p.burst_left > 0:
            wants = True
        if not wants:
            return
        if d.is_gun and ws.mag <= 0:
            self._start_reload(p)
            p.burst_left = 0
            return
        rate = d.rate
        if d.rate_ramp:
            top, ramp_time = d.rate_ramp
            rate += (top - d.rate) * min(1.0, p.fire_held / max(ramp_time, 1e-6))
        rate *= self._ult_ability(p, "rate_mult") if self.time < p.overdrive_until else 1.0
        if abilities.has(self, p, "stim"):
            rate *= abilities.rule(self, "stim_rate")
        if alt_trigger and alt_kind == "spin" and d.rate_ramp:
            rate = d.rate_ramp[0] * (rate / max(d.rate, 1e-6))
        if p.burst_left > 0 or d.burst or (alt_trigger and alt_kind == "burst"):
            if p.burst_left == 0:
                if d.burst:
                    p.burst_left, p.burst_gap, p.burst_cool, p.burst_spread = d.pellets, 0.075, 1.0 / rate, 1.0
                else:
                    p.burst_left = int(d.alt_get("count", 3))
                    p.burst_gap = float(d.alt_get("interval", 0.06))
                    p.burst_cool = float(d.alt_get("cooldown", 0.4))
                    p.burst_spread = float(d.alt_get("spread_mult", 1.0))
            p.burst_left -= 1
            p.next_shot = self.time + (p.burst_gap if p.burst_left > 0 else p.burst_cool)
            self._fire_bullet(p, d, 1, spread_mult=p.burst_spread)
        elif alt_trigger and alt_kind == "spread_shot":
            p.next_shot = self.time + float(d.alt_get("cooldown", 0.5))
            self._fire_bullet(p, d, int(d.alt_get("pellets", 3)), extra_spread=float(d.alt_get("spread", 3.0)))
        else:
            p.next_shot = self.time + 1.0 / rate
            extra = float(d.alt_get("spread_add", 0.0)) if alt_trigger and alt_kind == "spin" else 0.0
            self._fire_bullet(p, d, d.pellets, extra_spread=extra)
        if d.is_gun:
            ws.mag -= 1

    def _ult_ability(self, p: PlayerState, key: str) -> float:
        return float(self.agents[p.agent]["abilities"].get("X", {}).get(key, 1.0))

    def current_spread(self, p: PlayerState, d: WeaponDef) -> float:
        """Spread in degrees for the next shot. 0 = exact (standing, first shot)."""
        speed = p.vel.length()
        run = float(self._mv["run_speed"])
        moving = 0.0 if self.time < p.overdrive_until else d.spread_run * min(1.0, speed / run)
        if speed <= run * float(self._mv["walk_mod"]) * 0.35:
            moving = 0.0
        air = d.spread_run * 1.5 if p.z > 0.001 else 0.0
        base = moving + air
        if p.spray > 0:
            base += d.spread_first + p.spray
        if p.crouching:
            base *= 0.8
        if p.zoomed:
            base *= float(d.alt_get("spread_mult", 1.0))
        if abilities.has(self, p, "concuss"):
            base += abilities.rule(self, "concuss_spread")
        return base

    def _fire_bullet(self, p: PlayerState, d: WeaponDef, pellets: int, spread_mult: float = 1.0,
                     extra_spread: float = 0.0) -> None:
        aim = heading(p.facing)
        spread = self.current_spread(p, d) * spread_mult + extra_spread
        loud = self._sound["silenced_radius"] if d.silenced else self._sound["shot_radius"]
        if d.is_gun:
            self.events.append(GameEvent("sound", self.time, {"pid": p.pid, "pos": (p.pos.x, p.pos.y), "radius": loud, "kind": "shot"}))
        for _ in range(pellets):
            dev = spread if pellets == 1 else max(spread, d.spread_first if not extra_spread else extra_spread)
            angle = self.rng.uniform(-dev, dev) if dev > 0 else 0.0
            self._trace(p, d, heading(p.facing + angle), aim)
        p.spray = min(d.spray_max, p.spray + d.spray_step)

    def _trace(self, p: PlayerState, d: WeaponDef, direction: Vec, aim: Vec) -> None:
        origin = p.pos
        hits: list[tuple[float, str, Any]] = []
        for w in self.world.walls:
            if w.height <= p.level or not self.wall_active(w):
                continue
            iv = w.rect.ray_interval(origin, direction)
            if iv and iv[0] <= d.range:
                hits.append((iv[0], "wall", (w, iv[1] - iv[0])))
        cursor_point = origin + aim * p.cursor_depth
        cursor_level = self.world.floor_level(cursor_point)
        for t in self.players.values():
            if t.pid == p.pid or not t.alive:
                continue
            res = resolve_zone(origin, direction, aim, p.cursor_depth, t.pos, t.level == p.level,
                               cursor_level == t.level, self.cfg.hit_zones)
            if res.zone and res.along <= d.range:
                hits.append((res.along, "player", (t, res.zone)))
        hits.sort(key=lambda h: h[0])
        mult = 1.0
        end = d.range
        for dist, kind, payload in hits:
            if kind == "wall":
                wall, thickness = payload
                if wall.penetration >= 3 or wall.penetration > d.penetration or thickness > 1.0 + d.penetration:
                    end = dist
                    break
                mult *= PEN_DAMAGE.get(wall.penetration, 0.5)
                continue
            target, zone = payload
            dmg = int(round(d.damage_at(dist, zone) * mult))
            self._damage(p, target, dmg, zone, d.key)
            end = dist
            break
        tip = origin + direction * end
        self.events.append(GameEvent("shot", self.time, {"pid": p.pid, "from": (origin.x, origin.y), "to": (tip.x, tip.y), "weapon": d.key}))

    def _damage(self, attacker: PlayerState | None, target: PlayerState, dmg: int, zone: str, source: str) -> None:
        if not target.alive or dmg <= 0:
            return
        if abilities.has(self, target, "vulnerable"):
            dmg = int(round(dmg * abilities.rule(self, "vulnerable_mult")))
        absorbed = min(target.armor, int(round(dmg * self._absorb)))
        target.armor -= absorbed
        target.hp -= dmg - absorbed
        self.events.append(GameEvent("hit", self.time, {"by": attacker.pid if attacker else None, "pid": target.pid, "dmg": dmg, "zone": zone}))
        if target.hp <= 0:
            self._kill(attacker, target, source, zone)

    def _kill(self, attacker: PlayerState | None, target: PlayerState, source: str, zone: str) -> None:
        target.alive = False
        target.hp = 0
        target.deaths += 1
        target.ult_points += int(self._ult["per_death"])
        target.plant_progress = target.defuse_progress = 0.0
        if self.spike_carrier == target.pid:
            self.spike_carrier = None
            self.spike_pos = target.pos
        for slot in ("primary", "sidearm"):
            ws = target.weapons.get(slot)
            if ws and (slot == "primary" or ws.key != "spatz"):
                self.drops.append(Drop(ws.key, ws.mag, ws.reserve, target.pos))
                break
        if attacker and attacker.team != target.team:
            attacker.kills += 1
            attacker.credits = min(int(self._eco["max"]), attacker.credits + int(self._eco["kill"]))
            attacker.ult_points += int(self._ult["per_kill"])
            ab = self.agents[attacker.agent]["abilities"].get("E", {})
            if "kills_to_recharge" in ab:
                attacker.sig_kills += 1
                if attacker.sig_kills >= int(ab["kills_to_recharge"]):
                    attacker.sig_kills = 0
                    attacker.charges["E"] = min(int(ab["max"]), attacker.charges.get("E", 0) + 1)
        self.events.append(GameEvent("kill", self.time, {"by": attacker.pid if attacker else None, "pid": target.pid, "weapon": source, "head": zone == "head"}))

    # ------------------------------------------------------------------ Abilities
    def _use_ability(self, p: PlayerState, key: str) -> None:
        ab = self.agents[p.agent]["abilities"].get(key)
        if not ab or abilities.has(self, p, "suppress"):
            return
        if key == "X":
            if p.ult_points < int(ab["cost"]):
                return
        elif p.charges.get(key, 0) <= 0:
            return
        try:
            target = abilities.use(self, p, key, ab)
        except (KeyError, TypeError, ValueError) as exc:
            warnings.warn(f"Ability {ab.get('name', key)} of {p.agent} misconfigured: {exc}")
            return
        if target is None:
            return
        if key == "X":
            p.ult_points -= int(ab["cost"])
        else:
            p.charges[key] -= 1
        self.events.append(GameEvent("ability", self.time, {"pid": p.pid, "key": key, "kind": ab["kind"], "pos": (target.x, target.y)}))

    def _clip_to_walls(self, a: Vec, b: Vec, level: int) -> Vec:
        direction = (b - a).normalized()
        dist = (b - a).length()
        best = dist
        for w in self.active_sight_walls(level):
            iv = w.rect.ray_interval(a, direction)
            if iv and iv[0] < best:
                best = iv[0]
        return a + direction * max(0.0, best - 0.3)

    def _tick_effects(self, dt: float) -> None:
        abilities.tick(self, dt)

    # ------------------------------------------------------------------ Sight
    def _line_clear(self, a: Vec, b: Vec, level: int, ignore_effects: bool = False) -> bool:
        direction = b - a
        dist = direction.length()
        if dist < 1e-6:
            return True
        u = direction * (1.0 / dist)
        for w in self.active_sight_walls(level):
            iv = w.rect.ray_interval(a, u)
            if iv and iv[0] < dist:
                return False
        if ignore_effects:
            return True
        for e in self.effects:
            if e.kind == "smoke" and segment_circle_hit(a, b, e.pos, e.radius):
                if (a - e.pos).length() > e.radius and (b - e.pos).length() > e.radius:
                    return False
                return (a - e.pos).length() <= e.radius and (b - e.pos).length() <= e.radius
            if e.kind == "wall" and e.a and e.b:
                from gameplay.geometry import segments_intersect
                if segments_intersect(a, b, e.a, e.b):
                    return False
        return True

    def can_see(self, viewer: PlayerState, target: PlayerState) -> bool:
        if not target.alive:
            return False
        if viewer.pid == target.pid or viewer.team == target.team:
            return True
        if target.revealed_until > self.time:
            return True
        if viewer.blind_until > self.time or not viewer.alive:
            return False
        if abilities.has(self, viewer, "nearsight") and (target.pos - viewer.pos).length() > abilities.rule(self, "nearsight_range"):
            return False
        if not self.cfg.lobby.all_around_sight:
            to = angle_of(target.pos - viewer.pos)
            if abs(angle_diff(viewer.facing, to)) > self.fov / 2:
                return False
        return self._line_clear(viewer.pos, target.pos, min(viewer.level, target.level))

    # ------------------------------------------------------------------ Bomb
    def _tick_spike(self, dt: float, commands: dict[int, Command]) -> None:
        if self.phase in ("live",) and self.spike_carrier is None and self.spike_pos is not None:
            for p in self.players.values():
                if p.alive and self.side(p.team) == "attack" and (p.pos - self.spike_pos).length() <= PICKUP_RANGE:
                    self.spike_carrier = p.pid
                    self.spike_pos = None
                    break
        if self.phase == "live" and self.spike_carrier is not None:
            p = self.players[self.spike_carrier]
            cmd = commands.get(p.pid, Command())
            site = self.world.site_at(p.pos)
            if p.alive and cmd.interact and site and p.z <= 0.001:
                p.plant_progress += dt
                if p.plant_progress >= float(self._spike["plant_time"]):
                    self._plant(p, site.name)
            else:
                p.plant_progress = 0.0
        if self.phase == "planted" and self.spike_pos is not None:
            for p in self.players.values():
                if not p.alive or self.side(p.team) != "defense":
                    continue
                cmd = commands.get(p.pid, Command())
                if cmd.interact and (p.pos - self.spike_pos).length() <= INTERACT_RANGE and p.z <= 0.001:
                    p.defuse_progress += dt
                    if p.defuse_progress >= float(self._spike["defuse_time"]):
                        p.ult_points += int(self._ult["per_defuse"])
                        self.events.append(GameEvent("defuse", self.time, {"pid": p.pid}))
                        self._end_round(p.team, "Bomb defused")
                        return
                else:
                    cp = float(self._spike["defuse_checkpoint"])
                    p.defuse_progress = cp if p.defuse_progress >= cp else 0.0
            if self.time >= self.spike_planted_at + float(self._spike["fuse_time"]):
                for t in self.players.values():
                    if t.alive and (t.pos - self.spike_pos).length() <= float(self._spike["blast_radius"]):
                        self._kill(None, t, "spike", "body")
                self.events.append(GameEvent("explode", self.time, {"pos": (self.spike_pos.x, self.spike_pos.y)}))
                self._end_round(self.attacking_team, "Bomb detonated")

    def _plant(self, p: PlayerState, site: str) -> None:
        self.phase = "planted"
        self.spike_pos = p.pos
        self.spike_site = site
        self.spike_carrier = None
        self.spike_planted_at = self.time
        p.plant_progress = 0.0
        p.ult_points += int(self._ult["per_plant"])
        for t in self.players.values():
            if t.team == p.team:
                t.credits = min(int(self._eco["max"]), t.credits + int(self._eco["plant"]))
        self.events.append(GameEvent("plant", self.time, {"pid": p.pid, "site": site}))

    # ------------------------------------------------------------------ Snapshot
    def _effect_visible(self, e: Effect, viewer: PlayerState | None) -> bool:
        """Flashes and decoys are never drawn; enemy traps only for their own team."""
        if e.kind in ("flash", "decoy"):
            return False
        if e.kind in ("tripwire", "alarm") and viewer is not None and viewer.team != e.team:
            return False
        return True

    def spike_time_left(self) -> float:
        if self.phase != "planted":
            return 0.0
        return max(0.0, self.spike_planted_at + float(self._spike["fuse_time"]) - self.time)

    def phase_time_left(self) -> float:
        if self.phase == "planted":
            return self.spike_time_left()
        return max(0.0, self.phase_until - self.time)

    def snapshot(self, viewer_pid: int | None = None) -> dict[str, Any]:
        """JSON-ready snapshot. With viewer_pid, enemies the viewer cannot see are left out."""
        viewer = self.players.get(viewer_pid) if viewer_pid else None
        players = []
        for p in self.players.values():
            visible = viewer is None or self.can_see(viewer, p) or not p.alive
            if not visible:
                continue
            players.append({
                "pid": p.pid, "name": p.name, "team": p.team, "agent": p.agent, "bot": p.is_bot,
                "x": p.pos.x, "y": p.pos.y, "z": p.z, "level": p.level, "facing": p.facing,
                "alive": p.alive, "hp": p.hp, "armor": p.armor,
                "credits": p.credits if viewer is None or viewer.team == p.team else None,
                "slot": p.slot, "weapon": p.weapon.key if p.weapon else None,
                "mag": p.weapon.mag if p.weapon else 0, "reserve": p.weapon.reserve if p.weapon else 0,
                "charges": dict(p.charges), "ult": p.ult_points, "kills": p.kills, "deaths": p.deaths,
                "blind": p.blind_until > self.time, "reloading": p.reload_until > self.time,
                "plant": p.plant_progress, "defuse": p.defuse_progress,
                "status": sorted(k for k, v in p.status.items() if v > self.time)
                if viewer is None or viewer.team == p.team else [],
                "vx": p.vel.x, "vy": p.vel.y, "spray": p.spray,
            })
        return {
            "time": self.time, "phase": self.phase, "phase_left": self.phase_time_left(), "round": self.round_no,
            "score": list(self.score), "attacking_team": self.attacking_team, "winner": self.match_winner,
            "round_winner": self.round_winner, "round_reason": self.round_reason,
            "spike": {"carrier": self.spike_carrier, "pos": (self.spike_pos.x, self.spike_pos.y) if self.spike_pos else None, "site": self.spike_site},
            "effects": [{"kind": e.kind, "team": e.team, "x": e.pos.x, "y": e.pos.y, "r": e.radius,
                         "a": (e.a.x, e.a.y) if e.a else None, "b": (e.b.x, e.b.y) if e.b else None,
                         "start": e.start, "until": e.until, "status": e.props.get("status")}
                        for e in self.effects if self._effect_visible(e, viewer)],
            "players": players,
            "roster": [{"pid": p.pid, "name": p.name, "team": p.team, "agent": p.agent, "kills": p.kills,
                        "deaths": p.deaths, "alive": p.alive} for p in self.players.values()],
            "drops": [{"key": d.key, "x": d.pos.x, "y": d.pos.y} for d in self.drops],
            "doors_open": [[r.x0, r.y0, r.x1, r.y1] for r in self.open_doors],
        }
