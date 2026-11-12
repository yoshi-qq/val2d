"""Buy menu."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)


class BuyMixin:
    # columns like the real buy menu: each column holds one or two groups stacked
    BUY_COLUMNS = ((("sidearm", "Sidearms"),), (("smg", "SMGs"), ("shotgun", "Shotguns")), (("rifle", "Rifles"),),
                   (("sniper", "Sniper rifles"), ("heavy", "Machine guns")), (("armor", "Shields"), ("abilities", "Abilities")))
    CARD_W, CARD_H, GAP, HEAD = 214, 70, 8, 30

    def buy_groups(self) -> dict[str, list[tuple[str, str]]]:
        m = self.match
        groups: dict[str, list[tuple[str, str]]] = {g: [] for col in self.BUY_COLUMNS for g, _ in col}
        for key, d in sorted(m.weapons.items(), key=lambda kv: kv[1].price):
            if d.slot != "melee":
                groups.setdefault(d.category if d.category in groups else "rifle", []).append((key, f"{d.name}  {d.price}"))
        for key, a in m.armor.items():
            groups["armor"].append((key, f"{a.name}  {a.price}"))
        me = m.players.get(self.me)
        for k in (("C", "Q") if me else ()):
            ab = m.agents[me.agent]["abilities"][k]
            groups["abilities"].append((k, f"{k} {ab['name']}  {ab['price']}"))
        return groups

    def buy_layout(self) -> list[tuple[pygame.Rect, str, str]]:
        """Card rectangles for every item, column by column, groups stacked with a heading each."""
        groups = self.buy_groups()
        out = []
        left = (self.w - len(self.BUY_COLUMNS) * (self.CARD_W + self.GAP) + self.GAP) // 2
        for ci, col in enumerate(self.BUY_COLUMNS):
            x = left + ci * (self.CARD_W + self.GAP)
            y = 120
            for g, _ in col:
                y += self.HEAD
                for key, label in groups.get(g, []):
                    out.append((pygame.Rect(x, y, self.CARD_W, self.CARD_H), key, label))
                    y += self.CARD_H + self.GAP
                y += 10
        return out

    def buy_headings(self) -> list[tuple[str, int, int]]:
        groups = self.buy_groups()
        out = []
        left = (self.w - len(self.BUY_COLUMNS) * (self.CARD_W + self.GAP) + self.GAP) // 2
        for ci, col in enumerate(self.BUY_COLUMNS):
            x, y = left + ci * (self.CARD_W + self.GAP), 120
            for g, title in col:
                out.append((title, x, y + 6))
                y += self.HEAD + len(groups.get(g, [])) * (self.CARD_H + self.GAP) + 10
        return out

    def request_at(self, pos: tuple[int, int]) -> str | None:
        for r, item in getattr(self, "request_cards", []):
            if r.collidepoint(pos):
                return item
        return None

    def buy_item_at(self, pos: tuple[int, int]) -> str | None:
        for r, key, _ in self.buy_layout():
            if r.collidepoint(pos):
                return key
        return None

    def item_price(self, me: PlayerState, key: str) -> int:
        m = self.match
        if key in m.weapons:
            return m.weapons[key].price
        if key in m.armor:
            return m.armor[key].price
        return int(m.agents[me.agent]["abilities"].get(key, {}).get("price", 0))

    def item_owned(self, me: PlayerState, key: str) -> bool:
        m = self.match
        if key in m.weapons:
            return any(ws.key == key for ws in me.weapons.values())
        if key in m.armor:
            return me.armor >= m.armor[key].points
        ab = m.agents[me.agent]["abilities"].get(key, {})
        return me.charges.get(key, 0) >= int(ab.get("max", 1))

    def item_picture(self, me: PlayerState, key: str) -> pygame.Surface | None:
        if key in self.match.weapons:
            return self.bank.scaled(f"weapons/val2d/{key}_kauf.png", (112, 42))
        if key in self.match.armor:
            return self.bank.scaled(f"ui/buy/{ {'leicht': 'vest_light', 'schwer': 'vest_heavy'}.get(key, key)}.png", (96, 36))
        return self.bank.scaled(f"ui/faehigkeit_{me.agent}_{key}.png", (36, 36))

    def draw_buy(self, me: PlayerState) -> None:
        """Valorant buy menu: credits and phase timer on top, five columns of cards (picture, name, price), the team's
        credits and weapon requests along the bottom."""
        from client.ui import color
        s, ui, m = self.screen, self.kit, self.match
        ui.fill(s.get_rect(), "#0f1923ee")
        open_ = m.phase == "buy" or m.mode == "deathmatch" or m.practice
        ui.text("Buy", (40, 30), "xl", "text", upper=True, bold=True, kind="title")
        if m.phase == "buy":
            left = m.phase_time_left()
            ui.text(f"buy phase ends in {int(left)} s", (40, 84), "xs", "muted", upper=True)
        elif not open_:
            ui.text("only in the buy phase, in spawn", (40, 84), "xs", "enemy", upper=True)
        coin = self.bank.scaled("ui/hud/credits.png", (22, 22))
        cw = ui.size(str(me.credits), "xl", bold=True, kind="numbers")[0]
        if coin is not None:
            s.blit(coin, (self.w - 40 - cw - 30, 44))
        ui.text(f"{me.credits}", (self.w - 40, 30), "xl", "text", "right", bold=True, kind="numbers")
        for title, x, y in self.buy_headings():
            ui.text(title, (x, y), "xs", "muted", upper=True, bold=True)
        mouse = pygame.mouse.get_pos()
        for r, key, label in self.buy_layout():
            price = self.item_price(me, key)
            owned = self.item_owned(me, key)
            affordable = me.credits >= price and open_
            hover = r.collidepoint(mouse) and affordable and not owned
            ui.fill(r, "text" if hover else "panel_light" if owned else "panel")
            ink = "bg" if hover else "text" if affordable or owned else "muted"
            pic = self.item_picture(me, key)
            if pic is not None:
                if not affordable and not owned:
                    pic = pic.copy()
                    pic.fill((110, 110, 110, 255), special_flags=pygame.BLEND_RGBA_MULT)
                s.blit(pic, (r.right - pic.get_width() - 10, r.y + (r.h - pic.get_height()) // 2))
            name = label.rsplit("  ", 1)[0]
            ui.text(name, (r.x + 10, r.bottom - 22), "xs", ink, upper=True, bold=True)
            ui.text("owned" if owned else str(price), (r.x + 10, r.y + 8), "xs",
                    "ally" if owned and not hover else ink if not affordable else "bg" if hover else "gold", bold=True)
            if owned:
                pygame.draw.rect(s, color("ally"), (r.x, r.y, 3, r.h))
        self.draw_team_strip(me, open_)

    def draw_team_strip(self, me: PlayerState, open_: bool) -> None:
        """Bottom: each teammate's credits and the weapon they asked for, with a button to buy it for them."""
        s, ui, m = self.screen, self.kit, self.match
        self.request_cards = []
        mates = sorted((p for p in m.players.values() if p.team == me.team and p.pid != me.pid), key=lambda p: p.pid)
        y = self.h - 64
        ui.fill(pygame.Rect(0, y - 8, self.w, 72), "panel")
        ui.text("Team", (40, y + 4), "xs", "muted", upper=True)
        x = 110
        for mate in mates[:4]:
            r = pygame.Rect(x, y, 270, 48)
            ui.fill(r, "panel_light")
            pic = self.bank.scaled(f"agents/{mate.agent}/{mate.agent}_killfeed.png", (32, 32))
            if pic is not None:
                s.blit(pic, (r.x + 6, r.y + 8))
            ui.text(mate.name[:12], (r.x + 46, r.y + 6), "xs", "text", bold=True)
            ui.text(str(mate.credits), (r.x + 46, r.y + 26), "xs", "gold")
            d = m.weapons.get(mate.request) if mate.request else None
            if d is not None:
                affordable = me.credits >= d.price and open_
                b = pygame.Rect(r.right - 132, r.y + 8, 124, 32)
                ui.button(b, f"buy {d.name}", f"gift:{mate.pid}:{mate.request}", primary=affordable, enabled=affordable, size="xs")
                self.request_cards.append((b, f"gift:{mate.pid}:{mate.request}"))
            x += 280
        hint = "click buys · right click asks the team for a weapon · B or Esc closes"
        if me.request:
            asked = m.weapons.get(me.request)
            hint = f"you asked for {asked.name if asked else me.request} · " + hint
        ui.text(hint, (self.w - 40, y - 26), "xs", "muted", "right", upper=True)
