"""Game events to sound and effects: shots, hits, kills, abilities, bomb."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)


class EventsMixin:
    def sound_key(self, data: dict, pos: Vec) -> str:
        """Sample for a sound event: the weapon class for shots, the floor for steps."""
        if data.get("kind") == "shot":
            d = self.match.weapons.get(str(data.get("weapon", "")))
            if d is None:
                return "shot_rifle"
            return "shot_silenced" if d.silenced else SHOT_SOUND.get(d.category, SHOT_SOUND.get(d.slot, "shot_rifle"))
        return STEP_SOUND.get(self.match.world.floor_material(pos), "step_hard")

    def occluded(self, listener: PlayerState, pos: Vec) -> bool:
        """True if a wall stands between listener and sound (sound is muffled, not silenced)."""
        try:
            return not self.match._line_clear(listener.pos, pos, listener.level, ignore_effects=True)
        except (AttributeError, TypeError, ValueError):
            return False

    def audio_tick(self, me: PlayerState) -> None:
        """Bomb beeps faster as the timer runs down; landing thuds; round start cue."""
        m = self.match
        if m.phase == "planted" and m.spike_pos is not None:
            left = m.spike_time_left()
            interval = max(0.12, min(1.0, left / 40.0))
            if m.time >= self._next_beep:
                self._next_beep = m.time + interval
                self.sound.play("bomb_beep", me, m.spike_pos, 60, gain=0.8)
        else:
            self._next_beep = 0.0
        for pid, landed in self.ui.landed_at.items():
            if landed == m.time and pid in m.players:
                self.sound.play("land", me, m.players[pid].pos, 18, occluded=self.occluded(me, m.players[pid].pos), gain=0.6)
        if m.phase == "buy" and self._last_phase != "buy":
            self.sound.play("round_start", gain=0.8)
        self._last_phase = m.phase

    def handle_events(self, events: list[GameEvent]) -> None:
        m, t = self.match, self.match.time
        me = m.players.get(self.me)
        if me is None:
            return
        for e in events:
            d = e.data
            if e.kind == "shot":
                self.ui.last_shot[d["pid"]] = t
                if d["pid"] == self.me:
                    self.stats["shots"] += 1
                if d.get("stop") == "wall":
                    self.ui.oneshots.append(("fx/einschlag_wand.png", Vec(*d["to"]), t, 0.25, 8, (0.5, 0.5)))
                self.ui.tracers.append(Tracer(Vec(*d["from"]), Vec(*d["to"]), t + 0.08, d["pid"] == self.me))
            elif e.kind == "sound":
                if me.status.get("deaf", 0.0) > t:
                    continue
                pos = Vec(*d["pos"])
                key = self.sound_key(d, pos)
                self.sound.play(key, me, pos, d["radius"], occluded=self.occluded(me, pos),
                                gain=0.45 if key.startswith("step") else 1.0)
                if m.cfg.lobby.sound_rings and d["pid"] != self.me:
                    self.ui.rings.append(Ring(pos, min(d["radius"], 6.0), t))
            elif e.kind == "hit":
                self.ui.last_hit[d["pid"]] = t
                if d.get("by") == self.me:
                    self.sound.play("hit_head" if d.get("zone") == "head" else "hit_body", gain=0.7)
                if d.get("by") == self.me:
                    self.stats["hits"] += 1
                    self.stats["heads"] += 1 if d.get("zone") == "head" else 0
                victim = m.players.get(d["pid"])
                if victim is not None:
                    self.ui.oneshots.append(("fx/treffer_koerper.png", victim.pos, t, 0.25, 8, (0.5, 0.5)))
                if d["by"] == self.me:
                    self.ui.hit_marker = t + 0.15
            elif e.kind == "kill":
                self.ui.died_at[d["pid"]] = t
                killer = m.players.get(d["by"]) if d["by"] else None
                victim = m.players.get(d["pid"])
                by = killer.name if killer else "Bomb"
                self.ui.feed.append((t + 5, f"{by} → {victim.name if victim else '?'}", killer.agent if killer else None,
                                     victim.agent if victim else None, bool(d["head"])))
                if d["by"] == self.me:
                    self.sound.play("kill")
                elif d["pid"] == self.me:
                    self.sound.play("death")
            elif e.kind == "plant":
                self.ui.banner = (t + 2.5, f"Bomb planted on {d['site']}")
                self.ui.banner_art = "spike_gelegt"
                self.sound.play("bomb_planted")
            elif e.kind == "blast":
                self.sound.play("ab_blast", me, Vec(*d["pos"]), 45, occluded=self.occluded(me, Vec(*d["pos"])))
                self.ui.blasts.append((Vec(*d["pos"]), float(d["radius"]), t))
                self.ui.scorches.append((Vec(*d["pos"]), t + 20.0))
            elif e.kind == "revive":
                self.ui.figure_fx.append((d["pid"], "revive", t, 0.6))
                revived = m.players.get(d["pid"])
                self.ui.feed.append((t + 4, f"{revived.name if revived else '?'} revived", None, revived.agent if revived else None, False))
            elif e.kind == "ability" and d.get("kind") == "wave":
                self.ui.last_cast[d["pid"]] = (t, str(d.get("key", "C")))
                self.ui.waves.append((d["pid"], Vec(*d["pos"]), t))
            elif e.kind == "ability":
                self.ui.last_cast[d["pid"]] = (t, str(d.get("key", "C")))
                kind, at = str(d.get("kind")), Vec(*d["pos"])
                caster = m.players.get(d["pid"])
                if kind == "hop" and caster is not None:
                    self.ui.oneshots.append(("fx/satz_staub.png", caster.pos, t, 0.35, 16, (1.0, 0.5)))
                elif kind == "reveal_all" and caster is not None:
                    self.ui.oneshots.append(("fx/ability/beacon.png", caster.pos, t, 1.5, 16, (1.0, 1.0)))
                elif kind in ("zone", "sensor", "alarm", "tripwire", "blast", "smoke"):
                    self.ui.oneshots.append(("fx/ability/impact_puff.png", at, t, 0.3, 16, (1.0, 1.0)))
                fx = {"teleport": ("teleport", 0.4), "shield": ("shield_shell", 0.6), "anchor": ("teleport", 0.4)}.get(str(d.get("kind")))
                if fx:
                    self.ui.figure_fx.append((d["pid"], fx[0], t, fx[1]))
                self.sound.play(ABILITY_SOUND.get(kind, "ab_power"), me, at, 30, occluded=self.occluded(me, at))
            elif e.kind == "round_end":
                won = d["winner"] == me.team
                self.sound.play("round_win" if won else "round_loss")
                self.ui.banner = (t + 5, f"{d['reason']}  {d['score'][me.team]}:{d['score'][1 - me.team]}")
                self.ui.banner_art = "sieg" if won else "niederlage"
                if d.get("reason") == "Bomb defused":
                    self.ui.banner_art = "entschaerft" if won else "niederlage"
            elif e.kind == "explode":
                self.ui.oneshots.append(("fx/spike_explosion.png", Vec(*d["pos"]), t, 1.0, 64, (24.0, 24.0)))
                self.ui.scorches.append((Vec(*d["pos"]), t + 30.0))
                self.sound.play("bomb_explode", me, Vec(*d["pos"]), 120)
            elif e.kind == "flash":
                self.sound.play("ab_flash", me, Vec(*d["pos"]), 35, occluded=self.occluded(me, Vec(*d["pos"])))
                self.ui.oneshots.append(("fx/funke_explosion.png", Vec(*d["pos"]), t, 0.3, 16, (1.0, 1.0)))
            elif e.kind == "door":
                self.sound.play("door", me, Vec(*d["pos"]), 20)
            elif e.kind == "defuse":
                self.sound.play("bomb_defused")
