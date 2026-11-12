# Building agents, abilities, statuses and maps

Everything here is a Python file in `config/` or `gameplay/data/maps/`. The game reads them at start; no game code
changes. Broken entries are skipped with a warning that names the problem (the rest of the game keeps working).

| What | Where | Start from |
|---|---|---|
| Balance patch (change any value without touching its file) | `config/patches/<nn_name>.py` | `config/patches/_example.py` |
| Ready-made abilities for any agent | `config/content/abilities/*.py` | `config/content/abilities/library.py` |
| Agent | `config/content/agents/<key>.py` (file name = key) | `config/content/agents/_template.py` |
| Status | `config/content/statuses.py` | one more entry |
| New effect or trigger | `config/content/mechanics/<name>.py` | `config/content/mechanics/swap.py` |
| Map | `gameplay/data/maps/<key>.py` or the map editor (`.json`) | `gameplay/data/maps/_template.py` |
| Rules (movement, economy, rounds, modes) | `config/rules/` | – |
| Hit zones, lobby defaults | `config/settings/` | – |
| Weapons, armor | `config/content/weapons.py` | – |
| Materials, props, decals | `config/content/materials.py` | – |

Files starting with `_` are templates and are never loaded. In a match against bots or in the range, the escape
menu has **Reload content**: agents, abilities, weapons, armor, statuses and patches are read again without
restarting (maps and rules from the next match).

## Balance patches

A file in `config/patches/` changes values of existing content; patches apply in file-name order, so name them
`01_...`, `02_...`. Each has `VERSION`, `NOTES` (shown on the Career page as patch notes) and `PATCH`:

```python
VERSION = "1.02"
NOTES = "Kestrel flash shorter, Hammer more expensive"
PATCH = {
    "agents":   {"kestrel": {"C": {"blind": 1.2}, "X": {"cost": 8}}},
    "weapons":  {"hammer": {"price": 3000}},
    "armor":    {"schwer": {"price": 1100}},
    "statuses": {"slow": {"speed": 0.6}, "frozen": {"speed": 0.1}},   # new statuses too
    "rules":    {"economy": {"start": 900}},
    "settings": {"hit_zones": {"head_half_width": 0.27}},
    "maps":     {"workyard": {"set": {"name": "Workyard"}, "add": {"crates": [[20, 20, 22, 22]]},
                             "remove": {"crates": [[30, 10, 32, 12]]}}},
}
```

`None` removes a field (`"alt": None` takes away a right-click variant). Unknown names are reported as warnings.

## Ability library

`library("name", ...changes)` takes a ready-made ability from `config/content/abilities/`:

```python
C=library("firebomb", price=250),
Q=library("cloak_step"),
```

Included: smoke_orb, flashbang, healing_orb, recon_dart, tripwire, sonic_pulse, earth_wall, poison_cloud, firebomb,
knockback_blast, gravity_well, frost_field, shock_dart, cloak_step, haste_aura, fortify_self, marked_shot,
healing_rain. Add your own in a new file with an `ABILITIES` dict.

## Sounds

Every ability may name its cast sound with `sound="..."`; the effect `sound(key, radius)` plays any sound at a
point (for example when a trap goes off). Cast sounds made by `tools/make_sounds.py`: cast_throw_light,
cast_throw_heavy, cast_deploy, cast_place_trap, cast_charge_up, cast_whoosh, cast_magic, cast_arcane, cast_tech,
cast_heal, cast_buff, cast_shield_up, cast_beam, cast_burst, cast_dark, cast_fire, cast_ice, cast_electric, cast_wind,
cast_poison, cast_sonic, cast_earth, ult_cast. Any other file in `assets/sounds` works too.

## An agent

```python
from gameplay.kit.dsl import *

AGENT = agent("Ember", role="Duelist", order=31,
    C=..., Q=..., E=..., X=...,          # the four abilities
    passives=[on("kill", do=[heal(25, over=2)])],   # optional
    sprites=dict(forms={"X": "overdrive"}),          # optional, docs/design/CHARACTER_SHEETS.md section 5
)
```

Slots: C and Q are bought in the buy phase, E is the signature (free each round), X the ultimate.
Slot values: `price`, `max`, `start` (free charges each round), `recharge` (seconds), `kills_to_recharge`;
X has `cost` (ultimate points) instead. `order` sorts the agent select.

## An ability: preset or composition

**Preset** – a classic building block with its values:

```python
C=preset("smoke", "Haze", price=200, max=2, range=30, radius=2.8, duration=15)
```

| Preset | Values |
|---|---|
| smoke | range, radius, duration, remote (through walls) |
| wall | range, length, duration, cross_status, cross_time |
| flash | range, fuse, blind, cone, through_walls |
| zone | range, radius, duration, delay, dps, status, status_time, reveal, heal_allies |
| blast | range, radius, delay, damage, status, status_time |
| wave | length, width, damage, status, status_time |
| sensor | range, radius, duration, pulse |
| alarm | range, radius, duration, status, status_time |
| tripwire | length, duration, status, status_time |
| dash | distance, duration |
| hop | velocity |
| teleport | range |
| anchor | duration |
| heal | amount, duration, range |
| stim | radius, duration |
| shield | points, range |
| revive | range |
| reveal_all | duration |
| overdrive | duration, rate_mult |
| immunity | duration, regen |
| decoy | duration, speed |

**Right-click variant:** `alt=dict(...)` holds values that replace the normal ones when the ability is cast with the right mouse button (`alt=None`: no variant). Flashes get an underhand throw, charges a lob and walls an `along` variant by default. Abilities that need aiming or have a variant are taken in hand with their key, cast with left or right click and put away with the same key, 1/2/3 or Esc.

The presets are written with the kit themselves (`gameplay/kit/presets.py`); read one to see how a composition looks.

**Composition** – target, steps on use, and an object with triggers:

```python
C=ability("Firebomb", price=200, max=1, target="aim", range=14, preview="zone", bot="offense",
    place=thing("blast", lasts=0.8, radius=3, thrown=True, triggers=[
        on("expire", who="enemies", sight="walls", do=[
            damage(40, falloff=0.5), event("blast"),
            spawn(thing("zone", lasts=4, radius=3, triggers=[on("tick", do=[dps(20), status("burn", 0.5)])])),
        ]),
    ]))
```

- `target`: `aim` (cursor, stops at walls), `aim_free` (through walls), `self`, `ahead` (straight ahead at full range). `range` limits it.
- `do=[...]`: steps run at once. A step returning “cancel” (teleport onto higher ground, revive with nobody there) refunds the charge.
- `place=thing(look, lasts, triggers, ...)`: an object in the world.
  - `look`: smoke, wall, flash, zone, blast, sensor, alarm, tripwire, decoy, none (how it is drawn until the design session delivers more)
  - `delay`, `radius`, `shape="line"` with `length` (across the aim), `thrown` (flies from the user), `clip_ends`,
    `blocks_sight`, `hidden` ("enemies" or "all"), `move` (m/s along the aim)
- `preview`: which preset's aim preview to show while holding the key; `bot`: offense, buff, place, heal or escape.

### Triggers of objects (`on(when, do=[...], ...)`)

| when | fires |
|---|---|
| start | once when the object becomes active (after `delay`) |
| expire | once when its time runs out |
| tick | every frame (use per-second effects: dps, heal_rate) |
| every | every `seconds` |
| enter / leave | a player steps into / out of the area |
| cross | a player crosses the object's line |
| noise | a player makes a sound (running, landing) in the area |
| gunfire | a player fires in the area |

`consume=True` ends the object after it fired; `first=True` takes only the nearest player.

### Passive triggers of agents (`passives=[on(...)]`)

kill, death, damage_dealt, damage_taken, ability_used (`slot=`), every (`seconds=`), low_health (`below=`).
The steps act on the agent by default; `who="other"` is the victim of the kill or the attacker of the hit.

### Choosing players (on a trigger or a step)

- `who`: enemies (default), allies (without the user), team (with the user), self, everyone, others, other,
  cursor_ally (teammate under the cursor, else self), cursor_fallen
- `area`: circle (default when there is a radius), line (the object's line, `width`), beam (from the user along the aim,
  `length`, `width`), everywhere; `radius` overrides the object's
- `sight`: "walls" (walls block) or "all" (smokes block too); `facing`: cone in degrees the player must look into

### Effects (steps)

| Effect | Values |
|---|---|
| damage | amount, falloff (share lost at the edge), zone |
| dps | per_second |
| status | name, seconds |
| heal | amount, over (seconds) |
| heal_rate | per_second |
| shield | points |
| reveal | seconds |
| cleanse | – (removes harmful statuses) |
| immunity | seconds |
| revive | health |
| push / pull | strength (metres) |
| knock_up | velocity |
| dash, hop, teleport, anchor, overdrive | as the presets |
| charge | slot, amount |
| ult_points, credits | amount |
| spawn | place (another object at the point) |
| noise | radius (a fake footstep) |
| event | kind (a visual/sound for the client: blast, flash) |
| end | – (ends this object) |

`step("name", ...)` uses any effect by name, also your own.

## Statuses

`config/content/statuses.py`, one entry each. Modifiers: speed, damage_taken, damage_dealt, fire_rate, reload (factors);
spread_add, hp_per_second (added); sight_range, seen_within (metres, smallest counts); blind, deaf, no_abilities,
revealed, lethal (switches); decay, decay_regen; positive (a buff). Ready to use beside the classic ten:
haste, cloak, fortify, empower, regen, burn, weaken, marked, jammed.

## A new mechanic

```python
# config/content/mechanics/lifesteal.py
from gameplay.kit.registry import effect

@effect("lifesteal")
def lifesteal(ctx, target, step):
    """Damage the target and heal the user by the same amount."""
    if target is None or ctx.owner is None:
        return
    amount = int(step.get("amount", 20))
    ctx.m._damage(ctx.owner, target, amount, "body", "ability:lifesteal")
    ctx.owner.hp = min(100, ctx.owner.hp + amount)
```

Then `step("lifesteal", amount=20)` works in every agent. Registries: `effect`, `trigger`, `target`, `who`,
`preset`, `passive_trigger` (all in `gameplay/kit/registry.py`); the context `ctx` carries the match, the user,
the point, the aim, the object and the frame time.

## A map

```python
from gameplay.mapkit import MapBuilder

b = MapBuilder("Yard", 48, 40, floor="concrete", source="Christian, 12.11.2026")
b.spawn_area(0, 16, 34, 32, 39, points=5, barrier="n")
b.room(4, 10, 20, 24, mat="brick", doors=[("s", 6, 2)]).door(11, 23)
b.platform(8, 12, 14, 15, ramp="s", ramp_width=2)
b.site("A", 5, 11, 19, 23)
MAP = b.build()
```

Helpers: wall, door, floor, crate, crates, room, platform (with ramp), site, spawn, spawn_area, callout, thing, decal,
target, mirror. Ramps rise toward the platform they touch. A `.json` of the same name (saved by the map editor) wins.
