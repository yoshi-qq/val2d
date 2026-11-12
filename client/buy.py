"""Buy menu."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)


class BuyMixin:
    BUY_COLUMNS = (("sidearm", "Sidearms"), ("smg", "SMGs"), ("shotgun", "Shotguns"), ("rifle", "Rifles"),
                   ("sniper", "Snipers"), ("heavy", "Heavy"), ("gear", "Gear"))

    def buy_layout(self) -> list[tuple[pygame.Rect, str, str]]:
        """Cards per column: weapons by category, then armor and the agent's buyable abilities under Gear."""
        m = self.match
        columns: dict[str, list[tuple[str, str]]] = {c: [] for c, _ in self.BUY_COLUMNS}
        for key, d in sorted(m.weapons.items(), key=lambda kv: kv[1].price):
            if d.slot != "melee":
                columns.setdefault(d.category if d.category in columns else "rifle", []).append((key, f"{d.name}  {d.price}"))
        for key, a in m.armor.items():
            columns["gear"].append((key, f"{a.name}  {a.price}"))
        me = m.players.get(self.me)
        for k in (("C", "Q") if me else ()):
            ab = m.agents[me.agent]["abilities"][k]
            columns["gear"].append((k, f"{k} {ab['name']}  {ab['price']}"))
        out = []
        col_w, card_h, gap = 158, 76, 8
        left = (self.w - len(self.BUY_COLUMNS) * (col_w + gap) + gap) / 2
        for ci, (cat, _) in enumerate(self.BUY_COLUMNS):
            for ri, (key, label) in enumerate(columns.get(cat, [])):
                out.append((pygame.Rect(left + ci * (col_w + gap), 150 + ri * (card_h + gap), col_w, card_h), key, label))
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
            return self.bank.scaled(f"weapons/val2d/{key}_kauf.png", (128, 48))
        if key in self.match.armor:
            return self.bank.scaled(f"ui/buy/{ {'leicht': 'vest_light', 'schwer': 'vest_heavy'}.get(key, key)}.png", (128, 48))
        return self.bank.scaled(f"ui/faehigkeit_{me.agent}_{key}.png", (36, 36))

    def draw_buy(self, me: PlayerState) -> None:
        s = self.screen
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((10, 10, 16, 200))
        s.blit(overlay, (0, 0))
        panel = pygame.Rect(30, 40, self.w - 60, self.h - 80)
        draw_nine_slice(s, self.bank, "ui/menu/panel.png", panel, 6, 3)
        open_ = self.match.phase == "buy"
        self.text("Buy menu" + ("" if open_ else " (only in the buy phase, in spawn)"), (70, 64), C_TEXT, big=True)
        credits_icon = self.bank.scaled("ui/icons/credits_large.png", (32, 32))
        if credits_icon is not None:
            s.blit(credits_icon, (self.w - 260, 66))
        self.text(f"{me.credits}", (self.w - 220, 70), C_SITE, big=True)
        layout = self.buy_layout()
        col_w, gap = 158, 8
        left = (self.w - len(self.BUY_COLUMNS) * (col_w + gap) + gap) / 2
        for ci, (cat, title) in enumerate(self.BUY_COLUMNS):
            x = left + ci * (col_w + gap)
            icon = self.bank.scaled(f"ui/buy/cat_{'abilities' if cat == 'gear' else cat}.png", (32, 32))
            if icon is not None:
                s.blit(icon, (x, 112))
            self.text(title, (x + 38, 118), C_MUTED)
        mouse = pygame.mouse.get_pos()
        for r, key, label in layout:
            price = self.item_price(me, key)
            owned = self.item_owned(me, key)
            affordable = me.credits >= price and open_
            state = "button_disabled" if not affordable and not owned else \
                "button_pressed" if owned else "button_hover" if r.collidepoint(mouse) else "button"
            if not draw_nine_slice(s, self.bank, f"ui/menu/{state}.png", r, 4, 2):
                pygame.draw.rect(s, (60, 58, 72) if state == "button_hover" else (36, 35, 45), r)
                pygame.draw.rect(s, C_MUTED, r, 1)
            pic = self.item_picture(me, key)
            if pic is not None:
                s.blit(pic, (r.centerx - pic.get_width() / 2, r.y + 4))
            name = label.rsplit("  ", 1)[0]
            self.text(name, (r.x + 10, r.bottom - 22), C_TEXT if affordable or owned else C_MUTED)
            cost = self.font.render(str(price), True, C_SITE if affordable else C_MUTED)
            s.blit(cost, (r.right - cost.get_width() - 10, r.bottom - 22))
        self.text("Click buys · right click asks the team for a weapon · B closes", (70, self.h - 76 + 10), C_MUTED)
        self.request_cards = []
        x = 300
        for mate in sorted((p for p in self.match.players.values() if p.team == me.team and p.pid != me.pid and p.request),
                           key=lambda p: p.pid):
            d = self.match.weapons.get(mate.request)
            if d is None:
                continue
            r = pygame.Rect(x, 64, 240, 40)
            affordable = me.credits >= d.price and open_
            if not draw_nine_slice(s, self.bank, f"ui/menu/{'button_hover' if r.collidepoint(mouse) and affordable else 'button' if affordable else 'button_disabled'}.png", r, 4, 2):
                pygame.draw.rect(s, C_MUTED, r, 1)
            self.text(f"Buy {d.name} for {mate.name[:10]}", (r.x + 10, r.y + 11), C_SITE if affordable else C_MUTED)
            self.request_cards.append((r, f"gift:{mate.pid}:{mate.request}"))
            x += 250
        if me.request:
            asked = self.match.weapons.get(me.request)
            self.text(f"You asked for: {asked.name if asked else me.request}", (self.w - 520, 110), C_SITE)
