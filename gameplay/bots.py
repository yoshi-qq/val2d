"""Simple bots: walk to a goal, aim with reaction time, stop to shoot, plant and defuse."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from gameplay.geometry import Vec, angle_diff, angle_of
from gameplay.kit.engine import resolve_target
from gameplay.kit.registry import BOT_CONTROL
from gameplay.match import Command, Match, PlayerState
from gameplay.nav import grid_for


@dataclass
class BotBrain:
    pid: int
    reaction: float = 0.35
    turn_speed: float = 420.0  # Grad pro Sekunde
    aim_error: float = 1.2     # remaining aim error in degrees per shot
    seen_since: dict[int, float] = field(default_factory=dict)
    goal: Vec | None = None
    rng: random.Random = field(default_factory=random.Random)
    stuck_time: float = 0.0
    last_pos: Vec | None = None
    detour: Vec | None = None
    ability_ready_at: float = 0.0
    path: list[Vec] = field(default_factory=list)
    path_goal: Vec | None = None
    path_time: float = -99.0

    def think(self, m: Match, dt: float) -> Command:
        p = m.players[self.pid]
        cmd = Command(facing=p.facing)
        if not p.alive or m.phase in ("lobby", "over", "end"):
            self.goal = None
            return cmd
        if m.phase == "buy":
            if m.mode != "deathmatch":
                cmd.buy = self._shopping(m, p)
                if m.spike_pos is not None and m.side(p.team) == "attack" and all(
                    teammate.is_bot for teammate in m.players.values() if teammate.team == p.team
                ):
                    return self._navigate(m, p, dt, cmd)
            return cmd
        if m.in_deathmatch_spawn(p):
            self.seen_since.clear()
            return self._navigate(m, p, dt, cmd)
        if (control := BOT_CONTROL.get(p.agent)) and control(m, p, cmd, self.goal):
            self.seen_since.clear()
            return cmd
        enemy = self._visible_enemy(m, p)
        if enemy:
            cmd = self._fight(m, p, enemy, dt, cmd)
        else:
            self.seen_since.clear()
            cmd = self._navigate(m, p, dt, cmd)
        return self._abilities(m, p, enemy, cmd)

    # ---------------------------------------------------------------- abilities
    OFFENSIVE = {"flash", "blast", "wave", "zone", "slow_field"}
    SELF_BUFF = {"overdrive", "immunity", "stim", "reveal_all"}
    PLACE_AHEAD = {"smoke", "wall", "vapor_wall", "sensor", "alarm", "tripwire", "decoy"}
    BOT_KIND = {"offense": "blast", "buff": "overdrive", "place": "smoke", "heal": "heal", "escape": "dash"}  # bot= of composed abilities

    @staticmethod
    def cursor_for(m: Match, ab: dict, distance: float) -> float:
        """Cursor depth that lands an ability at `distance`: bots know the hidden throw share of throwables."""
        from gameplay.kit import expand
        from gameplay.kit.builtins import throw_factor
        try:
            spec = expand(ab)
        except (KeyError, TypeError, ValueError):
            return distance
        return distance / max(0.1, throw_factor(m, spec)) if spec.get("target") == "throw" else distance

    def _usable(self, m: Match, p: PlayerState, key: str) -> dict | None:
        ab = m.agents.get(p.agent, {}).get("abilities", {}).get(key)
        if not ab:
            return None
        if key == "X":
            return ab if p.ult_points >= m.ultimate_cost(p) else None
        if ab.get("requires_target") and resolve_target(m, p, ab) is None:
            return None
        free = p.status.get(ab.get("free_with_status"), 0) > m.time
        return ab if free or p.charges.get(m.charge_key(p, key), 0) > 0 else None

    def _abilities(self, m: Match, p: PlayerState, enemy: PlayerState | None, cmd: Command) -> Command:
        """Simple rules: offensive blocks at a seen enemy, buffs in a fight, smokes/traps near the goal, heal when hurt."""
        if enemy is not None and p.dash_armed_at <= m.time < p.dash_armed_until:
            cmd.ability = "E"
            return cmd
        if enemy is not None and p.repeat_shots and p.repeat_next <= m.time < p.repeat_until:
            cmd.ability = "X"
            return cmd
        if m.phase not in ("live", "planted") or m.time < self.ability_ready_at or p.prev_ability:
            return cmd
        for key in ("X", "E", "Q", "C"):
            ab = self._usable(m, p, key)
            if not ab:
                continue
            if ab.get("blade_weapon") and p.blade_count:
                continue
            kind = self.BOT_KIND.get(str(ab.get("bot", "")), "") if ab.get("kind") == "custom" else str(ab.get("kind", ""))
            use = False
            if enemy is not None:
                dist = (enemy.pos - p.pos).length()
                if kind in self.OFFENSIVE and dist <= 1.5 * float(ab.get("range", ab.get("length", 20.0))) and dist > 3.0:
                    cmd.cursor_depth = self.cursor_for(m, ab, dist)
                    use = True
                elif kind in self.SELF_BUFF or kind == "shield":
                    use = True
                elif kind == "dash" and p.hp < 50:
                    cmd.facing = (cmd.facing or p.facing) + 180
                    use = True
            else:
                near_goal = self.goal is not None and (self.goal - p.pos).length() < 14.0
                attacking_site = near_goal and m.side(p.team) == "attack" and m.phase == "live"
                if (kind in self.PLACE_AHEAD or (kind in self.OFFENSIVE and attacking_site)) and near_goal                         and self.rng.random() < 0.02:
                    cmd.cursor_depth = self.cursor_for(m, ab, min(float(ab.get("range", 10.0)), (self.goal - p.pos).length()))
                    use = True
                elif kind == "heal" and p.hp < 60:
                    cmd.cursor_depth = 0.5
                    cmd.ability_alt = bool(ab.get("alt", {}).get("target") == "self")
                    use = True
            if use:
                cmd.ability = key
                self.ability_ready_at = m.time + self.rng.uniform(3.0, 7.0)
                break
        return cmd

    # ---------------------------------------------------------------- Buy
    def _shopping(self, m: Match, p: PlayerState) -> list[str]:
        wants: list[str] = []
        credits = p.credits
        for key in ("phantom", "vandal", "spectre", "stinger"):
            d = m.weapons.get(key)
            if d and "primary" not in p.weapons and credits >= d.price + 400:
                wants.append(key)
                credits -= d.price
                break
        for key in ("heavy_armor", "regen_shield", "light_armor"):
            a = m.armor.get(key)
            if a and credits >= a.price and m.armor_available(p, key):
                wants.append(key)
                credits -= a.price
                break
        abil = m.agents.get(p.agent, {}).get("abilities", {})
        for key in ("C", "Q", "E"):
            ab = abil.get(key, {})
            price = int(ab.get("price", 0))
            if price and not ab.get("shared_charge") and p.charges.get(key, 0) < int(ab.get("max", 1)) and credits >= price:
                wants.append(key)
                credits -= price
        return wants

    # ---------------------------------------------------------------- Kampf
    def _visible_enemy(self, m: Match, p: PlayerState) -> PlayerState | None:
        best: PlayerState | None = None
        best_d = 1e9
        for t in m.players.values():
            if (t.team == p.team or not t.alive or t.level != p.level or t.dm_ghost
                    or m.deathmatch_spawn_protected(t)):
                continue
            if not m.can_see(p, t) or not m.line_of_fire(p, t):
                continue  # seen but not hittable (e.g. behind low cover): keep moving instead of a standoff
            d = (t.pos - p.pos).length()
            if d < best_d:
                best, best_d = t, d
        return best

    def _fight(self, m: Match, p: PlayerState, enemy: PlayerState, dt: float, cmd: Command) -> Command:
        first = self.seen_since.setdefault(enemy.pid, m.time)
        want = angle_of(enemy.pos - p.pos)
        diff = angle_diff(p.facing, want)
        step = self.turn_speed * dt
        cmd.facing = (p.facing + max(-step, min(step, diff))) % 360
        cmd.cursor_depth = (enemy.pos - p.pos).length() + self.rng.uniform(-0.6, 0.6)
        wd = m.weapons.get(p.weapon.key) if p.weapon else None
        if (p.weapon and wd and wd.is_gun and p.weapon.mag == 0 and p.weapon.reserve == 0
                and not m.has_infinite_reserve(p.weapon) and "sidearm" in p.weapons and p.slot != "sidearm"):
            cmd.slot = "sidearm"
        ready = m.time - first >= self.reaction and abs(diff) <= self.aim_error + 2.0
        if ready:
            cmd.fire = True if (wd and wd.auto) else not p.prev_fire
        else:
            cmd.move_x = self.rng.choice((-1.0, 1.0)) if self.rng.random() < 0.05 else 0.0
        return cmd

    # ---------------------------------------------------------------- Laufen
    def _navigate(self, m: Match, p: PlayerState, dt: float, cmd: Command) -> Command:
        if m.mode == "deathmatch":  # hunt: walk towards the nearest enemy
            enemies = [t for t in m.players.values()
                       if t.alive and t.team != p.team and t.duel_id == p.duel_id and not t.dm_ghost]
            self.goal = min((t.pos for t in enemies), key=lambda pos: (pos - p.pos).length(), default=None)
            attack = False
        else:
            attack = m.side(p.team) == "attack"
        if attack:
            site = self._pick_site(m, attacking=True)
            if m.phase == "planted" and m.spike_pos is not None:
                self.goal = self._guard_spot(m, p)
                if (p.pos - self.goal).length() < 1.2:
                    cmd.facing = angle_of(m.spike_pos - p.pos) if (m.spike_pos - p.pos).length() > 0.5 else p.facing
                    return cmd
            elif m.spike_carrier == p.pid:
                self.goal = site
                if m.world.site_at(p.pos, p.level) and m.phase == "live":
                    cmd.interact = True
                    return cmd
            elif m.spike_pos is not None and m.phase in ("buy", "live"):
                self.goal = m.spike_pos
            else:
                self.goal = site
            if m.phase == "live" and site is not None and self.goal is not None and self.goal != m.spike_pos \
                    and not self._may_push(m, p, site):
                self.goal = self._staging(m, site)
        elif m.mode != "deathmatch":
            if m.phase == "planted" and m.spike_pos is not None:
                self.goal = m.spike_pos
                if m.near_spike(p, 1.2):
                    cmd.interact = True
                    return cmd
            elif self.goal is None:
                self.goal = self._pick_site(m)
        if self.goal is None:
            return cmd
        if self.path_goal is None or (self.path_goal - self.goal).length() > 0.5 or m.time - self.path_time > 3.0:
            grid = grid_for(m.world, frozenset(m.open_doors | m.broken_cover), tuple(m.ability_walls()))
            goal_ground = m.spike_ground if self.goal == m.spike_pos else float("inf")
            self.path = grid.path(p.pos, self.goal, start_ground=p.ground / float(m._mv["level_height"]),
                                  goal_ground=goal_ground)
            self.path_goal, self.path_time = self.goal, m.time
        while self.path and (self.path[0] - p.pos).length() < 0.6:
            self.path.pop(0)
        target = self.detour or (self.path[0] if self.path else self.goal)
        to = target - p.pos
        if to.length() < 1.0 and not self.path:
            if self.detour:
                self.detour = None
            return cmd
        cmd.facing = angle_of(to)
        cmd.move_y = 1.0
        cmd.cursor_depth = 10.0
        # festgefahren: kurzer Umweg seitlich
        if self.last_pos is not None and (p.pos - self.last_pos).length() < 0.02:
            self.stuck_time += dt
        else:
            self.stuck_time = 0.0
        self.last_pos = p.pos
        if self.stuck_time > 0.4:
            side = 1 if self.rng.random() < 0.5 else -1
            self.detour = p.pos + to.normalized().rotated(90 * side) * 1.5
            self.path_time = -99.0  # plan again after the sidestep
            self.stuck_time = 0.0
        if self.detour is not None and (self.detour - p.pos).length() < 0.5:
            self.detour = None
        return cmd

    def _pick_site(self, m: Match, attacking: bool = False) -> Vec | None:
        """Defenders spread over the sites; attackers all take the same site this round."""
        if not m.world.sites:
            return None
        if m.spike_site:
            for s in m.world.sites:
                if s.name == m.spike_site:
                    return s.rect.center
        idx = (m.round_no * 7 + 3) % len(m.world.sites) if attacking else (m.round_no + self.pid) % len(m.world.sites)
        site = m.world.sites[idx].rect.center
        grid = grid_for(m.world, frozenset(m.open_doors | m.broken_cover), tuple(m.ability_walls()))
        return grid.center(grid.nearest_free(grid.cell(site)))

    def _staging(self, m: Match, site: Vec) -> Vec:
        """Gathering point about 10 m before the site, on the side of the attackers' spawn."""
        zone = m.world.spawn_zones.get(0)
        origin = zone.center if zone else site
        away = (origin - site)
        point = site + (away.normalized() * min(10.0, away.length() * 0.6) if away.length() > 0.1 else Vec(0, 0))
        grid = grid_for(m.world, frozenset(m.open_doors | m.broken_cover), tuple(m.ability_walls()))
        return grid.center(grid.nearest_free(grid.cell(point)))

    def _may_push(self, m: Match, p: PlayerState, site: Vec) -> bool:
        """Push onto the site once enough attackers have gathered or the round is getting late."""
        if m.phase_time_left() < 55.0:
            return True
        attackers = [t for t in m.players.values() if t.alive and m.side(t.team) == "attack"]
        need = min(3, len(attackers))
        stage = self._staging(m, site)
        gathered = sum(1 for t in attackers if (t.pos - stage).length() < 7.0 or (t.pos - site).length() < (stage - site).length())
        return gathered >= need

    def _guard_spot(self, m: Match, p: PlayerState) -> Vec:
        """After the plant: hold a spot 5-7 m from the bomb, spread by player id, with sight on it."""
        assert m.spike_pos is not None
        grid = grid_for(m.world, frozenset(m.open_doors | m.broken_cover), tuple(m.ability_walls()))
        angle = (self.pid * 77) % 360
        for step in range(8):
            spot = m.spike_pos + Vec(1, 0).rotated(angle + step * 45) * 6.0
            cell = grid.cell(spot)
            if grid.free(cell) and grid.line_free(spot, m.spike_pos):
                return grid.center(cell)
        return m.spike_pos


class BotDirector:
    def __init__(self, match: Match, seed: int | None = None) -> None:
        self.match = match
        self.brains: dict[int, BotBrain] = {}
        self.rng = random.Random(seed)

    def sync(self) -> None:
        for p in self.match.players.values():
            if p.is_bot and not p.dummy and p.pid not in self.brains:
                self.brains[p.pid] = BotBrain(p.pid, rng=random.Random(self.rng.random()))

    def commands(self, dt: float) -> dict[int, Command]:
        self.sync()
        players = self.match.players
        return {pid: b.think(self.match, dt) for pid, b in self.brains.items() if pid in players and players[pid].is_bot}
