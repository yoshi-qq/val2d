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
        """Columns by category; each card: picture, name, price. Owned items carry a teammate-coloured edge,
        unaffordable ones are dimmed. Credits top right, team requests above the columns."""
        from client.ui import color
        s, ui, m = self.screen, self.kit, self.match
        ui.fill(s.get_rect(), "#0f1923ee")
        open_ = m.phase == "buy" or m.mode == "deathmatch" or m.practice
        ui.text("Buy", (60, 40), "xl", "text", upper=True, bold=True, kind="title")
        if not open_:
            ui.text("only in the buy phase, in spawn", (190, 62), "s", "muted", upper=True)
        ui.text(f"{me.credits}", (self.w - 60, 44), "xl", "gold", "right", bold=True, kind="numbers")
        ui.text("credits", (self.w - 60, 96), "xs", "muted", "right", upper=True)
        col_w, gap = 158, 8
        left = (self.w - len(self.BUY_COLUMNS) * (col_w + gap) + gap) / 2
        for ci, (cat, title) in enumerate(self.BUY_COLUMNS):
            x = left + ci * (col_w + gap)
            ui.text(title, (x, 124), "s", "muted", upper=True, bold=True)
            ui.line((x, 144), (x + col_w, 144))
        mouse = pygame.mouse.get_pos()
        for r, key, label in self.buy_layout():
            price = self.item_price(me, key)
            owned = self.item_owned(me, key)
            affordable = me.credits >= price and open_
            hover = r.collidepoint(mouse) and affordable and not owned
            ui.fill(r, "panel_light" if hover else "panel")
            ui.outline(r, "text" if hover else "line")
            if owned:
                pygame.draw.rect(s, color("ally"), (r.x, r.bottom - 3, r.w, 3))
            pic = self.item_picture(me, key)
            if pic is not None:
                if not affordable and not owned:
                    pic = pic.copy()
                    pic.fill((110, 110, 110, 255), special_flags=pygame.BLEND_RGBA_MULT)
                s.blit(pic, (r.centerx - pic.get_width() / 2, r.y + 4))
            name = label.rsplit("  ", 1)[0]
            ui.text(name, (r.x + 8, r.bottom - 22), "xs", "text" if affordable or owned else "muted", upper=True, bold=True)
            ui.text("owned" if owned else str(price), (r.right - 8, r.bottom - 22), "xs",
                    "ally" if owned else "gold" if affordable else "muted", "right", bold=True)
        ui.text("Click buys · right click asks the team for a weapon · B or Esc closes", (60, self.h - 40), "xs", "muted", upper=True)
        self.request_cards = []
        x = 300
        for mate in sorted((p for p in m.players.values() if p.team == me.team and p.pid != me.pid and p.request),
                           key=lambda p: p.pid):
            d = m.weapons.get(mate.request)
            if d is None:
                continue
            r = pygame.Rect(x, 52, 250, 40)
            affordable = me.credits >= d.price and open_
            ui.button(r, f"Buy {d.name} for {mate.name[:10]}", f"gift:{mate.pid}:{mate.request}", primary=affordable,
                      enabled=affordable, size="xs")
            self.request_cards.append((r, f"gift:{mate.pid}:{mate.request}"))
            x += 260
        if me.request:
            asked = m.weapons.get(me.request)
            ui.text(f"You asked for: {asked.name if asked else me.request}", (self.w - 60, 112), "xs", "gold", "right", upper=True)
