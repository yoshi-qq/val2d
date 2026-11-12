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
from gameplay.world import PLATFORM, Wall, WorldMap

SLOTS = ("primary", "sidearm", "melee")
FULL_WALL = 2  # walls this many levels high are never climbed or jumped over
PEN_DAMAGE = {0: 0.8, 1: 0.6, 2: 0.45}  # damage factor after passing through a material (own value)
INTERACT_RANGE = 1.5
DOOR_RANGE = 1.6
PICKUP_RANGE = 1.2


AGENTS_DIR = ROOT / "config" / "content" / "agents"


@lru_cache(maxsize=1)
def load_agents() -> dict[str, dict[str, Any]]:
    """Agents from config/content/agents/*.py (one file per agent, key = file name; files starting with _ are skipped).
    Broken agents and abilities are skipped with a warning naming the problem."""
    from gameplay.kit import check_ability
    from gameplay.patches import apply_agent, section
    found: list[tuple[int, str, dict[str, Any]]] = []
    known = {p.stem for p in AGENTS_DIR.glob("*.py")} if AGENTS_DIR.is_dir() else set()
    for fname, changes in section("agents"):
        for key in set(changes) - known:
            warnings.warn(f"Patch {fname}: no agent {key!r}; change ignored")
    for path in sorted(AGENTS_DIR.glob("*.py")) if AGENTS_DIR.is_dir() else []:
        if path.name.startswith("_"):
            continue
        agent = _load_py(path, "AGENT")
        if not isinstance(agent, dict):
            warnings.warn(f"Agent file {path.name} has no AGENT dict; skipped.")
            continue
        agent = apply_agent(path.stem, agent)  # balance patches (config/patches)
        try:
            abil = {slot: dict(agent["abilities"][slot]) for slot in ("C", "Q", "E", "X")}
        except (KeyError, TypeError) as exc:
            warnings.warn(f"Agent {path.stem} skipped: {exc}")
            continue
        problems = [msg for ab in abil.values() for msg in check_ability(ab)]
        if problems:
            warnings.warn(f"Agent {path.stem} skipped: " + "; ".join(problems))
            continue
        found.append((int(agent.get("order", 999)), path.stem, {
            "name": str(agent.get("name", path.stem.title())), "role": str(agent.get("role", "")), "abilities": abil,
            "sprites": dict(agent.get("sprites", {})), "passives": list(agent.get("passives", []))}))
    return {key: data for _, key, data in sorted(found, key=lambda f: (f[0], f[1]))}


def spray_offset(d: WeaponDef, index: int) -> float:
    """Deterministic part of the spray in degrees for bullet `index` of a spray (0 = first bullet).

    The first bullets stay on target, then the aim drifts to one side (side and sway
    taste per weapon from its key), with a slow sway back and forth; capped at the weapon's spray_max.
    Counter it by moving the mouse against the drift. Semi-automatic weapons and shotguns have none.
    """
    if not d.auto or d.pellets > 1 or index < 2:
        return 0.0
    seed = sum(ord(c) for c in d.key)
    side = 1.0 if seed % 2 else -1.0
    sway_speed = 0.45 + (seed % 5) * 0.08
    climb = min(d.spray_max * 0.8, (index - 1) * d.spray_step * 0.9)
    sway = math.sin((index - 2) * sway_speed) * min(d.spray_max * 0.45, (index - 1) * d.spray_step * 0.5)
    return max(-d.spray_max, min(d.spray_max, side * climb + sway))


@dataclass
class Command:
    move_x: float = 0.0          # sideways, -1 left â€¦ 1 right (relative to facing)
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
    ability_alt: bool = False    # cast with the alternate (right click) variant
    points: list = field(default_factory=list)  # multi-placement: chosen map points (x, y) for the ability
    interact: bool = False       # plant or defuse the bomb (hold)
    drop: bool = False           # G: drop the bomb if carried, else the weapon in hand
    buy: list[str] = field(default_factory=list)  # item keys, or "gift:<pid>:<weapon>" to buy for a teammate
    request: str | None = None   # weapon key this player asks the team for ("" clears)


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
    z: float = 0.0          # height above the ground under the player (jumping, falling)
    vz: float = 0.0
    level: int = 0          # rounded ground height, used for sight and hit rules
    ground: float = 0.0     # ground height under the player in metres (continuous on ramps)
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
    shot_index: int = 0     # bullets in the current spray (0 = first shot after a pause)
    dropped_at: float = -99.0
    burst_left: int = 0
    prev_fire: bool = False
    prev_alt: bool = False
    zoomed: bool = False
    zoom_level: int = 0     # 0 = not aiming; 1.. = zoom factor index of the weapon
    defusing: bool = False
    assists: int = 0
    round_kills: int = 0
    tagged_until: float = 0.0
    tag_slow: float = 0.0
    purchases: list = field(default_factory=list)  # this round: dicts with item, price, slot, weapon, previous, armor
    orb_progress: float = 0.0
    remote_sellable: list = field(default_factory=list)  # client copy: own items that can be sold
    burst_gap: float = 0.075
    burst_cool: float = 0.0
    burst_spread: float = 1.0
    charges: dict[str, int] = field(default_factory=dict)
    sig_timer: float = 0.0
    sig_kills: int = 0
    passive_state: dict[str, Any] = field(default_factory=dict)
    status_drain: float = 0.0
    ult_points: int = 0
    kills: int = 0
    damage_total: int = 0
    headshots: int = 0
    first_kills: int = 0
    plants: int = 0
    defuses: int = 0
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
    ping_ms: int | None = None  # round trip to the host; None for bots and the host itself
    dummy: bool = False  # practice-range target: does nothing, respawns after death
    remote_score: int = 0  # client copy of the host's combat score
    request: str = ""  # weapon asked for this round
    home: Vec = Vec(0, 0)
    died_at: float = -99.0

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
        self.statuses = abilities.load_statuses()
        self.rng = random.Random(seed)
        self.players: dict[int, PlayerState] = {}
        self.effects: list[Effect] = []
        self.drops: list[Drop] = []
        self.events: list[GameEvent] = []
        self.open_doors: set[Rect] = set()
        self.round_damage: dict[tuple[int, int], list[int]] = {}  # (attacker, target) -> [damage, hits] this round
        self.history: list[tuple[int, str]] = []  # (winning team, reason) per finished round
        self.remote_report: list[dict[str, int]] = []  # client copy of the viewer's damage report
        self._first_kill_done = False
        self.practice = False  # practice range: endless live phase, free buying, respawning dummies
        self.mode = "standard"
        self.dm_ends_at = 0.0
        self.time = 0.0
        self.phase = "lobby"  # lobby, buy, live, planted, end, over
        self.phase_until = 0.0
        self.round_no = 0
        self.score = [0, 0]
        self.attacking_team = 0
        self.loss_streak = [0, 0]
        self.orbs: list[Vec] = []          # ultimate orbs lying on the map this round
        self.loadout_value = [0, 0]        # team loadout value at the start of the live phase (thrifty)
        self.last_alive_vs: dict[int, int] = {}  # team -> enemies alive when it was down to its last player (clutch)
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
        self._mv = {k: rule("movement", k, d) for k, d in (("run_speed", 6.0), ("walk_mod", 0.55), ("crouch_mod", 0.4), ("air_mod", 0.9), ("accel", 60.0), ("decel", 45.0), ("jump_velocity", 4.2), ("gravity", 14.0), ("radius", 0.4), ("level_height", 1.0), ("step_up", 0.25), ("step_up_air", 0.15), ("step_down", 0.35))}
        self._eco = {k: rule("economy", k, d) for k, d in (("start", 800), ("win", 3000), ("loss", [1800, 2300, 2800]), ("kill", 200), ("plant", 300), ("max", 9000), ("survivor_loss", 1000), ("orb", 0))}
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

    RULE_NAMES = ("all_around_sight", "sound_rings", "win_rounds", "overtime", "play_all_rounds", "allow_cheats",
                  "infinite_ammo", "infinite_abilities", "invincibility", "bullet_tracers")

    def set_rules(self, **rules: Any) -> bool:
        """Changes lobby rules; only while the lobby is open. Unknown names and wrong types are ignored with a warning."""
        from dataclasses import replace
        if self.phase != "lobby":
            return False
        clean: dict[str, Any] = {}
        for name, value in rules.items():
            if name not in self.RULE_NAMES:
                warnings.warn(f"Unknown lobby rule {name}")
            elif name == "win_rounds" and isinstance(value, int) and 1 <= value <= 30:
                clean[name] = value
            elif name != "win_rounds" and isinstance(value, bool):
                clean[name] = value
        if not clean:
            return False
        self.cfg = replace(self.cfg, lobby=replace(self.cfg.lobby, **clean))
        if self.mode == "standard":
            self.win_rounds, self.overtime = self.cfg.lobby.win_rounds, self.cfg.lobby.overtime
        return True

    def cheat(self, name: str) -> bool:
        return self.cfg.lobby.cheat(name)

    def set_mode(self, mode: str) -> None:
        """"standard", "quick" or "deathmatch" (values in config/rules/ "modes"); call before start()."""
        self.mode = mode if mode in ("standard", "quick", "deathmatch") else "standard"
        if self.mode == "quick":
            q = rule("modes", "quick", {})
            self.win_rounds = int(q.get("win_rounds", 4))
            self.overtime = bool(q.get("overtime", False))
            for key in ("half_after", "buy_time", "round_time"):
                if key in q:
                    self._r[key] = q[key]

    def start(self) -> None:
        if self.mode == "deathmatch":
            self._start_deathmatch()
            return
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

    def start_practice(self) -> None:
        """Practice range: one endless live round, plenty of credits, no bomb."""
        self.practice = True
        self.start()
        self.phase, self.phase_until = "live", self.time + 10 ** 7
        self.spike_carrier = None
        for p in self.players.values():
            p.credits = 99_000
            for key in ("C", "Q", "E"):
                ab = self.agents[p.agent]["abilities"].get(key, {})
                p.charges[key] = int(ab.get("max", 1))
            p.ult_points = 99

    def _start_deathmatch(self) -> None:
        """Team deathmatch: one long round, buy anything anywhere, respawn after a delay, first team to the kill limit."""
        dm = rule("modes", "deathmatch", {})
        self.round_no, self.score, self.match_winner, self.attacking_team = 0, [0, 0], None, 0
        self._start_round()
        self.spike_carrier = None
        self.phase, self.phase_until = "live", self.time + 10 ** 7
        self.dm_ends_at = self.time + float(dm.get("time_limit", 360))
        for p in self.players.values():
            p.credits = 99_000

    def _deathmatch_upkeep(self) -> None:
        dm = rule("modes", "deathmatch", {})
        self.score = [sum(p.kills for p in self.players.values() if p.team == t) for t in (0, 1)]
        limit = int(dm.get("kill_limit", 40))
        if max(self.score) >= limit or self.time >= self.dm_ends_at:
            if self.score[0] != self.score[1]:
                self.match_winner = 0 if self.score[0] > self.score[1] else 1
                self.phase = "over"
                self.events.append(GameEvent("round_end", self.time, {"winner": self.match_winner, "reason": "Kill limit"
                                                                      if max(self.score) >= limit else "Time limit",
                                                                      "score": list(self.score)}))
                return
            self.dm_ends_at = self.time + 30  # tied: 30 s sudden death
        delay = float(dm.get("respawn", 3.0))
        for p in self.players.values():
            p.credits = max(p.credits, 99_000)
            if not p.alive and self.time - p.died_at >= delay:
                self._respawn(p, int(dm.get("spawn_shield", 50)))

    def _respawn(self, p: PlayerState, shield: int) -> None:
        """Back to life at the own side's spawn, far from enemies, with the weapons still in the inventory."""
        side_idx = 0 if self.side(p.team) == "attack" else 1
        points = self.world.spawns.get(side_idx) or [self.world.spawn_zones.get(side_idx, Rect(0, 0, 1, 1)).center]
        enemies = [e.pos for e in self.players.values() if e.alive and e.team != p.team]
        best = max(points, key=lambda pt: min(((pt - e).length() for e in enemies), default=99.0))
        p.alive, p.hp, p.armor = True, self._hp, shield
        p.pos, p.vel, p.z, p.vz = best, Vec(0, 0), 0.0, 0.0
        p.ground = self.world.ground_height(best)
        p.level = int(p.ground / float(self._mv["level_height"]) + 0.5)
        p.status, p.blind_until = {}, 0.0
        if "sidearm" not in p.weapons:
            p.weapons["sidearm"] = self._new_weapon("pistol")
        for ws in p.weapons.values():
            wd = self.weapons.get(ws.key)
            if wd:
                ws.mag, ws.reserve = wd.mag, wd.reserve
        p.slot = "primary" if "primary" in p.weapons else "sidearm"
        self.events.append(GameEvent("respawn", self.time, {"pid": p.pid}))

    def _practice_upkeep(self) -> None:
        for p in self.players.values():
            if p.dummy and not p.alive and self.time - p.died_at >= 2.0:
                p.alive, p.hp, p.armor = True, self._hp, 0
                p.pos = p.home
            elif not p.dummy:
                p.credits = max(p.credits, 99_000)
                for key in ("C", "Q", "E"):
                    ab = self.agents[p.agent]["abilities"].get(key, {})
                    if p.charges.get(key, 0) < 1:
                        p.charges[key] = int(ab.get("max", 1))
                p.ult_points = max(p.ult_points, 99)

    def _orb_spots(self) -> list[Vec]:
        """Ultimate orb positions: the map's "orbs", else between the map centre and each site."""
        if self.practice or self.mode == "deathmatch":
            return []
        spots = list(getattr(self.world, "orbs", []) or [])
        if not spots:
            centre = Vec(self.world.width / 2, self.world.height / 2)
            for site in self.world.sites[: int(rule("orbs", "count", 2))]:
                for share in (0.5, 0.4, 0.6, 0.3, 0.7):
                    p = centre + (site.rect.center - centre) * share
                    if self.world.ground_height(p) == 0.0 and not any(w.rect.contains(p) for w in self.world.walls):
                        spots.append(p)
                        break
        return spots

    def _start_round(self) -> None:
        self.round_no += 1
        half = int(self._r["half_after"])
        if self.round_no == half + 1 or (self._in_overtime() and self.round_no > 1):
            self.attacking_team = 1 - self.attacking_team
        pistol = self._is_pistol_round()
        self.effects.clear()
        self.drops.clear()
        self.open_doors.clear()
        self.round_damage = {}
        self.last_alive_vs = {}
        self.orbs = self._orb_spots()
        self._first_kill_done = False
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
                p.weapons["sidearm"] = self._new_weapon("pistol")
            p.weapons["melee"] = self._new_weapon("knife")
            for ws in p.weapons.values():
                d = self.weapons.get(ws.key)
                if d:
                    ws.mag, ws.reserve = d.mag, d.reserve
            p.alive = True
            p.hp = self._hp
            p.vel = Vec(0, 0)
            p.z = p.vz = 0.0
            p.ground = self.world.ground_height(p.pos)
            p.level = int(p.ground / float(self._mv["level_height"]) + 0.5)
            p.slot = "primary" if "primary" in p.weapons else "sidearm"
            p.spray = 0.0
            p.blind_until = p.revealed_until = p.overdrive_until = p.dash_until = p.immune_until = 0.0
            p.status = {}
            p.anchor, p.anchor_until = None, 0.0
            p.heal_left = p.heal_rate = p.hp_frac = p.decay_pool = 0.0
            p.round_kills, p.purchases, p.orb_progress, p.tagged_until = 0, [], 0.0, 0.0
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
            p.request = ""
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
        loser_side = self.side(loser)
        survivors_paid_less = (reason == "Time ran out" and loser_side == "attack") or \
            (reason == "Bomb detonated" and loser_side == "defense")
        for p in self.players.values():
            if p.team == winner_team:
                p.credits += int(self._eco["win"])
            elif survivors_paid_less and p.alive:
                p.credits += int(self._eco["survivor_loss"])  # saved instead of finishing the objective
            else:
                p.credits += int(losses[min(self.loss_streak[loser], len(losses)) - 1])
            p.credits = min(p.credits, int(self._eco["max"]))
        self._round_titles(winner_team)
        self.orbs = []
        self.history.append((winner_team, reason))
        self.events.append(GameEvent("round_end", self.time, {"winner": winner_team, "reason": reason, "score": list(self.score)}))
        if self._match_decided():
            self.match_winner = winner_team
            self.phase = "over"
            return
        self.phase = "end"
        self.phase_until = self.time + float(self._r["end_time"])

    def _round_titles(self, winner: int) -> None:
        """Round callouts like the real game: ace, clutch, flawless, thrifty (events "round_title")."""
        if self.practice or self.mode == "deathmatch":
            return
        enemies = [p for p in self.players.values() if p.team != winner and not p.dummy]
        team = [p for p in self.players.values() if p.team == winner and not p.dummy]
        for p in self.players.values():
            if len([e for e in self.players.values() if e.team != p.team]) >= 3 and p.round_kills >= \
                    len([e for e in self.players.values() if e.team != p.team]):
                self.events.append(GameEvent("round_title", self.time, {"title": "Ace", "pid": p.pid, "team": p.team}))
        if team and all(p.alive for p in team) and len(team) >= 2:
            self.events.append(GameEvent("round_title", self.time, {"title": "Flawless", "team": winner}))
        elif self.last_alive_vs.get(winner, 0) >= 2:
            last = next((p for p in team if p.alive), None)
            self.events.append(GameEvent("round_title", self.time, {"title": "Clutch", "team": winner,
                                                                   "pid": last.pid if last else None}))
        if enemies and self.loadout_value[winner] + 2000 <= self.loadout_value[1 - winner]:
            self.events.append(GameEvent("round_title", self.time, {"title": "Thrifty", "team": winner}))

    def surrender(self, team: int) -> bool:
        """The team gives up: the match ends as a loss for it (like a successful surrender vote)."""
        if self.phase in ("lobby", "over"):
            return False
        self.match_winner = 1 - team
        self.phase = "over"
        self.events.append(GameEvent("round_end", self.time, {"winner": 1 - team, "reason": "Surrendered", "score": list(self.score)}))
        return True

    def _match_decided(self) -> bool:
        a, b = self.score
        need = self.win_rounds
        if self.cfg.lobby.play_all_rounds and self.mode != "deathmatch":
            regulation = 2 * (need - 1)  # e.g. 24 rounds for first to 13
            if a + b < regulation:
                return False
            if a != b:
                return a + b == regulation or abs(a - b) >= int(self._r["overtime_margin"]) or not self.overtime
            return not self.overtime
        if max(a, b) < need:
            return False
        if not self.overtime:
            return True
        if a >= need - 1 and b >= need - 1:
            return abs(a - b) >= int(self._r["overtime_margin"])
        return True

    # ------------------------------------------------------------------ Buying
    def buy(self, p: PlayerState, item: str) -> bool:
        free_buy = self.practice or self.mode == "deathmatch"
        if not p.alive or (self.phase != "buy" and not free_buy):
            return False
        if item.startswith("gift:"):
            return self._gift(p, item)
        zone = self.world.spawn_zones.get(0 if self.side(p.team) == "attack" else 1)
        if zone and not zone.contains(p.pos) and not free_buy:
            return False
        if self.sellable(p, item):
            return self.sell(p, item)
        if item in self.weapons:
            d = self.weapons[item]
            if d.slot == "melee" or p.credits < d.price:
                return False
            p.credits -= d.price
            previous = p.weapons.get(d.slot)
            if previous is not None and not (d.slot == "sidearm" and previous.key == "pistol"):
                self.drops.append(Drop(previous.key, previous.mag, previous.reserve, p.pos))  # the old gun drops
            new = self._new_weapon(item)
            p.weapons[d.slot] = new
            p.purchases.append({"item": item, "price": d.price, "slot": d.slot, "weapon": new, "previous": previous,
                                "drop": self.drops[-1] if previous is not None and self.drops and self.drops[-1].key == previous.key else None})
            p.slot = d.slot
            p.equip_until = self.time + d.equip
        elif item in self.armor:
            a = self.armor[item]
            if p.credits < a.price or p.armor >= a.points:
                return False
            p.credits -= a.price
            p.purchases.append({"item": item, "price": a.price, "armor": p.armor})
            p.armor = a.points
        elif item in ("C", "Q", "E"):
            ab = self.agents[p.agent]["abilities"].get(item)
            if not ab or p.charges.get(item, 0) >= int(ab["max"]) or p.credits < int(ab["price"]) or int(ab["price"]) == 0:
                return False
            p.credits -= int(ab["price"])
            p.charges[item] = p.charges.get(item, 0) + 1
            p.purchases.append({"item": item, "price": int(ab["price"])})
        else:
            warnings.warn(f"Unknown buy request: {item}")
            return False
        self.events.append(GameEvent("buy", self.time, {"pid": p.pid, "item": item}))
        return True

    def sellable(self, p: PlayerState, item: str) -> bool:
        """Bought this buy phase and still held (not dropped, not given away): clicking it again sells it."""
        if self.phase != "buy" and not (self.practice or self.mode == "deathmatch"):
            return False
        for buy in reversed(p.purchases):
            if buy["item"] != item:
                continue
            if "weapon" in buy:
                return p.weapons.get(buy["slot"]) is buy["weapon"]
            if "armor" in buy:
                return p.armor == self.armor[item].points
            return p.charges.get(item, 0) > 0
        return False

    def sell(self, p: PlayerState, item: str) -> bool:
        """Takes back an item bought this buy phase: full refund; a gun that was replaced comes back if still lying there."""
        if not self.sellable(p, item):
            return False
        buy = next(b for b in reversed(p.purchases) if b["item"] == item)
        p.purchases.remove(buy)
        p.credits = min(int(self._eco["max"]), p.credits + int(buy["price"]))
        if "weapon" in buy:
            previous, drop = buy["previous"], buy.get("drop")
            if previous is not None and drop is not None and drop in self.drops:
                self.drops.remove(drop)
                p.weapons[buy["slot"]] = previous
            elif buy["slot"] == "sidearm":
                p.weapons["sidearm"] = self._new_weapon("pistol")
            else:
                p.weapons.pop(buy["slot"], None)
            if p.slot not in p.weapons:
                p.slot = "primary" if "primary" in p.weapons else "sidearm"
        elif "armor" in buy:
            p.armor = int(buy["armor"])
        else:
            p.charges[item] = max(0, p.charges.get(item, 0) - 1)
        self.events.append(GameEvent("sell", self.time, {"pid": p.pid, "item": item}))
        return True

    def _loadout(self, p: PlayerState) -> int:
        """Credits worth of what a player carries (weapons and armor), for the thrifty title."""
        value = sum(self.weapons[ws.key].price for ws in p.weapons.values() if ws.key in self.weapons)
        armor = max((a.price for a in self.armor.values() if a.points <= p.armor), default=0)
        return value + armor

    def _gift(self, buyer: PlayerState, item: str) -> bool:
        """Buy a primary weapon for a teammate; their old one drops at their feet."""
        try:
            _, pid_text, key = item.split(":", 2)
            target = self.players[int(pid_text)]
        except (ValueError, KeyError):
            return False
        d = self.weapons.get(key)
        if d is None or d.slot != "primary" or target.team != buyer.team or not target.alive or buyer.credits < d.price \
                or target.pid == buyer.pid:
            return False
        buyer.credits -= d.price
        old = target.weapons.get("primary")
        if old is not None:
            self.drops.append(Drop(old.key, old.mag, old.reserve, target.pos))
        target.weapons["primary"] = self._new_weapon(key)
        target.slot, target.equip_until = "primary", self.time + d.equip
        if target.request == key:
            target.request = ""
        self.events.append(GameEvent("buy", self.time, {"pid": buyer.pid, "item": key, "for": target.pid}))
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
            self.loadout_value = [sum(self._loadout(p) for p in self.players.values() if p.team == t) for t in (0, 1)]
            for p in self.players.values():
                p.purchases = []  # selling ends with the buy phase
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
        if self.practice:
            self._practice_upkeep()
            return
        if self.mode == "deathmatch":
            if self.phase == "live":
                self._deathmatch_upkeep()
            return
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
        if cmd.request is not None:
            p.request = cmd.request if cmd.request in self.weapons else ""
        if cmd.slot in SLOTS and cmd.slot != p.slot and cmd.slot in p.weapons:
            p.slot = cmd.slot
            d = self.weapons.get(p.weapons[cmd.slot].key)
            p.equip_until = self.time + (d.equip if d else 0.5)
            p.reload_until = 0.0
            p.burst_left = 0
            p.zoom_level = 0
            self.events.append(GameEvent("equip", self.time, {"pid": p.pid, "weapon": p.weapons[cmd.slot].key}))
        if cmd.reload:
            self._start_reload(p)
        if cmd.drop:
            self._drop(p)
        d_now = self._weapon_def(p)
        if d_now is None or p.reload_until > self.time or self.time < p.equip_until:
            p.zoom_level = 0
        else:
            p.zoom_level = d_now.zoom_after(p.zoom_level, cmd.alt_fire, p.prev_alt)
        p.zoomed = p.zoom_level > 0
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
            self.events.append(GameEvent("jump", self.time, {"pid": p.pid, "pos": (p.pos.x, p.pos.y)}))
        # ability (only on a new key press)
        if cmd.ability and cmd.ability != p.prev_ability and self.phase in ("buy", "live", "planted"):
            if cmd.points:
                self._use_multi(p, cmd.ability, cmd.points)
            else:
                self._use_ability(p, cmd.ability, cmd.ability_alt)
        # shooting
        if self.time >= p.reload_until > 0:
            self._finish_reload(p)
        if self.phase in ("live", "planted") and not busy:
            self._handle_fire(p, cmd)
        self._pickup(p, cmd)
        self._orb_pickup(p, cmd, dt)
        recovery = self._weapon_def(p).spray_recovery if self._weapon_def(p) else 5.0
        if not cmd.fire:
            p.spray = max(0.0, p.spray - recovery * dt)
            p.fire_held = 0.0
        else:
            p.fire_held += dt

    def drops_near(self, p: PlayerState) -> bool:
        return any((d.pos - p.pos).length() <= PICKUP_RANGE for d in self.drops)

    def wall_active(self, w: Wall, for_sight: bool = False) -> bool:
        """False for open doors, spawn barriers outside the buy phase, and (unless for sight) bushes."""
        if not w.solid and not for_sight:
            return False
        if w.buy_phase_only and self.phase != "buy":
            return False
        return not (w.door and w.rect in self.open_doors)

    def active_sight_walls(self, level: int) -> list[Wall]:
        return [w for w in self.world.sight_walls(level) if self.wall_active(w, for_sight=True)]

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

    def _drop(self, p: PlayerState) -> None:
        if self.spike_carrier == p.pid and self.phase in ("buy", "live"):
            self.spike_carrier = None
            self.spike_pos = p.pos + heading(p.facing) * 1.0
            p.dropped_at = self.time
            self.events.append(GameEvent("drop", self.time, {"pid": p.pid, "item": "bomb"}))
            return
        ws = p.weapon
        if ws is None or p.slot == "melee":
            return
        self.drops.append(Drop(ws.key, ws.mag, ws.reserve, p.pos + heading(p.facing) * 1.0))
        del p.weapons[p.slot]
        p.slot = "sidearm" if "sidearm" in p.weapons else "melee"
        p.reload_until = 0.0
        p.burst_left = 0
        p.dropped_at = self.time
        self.events.append(GameEvent("drop", self.time, {"pid": p.pid, "item": ws.key}))

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
            if not pressed and self.time - p.dropped_at < 1.0:
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

    def _orb_pickup(self, p: PlayerState, cmd: Command, dt: float) -> None:
        """Hold F next to an ultimate orb: one ultimate point (and the orb credits, if any)."""
        reach = float(rule("orbs", "reach", 1.2))
        orb = next((o for o in self.orbs if (o - p.pos).length() <= reach), None)
        if orb is None or not cmd.interact or p.z > 0.001 or self.phase not in ("live", "planted"):
            p.orb_progress = 0.0
            return
        p.orb_progress += dt
        if p.orb_progress >= float(rule("orbs", "pickup_time", 1.0)):
            self.orbs.remove(orb)
            p.orb_progress = 0.0
            p.ult_points += 1
            p.credits = min(int(self._eco["max"]), p.credits + int(self._eco["orb"]))
            self.events.append(GameEvent("orb", self.time, {"pid": p.pid, "pos": (orb.x, orb.y)}))

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
        if self.time < p.tagged_until:
            s *= 1.0 - p.tag_slow  # tagging: slowed for a moment after being shot
        return s * abilities.speed_factor(self, p)

    def _landing(self, p: PlayerState, speed: float) -> None:
        """Fall damage above a safe landing speed (config/rules/ "fall"); never from ordinary jumps."""
        safe = float(rule("fall", "safe_speed", 7.0))
        if speed <= safe or not p.alive or (self.cheat("invincibility") and not p.is_bot):
            return
        dmg = min(int(rule("fall", "max_damage", 60)), int((speed - safe) * float(rule("fall", "damage_per_speed", 15.0))))
        if dmg > 0:
            p.hp -= dmg  # armour does not absorb falls
            self.events.append(GameEvent("hit", self.time, {"by": None, "pid": p.pid, "dmg": dmg, "zone": "legs"}))
            if p.hp <= 0:
                self._kill(None, p, "fall", "legs")

    def _physics(self, p: PlayerState, dt: float) -> None:
        radius = float(self._mv["radius"])
        lh = float(self._mv["level_height"])
        zone = self.world.spawn_zones.get(0 if self.side(p.team) == "attack" else 1) if self.phase == "buy" else None
        # vertical, relative to the ground under the player
        p.vz -= float(self._mv["gravity"]) * dt
        airborne = p.z > 0.0
        p.z = max(0.0, p.z + p.vz * dt)
        if p.z <= 0.0:
            if airborne:
                self._landing(p, -p.vz)
            p.vz = 0.0
        # horizontal. Walking climbs small steps (step_up); in the air the feet must clear an edge almost fully
        # (step_up_air), so nobody pops up onto cover. Full-height walls are never climbed.
        step_down = float(self._mv["step_down"])
        tolerance = float(self._mv["step_up"]) if p.z <= 0.001 else float(self._mv["step_up_air"])
        feet = p.ground + p.z
        new = p.pos + p.vel * dt
        # ground too high to step onto blocks like a wall (slide along it on the free axis)
        if self.world.ground_height(new) * lh > feet + tolerance:
            for candidate in (Vec(new.x, p.pos.y), Vec(p.pos.x, new.y), p.pos):
                if self.world.ground_height(candidate) * lh <= feet + tolerance:
                    new = candidate
                    break
            else:
                new = p.pos
        for other in self.players.values():  # bodies block each other (on the same height)
            if other.pid == p.pid or not other.alive or other.dummy or abs((other.ground + other.z) - feet) > 1.2:
                continue
            gap = new - other.pos
            dist = gap.length()
            if 1e-6 < dist < 2 * radius:
                new = new + gap.normalized() * (2 * radius - dist) * 0.5
        for _ in range(3):
            for w in self.world.walls:
                if not self.wall_active(w) or (not w.full and w.top * lh <= feet + tolerance):
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
        # follow the ground: walk up and down ramps, fall from ledges from the current height, land on cover
        ground_new = self.world.ground_height(p.pos) * lh
        if p.z <= 0.001:
            if ground_new < p.ground - step_down:
                p.z = p.ground - ground_new  # stepped off a ledge: keep the height, gravity takes over
        else:
            p.z = max(0.0, p.ground + p.z - ground_new)
            if p.z <= 0.0:
                self._landing(p, -p.vz)
                p.vz = 0.0
        p.ground = ground_new
        p.level = int(ground_new / lh + 0.5)

    # ------------------------------------------------------------------ Weapons
    def _weapon_def(self, p: PlayerState) -> WeaponDef | None:
        ws = p.weapon
        return self.weapons.get(ws.key) if ws else None

    def _start_reload(self, p: PlayerState) -> None:
        ws, d = p.weapon, self._weapon_def(p)
        if not ws or not d or not d.is_gun or ws.mag >= d.mag or ws.reserve <= 0 or p.reload_until > self.time:
            return
        p.reload_until = self.time + d.reload * abilities.mult(self, p, "reload")
        p.burst_left = 0
        self.events.append(GameEvent("reload", self.time, {"pid": p.pid, "weapon": d.key, "pos": (p.pos.x, p.pos.y),
                                                            "seconds": p.reload_until - self.time}))

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
        if d.slot == "melee":
            self._handle_melee(p, d, cmd)
            return
        alt_trigger = (alt_kind == "spin" and cmd.alt_fire) or \
            (alt_kind in ("burst", "spread_shot", "tight") and cmd.alt_fire and not p.prev_alt)
        wants = (cmd.fire and (d.auto or not p.prev_fire)) or alt_trigger
        if p.burst_left > 0:
            wants = True
        if not wants:
            return
        if d.is_gun and ws.mag <= 0:
            if not p.prev_fire or cmd.alt_fire and not p.prev_alt:
                self.events.append(GameEvent("empty", self.time, {"pid": p.pid}))
            self._start_reload(p)
            p.burst_left = 0
            return
        rate = d.rate
        if d.rate_ramp:
            top, ramp_time = d.rate_ramp
            rate += (top - d.rate) * min(1.0, p.fire_held / max(ramp_time, 1e-6))
        rate *= self._ult_ability(p, "rate_mult") if self.time < p.overdrive_until else 1.0
        rate *= abilities.mult(self, p, "fire_rate")
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
        elif alt_trigger and alt_kind == "tight":
            p.next_shot = self.time + float(d.alt_get("cooldown", 1.0))
            self._fire_bullet(p, d, d.pellets, spread_mult=float(d.alt_get("spread_mult", 0.4)))
        elif alt_trigger and alt_kind == "spread_shot":
            p.next_shot = self.time + float(d.alt_get("cooldown", 0.5))
            self._fire_bullet(p, d, int(d.alt_get("pellets", 3)), extra_spread=float(d.alt_get("spread", 3.0)))
        else:
            p.next_shot = self.time + 1.0 / rate
            extra = float(d.alt_get("spread_add", 0.0)) if alt_trigger and alt_kind == "spin" else 0.0
            self._fire_bullet(p, d, d.pellets, extra_spread=extra)
        if d.is_gun and not self.cheat("infinite_ammo"):
            ws.mag -= 1
        if d.alt_get("unscope_after_shot"):
            p.zoom_level, p.zoomed = 0, False

    def _handle_melee(self, p: PlayerState, d: WeaponDef, cmd: Command) -> None:
        """Knife: left click a quick stab (hold for more), right click a slower heavy stab. No headshots;
        hits from behind deal `backstab` times the damage."""
        heavy = d.alt_get("kind") == "heavy" and cmd.alt_fire and not p.prev_alt
        if not heavy and not cmd.fire:
            return
        damage = float(d.alt_get("damage", 75)) if heavy else float(d.damage_at(0.0, "body"))
        reach = float(d.alt_get("range", d.range)) if heavy else d.range
        p.next_shot = self.time + (float(d.alt_get("cooldown", 1.0)) if heavy else 1.0 / d.rate)
        aim = heading(p.facing)
        best, best_d = None, reach + 0.4
        for t in self.players.values():
            if t.pid == p.pid or not t.alive or t.level != p.level:
                continue
            rel = t.pos - p.pos
            dist = rel.length()
            if dist > reach + 0.4 or dist < 1e-6:
                continue
            if abs(angle_diff(p.facing, angle_of(rel))) > 40 or not self._line_clear(p.pos, t.pos, p.level, ignore_effects=True):
                continue
            if dist < best_d:
                best, best_d = t, dist
        end = p.pos + aim * reach
        self.events.append(GameEvent("sound", self.time, {"pid": p.pid, "pos": (p.pos.x, p.pos.y), "radius": 8.0, "kind": "knife",
                                                          "heavy": heavy}))
        if best is not None:
            behind = abs(angle_diff(best.facing, angle_of(p.pos - best.pos))) > 110
            dmg = int(round(damage * (d.backstab if behind else 1.0)))
            self._damage(p, best, dmg, "body", d.key)
            end = best.pos
        self.events.append(GameEvent("shot", self.time, {"pid": p.pid, "from": (p.pos.x, p.pos.y), "to": (end.x, end.y),
                                                          "weapon": d.key, "stop": "player" if best else "", "melee": True,
                                                          "heavy": heavy}))

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
        elif d.spread_unscoped:
            base += d.spread_unscoped
        base += abilities.add(self, p, "spread_add")
        return base

    def _fire_bullet(self, p: PlayerState, d: WeaponDef, pellets: int, spread_mult: float = 1.0,
                     extra_spread: float = 0.0) -> None:
        aim = heading(p.facing)
        spread = self.current_spread(p, d) * spread_mult + extra_spread
        loud = self._sound["silenced_radius"] if d.silenced else self._sound["shot_radius"]
        if d.is_gun:
            self.events.append(GameEvent("sound", self.time, {"pid": p.pid, "pos": (p.pos.x, p.pos.y), "radius": loud, "kind": "shot",
                                                              "weapon": d.key}))
        if p.spray <= 0.0:
            p.shot_index = 0
        pattern = spray_offset(d, p.shot_index) * spread_mult if pellets == 1 else 0.0
        for _ in range(pellets):
            dev = spread if pellets == 1 else max(spread, d.spread_first if not extra_spread else extra_spread)
            jitter = 0.35 if pattern else 1.0  # with a pattern, randomness only blurs it
            angle = pattern + (self.rng.uniform(-dev, dev) * jitter if dev > 0 else 0.0)
            self._trace(p, d, heading(p.facing + angle), aim)
        p.spray = min(d.spray_max, p.spray + d.spray_step)
        p.shot_index += 1

    def _trace(self, p: PlayerState, d: WeaponDef, direction: Vec, aim: Vec) -> None:
        origin = p.pos
        hits: list[tuple[float, str, Any]] = []
        for w in self.world.walls:
            if w.top <= p.level or w.low or w.material == PLATFORM or not self.wall_active(w):  # bullets fly over low props
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
        head_over = {id(pl[0]) for _, kind, pl in hits if kind == "player" and pl[1] == "head" and not pl[0].crouching}
        mult = 1.0
        end = d.range
        stopped_by = ""
        for i, (dist, kind, payload) in enumerate(hits):
            if kind == "wall":
                wall, thickness = payload
                cover = wall.top == p.level + 1  # head-high: a standing target's head shows above it
                nxt = next((h for h in hits[i + 1:] if h[1] == "player"), None)
                if cover and nxt is not None and id(nxt[2][0]) in head_over and nxt[0] - dist < 3.0:
                    continue
                if wall.penetration >= 3 or wall.penetration > d.penetration or thickness > 1.0 + d.penetration:
                    end = dist
                    stopped_by = "wall"
                    break
                mult *= PEN_DAMAGE.get(wall.penetration, 0.5)
                continue
            target, zone = payload
            dmg = int(round(d.damage_at(dist, zone) * mult))
            through = mult < 1.0
            slow = float(rule("tagging", "through_walls" if through else "slow", 0.25 if through else 0.725))
            target.tagged_until = self.time + float(rule("tagging", "seconds", 0.35))
            target.tag_slow = max(slow, target.tag_slow if self.time < target.tagged_until else 0.0)
            self._wallbang = through
            self._damage(p, target, dmg, zone, d.key)
            self._wallbang = False
            end = dist
            stopped_by = "player"
            break
        tip = origin + direction * end
        self.events.append(GameEvent("shot", self.time, {"pid": p.pid, "from": (origin.x, origin.y), "to": (tip.x, tip.y), "weapon": d.key,
                                                          "stop": stopped_by}))

    def _damage(self, attacker: PlayerState | None, target: PlayerState, dmg: int, zone: str, source: str) -> None:
        if not target.alive or dmg <= 0:
            return
        if self.cheat("invincibility") and not target.is_bot:
            return
        factor = abilities.mult(self, target, "damage_taken") * (abilities.mult(self, attacker, "damage_dealt") if attacker else 1.0)
        if factor != 1.0:
            dmg = int(round(dmg * factor))
        absorbed = min(target.armor, int(round(dmg * self._absorb)))
        target.armor -= absorbed
        dealt = min(dmg, max(0, target.hp + absorbed))
        target.hp -= dmg - absorbed
        if attacker is not None and attacker.team != target.team:
            entry = self.round_damage.setdefault((attacker.pid, target.pid), [0, 0])
            entry[0] += dealt
            entry[1] += 1
            attacker.damage_total += dealt
            if zone == "head":
                attacker.headshots += 1
        self.events.append(GameEvent("hit", self.time, {"by": attacker.pid if attacker else None, "pid": target.pid, "dmg": dmg, "zone": zone}))
        if target.hp <= 0:
            self._kill(attacker, target, source, zone)

    def _kill(self, attacker: PlayerState | None, target: PlayerState, source: str, zone: str) -> None:
        target.alive = False
        target.died_at = self.time
        target.hp = 0
        target.deaths += 1
        target.ult_points += int(self._ult["per_death"])
        target.plant_progress = target.defuse_progress = 0.0
        if self.spike_carrier == target.pid:
            self.spike_carrier = None
            self.spike_pos = target.pos
        for slot in ("primary", "sidearm"):
            ws = target.weapons.get(slot)
            if ws and (slot == "primary" or ws.key != "pistol"):
                self.drops.append(Drop(ws.key, ws.mag, ws.reserve, target.pos))
                break
        if attacker and attacker.team != target.team:
            attacker.kills += 1
            attacker.round_kills += 1
            for (dealer, victim), (dealt, _) in self.round_damage.items():
                helper = self.players.get(dealer)
                if victim == target.pid and dealt > 0 and helper is not None and helper.pid != attacker.pid \
                        and helper.team == attacker.team:
                    helper.assists += 1
            if not self._first_kill_done and not self.practice:
                attacker.first_kills += 1
        if not self.practice:
            self._first_kill_done = True
        if attacker and attacker.team != target.team:
            attacker.credits = min(int(self._eco["max"]), attacker.credits + int(self._eco["kill"]))
            attacker.ult_points += int(self._ult["per_kill"])
            ab = self.agents[attacker.agent]["abilities"].get("E", {})
            if "kills_to_recharge" in ab:
                attacker.sig_kills += 1
                if attacker.sig_kills >= int(ab["kills_to_recharge"]):
                    attacker.sig_kills = 0
                    attacker.charges["E"] = min(int(ab["max"]), attacker.charges.get("E", 0) + 1)
        self.events.append(GameEvent("kill", self.time, {"by": attacker.pid if attacker else None, "pid": target.pid, "weapon": source,
                                                          "head": zone == "head", "wallbang": bool(getattr(self, "_wallbang", False)),
                                                          "streak": attacker.round_kills if attacker else 0}))
        alive_team = [q for q in self.players.values() if q.team == target.team and q.alive and not q.dummy]
        if len(alive_team) == 1 and target.team not in self.last_alive_vs:
            self.last_alive_vs[target.team] = len([q for q in self.players.values() if q.team != target.team and q.alive])

    # ------------------------------------------------------------------ Abilities
    def _use_multi(self, p: PlayerState, key: str, points: list) -> None:
        """Multi-placement (multi=N): one charge per point for C/Q/E; the ultimate costs once for all of its points."""
        ab = self.agents[p.agent]["abilities"].get(key, {})
        limit = max(1, int(ab.get("multi", 1)))
        chosen = [Vec(float(x), float(y)) for x, y in points[:limit]]
        if key == "X":
            if not chosen or (p.ult_points < int(ab.get("cost", 99)) and not self.cheat("infinite_abilities")):
                return
            used = [q for q in chosen if self._use_ability(p, key, point=q, free=True)]
            if used and not self.cheat("infinite_abilities"):
                p.ult_points -= int(ab["cost"])
            return
        for q in chosen:
            self._use_ability(p, key, point=q)

    def _use_ability(self, p: PlayerState, key: str, alt: bool = False, point: Vec | None = None, free: bool = False) -> bool:
        ab = self.agents[p.agent]["abilities"].get(key)
        if ab and alt and isinstance(ab.get("alt"), dict):
            ab = {**ab, **ab["alt"]}  # right-click variant: its values replace the normal ones
        if not ab or abilities.flag(self, p, "no_abilities"):
            return False
        endless = self.cheat("infinite_abilities") or free
        if endless:
            pass
        elif key == "X":
            if p.ult_points < int(ab["cost"]):
                return False
        elif p.charges.get(key, 0) <= 0:
            return False
        try:
            target = abilities.use(self, p, key, ab, point=point)
        except (KeyError, TypeError, ValueError) as exc:
            warnings.warn(f"Ability {ab.get('name', key)} of {p.agent} misconfigured: {exc}")
            return False
        if target is None:
            return False
        if endless:
            pass
        elif key == "X":
            p.ult_points -= int(ab["cost"])
        else:
            p.charges[key] -= 1
        self.events.append(GameEvent("ability", self.time, {"pid": p.pid, "key": key, "kind": ab["kind"], "pos": (target.x, target.y),
                                                            "sound": str(ab.get("sound", ""))}))
        return True

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
            blocks = e.props.get("blocks_sight", e.kind in ("smoke", "wall"))
            if blocks and e.a is None and e.radius > 0 and segment_circle_hit(a, b, e.pos, e.radius):
                if (a - e.pos).length() > e.radius and (b - e.pos).length() > e.radius:
                    return False
                return (a - e.pos).length() <= e.radius and (b - e.pos).length() <= e.radius
            if blocks and e.a and e.b and e.kind != "tripwire":
                from gameplay.geometry import segments_intersect
                if segments_intersect(a, b, e.a, e.b):
                    return False
        return True

    def line_of_fire(self, shooter: PlayerState, target: PlayerState) -> bool:
        """True if a bullet from the shooter's current weapon can get through to the target."""
        d = self._weapon_def(shooter)
        pen = d.penetration if d else 0
        a, b = shooter.pos, target.pos
        dist = (b - a).length()
        if dist < 1e-6:
            return True
        u = (b - a) * (1.0 / dist)
        for w in self.world.walls:
            if w.top <= shooter.level or w.material == PLATFORM or not self.wall_active(w):
                continue
            iv = w.rect.ray_interval(a, u)
            if iv and iv[0] < dist and (w.penetration >= 3 or w.penetration > pen or iv[1] - iv[0] > 1.0 + pen):
                return False
        return True

    def _behind_cover(self, viewer: PlayerState, target: PlayerState) -> bool:
        """A head-high wall (one level above the target, not a low prop) lies between them, close to the target."""
        direction = target.pos - viewer.pos
        dist = direction.length()
        if dist < 1e-6:
            return False
        unit = direction * (1.0 / dist)
        for w in self.world.walls:
            if w.top != target.level + 1 or w.low or w.top <= viewer.level:
                continue
            iv = w.rect.ray_interval(viewer.pos, unit)
            if iv and iv[0] < dist and dist - iv[0] < 3.0:
                return True
        return False

    def can_see(self, viewer: PlayerState, target: PlayerState) -> bool:
        if not target.alive:
            return False
        if viewer.pid == target.pid or viewer.team == target.team:
            return True
        if target.revealed_until > self.time:
            return True
        if viewer.blind_until > self.time or not viewer.alive:
            return False
        sight = abilities.lowest(self, viewer, "sight_range")
        if sight is not None and (target.pos - viewer.pos).length() > sight:
            return False
        if target.crouching and self._behind_cover(viewer, target):
            return False  # crouched behind head-high cover
        cloak = abilities.lowest(self, target, "seen_within")
        if cloak is not None and (target.pos - viewer.pos).length() > cloak:
            return False
        if not self.cfg.lobby.all_around_sight:
            to = angle_of(target.pos - viewer.pos)
            if abs(angle_diff(viewer.facing, to)) > self.fov / 2:
                return False
        return self._line_clear(viewer.pos, target.pos, min(viewer.level, target.level))

    # ------------------------------------------------------------------ Bomb
    def _tick_spike(self, dt: float, commands: dict[int, Command]) -> None:
        if self.phase in ("buy", "live") and self.spike_carrier is None and self.spike_pos is not None:
            for p in self.players.values():
                if p.alive and self.side(p.team) == "attack" and (p.pos - self.spike_pos).length() <= PICKUP_RANGE                         and self.time - p.dropped_at >= 1.0:
                    self.spike_carrier = p.pid
                    self.spike_pos = None
                    break
        if self.phase == "live" and self.spike_carrier is not None:
            p = self.players[self.spike_carrier]
            cmd = commands.get(p.pid, Command())
            site = self.world.site_at(p.pos)
            if p.alive and cmd.interact and site and p.z <= 0.001:
                if p.plant_progress == 0.0:
                    self.events.append(GameEvent("plant_start", self.time, {"pid": p.pid, "pos": (p.pos.x, p.pos.y)}))
                p.plant_progress += dt
                if p.plant_progress >= float(self._spike["plant_time"]):
                    self._plant(p, site.name)
            else:
                if p.plant_progress > 0.0:
                    self.events.append(GameEvent("plant_stop", self.time, {"pid": p.pid}))
                p.plant_progress = 0.0
        if self.phase == "planted" and self.spike_pos is not None:
            for p in self.players.values():
                if not p.alive or self.side(p.team) != "defense":
                    continue
                cmd = commands.get(p.pid, Command())
                if cmd.interact and (p.pos - self.spike_pos).length() <= INTERACT_RANGE and p.z <= 0.001:
                    if p.defuse_progress in (0.0, float(self._spike["defuse_checkpoint"])) and not p.defusing:
                        self.events.append(GameEvent("defuse_start", self.time, {"pid": p.pid, "pos": (p.pos.x, p.pos.y)}))
                    p.defusing = True
                    cp = float(self._spike["defuse_checkpoint"])
                    if p.defuse_progress < cp <= p.defuse_progress + dt:
                        self.events.append(GameEvent("defuse_half", self.time, {"pid": p.pid}))
                    p.defuse_progress += dt
                    if p.defuse_progress >= float(self._spike["defuse_time"]):
                        p.ult_points += int(self._ult["per_defuse"])
                        p.defuses += 1
                        self.events.append(GameEvent("defuse", self.time, {"pid": p.pid}))
                        self._end_round(p.team, "Bomb defused")
                        return
                else:
                    cp = float(self._spike["defuse_checkpoint"])
                    p.defuse_progress = cp if p.defuse_progress >= cp else 0.0
                    if p.defusing:
                        self.events.append(GameEvent("defuse_stop", self.time, {"pid": p.pid}))
                    p.defusing = False
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
        self.orbs = []  # orbs vanish when the spike is planted
        p.plant_progress = 0.0
        p.plants += 1
        p.ult_points += int(self._ult["per_plant"])
        for t in self.players.values():
            if t.team == p.team:
                t.credits = min(int(self._eco["max"]), t.credits + int(self._eco["plant"]))
        self.events.append(GameEvent("plant", self.time, {"pid": p.pid, "site": site}))

    # ------------------------------------------------------------------ Snapshot
    def combat_score(self, p: PlayerState) -> int:
        """Own score for MVP and the scoreboard: damage plus bonuses for kills and objectives."""
        return p.damage_total + 150 * p.kills + 50 * p.first_kills + 100 * (p.plants + p.defuses)

    def damage_report(self, pid: int) -> list[dict[str, int]]:
        """This round: per opponent, damage and hits dealt by pid and taken from them."""
        rows: dict[int, dict[str, int]] = {}
        for (attacker, target), (dmg, hits) in self.round_damage.items():
            if attacker == pid:
                rows.setdefault(target, {"pid": target, "dealt": 0, "dealt_hits": 0, "taken": 0, "taken_hits": 0})
                rows[target]["dealt"] += dmg
                rows[target]["dealt_hits"] += hits
            elif target == pid:
                rows.setdefault(attacker, {"pid": attacker, "dealt": 0, "dealt_hits": 0, "taken": 0, "taken_hits": 0})
                rows[attacker]["taken"] += dmg
                rows[attacker]["taken_hits"] += hits
        return sorted(rows.values(), key=lambda r: -(r["dealt"] + r["taken"]))

    def _effect_visible(self, e: Effect, viewer: PlayerState | None) -> bool:
        """Flashes and decoys are never drawn; enemy traps only for their own team."""
        hidden = e.props.get("hidden", {"decoy": "all", "alarm": "enemies", "tripwire": "enemies"}.get(e.kind))
        if hidden == "all":
            return False
        if hidden == "enemies" and viewer is not None and viewer.team != e.team:
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
                "x": p.pos.x, "y": p.pos.y, "z": p.z, "level": p.level, "ground": p.ground, "facing": p.facing,
                "alive": p.alive, "hp": p.hp, "armor": p.armor,
                "credits": p.credits if viewer is None or viewer.team == p.team else None,
                "slot": p.slot, "weapon": p.weapon.key if p.weapon else None,
                "mag": p.weapon.mag if p.weapon else 0, "reserve": p.weapon.reserve if p.weapon else 0,
                "charges": dict(p.charges), "ult": p.ult_points, "kills": p.kills, "deaths": p.deaths, "assists": p.assists,
                "sellable": [b["item"] for b in p.purchases if self.sellable(p, b["item"])] if viewer is None or viewer.pid == p.pid else [],
                "orb": p.orb_progress, "crouch": p.crouching,
                "blind": p.blind_until > self.time, "reloading": p.reload_until > self.time,
                "plant": p.plant_progress, "defuse": p.defuse_progress,
                "status": sorted(k for k, v in p.status.items() if v > self.time)
                if viewer is None or viewer.team == p.team else [],
                "request": p.request if viewer is None or viewer.team == p.team else "",
                "anchor": [p.anchor.x, p.anchor.y] if p.anchor is not None and p.anchor_until > self.time
                and (viewer is None or viewer.team == p.team) else None,
                "dashing": p.dash_until > self.time,
                "vx": p.vel.x, "vy": p.vel.y, "spray": p.spray,
            })
        return {
            "time": self.time, "phase": self.phase, "phase_left": self.phase_time_left(), "round": self.round_no,
            "mode": self.mode, "dm_left": max(0.0, self.dm_ends_at - self.time) if self.mode == "deathmatch" else 0.0,
            "rules": {k: getattr(self.cfg.lobby, k) for k in self.RULE_NAMES},
            "score": list(self.score), "attacking_team": self.attacking_team, "winner": self.match_winner,
            "round_winner": self.round_winner, "round_reason": self.round_reason,
            "spike": {"carrier": self.spike_carrier, "pos": (self.spike_pos.x, self.spike_pos.y) if self.spike_pos else None, "site": self.spike_site},
            "effects": [{"kind": e.kind, "team": e.team, "x": e.pos.x, "y": e.pos.y, "r": e.radius,
                         "a": (e.a.x, e.a.y) if e.a else None, "b": (e.b.x, e.b.y) if e.b else None,
                         "start": e.start, "until": e.until, "status": e.props.get("status")}
                        for e in self.effects if self._effect_visible(e, viewer)],
            "players": players,
            "orbs": [(o.x, o.y) for o in self.orbs],
            "roster": [{"pid": p.pid, "name": p.name, "team": p.team, "agent": p.agent, "kills": p.kills, "assists": p.assists,
                        "deaths": p.deaths, "alive": p.alive, "bot": p.is_bot, "ping": p.ping_ms,
                        "score": self.combat_score(p), "damage": p.damage_total}
                       for p in self.players.values()],
            "history": [[w, r] for w, r in self.history],
            "report": self.damage_report(viewer.pid) if viewer is not None else [],
            "drops": [{"key": d.key, "x": d.pos.x, "y": d.pos.y} for d in self.drops],
            "doors_open": [[r.x0, r.y0, r.x1, r.y1] for r in self.open_doors],
        }
