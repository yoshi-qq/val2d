"""Game events to sound and effects: shots, hits, kills, abilities, bomb."""
from __future__ import annotations

from time import monotonic_ns

from client.common import *  # noqa: F403  (pygame, colours, types)
from gameplay.geometry import projectile_progress
from gameplay.kit.statuses import flag as status_flag


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
        self.ui.spike_sound_sources.pop(pid, None)
        if playback := self.ui.spike_sounds.pop(pid, None):
            for channel, sample, _ in playback[1]:
                if channel.get_sound() == sample:
                    self._set_alternate_priority(channel, sample, False)
                    channel.stop()

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

    def update_audio_perspective(self, listener: PlayerState | None) -> None:
        now = self.match.time
        if listener is None or not listener.alive or listener.status.get("kayo_downed", 0) <= now:
            self.sound.set_perspective_gain(1.0)
            return
        deadline = listener.passive_state.get("kayo_downed_until")
        if record := listener.passive_state.get("kayo_downed"):
            deadline = record[0]
        remaining = max(0.0, min(1.0, (deadline - now) / 5.0)) if deadline is not None else 1.0
        self.sound.set_perspective_gain(0.25 + 0.75 * remaining)

    def audio_tick(self, me: PlayerState, *, spike_listener: PlayerState | None = None) -> None:
        """Bomb beeps faster as the timer runs down; landing thuds; round start cue."""
        m = self.match
        if spike_listener is None:
            spike_listener = me
        self.update_spike_audio(spike_listener)
        self.update_incendiary_audio(spike_listener)
        self.update_recon_audio(spike_listener)
        self.update_rotor_audio(spike_listener)
        self.update_lockdown_audio(spike_listener)
        self.update_kayo_stabilize_audio(spike_listener)
        self.update_drone_warning(spike_listener)
        if not self.has_current_audio_state():
            self._next_beep = None
        elif m.phase == "planted" and m.spike_pos is not None:
            left = m.spike_time_left()
            if left > 0 and (self._next_beep is None or m.time + 1e-6 >= self._next_beep):
                recovering = self._next_beep is None
                second = max(1, math.ceil(left - 1e-6))
                offsets = (0.0, 0.20, 0.40) if second <= 10 else (0.0, 0.20) if second <= 20 else (0.0,)
                end = m.time + left
                start = end - second
                self._next_beep = next((start + offset for offset in offsets if start + offset > m.time + 1e-6),
                                       start + 1.0)
                if not recovering or any(abs(start + offset - m.time) <= 1e-6 for offset in offsets):
                    self.sound.play("bomb_beep", spike_listener, m.spike_pos, 60,
                                    occluded=self.occluded(spike_listener, m.spike_pos), gain=0.8)
        else:
            self._next_beep = 0.0
        if not self.has_current_audio_state():
            self.ui.pending_sounds.clear()
        due = [s for s in self.ui.pending_sounds if s[0] <= m.time]
        self.ui.pending_sounds = [s for s in self.ui.pending_sounds if s[0] > m.time]
        for _, key, pid, radius, gain in due:
            p = m.players.get(pid)
            if p is not None and p.alive:
                self.sound.play(key, spike_listener, p.pos, radius,
                                occluded=self.occluded(spike_listener, p.pos), gain=gain)
        ready = me.ult_points >= m.ultimate_cost(me)
        if ready and not self._ult_was_ready:
            self.sound.play("ult_ready", gain=0.6)
        self._ult_was_ready = ready
        if m.phase == "buy" and self._last_phase != "buy":
            self.sound.play("round_start", gain=0.8, apply_perspective=False)
        self._last_phase = m.phase

    def update_spike_audio(self, listener: PlayerState) -> None:
        if not self.has_current_audio_state():
            for pid in list(self.ui.spike_sounds):
                self.stop_spike_sound(pid)
            return
        for pid, (pos, tracks) in list(self.ui.spike_sounds.items()):
            tracks[:] = [track for track in tracks if track[0].get_sound() == track[1]]
            left, right, muffled = self.sound.spatial_mix(listener, pos, 35, self.occluded(listener, pos), 1.0)
            if len(tracks) < 2 and pid in self.ui.spike_sound_sources:
                started, normal, filtered_sample = self.ui.spike_sound_sources[pid]
                elapsed = (monotonic_ns() - started) / 1_000_000_000
                if not tracks and elapsed >= normal.get_length():
                    self.stop_spike_sound(pid)
                    continue
                filtered = filtered_sample is not None and (not tracks[0][2] if tracks else muffled)
                source = filtered_sample if filtered else normal
                if (not tracks or filtered != tracks[0][2]) and (channel := pygame.mixer.find_channel()):
                    sample = self.sound.sound_tail(source, elapsed)
                    if sample is not None:
                        channel.play(sample)
                        tracks.append((channel, sample, filtered))
            elif not tracks:
                self.stop_spike_sound(pid)
                continue
            for channel, sample, filtered in tracks:
                volume = (left, right) if len(tracks) == 1 or filtered == muffled else (0, 0)
                if sum(volume) < 0.01:
                    volume = (0, 0)
                channel.set_volume(*volume)
                self._set_alternate_priority(channel, sample, len(tracks) > 1 and filtered != muffled)

    def update_incendiary_audio(self, listener: PlayerState | None) -> None:
        """Keep one spatial loop per audible, active fire pool."""
        self._update_effect_loops(listener, self.ui.fire_sounds, "incendiary_fire", 22.0, 0.75)

    def update_drone_warning(self, listener: PlayerState | None) -> None:
        now = self.match.time
        channel = self.ui.drone_warning
        if not self.has_current_audio_state():
            listener = None
        active = (listener is not None and listener.alive and listener.status.get("owl_drone_spotted", 0) > now
                  and not status_flag(self.match, listener, "deaf"))
        mark = (listener.pid, listener.passive_state.get("owl_drone_spotted_at")) if active else None
        if channel is not None and channel.get_sound() == self.ui.drone_warning_sample:
            if active and mark == self.ui.drone_warning_mark:
                channel.set_volume(0.175 * self.sound.volume * self.sound.perspective_gain)
                return
            channel.stop()
        self.ui.drone_warning = self.ui.drone_warning_sample = None
        self.ui.drone_warning_mark = None
        if not active:
            self.ui.drone_warning_waiting = None
            return
        waiting = self.ui.drone_warning_waiting
        if waiting is not None and waiting[0] != mark:
            waiting = self.ui.drone_warning_waiting = None
        if self.sound.volume <= 0:
            if waiting is None:
                self.ui.drone_warning_waiting = (mark, monotonic_ns())
            return
        sample = self.sound.sounds.get("ab_alarm")
        override = None
        started = monotonic_ns()
        if waiting is not None:
            started = waiting[1]
        marked_at = mark[1]
        age_ms = max(0, round((now - marked_at) * 1_000_000_000) // 1_000_000) if marked_at is not None else 0
        elapsed = max(age_ms, (monotonic_ns() - started) // 1_000_000)
        if sample is not None and elapsed:
            if pygame.mixer.find_channel() is None and not self.sound.silent_alternates:
                self.ui.drone_warning_waiting = (mark, started)
                return
            override = self.sound.shifted_loop(sample, elapsed)
        channel = self.sound.play("ab_alarm", gain=0.35, loops=-1, sample_override=override)
        if channel is not None:
            self.ui.drone_warning = channel
            self.ui.drone_warning_sample = channel.get_sound()
            self.ui.drone_warning_mark = mark
            self.ui.drone_warning_waiting = None
        elif sample is not None:
            self.ui.drone_warning_waiting = (mark, started)

    def update_recon_audio(self, listener: PlayerState | None) -> None:
        self._update_effect_loops(listener, self.ui.recon_sounds, "recon_flight", 24.0, 0.8)

    def update_rotor_audio(self, listener: PlayerState | None) -> None:
        self._update_effect_loops(listener, self.ui.rotor_sounds, "owl_rotor", 22.0, 0.65)

    def update_lockdown_audio(self, listener: PlayerState | None) -> None:
        self._update_effect_loops(listener, self.ui.lockdown_sounds, "lockdown_warning", 0.0, 0.55)

    def update_kayo_stabilize_audio(self, listener: PlayerState | None) -> None:
        self._update_effect_loops(listener, self.ui.kayo_stabilize_sounds, "cast_charge_up", 15.0, 0.6)

    def _update_effect_loops(self, listener, channels, key: str, radius: float, gain: float) -> None:
        m = self.match
        active = {}
        if listener is not None and self.has_current_audio_state() and not status_flag(m, listener, "deaf"):
            for effect in m.effects:
                if effect.props.get("ended") or m.time >= effect.until:
                    continue
                sprite = effect.props.get("sprite")
                pos = effect.pos
                reach = radius
                if key == "lockdown_warning":
                    if (sprite != "killjoy_lockdown_pulse" or m.time >= effect.start
                            or not listener.alive or listener.team == effect.team
                            or (listener.pos - pos).length() > effect.radius):
                        continue
                    reach = effect.radius * 1.25
                elif m.time < effect.start:
                    continue
                if key == "recon_flight":
                    if sprite != "sova_recon_bolt" or effect.kind != "blast" or effect.a is None:
                        continue
                    progress = projectile_progress(m.time, effect.start, effect.until, lands_at_expiry=True)
                    if progress >= 1.0:
                        continue
                    pos = effect.a + (effect.pos - effect.a) * progress
                elif key == "owl_rotor":
                    if sprite != "sova_owl_drone":
                        continue
                elif key == "cast_charge_up":
                    if (effect.kind != "kayo_stabilize" or listener.team != effect.team
                            or m.phase not in ("live", "planted")):
                        continue
                elif key == "incendiary_fire" and sprite not in ("brimstone_incendiary_burning", "phoenix_hot_hands_pool"):
                    continue
                identity = (effect.owner, Vec(0, 0) if key == "owl_rotor" else effect.pos, effect.start)
                index = 0
                while (*identity, index) in active:
                    index += 1
                occluded = self.occluded(listener, pos)
                base_left, base_right, muffled = self.sound.spatial_mix(
                    listener, pos, reach, occluded, gain, unscaled=True
                )
                if base_left + base_right < 0.01:
                    continue
                level = self.sound.volume * self.sound.perspective_gain
                left, right = min(1.0, base_left * level), min(1.0, base_right * level)
                audio_start = effect.props.get("warning_start") if key == "lockdown_warning" else effect.start
                active[(*identity, index)] = (left, right, muffled, occluded, pos, reach, audio_start)
        normal = self.sound.sounds.get(key)
        muffled_sample = self.sound.muffled.get(key, normal)
        for identity, channel in list(channels.items()):
            mix = active.get(identity)
            alternate_id = (key, identity)
            started, sample, primary_filtered = self.ui.effect_sound_primary[alternate_id]
            alternate, other_sample = self.ui.effect_sound_alternates.get(alternate_id, (None, None))
            alternate_active = alternate is not None and alternate.get_sound() == other_sample
            if mix and channel.get_sound() != sample and alternate_active:
                channels[identity] = channel = alternate
                sample, primary_filtered = other_sample, not primary_filtered
                self.ui.effect_sound_primary[alternate_id] = (started, sample, primary_filtered)
                self.ui.effect_sound_alternates.pop(alternate_id)
                alternate, alternate_active = None, False
            if mix and channel.get_sound() == sample:
                left, right, muffled, *_ = mix
                if alternate_active:
                    main_audible = primary_filtered == muffled
                    channel.set_volume(*((left, right) if main_audible else (0, 0)))
                    alternate.set_volume(*((0, 0) if main_audible else (left, right)))
                    self._set_alternate_priority(channel, sample, not main_audible)
                    self._set_alternate_priority(alternate, other_sample, main_audible)
                else:
                    self.ui.effect_sound_alternates.pop(alternate_id, None)
                    self._set_alternate_priority(channel, sample, False)
                    channel.set_volume(left, right)
                continue
            self.ui.effect_sound_alternates.pop(alternate_id, None)
            self.ui.effect_sound_primary.pop(alternate_id)
            if alternate_active:
                self._set_alternate_priority(alternate, other_sample, False)
                alternate.stop()
            if channel.get_sound() == sample:
                self._set_alternate_priority(channel, sample, False)
                channel.stop()
            del channels[identity]
        waiting = self.ui.effect_sound_waiting
        for pending in list(waiting):
            if pending[0] == key and pending[1] not in active:
                del waiting[pending]
        for identity, (left, right, muffled, occluded, pos, reach, audio_start) in active.items():
            if identity not in channels and normal is not None:
                slot = (key, identity)
                now = monotonic_ns()
                # A listener entering range can join a loop that already started on the host.
                age = max(0.0, m.time - audio_start) if audio_start is not None else 0.0
                started = min(waiting.get(slot, now), now - round(age * 1_000_000_000))
                if left + right < 0.01:
                    waiting.setdefault(slot, started)
                    continue
                primary_filtered = normal is not muffled_sample and muffled
                override = None
                if (elapsed := (now - started) // 1_000_000) > 0:
                    if pygame.mixer.find_channel() is None and not self.sound.silent_alternates:
                        continue
                    source = muffled_sample if primary_filtered else normal
                    override = self.sound.shifted_loop(source, elapsed)
                channel = self.sound.play(key, listener, pos, reach, occluded=occluded, gain=gain, loops=-1,
                                          sample_override=override)
                if channel is not None:
                    channels[identity] = channel
                    self.ui.effect_sound_primary[slot] = (started, channel.get_sound(), primary_filtered)
                    waiting.pop(slot, None)
                else:
                    waiting.setdefault(slot, started)
        # Give the audible tracks first claim on free mixer channels.
        for identity, channel in channels.items():
            alternate_id = (key, identity)
            if alternate_id in self.ui.effect_sound_alternates or normal is muffled_sample:
                continue
            alternate = pygame.mixer.find_channel()
            if alternate is None:
                break
            started, sample, primary_filtered = self.ui.effect_sound_primary[alternate_id]
            other_sample = normal if primary_filtered else muffled_sample
            elapsed = (monotonic_ns() - started) // 1_000_000
            shifted = self.sound.shifted_loop(other_sample, elapsed)
            alternate.play(shifted, loops=-1)
            left, right, muffled, *_ = active[identity]
            main_audible = primary_filtered == muffled
            channel.set_volume(*((left, right) if main_audible else (0, 0)))
            alternate.set_volume(*((0, 0) if main_audible else (left, right)))
            self.ui.effect_sound_alternates[alternate_id] = (alternate, shifted)
            self._set_alternate_priority(channel, sample, not main_audible)
            self._set_alternate_priority(alternate, shifted, main_audible)

    def has_current_audio_state(self) -> bool:
        client = getattr(self, "client", None)
        return client is None or (client.connected and not getattr(self, "restore_spike_audio", False))

    def stop_ability_audio(self) -> None:
        self.update_incendiary_audio(None)
        self.update_recon_audio(None)
        self.update_rotor_audio(None)
        self.update_lockdown_audio(None)
        self.update_kayo_stabilize_audio(None)
        self.update_drone_warning(None)

    def _set_alternate_priority(self, channel, sample, silent: bool) -> None:
        if silent:
            self.sound.silent_alternates[channel.id] = (channel, sample)
        else:
            self.sound.silent_alternates.pop(channel.id, None)

    def handle_events(self, events: list[GameEvent], *, spike_listener: PlayerState | None = None) -> None:
        m, t = self.match, self.match.time
        me = m.players.get(self.me)
        if me is None:
            return
        if spike_listener is None:
            spike_listener = me
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
                if not self.has_current_audio_state():
                    continue
                p = m.players.get(d["pid"])
                if p is not None:
                    gain = 0.8 if d["pid"] == self.me else 0.5
                    pos = Vec(*d["pos"]) if "pos" in d else p.pos
                    self.sound.play("reload_out", spike_listener, pos, 14,
                                    occluded=self.occluded(spike_listener, pos), gain=gain)
                    self.ui.pending_sounds.append((t + max(0.2, float(d.get("seconds", 1.5)) - 0.35), "reload_in", d["pid"], 14, gain))
            elif e.kind == "equip" and d["pid"] == self.me:
                self.sound.play("equip", gain=0.6)
            elif e.kind == "empty" and d["pid"] == self.me:
                self.sound.play("empty", gain=0.7)
            elif e.kind == "land" and self.has_current_audio_state():
                self.ui.landed_at[d["pid"]] = t
                if not d.get("quiet"):
                    pos = Vec(*d["pos"])
                    if (not m.sound_blocked(spike_listener.pos, pos)
                            and not status_flag(m, spike_listener, "deaf")):
                        self.sound.play("land", spike_listener, pos, 18,
                                        occluded=self.occluded(spike_listener, pos), gain=0.6)
            elif e.kind == "jump" and self.has_current_audio_state():
                p = m.players.get(d["pid"])
                pos = Vec(*d["pos"]) if "pos" in d else p.pos if p is not None else None
                if (pos is not None and not m.sound_blocked(spike_listener.pos, pos)
                        and not status_flag(m, spike_listener, "deaf")):
                    self.sound.play("jump", spike_listener, pos, 12,
                                    occluded=self.occluded(spike_listener, pos), gain=0.6)
            elif e.kind == "pickup" and d.get("pid") == self.me:
                self.sound.play("pickup", gain=0.6)
            elif e.kind in ("plant_start", "defuse_start", "spike_audio_restore"):
                if not self.has_current_audio_state():
                    continue
                audio_id = d.get("audio_id", d["pid"])
                self.stop_spike_sound(audio_id)
                key = d.get("key", "spike_plant" if e.kind == "plant_start" else "spike_defuse")
                pos = Vec(*d["pos"])
                occluded = self.occluded(spike_listener, pos)
                restored = e.kind == "spike_audio_restore"
                resumed = d.get("resumed") or key == "spike_defuse_half"
                offset = max(0.0, t - e.t) if restored else 0.0
                if resumed:
                    if not restored:
                        spike = Vec(*d["spike_pos"]) if "spike_pos" in d else m.spike_pos or pos
                        self.sound.play("spike_defuse_half", spike_listener, spike, 35,
                                        occluded=self.occluded(spike_listener, spike))
                    key = "spike_defuse"
                    offset += float(m._spike["defuse_checkpoint"])
                normal, filtered = self.sound.sounds.get(key), self.sound.muffled.get(key)
                override = None
                if offset > 0:
                    if normal is None:
                        continue
                    normal = self.sound.sound_tail(normal, offset)
                    filtered = self.sound.sound_tail(filtered, offset) if filtered is not None else None
                    if normal is None:
                        continue
                    _, _, muffled = self.sound.spatial_mix(spike_listener, pos, 35, occluded, 1.0)
                    override = (filtered if muffled else normal) or normal
                ch = self.sound.play(key, spike_listener, pos, 35, occluded=occluded,
                                     keep_silent=True, sample_override=override)
                if normal is not None:
                    self.ui.spike_sound_sources[audio_id] = (monotonic_ns(), normal, filtered)
                    self.ui.spike_sounds[audio_id] = (pos, [])
                if ch is not None:
                    sample = ch.get_sound()
                    tracks = [(ch, sample, sample == filtered)]
                    alternate = normal if sample == filtered else filtered
                    if alternate is not None and alternate != sample:
                        # Start both variants together so changing the mix preserves playback progress.
                        if other := pygame.mixer.find_channel():
                            other.play(alternate)
                            other.set_volume(0, 0)
                            tracks.append((other, alternate, alternate == filtered))
                            self._set_alternate_priority(other, alternate, True)
                    self.ui.spike_sounds[audio_id] = (pos, tracks)
            elif e.kind in ("plant_stop", "defuse_stop"):
                self.stop_spike_sound(d.get("audio_id", d["pid"]))
            elif e.kind == "defuse_half":
                p = m.players.get(d["pid"])
                pos = Vec(*d["pos"]) if "pos" in d else m.spike_pos or (p.pos if p is not None else None)
                if pos is not None:
                    self.sound.play("spike_defuse_half", spike_listener, pos, 35,
                                    occluded=self.occluded(spike_listener, pos))
            elif e.kind == "sound":
                pos = Vec(*d["pos"])
                if m.sound_blocked(spike_listener.pos, pos):
                    continue
                if status_flag(m, spike_listener, "deaf"):
                    continue
                if d.get("pid") == self.me and not d.get("decoy"):
                    self.ui.noise.append((float(d["radius"]), t))  # own noise circle on the minimap
                if "shot_facing" in d and not e.within_sound_range(spike_listener.pos):
                    continue
                radius = e.sound_radius_at(spike_listener.pos)
                key = self.sound_key(d, pos)
                self.sound.play(key, spike_listener, pos, radius, occluded=self.occluded(spike_listener, pos),
                                gain=float(SOUND_MIX["step_gain"]) if key.startswith("step") else 1.0)
                if m.cfg.lobby.sound_rings and d["pid"] != self.me and e.within_sound_range(spike_listener.pos):
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
                by = killer.name if killer else "Spawn" if d.get("weapon") == "spawn" else "Bomb"
                self.ui.feed.append((t + 5, f"{by} → {victim.name if victim else '?'}", killer.agent if killer else None,
                                     victim.agent if victim else None, bool(d["head"]), str(d.get("weapon", "")),
                                     killer.team if killer else None, bool(d.get("wallbang"))))
                if d["by"] == self.me:
                    streak = max(1, min(5, int(d.get("streak", 1) or 1)))
                    self.sound.play(f"kill_{streak}" if f"kill_{streak}" in self.sound.sounds else "kill")
                    self.ui.kill_flash = (t + 1.2, streak)
                elif d["pid"] == self.me:
                    self.sound.play("death")
            elif e.kind == "assist" and d["pid"] == self.me:
                self.sound.play("assist")
            elif e.kind == "neon_battery_low" and d["pid"] == self.me:
                self.sound.play("ab_alarm", gain=0.5)
            elif e.kind == "neon_battery_empty" and d["pid"] == self.me:
                self.sound.play("cast_whoosh", gain=0.5)
            elif e.kind == "neon_battery_insufficient" and d["pid"] == self.me:
                self.sound.play("empty", gain=0.5)
            elif e.kind in ("device_hit_audio", "owl_dart_hit") and d["pid"] == self.me:
                self.sound.play(str(d["key"]), gain=0.7)
            elif e.kind == "lockdown_destroyed" and d["team"] == me.team:
                self.sound.play("cast_burst")
            elif e.kind == "lockdown_result" and d["team"] == me.team:
                count = int(d["count"])
                self.sound.play("ui_click" if count == 0 else f"kill_{min(count, 5)}")
            elif e.kind == "plant":
                self.stop_spike_sound(d["pid"])
                self.ui.banner = (t + 2.5, f"Bomb planted on {d['site']}")
                self.ui.banner_art = "bomb_planted"
                self.sound.play("bomb_planted", apply_perspective=False)
            elif e.kind == "blast":
                pos = Vec(*d["pos"])
                self.sound.play("ab_blast", spike_listener, pos, 45, occluded=self.occluded(spike_listener, pos))
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
            elif e.kind == "ability":
                self.ui.last_cast[d["pid"]] = (t, str(d.get("key", "C")))
                if d["pid"] == self.me and self.aiming == d.get("key") and d.get("repeat_left") == 0:
                    self.set_aim(None)
                kind, at = str(d.get("kind")), Vec(*d["pos"])
                caster = m.players.get(d["pid"])
                if kind == "wave":
                    self.ui.waves.append((d["pid"], at, t))
                elif kind == "hop" and caster is not None:
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
                radius = float(d.get("cast_radius", 30))
                if announcement := d.get("cast_announcement"):
                    self.sound.play(announcement["ally" if d["team"] == me.team else "enemy"],
                                    apply_perspective=False)
                elif radius > 0 and (d.get("cast_team") is None or d["cast_team"] == me.team):
                    self.sound.play(key, spike_listener, origin, radius, occluded=self.occluded(spike_listener, origin))
            elif e.kind == "round_end":
                for pid in list(self.ui.spike_sounds):
                    self.stop_spike_sound(pid)
                won = d["winner"] == me.team
                if d["winner"] is not None:
                    self.sound.play("round_win" if won else "round_loss", apply_perspective=False)
                self.ui.banner = (t + 5, f"{d['reason']}  {d['score'][me.team]}:{d['score'][1 - me.team]}")
                self.ui.banner_art = "" if d["winner"] is None else "victory" if won else "defeat"
                if d.get("reason") == "Bomb defused":
                    self.ui.banner_art = "bomb_defused" if won else "defeat"
            elif e.kind == "explode":
                self.ui.oneshots.append(("fx/spike_explosion.png", Vec(*d["pos"]), t, 1.0, 64, (24.0, 24.0)))
                self.ui.scorches.append((Vec(*d["pos"]), t + 30.0))
                self.sound.play("bomb_explode", spike_listener, Vec(*d["pos"]), 120)
            elif e.kind == "flash":
                pos = Vec(*d["pos"])
                self.sound.play("ab_flash", spike_listener, pos, 35, occluded=self.occluded(spike_listener, pos))
                self.ui.oneshots.append(("fx/flash_burst.png", Vec(*d["pos"]), t, 0.3, 16, (1.0, 1.0)))
            elif e.kind == "round_title":
                ours = d.get("team") == me.team
                who = m.players.get(d["pid"]).name if d.get("pid") in m.players else ""
                text = f"{d['title']} · {who}" if who and d["title"] in ("Ace", "Clutch") else str(d["title"])
                self.ui.title_banner = (t + 3.5, text, ours)
                self.sound.play("round_title" if ours else "round_loss", gain=0.7, apply_perspective=False)
            elif e.kind == "orb":
                self.sound.play("orb_pickup", spike_listener, Vec(*d["pos"]), 25)
            elif e.kind == "sell" and d.get("pid") == self.me:
                self.sound.play("ui_click", gain=0.6)
            elif e.kind == "kayo_announcement":
                self.sound.play(d["ally"] if d["team"] == me.team else d["enemy"], apply_perspective=False)
            elif e.kind == "kayo_scan" and d["team"] == me.team:
                self.ui.title_banner = (t + 2.5, "Suppressed · " + ", ".join(d["agents"]), True)
            elif e.kind == "sound_fx":
                pos = Vec(*d["pos"])
                personal = d.get("range_filtered") and d.get("pid") == self.me
                listener = me if personal else spike_listener
                if m.sound_blocked(listener.pos, pos):
                    continue
                radius = float(d.get("radius", 30.0))
                if d.get("range_filtered"):
                    if d.get("team", me.team) != me.team or status_flag(m, listener, "deaf"):
                        continue
                    if personal:
                        self.sound.play(str(d["key"]), gain=float(d.get("gain", 1.0)))
                        continue
                    if (listener.pos - pos).length() >= radius:
                        continue
                self.sound.play(str(d.get("key", "")), listener, pos, radius, occluded=self.occluded(listener, pos),
                                gain=float(d.get("gain", 1.0)))
            elif e.kind == "door":
                self.sound.play("door", spike_listener, Vec(*d["pos"]), 20)
            elif e.kind == "defuse":
                self.stop_spike_sound(d["pid"])
                self.sound.play("bomb_defused", apply_perspective=False)
