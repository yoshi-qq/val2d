"""Buy menu."""
from __future__ import annotations

from client.common import *  # noqa: F403  (pygame, colours, types)


class BuyMixin:
    # columns like the real buy menu: each column holds one or two groups stacked
    BUY_COLUMNS = ((("sidearm", "Sidearms"),), (("smg", "SMGs"), ("shotgun", "Shotguns")), (("rifle", "Rifles"),),
                   (("sniper", "Sniper rifles"), ("heavy", "Machine guns")), (("armor", "Shields"),))
    CARD_W, CARD_H, GAP, HEAD = 214, 58, 8, 30
    request_focus: str | None = None

    def buy_teammates(self, me: PlayerState) -> list[PlayerState]:
        return sorted((p for p in self.match.players.values() if p.team == me.team and p.pid != me.pid),
                      key=lambda p: p.pid)[:4]

    def request_navigation_keys(self) -> tuple[int, int]:
        buy = self.keys["buy"]
        return (pygame.K_PAGEDOWN if buy == pygame.K_TAB else pygame.K_TAB,
                pygame.K_KP_ENTER if buy == pygame.K_RETURN else pygame.K_RETURN)

    def buy_request_key(self, me: PlayerState, key: int, modifiers: int, cmd: Command) -> bool:
        if not self.ui.buy_open or self.match.mode == "deathmatch":
            return False
        cycle, confirm = self.request_navigation_keys()
        if key == pygame.K_ESCAPE and self.request_focus:
            self.request_focus = None
            return True
        if key not in (cycle, confirm):
            return False
        requests = {p.gift_action(): self.match.weapons[p.request]
                    for p in self.buy_teammates(me) if p.request in self.match.weapons}
        if key == cycle and requests:
            actions = list(requests)
            backwards = bool(modifiers & pygame.KMOD_SHIFT)
            if self.request_focus in requests:
                index = actions.index(self.request_focus) + (-1 if backwards else 1)
            else:
                index = -1 if backwards else 0
            self.request_focus = actions[index % len(actions)]
            return True
        if key == confirm and self.request_focus:
            weapon = requests.get(self.request_focus)
            if weapon and me.alive and me.credits >= weapon.price and (self.match.phase == "buy" or self.match.practice):
                cmd.buy.append(self.request_focus)
                self.sound.play("ui_buy", gain=0.6)
            self.request_focus = None
            return True
        return False

    def buy_card_metrics(self) -> tuple[int, int, int, int]:
        if self.w < 1120 or self.h < 600:
            return (self.w - 48) // 5, 34, 4, 20
        return self.CARD_W, self.CARD_H, self.GAP, self.HEAD

    def buy_groups(self) -> dict[str, list[tuple[str, str]]]:
        m = self.match
        groups: dict[str, list[tuple[str, str]]] = {g: [] for col in self.BUY_COLUMNS for g, _ in col}
        groups["abilities"] = []
        for key, d in sorted(m.weapons.items(), key=lambda kv: kv[1].price):
            if d.slot not in ("melee", "ability"):
                groups.setdefault(d.category if d.category in groups else "rifle", []).append((key, f"{d.name}  {d.price}"))
        for key, a in m.armor.items():
            groups["armor"].append((key, f"{a.name}  {a.price}"))
        me = m.players.get(self.me)
        for k in (("C", "Q", "E") if me else ()):
            ab = m.agents[me.agent]["abilities"][k]
            if int(ab["price"]) > 0 and not ab.get("shared_charge"):
                label = ab.get("shop_name", f"{k} {ab['name']}")
                groups["abilities"].append((k, f"{label}  {ab['price']}"))
        return groups

    def buy_sections(self) -> list[tuple[str, str, pygame.Rect, list[tuple[str, str]]]]:
        card_w, card_h, gap, head = self.buy_card_metrics()
        compact = card_h < self.CARD_H
        top = 54 if compact else 120
        if self.match.mode == "deathmatch":
            stages = self.match.deathmatch_rules["loadouts"]
            left = (self.w - len(stages) * (card_w + gap) + gap) // 2
            sections = []
            for number, options in enumerate(stages, 1):
                x = left + (number - 1) * (card_w + gap)
                cards = [(f"tdm{number}:{key}", self.match.armor[shield].name if shield else "No shield")
                         for key, shield in options.items()]
                sections.append(("loadout", f"Stage {number}", pygame.Rect(x, top, card_w, head - 4), cards))
            return sections
        groups = self.buy_groups()
        sections = []
        left = (self.w - len(self.BUY_COLUMNS) * (card_w + gap) + gap) // 2
        for ci, col in enumerate(self.BUY_COLUMNS):
            x, y = left + ci * (card_w + gap), top
            for g, title in col:
                items = groups[g]
                sections.append((g, title, pygame.Rect(x, y, card_w, head - 4), items))
                y += head + len(items) * (card_h + gap) + (4 if compact else 10)
        abilities = groups["abilities"]
        if abilities:
            width = len(abilities) * (card_w + gap) - gap
            sections.append(("abilities", "Abilities",
                             pygame.Rect((self.w - width) // 2, self.h - (136 if compact else 204), width, head - 4), abilities))
        return sections

    def buy_layout(self) -> list[tuple[pygame.Rect, str, str]]:
        """Use the same card rectangles for drawing and input."""
        cards = []
        card_w, card_h, gap, head = self.buy_card_metrics()
        for group, _, header, items in self.buy_sections():
            for i, (key, label) in enumerate(items):
                x, y = header.x, header.y + head
                if group == "abilities":
                    x += i * (card_w + gap)
                else:
                    y += i * (card_h + gap)
                cards.append((pygame.Rect(x, y, card_w, card_h), key, label))
        return cards

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

    @staticmethod
    def charge_sell_rect(card: pygame.Rect) -> pygame.Rect:
        if card.h < 58:
            return pygame.Rect(card.right - 58, card.y + 1, 57, 16)
        return pygame.Rect(card.right - 72, card.bottom - 26, 72, 26)

    def buy_action_at(self, me: PlayerState, key: str, pos: tuple[int, int]) -> str | None:
        if self.match.mode == "deathmatch":
            return key if self.match.can_select_deathmatch_loadout(me) else None
        sellable = self.item_sellable(me, key)
        if key in ("C", "Q", "E"):
            if sellable and any(item == key and self.charge_sell_rect(card).collidepoint(pos)
                                for card, item, _ in self.buy_layout()):
                return f"sell:{key}"
        elif sellable:
            return f"sell:{key}"
        return None if self.item_owned(me, key) else f"buy:{key}"

    def item_sellable(self, me: PlayerState, key: str) -> bool:
        """Bought this buy phase and still held: a click sells it back."""
        if self.mode == "client":
            return key in me.remote_sellable
        return self.match.sellable(me, key)

    def item_owned(self, me: PlayerState, key: str) -> bool:
        m = self.match
        if key in m.weapons:
            return any(ws.key == key for ws in me.weapons.values())
        if key in m.armor:
            return m.armor_owned(me, key)
        ab = m.agents[me.agent]["abilities"].get(key, {})
        return me.charges.get(key, 0) >= int(ab.get("max", 1))

    def item_picture(self, me: PlayerState, key: str) -> pygame.Surface | None:
        if key in self.match.weapons:
            art, skin = self.weapon_art(key), self.weapon_skins.get(key, "")
            if skin:
                return self.bank.weapon(art, (116, 34), skin, view="preview")
            return self.kit.silhouette(f"weapons/val2d/{art}_buy.png", (116, 34))
        if key in self.match.armor:
            art = {"light_armor": "vest_light", "heavy_armor": "vest_heavy"}.get(key, key)
            return self.bank.scaled(f"ui/buy/{art}.png", (96, 36))
        return self.bank.scaled(f"ui/ability_{me.agent}_{key}.png", (36, 36))

    def draw_buy(self, me: PlayerState) -> None:
        """Valorant buy menu: credits and phase timer on top, five columns of cards (picture, name, price), the team's
        credits and weapon requests along the bottom."""
        s, ui, m = self.screen, self.kit, self.match
        ui.fill(s.get_rect(), "#0f1923ee")
        if m.mode == "deathmatch":
            self.draw_deathmatch_loadouts(me)
            return
        open_ = m.phase == "buy" or m.practice
        compact = self.buy_card_metrics()[1] < self.CARD_H
        margin, title_y, sub_y, title_size = (16, 4, 36, "l") if compact else (40, 30, 84, "xl")
        ui.text("Buy", (margin, title_y), title_size, "text", upper=True, bold=True, kind="title")
        if m.phase == "buy":
            left = m.phase_time_left()
            ui.text(f"buy phase ends in {int(left)} s", (margin, sub_y), "xs", "muted", upper=True)
        elif not open_:
            ui.text("only in the buy phase, in spawn", (margin, sub_y), "xs", "enemy", upper=True)
        coin = self.bank.scaled("ui/hud/credits.png", (22, 22))
        cw = ui.size(str(me.credits), title_size, bold=True, kind="numbers")[0]
        if coin is not None:
            s.blit(coin, (self.w - margin - cw - 30, title_y + (5 if compact else 14)))
        ui.text(f"{me.credits}", (self.w - margin, title_y), title_size, "text", "right", bold=True, kind="numbers")
        if asked := m.weapons.get(me.request):
            ui.text(f"Requested: {asked.name} · right click again to cancel",
                    (self.w - margin, sub_y), "xs", "ally", "right", upper=True)
        for group, title, header, _ in self.buy_sections():
            ui.skin("menu/tab", header)
            size = 12 if compact else 20
            ui.sprite(f"buy/cat_{group}", pygame.Rect(header.x + 6, header.y + 2, size, size))
            ui.text(title, (header.x + size + 12, header.y + (1 if compact else 5)), "xs", "text", upper=True, bold=True)
        mouse = pygame.mouse.get_pos()
        for r, key, label in self.buy_layout():
            price = self.item_price(me, key)
            ability = key in ("C", "Q", "E")
            owned = self.item_owned(me, key)
            sell = (owned or ability) and self.item_sellable(me, key)
            affordable = me.credits >= price and open_ and (key not in m.armor or m.armor_available(me, key))
            hover = r.collidepoint(mouse) and ((affordable and not owned) or sell)
            skin = "card_hover" if hover else "card_owned" if owned else "card" if affordable else "card_locked"
            ui.skin(f"buy/{skin}", r)
            ink = "text" if affordable or owned else "muted"
            pic = self.item_picture(me, key)
            if pic is not None:
                if compact:
                    bounds = pic.get_rect().fit(pygame.Rect(0, 0, 57, 16))
                    pic = pygame.transform.scale(pic, bounds.size)
                if not affordable and not owned:
                    pic = pic.copy()
                    pic.set_alpha(100)
                if not (compact and ability and sell):
                    s.blit(pic, (r.right - pic.get_width() - 8, r.y + (9 if compact else 24) - pic.get_height() // 2))
            name = label.rsplit("  ", 1)[0]
            name_pos = r.x + (6 if compact else 10), r.bottom - (15 if compact else 22)
            ui.text(name, name_pos, "xs", ink, upper=True, bold=True)
            if ability:
                limit = m.agents[me.agent]["abilities"][key]["max"]
                count = f"{me.charges.get(key, 0)}/{limit}"
                separator = " " if compact else "  ·  "
                label = count + (f"{separator}{price}" if not owned else "")
                if sell:
                    sell_rect = self.charge_sell_rect(r)
                    if compact:
                        ui.outline(sell_rect, "ally", 1)
                    refund = f"+{price}" if compact else f"sell +{price}"
                    ui.text(refund, (sell_rect.right - (3 if compact else 8), sell_rect.y + (1 if compact else 4)),
                            "xs", "ally", "right")
            else:
                label = f"sell +{price}" if sell else "owned" if owned else str(price)
            ui.text(label, (name_pos[0], r.y + (2 if compact else 8)), "xs",
                    "ally" if sell or owned else ink, bold=True)
        self.draw_team_strip(me, open_)

    def draw_deathmatch_loadouts(self, me: PlayerState) -> None:
        m, ui = self.match, self.kit
        self.request_cards = []
        compact = self.buy_card_metrics()[1] < self.CARD_H
        ui.text("Team Deathmatch loadouts", (16, 4) if compact else (40, 30), "l" if compact else "xl",
                "text", upper=True, bold=True, kind="title")
        ui.text("Choose a weapon for each stage", (16, 36) if compact else (40, 84), "s", "muted")
        ui.text(f"{pygame.key.name(self.keys['buy'])} or Esc closes", (self.w - 16, 36) if compact else (self.w - 40, 84),
                "xs", "muted", "right", upper=True)
        for number, (_, title, rect, _) in enumerate(self.buy_sections(), 1):
            ui.skin("menu/tab", rect)
            ui.text(title, (rect.x + 8, rect.y + (1 if compact else 4)), "xs" if compact else "s",
                    "ally" if number == m.dm_stage else "muted", upper=True, bold=True)
        mouse = pygame.mouse.get_pos()
        for rect, item, shield in self.buy_layout():
            stage, key = item.split(":")
            index = int(stage[-1]) - 1
            selected = index < len(me.dm_loadout) and me.dm_loadout[index] == key
            skin = "card_owned" if selected else "card_hover" if rect.collidepoint(mouse) else "card"
            ui.skin(f"buy/{skin}", rect)
            picture = self.item_picture(me, key)
            if picture is not None:
                if compact:
                    picture = pygame.transform.scale(picture, picture.get_rect().fit(pygame.Rect(0, 0, 53, 15)).size)
                self.screen.blit(picture, (rect.right - picture.get_width() - 10, rect.y + 4))
            ui.text(shield, (rect.x + 8, rect.y + (2 if compact else 9)), "xs", "ally" if selected else "muted")
            ui.text(m.weapons[key].name, (rect.x + 8, rect.bottom - (15 if compact else 22)),
                    "xs", "text", upper=True, bold=True)

    def draw_team_strip(self, me: PlayerState, open_: bool) -> None:
        """Bottom: each teammate's credits and the weapon they asked for, with a button to buy it for them."""
        s, ui, m = self.screen, self.kit, self.match
        self.request_cards = []
        mates = self.buy_teammates(me)
        compact = self.buy_card_metrics()[1] < self.CARD_H
        y = self.h - (42 if compact else 64)
        ui.fill(pygame.Rect(0, y - 8, self.w, 72), "panel")
        ui.text("Team", (12 if compact else 40, y + 4), "xs", "muted", upper=True)
        x = 54 if compact else 110
        width = (self.w - x - 24) // 4 if compact else 270
        mouse = pygame.mouse.get_pos()
        hovered_request = keyboard_request = ""
        for mate in mates:
            r = pygame.Rect(x, y, width, 36 if compact else 48)
            ui.fill(r, "panel_light")
            icon = 18 if compact else 32
            pic = self.bank.scaled(f"agents/{mate.agent}/{mate.agent}_killfeed.png", (icon, icon))
            if pic is not None:
                s.blit(pic, (r.x + 6, r.y + 8))
            label_x = r.x + (27 if compact else 46)
            label = mate.name[:12]
            if compact and mate.request:
                available = r.right - 98 - label_x
                if ui.size(label, "xs", bold=True)[0] > available:
                    while label and ui.size(label + "…", "xs", bold=True)[0] > available:
                        label = label[:-1]
                    label += "…"
            ui.text(label, (label_x, r.y + 3), "xs", "text", bold=True)
            ui.text(str(mate.credits), (label_x, r.y + (18 if compact else 26)), "xs", "gold")
            d = m.weapons.get(mate.request) if mate.request else None
            if d is not None:
                if compact and r.collidepoint(mouse):
                    hovered_request = f"{mate.name} requested {d.name}"
                affordable = me.credits >= d.price and open_
                b = pygame.Rect(r.right - 94, r.y + 7, 90, 22) if compact else pygame.Rect(r.right - 132, r.y + 8, 124, 32)
                action = mate.gift_action()
                ui.button(b, f"buy {d.name}", action, primary=affordable, enabled=affordable, size="xs")
                self.request_cards.append((b, action))
                if action == self.request_focus:
                    ui.outline(b.inflate(4, 4), "text", 2)
                    keyboard_request = f"{mate.name} requested {d.name}"
                    if not affordable:
                        keyboard_request += f" · {d.price} credits" if open_ else " · buying closed"
            x += width + (4 if compact else 10)
        close = pygame.key.name(self.keys["buy"])
        hint = (f"click buys or refunds (+) · right click requests · {close} or Esc closes" if compact
                else f"left click buys or sells · right click requests weapons · {close} or Esc closes")
        if not keyboard_request:
            self.request_focus = None
        if self.request_cards:
            cycle, confirm = map(pygame.key.name, self.request_navigation_keys())
            detail_y = y - (37 if compact else 46)
            ui.fill(pygame.Rect(12, detail_y, self.w - 24, 17), "panel")
            ui.text(keyboard_request or hovered_request, (20, detail_y + 2), "xs", "text", bold=True)
            keys = f"{cycle}: next · {confirm}: buy · Esc: clear focus" if keyboard_request else f"{cycle}: focus team requests"
            ui.text(keys, (self.w - 20, detail_y + 2), "xs", "muted", "right", upper=True)
        ui.text(hint, (self.w - (16 if compact else 40), y - (18 if compact else 26)), "xs", "muted", "right", upper=True)
