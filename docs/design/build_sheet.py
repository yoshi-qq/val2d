"""Builds the sprite sheet page (docs/design/sprite-bogen.html) from the PNGs under assets/.

Usage: python docs/design/build_sheet.py
Weapon and ability names are read from gameplay/data so the page follows the game data.
"""
from __future__ import annotations

import base64
import json
import runpy
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "sprite-bogen.html"


def uri(rel: str) -> str:
    return "data:image/png;base64," + base64.b64encode((ROOT / rel).read_bytes()).decode()


def size(rel: str) -> tuple[int, int]:
    with Image.open(ROOT / rel) as im:
        return im.size


def img(rel: str, scale: int, label: str) -> str:
    w, h = size(rel)
    return (f'<figure><img src="{uri(rel)}" width="{w * scale}" height="{h * scale}" alt="{label}">'
            f'<figcaption>{label}<span>{w}×{h}</span></figcaption></figure>')


def anim(rel: str, frames: int, scale: int, label: str, fps: int = 8) -> str:
    w, h = size(rel)
    fw = w // frames
    style = (f"width:{fw * scale}px;height:{h * scale}px;background-image:url({uri(rel)});"
             f"background-size:{w * scale}px {h * scale}px;--steps:{frames};--end:-{w * scale}px;"
             f"animation-duration:{frames / fps}s")
    return (f'<figure><div class="anim" style="{style}"></div>'
            f'<figcaption>{label}<span>{fw}×{h} · {frames} frames · {fps}/s</span></figcaption></figure>')


def section(title: str, note: str, items: list[str]) -> str:
    small = f" <small>{note}</small>" if note else ""
    return f'<section><h2>{title}{small}</h2><div class="row">{"".join(items)}</div></section>'


def load(rel: str) -> dict:
    try:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def config_dict(name: str, probe: str) -> dict:
    """Finds the dict in config/{name}.py that contains the probe key."""
    try:
        data = runpy.run_path(str(ROOT / "config" / f"{name}.py"))
    except Exception as exc:  # the sheet must still build without config
        print(f"warning: config/{name}.py not readable: {exc}")
        return {}
    for value in data.values():
        if isinstance(value, dict) and probe in value:
            return value
    return {}


def build() -> str:
    agents = config_dict("agents", "kestrel")
    weapons = config_dict("weapons", "spatz")
    parts: list[str] = []
    on_disk = sorted(p.name for p in (ROOT / "assets" / "agents").iterdir() if (p / f"{p.name}_idle.png").exists() and p.name != "omen")
    for key in list(agents) + [k for k in on_disk if k not in agents]:
        info = agents.get(key, {})
        name, role = info.get("name", key.title()), info.get("role", "")
        a = f"assets/agents/{key}/{key}"
        parts.append(section(f"{name}", role, [
            img(f"{a}_portrait.png", 4, "Portrait"),
            img(f"{a}_idle.png", 5, "Idle"),
            anim(f"{a}_walk.png", 4, 5, "Walk"),
            img(f"{a}_crouch.png", 5, "Crouch"),
            img(f"{a}_jump.png", 5, "Jump"),
            img(f"{a}_dead.png", 5, "Dead"),
            anim(f"{a}_shoot.png", 2, 5, "Shoot", 12),
            anim(f"{a}_reload.png", 4, 5, "Reload", 6),
            anim(f"{a}_cast_c.png", 3, 5, "Ability C"),
            anim(f"{a}_cast_q.png", 3, 5, "Ability Q"),
            anim(f"{a}_cast_e.png", 3, 5, "Ability E"),
            anim(f"{a}_cast_x.png", 5, 5, "Ultimate X"),
            img(f"{a}_idle_feind.png", 5, "As enemy"),
            anim(f"{a}_walk_feind.png", 4, 5, "Enemy walking"),
        ]))
    guns = [img(f"assets/weapons/val2d/{k}_kauf.png", 2, w.get("name", k)) for k, w in weapons.items() if k != "messer"]
    guns.append(img("assets/weapons/val2d/messer_kauf.png", 2, weapons.get("messer", {}).get("name", "Knife")))
    parts.append(section("Weapons", "buy menu 64×24, in hand 16×8", guns))
    t = "assets/maps/werkhof/"
    parts.append(section("Tiles: Werkhof", "32×32 = 2 m", [img(t + f, 4, l) for f, l in (
        ("boden_stein.png", "Stone floor"), ("wand.png", "Thick wall"), ("wand_duenn.png", "Thin wall"),
        ("kiste_metall.png", "Metal crate"), ("plattform.png", "Platform"), ("rampe.png", "Ramp"),
        ("platz_rand.png", "Site border"))]))
    fx = "assets/fx/"
    parts.append(section("Bomb and effects", "", [
        anim(fx + "spike.png", 2, 6, "Bomb blinking", 4), anim(fx + "muendung.png", 3, 10, "Muzzle flash", 15),
        img(fx + "dunst.png", 3, "Smoke"), img(fx + "bann.png", 3, "Slow field"), img(fx + "schleier.png", 6, "Vapor wall segment"),
        img(fx + "funke.png", 6, "Flash"), img(fx + "lauscher.png", 10, "Sensor")]))
    parts.append(section("Effect animations", "", [
        anim(fx + "dunst_aufbau.png", 4, 2, "Smoke forming"), anim(fx + "bann_puls.png", 3, 2, "Slow field pulse", 4),
        anim(fx + "lauscher_puls.png", 3, 3, "Sensor pulse", 6), anim(fx + "funke_explosion.png", 3, 6, "Flash going off", 10),
        anim(fx + "gleiten_spur.png", 3, 4, "Dash trail", 12), anim(fx + "satz_staub.png", 3, 6, "Hop dust", 10),
        anim(fx + "schleier_aufbau.png", 3, 6, "Vapor wall forming"), anim(fx + "spike_explosion.png", 6, 2, "Bomb explosion", 10),
        anim(fx + "einschlag_wand.png", 3, 10, "Wall impact", 15), anim(fx + "treffer_koerper.png", 3, 10, "Body hit", 15)]))
    icons = []
    for key in agents or ("kestrel", "marrow"):
        abil = agents.get(key, {}).get("abilities", {})
        for slot in "CQEX":
            label = f"{agents.get(key, {}).get('name', key)} {slot} · {abil.get(slot, {}).get('name', '')}"
            icons.append(img(f"assets/ui/faehigkeit_{key}_{slot}.png", 3, label))
    parts.append(section("Ability icons", "32×32", icons))
    hud = "assets/ui/hud/"
    parts.append(section("HUD", "icons 16×16, frames 24×24 nine-slice, bars 96×12", [img(hud + f, 4 if f.endswith(("rahmen.png", "rahmen_aktiv.png")) or len(f) < 16 else 2, l) for f, l in (
        ("leben.png", "Health"), ("schild.png", "Shield"), ("credits.png", "Credits"), ("munition.png", "Ammo"),
        ("kopfschuss.png", "Headshot (kill feed)"), ("spike_klein.png", "Bomb (HUD)"), ("uhr.png", "Round timer"),
        ("tot.png", "Eliminated"), ("rahmen.png", "Frame"), ("rahmen_aktiv.png", "Frame selected"),
        ("balken_leben.png", "Health bar"), ("balken_schild.png", "Shield bar"),
        ("balken_fortschritt.png", "Plant/defuse bar"), ("balken_leer.png", "Empty bar"))]))
    mm = "assets/ui/minimap/"
    parts.append(section("Generic effects", "tint zone and blast in code per status", [
        anim(fx + "zone.png", 3, 2, "Zone", 4), anim(fx + "blast.png", 6, 2, "Blast ring", 12),
        img(fx + "tripwire.png", 8, "Tripwire (tile)"), img(fx + "tripwire_node.png", 10, "Tripwire node"),
        anim(fx + "alarm.png", 2, 6, "Alarm", 3), anim(fx + "wave.png", 3, 6, "Wave (tile)", 10)]))
    st = "assets/ui/status/"
    parts.append(section("Status icons", "16×16", [img(st + f"{k}.png", 4, k.title()) for k in (
        "nearsight", "concuss", "slow", "vulnerable", "decay", "suppress", "detain", "deaf", "stim")]))
    for folder, title in (("ui/menu", "Menus"), ("ui/icons", "Interface icons"), ("ui/buy", "Buy menu"),
                          ("maps/common", "Map tiles: common set"), ("maps/common/props", "Map props"),
                          ("maps/common/decals", "Map decals"), ("fx/ability", "Ability sprites"),
                          ("ui/crosshair", "Crosshair"), ("ui/scoreboard", "Scoreboard")):
        items = []
        for f in sorted((ROOT / "assets" / folder).glob("*.png")):
            rel = str(f.relative_to(ROOT)).replace("\\", "/")
            w, h = size(rel)
            scale = 1 if w > 200 else 8 if h <= 8 else 5 if h <= 16 else 3 if h <= 32 else 2
            items.append(img(rel, scale, f.stem.replace("_", " ")))
        parts.append(section(title, "", items))
    parts.append(section("Minimap", "12×12", [img(mm + f"{k}.png", 6, l) for k, l in (
        ("selbst", "You"), ("verbuendet", "Ally"), ("feind", "Enemy"), ("tot", "Eliminated"), ("spike", "Bomb"),
        ("dunst", "Smoke"), ("bann", "Slow field"), ("schleier", "Vapor wall"))]))
    bn = "assets/ui/banner/"
    parts.append(section("Round banners", "height 32 px, game font", [img(bn + f"{k}.png", 3, l) for k, l in (
        ("sieg", "Victory"), ("niederlage", "Defeat"), ("seitenwechsel", "Switching sides"),
        ("spike_gelegt", "Bomb planted"), ("entschaerft", "Bomb defused"), ("verlaengerung", "Overtime"))]))
    logo = section("Logo", "chosen: crosshair; replaces the former Riot logo", [
        img("assets/logo.png", 4, "Logo 48×48"), img("assets/menu/lobby/playercard.png", 2, "Player card"),
        img("assets/logo.png", 1, "Actual size")])
    parts.append(logo)
    return TEMPLATE.replace("{{SECTIONS}}", "\n".join(parts))


TEMPLATE = """<title>Val2d Sprite Sheet</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Silkscreen&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono&display=swap">
<style>
:root{--bg:#16151c;--panel:#1f1e27;--line:#363443;--fg:#e8e6ef;--muted:#9b98aa;--accent:#4fd6c8;--floor:#34323c;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font-family:"IBM Plex Sans",system-ui,sans-serif;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:28px 60px}
main{max-width:1100px;margin:0 auto;display:flex;flex-direction:column;gap:36px}
h1,h2{font-family:Silkscreen,monospace;font-weight:400;margin:0} h1{font-size:28px} h2{font-size:18px}
h2 small{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--muted);margin-left:8px}
p{margin:0;max-width:68ch;color:var(--muted)}
section{display:flex;flex-direction:column;gap:12px}
.row{display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end}
figure{margin:0;background:var(--floor);border:1px solid var(--line);padding:10px;display:flex;flex-direction:column;gap:6px;align-items:flex-start;max-width:100%}
figure img,.anim{image-rendering:pixelated;display:block;max-width:100%;height:auto}
figcaption{font-size:12px;display:flex;flex-direction:column} figcaption span{font-family:"IBM Plex Mono",monospace;color:var(--muted);font-size:11px}
.anim{animation-name:play;animation-timing-function:steps(var(--steps));animation-iteration-count:infinite;background-repeat:no-repeat}
@keyframes play{from{background-position:0 0}to{background-position:var(--end) 0}}
@media (prefers-reduced-motion:reduce){.anim{animation:none}}
</style>
<main>
<header style="display:flex;flex-direction:column;gap:8px"><h1>Val2d Sprite Sheet</h1>
<p>Sprites from the design session, following the concept rules: outline in a darker shade of the neighbouring colour, two shading steps, light from the top left, team-neutral, enemies with a red outline. All figures and items are original designs. 16 px = 1 m.</p></header>
{{SECTIONS}}
</main>"""


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print("written:", OUT.relative_to(ROOT))
