"""Agent figures: animation state, frames, figure effects."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)


class CharactersMixin:
    def sprite_cfg(self, p: PlayerState) -> dict:
        return dict(self.match.agents.get(p.agent, {}).get("sprites", {}))

    def slot_active(self, p: PlayerState, slot: str) -> bool:
        """An ability counts as active for its duration after use; X also while overdrive or immunity runs."""
        t = self.match.time
        if slot == "X" and (p.overdrive_until > t or p.immune_until > t):
            return True
        cast_t, cast_slot = self.ui.last_cast.get(p.pid, (-99.0, ""))
        if cast_slot != slot:
            return False
        ab = self.match.agents.get(p.agent, {}).get("abilities", {}).get(slot, {})
        return t - cast_t < float(ab.get("duration", 0.0)) and float(ab.get("duration", 0.0)) <= 15.0

    def character_state(self, p: PlayerState, me: PlayerState) -> tuple[str, float, float]:
        """(state, clock, speed factor) after the priority list of CHARACTER_SHEETS.md."""
        m, t, enemy = self.match, self.match.time, p.team != me.team
        if not p.alive:
            since = t - self.ui.died_at.get(p.pid, -99.0)
            dying = self.chars.duration(p.agent, "dying", enemy)
            return ("dying", since, 1.0) if since < dying else ("dead", 0.0, 1.0)
        if m.phase == "over" and m.match_winner == p.team:
            return "victory", t, 1.0
        if p.plant_progress > 0:
            return "plant", t, 1.0
        if p.defuse_progress > 0:
            return "defuse", t, 1.0
        cfg = self.sprite_cfg(p)
        for slot, name in dict(cfg.get("mechanics", {})).items():
            if self.slot_active(p, slot):
                return f"mech_{name}", t, 1.0
        cast_t, slot = self.ui.last_cast.get(p.pid, (-99.0, ""))
        if slot:
            tag = f"cast_{slot.lower()}"
            since = t - cast_t
            if since < self.chars.duration(p.agent, tag, enemy):
                return tag, since, 1.0
            if self.slot_active(p, slot):
                return f"channel_{slot.lower()}", since, 1.0
        weapon = m.weapons.get(p.weapon.key) if p.weapon else None
        if p.reload_until > t and weapon:
            return "reload", 1 - (p.reload_until - t) / max(weapon.reload, 0.01), 1.0
        if p.equip_until > t and weapon:
            return "equip", 1 - (p.equip_until - t) / max(weapon.equip, 0.01), 1.0
        shot = t - self.ui.last_shot.get(p.pid, -99.0)
        if shot < self.chars.duration(p.agent, "shoot", enemy):
            return ("melee" if weapon and weapon.slot == "melee" else "shoot"), shot, 1.0
        hit = t - self.ui.last_hit.get(p.pid, -99.0)
        if hit < self.chars.duration(p.agent, "flinch", enemy):
            return "flinch", hit, 1.0
        prev_z = self.ui.prev_z.get(p.pid, 0.0)
        self.ui.prev_z[p.pid] = p.z
        if prev_z > 0.05 and p.z <= 0.001:
            self.ui.landed_at[p.pid] = t
        if p.z > 0.001:
            return ("jump" if p.vz > 0 else "fall"), t, 1.0
        landed = t - self.ui.landed_at.get(p.pid, -99.0)
        if landed < self.chars.duration(p.agent, "land", enemy):
            return "land", landed, 1.0
        speed = p.vel.length()
        run = float(m._mv["run_speed"])
        if p.crouching:
            return ("crouch_walk" if speed > 0.3 else "crouch"), t, 1.0
        if speed > 0.5:
            return "walk", t, max(0.4, min(1.0, speed / run))
        return "idle", t, 1.0

    def character_frame(self, p: PlayerState, me: PlayerState) -> pygame.Surface | None:
        state, clock, speed = self.character_state(p, me)
        form = None
        for slot, name in dict(self.sprite_cfg(p).get("forms", {})).items():
            if self.slot_active(p, slot):
                form = str(name)
        return self.chars.frame(p.agent, state, p.team != me.team, self.scale, clock, form=form, speed=speed)

    def draw_figure_fx(self, p: PlayerState, at: tuple[float, float]) -> None:
        """Effects in the 16x32 figure cell, centred on the player: one-shots from events, loops while active."""
        t = self.match.time
        size = (round(self.scale), round(2 * self.scale))
        active: list[tuple[str, float]] = []
        keep = []
        for pid, name, start, duration in self.ui.figure_fx:
            if t - start > duration:
                continue
            keep.append((pid, name, start, duration))
            if pid == p.pid:
                active.append((name, (t - start) / duration))
        self.ui.figure_fx = keep
        if p.heal_left > 0:
            active.append(("heal", (t * 6 % 3) / 3))
        if p.immune_until > t:
            active.append(("immunity_aura", (t * 4 % 2) / 2))
        for name, progress in active:
            img = self.bank.strip_frame(f"fx/ability/{name}.png", size, progress, 16)
            if img is not None:
                self.screen.blit(img, (at[0] - size[0] / 2, at[1] - size[1] / 2))

    def held_item(self, p: PlayerState) -> tuple[str, str]:
        """What the figure holds: ("ability", slot), ("spike", ""), ("weapon", key) or ("", "")."""
        m = self.match
        cast = self.ui.last_cast.get(p.pid)
        if cast and m.time - cast[0] < 0.45:
            return "ability", cast[1]
        if p.pid == self.me and self.aiming:
            return "ability", self.aiming
        if p.plant_progress > 0 or p.defuse_progress > 0:
            return "spike", ""
        if p.weapon:
            return "weapon", p.weapon.key
        return "", ""

    def draw_held(self, p: PlayerState, me: PlayerState, at: tuple[float, float], body_h: float) -> None:
        """Draws the weapon, ability or bomb in the figure's hand, pointing where the player looks; the bomb carrier
        also shows the bomb on the back."""
        s, m = self.screen, self.match
        px, py = at
        hand = self.to_screen(p.pos + heading(p.facing) * 0.32, me)
        dx, dy = hand[0] - self.to_screen(p.pos, me)[0], hand[1] - self.to_screen(p.pos, me)[1]
        screen_angle = math.degrees(math.atan2(-dy, dx))  # 0 = pointing right, counter-clockwise
        hx, hy = px + dx, py + dy + body_h * 0.12
        kind, key = self.held_item(p)
        if m.spike_carrier == p.pid and kind != "spike":
            pack = self.bank.scaled("fx/spike.png", (max(4, round(self.scale * 0.45)),) * 2, 0, 16)
            if pack is not None:
                s.blit(pack, (px - dx * 0.6 - pack.get_width() / 2, py - dy * 0.6 - pack.get_height() / 2 + body_h * 0.05))
        if kind == "weapon":
            d = m.weapons.get(key)
            length = 0.55 if d is not None and d.slot == "melee" else 0.7 if d is not None and d.slot == "sidearm" else 1.05
            img = self.bank.scaled(f"weapons/val2d/{key}.png", (max(4, round(self.scale * length)), max(2, round(self.scale * length / 2))))
            if img is None:
                pygame.draw.line(s, (40, 44, 50), (hx, hy), (hx + dx * 1.4, hy + dy * 1.4), 3)
                return
            flip = 90 < screen_angle % 360 < 270
            if flip:
                img = pygame.transform.flip(img, False, True)
            rot = pygame.transform.rotate(img, screen_angle)
            s.blit(rot, (hx + dx * 0.5 - rot.get_width() / 2, hy + dy * 0.5 - rot.get_height() / 2))
        elif kind == "ability":
            icon = self.bank.scaled(f"ui/faehigkeit_{p.agent}_{key}.png", (max(4, round(self.scale * 0.42)),) * 2)
            if icon is not None:
                s.blit(icon, (hx - icon.get_width() / 2, hy - icon.get_height() / 2))
        elif kind == "spike":
            pack = self.bank.scaled("fx/spike.png", (max(4, round(self.scale * 0.5)),) * 2, 0, 16)
            if pack is not None:
                s.blit(pack, (hx - pack.get_width() / 2, hy - pack.get_height() / 2))

