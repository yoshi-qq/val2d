"""Builds the blueprint page docs/design/character-blueprint.html from character_sheet_spec.py and the templates.

Usage: python docs/design/build_blueprint.py   (run character_templates.py first)
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character_sheet_spec import STATES, ZONES  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def strip_cell(agent: str, state: str, scale: int = 4) -> str:
    path = ROOT / "assets" / "agents" / agent / f"{agent}_{state}.png"
    if not path.exists():
        return '<span class="none">–</span>'
    with Image.open(path) as im:
        w, h = im.size
    st = next(s for s in STATES if s.tag == state)
    fw = st.size[0]
    frames = max(1, w // fw)
    fps = st.fps or 4
    return (f'<div class="anim" style="width:{fw * scale}px;height:{h * scale}px;background-image:url({uri(path)});'
            f'background-size:{w * scale}px {h * scale}px;--end:-{w * scale}px;animation-timing-function:steps({frames});'
            f'animation-duration:{frames / fps:.2f}s"></div>')


def states_table() -> str:
    rows = []
    group = ""
    for st in STATES:
        g = st.group if st.group != group else ""
        group = st.group
        fr = f"{st.frames[0]}–{st.frames[1]}" if st.frames[0] != st.frames[1] else str(st.frames[0])
        speed = f"{st.fps:g} fps" if st.fps else ("stretched" if st.tag in ("reload", "equip") else "still")
        need = '<b class="req">required</b>' if st.required else f'<span class="opt">optional → {st.fallback}</span>'
        size = f"{st.size[0]}×{st.size[1]}"
        rows.append(f"<tr><td class='grp'>{g}</td><td><code>{st.tag}</code></td><td>{fr}</td><td>{speed}</td>"
                    f"<td>{'yes' if st.loop else ''}</td><td>{size}</td><td>{need}</td><td>{st.note}</td>"
                    f"<td class='ex'>{strip_cell('omen', st.tag, 3)}</td></tr>")
    return "\n".join(rows)


def zones_table() -> str:
    out = []
    for name, z in ZONES.items():
        (x0, x1), (y0, y1) = z["x"], z["y"]
        w = x1 - x0 + 1
        out.append(f"<tr><td>{name.title()}</td><td>{x0}–{x1}</td><td>{w} px = {w / 16:.2f} m</td><td>{y0}–{y1}</td></tr>")
    return "\n".join(out)


def build() -> str:
    t = HERE / "templates"
    guide = uri(t / "character_guides_x8.png")
    layout = uri(t / "example_omen_sheet.png")
    req = sum(1 for s in STATES if s.required)
    return TEMPLATE.format(guide=guide, layout=layout, zones=zones_table(), states=states_table(), required=req)


TEMPLATE = """<title>Val2d Character Blueprint</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Silkscreen&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono&display=swap">
<style>
:root{{--bg:#16151c;--panel:#1f1e27;--line:#363443;--fg:#e8e6ef;--muted:#9b98aa;--accent:#4fd6c8;--gold:#e0b437;--floor:#2b2a33;color-scheme:dark}}
body{{background:var(--bg);color:var(--fg);font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:15px;line-height:1.55;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:28px 64px}}
main{{max-width:1120px;margin:0 auto;display:flex;flex-direction:column;gap:40px}}
h1,h2{{font-family:Silkscreen,monospace;font-weight:400;margin:0;text-wrap:balance}} h1{{font-size:30px}} h2{{font-size:19px}}
h3{{margin:0;font-size:15px}} p,li{{max-width:72ch}} p{{margin:0}} ul{{margin:0;padding-left:18px}}
.muted{{color:var(--muted)}} code{{font-family:"IBM Plex Mono",monospace;font-size:13px}}
section{{display:flex;flex-direction:column;gap:14px}}
.cols{{display:grid;grid-template-columns:minmax(0,auto) minmax(0,1fr);gap:24px;align-items:start}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}}
.card{{background:var(--panel);border:1px solid var(--line);padding:14px 16px;display:flex;flex-direction:column;gap:6px;min-width:0}}
.card b{{font-family:"IBM Plex Mono",monospace;font-weight:500}}
img.px,.anim{{image-rendering:pixelated;display:block;max-width:100%}}
.anim{{background-repeat:no-repeat;animation-name:play;animation-iteration-count:infinite}}
@keyframes play{{from{{background-position:0 0}}to{{background-position:var(--end) 0}}}}
@media (prefers-reduced-motion:reduce){{.anim{{animation:none}}}}
.tbl{{overflow-x:auto;border:1px solid var(--line)}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:middle}}
th{{font-family:"IBM Plex Mono",monospace;font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);background:var(--panel)}}
td.grp{{font-family:Silkscreen,monospace;font-size:12px;color:var(--accent);white-space:nowrap}}
td.ex{{background:var(--floor)}}
.req{{color:var(--accent);font-weight:600}} .opt{{color:var(--muted)}} .none{{color:var(--muted)}}
.legend{{display:flex;flex-direction:column;gap:6px;font-size:14px}}
.legend span{{display:inline-block;width:12px;height:12px;margin-right:8px;vertical-align:-1px}}
pre{{background:var(--panel);border:1px solid var(--line);padding:12px 14px;overflow-x:auto;margin:0}}
@media (max-width:720px){{.cols{{grid-template-columns:minmax(0,1fr)}}}}
</style>
<main>
<header style="display:flex;flex-direction:column;gap:10px">
  <h1>Val2d Character Blueprint</h1>
  <p class="muted">Everything needed to draw an agent's sprite sheets by hand in Aseprite. The examples use Omen; the file <code>docs/design/CHARACTER_SHEETS.md</code> has the same rules as text. {required} states are required, everything else has a fallback.</p>
</header>

<section>
  <h2>Grid and hit zones</h2>
  <div class="cols">
    <img class="px" src="{guide}" width="128" height="256" alt="16 by 32 guide cell with hit zones">
    <div style="display:flex;flex-direction:column;gap:14px;min-width:0">
      <div class="legend">
        <div><span style="background:rgba(238,76,74,.5)"></span>Head zone</div>
        <div><span style="background:rgba(224,180,55,.5)"></span>Body zone (torso and arms)</div>
        <div><span style="background:rgba(79,214,200,.5)"></span>Leg zone</div>
        <div><span style="background:#fff"></span>Cross = cell centre = player position · line = ground row 30 · edges = columns 0 and 15 stay free</div>
      </div>
      <div class="tbl"><table><thead><tr><th>Zone</th><th>Columns</th><th>Width</th><th>Rows</th></tr></thead><tbody>{zones}</tbody></table></div>
      <p class="muted">The game computes head, body and leg hits from these widths, so the silhouette must match them. Hair or helmets may poke out one pixel; the face stays inside.</p>
    </div>
  </div>
</section>

<section>
  <h2>Look</h2>
  <div class="cards">
    <div class="card"><b>16 × 32, upright</b><span class="muted">16 px = 1 m. Always front-facing; the game never rotates figures and shows the facing with a line.</span></div>
    <div class="card"><b>Darker-shade outline</b><span class="muted">1 px, about 45 % of the bordering colour. No black outline.</span></div>
    <div class="card"><b>Two shading steps</b><span class="muted">Base and shadow per material, light from the top left.</span></div>
    <div class="card"><b>≤ 20 drawn colours</b><span class="muted">Outline, enemy variant and glow in ability frames don't count.</span></div>
    <div class="card"><b>Team-neutral</b><span class="muted">Keep teal #4fd6c8 and red #ee4c4a off large areas. Enemy outlines are generated.</span></div>
    <div class="card"><b>No guns, no effects</b><span class="muted">Weapon, muzzle flash, bomb and ability effects are drawn by the game. Draw hands and poses.</span></div>
  </div>
</section>

<section>
  <h2>States</h2>
  <p class="muted">One Aseprite tag per state; the tag name is the state name. Abilities each need their own animation (C, Q, E, X).</p>
  <div class="tbl"><table>
    <thead><tr><th>Group</th><th>State</th><th>Frames</th><th>Speed</th><th>Loops</th><th>Cell</th><th>Needed</th><th>What it shows</th><th>Omen</th></tr></thead>
    <tbody>{states}</tbody>
  </table></div>
</section>

<section>
  <h2>Special mechanics</h2>
  <div class="tbl"><table>
    <thead><tr><th>Building block</th><th>File</th><th>Frames</th><th>Falls back to</th><th>Use for</th></tr></thead>
    <tbody>
      <tr><td>Extra state</td><td><code>{{key}}_mech_{{name}}.png</code></td><td>1–6, 16×32, loops</td><td>idle</td><td>poses only this mechanic has: gliding, hovering, carrying, riding a dash, stunned</td></tr>
      <tr><td>Form</td><td><code>{{key}}@{{form}}_{{state}}.png</code></td><td>like the normal state</td><td>normal state</td><td>the whole look changes while something is active: ult transformation, disguise, armoured mode. Draw at least idle and walk</td></tr>
      <tr><td>Overlay</td><td><code>{{key}}_overlay_{{name}}.png</code></td><td>1, or as many as walk</td><td>none</td><td>a layer on top of every state: glowing eyes, shield shell, burning, frozen, a mark</td></tr>
    </tbody>
  </table></div>
  <p class="muted">See-through, invisible and tinted looks are done by the game with transparency and tint, so they need no sprites. Forms may use up to 8 extra colours.</p>
</section>

<section>
  <h2>Files and workflow</h2>
  <ul>
    <li><code>assets/agents/{{key}}/{{key}}.aseprite</code> holds all 16×32 states as tags; dead (32×16) and portrait (32×32) get their own files.</li>
    <li>Layers: <code>guides</code> (locked, hidden on export, from <code>docs/design/templates/character_guides.png</code>), <code>body</code>, optional <code>fx</code>.</li>
    <li>Export every tag as a horizontal strip <code>{{key}}_{{tag}}.png</code> without spacing. The command below is untested.</li>
  </ul>
  <pre><code>aseprite -b assets/agents/vesper/vesper.aseprite --ignore-layer guides --split-tags --sheet-type horizontal --sheet assets/agents/vesper/vesper_{{tag}}.png
python docs/design/check_agent_sprites.py vesper</code></pre>
  <p class="muted">The check writes the red enemy variants and lists problems: size, frame count, free columns, reserved colours, colour budget.</p>
</section>

<section>
  <h2>Sheet layout with Omen</h2>
  <p class="muted">Light slots are the minimum frame count, dark slots are optional extra frames. Empty rows are optional states Omen doesn't have yet.</p>
  <div class="tbl" style="border:0"><img class="px" src="{layout}" alt="Every state as a row with its frame slots, filled with Omen's frames" style="max-width:none"></div>
</section>
</main>"""


if __name__ == "__main__":
    out = HERE / "character-blueprint.html"
    out.write_text(build(), encoding="utf-8")
    print("written:", out.relative_to(ROOT))
