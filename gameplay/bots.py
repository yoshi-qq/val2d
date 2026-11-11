"""Simple bots: walk to a goal, aim with reaction time, stop to shoot, plant and defuse."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from gameplay.geometry import Vec, angle_diff, angle_of
from gameplay.match import Command, Match, PlayerState


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

    def think(self, m: Match, dt: float) -> Command:
        p = m.players[self.pid]
        cmd = Command(facing=p.facing)
        if not p.alive or m.phase in ("lobby", "over", "end"):
            self.goal = None
            return cmd
        if m.phase == "buy":
            cmd.buy = self._shopping(m, p)
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

    def _usable(self, m: Match, p: PlayerState, key: str) -> dict | None:
        ab = m.agents.get(p.agent, {}).get("abilities", {}).get(key)
        if not ab:
            return None
        if key == "X":
            return ab if p.ult_points >= int(ab.get("cost", 99)) else None
        return ab if p.charges.get(key, 0) > 0 else None

    def _abilities(self, m: Match, p: PlayerState, enemy: PlayerState | None, cmd: Command) -> Command:
        """Simple rules: offensive blocks at a seen enemy, buffs in a fight, smokes/traps near the goal, heal when hurt."""
        if m.phase not in ("live", "planted") or m.time < self.ability_ready_at or p.prev_ability:
            return cmd
        for key in ("X", "E", "Q", "C"):
            ab = self._usable(m, p, key)
            if not ab:
                continue
            kind = str(ab.get("kind", ""))
            use = False
            if enemy is not None:
                dist = (enemy.pos - p.pos).length()
                if kind in self.OFFENSIVE and dist <= 1.5 * float(ab.get("range", ab.get("length", 20.0))) and dist > 3.0:
                    cmd.cursor_depth = dist
                    use = True
                elif kind in self.SELF_BUFF or kind == "shield":
                    use = True
                elif kind == "dash" and p.hp < 50:
                    cmd.facing = (cmd.facing or p.facing) + 180
                    use = True
            else:
                near_goal = self.goal is not None and (self.goal - p.pos).length() < 14.0
                if kind in self.PLACE_AHEAD and near_goal and self.rng.random() < 0.02:
                    cmd.cursor_depth = min(float(ab.get("range", 10.0)), (self.goal - p.pos).length())
                    use = True
                elif kind == "heal" and p.hp < 60:
                    cmd.cursor_depth = 0.5
                    use = True
            if use:
                cmd.ability = key
                self.ability_ready_at = m.time + self.rng.uniform(3.0, 7.0)
                break
        return cmd

    # ---------------------------------------------------------------- Kauf
    def _shopping(self, m: Match, p: PlayerState) -> list[str]:
        wants: list[str] = []
        credits = p.credits
        for key in ("speer", "hammer", "sirene", "wespe"):
            d = m.weapons.get(key)
            if d and "primary" not in p.weapons and credits >= d.price + 400:
                wants.append(key)
                credits -= d.price
                break
        for key in ("schwer", "leicht"):
            a = m.armor.get(key)
            if a and p.armor < a.points and credits >= a.price:
                wants.append(key)
                credits -= a.price
                break
        abil = m.agents.get(p.agent, {}).get("abilities", {})
        for key in ("C", "Q"):
            ab = abil.get(key, {})
            price = int(ab.get("price", 0))
            if price and p.charges.get(key, 0) < int(ab.get("max", 1)) and credits >= price:
                wants.append(key)
                credits -= price
        return wants

    # ---------------------------------------------------------------- Kampf
    def _visible_enemy(self, m: Match, p: PlayerState) -> PlayerState | None:
        best: PlayerState | None = None
        best_d = 1e9
        for t in m.players.values():
            if t.team == p.team or not t.alive or t.level != p.level:
                continue
            if not m.can_see(p, t):
                continue
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
        if p.weapon and wd and wd.is_gun and p.weapon.mag == 0 and p.weapon.reserve == 0 and "sidearm" in p.weapons and p.slot != "sidearm":
            cmd.slot = "sidearm"
        ready = m.time - first >= self.reaction and abs(diff) <= self.aim_error + 2.0
        if ready:
            cmd.fire = True if (wd and wd.auto) else not p.prev_fire
        else:
            cmd.move_x = self.rng.choice((-1.0, 1.0)) if self.rng.random() < 0.05 else 0.0
        return cmd

    # ---------------------------------------------------------------- Laufen
    def _navigate(self, m: Match, p: PlayerState, dt: float, cmd: Command) -> Command:
        attack = m.side(p.team) == "attack"
        if attack:
            if m.spike_carrier == p.pid:
                site = self._pick_site(m)
                self.goal = site
                if m.world.site_at(p.pos) and m.phase == "live":
                    cmd.interact = True
                    return cmd
            elif m.spike_pos is not None and m.phase == "live":
                self.goal = m.spike_pos
            elif self.goal is None:
                self.goal = self._pick_site(m)
        else:
            if m.phase == "planted" and m.spike_pos is not None:
                self.goal = m.spike_pos
                if (p.pos - m.spike_pos).length() <= 1.2:
                    cmd.interact = True
                    return cmd
            elif self.goal is None:
                self.goal = self._pick_site(m)
        if self.goal is None:
            return cmd
        target = self.detour or self.goal
        to = target - p.pos
        if to.length() < 1.0:
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
            self.detour = p.pos + to.normalized().rotated(90 * side) * 4.0
            self.stuck_time = 0.0
        return cmd

    def _pick_site(self, m: Match) -> Vec | None:
        if not m.world.sites:
            return None
        if m.spike_site:
            for s in m.world.sites:
                if s.name == m.spike_site:
                    return s.rect.center
        idx = (m.round_no + self.pid) % len(m.world.sites)
        return m.world.sites[idx].rect.center


class BotDirector:
    def __init__(self, match: Match, seed: int | None = None) -> None:
        self.match = match
        self.brains: dict[int, BotBrain] = {}
        self.rng = random.Random(seed)

    def sync(self) -> None:
        for p in self.match.players.values():
            if p.is_bot and p.pid not in self.brains:
                self.brains[p.pid] = BotBrain(p.pid, rng=random.Random(self.rng.random()))

    def commands(self, dt: float) -> dict[int, Command]:
        self.sync()
        return {pid: b.think(self.match, dt) for pid, b in self.brains.items()}
