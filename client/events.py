"""Game events to sound and effects: shots, hits, kills, abilities, bomb."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)


class EventsMixin:
    def sound_key(self, data: dict, pos: Vec) -> str:
        """Sample for a sound event: the weapon class for shots, the floor for steps."""
        if data.get("kind") == "knife":
            return "knife_heavy" if data.get("heavy") else "knife"
        if data.get("kind") == "shot":
            d = self.match.weapons.get(str(data.get("weapon", "")))
            if d is None:
                return "shot_rifle"
            return "shot_silenced" if d.silenced else SHOT_SOUND.get(d.category, SHOT_SOUND.get(d.slot, "shot_rifle"))
        return STEP_SOUND.get(self.match.world.floor_material(pos), "step_hard")

    def stop_spike_sound(self, pid: int) -> None:
        ch = self.ui.spike_sounds.pop(pid, None)
        if ch is not None:
            ch.stop()

    def through_smoke(self, a: Vec, b: Vec) -> bool:
        from gameplay.geometry import segment_circle_hit
        return any(e.kind == "smoke" and e.start <= self.match.time and segment_circle_hit(a, b, e.pos, e.radius)
                   for e in self.match.effects)

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
            interval = 1 / 3 if left <= 10 else 0.5 if left <= 20 else 1.0
            if m.time >= self._next_beep:
                self._next_beep = m.time + interval
                self.sound.play("bomb_beep", me, m.spike_pos, 60, gain=0.8)
        else:
            self._next_beep = 0.0
        for pid, landed in self.ui.landed_at.items():
            if landed == m.time and pid in m.players:
                self.sound.play("land", me, m.players[pid].pos, 18, occluded=self.occluded(me, m.players[pid].pos), gain=0.6)
        due = [s for s in self.ui.pending_sounds if s[0] <= m.time]
        self.ui.pending_sounds = [s for s in self.ui.pending_sounds if s[0] > m.time]
        for _, key, pid, radius, gain in due:
            p = m.players.get(pid)
            if p is not None and p.alive:
                self.sound.play(key, me, p.pos, radius, occluded=self.occluded(me, p.pos), gain=gain)
        abil = m.agents.get(me.agent, {}).get("abilities", {}).get("X", {})
        ready = me.ult_points >= int(abil.get("cost", 99))
        if ready and not self._ult_was_ready:
            self.sound.play("ult_ready", gain=0.6)
        self._ult_was_ready = ready
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
                if d.get("melee"):
                    continue  # knives: no tracer; the swing is heard through its sound event
                if d["pid"] == self.me:
                    self.stats["shots"] += 1
                if d.get("stop") == "wall":
                    self.ui.oneshots.append(("fx/wall_impact.png", Vec(*d["to"]), t, 0.25, 8, (0.5, 0.5)))
                a, b = Vec(*d["from"]), Vec(*d["to"])
                shooter = m.players.get(d["pid"])
                wd = m.weapons.get(str(d.get("weapon", "")))
                enemy_silenced = bool(wd and wd.silenced and shooter is not None and shooter.team != me.team)
                tracers_cheat = m.cheat("bullet_tracers")
                if enemy_silenced and self.through_smoke(a, b) and not tracers_cheat:
                    continue  # suppressed weapons leave no tracer for enemies when fired through smoke
                self.ui.tracers.append(Tracer(a, b, t + (1.5 if tracers_cheat else 0.08), d["pid"] == self.me,
                                              muzzle=not enemy_silenced))
            elif e.kind == "reload":
                p = m.players.get(d["pid"])
                if p is not None:
                    gain = 0.8 if d["pid"] == self.me else 0.5
                    self.sound.play("reload_out", me, p.pos, 14, occluded=self.occluded(me, p.pos), gain=gain)
                    self.ui.pending_sounds.append((t + max(0.2, float(d.get("seconds", 1.5)) - 0.35), "reload_in", d["pid"], 14, gain))
            elif e.kind == "equip" and d["pid"] == self.me:
                self.sound.play("equip", gain=0.6)
            elif e.kind == "empty" and d["pid"] == self.me:
                self.sound.play("empty", gain=0.7)
            elif e.kind == "jump":
                p = m.players.get(d["pid"])
                if p is not None:
                    self.sound.play("jump", me, p.pos, 12, occluded=self.occluded(me, p.pos), gain=0.6)
            elif e.kind == "pickup" and d.get("pid") == self.me:
                self.sound.play("pickup", gain=0.6)
            elif e.kind in ("plant_start", "defuse_start"):
                self.stop_spike_sound(d["pid"])
                key = "spike_plant" if e.kind == "plant_start" else "spike_defuse"
                ch = self.sound.play(key, me, Vec(*d["pos"]), 35, occluded=self.occluded(me, Vec(*d["pos"])))
                if ch is not None:
                    self.ui.spike_sounds[d["pid"]] = ch
            elif e.kind in ("plant_stop", "defuse_stop"):
                self.stop_spike_sound(d["pid"])
            elif e.kind == "defuse_half":
                p = m.players.get(d["pid"])
                if p is not None:
                    self.sound.play("spike_defuse_half", me, p.pos, 35, occluded=self.occluded(me, p.pos))
            elif e.kind == "sound":
                if me.status.get("deaf", 0.0) > t:
                    continue
                pos = Vec(*d["pos"])
                if d.get("pid") == self.me and not d.get("decoy"):
                    self.ui.noise.append((float(d["radius"]), t))  # own noise circle on the minimap
                key = self.sound_key(d, pos)
                self.sound.play(key, me, pos, d["radius"], occluded=self.occluded(me, pos),
                                gain=float(SOUND_MIX["step_gain"]) if key.startswith("step") else 1.0)
                if m.cfg.lobby.sound_rings and d["pid"] != self.me:
                    self.ui.rings.append(Ring(pos, min(d["radius"], 6.0), t))
            elif e.kind == "hit":
                self.ui.last_hit[d["pid"]] = t
                if d["pid"] == self.me and d.get("by") is not None and d.get("by") != self.me:
                    attacker = m.players.get(d["by"])
                    self.sound.play("hurt", gain=0.7)
                    if attacker is not None:
                        self.ui.damage_from.append((attacker.pos, t))
                if d.get("by") == self.me:
                    self.sound.play("hit_head" if d.get("zone") == "head" else "hit_body", gain=0.7)
                if d.get("by") == self.me:
                    self.stats["hits"] += 1
                    self.stats["heads"] += 1 if d.get("zone") == "head" else 0
                victim = m.players.get(d["pid"])
                if victim is not None:
                    self.ui.oneshots.append(("fx/body_hit.png", victim.pos, t, 0.25, 8, (0.5, 0.5)))
                if d["by"] == self.me:
                    self.ui.hit_marker = t + 0.15
            elif e.kind == "kill":
                self.stop_spike_sound(d["pid"])
                self.ui.died_at[d["pid"]] = t
                killer = m.players.get(d["by"]) if d["by"] else None
                victim = m.players.get(d["pid"])
                by = killer.name if killer else "Bomb"
                self.ui.feed.append((t + 5, f"{by} → {victim.name if victim else '?'}", killer.agent if killer else None,
                                     victim.agent if victim else None, bool(d["head"]), str(d.get("weapon", "")),
                                     killer.team if killer else None, bool(d.get("wallbang"))))
                if d["by"] == self.me:
                    streak = max(1, min(5, int(d.get("streak", 1) or 1)))
                    self.sound.play(f"kill_{streak}" if f"kill_{streak}" in self.sound.sounds else "kill")
                    self.ui.kill_flash = (t + 1.2, streak)
                elif d["pid"] == self.me:
                    self.sound.play("death")
            elif e.kind == "plant":
                self.stop_spike_sound(d["pid"])
                self.ui.banner = (t + 2.5, f"Bomb planted on {d['site']}")
                self.ui.banner_art = "bomb_planted"
                self.sound.play("bomb_planted")
            elif e.kind == "blast":
                self.sound.play("ab_blast", me, Vec(*d["pos"]), 45, occluded=self.occluded(me, Vec(*d["pos"])))
                self.ui.blasts.append((Vec(*d["pos"]), float(d["radius"]), t))
                self.ui.scorches.append((Vec(*d["pos"]), t + 20.0))
            elif e.kind == "revive":
                self.ui.figure_fx.append((d["pid"], "revive", t, 0.6))
                revived = m.players.get(d["pid"])
                self.ui.feed.append((t + 4, f"{revived.name if revived else '?'} revived", None,
                                     revived.agent if revived else None, False, "", revived.team if revived else None))
            elif e.kind == "ability_return" and d["pid"] == self.me:
                self.local_facing = float(d["facing"])
                self.set_aim(None)
                if self.mode == "client" and me is not None:
                    me.pos = Vec(*d["pos"])
                    me.facing = self.local_facing
                    self.server_pos[self.me] = me.pos
            elif e.kind == "ability" and d.get("kind") == "wave":
                self.ui.last_cast[d["pid"]] = (t, str(d.get("key", "C")))
                self.ui.waves.append((d["pid"], Vec(*d["pos"]), t))
            elif e.kind == "ability":
                self.ui.last_cast[d["pid"]] = (t, str(d.get("key", "C")))
                if d["pid"] == self.me and self.aiming == d.get("key") and d.get("repeat_left") == 0:
                    self.set_aim(None)
                kind, at = str(d.get("kind")), Vec(*d["pos"])
                caster = m.players.get(d["pid"])
                if kind == "hop" and caster is not None:
                    self.ui.oneshots.append(("fx/hop_dust.png", caster.pos, t, 0.35, 16, (1.0, 0.5)))
                elif kind == "reveal_all" and caster is not None:
                    self.ui.oneshots.append(("fx/ability/beacon.png", caster.pos, t, 1.5, 16, (1.0, 1.0)))
                elif kind in ("zone", "sensor", "alarm", "tripwire", "blast", "smoke"):
                    self.ui.oneshots.append(("fx/ability/impact_puff.png", at, t, 0.3, 16, (1.0, 1.0)))
                fx = {"teleport": ("teleport", 0.4), "shield": ("shield_shell", 0.6), "anchor": ("teleport", 0.4)}.get(str(d.get("kind")))
                if fx:
                    self.ui.figure_fx.append((d["pid"], fx[0], t, fx[1]))
                cast = str(d.get("sound") or "")  # an ability may name its own cast sound
                key = cast if cast in self.sound.sounds else ABILITY_SOUND.get(kind, "cast_magic")
                origin = caster.pos if caster is not None else at
                if d.get("cast_team") is None or d["cast_team"] == me.team:
                    self.sound.play(key, me, origin, float(d.get("cast_radius", 30)), occluded=self.occluded(me, origin))
            elif e.kind == "round_end":
                won = d["winner"] == me.team
                self.sound.play("round_win" if won else "round_loss")
                self.ui.banner = (t + 5, f"{d['reason']}  {d['score'][me.team]}:{d['score'][1 - me.team]}")
                self.ui.banner_art = "victory" if won else "defeat"
                if d.get("reason") == "Bomb defused":
                    self.ui.banner_art = "bomb_defused" if won else "defeat"
            elif e.kind == "explode":
                self.ui.oneshots.append(("fx/spike_explosion.png", Vec(*d["pos"]), t, 1.0, 64, (24.0, 24.0)))
                self.ui.scorches.append((Vec(*d["pos"]), t + 30.0))
                self.sound.play("bomb_explode", me, Vec(*d["pos"]), 120)
            elif e.kind == "flash":
                self.sound.play("ab_flash", me, Vec(*d["pos"]), 35, occluded=self.occluded(me, Vec(*d["pos"])))
                self.ui.oneshots.append(("fx/flash_burst.png", Vec(*d["pos"]), t, 0.3, 16, (1.0, 1.0)))
            elif e.kind == "round_title":
                ours = d.get("team") == me.team
                who = m.players.get(d["pid"]).name if d.get("pid") in m.players else ""
                text = f"{d['title']} · {who}" if who and d["title"] in ("Ace", "Clutch") else str(d["title"])
                self.ui.title_banner = (t + 3.5, text, ours)
                self.sound.play("round_title" if ours else "round_loss", gain=0.7)
            elif e.kind == "orb":
                self.sound.play("orb_pickup", me, Vec(*d["pos"]), 25)
            elif e.kind == "sell" and d.get("pid") == self.me:
                self.sound.play("ui_click", gain=0.6)
            elif e.kind == "sound_fx":
                pos = Vec(*d["pos"])
                self.sound.play(str(d.get("key", "")), me, pos, float(d.get("radius", 30.0)), occluded=self.occluded(me, pos))
            elif e.kind == "door":
                self.sound.play("door", me, Vec(*d["pos"]), 20)
            elif e.kind == "defuse":
                self.stop_spike_sound(d["pid"])
                self.sound.play("bomb_defused")
