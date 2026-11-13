"""Authoritative match: movement, combat, economy, rounds, bomb, abilities.

Controlled only through one Command per player and tick. A host (player 1 or a dedicated
server process) runs Match.tick and sends Match.snapshot() to everyone.
"""
from __future__ import annotations

import math
import random
import warnings
from dataclasses import dataclass, field, replace
from functools import cached_property, lru_cache
from typing import Any

from gameplay import abilities
from gameplay.data import LEGACY_ITEM_KEYS, ROOT, GameConfig, WeaponDef, _load_py, load_armor, load_config, load_weapons, rule
from gameplay.geometry import Rect, Vec, angle_diff, angle_of, heading, segment_circle_hit
from gameplay.hitzones import resolve_zone
from gameplay.kit.registry import COMMAND_FILTERS, LETHAL_FILTERS, MATCH_TICKS
from gameplay.nav import NavGrid
from gameplay.skins import clean_loadout
from gameplay.world import PLATFORM, Wall, WorldMap, head_height

SLOTS = ("primary", "sidearm", "melee")
FULL_WALL = 2  # walls this many levels high are never climbed or jumped over
PEN_DAMAGE = {0: 0.8, 1: 0.6, 2: 0.45}  # damage factor after passing through a material (own value)
INTERACT_RANGE = 1.5
DOOR_RANGE = 1.6
PICKUP_RANGE = 1.2


AGENTS_DIR = ROOT / "config" / "content" / "agents"
PLAYABLE_AGENT_KEYS = (
    "brimstone", "omen", "jett", "sova", "sage", "cypher", "phoenix", "killjoy", "breach", "reyna", "miks", "waylay",
    "gekko", "chamber", "raze", "skye", "kayo", "viper", "neon", "yoru", "fade", "harbor", "deadlock", "vyse", "iso", "clove", "tejo", "veto", "astra", "hush",
)
DEFAULT_AGENT = "omen"
SPRAY_SEEDS = {key: sum(map(ord, old)) for old, key in LEGACY_ITEM_KEYS["weapons"].items()}


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
            "sprites": dict(agent.get("sprites", {})), "passives": list(agent.get("passives", [])),
            "interact_bonus": float(agent.get("interact_bonus", 0)),
            "drift_fall_speed": float(agent.get("drift_fall_speed", 0.0))}))
    return {key: data for _, key, data in sorted(found, key=lambda f: (f[0], f[1]))}


def playable_agents() -> dict[str, dict[str, Any]]:
    return {key: data for key, data in load_agents().items() if key in PLAYABLE_AGENT_KEYS}


def spray_offset(d: WeaponDef, index: int) -> float:
    """Deterministic part of the spray in degrees for bullet `index` of a spray (0 = first bullet).

    The first bullets stay on target, then the aim drifts to one side (side and sway
    taste per weapon from its key), with a slow sway back and forth; capped at the weapon's spray_max.
    Counter it by moving the mouse against the drift. Semi-automatic weapons and shotguns have none.
    """
    if not d.auto or d.pellets > 1 or index < 2:
        return 0.0
    seed = SPRAY_SEEDS.get(d.key, sum(map(ord, d.key)))
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
    target_lift: float = 0.0
    bounces: int = 0
    drone_pitch: float = 0.0
    points: list = field(default_factory=list)  # multi-placement: chosen map points (x, y) for the ability
    interact: bool = False       # plant or defuse the bomb (hold)
    use_spike: bool = False
    drop: bool = False           # G: drop the bomb if carried, else the weapon in hand
    buy: list[str] = field(default_factory=list)  # item keys, teammate gifts, or TDM loadout selections
    request: str | None = None   # weapon key this player asks the team for ("" clears)
    request_clicks: list[str] = field(default_factory=list)
    equipment_actions: list[str] = field(default_factory=list)

    def ordered_equipment(self) -> list[str]:
        if self.equipment_actions:
            return self.equipment_actions
        return ([self.slot] if self.slot else []) + (["reload"] if self.reload else []) + (["drop"] if self.drop else [])


@dataclass
class WeaponState:
    key: str
    mag: int
    reserve: int
    skin: str = ""
    from_station: bool = False


@dataclass
class PlayerState:
    pid: int
    name: str
    team: int
    agent: str
    duel_id: int = field(default=0, init=False)
    duel_bounds: Rect | None = field(default=None, init=False)
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
    death_drop: Drop | None = field(default=None, init=False)
    hp: int = 100
    armor: int = 0
    armor_key: str = ""
    dm_loadout: list[str] = field(default_factory=list)
    dm_stowed_primary: WeaponState | None = None
    dm_stage_equip_until: float = 0.0
    dm_spawn_protected_until: float = 0.0
    dm_ghost: bool = False
    dm_ghost_origin: Vec = Vec(0, 0)
    dm_next_spawn_damage: float = 0.0
    dm_recovery_until: float = 0.0
    dm_recovery_paused_until: float = 0.0
    dm_recovery_hp_frac: float = 0.0
    dm_recovery_armor_frac: float = 0.0
    overheal: int = 0
    overheal_until: float = 0.0
    armor_reserve: int = 0
    armor_regen_at: float | None = None
    credits: int = 800
    weapons: dict[str, WeaponState] = field(default_factory=dict)
    weapon_skins: dict[str, str] = field(default_factory=dict, kw_only=True)
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
    dash_armed_at: float = 0.0
    dash_armed_until: float = 0.0
    channel_until: float = 0.0
    blade_count: int = 0
    blades_equipped: bool = False
    repeat_shots: int = 0
    repeat_until: float = 0.0
    repeat_next: float = 0.0
    plant_progress: float = 0.0
    spike_equipped: bool = False
    defuse_progress: float = 0.0
    status: dict[str, float] = field(default_factory=dict)  # status -> active until
    immune_until: float = 0.0
    anchor: Vec | None = None
    anchor_until: float = 0.0
    heal_left: float = 0.0
    heal_rate: float = 0.0
    dm_heal_source: int | None = None
    dm_healed_by: dict[int, float] = field(default_factory=dict)
    hp_frac: float = 0.0
    decay_pool: float = 0.0
    recharge_timers: dict[str, float] = field(default_factory=dict)
    ability_ready_at: dict[str, float] = field(default_factory=dict)
    dm_device_recalls: dict[str, list[float]] = field(default_factory=dict)
    temporary_charges: dict[str, int] = field(default_factory=dict)
    last_pos: Vec | None = None
    prev_ability: str | None = None
    prev_interact: bool = False
    zipline: int | None = None
    quiet_drop: bool = False
    quiet_landing_at: float = -99.0
    visible: bool = True  # only meaningful in a client's shadow match
    ping_ms: int | None = None  # round trip to the host; None for bots and the host itself
    dummy: bool = False  # practice-range target: does nothing, respawns after death
    remote_score: int = 0  # client copy of the host's combat score
    request: str = ""  # weapon asked for this round
    request_revision: int = 0
    home: Vec = Vec(0, 0)
    died_at: float = -99.0
    ability_return_at: float = -99.0

    def gift_action(self) -> str:
        return f"gift:{self.pid}:{self.request_revision}:{self.request}"

    @property
    def weapon(self) -> WeaponState | None:
        return self.weapons.get(self.slot)


@dataclass(eq=False)
class Drop:
    key: str
    mag: int
    reserve: int
    pos: Vec
    skin: str = ""
    ground: float | None = None


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

    def fall_offset(self, now: float) -> float:
        fall = self.props.get("fall")
        if fall is None:
            return 0.0
        lift, speed = fall
        return max(0.0, lift - max(0.0, now - self.start) * speed)


@dataclass
class GameEvent:
    kind: str  # shot, hit, kill, sound, plant, defuse, explode, round_end, ability, buy
    t: float
    data: dict[str, Any]

    def sound_radius_at(self, listener_pos: Vec) -> float:
        radius = float(self.data["radius"])
        if "shot_facing" in self.data:
            offset = listener_pos - Vec(*self.data["pos"])
            angle = angle_diff(self.data["shot_facing"], angle_of(offset))
            if abs(angle) <= self.data["forward_half_angle"]:
                return max(radius, float(self.data["forward_radius"]))
        return radius

    def within_sound_range(self, listener_pos: Vec) -> bool:
        origin = Vec(*self.data["pos"])
        return (listener_pos - origin).length() < self.sound_radius_at(listener_pos)


class Match:
    def __init__(self, world: WorldMap, config: GameConfig | None = None, seed: int | None = None,
                 *, agent_roster: dict[str, dict[str, Any]] | None = None) -> None:
        self.world = world
        self.cfg = config or load_config()
        self.weapons = load_weapons()
        self.armor = load_armor()
        self.agents = load_agents() if agent_roster is None else agent_roster
        self.ability_weapons = {weapon.key: weapon
                                for agent in self.agents.values() for ab in agent["abilities"].values()
                                if (weapon := ab.get("ability_weapon") or ab.get("registered_weapon")) is not None}
        self.weapons = {**self.weapons, **self.ability_weapons}
        self.statuses = abilities.load_statuses()
        self.rng = random.Random(seed)
        self.players: dict[int, PlayerState] = {}
        self.effects: list[Effect] = []
        self.remote_minimap_obscured = False
        self.remote_paranoia_warning = False
        self.drops: list[Drop] = []
        self.events: list[GameEvent] = []
        self.open_doors: set[Rect] = set()
        self.door_close_at: dict[Rect, float] = {}
        self.broken_cover: set[Rect] = set()
        self.cover_health: dict[Rect, int] = {}
        self.round_damage: dict[tuple[int, int], list[int]] = {}  # (attacker, target) -> [damage, hits] this round
        self.dm_recent_damage: dict[tuple[int, int], list[tuple[float, int]]] = {}
        self.history: list[tuple[int, str]] = []  # (winning team, reason) per finished round
        self.remote_report: list[dict[str, int]] = []  # client copy of the viewer's damage report
        self._first_kill_done = False
        self.practice = False  # practice range: endless live phase, free buying, respawning dummies
        self.mode = "standard"
        self.dm_ends_at = 0.0
        self.dm_timer_paused = False
        self.dm_stage = 0
        self.time = 0.0
        self.phase = "lobby"  # lobby, buy, live, planted, end, over
        self.phase_until = 0.0
        self.round_no = 0
        self.score = [0, 0]
        self.attacking_team = 0
        self.loss_streak = [0, 0]
        self.orbs: list[Vec] = []          # ultimate orbs lying on the map this round
        self.dm_recovery_orbs: dict[Vec, float] = {}
        self.dm_ultimate_anchors: list[Vec] = []
        self.dm_next_ultimate_wave = 0.0
        self.loadout_value = [0, 0]        # team loadout value at the start of the live phase (thrifty)
        self.last_alive_vs: dict[int, int] = {}  # team -> enemies alive when it was down to its last player (clutch)
        self.spike_carrier: int | None = None
        self.spike_pos: Vec | None = None
        self.spike_ground = 0.0
        self.spike_planted_at = 0.0
        self.spike_site = ""
        self.spike_half_defused = False
        self.spike_player_defuser: tuple[PlayerState, Command] | None = None
        self.spike_player_defuser_at_tick_start: int | None = None
        self.spike_device_defuser_at_tick_start: Effect | None = None
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
        self._sound = {k: rule("sound", k, d) for k, d in (
            ("run_radius", 18.0), ("shot_radius", 45.0), ("silenced_radius", 40.0),
            ("silenced_forward_radius", 80.0), ("silenced_half_angle", 30.0),
        )}

    # ------------------------------------------------------------------ Setup
    def add_player(self, name: str, team: int, agent: str, is_bot: bool = False, *, weapon_skins: object = None) -> PlayerState:
        if agent not in self.agents:
            fallback = DEFAULT_AGENT if DEFAULT_AGENT in self.agents else next(iter(self.agents))
            warnings.warn(f"Unavailable agent {agent}; using {fallback}.")
            agent = fallback
        pid = max(self.players, default=0) + 1
        p = PlayerState(pid=pid, name=name, team=team, agent=agent, is_bot=is_bot, credits=int(self._eco["start"]),
                        weapon_skins=clean_loadout(weapon_skins, self.weapons))
        self.players[pid] = p
        return p

    RULE_NAMES = ("all_around_sight", "sound_rings", "win_rounds", "overtime", "play_all_rounds", "allow_cheats",
                  "infinite_ammo", "infinite_magazines", "infinite_abilities", "invincibility", "bullet_tracers")

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
        self.win_rounds, self.overtime = self.cfg.lobby.win_rounds, self.cfg.lobby.overtime
        for key, default in (("half_after", 12), ("buy_time", 30), ("round_time", 100)):
            self._r[key] = rule("rounds", key, default)
        if self.mode == "quick":
            q = rule("modes", "quick", {})
            self.win_rounds = int(q.get("win_rounds", 5))
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
        """Set up the first loadout during the pre-match spawn phase."""
        dm = self.deathmatch_rules
        self.round_no, self.score, self.match_winner, self.attacking_team = 0, [0, 0], None, 0
        self._start_round()
        self.spike_carrier = None
        self.dm_stage = 1
        self.phase_until = self.time + dm["setup_time"]
        self.dm_ends_at = self.phase_until + sum(dm["stage_times"])
        self.dm_timer_paused = False
        self.dm_recovery_orbs = dict.fromkeys(self._deathmatch_recovery_anchors(), self.phase_until)
        self.dm_ultimate_anchors = self._deathmatch_ultimate_anchors()
        self.dm_next_ultimate_wave = self.phase_until + dm["ultimate_orbs"]["interval"]
        for p in self.players.values():
            p.credits = 0
            p.ult_points = 0
            p.dm_device_recalls.clear()
            p.dm_healed_by.clear()
            p.dm_heal_source = None
            p.dm_spawn_protected_until = p.dm_next_spawn_damage = 0.0
            self._clear_deathmatch_recovery(p)
            for key, cooldown in zip(("C", "Q", "E"), dm["ability_cooldowns"].get(p.agent, ())):
                ab = self.agents[p.agent]["abilities"][key]
                if cooldown > 0 and not ab.get("shared_charge"):
                    p.charges[key] = int(key == "E")
                    p.recharge_timers[key] = cooldown / 2
            if p.agent == "astra":
                p.charges["E"] = dm["astra"]["start_stars"]
                p.recharge_timers["E"] = 0.0
            p.dm_loadout = [next(iter(options)) for options in dm["loadouts"]]
            self._equip_deathmatch(p)

    @cached_property
    def deathmatch_rules(self) -> dict:
        return rule("modes", "deathmatch", {})

    def can_end_deathmatch_phase(self) -> bool:
        return (self.mode == "deathmatch" and not self.practice and self.cfg.lobby.allow_cheats
                and self.phase in ("buy", "live") and self.phase_until > self.time)

    def end_deathmatch_phase(self) -> bool:
        if not self.can_end_deathmatch_phase():
            return False
        skipped = self.phase_until - self.time
        self.phase_until = self.time
        self.dm_timer_paused = False
        self.dm_ends_at -= skipped
        if self.phase == "buy":
            self.dm_recovery_orbs = dict.fromkeys(self.dm_recovery_orbs, self.time)
            self.dm_next_ultimate_wave -= skipped
        return True

    def toggle_deathmatch_timer(self) -> bool:
        if not self.can_end_deathmatch_phase():
            return False
        self.dm_timer_paused = not self.dm_timer_paused
        return True

    def can_toggle_deathmatch_ghost(self, p: PlayerState) -> bool:
        return (self.mode == "deathmatch" and self.phase == "live" and self.cfg.lobby.allow_cheats
                and p.alive and not p.is_bot and not p.duel_id)

    def _toggle_deathmatch_ghost(self, p: PlayerState) -> None:
        if not self.can_toggle_deathmatch_ghost(p):
            return
        if p.dm_ghost:
            ground = self.world.ground_height(p.pos)
            radius = float(self._mv["radius"])
            if ground < 0 or any(w.rect.circle_push(p.pos, radius) is not None and self.wall_active(w)
                                 and (w.full or w.base <= ground < w.top) for w in self.combat_walls()):
                p.pos = p.dm_ghost_origin
                ground = self.world.ground_height(p.pos)
            p.ground = ground * float(self._mv["level_height"])
            p.level = int(ground + 0.5)
        else:
            p.dm_ghost_origin = p.pos
            p.zipline = None
            p.quiet_drop, p.quiet_landing_at = False, -99.0
        p.dm_ghost = not p.dm_ghost
        p.vel, p.vz, p.z = Vec(0, 0), 0.0, 0.0
        p.dash_until = p.reload_until = 0.0

    def can_select_deathmatch_loadout(self, p: PlayerState) -> bool:
        return (self.in_deathmatch_spawn(p) and self.phase in ("buy", "live") and p.alive and not p.dm_ghost
                and len(p.dm_loadout) == len(self.deathmatch_rules["loadouts"]))

    def _select_deathmatch_loadout(self, p: PlayerState, item: str) -> bool:
        if not self.can_select_deathmatch_loadout(p):
            return False
        # The stage is explicit because Ares is an option in two different stages.
        prefix, _, weapon = item.partition(":")
        for index, options in enumerate(self.deathmatch_rules["loadouts"]):
            if prefix == f"tdm{index + 1}" and weapon in options and weapon in self.weapons:
                if p.dm_loadout[index] != weapon:
                    p.dm_loadout[index] = weapon
                    if index + 1 == self.dm_stage:
                        self._equip_deathmatch(p)
                    elif index == 0:
                        p.weapons["sidearm"] = self._new_weapon(weapon, p)
                        if p.slot == "sidearm":
                            self._reset_deathmatch_weapon(p)
                return True
        return False

    def deathmatch_stage_equip_left(self, p: PlayerState) -> float:
        if self.mode != "deathmatch" or self.phase != "live" or not p.alive or p.duel_id or p.dm_ghost:
            return 0.0
        return max(0.0, p.dm_stage_equip_until - self.time)

    def _equip_deathmatch(self, p: PlayerState, *, keep_station: bool = False) -> None:
        for effect in self.effects:
            if effect.owner == p.pid and "return_armor" in effect.data:
                effect.data["keep_current_armor"] = True
        p.dm_stage_equip_until = 0.0
        index = self.dm_stage - 1
        weapon = p.dm_loadout[index]
        primary = self._new_weapon(weapon, p) if index else None
        held_primary = p.weapons.get("primary")
        if keep_station and held_primary is not None and held_primary.from_station:
            p.dm_stowed_primary = primary
        else:
            p.dm_stowed_primary = None
            p.weapons["sidearm"] = self._new_weapon(p.dm_loadout[0], p)
            if primary is None:
                p.weapons.pop("primary", None)
            else:
                p.weapons["primary"] = primary
            slot = "primary" if primary is not None and not abilities.flag(self, p, "jam_primary") else "sidearm"
            if keep_station and p.slot == "ability":
                p.passive_state["ability_weapon_prior"] = slot
            elif keep_station and p.blades_equipped:
                p.slot = slot
            else:
                p.slot = slot
                self._reset_deathmatch_weapon(p)
        p.armor_key = self.deathmatch_rules["loadouts"][index][weapon]
        armor = self.armor.get(p.armor_key)
        p.armor, p.armor_reserve = (armor.points, armor.regen_pool) if armor else (0, 0)
        p.armor_regen_at = None
        p.dm_recovery_armor_frac = 0.0

    @cached_property
    def _deathmatch_pickup_candidates(self) -> list[Vec]:
        world = self.world
        if not all(world.spawns.get(team) for team in (0, 1)):
            return []
        grid = NavGrid(world, frozenset(self.open_doors))
        shared = grid.connected_cells(world.spawns[0][0])
        other_spawn = grid.nearest_free(grid.cell(world.spawns[1][0]))
        if other_spawn not in shared:
            return []
        cells = [grid.center(cell) for cell in shared if grid.free(cell) and cell not in grid.deck_height]
        return [point for point in cells if not any(zone.contains(point) for zone in world.spawn_zones.values())]

    def _deathmatch_pickup_anchors(self, targets: list[Vec], count: int, occupied: list[Vec]) -> list[Vec]:
        candidates = [point for point in self._deathmatch_pickup_candidates
                      if all((point - anchor).length() > 8.0 for anchor in occupied)]
        anchors: list[Vec] = []
        for target in targets:
            if not candidates:
                break
            point = min(candidates, key=lambda pos: ((pos - target).length(), pos.x, pos.y))
            anchors.append(point)
            candidates = [pos for pos in candidates if (pos - point).length() > 8.0]
            if len(anchors) == count:
                break
        return anchors

    @cached_property
    def _deathmatch_station_anchors(self) -> list[Vec]:
        if not self._deathmatch_pickup_candidates:
            return []
        world = self.world
        center = (world.spawns[0][0] + world.spawns[1][0]) * 0.5
        targets = [center, *(center + (site.rect.center - center) * 0.6 for site in world.sites)]
        return self._deathmatch_pickup_anchors(targets, 3, [])

    def _deathmatch_recovery_anchors(self) -> list[Vec]:
        if not self._deathmatch_pickup_candidates:
            return []
        world = self.world
        first, second = world.spawns[0][0], world.spawns[1][0]
        targets = [*world.orbs, first + (second - first) * 0.4, first + (second - first) * 0.6]
        return self._deathmatch_pickup_anchors(targets, 2, self._deathmatch_station_anchors)

    def _deathmatch_ultimate_anchors(self) -> list[Vec]:
        if not self._deathmatch_pickup_candidates:
            return []
        world = self.world
        first, second = world.spawns[0][0], world.spawns[1][0]
        targets = [*world.orbs, first + (second - first) * 0.45, first + (second - first) * 0.55]
        occupied = [*self._deathmatch_station_anchors, *self.dm_recovery_orbs]
        return self._deathmatch_pickup_anchors(targets, 2, occupied)

    @property
    def recovery_orbs(self) -> list[Vec]:
        if self.mode != "deathmatch" or self.phase != "live":
            return []
        return [point for point, ready_at in self.dm_recovery_orbs.items() if self.time >= ready_at]

    def _clear_deathmatch_recovery(self, p: PlayerState) -> None:
        p.dm_recovery_until = p.dm_recovery_paused_until = 0.0
        p.dm_recovery_hp_frac = p.dm_recovery_armor_frac = 0.0

    def _tick_deathmatch_orbs(self, dt: float) -> None:
        living = [p for p in self.players.values() if p.alive and not p.dummy and not p.dm_ghost and not p.duel_id]
        self._tick_deathmatch_recovery(dt, living)
        ultimate = self.deathmatch_rules["ultimate_orbs"]
        if self.time >= self.dm_next_ultimate_wave:
            interval = ultimate["interval"]
            waves = int((self.time - self.dm_next_ultimate_wave) // interval) + 1
            self.dm_next_ultimate_wave += waves * interval
            self.orbs = self.dm_ultimate_anchors.copy()
        for point in self.orbs[:]:
            collector = min((p for p in living if self._deathmatch_orb_in_reach(p, point, PICKUP_RANGE)),
                            key=lambda p: (p.pos - point).length(), default=None)
            if collector is not None:
                self.orbs.remove(point)
                self.effects.append(Effect("tdm_ultimate", collector.pid, collector.team, point,
                                           self.time + ultimate["duration"], ultimate["radius"], start=self.time))
        for zone in self.effects:
            if (zone.kind not in ("tdm_recovery", "tdm_ultimate")
                    or zone.props.get("ended") or not zone.start <= self.time < zone.until):
                continue
            recipients = zone.data.setdefault("recipients", set())
            for p in living:
                if (p.team != zone.team or p.pid in recipients
                        or not self._deathmatch_orb_in_reach(p, zone.pos, zone.radius)):
                    continue
                recipients.add(p.pid)
                if zone.kind == "tdm_recovery":
                    p.dm_recovery_until = max(p.dm_recovery_until, zone.until)
                else:
                    p.ult_points = min(self.ultimate_cost(p), p.ult_points + ultimate["points"])

    def _tick_deathmatch_recovery(self, dt: float, living: list[PlayerState]) -> None:
        rules = self.deathmatch_rules["recovery_orbs"]
        duration = rules["duration"]
        caps = {p.pid: self.armor[p.armor_key].points if p.armor_key in self.armor else 0 for p in living}
        for p in living:
            cap = caps[p.pid]
            elapsed = min(self.time, p.dm_recovery_until) - max(self.time - dt, p.dm_recovery_paused_until)
            if elapsed > 0:
                if p.hp < self._hp:
                    hp = p.dm_recovery_hp_frac + self._hp * elapsed / duration
                    whole = int(hp + 1e-8)
                    p.hp = min(self._hp, p.hp + whole)
                    p.dm_recovery_hp_frac = max(0.0, hp - whole)
                if p.armor < cap:
                    armor = p.dm_recovery_armor_frac + cap * elapsed / duration
                    whole = int(armor + 1e-8)
                    p.armor = min(cap, p.armor + whole)
                    p.dm_recovery_armor_frac = max(0.0, armor - whole)
            if self.time >= p.dm_recovery_until:
                p.dm_recovery_hp_frac = p.dm_recovery_armor_frac = 0.0
            else:
                if p.hp >= self._hp:
                    p.dm_recovery_hp_frac = 0.0
                if p.armor >= cap:
                    p.dm_recovery_armor_frac = 0.0

        for point in self.recovery_orbs:
            collector = min((p for p in living if (p.hp < self._hp or p.armor < caps[p.pid])
                             and self._deathmatch_orb_in_reach(p, point, PICKUP_RANGE)),
                            key=lambda p: (p.pos - point).length(), default=None)
            if collector is None:
                continue
            self.dm_recovery_orbs[point] = self.time + rules["respawn"]
            self.effects.append(Effect("tdm_recovery", collector.pid, collector.team, point, self.time + duration,
                                       rules["radius"], start=self.time))

    def _deathmatch_orb_in_reach(self, p: PlayerState, point: Vec, radius: float) -> bool:
        feet = (p.ground + p.z) / float(self._mv["level_height"])
        ground = self.world.ground_height(point)
        return ((p.pos - point).length() <= radius
                and abs(feet - ground) <= 0.75
                and not self.world.deck_blocks(p.pos, feet, point, ground)
                and self._deathmatch_pickup_path_clear(p.pos, point, feet)
                and self._line_clear(p.pos, point, p.level, ignore_effects=True))

    def _deathmatch_pickup_path_clear(self, origin: Vec, point: Vec, feet: float) -> bool:
        offset = point - origin
        distance = offset.length()
        if distance == 0:
            return True
        direction = offset * (1.0 / distance)
        reach = feet + 0.4
        return not any((w.full or w.base <= reach < w.top)
                       and (not w.on_deck or w.base <= reach) and self.wall_active(w)
                       and (hit := w.rect.ray_interval(origin, direction)) is not None
                       and hit[1] >= 0 and hit[0] < distance for w in self.combat_walls())

    def _refresh_deathmatch_stations(self) -> None:
        anchors = self._deathmatch_station_anchors
        offers = self.deathmatch_rules["station_weapons"][self.dm_stage - 1]
        self.drops = [Drop(key, mag, reserve, anchor)
                      for anchor, (key, mag, reserve) in zip(anchors, self.rng.sample(offers, len(anchors)))]

    def _discard_deathmatch_station_weapon(self, p: PlayerState) -> None:
        primary = p.weapons.get("primary")
        if primary is None or not primary.from_station:
            return
        if p.alive and not p.duel_id and p.dm_stage_equip_until:
            self._equip_deathmatch(p)
            return
        was_equipped = p.slot == "primary"
        if p.dm_stowed_primary is None:
            del p.weapons["primary"]
        else:
            p.weapons["primary"] = p.dm_stowed_primary
        p.dm_stowed_primary = None
        if was_equipped:
            if "primary" not in p.weapons or abilities.flag(self, p, "jam_primary"):
                p.slot = "sidearm"
            self._reset_deathmatch_weapon(p)

    def _deathmatch_station_in_reach(self, p: PlayerState) -> Drop | None:
        if self.phase != "live" or not p.alive or p.dm_ghost or p.duel_id:
            return None
        feet = (p.ground + p.z) / float(self._mv["level_height"])
        for drop in sorted(self.drops, key=lambda item: (item.pos - p.pos).length()):
            ground = self.drop_ground(drop)
            if ((drop.pos - p.pos).length() > PICKUP_RANGE or abs(feet - ground) > 0.75
                    or self.world.deck_blocks(p.pos, feet, drop.pos, ground)):
                continue
            if self._deathmatch_pickup_path_clear(p.pos, drop.pos, feet):
                return drop
        return None

    def _reset_deathmatch_weapon(self, p: PlayerState) -> None:
        p.reload_until = p.next_shot = 0.0
        p.burst_left = p.zoom_level = 0
        p.zoomed = p.blades_equipped = False
        p.spray = p.fire_held = 0.0
        p.equip_until = self.time + self.weapons[p.weapon.key].equip if p.weapon else self.time

    def _deathmatch_upkeep(self) -> None:
        dm = self.deathmatch_rules
        limit = dm["kill_limit"]
        if max(self.score) >= limit or self.time >= self.dm_ends_at:
            winner = max(range(2), key=self.score.__getitem__) if self.score[0] != self.score[1] else None
            self._finish_deathmatch(winner, "Kill limit" if max(self.score) >= limit else "Time limit")
            return
        reviving = {e.props["revive_pid"] for e in self.effects
                    if "revive_pid" in e.props and not e.props.get("ended") and e.until > self.time}
        for p in self.players.values():
            if (not p.alive and not p.duel_id
                    and p.pid not in reviving
                    and not (p.passive_state.get("clove_revived_round") and p.channel_until > self.time)
                    and self.time - p.died_at >= dm["respawn"]):
                self._respawn(p)

    def in_deathmatch_spawn(self, p: PlayerState) -> bool:
        if self.mode != "deathmatch" or p.duel_id:
            return False
        zone = self.world.spawn_zones.get(p.team)
        return zone is not None and zone.contains(p.pos)

    def _deathmatch_invulnerable(self, p: PlayerState) -> bool:
        return self.mode == "deathmatch" and not p.is_bot and self.cheat("invincibility")

    def deathmatch_spawn_protected(self, p: PlayerState) -> bool:
        if self.mode != "deathmatch" or self.phase != "live" or not p.alive or self.time >= p.dm_spawn_protected_until:
            return False
        return self.in_deathmatch_spawn(p)

    def _tick_deathmatch_spawn(self, p: PlayerState) -> None:
        if not p.alive or not p.dm_next_spawn_damage:
            return
        if not self.in_deathmatch_spawn(p):
            p.dm_spawn_protected_until = p.dm_next_spawn_damage = 0.0
            return
        if self.time < p.dm_next_spawn_damage:
            return
        p.dm_next_spawn_damage += math.floor(self.time - p.dm_next_spawn_damage) + 1
        if p.dm_ghost or (self.cheat("invincibility") and not p.is_bot):
            return
        damage = min(p.hp, self.deathmatch_rules["spawn_damage_per_second"])
        p.hp -= damage
        p.dm_recovery_paused_until = self.time + self.deathmatch_rules["recovery_orbs"]["damage_pause"]
        self.events.append(GameEvent("hit", self.time, {"by": None, "pid": p.pid, "dmg": damage,
                                                       "zone": "body", "source": "spawn"}))
        if p.hp <= 0:
            self._kill(None, p, "spawn", "body")

    def _respawn(self, p: PlayerState) -> None:
        """Return with the current stage loadout at the safest team spawn point."""
        side_idx = 0 if self.side(p.team) == "attack" else 1
        points = self.world.spawns.get(side_idx) or [self.world.spawn_zones.get(side_idx, Rect(0, 0, 1, 1)).center]
        active = [other for other in self.players.values()
                  if other.alive and other.pid != p.pid and not other.dummy and not other.duel_id
                  and not abilities.flag(self, other, "intangible")]
        enemies = [other.pos for other in active if other.team != p.team]
        diameter = 2 * float(self._mv["radius"])
        level_height = float(self._mv["level_height"])
        free = [point for point in points if not any(
            (point - other.pos).length() < diameter
            and abs(self.world.ground_height(point) * level_height - other.ground - other.z) <= 1.2
            for other in active
        )]
        best = max(free or points, key=lambda pt: min(((pt - e).length() for e in enemies), default=99.0))
        p.alive, p.hp = True, self._hp
        p.passive_state.pop("clove_revived_round", None)
        p.dm_spawn_protected_until = self.time + self.deathmatch_rules["spawn_protection"]
        p.dm_next_spawn_damage = p.dm_spawn_protected_until
        p.pos, p.vel, p.z, p.vz = best, Vec(0, 0), 0.0, 0.0
        floor = self.world.ground_height(best)
        p.ground = floor * level_height
        p.level = int(floor + 0.5)
        p.quiet_drop, p.quiet_landing_at = False, -99.0
        # A deployed Interceptor survives its owner's death and still needs to be activated.
        p.status = {key: until for key, until in p.status.items()
                    if key == "veto_interceptor_ready" and until > self.time}
        p.blind_until = p.revealed_until = p.overdrive_until = p.dash_until = p.immune_until = 0.0
        p.tagged_until = 0.0
        p.heal_left = p.heal_rate = p.hp_frac = p.decay_pool = p.status_drain = 0.0
        p.dash_armed_at = p.dash_armed_until = 0.0
        p.channel_until = 0.0
        p.blade_count, p.blades_equipped = 0, False
        p.repeat_shots, p.repeat_until, p.repeat_next = 0, 0.0, 0.0
        self._equip_deathmatch(p)
        self.round_damage = {pair: hit for pair, hit in self.round_damage.items() if pair[1] != p.pid}
        self.dm_recent_damage = {pair: hits for pair, hits in self.dm_recent_damage.items() if pair[1] != p.pid}
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
                    if ab.get("shared_charge"):
                        continue
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
        endgame = self._in_overtime()
        if self.round_no == half + 1 or (endgame and self.overtime):
            self.attacking_team = 1 - self.attacking_team
        pistol = self._is_pistol_round()
        swiftplay = rule("modes", "quick", {}) if self.mode == "quick" else {}
        if pistol:
            self.loss_streak = [0, 0]
        self.effects.clear()
        self.drops.clear()
        self.open_doors = {w.rect for w in self.world.walls if w.door and w.switch is not None}
        self.open_doors.update(self.world.drop_wall_links.values())
        self.door_close_at.clear()
        self.broken_cover.clear()
        self.cover_health = {w.rect: w.hp for w in self.world.walls if w.hp > 0}
        self.round_damage = {}
        self.dm_recent_damage.clear()
        self.last_alive_vs = {}
        self.orbs = self._orb_spots()
        self._first_kill_done = False
        self.round_winner = None
        self.round_reason = ""
        self.spike_pos = None
        self.spike_site = ""
        self.spike_half_defused = False
        spawn_idx = {0: 0, 1: 0}
        for p in self.players.values():
            side_idx = 0 if self.side(p.team) == "attack" else 1
            pts = self.world.spawns.get(side_idx) or [self.world.spawn_zones.get(side_idx, Rect(0, 0, 1, 1)).center]
            p.pos = pts[spawn_idx[side_idx] % len(pts)]
            spawn_idx[side_idx] += 1
            enemy_zone = self.world.spawn_zones.get(1 - side_idx)
            p.facing = angle_of(enemy_zone.center - p.pos) if enemy_zone else 0.0
            p.death_drop = None
            if pistol or endgame or not p.alive:
                p.weapons = {}
                p.armor = 0
                p.armor_key, p.armor_reserve, p.armor_regen_at = "", 0, None
            if pistol or endgame:
                p.charges = {}
                p.credits = int(self._r["overtime_credits"]) if endgame else int(self._eco["start"])
                if pistol and swiftplay:
                    ult_cost = int(self.agents[p.agent]["abilities"]["X"].get("cost", 0))
                    p.ult_points = int(swiftplay["high_cost_ult_points" if ult_cost == 9 else "half_ult_points"])
            p.weapons.pop("ability", None)
            if "sidearm" not in p.weapons:
                p.weapons["sidearm"] = self._new_weapon("classic", p)
            p.weapons["melee"] = self._new_weapon("tactical_knife", p)
            for ws in p.weapons.values():
                d = self.weapons.get(ws.key)
                if d:
                    ws.mag, ws.reserve = d.mag, d.reserve
            p.alive = True
            p.hp = self._hp
            p.vel = Vec(0, 0)
            p.z = p.vz = 0.0
            p.zipline = None
            p.quiet_drop, p.quiet_landing_at = False, -99.0
            p.ground = self.world.ground_height(p.pos)
            p.level = int(p.ground / float(self._mv["level_height"]) + 0.5)
            p.slot = "primary" if "primary" in p.weapons else "sidearm"
            p.spray = 0.0
            p.blind_until = p.revealed_until = p.overdrive_until = p.dash_until = p.immune_until = 0.0
            p.dash_armed_at = p.dash_armed_until = 0.0
            p.channel_until = 0.0
            p.blade_count, p.blades_equipped = 0, False
            p.repeat_shots, p.repeat_until, p.repeat_next = 0, 0.0, 0.0
            p.status = {}
            p.passive_state.clear()
            p.duel_id, p.duel_bounds = 0, None
            p.overheal, p.overheal_until = 0, 0.0
            p.anchor, p.anchor_until = None, 0.0
            p.heal_left = p.heal_rate = p.hp_frac = p.decay_pool = 0.0
            p.round_kills, p.purchases, p.orb_progress, p.tagged_until = 0, [], 0.0, 0.0
            p.recharge_timers = {}
            p.ability_ready_at = {}
            p.last_pos = None
            p.plant_progress = p.defuse_progress = 0.0
            p.defusing = False
            p.spike_equipped = False
            for key, ab in self.agents[p.agent]["abilities"].items():
                if key == "X" or ab.get("shared_charge"):
                    continue
                start = int(ab.get("start", 0))
                carried = p.charges.get(key, 0) - p.temporary_charges.get(key, 0)
                p.charges[key] = max(carried, start)
            p.temporary_charges.clear()
            p.sig_timer = 0.0
            p.sig_kills = 0
            p.request = ""
        attackers = [p for p in self.players.values() if self.side(p.team) == "attack"]
        self.spike_carrier = None
        self.phase = "buy"
        if attackers:
            lead = attackers[0]
            grid, _ = self._buy_areas
            zone = self.buy_spawn_zone(lead)
            candidates = (lead.pos + heading(lead.facing + offset) * distance
                          for offset in (0, -30, 30, -60, 60, -90, 90)
                          for distance in (2.5, 2.0, 1.5))
            self.spike_pos = next((point for point in candidates
                                   if (zone is None or zone.contains(point))
                                   and grid.line_free(lead.pos, point)
                                   and all((point - player.pos).length() > PICKUP_RANGE for player in attackers)),
                                  lead.pos)
            self.spike_ground = self.world.ground_height(self.spike_pos, lead.level)
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
        swiftplay = rule("modes", "quick", {}) if self.mode == "quick" else {}
        swiftpay = swiftplay.get("round_credits", ())
        round_in_half = (self.round_no - 1) % int(self._r["half_after"])
        for p in self.players.values():
            if round_in_half < len(swiftpay):
                p.credits += int(swiftpay[round_in_half])
                if round_in_half == 0 and p.team == winner_team:
                    p.credits += int(swiftplay["pistol_win_bonus"])
            elif p.team == winner_team:
                p.credits += int(self._eco["win"])
            elif survivors_paid_less and p.alive:
                p.credits += int(self._eco["survivor_loss"])  # saved instead of finishing the objective
            else:
                p.credits += int(losses[min(self.loss_streak[loser], len(losses)) - 1])
            p.credits = min(p.credits, int(self._eco["max"]))
        self._round_titles(winner_team)
        self.orbs = []
        for effect in self.effects:
            if "revive_pid" in effect.props:
                effect.props["ended"] = True
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

    def _finish_deathmatch(self, winner: int | None, reason: str) -> None:
        self.phase = "over"
        self.phase_until = self.dm_ends_at = self.time
        self.dm_timer_paused = False
        self.match_winner = self.round_winner = winner
        self.round_reason = reason
        self.events.append(GameEvent("round_end", self.time, {"winner": winner, "reason": reason, "score": list(self.score)}))

    def surrender(self, team: int) -> bool:
        """The team gives up: the match ends as a loss for it (like a successful surrender vote)."""
        if self.phase in ("lobby", "over"):
            return False
        if self.mode == "deathmatch":
            self._finish_deathmatch(1 - team, "Surrendered")
            return True
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
    def armor_owned(self, p: PlayerState, item: str) -> bool:
        """A shield only counts as full if its equipped protection and reserve are full."""
        armor = self.armor[item]
        if p.armor_key == item:
            return p.armor >= armor.points and p.armor_reserve >= armor.regen_pool
        return not p.armor_key and not armor.regen_pool and p.armor == armor.points

    def armor_available(self, p: PlayerState, item: str) -> bool:
        armor = self.armor[item]
        if self.armor_owned(p, item):
            return False
        current = self.armor.get(p.armor_key)
        if current:
            return p.armor < armor.points or current.price <= armor.price
        return p.armor < armor.points or bool(armor.regen_pool)

    def buy_spawn_zone(self, p: PlayerState) -> Rect | None:
        if self.phase == "buy" and (self.world.lock_spawn_during_buy or self.mode == "deathmatch"):
            return self.world.spawn_zones.get(0 if self.side(p.team) == "attack" else 1)
        return None

    @cached_property
    def _buy_areas(self) -> tuple[NavGrid, dict[int, set[tuple[int, int]]]]:
        # Doors can open during buy. Only the map's permanent walls and buy barriers define the areas.
        doors = frozenset(w.rect for w in self.world.walls if w.door)
        grid = NavGrid(self.world, doors, buy_phase=True)
        areas = {side: grid.connected_cells(points[0]) for side, points in self.world.spawns.items() if points}
        for area in areas.values():
            transports = [(entry, destination) for entry, destination in self.world.teleporters
                          if entry in self.world.buy_teleporters]
            while transports:
                available = [(entry, destination) for entry, destination in transports if grid.cell(entry.center) in area]
                if not available:
                    break
                for entry, destination in available:
                    transports.remove((entry, destination))
                    area.update(grid.connected_cells(destination))
        return grid, areas

    def buy_phase_allows_landing(self, p: PlayerState, point: Vec) -> bool:
        if self.phase != "buy" or self.world.lock_spawn_during_buy:
            return True
        grid, areas = self._buy_areas
        side = 0 if self.side(p.team) == "attack" else 1
        return grid.cell(point) in areas.get(side, ())

    def purchase_block_reason(self, p: PlayerState) -> str | None:
        """Why the standard armory cannot accept a transaction for this player."""
        if not p.alive:
            return "dead"
        if self.practice:
            return None
        if self.phase != "buy":
            return "phase"
        zone = self.buy_spawn_zone(p)
        return "zone" if zone is not None and not zone.contains(p.pos) else None

    def buy(self, p: PlayerState, item: str) -> bool:
        if self.mode == "deathmatch":
            if item == f"tdm:equip:{self.dm_stage}":
                if not self.deathmatch_stage_equip_left(p):
                    return False
                self._equip_deathmatch(p)
                return True
            return self._select_deathmatch_loadout(p, item)
        if self.purchase_block_reason(p) is not None:
            return False
        if item.startswith("gift:"):
            return self._gift(p, item)
        if item.startswith("sell:"):
            return self.sell(p, item[5:])
        explicit_buy = item.startswith("buy:")
        if explicit_buy:
            item = item[4:]
        item = self.charge_key(p, item)
        if item in self.ability_weapons:
            return False
        if not explicit_buy and item not in ("C", "Q", "E") and self.sellable(p, item):
            return self.sell(p, item)
        if item in self.weapons:
            d = self.weapons[item]
            previous = p.weapons.get(d.slot)
            if d.slot == "melee" or p.credits < d.price or (previous is not None and previous.key == item):
                return False
            p.credits -= d.price
            drop = None
            if previous is not None and not (d.slot == "sidearm" and previous.key == "classic"):
                drop = self._ground_weapon(p, previous, p.pos)
                self.drops.append(drop)
            new = self._new_weapon(item, p)
            p.weapons[d.slot] = new
            if p.request == item:
                p.request = ""
            p.purchases.append({"item": item, "price": d.price, "slot": d.slot, "weapon": new, "previous": previous,
                                "drop": drop})
            p.slot = d.slot
            p.equip_until = self.time + d.equip
            p.reload_until = 0.0
            p.burst_left = 0
            p.zoom_level, p.zoomed = 0, False
        elif item in self.armor:
            a = self.armor[item]
            if p.credits < a.price or not self.armor_available(p, item):
                return False
            p.credits -= a.price
            p.purchases.append({"item": item, "price": a.price,
                                "armor": (p.armor, p.armor_key, p.armor_reserve, p.armor_regen_at)})
            p.armor, p.armor_key, p.armor_reserve, p.armor_regen_at = a.points, item, a.regen_pool, None
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
        if self.purchase_block_reason(p) is not None:
            return False
        item = self.charge_key(p, item)
        for buy in reversed(p.purchases):
            if buy["item"] != item:
                continue
            if "weapon" in buy:
                return p.weapons.get(buy["slot"]) is buy["weapon"]
            if "armor" in buy:
                return p.armor_key == item and self.armor_owned(p, item)
            return p.charges.get(item, 0) > 0
        return False

    def sell(self, p: PlayerState, item: str) -> bool:
        """Takes back an item bought this buy phase: full refund; a gun that was replaced comes back if still lying there."""
        item = self.charge_key(p, item)
        if not self.sellable(p, item):
            return False
        buy = next(b for b in reversed(p.purchases) if b["item"] == item)
        p.purchases.remove(buy)
        payer = self.players.get(buy.get("payer", p.pid))
        if payer is not None:
            payer.credits = min(int(self._eco["max"]), payer.credits + int(buy["price"]))
        if "weapon" in buy:
            previous, drop = buy["previous"], buy.get("drop")
            was_equipped = p.slot == buy["slot"]
            if previous is not None and drop is not None and drop in self.drops:
                self.drops.remove(drop)
                p.weapons[buy["slot"]] = previous
                if p.request == previous.key:
                    p.request = ""
            elif buy["slot"] == "sidearm":
                p.weapons["sidearm"] = self._new_weapon("classic", p)
            else:
                p.weapons.pop(buy["slot"], None)
            if p.slot not in p.weapons:
                p.slot = next((slot for slot in SLOTS if slot in p.weapons), "melee")
            if was_equipped:
                p.reload_until = 0.0
                p.burst_left = 0
                p.zoom_level, p.zoomed = 0, False
                weapon = self._weapon_def(p)
                p.equip_until = self.time + (weapon.equip if weapon else 0.0)
        elif "armor" in buy:
            p.armor, p.armor_key, p.armor_reserve, p.armor_regen_at = buy["armor"]
        else:
            p.charges[item] = max(0, p.charges.get(item, 0) - 1)
        self.events.append(GameEvent("sell", self.time, {"pid": p.pid, "item": item}))
        return True

    def charge_key(self, p: PlayerState, slot: str) -> str:
        if slot not in ("C", "Q", "E"):
            return slot
        return self.agents[p.agent]["abilities"][slot].get("shared_charge", slot)

    def ultimate_cost(self, p: PlayerState) -> int:
        ab = self.agents.get(p.agent, {}).get("abilities", {}).get("X", {})
        cost = int(ab.get("cost", 99))
        if self.mode == "deathmatch":
            return self.deathmatch_rules["ultimate_costs"].get(p.agent, cost)
        return cost

    def _loadout(self, p: PlayerState) -> int:
        """Credits worth of what a player carries (weapons and armor), for the thrifty title."""
        value = sum(self.weapons[ws.key].price for ws in p.weapons.values() if ws.key in self.weapons)
        equipped = self.armor.get(p.armor_key)
        armor = equipped.price if equipped and (p.armor or p.armor_reserve) else max(
            (a.price for a in self.armor.values() if not a.regen_pool and a.points <= p.armor), default=0)
        return value + armor

    def _gift(self, buyer: PlayerState, item: str) -> bool:
        """Buy a primary weapon for a teammate; their old one drops at their feet."""
        try:
            _, pid_text, revision, key = item.split(":", 3)
            target = self.players[int(pid_text)]
        except (ValueError, KeyError):
            return False
        d = self.weapons.get(key)
        if d is None or d.slot != "primary" or target.team != buyer.team or not target.alive or buyer.credits < d.price \
                or target.pid == buyer.pid or target.request != key or revision != str(target.request_revision):
            return False
        old = target.weapons.get("primary")
        if old is not None and old.key == key:
            return False
        buyer.credits -= d.price
        drop = None
        if old is not None:
            drop = self._ground_weapon(target, old, target.pos)
            self.drops.append(drop)
        new = self._new_weapon(key, target)
        target.weapons["primary"] = new
        target.purchases.append({"item": key, "price": d.price, "slot": "primary", "weapon": new,
                                 "previous": old, "drop": drop, "payer": buyer.pid})
        target.slot, target.equip_until = "primary", self.time + d.equip
        target.reload_until = 0.0
        target.burst_left = 0
        target.zoom_level, target.zoomed = 0, False
        target.request = ""
        self.events.append(GameEvent("buy", self.time, {"pid": buyer.pid, "item": key, "for": target.pid}))
        return True

    def _new_weapon(self, key: str, player: PlayerState | None = None) -> WeaponState:
        d = self.weapons.get(key)
        skin = player.weapon_skins.get(key, "") if player else ""
        return WeaponState(key, d.mag if d else 0, d.reserve if d else 0, skin)

    # ------------------------------------------------------------------ Tick
    def tick(self, dt: float, commands: dict[int, Command]) -> list[GameEvent]:
        self.events = []
        if self.phase in ("lobby", "over"):
            return self.events
        dt = max(0.0, min(dt, 0.1))
        self.time += dt
        if self.mode == "deathmatch" and self.dm_timer_paused:
            self.phase_until += dt
            self.dm_ends_at += dt
            if self.phase == "buy":
                self.dm_next_ultimate_wave += dt
                for point in self.dm_recovery_orbs:
                    self.dm_recovery_orbs[point] += dt
        if self.mode == "deathmatch" and self.phase == "live" and self.time >= self.dm_ends_at:
            self._deathmatch_upkeep()
            return self.events
        if self.mode == "deathmatch" and self.time >= self.phase_until:
            stage_times = self.deathmatch_rules["stage_times"]
            if self.phase == "buy":
                self.phase = "live"
                self.phase_until += stage_times[0]
                self._refresh_deathmatch_stations()
            elif self.dm_stage < len(stage_times):
                self.dm_stage += 1
                if self.dm_stage == len(stage_times):
                    self.phase_until = self.dm_ends_at
                else:
                    self.phase_until += stage_times[self.dm_stage - 1]
                self._refresh_deathmatch_stations()
                for p in self.players.values():
                    p.dm_stage_equip_until = self.time + self.deathmatch_rules["stage_equip_window"]
            else:
                self._deathmatch_upkeep()
                return self.events
        elif self.phase == "buy" and self.time >= self.phase_until:
            for p in self.players.values():
                p.purchases = []  # selling ends with the buy phase
                p.request = ""
                if p.alive and "primary" not in p.weapons and "sidearm" not in p.weapons:
                    p.weapons["sidearm"] = self._new_weapon("classic", p)
                    p.slot = "sidearm"
            self.loadout_value = [sum(self._loadout(p) for p in self.players.values() if p.team == t) for t in (0, 1)]
            self.phase = "live"
            self.phase_until = self.time + float(self._r["round_time"])
        elif self.phase == "end" and self.time >= self.phase_until:
            self._start_round()
            return self.events
        if self.world.automatic_doors:
            self._update_automatic_doors(dt)
        if self.door_close_at:
            self._close_timed_doors()
        if self.mode != "deathmatch" and (self.phase == "buy" or self.practice):
            for pid, cmd in commands.items():
                p = self.players.get(pid)
                if p is None or not p.alive:
                    continue
                if cmd.request is not None:
                    self._set_weapon_request(p, cmd.request)
                for key in cmd.request_clicks:
                    self._set_weapon_request(p, "" if p.request == key else key)
        team_purchases: list[tuple[PlayerState, str]] = []
        defuser = self._select_defuser(commands)
        device_defuser = next((e for e in self.effects if e.data.get("defusing") and not e.props.get("ended")), None)
        for p in self.players.values():
            cmd = commands.get(p.pid, Command())
            if self.mode == "deathmatch" and not cmd.interact:
                p.prev_interact = False
            if p.alive:
                self._apply_command(p, cmd, dt, team_purchases, defuser)
                if self.mode == "deathmatch" and self.phase == "over":
                    return self.events
            elif cmd.ability and cmd.ability != p.prev_ability and self.can_cast_dead(p, cmd.ability):
                if cmd.points:
                    self._use_multi(p, cmd.ability, cmd.points)
                elif not self.agents[p.agent]["abilities"][cmd.ability].get("tactical"):
                    self._use_ability(p, cmd.ability)
            p.prev_fire = cmd.fire
            p.prev_alt = cmd.alt_fire
            p.prev_ability = cmd.ability
        for buyer, item in team_purchases:
            self.buy(buyer, item)
        for p in self.players.values():
            if p.alive:
                cmd = commands.get(p.pid)
                hold_jump = cmd is not None and cmd.jump and not p.passive_state.get("revive_jump_wait_for_release")
                self._physics(p, dt, hold_jump=hold_jump, climb=cmd.move_y if cmd else 0.0)
                if self.mode == "deathmatch" and self.phase == "live":
                    self._tick_deathmatch_spawn(p)
        self.spike_player_defuser_at_tick_start = defuser
        self.spike_player_defuser = (self.players[defuser], commands[defuser]) if defuser is not None else None
        self.spike_device_defuser_at_tick_start = device_defuser
        try:
            self._tick_effects(dt)
        finally:
            self.spike_player_defuser = None
            self.spike_player_defuser_at_tick_start = None
            self.spike_device_defuser_at_tick_start = None
        if self.mode == "deathmatch" and self.phase == "over":
            return self.events
        if self.phase in ("buy", "live", "planted"):
            for agent in {p.agent for p in self.players.values()}:
                if match_tick := MATCH_TICKS.get(agent):
                    match_tick(self, commands, dt)
        if self.mode == "deathmatch" and self.phase == "live":
            self._tick_deathmatch_orbs(dt)
        self._tick_spike(dt, commands, defuser)
        for p in self.players.values():
            if p.alive and p.armor_reserve and p.armor_regen_at is not None and p.armor_regen_at <= self.time:
                p.armor_regen_at = None
                armor = self.armor.get(p.armor_key)
                if armor is not None:
                    restored = min(p.armor_reserve, max(0, armor.points - p.armor))
                    p.armor += restored
                    p.armor_reserve -= restored
        self._check_round()
        if self.phase == "planted" or (self.phase == "live" and self.mode != "deathmatch" and not self.practice):
            from gameplay.kit.engine import finish_round_resurrections
            finish_round_resurrections(self)
        return self.events

    def _set_weapon_request(self, p: PlayerState, key: str) -> None:
        weapon = self.weapons.get(key)
        owned = p.weapons.get("primary")
        if key and (not weapon or weapon.slot != "primary" or key in self.ability_weapons
                    or (owned is not None and owned.key == key)):
            return
        if p.request != key:
            p.request = key
            p.request_revision += 1

    def can_cast_dead(self, p: PlayerState, key: str) -> bool:
        ab = self.agents[p.agent]["abilities"].get(key, {})
        if p.alive or p.duel_id or self.phase not in ("live", "planted"):
            return False
        if not ab.get("cast_while_dead") or p.channel_until > self.time:
            return False
        if key == "X":
            if self.mode == "deathmatch" and any(
                e.props.get("revive_pid") == p.pid and not e.props.get("ended") for e in self.effects
            ):
                return False
            return (not p.passive_state.get("clove_revived_round") and self.time - p.died_at <= 5
                    and (p.ult_points >= self.ultimate_cost(p) or self.cheat("infinite_abilities")))
        return True

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
        att = [p for p in self.players.values() if self.side(p.team) == "attack" and p.alive
               and not abilities.flag(self, p, "downed")]
        dfn = [p for p in self.players.values() if self.side(p.team) == "defense" and p.alive
               and not abilities.flag(self, p, "downed")]
        for p in self.players.values():
            if p.alive and abilities.flag(self, p, "downed") and not (att if self.side(p.team) == "attack" else dfn):
                self._kill(None, p, "downed", "body")
        has_att = any(self.side(p.team) == "attack" for p in self.players.values())
        has_dfn = any(self.side(p.team) == "defense" for p in self.players.values())
        defense_team = 1 - self.attacking_team
        if any(p.duel_id for p in self.players.values()) and (not att or not dfn):
            if self.phase == "planted" or self.time < self.phase_until:
                return
        if (not att or not dfn) and (self.phase == "planted" or self.time < self.phase_until):
            pending = [p for p in self.players.values() if p.agent == "clove" and not p.alive
                       and (self.can_cast_dead(p, "X") or p.channel_until > self.time)]
            if ((not att and self.phase == "live" and any(self.side(p.team) == "attack" for p in pending))
                    or (not dfn and any(self.side(p.team) == "defense" for p in pending))):
                return
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
    def _apply_command(self, p: PlayerState, cmd: Command, dt: float,
                       team_purchases: list[tuple[PlayerState, str]], defuser: int | None) -> None:
        if p.repeat_shots and p.repeat_until <= self.time:
            p.repeat_shots = 0
            ultimate = self.agents[p.agent]["abilities"].get("X", {})
            self._recover_after_repeat(p, ultimate)
        if "tdm:toggle_ghost" in cmd.buy:
            self._toggle_deathmatch_ghost(p)
        if p.dm_ghost:
            if cmd.facing is not None:
                p.facing = cmd.facing % 360.0
            wish = Vec(cmd.move_x, cmd.move_y)
            p.vel = (wish.normalized() if wish.length() > 1 else wish).rotated(p.facing) * self._max_speed(p)
            p.crouching = cmd.crouch
            return
        if self.mode == "deathmatch" and not p.duel_id and 0 < p.dm_stage_equip_until <= self.time:
            self._equip_deathmatch(p, keep_station=True)
        if self.in_deathmatch_spawn(p):
            p.burst_left = 0
            if cmd.ability or cmd.fire or cmd.alt_fire:
                cmd = replace(cmd, ability=None, fire=False, alt_fire=False)
        revive_recovery = abilities.has(self, p, "sage_revive_recovery")
        if not cmd.interact:
            p.passive_state.pop("revive_interact_wait_for_release", None)
        elif revive_recovery:
            p.passive_state["revive_interact_wait_for_release"] = True
        if not cmd.use_spike:
            p.passive_state.pop("revive_use_spike_wait_for_release", None)
        elif revive_recovery:
            p.passive_state["revive_use_spike_wait_for_release"] = True
        if not cmd.fire:
            p.passive_state.pop("revive_fire_wait_for_release", None)
        elif revive_recovery:
            p.passive_state["revive_fire_wait_for_release"] = True
        if p.passive_state.get("revive_fire_wait_for_release"):
            cmd = replace(cmd, fire=False)
        if not cmd.alt_fire:
            p.passive_state.pop("revive_alt_fire_wait_for_release", None)
        elif revive_recovery:
            p.passive_state["revive_alt_fire_wait_for_release"] = True
        if p.passive_state.get("revive_alt_fire_wait_for_release"):
            cmd = replace(cmd, alt_fire=False)
        if not cmd.jump:
            p.passive_state.pop("revive_jump_wait_for_release", None)
        elif revive_recovery:
            p.passive_state["revive_jump_wait_for_release"] = True
        if p.passive_state.get("revive_jump_wait_for_release"):
            cmd = replace(cmd, jump=False)
        if revive_recovery:
            cmd = replace(cmd, slot=None, reload=False, drop=False, crouch=False, equipment_actions=[])
        if abilities.flag(self, p, "no_interact"):
            cmd = replace(cmd, interact=False, use_spike=False, slot=None, drop=False,
                          equipment_actions=[action for action in cmd.equipment_actions if action == "reload"])
        if abilities.flag(self, p, "forced_crouch"):
            cmd = replace(cmd, crouch=True, jump=False)
            if cmd.interact:
                cmd = replace(cmd, interact=False, fire=False, alt_fire=False, ability=None, reload=False,
                              use_spike=False, equipment_actions=[])
        if command_filter := COMMAND_FILTERS.get(p.agent):
            cmd = command_filter(self, p, cmd, dt)
            if cmd is None:
                return
        if cmd.facing is not None:
            p.facing = cmd.facing % 360.0
        p.cursor_depth = max(0.0, min(cmd.cursor_depth, 120.0))
        p.walking, p.crouching = cmd.walk, cmd.crouch
        for item in cmd.buy:
            if item.startswith("gift:"):
                team_purchases.append((p, item))
            else:
                self.buy(p, item)
        if cmd.ability and not cmd.slot:
            p.spike_equipped = False
        plant_input = self._spike_plant_requested(p, cmd)
        holding_objective = (p.pid == defuser and self._spike_use_requested(p, cmd)
                             or p.plant_progress > 0 and plant_input)
        if not holding_objective and plant_input \
                and p.zipline is None and p.z <= 0.001 and p.channel_until <= self.time:
            holding_objective = (
                self.phase == "live" and self.spike_carrier == p.pid
                and self.world.site_at(p.pos, p.level) is not None
            )
        for action in cmd.ordered_equipment():
            if action == "drop":
                if not holding_objective:
                    self._drop(p)
            elif action == "reload":
                if cmd.reload and not (holding_objective or p.spike_equipped or p.blades_equipped) \
                        and not abilities.flag(self, p, "no_fire"):
                    self._start_reload(p)
            else:
                self._select_equipment(p, action)
        d_now = self._weapon_def(p)
        if d_now is None or p.spike_equipped or p.blades_equipped or p.reload_until > self.time or self.time < p.equip_until:
            p.zoom_level = 0
        else:
            p.zoom_level = d_now.zoom_after(p.zoom_level, cmd.alt_fire, p.prev_alt)
        p.zoomed = p.zoom_level > 0
        busy = holding_objective or p.channel_until > max(0.0, self.time - dt)
        # movement
        speed = self._max_speed(p)
        wish = Vec(cmd.move_x, cmd.move_y)
        if wish.length() > 1:
            wish = wish.normalized()
        if busy:
            wish = Vec(0, 0)
        world_wish = wish.rotated(p.facing) * speed  # forward = facing
        if holding_objective:
            p.vel = Vec(0, 0)
        elif self.time < p.dash_until:
            p.vel = p.dash_vel * abilities.mult(self, p, "dash_speed")
        else:
            diff = world_wish - p.vel
            rate = self._mv["accel"] if wish.length() > 0 else self._mv["decel"]
            step = rate * dt
            p.vel = world_wish if diff.length() <= step else p.vel + diff.normalized() * step
        if cmd.jump and p.zipline is not None:
            self._leave_zipline(p)
        elif cmd.jump and not busy and speed > 0 and p.z <= 0.001 and p.vz == 0:
            p.vz = float(self._mv["jump_velocity"])
            self.events.append(GameEvent("jump", self.time, {"pid": p.pid, "pos": (p.pos.x, p.pos.y)}))
        # ability (only on a new key press)
        if (cmd.ability and cmd.ability != p.prev_ability and self.phase in ("buy", "live", "planted")
                and not (self.mode == "deathmatch" and self.phase == "buy")):
            if cmd.points:
                self._use_multi(p, cmd.ability, cmd.points, alt=cmd.ability_alt, target_lift=cmd.target_lift)
            else:
                ab = self.agents[p.agent]["abilities"].get(cmd.ability, {})
                if (p.is_bot or p.channel_until > self.time or not ab.get("tactical")
                        or (ab.get("instant_with_status") and abilities.has(self, p, ab["instant_with_status"]))):
                    self._use_ability(p, cmd.ability, cmd.ability_alt, bounces=cmd.bounces)
        # shooting
        if not holding_objective and self.time >= p.reload_until > 0:
            self._finish_reload(p)
        if self.phase in ("live", "planted") and not (busy or p.plant_progress > 0 or p.defusing or p.spike_equipped or holding_objective) \
                and not p.repeat_shots and not self.in_deathmatch_spawn(p) \
                and not abilities.flag(self, p, "no_fire"):
            self._handle_fire(p, cmd)
        if self.mode == "deathmatch" and self.phase == "over":
            return
        if not revive_recovery:
            self._pickup(p, cmd)
            if self.mode != "deathmatch" and not p.passive_state.get("revive_interact_wait_for_release"):
                self._orb_pickup(p, cmd, dt)
        else:
            p.prev_interact = cmd.interact
            p.orb_progress = 0.0
        recovery = self._weapon_def(p).spray_recovery if self._weapon_def(p) else 5.0
        if not cmd.fire:
            p.spray = max(0.0, p.spray - recovery * dt * abilities.mult(self, p, "recovery"))
            p.fire_held = 0.0
        else:
            p.fire_held += dt

    def wall_active(self, w: Wall, for_sight: bool = False) -> bool:
        """False for open doors, spawn barriers outside the buy phase, and (unless for sight) bushes."""
        if not w.solid and not for_sight:
            return False
        if w.buy_phase_only and self.phase != "buy":
            return False
        return w.rect not in self.broken_cover and not (w.door and w.rect in self.open_doors)

    def active_sight_walls(self, level: int) -> list[Wall]:
        return [w for w in self.combat_walls() if w.blocks_sight and w.top > level and not w.low
                and (not w.on_deck or w.base <= level)
                and self.wall_active(w, for_sight=True)]

    def ability_walls(self) -> list[Wall]:
        return [e.props["barrier"] for e in self.effects if "barrier" in e.props
                and not e.props.get("ended") and e.start <= self.time < e.until]

    def combat_walls(self) -> list[Wall]:
        barriers = self.ability_walls()
        return self.world.walls + barriers if barriers else self.world.walls

    def interactable_door(self, p: PlayerState, aimed_at: Vec | None = None) -> Wall | None:
        """Return the door that can currently be toggled by this player."""
        if self.phase not in ("live", "planted"):
            return None
        best, best_d = None, DOOR_RANGE + self.agents[p.agent].get("interact_bonus", 0)
        for w in self.world.walls:
            if not w.door or w.rect in self.broken_cover:
                continue
            if w.rect in self.world.automatic_doors or w.rect in self.world.drop_wall_links.values():
                continue
            if w.rect in self.door_close_at:
                continue
            if aimed_at is not None and (w.switch is None or (w.switch - aimed_at).length() > 0.35):
                continue
            if not w.reopenable and w.rect not in self.open_doors:
                continue
            if w.switch is None:
                dx = max(w.rect.x0 - p.pos.x, 0.0, p.pos.x - w.rect.x1)
                dy = max(w.rect.y0 - p.pos.y, 0.0, p.pos.y - w.rect.y1)
                d = (dx * dx + dy * dy) ** 0.5
            else:
                d = (w.switch - p.pos).length()
                if d < best_d and not self._line_clear(p.pos, w.switch, p.level, ignore_effects=True):
                    continue
            if d < best_d:
                best, best_d = w, d
        if (best is not None and best.rect in self.open_doors and best.switch is not None
                and any(t.alive and best.rect.circle_push(t.pos, float(self._mv["radius"])) is not None
                        for t in self.players.values())):
            return None
        return best

    def _toggle_door(self, p: PlayerState, aimed_at: Vec | None = None) -> bool:
        best = self.interactable_door(p, aimed_at)
        if best is None:
            return False
        if best.rect in self.open_doors:
            self.open_doors.discard(best.rect)
        else:
            self.open_doors.add(best.rect)
            duration = self.world.timed_doors.get(best.rect)
            if duration is not None:
                self.door_close_at[best.rect] = self.time + duration
        c = best.rect.center
        self.events.append(GameEvent("door", self.time, {"pos": (c.x, c.y), "open": best.rect in self.open_doors}))
        self.events.append(GameEvent("sound", self.time, {"pid": p.pid, "pos": (c.x, c.y), "radius": 15.0, "kind": "step"}))
        return True

    def _ground_weapon(self, p: PlayerState, weapon: WeaponState, point: Vec) -> Drop:
        level_height = float(self._mv["level_height"])
        reach = (p.ground + p.z) / level_height
        ground = self.world.ground_height(point, reach)
        return Drop(weapon.key, weapon.mag, weapon.reserve, point, weapon.skin, ground)

    def _restore_death_drop(self, p: PlayerState) -> None:
        death_drop, p.death_drop = p.death_drop, None
        if death_drop is None:
            return
        for index, drop in enumerate(self.drops):
            if drop is death_drop:
                slot = self.weapons[drop.key].slot
                p.weapons[slot] = WeaponState(drop.key, drop.mag, drop.reserve, drop.skin)
                self.drops.pop(index)
                break
        if "primary" not in p.weapons and "sidearm" not in p.weapons:
            p.weapons["sidearm"] = self._new_weapon("classic", p)
        if p.slot not in p.weapons:
            p.slot = next(slot for slot in SLOTS if slot in p.weapons)

    def _select_equipment(self, p: PlayerState, slot: str) -> None:
        if slot == "primary" and abilities.flag(self, p, "jam_primary"):
            return
        if slot == "spike" and self.spike_carrier == p.pid and self.phase in ("buy", "live"):
            if not (self.phase == "live" and p.z <= 0.001 and self.world.site_at(p.pos, p.level)):
                p.spike_equipped = True
                p.blades_equipped = False
                p.reload_until = 0.0
                p.burst_left = 0
                if p.slot == "ability":
                    self._holster_ability_weapon(p)
            return
        if slot not in p.weapons:
            return
        was_holding_spike = p.spike_equipped
        p.spike_equipped = False
        if p.blades_equipped:
            p.blades_equipped = False
            p.equip_until = self.time + 0.25
        if slot in SLOTS and (slot != p.slot or was_holding_spike):
            p.slot = slot
            d = self._weapon_def(p)
            p.equip_until = self.time + (d.equip if d else 0.5) * abilities.mult(self, p, "equip")
            p.reload_until = 0.0
            p.burst_left = 0
            p.zoom_level = 0
            self.events.append(GameEvent("equip", self.time, {"pid": p.pid, "weapon": p.weapons[slot].key}))
        if slot in SLOTS and p.repeat_shots:
            p.repeat_shots = 0
            self._recover_after_repeat(p, self.agents[p.agent]["abilities"].get("X", {}))

    def _drop(self, p: PlayerState) -> None:
        if p.blades_equipped or p.channel_until > self.time or abilities.has(self, p, "raze_showstopper"):
            return
        if self.mode == "deathmatch":
            if self.phase == "live" and p.weapon and p.weapon.from_station:
                self._discard_deathmatch_station_weapon(p)
            return
        if p.spike_equipped and self.spike_carrier == p.pid and self.phase in ("buy", "live"):
            self._select_equipment(p, p.slot)
            p.spike_equipped = False  # also clear it if no weapon remains in the selected slot
            self.spike_carrier = None
            self.spike_pos = self._manual_drop_point(p)
            self.spike_ground = self.world.ground_height(self.spike_pos, p.level)
            p.dropped_at = self.time
            self.events.append(GameEvent("drop", self.time, {"pid": p.pid, "item": "bomb"}))
            return
        ws = p.weapon
        if ws is None or p.slot in ("melee", "ability"):
            return
        point = self._manual_drop_point(p)
        if self.world.drop_recovery(point) is None:
            self.drops.append(self._ground_weapon(p, ws, point))
        del p.weapons[p.slot]
        p.slot = next((slot for slot in SLOTS if slot in p.weapons), "melee")
        p.reload_until = 0.0
        p.burst_left = 0
        p.zoom_level, p.zoomed = 0, False
        weapon = self._weapon_def(p)
        p.equip_until = self.time + (weapon.equip * abilities.mult(self, p, "equip") if weapon else 0.0)
        p.dropped_at = self.time
        self.events.append(GameEvent("drop", self.time, {"pid": p.pid, "item": ws.key}))

    def _manual_drop_point(self, p: PlayerState) -> Vec:
        point = p.pos + heading(p.facing)
        if not (0 < point.x < self.world.width and 0 < point.y < self.world.height):
            return p.pos
        return point if self._line_clear(p.pos, point, p.level, ignore_effects=True, solid_only=True) else p.pos

    def drop_ground(self, drop: Drop) -> float:
        return drop.ground if drop.ground is not None else self.world.ground_height(drop.pos)

    def drop_in_reach(self, p: PlayerState, drop: Drop) -> bool:
        feet = (p.ground + p.z) / float(self._mv["level_height"])
        ground = self.drop_ground(drop)
        return ((drop.pos - p.pos).length() <= PICKUP_RANGE + self.agents[p.agent].get("interact_bonus", 0)
                and abs(feet - ground) <= 0.75
                and not self.world.deck_blocks(p.pos, feet, drop.pos, ground)
                and self._line_clear(p.pos, drop.pos, p.level, ignore_effects=True, solid_only=True))

    def _pickup(self, p: PlayerState, cmd: Command) -> None:
        """Empty slot: pick up automatically. F (when not planting or defusing): swap."""
        if p.duel_id:
            return
        pressed = cmd.interact and not p.prev_interact
        p.prev_interact = cmd.interact
        busy_with_bomb = self.spike_carrier == p.pid and self.world.site_at(p.pos, p.level) is not None
        defusing = self.phase == "planted" and self.side(p.team) == "defense" and self._can_reach_planted_spike(p)
        if pressed and self.phase in ("live", "planted") and (p.zipline is not None or not (busy_with_bomb or defusing)):
            if self._interact_zipline(p):
                return
        if pressed and self.phase in ("buy", "live", "planted") and not (busy_with_bomb or defusing) \
                and not abilities.flag(self, p, "no_abilities"):
            from gameplay.kit.engine import activate_device, aimed_device, remove_device
            device = aimed_device(self, p, p.cursor_depth)
            if device is not None:
                if device.props.get("manual"):
                    if not self.in_deathmatch_spawn(p):
                        activate_device(self, device)
                        return
                else:
                    remove_device(self, device, "recall")
                    return
        if self.mode == "deathmatch":
            if not pressed or self.phase != "live":
                return
            drop = self._deathmatch_station_in_reach(p)
            if drop is None:
                self._toggle_door(p)
                return
            primary = p.weapons.get("primary")
            if primary is None or not primary.from_station:
                p.dm_stowed_primary = primary
            p.weapons["primary"] = WeaponState(drop.key, drop.mag, drop.reserve, drop.skin, from_station=True)
            self.drops.remove(drop)
            if not abilities.flag(self, p, "jam_primary"):
                p.slot = "primary"
            if p.slot == "primary":
                self._reset_deathmatch_weapon(p)
            self.events.append(GameEvent("pickup", self.time, {"pid": p.pid, "weapon": drop.key}))
            return
        can_toggle = pressed and not (busy_with_bomb or defusing)
        aim = p.pos + heading(p.facing) * p.cursor_depth
        if can_toggle and self._toggle_door(p, aimed_at=aim):
            return
        nearby = [drop for drop in self.drops if (drop.pos - p.pos).length() <= PICKUP_RANGE + self.agents[p.agent].get("interact_bonus", 0)]
        target = aim if can_toggle else p.pos
        nearby.sort(key=lambda drop: ((drop.pos - target).length(), (drop.pos - p.pos).length()))
        for drop in nearby:
            if not self.drop_in_reach(p, drop):
                continue
            if not pressed and self.time - p.dropped_at < 1.0:
                continue
            d = self.weapons.get(drop.key)
            if not d:
                continue
            if d.slot not in p.weapons or (pressed and not (busy_with_bomb or defusing)):
                old = p.weapons.get(d.slot)
                p.weapons[d.slot] = WeaponState(drop.key, drop.mag, drop.reserve, drop.skin)
                if p.request == drop.key:
                    p.request = ""
                self.drops.remove(drop)
                if old:
                    self.drops.append(self._ground_weapon(p, old, p.pos))
                if d.slot != "primary" or not abilities.flag(self, p, "jam_primary"):
                    p.slot = d.slot
                if not (busy_with_bomb or defusing):
                    p.spike_equipped = False
                p.equip_until = self.time + d.equip * abilities.mult(self, p, "equip")
                p.reload_until = 0.0
                p.burst_left = 0
                p.zoom_level = 0
                p.zoomed = False
                self.events.append(GameEvent("pickup", self.time, {"pid": p.pid, "weapon": drop.key}))
                return
        if can_toggle:
            self._toggle_door(p)

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
        if p.dm_ghost:
            return float(self._mv["run_speed"])
        if p.zipline is not None:
            speed = self.world.ziplines[p.zipline].speed
            return speed * abilities.speed_factor(self, p)
        if (override := abilities.lowest(self, p, "move_speed")) is not None:
            return override
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
        factor = abilities.speed_factor(self, p)
        if p.z > 0.001 and abilities.has(self, p, "neon_sprint"):
            factor /= 1.35
        return s * factor

    def _landing(self, p: PlayerState, speed: float) -> None:
        """Fall damage above a safe landing speed (config/rules/ "fall"); never from ordinary jumps."""
        if p.quiet_drop and (p.walking or p.crouching) and any(zone.contains(p.pos) for zone in self.world.quiet_landings):
            p.quiet_landing_at = self.time
        if p.alive:
            self.events.append(GameEvent("land", self.time, {
                "pid": p.pid, "pos": (p.pos.x, p.pos.y), "quiet": p.quiet_landing_at == self.time,
            }))
        p.quiet_drop = False
        if p.passive_state.pop("waylay_protected_landing", False):
            return
        safe = float(rule("fall", "safe_speed", 7.0))
        if (speed <= safe or not p.alive or abilities.flag(self, p, "intangible")
                or self.deathmatch_spawn_protected(p)
                or (self.mode == "deathmatch" and self.phase != "live")
                or (self.cheat("invincibility") and not p.is_bot)):
            return
        dmg = min(int(rule("fall", "max_damage", 60)), int((speed - safe) * float(rule("fall", "damage_per_speed", 15.0))))
        if dmg > 0:
            p.hp -= dmg  # armour does not absorb falls
            if self.mode == "deathmatch":
                p.dm_recovery_paused_until = self.time + self.deathmatch_rules["recovery_orbs"]["damage_pause"]
            self.events.append(GameEvent("hit", self.time, {"by": None, "pid": p.pid, "dmg": dmg, "zone": "legs"}))
            if p.hp <= 0:
                self._kill(None, p, "fall", "legs")

    def _physics(self, p: PlayerState, dt: float, hold_jump: bool = False, climb: float = 0.0) -> None:
        radius = float(self._mv["radius"])
        lh = float(self._mv["level_height"])
        if abilities.has(self, p, "hush_suspended"):
            deck = self.world.deck_at(p.pos)
            ceiling = 2.0
            if deck is not None and p.level < deck.level:
                ceiling = max(0.0, deck.underside * lh - p.ground - head_height())
            p.z = min(ceiling, p.z + 7 * dt)
            p.vz = 0
            return
        if p.duel_bounds is not None:
            p.pos = self._move_against_walls(p.pos, p.pos + p.vel * dt, radius, [], p.duel_bounds)
            p.vz -= self._mv["gravity"] * dt
            p.z = max(0.0, p.z + p.vz * dt)
            if p.z == 0 and p.vz < 0:
                p.vz = 0
            return
        if p.dm_ghost:
            point = p.pos + p.vel * dt
            p.pos = Vec(max(radius, min(self.world.width - radius, point.x)),
                        max(radius, min(self.world.height - radius, point.y)))
            vertical = int(hold_jump) - int(p.crouching)
            p.z = max(-p.ground, min(12.0 - p.ground, p.z + vertical * self._max_speed(p) * dt))
            return
        if p.zipline is not None:
            cable = self.world.ziplines[p.zipline]
            axis = cable.end - cable.start
            if cable.lower is None:
                progress = cable.progress(p.pos)
                along = max(-cable.speed, min(cable.speed, p.vel.dot(axis.normalized())))
                length = axis.length()
            else:
                length = (cable.level - cable.lower) * lh
                progress = (p.ground - cable.lower * lh) / length
                along = max(-1.0, min(1.0, climb)) * self._max_speed(p)
            travel = progress + along * dt / length
            fraction = max(0.0, min(1.0, travel))
            p.pos = cable.start + axis * fraction
            level = cable.level if cable.lower is None else cable.lower + (cable.level - cable.lower) * fraction
            p.ground, p.z, p.vz = level * lh, 0.0, 0.0
            p.level = int(level + 0.5)
            if (travel <= 0.0 and along < 0.0) or (travel >= 1.0 and along > 0.0):
                self._leave_zipline(p)
            return
        zone = self.buy_spawn_zone(p)
        # vertical, relative to the ground under the player
        if abilities.has(self, p, "hush_hover"):
            p.vz = 0
        else:
            p.vz -= float(self._mv["gravity"]) * abilities.mult(self, p, "gravity") * dt
        if hold_jump and p.vz < 0 and p.z > 0 and not abilities.flag(self, p, "no_abilities"):
            drift = self.agents[p.agent].get("drift_fall_speed", 0.0)
            if drift > 0:
                p.vz = max(p.vz, -drift)
        airborne = p.z > 0.0
        p.z = max(0.0, p.z + p.vz * dt)
        deck = self.world.deck_at(p.pos) if self.world.decks else None
        if deck is not None and p.ground < deck.level * lh:
            clearance = max(0.0, deck.underside * lh - p.ground - head_height())
            if p.z > clearance:
                p.z, p.vz = clearance, min(0.0, p.vz)
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
        tether_key = "veto_tether" if abilities.has(self, p, "veto_tether") else "fade_tether"
        if abilities.has(self, p, tether_key) and (tether := p.passive_state.get(tether_key)):
            center, reach = tether
            offset = new - center
            if offset.length() > reach:
                new = center + offset.normalized() * reach
        # ground too high to step onto blocks like a wall (slide along it on the free axis)
        reach = (feet + tolerance) / lh
        if self.world.ground_height(new, reach) * lh > feet + tolerance:
            for candidate in (Vec(new.x, p.pos.y), Vec(p.pos.x, new.y), p.pos):
                if self.world.ground_height(candidate, reach) * lh <= feet + tolerance:
                    new = candidate
                    break
            else:
                new = p.pos
        for other in self.players.values():  # bodies block each other (on the same height)
            if (other.pid == p.pid or not other.alive or other.dummy or abs((other.ground + other.z) - feet) > 1.2
                    or abilities.flag(self, p, "intangible") or abilities.flag(self, other, "intangible")):
                continue
            gap = new - other.pos
            dist = gap.length()
            if 1e-6 < dist < 2 * radius:
                new = new + gap.normalized() * (2 * radius - dist) * 0.5
        walls = [w.rect for w in self.combat_walls() if (w.full or w.top > reach)
                 and (not w.on_deck or w.base <= reach) and self.wall_active(w)]
        new = self._move_against_walls(p.pos, new, radius, walls, zone)
        if dt > 0:
            speed = (new - p.pos).length() / dt
            if speed > float(self._mv["run_speed"]) * 0.7 and p.z <= 0 and int(self.time * 3) != int((self.time - dt) * 3):
                self.events.append(GameEvent("sound", self.time, {"pid": p.pid, "pos": (new.x, new.y), "radius": self._sound["run_radius"], "kind": "step"}))
            if self.time >= p.dash_until:
                p.vel = (new - p.pos) * (1.0 / dt)
        previous_pos, p.pos = p.pos, new
        # follow the ground: walk up and down ramps, fall from ledges from the current height, land on cover
        ground_new = self.world.ground_height(p.pos, reach) * lh
        if p.z <= 0.001:
            if ground_new < p.ground - step_down:
                p.z = p.ground - ground_new  # stepped off a ledge: keep the height, gravity takes over
                p.quiet_drop = (p.walking or p.crouching) and any(
                    zone.contains(new) and not zone.contains(previous_pos) for zone in self.world.quiet_landings)
        else:
            p.z = max(0.0, p.ground + p.z - ground_new)
            if p.z <= 0.0:
                self._landing(p, -p.vz)
                p.vz = 0.0
        p.ground = ground_new
        p.level = int(ground_new / lh + 0.5)
        if ground_new < 0 and p.alive and self.phase in ("live", "planted"):
            safe_edge = self.world.drop_recovery(p.pos)
            if safe_edge is not None and ground_new + p.z < self.world.ground_height(safe_edge) * lh - 1.0:
                self._kill(None, p, "fall", "legs")
                return
        deck = self.world.deck_at(p.pos) if self.world.decks else None
        if deck is not None and ground_new < deck.level * lh:
            clearance = max(0.0, deck.underside * lh - ground_new - head_height())
            if p.z > clearance:
                p.z, p.vz = clearance, min(0.0, p.vz)
        if self.world.teleporters and self.phase in ("buy", "live", "planted") and p.alive:
            self._map_teleport(p, radius, lh)

    @staticmethod
    def _move_against_walls(start: Vec, end: Vec, radius: float, walls: list[Rect], zone: Rect | None) -> Vec:
        travel = end - start
        # Keep the centre from crossing a thin wall before the circle can make contact.
        steps = max(1, math.ceil(travel.length() / (radius * 0.5))) if radius > 0 else 1
        step = travel * (1.0 / steps)
        pos = start
        for _ in range(steps):
            candidate = pos + step
            for _ in range(3):
                before = candidate
                for wall in walls:
                    push = wall.circle_push(candidate, radius)
                    if push is not None:
                        candidate = candidate + push
                if zone is not None:
                    candidate = Vec(min(max(candidate.x, zone.x0 + radius), zone.x1 - radius),
                                    min(max(candidate.y, zone.y0 + radius), zone.y1 - radius))
                if candidate == before:
                    break
            # A wall push or the buy-zone clamp can move the circle into another wall at a corner.
            if any(wall.circle_push(candidate, max(0.0, radius - 1e-6)) is not None for wall in walls):
                break
            pos = candidate
        return pos

    def zipline_endpoint_in_reach(self, p: PlayerState) -> tuple[int, Vec, float] | None:
        lh = float(self._mv["level_height"])
        for index, cable in enumerate(self.world.ziplines):
            start_level = cable.level if cable.lower is None else cable.lower
            for end, level in ((cable.start, start_level), (cable.end, cable.level)):
                if (p.pos - end).length() <= cable.reach and abs(p.ground + p.z - level * lh) <= cable.reach:
                    return index, end, level
        return None

    def _interact_zipline(self, p: PlayerState) -> bool:
        if p.zipline is not None:
            self._leave_zipline(p)
            return True
        endpoint = self.zipline_endpoint_in_reach(p)
        if endpoint is None:
            return False
        index, end, level = endpoint
        p.pos, p.zipline = end, index
        p.vel, p.z, p.vz = Vec(0, 0), 0.0, 0.0
        p.ground, p.level = level * float(self._mv["level_height"]), int(level + 0.5)
        p.dash_until = 0.0
        return True

    def _leave_zipline(self, p: PlayerState) -> None:
        cable = self.world.ziplines[p.zipline] if p.zipline is not None else None
        p.zipline = None
        lh = float(self._mv["level_height"])
        height = p.ground + p.z
        if cable is not None and cable.lower is not None:
            p.pos = cable.end if height >= cable.level * lh else cable.start
        p.ground = self.world.ground_height(p.pos, height / lh) * lh
        p.z, p.vz = max(0.0, height - p.ground), 0.0
        p.level = int(p.ground / lh + 0.5)

    def _map_teleport(self, p: PlayerState, radius: float, level_height: float) -> None:
        for entry, destination in self.world.teleporters:
            if not entry.contains(p.pos) or (self.phase == "buy" and entry not in self.world.buy_teleporters):
                continue
            if any(other is not p and other.alive and (other.pos - destination).length() < 2 * radius
                   for other in self.players.values()):
                return
            origin = p.pos
            p.pos, p.vel = destination, Vec(0, 0)
            p.z = p.vz = 0.0
            p.dash_until = 0.0
            p.ground = self.world.ground_height(destination) * level_height
            p.level = int(p.ground / level_height + 0.5)
            if self.phase != "buy":
                for point in (origin, destination):
                    self.events.append(GameEvent("sound_fx", self.time,
                                                 {"key": "ab_teleport", "pos": (point.x, point.y), "radius": 35.0}))
            return

    def _update_automatic_doors(self, dt: float) -> None:
        radius = float(self._mv["radius"])
        for wall, trigger in self.world.automatic_doors.items():
            opening = any(player.alive and (trigger.contains(player.pos)
                                           or wall.circle_push(player.pos, radius) is not None)
                          for player in self.players.values())
            if not opening:
                for effect in self.effects:
                    if (not effect.props.get("thrown") or effect.props.get("ended") or effect.a is None
                            or self.time < effect.start or self.time - dt >= effect.until):
                        continue
                    duration = effect.until - effect.start
                    if duration <= 0:
                        continue
                    path = effect.pos - effect.a
                    previous = max(0.0, (self.time - dt - effect.start) / duration)
                    current = min(1.0, (self.time - effect.start) / duration)
                    hit = trigger.ray_interval(effect.a + path * previous, path * (current - previous))
                    if hit is not None and hit[0] <= 1.0:
                        opening = True
                        break
            if opening == (wall in self.open_doors):
                continue
            if opening:
                self.open_doors.add(wall)
            else:
                self.open_doors.remove(wall)
            center = wall.center
            self.events.append(GameEvent("door", self.time, {"pos": (center.x, center.y), "open": opening}))

    def _close_timed_doors(self) -> None:
        radius = float(self._mv["radius"])
        for wall, deadline in list(self.door_close_at.items()):
            if self.time < deadline or any(p.alive and wall.circle_push(p.pos, radius) is not None
                                           for p in self.players.values()):
                continue
            self.door_close_at.pop(wall)
            self.open_doors.discard(wall)
            center = wall.center
            self.events.append(GameEvent("door", self.time, {"pos": (center.x, center.y), "open": False}))

    # ------------------------------------------------------------------ Weapons
    def _weapon_def(self, p: PlayerState) -> WeaponDef | None:
        ws = p.weapon
        return self.weapons.get(ws.key) if ws else None

    def has_infinite_reserve(self, ws: WeaponState) -> bool:
        if ws.key in self.ability_weapons:
            return False
        return self.cheat("infinite_magazines") or (self.mode == "deathmatch" and not ws.from_station)

    def _start_reload(self, p: PlayerState) -> None:
        ws, d = p.weapon, self._weapon_def(p)
        if (not ws or not d or not d.is_gun or ws.mag >= d.mag or p.reload_until > self.time
                or (ws.reserve <= 0 and not self.has_infinite_reserve(ws))):
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
        if self.has_infinite_reserve(ws):
            ws.mag = d.mag
            return
        take = min(need, ws.reserve)
        ws.mag += take
        ws.reserve -= take

    def _handle_fire(self, p: PlayerState, cmd: Command) -> None:
        if p.blades_equipped:
            self._throw_blades(p, cmd)
            return
        d, ws = self._weapon_def(p), p.weapon
        if not d or not ws:
            return
        if self.time < p.equip_until or self.time < p.reload_until or self.time < p.next_shot:
            return
        if d.slot == "primary" and abilities.flag(self, p, "jam_primary"):
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
            if p.slot == "ability":
                slot = next(key for key, ab in self.agents[p.agent]["abilities"].items()
                            if ab.get("ability_weapon") == d)
                ab = self.agents[p.agent]["abilities"][slot]
                if ab.get("weapon_charge_ammo"):
                    p.charges[slot] = max(0, p.charges.get(slot, 0) - 1)
                else:
                    p.passive_state[f"weapon_ammo:{slot}"] = ws.mag
                if ws.mag <= 0:
                    if ammo_status := ab.get("weapon_ammo_status"):
                        p.status.pop(ammo_status, None)
                    self._holster_ability_weapon(p)
                    p.equip_until = self.time + float(ab.get("weapon_empty_equip", 0.5))
        if d.alt_get("unscope_after_shot"):
            p.zoom_level, p.zoomed = 0, False
        if ws.from_station and ws.mag == 0 and ws.reserve == 0 and not self.has_infinite_reserve(ws):
            self._discard_deathmatch_station_weapon(p)

    def _throw_blades(self, p: PlayerState, cmd: Command) -> None:
        if self.time < max(p.equip_until, p.next_shot):
            return
        volley = cmd.alt_fire and not p.prev_alt
        if not volley and not (cmd.fire and not p.prev_fire):
            return
        ab = self.agents[p.agent]["abilities"]["X"]
        weapon: WeaponDef = ab["blade_weapon"]
        aim = heading(p.facing)
        p.next_shot = self.time + 1 / weapon.rate
        if volley:
            count = p.blade_count
            p.blade_count, p.blades_equipped = 0, False
            fan = float(ab["fan_degrees"])
            for i in range(count):
                offset = fan * (i / (count - 1) - 0.5) if count > 1 else 0.0
                self._trace(p, weapon, heading(p.facing + offset), aim)
                if self.mode == "deathmatch" and self.phase == "over":
                    break
        else:
            p.blade_count -= 1
            self._trace(p, weapon, aim, aim)
            p.blades_equipped = p.blade_count > 0
        if not p.blades_equipped:
            p.equip_until = self.time + weapon.equip

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
            if t.pid == p.pid or not t.alive or t.level != p.level or abilities.flag(self, t, "intangible"):
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
        else:
            walls = [(iv[0], w) for w in self.combat_walls()
                     if w.top > p.level and not w.low and w.material != PLATFORM and self.wall_active(w)
                     and (not w.on_deck or w.base <= p.level)
                     and (iv := w.rect.ray_interval(p.pos, aim)) and iv[0] <= reach]
            if walls:
                distance, wall = min(walls, key=lambda hit: hit[0])
                end = p.pos + aim * distance
                if wall.hp:
                    self._damage_cover(wall, round(damage * 2))
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
        if d.is_gun:
            sound = {"pid": p.pid, "pos": (p.pos.x, p.pos.y), "kind": "shot", "weapon": d.key,
                     "radius": self._sound["silenced_radius" if d.silenced else "shot_radius"]}
            if d.silenced:
                sound.update(shot_facing=p.facing, forward_radius=self._sound["silenced_forward_radius"],
                             forward_half_angle=self._sound["silenced_half_angle"])
            self.events.append(GameEvent("sound", self.time, sound))
        if p.spray <= 0.0:
            p.shot_index = 0
        pattern = spray_offset(d, p.shot_index) * spread_mult if pellets == 1 else 0.0
        for _ in range(pellets):
            dev = spread if pellets == 1 else max(spread, d.spread_first if not extra_spread else extra_spread)
            jitter = 0.35 if pattern else 1.0  # with a pattern, randomness only blurs it
            angle = pattern + (self.rng.uniform(-dev, dev) * jitter if dev > 0 else 0.0)
            self._trace(p, d, heading(p.facing + angle), aim)
            if self.mode == "deathmatch" and self.phase == "over":
                break
        p.spray = min(d.spray_max, p.spray + d.spray_step)
        p.shot_index += 1

    def _damage_cover(self, wall: Wall, damage: int) -> None:
        for e in self.effects:
            if e.props.get("barrier") is wall:
                e.data["hp"] = max(0, e.data["hp"] - damage)
                if e.data["hp"] == 0:
                    e.props["ended"] = True
                return
        remaining = max(0, self.cover_health.get(wall.rect, wall.hp) - damage)
        self.cover_health[wall.rect] = remaining
        if remaining == 0:
            self.broken_cover.add(wall.rect)
            drop_wall = self.world.drop_wall_links.get(wall.rect)
            if drop_wall is not None and drop_wall in self.open_doors:
                self.open_doors.remove(drop_wall)
                center = drop_wall.center
                self.events.append(GameEvent("door", self.time, {"pos": (center.x, center.y), "open": False}))
                for player in self.players.values():
                    if player.alive and drop_wall.circle_push(player.pos, float(self._mv["radius"])) is not None:
                        self._kill(None, player, "crush", "body")
                if self.phase == "live" and self.spike_pos is not None and drop_wall.contains(self.spike_pos):
                    self.spike_pos = wall.rect.center
                    self.spike_ground = self.world.ground_height(self.spike_pos)

    def break_glass(self, start: Vec, end: Vec, level: int) -> None:
        for wall in self.world.walls:
            if wall.material != "obj:ascent_glass" or not self.wall_active(wall):
                continue
            interval = wall.rect.ray_interval(start, end - start)
            if interval is not None and interval[0] <= 1:
                point = start + (end - start) * interval[0]
                if self._line_clear(start, point, level, ignore_effects=True, ignore_wall=wall):
                    self._damage_cover(wall, wall.hp)

    def _trace(self, p: PlayerState, d: WeaponDef, direction: Vec, aim: Vec) -> None:
        from gameplay.kit.engine import device_hit_points, remove_device
        from gameplay.geometry import segments_intersect

        origin = p.pos
        level_height = float(self._mv["level_height"])
        shot_height = (p.ground + p.z) / level_height
        hits: list[tuple[float, str, Any]] = []
        for w in (() if p.duel_id else self.combat_walls()):
            if (w.top <= p.level or w.low or w.movement_only or w.material == PLATFORM or not self.wall_active(w)
                    or (w.on_deck and w.base > p.level)):
                continue
            iv = w.rect.ray_interval(origin, direction)
            if iv and iv[0] <= d.range:
                hits.append((iv[0], "wall", (w, iv[1] - iv[0])))
        cursor_point = origin + aim * p.cursor_depth
        cursor_level = self.world.floor_level(cursor_point, p.level)
        for t in self.players.values():
            if t.pid == p.pid or t.duel_id != p.duel_id or not t.alive or abilities.flag(self, t, "intangible"):
                continue
            if self._deathmatch_invulnerable(t):
                continue
            if self._deck_between(p, t):
                continue
            res = resolve_zone(origin, direction, aim, p.cursor_depth, t.pos, t.level == p.level,
                               cursor_level == t.level, self.cfg.hit_zones)
            if res.zone and res.along <= d.range:
                # Compare the first contact with the body to the wall entry, just like for devices.
                half_width = self.cfg.hit_zones.body_half_width
                entry = max(0.0, res.along - math.sqrt(max(0.0, half_width ** 2 - res.lateral ** 2)))
                hits.append((entry, "player", (t, res.zone)))
        for device in self.effects:
            if device.props.get("duel_id", 0) != p.duel_id or device.props.get("ended") or self.time >= device.until:
                continue
            if (device.props.get("bullet_screen") and self.time >= device.start and device.a and device.b
                    and (device.props.get("all_heights") or abs(shot_height - device.props.get("source_level", 0)) < 2)
                    and segments_intersect(origin, origin + direction * d.range, device.a, device.b)):
                arm = device.b - device.a
                cross = direction.cross(arm)
                if abs(cross) > 1e-9:
                    distance = (device.a - origin).cross(arm) / cross
                    hits.append((distance, "screen", None))
            radius = device.props.get("hit_radius")
            if (not radius or (device.team == p.team and not device.props.get("friendly_fire"))
                    or device.props.get("ended") or self.time >= device.until
                    or (device.props.get("cancel_channel") and self.time < device.start)):
                continue
            height = device.props.get("flight_height")
            if height is None:
                if device.props.get("source_level", 0) != p.level:
                    continue
            else:
                radius_squared = radius ** 2 - ((height - shot_height) * level_height) ** 2
                if radius_squared <= 0:
                    continue
                radius = math.sqrt(radius_squared)
            for point in device_hit_points(device):
                if height is not None and self.world.deck_blocks(origin, shot_height, point, height):
                    continue
                offset = point - origin
                along, across = offset.dot(direction), abs(offset.cross(direction))
                if device.props.get("bullet_shell"):
                    if self.time >= device.start and across < radius:
                        half = math.sqrt(radius * radius - across * across)
                        hit = along - half if offset.length() >= radius else along + half
                        if 0 <= hit <= d.range:
                            hits.append((hit, "device", device))
                elif 0 < along <= d.range and across < radius:
                    hit = max(0.0, along - math.sqrt(radius * radius - across * across))
                    hits.append((hit, "device", device))
        hits.sort(key=lambda h: h[0])
        head_over = {id(pl[0]) for _, kind, pl in hits if kind == "player" and pl[1] == "head" and not pl[0].crouching}
        mult = 1.0
        end = d.range
        stopped_by = ""
        for i, (dist, kind, payload) in enumerate(hits):
            if kind == "screen":
                end, stopped_by = dist, "wall"
                break
            if kind == "wall":
                wall, thickness = payload
                if wall.hp:
                    self._damage_cover(wall, round(d.damage_at(dist, "body") * mult))
                    if not wall.blocks_sight and wall.rect in self.broken_cover:
                        continue
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
            if kind == "device":
                damage = round(d.damage_at(dist, "body") * mult)
                payload.data["hp"] -= damage
                payload.data["last_attacker"] = p.pid
                if damage > 0 and (sound := payload.props.get("hit_sound")):
                    self.events.append(GameEvent("device_hit_audio", self.time, {"pid": p.pid, "key": sound}))
                if payload.data["hp"] <= 0:
                    remove_device(self, payload, "destroy")
                end, stopped_by = dist, "device"
                break
            target, zone = payload
            dmg = int(round(d.damage_at(dist, zone) * mult))
            through = mult < 1.0
            slow = float(rule("tagging", "through_walls" if through else "slow", 0.25 if through else 0.725))
            if not self.deathmatch_spawn_protected(target):
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
        if self.mode == "deathmatch" and self.phase != "live":
            return
        if not target.alive or dmg <= 0 or self.deathmatch_spawn_protected(target) or abilities.flag(self, target, "intangible"):
            return
        if self.cheat("invincibility") and not target.is_bot:
            return
        if target.duel_id != (attacker.duel_id if attacker else 0):
            return
        if abilities.has(self, target, "veto_evolved") and source not in self.weapons:
            return
        if source not in ("spike", "fall") and abilities.has(self, target, "iso_shield"):
            target.status.pop("iso_shield", None)
            self.events.append(GameEvent("sound_fx", self.time, {"key": "cast_shield_up", "radius": 18,
                                                                 "pos": (target.pos.x, target.pos.y)}))
            return
        factor = abilities.mult(self, target, "damage_taken") * (abilities.mult(self, attacker, "damage_dealt") if attacker else 1.0)
        if factor != 1.0:
            dmg = int(round(dmg * factor))
        if dmg <= 0:
            return
        if self.mode == "deathmatch":
            target.dm_recovery_paused_until = self.time + self.deathmatch_rules["recovery_orbs"]["damage_pause"]
        overheal_absorbed = min(target.overheal, dmg)
        target.overheal -= overheal_absorbed
        dmg -= overheal_absorbed
        armor = self.armor.get(target.armor_key)
        absorb = armor.absorb if armor and armor.absorb is not None else self._absorb
        absorbed = min(target.armor, int(round(dmg * absorb)))
        target.armor -= absorbed
        if armor and target.armor_reserve and dmg > 0:
            target.armor_regen_at = self.time + armor.regen_delay
        dealt = min(dmg, max(0, target.hp + absorbed)) + overheal_absorbed
        target.hp -= dmg - absorbed
        if attacker is not None and attacker.team != target.team:
            pair = attacker.pid, target.pid
            if attacker.agent == "clove" and dealt > 0:
                attacker.passive_state.setdefault("clove_last_hit", {})[target.pid] = self.time
            entry = self.round_damage.setdefault(pair, [0, 0])
            entry[0] += dealt
            entry[1] += 1
            if self.mode == "deathmatch" and dealt > 0:
                cutoff = self.time - self.deathmatch_rules["damage_assist"]["window"]
                hits = self.dm_recent_damage.get(pair, ())
                self.dm_recent_damage[pair] = [(at, amount) for at, amount in hits if at >= cutoff]
                self.dm_recent_damage[pair].append((self.time, dealt))
            attacker.damage_total += dealt
            if zone == "head":
                attacker.headshots += 1
        self.events.append(GameEvent("hit", self.time, {"by": attacker.pid if attacker else None, "pid": target.pid,
                                                       "dmg": dmg + overheal_absorbed, "zone": zone,
                                                       "overheal": overheal_absorbed}))
        if target.hp <= 0:
            self._kill(attacker, target, source, zone)

    def _kill(self, attacker: PlayerState | None, target: PlayerState, source: str, zone: str) -> None:
        if self.mode == "deathmatch" and self.phase != "live":
            return
        from gameplay.kit.engine import return_to_marker
        if not target.duel_id and return_to_marker(self, target):
            return
        if source == "downed" and (record := target.passive_state.get("kayo_downed")):
            _, by, source, zone = record
            attacker = self.players.get(by)
        if not target.duel_id and (lethal := LETHAL_FILTERS.get(target.agent)):
            if lethal(self, attacker, target, source, zone):
                return
        if target.status.pop("veto_evolved", None) is not None:
            target.immune_until = 0
        if target.status.pop("kayo_downed", None) is not None:
            self.events.append(GameEvent("sound_fx", self.time, {
                "key": "cast_electric", "pos": (target.pos.x, target.pos.y),
                "radius": 15, "range_filtered": True,
            }))
        target.alive = False
        target.dm_ghost = False
        target.request = ""
        target.zipline = None
        target.dash_armed_at = target.dash_armed_until = 0.0
        target.blade_count, target.blades_equipped = 0, False
        target.repeat_shots, target.repeat_until, target.repeat_next = 0, 0.0, 0.0
        target.died_at = self.time
        if target.agent == "clove":
            target.channel_until = 0
            target.charges["E"] = min(1, target.charges.get("E", 0))
            target.temporary_charges["E"] = min(1, target.temporary_charges.get("E", 0))
            target.status.pop("clove_second_chance", None)
            target.status.pop("clove_phase", None)
            target.passive_state.pop("clove_duel_from", None)
        target.hp = 0
        target.overheal, target.overheal_until = 0, 0.0
        target.status.pop("empress", None)
        target.deaths += 1
        if self.mode == "deathmatch":
            target.round_kills = 0
            target.dm_healed_by.clear()
            target.dm_heal_source = None
        if self.mode != "deathmatch":
            target.ult_points += int(self._ult["per_death"])
        target.plant_progress = target.defuse_progress = 0.0
        target.defusing = False
        target.spike_equipped = False
        if self.mode == "deathmatch":
            target.dm_stage_equip_until = 0.0
            self._discard_deathmatch_station_weapon(target)
            self._clear_deathmatch_recovery(target)
            target.dm_spawn_protected_until = target.dm_next_spawn_damage = 0.0
        if self.spike_carrier == target.pid:
            self.spike_carrier = None
            self.spike_pos = target.pos
            self.spike_ground = self.world.ground_height(target.pos, target.level)
        if self.phase in ("live", "planted") and not any(
            player.alive and player.team == target.team for player in self.players.values()
        ):
            from gameplay.kit.engine import remove_device
            for effect in list(self.effects):
                owner = self.players.get(effect.owner)
                if effect.props.get("gekko_objective") and owner and owner.team == target.team:
                    remove_device(self, effect, "cancel")
        if self.mode != "deathmatch" and self.world.drop_recovery(target.pos) is None:
            for slot in ("primary", "sidearm"):
                ws = target.weapons.get(slot)
                if ws and (slot == "primary" or ws.key != "classic"):
                    target.death_drop = self._ground_weapon(target, ws, target.pos)
                    self.drops.append(target.death_drop)
                    del target.weapons[slot]
                    break
        if attacker and attacker.team != target.team:
            attacker.kills += 1
            if self.mode == "deathmatch":
                self.score[attacker.team] += 1
            attacker.round_kills += 1
            credited = set()
            for (dealer, victim), (dealt, _) in self.round_damage.items():
                helper = self.players.get(dealer)
                if victim == target.pid and dealt > 0 and helper is not None and helper.pid != attacker.pid \
                        and helper.team == attacker.team:
                    if self.mode == "deathmatch":
                        rule = self.deathmatch_rules["damage_assist"]
                        cutoff = self.time - rule["window"]
                        recent = sum(amount for at, amount in self.dm_recent_damage.get((dealer, victim), ())
                                     if at >= cutoff)
                        if dealt < rule["total"] and recent <= rule["recent"]:
                            continue
                    helper.assists += 1
                    credited.add(helper.pid)
                    self.events.append(GameEvent("assist", self.time, {"pid": helper.pid}))
            if self.mode == "deathmatch":
                window = self.deathmatch_rules["healing_assist_window"]
                for pid, ended_at in attacker.dm_healed_by.items():
                    helper = self.players.get(pid)
                    if (helper is not None and helper.team == attacker.team and pid not in credited
                            and ended_at <= self.time <= ended_at + window):
                        helper.assists += 1
                        self.events.append(GameEvent("assist", self.time, {"pid": pid}))
            if not self._first_kill_done and not self.practice:
                attacker.first_kills += 1
        if not self.practice:
            self._first_kill_done = True
        if attacker and attacker.team != target.team:
            blade = self.agents[attacker.agent]["abilities"]["X"].get("blade_weapon")
            if blade and attacker.blades_equipped and source == blade.key:
                attacker.blade_count = blade.mag
            if self.mode != "deathmatch":
                attacker.credits = min(int(self._eco["max"]), attacker.credits + int(self._eco["kill"]))
                attacker.ult_points += int(self._ult["per_kill"])
            else:
                attacker.ult_points = min(self.ultimate_cost(attacker),
                                          attacker.ult_points + self.deathmatch_rules["ultimate_per_kill"])
            ab = self.agents[attacker.agent]["abilities"].get("E", {})
            if self.mode != "deathmatch" and "kills_to_recharge" in ab:
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
        if self.mode == "deathmatch" and max(self.score) >= self.deathmatch_rules["kill_limit"]:
            self._deathmatch_upkeep()

    # ------------------------------------------------------------------ Abilities
    def smoke_target_distance(self, p: PlayerState, point: Vec, height: float) -> float:
        return math.hypot((point - p.pos).length(), height * float(self._mv["level_height"]) - p.ground - p.z)

    def valid_tactical_point(self, p: PlayerState, ab: dict[str, Any], point: Vec) -> bool:
        if not p.alive and "dead_range" in ab:
            ab = {**ab, "range": ab["dead_range"]}
        if not (0 <= point.x <= self.world.width and 0 <= point.y <= self.world.height
                and (ab.get("global_target") or (point - p.pos).length() <= float(ab["range"]) + 1e-9)):
            return False
        if ab.get("place", {}).get("settle_on_floor"):
            if self.world.drop_recovery(point) is not None:
                return False
            _, height = self.world.smoke_target_heights(point, bool(ab.get("under_deck")), float(ab.get("target_lift", 0)))
            if self.smoke_target_distance(p, point, height) > float(ab["range"]) + 1e-9:
                return False
        if ab.get("preview") == "teleport":
            from gameplay.kit.builtins import can_land
            return can_land(self, p, point)
        return True

    def _use_multi(self, p: PlayerState, key: str, points: list, *, alt: bool = False, target_lift: float = 0.0) -> None:
        """Multi-placement (multi=N): one charge per point for C/Q/E; the ultimate costs once for all of its points."""
        if self.in_deathmatch_spawn(p):
            return
        ab = self.agents[p.agent]["abilities"].get(key, {})
        limit = 1 if not p.alive else max(1, int(ab.get("multi", 1)))
        if limit == 1 and not ab.get("tactical"):
            return
        chosen = [Vec(float(x), float(y)) for x, y in points[:limit]]
        if not all(math.isfinite(q.x) and math.isfinite(q.y) for q in chosen):
            return
        if ab.get("astral_form") and len(chosen) == 1:
            from gameplay.kit.registry import Ctx, EFFECTS
            ctx = Ctx(self, p, p.team, chosen[0], p.pos, heading(p.facing), key="E")
            EFFECTS["astra_place_star"].fn(ctx, None, {"reclaim": alt})
            return
        if ab.get("tactical_line"):
            if len(chosen) != 2 or chosen[0] == chosen[1] or not self.valid_tactical_point(p, ab, chosen[0]):
                return
            if not (0 <= chosen[1].x <= self.world.width and 0 <= chosen[1].y <= self.world.height):
                return
            self._use_ability(p, key, point=chosen[0], direction=(chosen[1] - chosen[0]).normalized())
            return
        if ab.get("tactical"):
            if not all(self.valid_tactical_point(p, ab, q) for q in chosen):
                return
            chosen = list(dict.fromkeys(chosen))
        if key == "X":
            if not chosen or (p.ult_points < self.ultimate_cost(p) and not self.cheat("infinite_abilities")):
                return
            used = [q for q in chosen if self._use_ability(p, key, point=q, free=True)]
            if used and not self.cheat("infinite_abilities"):
                p.ult_points -= self.ultimate_cost(p)
            return
        for q in chosen:
            self._use_ability(p, key, point=q, alt=alt and bool(ab.get("shadow_targeting")), target_lift=target_lift)

    def _holster_ability_weapon(self, p: PlayerState) -> None:
        prior = p.passive_state.get("ability_weapon_prior", "sidearm")
        if prior == "primary" and abilities.flag(self, p, "jam_primary"):
            prior = "sidearm"
        p.slot = prior if prior in p.weapons else "sidearm"
        p.zoom_level, p.zoomed = 0, False

    def _use_ability_weapon(self, p: PlayerState, key: str, ab: dict) -> bool:
        weapon = ab["ability_weapon"]
        ammo_key = f"weapon_ammo:{key}"
        first = not ab.get("weapon_charge_ammo") and ammo_key not in p.passive_state
        if ab.get("weapon_charge_ammo"):
            ammo = p.charges.get(key, 0)
            if self.cheat("infinite_abilities"):
                ammo = max(1, ammo)
        elif first:
            if not self.cheat("infinite_abilities") and p.ult_points < self.ultimate_cost(p):
                return False
            ammo = weapon.mag
            p.passive_state[ammo_key] = ammo
            if ammo_status := ab.get("weapon_ammo_status"):
                abilities.apply_status(self, p, ammo_status, float("inf"))
            if not self.cheat("infinite_abilities"):
                p.ult_points -= self.ultimate_cost(p)
        else:
            ammo = p.passive_state[ammo_key]
        if ammo <= 0:
            return False
        if p.slot == "ability" and p.weapon and p.weapon.key == weapon.key:
            self._holster_ability_weapon(p)
            p.equip_until = self.time + (self._weapon_def(p).equip if p.weapon else 0)
            return True
        if p.slot != "ability":
            p.passive_state["ability_weapon_prior"] = p.slot
        p.slot = "ability"
        p.weapons["ability"] = WeaponState(weapon.key, ammo, 0)
        p.equip_until = self.time + (ab.get("weapon_summon_time", weapon.equip) if first else weapon.equip)
        p.reload_until = p.burst_left = 0
        p.spray = 0
        p.zoom_level, p.zoomed = 0, False
        self.events.append(GameEvent("equip", self.time, {"pid": p.pid, "weapon": weapon.key}))
        return True

    def _use_ability(self, p: PlayerState, key: str, alt: bool = False, point: Vec | None = None, free: bool = False,
                     *, target_lift: float = 0.0, direction: Vec | None = None, bounces: int = 0) -> bool:
        if self.in_deathmatch_spawn(p):
            return False
        ab = self.agents[p.agent]["abilities"].get(key)
        if ab and ab.get("max_bounces"):
            ab = {**ab, "bounces": max(0, min(ab["max_bounces"], bounces))}
        if not p.alive and not self.can_cast_dead(p, key):
            return False
        clove_phased = abilities.has(self, p, "clove_phase")
        if (ab and ab.get("requires_death") and p.alive and not clove_phased) or (clove_phased and key != "X"):
            return False
        if ab and alt and isinstance(ab.get("alt"), dict):
            ab = {**ab, **ab["alt"]}  # right-click variant: its values replace the normal ones
        if target_lift and ab and (limit := ab.get("place", {}).get("raised_target_lift")):
            ab = {**ab, "target_lift": max(0.0, min(float(limit), target_lift))}
        if ab and any(abilities.has(self, p, name) for name in ab.get("cancel_statuses", ())):
            for name in ab["cancel_statuses"]:
                p.status.pop(name, None)
            p.equip_until = self.time + float(ab.get("cancel_equip", 0.0))
            return True
        if p.channel_until > self.time and point is None:
            from gameplay.kit.engine import remove_device
            for effect in self.effects:
                if (effect.owner == p.pid and effect.props.get("key") == key
                        and effect.props.get("cancel_channel") and not effect.props.get("ended")
                        and effect.start <= self.time < effect.until):
                    remove_device(self, effect, "cancel")
                    return True
        if not ab or p.channel_until > self.time or abilities.flag(self, p, "no_abilities"):
            return False
        if ab.get("ability_weapon"):
            return self._use_ability_weapon(p, key, ab)
        armed = ab.get("arm_duration") and self.time < p.dash_armed_until
        repeating = bool(ab.get("repeat_shots") and p.repeat_shots and self.time < p.repeat_until)
        if repeating and self.time < p.repeat_next:
            return False
        if armed and self.time < p.dash_armed_at:
            return False
        blade = ab.get("blade_weapon")
        if blade and p.blade_count:
            p.blades_equipped = not p.blades_equipped
            p.equip_until = self.time + blade.equip
            p.burst_left = 0
            return True
        charge = self.charge_key(p, key)
        endless = self.cheat("infinite_abilities") or free or ab.get("always_available") or bool(armed) or repeating or (
            ab.get("free_with_status") and abilities.has(self, p, ab["free_with_status"]))
        if endless:
            pass
        elif key == "X":
            if p.ult_points < self.ultimate_cost(p):
                return False
        elif p.charges.get(charge, 0) <= 0:
            return False
        if ab.get("arm_duration") and not armed:
            p.dash_armed_at = self.time + float(ab["arm_delay"])
            p.dash_armed_until = p.dash_armed_at + float(ab["arm_duration"])
            target = p.pos
        elif blade:
            p.blade_count, p.blades_equipped = blade.mag, True
            p.reload_until, p.burst_left = 0.0, 0
            p.equip_until = self.time + blade.equip
            target = p.pos
        else:
            try:
                target = abilities.use(self, p, key, ab, point=point, direction=direction)
            except (KeyError, TypeError, ValueError) as exc:
                warnings.warn(f"Ability {ab.get('name', key)} of {p.agent} misconfigured: {exc}")
                return False
        if target is None:
            return False
        if armed:
            p.dash_armed_at = p.dash_armed_until = 0.0
        if ab.get("repeat_shots"):
            if not repeating:
                p.repeat_shots = int(ab["repeat_shots"])
                p.repeat_until = self.time + float(ab["repeat_window"])
            p.repeat_shots -= 1
            p.repeat_next = self.time + float(ab["repeat_delay"])
            if not p.repeat_shots:
                self._recover_after_repeat(p, ab)
        if endless:
            pass
        elif key == "X":
            p.ult_points -= self.ultimate_cost(p)
        else:
            p.charges[charge] -= 1
            if p.temporary_charges.get(charge, 0):
                p.temporary_charges[charge] -= 1
            else:
                for purchase in reversed(p.purchases):
                    if purchase["item"] == charge:
                        p.purchases.remove(purchase)
                        break
        self.events.append(GameEvent("ability", self.time, {"pid": p.pid, "key": key, "kind": ab["kind"], "pos": (target.x, target.y),
                                                            "sound": str(ab.get("sound", "")),
                                                            "cast_team": p.team if ab.get("cast_team_only") else None,
                                                            "cast_radius": ab.get("cast_radius", 30),
                                                            **({"cast_announcement": ab["cast_announcement"], "team": p.team}
                                                               if "cast_announcement" in ab and not repeating else {}),
                                                            "repeat_left": p.repeat_shots if ab.get("repeat_shots") else None}))
        return True

    def _recover_after_repeat(self, p: PlayerState, ab: dict) -> None:
        if recovery := float(ab.get("repeat_final_equip", 0)):
            p.equip_until = max(p.equip_until, self.time + recovery)
            p.reload_until, p.burst_left = 0.0, 0
            abilities.apply_status(self, p, "weapon_recovery", recovery)

    def _clip_to_walls(self, a: Vec, b: Vec, level: int, *, thrown: bool = False) -> Vec:
        direction = (b - a).normalized()
        dist = (b - a).length()
        best = None
        for w in self.active_sight_walls(level):
            if thrown and (trigger := self.world.automatic_doors.get(w.rect)) is not None:
                entry = trigger.ray_interval(a, direction)
                if entry is not None and entry[0] <= dist:
                    continue
            iv = w.rect.ray_interval(a, direction)
            if iv and iv[0] <= dist and (best is None or iv[0] < best):
                best = iv[0]
        if best is None:
            return b
        return a + direction * max(0.0, best - 0.3)

    def _tick_effects(self, dt: float) -> None:
        abilities.tick(self, dt)

    # ------------------------------------------------------------------ Sight
    def _line_clear(self, a: Vec, b: Vec, level: int, ignore_effects: bool = False,
                    ignore_wall: Wall | None = None, *, solid_only: bool = False) -> bool:
        direction = b - a
        dist = direction.length()
        if dist < 1e-6:
            return True
        u = direction * (1.0 / dist)
        walls = self.active_sight_walls(level)
        if solid_only:
            walls = [w for w in self.combat_walls() if w.solid and w.top > level and not w.low
                     and (not w.on_deck or w.base <= level) and self.wall_active(w)]
        for w in walls:
            if w is ignore_wall:
                continue
            iv = w.rect.ray_interval(a, u)
            if iv and iv[0] < dist:
                return False
        if ignore_effects:
            return True
        for e in self.effects:
            if e.props.get("ended") or not e.start <= self.time < e.until:
                continue
            ground = e.props.get("settled_ground")
            if ground is not None and (deck := self.world.deck_at(e.pos)):
                if (ground >= deck.level) != (level >= deck.level):
                    continue
            blocks = e.props.get("blocks_sight", e.kind in ("smoke", "wall"))
            radius = e.radius
            if e.props.get("fall"):
                radius = math.sqrt(max(0.0, radius * radius - e.fall_offset(self.time) ** 2))
            if blocks and e.a is None and radius > 0 and segment_circle_hit(a, b, e.pos, radius):
                if (a - e.pos).length() > radius or (b - e.pos).length() > radius:
                    return False
            if (blocks and e.a and e.b and e.kind != "tripwire"
                    and (not (height := e.props.get("sight_height"))
                         or e.props["source_level"] <= level < e.props["source_level"] + height)):
                from gameplay.geometry import segments_intersect
                if segments_intersect(a, b, e.a, e.b):
                    return False
        return True

    def line_of_fire(self, shooter: PlayerState, target: PlayerState) -> bool:
        """True if a bullet from the shooter's current weapon can get through to the target."""
        if self._deathmatch_invulnerable(target) or self._deck_between(shooter, target):
            return False
        d = self._weapon_def(shooter)
        pen = d.penetration if d else 0
        a, b = shooter.pos, target.pos
        dist = (b - a).length()
        if dist < 1e-6:
            return True
        u = (b - a) * (1.0 / dist)
        for w in self.combat_walls():
            if (w.top <= shooter.level or w.movement_only or w.material == PLATFORM or not self.wall_active(w)
                    or (w.on_deck and w.base > shooter.level)):
                continue
            iv = w.rect.ray_interval(a, u)
            if iv and iv[0] < dist and (w.penetration >= 3 or w.penetration > pen or iv[1] - iv[0] > 1.0 + pen):
                return False
        return True

    def _deck_between(self, a: PlayerState, b: PlayerState) -> bool:
        if not (self.world.decks or self.world.lintels):
            return False
        lh = float(self._mv["level_height"])
        eye_a = head_height() * (0.65 if a.crouching else 1.0)
        eye_b = head_height() * (0.65 if b.crouching else 1.0)
        return self.world.deck_blocks(a.pos, (a.ground + a.z + eye_a) / lh,
                                      b.pos, (b.ground + b.z + eye_b) / lh)

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

    def paranoia_warning(self, p: PlayerState) -> bool:
        if not p.alive or abilities.has(self, p, "paranoia"):
            return False
        if self.remote_paranoia_warning:
            return True
        for e in self.effects:
            if (e.owner == p.pid or e.props.get("sprite") != "omen_paranoia_travel"
                    or e.props.get("ended") or not e.start <= self.time < e.until):
                continue
            aim = Vec(*e.props["aim"])
            end = e.pos + aim * (e.until - self.time) * e.props["move"]
            if segment_circle_hit(e.pos, end, p.pos, e.radius):
                return True
        return False

    def minimap_obscured(self, p: PlayerState) -> bool:
        return self.remote_minimap_obscured or any(
            e.team != p.team and self.time < e.until and not e.props.get("ended")
            and e.props.get("sprite") == "omen_from_the_shadows"
            and (owner := self.players.get(e.owner)) is not None and owner.alive
            for e in self.effects
        )

    def shade_sight_range(self, p: PlayerState) -> float | None:
        if not abilities.has(self, p, "omen_shade"):
            return None
        shade = next((e for e in self.effects if e.owner == p.pid and e.props.get("sprite") == "omen_from_the_shadows"
                      and not e.props.get("ended") and e.start <= self.time < e.until), None)
        if shade is None:
            return None
        progress = (self.time - shade.start) / (shade.until - shade.start)
        return math.hypot(self.world.width, self.world.height) * progress ** 2

    def sight_range(self, p: PlayerState) -> float | None:
        limits = (abilities.lowest(self, p, "sight_range"), self.shade_sight_range(p))
        return min((limit for limit in limits if limit is not None), default=None)

    def can_see(self, viewer: PlayerState, target: PlayerState) -> bool:
        if not target.alive or viewer.duel_id != target.duel_id:
            return False
        if viewer.pid != target.pid and abilities.flag(self, viewer, "no_contacts"):
            return False
        if viewer.pid == target.pid or viewer.team == target.team:
            return True
        if viewer.channel_until > self.time:
            creature = next((e for e in self.effects if e.owner == viewer.pid
                             and e.props.get("sprite") in ("gekko_thrash", "skye_tiger", "sova_owl_drone", "tejo_drone")
                             and not e.props.get("ended")
                             and (e.props.get("sprite") != "sova_owl_drone" or e.start <= self.time)), None)
            if creature is not None:
                radius = {"skye_tiger": 22.5, "tejo_drone": 18}.get(creature.props["sprite"], 20)
                if creature.props["sprite"] == "sova_owl_drone":
                    radius = creature.radius
                    if creature.data.get("nearsighted_until", 0) > self.time:
                        radius = min(radius, creature.data["nearsighted_range"])
                return ((target.pos - creature.pos).length() <= radius
                        and not abilities.flag(self, target, "invisible")
                        and self._line_clear(creature.pos, target.pos, min(creature.props.get("source_level", 0), target.level)))
        if abilities.flag(self, target, "invisible"):
            return False
        shade_sight = self.shade_sight_range(viewer)
        if shade_sight is not None and (target.pos - viewer.pos).length() > shade_sight:
            return False
        if target.revealed_until > self.time:
            return True
        if self._deck_between(viewer, target):
            return False
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
    def near_spike(self, p: PlayerState, reach: float) -> bool:
        if p.zipline is not None or self.spike_pos is None or (p.pos - self.spike_pos).length() > reach:
            return False
        feet = (p.ground + p.z) / float(self._mv["level_height"])
        return (abs(feet - self.spike_ground) <= 0.75
                and not self.world.deck_blocks(p.pos, feet, self.spike_pos, self.spike_ground))

    def _can_reach_planted_spike(self, p: PlayerState) -> bool:
        return (self.spike_pos is not None and self.near_spike(p, INTERACT_RANGE)
                and self._line_clear(p.pos, self.spike_pos, p.level, ignore_effects=True, solid_only=True))

    def _spike_detonation_at(self) -> float:
        return self.spike_planted_at + float(self._spike["fuse_time"])

    def _spike_defuse_dt(self, dt: float) -> float:
        return min(dt, max(0.0, self._spike_detonation_at() - (self.time - dt)))

    def _advance_spike_defuse(self, p: PlayerState, progress: float, dt: float) -> float:
        progress += dt
        checkpoint = float(self._spike["defuse_checkpoint"])
        # Summing fractional ticks can land just below the exact checkpoint.
        if not self.spike_half_defused and progress >= checkpoint - 1e-9:
            progress = max(progress, checkpoint)
            self.spike_half_defused = True
            pos = self.spike_pos if self.spike_pos is not None else p.pos
            self.events.append(GameEvent("defuse_half", self.time, {"pid": p.pid, "pos": (pos.x, pos.y)}))
        return progress

    def _spike_use_requested(self, p: PlayerState, cmd: Command) -> bool:
        use_spike = cmd.use_spike and not p.passive_state.get("revive_use_spike_wait_for_release")
        interact = cmd.interact and not p.passive_state.get("revive_interact_wait_for_release")
        return use_spike or interact

    def _can_defuse(self, p: PlayerState, cmd: Command) -> bool:
        return (p.alive and self.side(p.team) == "defense" and self._spike_use_requested(p, cmd)
                and not (cmd.interact and abilities.flag(self, p, "forced_crouch"))
                and p.channel_until <= self.time and not abilities.flag(self, p, "no_interact")
                and p.zipline is None and p.z <= 0.001 and self._can_reach_planted_spike(p))

    def _spike_plant_requested(self, p: PlayerState, cmd: Command) -> bool:
        return self._spike_use_requested(p, cmd) or (
            p.spike_equipped and cmd.fire and not p.passive_state.get("revive_fire_wait_for_release")
        )

    def _select_defuser(self, commands: dict[int, Command]) -> int | None:
        if self.phase != "planted" or any(e.data.get("defusing") and not e.props.get("ended") for e in self.effects):
            return None
        candidates = (p for p in self.players.values() if (cmd := commands.get(p.pid)) and self._can_defuse(p, cmd))
        selected = min(candidates, key=lambda p: (not p.defusing, p.pid), default=None)
        return selected.pid if selected else None

    def _tick_spike(self, dt: float, commands: dict[int, Command], defuser: int | None) -> None:
        if self.spike_pos is not None and self.phase == "live":
            safe_edge = self.world.drop_recovery(self.spike_pos)
            if safe_edge is not None:
                self.spike_pos = safe_edge
                self.spike_ground = self.world.ground_height(safe_edge)
        if self.phase in ("buy", "live") and self.spike_carrier is None and self.spike_pos is not None:
            for p in self.players.values():
                cmd = commands.get(p.pid)
                manual = cmd and cmd.interact and not p.passive_state.get("revive_interact_wait_for_release")
                reach = (INTERACT_RANGE if manual else PICKUP_RANGE) + self.agents[p.agent].get("interact_bonus", 0)
                if (p.alive and not abilities.has(self, p, "sage_revive_recovery") and not abilities.flag(self, p, "downed")
                        and self.side(p.team) == "attack" and self.near_spike(p, reach)
                        and self.time - p.dropped_at >= 1.0
                        and self._line_clear(p.pos, self.spike_pos, p.level, ignore_effects=True, solid_only=True)):
                    self.spike_carrier = p.pid
                    self.spike_pos = None
                    break
        if self.phase == "live" and self.spike_carrier is not None:
            p = self.players[self.spike_carrier]
            cmd = commands.get(p.pid, Command())
            if cmd.interact and abilities.flag(self, p, "forced_crouch"):
                cmd = replace(cmd, interact=False, use_spike=False, fire=False)
            site = self.world.site_at(p.pos, p.level)
            if (p.alive and p.zipline is None and not abilities.flag(self, p, "no_interact") and p.channel_until <= self.time
                    and self._spike_plant_requested(p, cmd) and site and p.z <= 0.001):
                if p.plant_progress == 0.0:
                    p.reload_until = 0.0
                    p.burst_left = 0
                    p.passive_state["spike_audio"] = ("spike_plant", p.pos, self.time)
                    self.events.append(GameEvent("plant_start", self.time, {"pid": p.pid, "pos": (p.pos.x, p.pos.y)}))
                p.plant_progress += dt
                if p.plant_progress >= float(self._spike["plant_time"]):
                    self._plant(p, site.name)
            else:
                if p.plant_progress > 0.0:
                    self.events.append(GameEvent("plant_stop", self.time, {"pid": p.pid}))
                    self._reequip_after_spike_use(p)
                p.plant_progress = 0.0
        if self.phase == "planted" and self.spike_pos is not None:
            defuse_dt = self._spike_defuse_dt(dt)
            occupied = any(e.data.get("defusing") and not e.props.get("ended") for e in self.effects)
            selected = self.players.get(defuser) if defuser is not None else None
            if (not occupied and self.time < self._spike_detonation_at()
                    and (selected is None or not self._can_defuse(selected, commands.get(selected.pid, Command())))):
                defuser = self._select_defuser(commands)
                # A late handoff starts now. Time earlier in this tick belonged to the prior attempt.
                defuse_dt = 0.0
            cp = float(self._spike["defuse_checkpoint"])
            for p in self.players.values():
                if not p.alive or self.side(p.team) != "defense":
                    continue
                cmd = commands.get(p.pid, Command())
                if cmd.interact and abilities.flag(self, p, "forced_crouch"):
                    cmd = replace(cmd, interact=False, fire=False)
                if not occupied and p.pid == defuser and self._can_defuse(p, cmd):
                    if not p.defusing:
                        p.vel = Vec(0, 0)
                        p.reload_until = 0.0
                        p.burst_left = 0
                        p.defuse_progress = cp if self.spike_half_defused else 0.0
                        key = "spike_defuse_half" if self.spike_half_defused else "spike_defuse"
                        p.passive_state["spike_audio"] = (key, self.spike_pos, self.time)
                        self.events.append(GameEvent("defuse_start", self.time, {
                            "pid": p.pid, "pos": (self.spike_pos.x, self.spike_pos.y), "resumed": p.defuse_progress > 0.0,
                            "spike_pos": (self.spike_pos.x, self.spike_pos.y),
                        }))
                    p.defusing = True
                    p.defuse_progress = self._advance_spike_defuse(p, p.defuse_progress, defuse_dt)
                    if p.defuse_progress >= float(self._spike["defuse_time"]):
                        self._complete_defuse(p)
                        return
                else:
                    p.defuse_progress = cp if p.defuse_progress >= cp else 0.0
                    if p.defusing:
                        self.events.append(GameEvent("defuse_stop", self.time, {"pid": p.pid}))
                        self._reequip_after_spike_use(p)
                    p.defusing = False
            if self.time >= self._spike_detonation_at():
                for t in self.players.values():
                    if t.alive and (t.pos - self.spike_pos).length() <= float(self._spike["blast_radius"]):
                        self._kill(None, t, "spike", "body")
                self.events.append(GameEvent("explode", self.time, {"pos": (self.spike_pos.x, self.spike_pos.y)}))
                self._end_round(self.attacking_team, "Bomb detonated")

    def _complete_defuse(self, p: PlayerState) -> None:
        p.ult_points += int(self._ult["per_defuse"])
        p.defuses += 1
        self.events.append(GameEvent("defuse", self.time, {"pid": p.pid}))
        self._end_round(p.team, "Bomb defused")

    def _reequip_after_spike_use(self, p: PlayerState) -> None:
        if not p.spike_equipped and (weapon := self._weapon_def(p)) is not None:
            p.equip_until = self.time + weapon.equip * abilities.mult(self, p, "equip")
            p.reload_until = 0.0
            p.burst_left = 0

    def _plant(self, p: PlayerState, site: str, *, point: Vec | None = None, level: int | None = None) -> None:
        self.phase = "planted"
        self.spike_pos = p.pos if point is None else point
        self.spike_ground = self.world.ground_height(self.spike_pos, p.level if level is None else level)
        self.spike_site = site
        self.spike_carrier = None
        self.spike_planted_at = self.time
        self.orbs = []  # orbs vanish when the spike is planted
        if p.plant_progress > 0:
            p.spike_equipped = False
            self._reequip_after_spike_use(p)
        p.plant_progress = 0.0
        p.spike_equipped = False
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

    def sound_blocked(self, a: Vec, b: Vec) -> bool:
        from gameplay.geometry import segments_intersect
        return any(e.props.get("blocks_sound") and not e.props.get("ended") and e.start <= self.time < e.until
                   and e.a is not None and e.b is not None and segments_intersect(a, b, e.a, e.b)
                   for e in self.effects)

    def _effect_visible(self, e: Effect, viewer: PlayerState | None) -> bool:
        """Decoys are hidden; enemies only detect hidden utility within its reveal range."""
        if e.props.get("ended") or (viewer is not None and viewer.duel_id != e.props.get("duel_id", 0)):
            return False
        if e.props.get("hidden") == "team_only" and viewer is not None and viewer.team != e.team:
            return False
        if e.props.get("cancel_channel") and self.time < e.start:
            return False
        if e.props.get("owner_only") and viewer is not None and e.owner != viewer.pid:
            return False
        hidden = e.props.get("hidden", {"decoy": "all", "alarm": "enemies", "tripwire": "enemies"}.get(e.kind))
        if hidden == "all":
            return False
        if hidden == "enemies" and viewer is not None and viewer.team != e.team:
            owner = self.players.get(e.owner)
            if "owner_range" in e.props and owner is not None and (
                not owner.alive or abilities.flag(self, owner, "no_abilities")
            ):
                return True
            reach = float(e.props.get("detect_range", 0))
            from gameplay.kit.engine import device_hit_points
            return reach > 0 and any((viewer.pos - point).length() <= reach
                                     and self._line_clear(viewer.pos, point, viewer.level)
                                     for point in device_hit_points(e))
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
            if viewer is not None and viewer.duel_id != p.duel_id:
                continue
            if viewer is not None and p.pid != viewer.pid and abilities.flag(self, viewer, "no_contacts"):
                continue
            visible = viewer is None or self.can_see(viewer, p) or not p.alive
            if not visible:
                continue
            players.append({
                "pid": p.pid, "name": p.name, "team": p.team, "agent": p.agent, "bot": p.is_bot,
                "x": p.pos.x, "y": p.pos.y, "z": p.z, "level": p.level, "ground": p.ground, "facing": p.facing,
                **({"duel_id": p.duel_id, "duel_bounds": [p.duel_bounds.x0, p.duel_bounds.y0,
                                                        p.duel_bounds.x1, p.duel_bounds.y1]} if p.duel_bounds else {}),
                **({"zipline": p.zipline} if p.zipline is not None else {}),
                **({"quiet_landing_at": p.quiet_landing_at} if self.world.quiet_landings else {}),
                "alive": p.alive, "hp": p.hp, "armor": p.armor,
                "overheal": p.overheal,
                "armor_key": p.armor_key if viewer is None or viewer.team == p.team else "",
                "armor_reserve": p.armor_reserve if viewer is None or viewer.team == p.team else 0,
                "credits": p.credits if viewer is None or viewer.team == p.team else None,
                "slot": p.slot, "weapon": p.weapon.key if p.weapon else None,
                "skin": p.weapon.skin if p.weapon else "",
                "mag": p.weapon.mag if p.weapon else 0, "reserve": p.weapon.reserve if p.weapon else 0,
                "from_station": bool(p.weapon and p.weapon.from_station),
                "dm_loadout": p.dm_loadout if viewer is None or viewer.pid == p.pid else [],
                "dm_stage_equip_until": p.dm_stage_equip_until if viewer is None or viewer.pid == p.pid else 0.0,
                "dm_spawn_protected_until": p.dm_spawn_protected_until if self.deathmatch_spawn_protected(p) else 0.0,
                "dm_ghost": p.dm_ghost,
                "dm_next_spawn_damage": p.dm_next_spawn_damage if viewer is None or viewer.pid == p.pid else 0.0,
                "inventory": {slot: {"key": ws.key, "mag": ws.mag, "reserve": ws.reserve, "skin": ws.skin,
                                     "from_station": ws.from_station}
                              for slot, ws in p.weapons.items()}
                if viewer is None or viewer.pid == p.pid else {},
                "charges": dict(p.charges), "ult": p.ult_points, "kills": p.kills, "deaths": p.deaths, "assists": p.assists,
                "sellable": [b["item"] for b in p.purchases if self.sellable(p, b["item"])] if viewer is None or viewer.pid == p.pid else [],
                **({"dropped_at": p.dropped_at} if viewer is None or viewer.pid == p.pid else {}),
                "orb": p.orb_progress, "crouch": p.crouching,
                "blind": p.blind_until > self.time, "reloading": p.reload_until > self.time,
                "revealed_until": p.revealed_until if p.revealed_until > self.time else 0.0,
                "plant": p.plant_progress, "defuse": p.defuse_progress,
                "defusing": p.defusing,
                "spike_equipped": p.spike_equipped,
                "status": sorted(k for k, v in p.status.items() if v > self.time
                                 and (viewer is None or viewer.team == p.team
                                      or k in ("dismiss", "waylay_refract_transit", "raze_showstopper", "kayo_downed",
                                               "deadlock_netted", "deadlock_cocooned", "deadlock_accelerator_equipped", "iso_shield",
                                               "clove_phase", "veto_evolved", "hush_suspended"))),
                "viper_fuel": p.passive_state.get("viper_fuel", 100)
                if p.agent == "viper" and (viewer is None or viewer.pid == p.pid) else None,
                "neon_battery": p.passive_state.get("neon_battery", 100)
                if p.agent == "neon" and (viewer is None or viewer.pid == p.pid) else None,
                "neon_ammo": p.passive_state.get("neon_ammo") if viewer is None or viewer.pid == p.pid else None,
                **({"kayo_downed_until": p.passive_state["kayo_downed"][0]}
                   if viewer is not None and (viewer.pid == p.pid or
                       (not viewer.alive and viewer.team == p.team and self.phase in ("live", "planted")))
                   and p.status.get("kayo_downed", 0) > self.time
                   and "kayo_downed" in p.passive_state else {}),
                **({"owl_drone_spotted_at": p.passive_state["owl_drone_spotted_at"]}
                   if (viewer is None or viewer.team == p.team)
                   and p.status.get("owl_drone_spotted", 0) > self.time
                   and "owl_drone_spotted_at" in p.passive_state else {}),
                "request": p.request if viewer is None or viewer.team == p.team else "",
                "request_revision": p.request_revision if viewer is None or viewer.team == p.team else 0,
                "anchor": [p.anchor.x, p.anchor.y] if p.anchor is not None and p.anchor_until > self.time
                and (viewer is None or viewer.team == p.team) else None,
                "dashing": p.dash_until > self.time,
                "dash_armed_at": p.dash_armed_at, "dash_armed_until": p.dash_armed_until,
                "channel_until": p.channel_until,
                **({"died_at": p.died_at, "clove_revived_round": bool(p.passive_state.get("clove_revived_round"))}
                   if p.agent == "clove" else {}),
                "blade_count": p.blade_count, "blades_equipped": p.blades_equipped,
                "repeat_shots": p.repeat_shots, "repeat_until": p.repeat_until, "repeat_next": p.repeat_next,
                "vx": p.vel.x, "vy": p.vel.y, "spray": p.spray,
                **({"ability_return_at": p.ability_return_at} if p.ability_return_at >= 0 else {}),
            })
        return {
            "time": self.time, "phase": self.phase, "phase_left": self.phase_time_left(), "round": self.round_no,
            "minimap_obscured": viewer is not None and self.minimap_obscured(viewer),
            "paranoia_warning": viewer is not None and self.paranoia_warning(viewer),
            "mode": self.mode, "dm_left": max(0.0, self.dm_ends_at - self.time) if self.mode == "deathmatch" else 0.0,
            "dm_timer_paused": self.dm_timer_paused and self.phase in ("buy", "live"),
            "dm_stage": self.dm_stage,
            "rules": {k: getattr(self.cfg.lobby, k) for k in self.RULE_NAMES},
            "score": list(self.score), "attacking_team": self.attacking_team, "winner": self.match_winner,
            "round_winner": self.round_winner, "round_reason": self.round_reason,
            "spike": {"carrier": self.spike_carrier, "pos": (self.spike_pos.x, self.spike_pos.y) if self.spike_pos else None,
                      "site": self.spike_site, "ground": self.spike_ground},
            "effects": [{"kind": e.kind, "team": e.team, "x": e.pos.x, "y": e.pos.y, "r": e.radius,
                         "a": (e.a.x, e.a.y) if e.a else None, "b": (e.b.x, e.b.y) if e.b else None,
                         "start": e.start, "until": e.until, "status": e.props.get("status"),
                         **({"blocks_sound": True} if e.props.get("blocks_sound") else {}),
                         **({"duel_id": e.props["duel_id"]} if e.props.get("duel_id") else {}),
                         "blocks_sight": e.props.get("blocks_sight", e.kind in ("smoke", "wall")),
                         "settled_ground": e.props.get("settled_ground"),
                         "flight_height": e.props.get("flight_height"),
                         "bolt_path": e.props.get("bolt_path"),
                         "source_level": e.props.get("source_level", 0),
                         "fall": e.props.get("fall"),
                         "sprite": e.props.get("sprite"), "sprite_width": e.props.get("sprite_width"),
                         "warning_sprite": e.props.get("warning_sprite"), "owner": e.owner,
                         **({"warning_start": e.props["warning_start"]} if "warning_start" in e.props else {}),
                         "clone_facing": e.props.get("clone_facing"),
                         "cone": e.props.get("cone"), "aim": e.props.get("aim") if e.props.get("cone") else None,
                         "carrying_spike": bool(e.data.get("carrying")),
                         "soul_orb": bool(e.props.get("soul_orb")),
                         "devour_tether": bool(e.props.get("devour_tether")),
                         "barrier": ([wall.rect.x0, wall.rect.y0, wall.rect.x1, wall.rect.y1]
                                     if (wall := e.props.get("barrier")) else None),
                         **({"barrier_movement_only": True} if wall is not None and wall.movement_only else {}),
                         "manual": e.props.get("manual") if viewer is None or e.owner == viewer.pid else None,
                         "recall_recharge": e.props.get("recall_recharge") if viewer is None or e.owner == viewer.pid else None}
                        for e in self.effects if self._effect_visible(e, viewer)],
            "players": players,
            "spike_audio": [
                {"pid": p.pid, "key": key, "pos": (pos.x, pos.y), "started": started}
                for p in self.players.values()
                if p.alive and (self.phase == "live" and p.pid == self.spike_carrier and p.plant_progress > 0
                                or self.phase == "planted" and p.defusing)
                if (audio := p.passive_state.get("spike_audio")) is not None
                for key, pos, started in (audio,)
            ] + [
                audio for effect in self.effects
                if self.phase in ("live", "planted") and not effect.props.get("ended")
                if (audio := effect.data.get("spike_audio")) is not None
            ],
            "orbs": [(o.x, o.y) for o in self.orbs],
            "recovery_orbs": [(o.x, o.y) for o in self.recovery_orbs],
            "roster": [{"pid": p.pid, "name": p.name, "team": p.team, "agent": p.agent, "kills": p.kills, "assists": p.assists,
                        "deaths": p.deaths, "alive": p.alive, "bot": p.is_bot, "ping": p.ping_ms,
                        "score": self.combat_score(p), "damage": p.damage_total}
                       for p in self.players.values()],
            "history": [[w, r] for w, r in self.history],
            "report": self.damage_report(viewer.pid) if viewer is not None else [],
            "drops": [{"key": d.key, "x": d.pos.x, "y": d.pos.y, "skin": d.skin, "ground": d.ground}
                      for d in self.drops],
            "cover_broken": [[r.x0, r.y0, r.x1, r.y1] for r in self.broken_cover],
            "doors_open": [[r.x0, r.y0, r.x1, r.y1] for r in self.open_doors],
        }
