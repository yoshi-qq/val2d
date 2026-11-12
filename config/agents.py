"""Agents and abilities of Val2d. Edit freely; the game reads this file at start.

Every ability is one building block (`kind`) with its own values. You can move blocks between
agents, change values, or add new agents without touching the code.
Source of all values: own design by Claude Code, 11.11.2026 (no official data). Tune freely.

Slots: C and Q are bought in the buy phase, E is the signature (free each round, may recharge),
X is the ultimate (costs `cost` ultimate points).

Common fields:
  name, kind        display name, building block (list below)
  price, max, start buy price, max charges, free charges each round (C, Q, E)
  recharge          seconds until one charge comes back (optional)
  kills_to_recharge kills that give one charge back (optional)
  cost              ultimate points (X only)

Building blocks (kind) and their fields:
  smoke        range, radius, duration, remote(bool: placed anywhere in range, ignoring walls)
  wall         range, length, duration, cross_status, cross_time   (sight-blocking line; optional status on crossing)
  flash        range, fuse, blind, cone, through_walls(bool)
  zone         range, radius, duration, delay, dps, status, status_time, reveal(bool), heal_allies(per s)
  blast        range, radius, delay, damage, status, status_time   (grenade, rocket, airstrike)
  wave         length, width, damage, status, status_time            (line from the user, goes through walls)
  sensor       range, radius, duration, pulse                        (reveals enemies in radius)
  alarm        range, radius, duration, status, status_time          (enemies making noise nearby get the status)
  tripwire     length, duration, status, status_time                 (line at the cursor; crossing reveals + status)
  dash         distance, duration
  hop          velocity
  teleport     range                                                 (to the cursor if the way is clear)
  anchor       duration                                              (first use sets, second use returns)
  heal         amount, duration, range                               (ally under the cursor within range, else self)
  stim         radius, duration                                      (user and allies in radius)
  shield       points, range                                         (temporary armor, ally under cursor or self)
  revive       range                                                 (nearest fallen ally within range)
  reveal_all   duration
  overdrive    duration, rate_mult
  immunity     duration, regen                                       (clears and blocks statuses, heals per s, stim)
  decoy        duration, speed                                       (fake footsteps walking forward)

Statuses (status fields): blind, nearsight, concuss, slow, vulnerable, decay, suppress, detain, deaf, stim.

Optional per agent: sprites=dict(...) for special sprite mechanics (docs/design/CHARACTER_SHEETS.md, section 5):
  forms      {slot: form}   while that ability is active, {key}@{form}_{state}.png replaces the normal state
  mechanics  {slot: name}   while that ability is active, the state {key}_mech_{name}.png is shown
  overlays   [name, ...]    {key}_overlay_{name}.png drawn on top of every state
An ability counts as active for its `duration` after use (or while channel_{slot} would loop).
Example: "kestrel": dict(..., sprites=dict(forms={"X": "overdrive"}, overlays=["scarf"]))
"""

STATUS_RULES = dict(
    nearsight_range=5.0,      # metres an affected player can still see
    concuss_spread=6.0,       # extra spread in degrees
    concuss_speed=0.6,        # movement factor
    slow_speed=0.55,          # movement factor
    vulnerable_mult=1.5,      # damage taken factor
    decay_per_second=15.0,    # health drained while decayed (never below 1)
    decay_regen=10.0,         # health per second given back afterwards
    stim_rate=1.12,           # fire-rate factor
    stim_reload=0.8,          # reload-time factor
)

AGENTS: dict[str, dict] = {
    "kestrel": dict(name="Kestrel", role="Duelist", abilities=dict(
        C=dict(name="Spark", kind="flash", price=250, max=2, start=0, range=12.0, fuse=0.5, blind=1.6, cone=120.0),
        Q=dict(name="Leap", kind="hop", price=150, max=2, start=0, velocity=6.5),
        E=dict(name="Glide", kind="dash", price=0, max=1, start=1, distance=7.0, duration=0.2, kills_to_recharge=2),
        X=dict(name="Overdrive", kind="overdrive", cost=7, duration=8.0, rate_mult=1.15),
    )),
    "marrow": dict(name="Marrow", role="Controller", abilities=dict(
        C=dict(name="Listener", kind="sensor", price=200, max=1, start=0, range=12.0, radius=10.0, duration=30.0, pulse=2.0),
        Q=dict(name="Veil", kind="wall", price=300, max=1, start=0, range=25.0, length=10.0, duration=10.0),
        E=dict(name="Haze", kind="smoke", price=0, max=2, start=2, range=30.0, radius=2.8, duration=15.0, recharge=35.0),
        X=dict(name="Binding", kind="zone", cost=8, range=30.0, radius=7.0, duration=8.0, status="slow", status_time=0.5, reveal=True),
    )),
    "vesper": dict(name="Vesper", role="Duelist", abilities=dict(
        C=dict(name="Footfall", kind="decoy", price=150, max=2, start=0, duration=4.0, speed=5.0),
        Q=dict(name="Slip", kind="teleport", price=250, max=1, start=0, range=8.0),
        E=dict(name="Jolt", kind="blast", price=0, max=1, start=1, range=14.0, radius=3.5, delay=1.0, damage=0,
               status="concuss", status_time=2.5, kills_to_recharge=2),
        X=dict(name="Second Wind", kind="immunity", cost=7, duration=10.0, regen=6.0),
    )),
    "rook": dict(name="Rook", role="Duelist", abilities=dict(
        C=dict(name="Tar", kind="blast", price=200, max=2, start=0, range=12.0, radius=3.0, delay=1.2, damage=15,
               status="slow", status_time=3.0),
        Q=dict(name="Plating", kind="shield", price=200, max=1, start=0, points=30, range=10.0),
        E=dict(name="Charge", kind="dash", price=0, max=1, start=1, distance=6.0, duration=0.25, recharge=30.0),
        X=dict(name="Breach Shell", kind="blast", cost=8, range=40.0, radius=6.0, delay=0.6, damage=160),
    )),
    "tamsin": dict(name="Tamsin", role="Initiator", abilities=dict(
        C=dict(name="Hush", kind="zone", price=200, max=1, start=0, range=20.0, radius=4.0, duration=6.0, delay=0.5,
               status="deaf", status_time=1.0, reveal=True),
        Q=dict(name="Haze Line", kind="wave", price=250, max=1, start=0, length=22.0, width=2.0, damage=0,
               status="nearsight", status_time=3.5),
        E=dict(name="Dart", kind="sensor", price=0, max=1, start=1, range=30.0, radius=8.0, duration=4.0, pulse=1.0,
               recharge=40.0),
        X=dict(name="Shockline", kind="wave", cost=8, length=50.0, width=1.2, damage=80, status="vulnerable", status_time=6.0),
    )),
    "okoro": dict(name="Okoro", role="Initiator", abilities=dict(
        C=dict(name="Glare", kind="flash", price=250, max=2, start=0, range=14.0, fuse=0.35, blind=1.4, cone=140.0,
               through_walls=False),
        Q=dict(name="Mark", kind="zone", price=200, max=1, start=0, range=20.0, radius=3.5, duration=5.0, delay=0.3,
               status="vulnerable", status_time=1.0, reveal=True),
        E=dict(name="Rattle", kind="blast", price=0, max=1, start=1, range=16.0, radius=4.0, delay=0.8, damage=0,
               status="concuss", status_time=2.0, recharge=40.0),
        X=dict(name="Barrage", kind="blast", cost=7, range=60.0, radius=7.0, delay=2.5, damage=150),
    )),
    "juniper": dict(name="Juniper", role="Controller", abilities=dict(
        C=dict(name="Muffle", kind="zone", price=150, max=1, start=0, range=18.0, radius=3.5, duration=8.0,
               status="deaf", status_time=1.0),
        Q=dict(name="Rot", kind="zone", price=200, max=1, start=0, range=18.0, radius=3.0, duration=7.0, dps=0,
               status="decay", status_time=1.0),
        E=dict(name="Cloudcast", kind="smoke", price=0, max=3, start=3, range=40.0, radius=3.0, duration=14.0,
               remote=True, recharge=40.0),
        X=dict(name="Blackout", kind="zone", cost=8, range=30.0, radius=9.0, duration=6.0, delay=1.0,
               status="suppress", status_time=1.0),
    )),
    "nyx": dict(name="Nyx", role="Controller", abilities=dict(
        C=dict(name="Static", kind="blast", price=200, max=1, start=0, range=14.0, radius=4.0, delay=0.8, damage=0,
               status="deaf", status_time=4.0),
        Q=dict(name="Shade", kind="smoke", price=150, max=2, start=0, range=20.0, radius=2.6, duration=12.0),
        E=dict(name="Curtain", kind="wall", price=0, max=1, start=1, range=20.0, length=12.0, duration=12.0,
               cross_status="nearsight", cross_time=2.0, recharge=45.0),
        X=dict(name="Eclipse", kind="smoke", cost=7, range=30.0, radius=8.0, duration=10.0),
    )),
    "harrow": dict(name="Harrow", role="Sentinel", abilities=dict(
        C=dict(name="Snare", kind="tripwire", price=200, max=2, start=0, length=6.0, duration=120.0,
               status="detain", status_time=2.0),
        Q=dict(name="Bell", kind="alarm", price=200, max=1, start=0, range=10.0, radius=5.0, duration=120.0,
               status="concuss", status_time=2.0),
        E=dict(name="Bulwark", kind="shield", price=0, max=1, start=1, points=40, range=12.0, recharge=45.0),
        X=dict(name="Rally", kind="revive", cost=8, range=12.0),
    )),
    "sable": dict(name="Sable", role="Sentinel", abilities=dict(
        C=dict(name="Waypoint", kind="anchor", price=150, max=1, start=0, duration=60.0),
        Q=dict(name="Caltrops", kind="zone", price=200, max=1, start=0, range=10.0, radius=2.5, duration=30.0, dps=8,
               status="slow", status_time=1.0),
        E=dict(name="Mend", kind="heal", price=0, max=1, start=1, amount=60, duration=4.0, range=12.0, recharge=40.0),
        X=dict(name="Watchtower", kind="reveal_all", cost=7, duration=4.0),
    )),
    # ------------------------------------------------------------------ added 12.11.2026 (own kits, own looks)
    "brann": dict(name="Brann", role="Duelist", abilities=dict(
        C=dict(name="Clinker", kind="blast", price=200, max=2, start=0, range=14.0, radius=2.2, delay=0.7, damage=45),
        Q=dict(name="Bellows", kind="hop", price=150, max=1, start=0, velocity=6.0),
        E=dict(name="Forge Step", kind="dash", price=0, max=1, start=1, distance=6.0, duration=0.2, recharge=25.0),
        X=dict(name="Slag Field", kind="zone", cost=7, range=25.0, radius=5.0, duration=7.0, dps=20, status="slow", status_time=0.5),
    )),
    "quill": dict(name="Quill", role="Duelist", abilities=dict(
        C=dict(name="Prick", kind="wave", price=200, max=2, start=0, length=10.0, width=1.0, damage=25, status="vulnerable", status_time=3.0),
        Q=dict(name="Feint", kind="decoy", price=100, max=2, start=0, duration=3.0, speed=5.5),
        E=dict(name="Quill Dart", kind="sensor", price=0, max=1, start=1, range=18.0, radius=5.0, duration=3.0, pulse=0.75, recharge=35.0),
        X=dict(name="Volley", kind="wave", cost=7, length=40.0, width=2.0, damage=70, status="nearsight", status_time=3.0),
    )),
    "sorrel": dict(name="Sorrel", role="Duelist", abilities=dict(
        C=dict(name="Thicket", kind="smoke", price=150, max=2, start=0, range=8.0, radius=2.0, duration=8.0),
        Q=dict(name="Sap", kind="zone", price=150, max=1, start=0, range=12.0, radius=2.5, duration=5.0, status="slow", status_time=0.5),
        E=dict(name="Spring", kind="hop", price=0, max=1, start=1, velocity=7.0, recharge=20.0),
        X=dict(name="Overgrowth", kind="immunity", cost=7, duration=8.0, regen=10.0),
    )),
    "dace": dict(name="Dace", role="Duelist", abilities=dict(
        C=dict(name="Ripple", kind="flash", price=250, max=2, start=0, range=10.0, fuse=0.3, blind=1.2, cone=110.0),
        Q=dict(name="Undertow", kind="teleport", price=250, max=1, start=0, range=6.0),
        E=dict(name="Current", kind="dash", price=0, max=1, start=1, distance=5.0, duration=0.18, kills_to_recharge=1),
        X=dict(name="Riptide", kind="overdrive", cost=7, duration=10.0, rate_mult=1.2),
    )),
    "mako": dict(name="Mako", role="Duelist", abilities=dict(
        C=dict(name="Chum", kind="decoy", price=100, max=2, start=0, duration=4.0, speed=4.5),
        Q=dict(name="Bite", kind="blast", price=250, max=1, start=0, range=10.0, radius=2.0, delay=0.4, damage=50,
               status="concuss", status_time=1.0),
        E=dict(name="Hunt", kind="stim", price=0, max=1, start=1, radius=0.5, duration=6.0, recharge=40.0),
        X=dict(name="Bloodline", kind="reveal_all", cost=8, duration=3.0),
    )),
    "wren": dict(name="Wren", role="Initiator", abilities=dict(
        C=dict(name="Peep", kind="sensor", price=200, max=2, start=0, range=20.0, radius=6.0, duration=6.0, pulse=1.0),
        Q=dict(name="Chirp", kind="flash", price=250, max=1, start=0, range=16.0, fuse=0.6, blind=1.5, cone=130.0),
        E=dict(name="Flit", kind="hop", price=0, max=1, start=1, velocity=6.5, recharge=20.0),
        X=dict(name="Murmuration", kind="zone", cost=8, range=40.0, radius=10.0, duration=5.0, delay=0.8,
               status="nearsight", status_time=1.0, reveal=True),
    )),
    "odile": dict(name="Odile", role="Initiator", abilities=dict(
        C=dict(name="Pirouette", kind="wave", price=200, max=1, start=0, length=14.0, width=2.5, damage=0,
               status="nearsight", status_time=2.5),
        Q=dict(name="Pas", kind="teleport", price=200, max=1, start=0, range=5.0),
        E=dict(name="Grace", kind="shield", price=0, max=1, start=1, points=30, range=12.0, recharge=40.0),
        X=dict(name="Swan Song", kind="zone", cost=7, range=30.0, radius=7.0, duration=6.0, delay=0.5,
               status="vulnerable", status_time=1.0, reveal=True),
    )),
    "pike": dict(name="Pike", role="Initiator", abilities=dict(
        C=dict(name="Hook", kind="blast", price=250, max=1, start=0, range=14.0, radius=2.0, delay=0.5, damage=0,
               status="detain", status_time=1.5),
        Q=dict(name="Lure", kind="decoy", price=100, max=2, start=0, duration=5.0, speed=4.0),
        E=dict(name="Scan", kind="sensor", price=0, max=1, start=1, range=25.0, radius=7.0, duration=4.0, pulse=1.0, recharge=40.0),
        X=dict(name="Harpoon", kind="wave", cost=7, length=45.0, width=1.0, damage=100, status="detain", status_time=2.0),
    )),
    "lark": dict(name="Lark", role="Initiator", abilities=dict(
        C=dict(name="Trill", kind="zone", price=150, max=1, start=0, range=16.0, radius=4.0, duration=6.0, status="deaf", status_time=1.0),
        Q=dict(name="Dawn", kind="flash", price=250, max=2, start=0, range=12.0, fuse=0.8, blind=1.4, cone=140.0, through_walls=True),
        E=dict(name="Lift", kind="stim", price=0, max=1, start=1, radius=6.0, duration=6.0, recharge=40.0),
        X=dict(name="Aria", kind="zone", cost=8, range=30.0, radius=8.0, duration=4.0, delay=1.5, status="concuss", status_time=1.0),
    )),
    "rhea": dict(name="Rhea", role="Initiator", abilities=dict(
        C=dict(name="Tremor", kind="wave", price=250, max=1, start=0, length=12.0, width=3.0, damage=0, status="concuss", status_time=2.0),
        Q=dict(name="Quarry", kind="blast", price=200, max=2, start=0, range=14.0, radius=3.0, delay=1.0, damage=30),
        E=dict(name="Tell", kind="alarm", price=0, max=1, start=1, range=12.0, radius=6.0, duration=90.0,
               status="slow", status_time=2.0, recharge=45.0),
        X=dict(name="Landslide", kind="blast", cost=8, range=40.0, radius=7.0, delay=2.0, damage=120, status="slow", status_time=3.0),
    )),
    "fen": dict(name="Fen", role="Controller", abilities=dict(
        C=dict(name="Bog", kind="zone", price=150, max=1, start=0, range=18.0, radius=3.0, duration=8.0, status="slow", status_time=0.5),
        Q=dict(name="Reed Wall", kind="wall", price=250, max=1, start=0, range=20.0, length=10.0, duration=12.0,
               cross_status="slow", cross_time=2.0),
        E=dict(name="Mist", kind="smoke", price=0, max=2, start=2, range=35.0, radius=2.8, duration=14.0, remote=True, recharge=40.0),
        X=dict(name="Drown", kind="zone", cost=8, range=30.0, radius=8.0, duration=7.0, delay=0.5, status="decay", status_time=1.0),
    )),
    "thorne": dict(name="Thorne", role="Controller", abilities=dict(
        C=dict(name="Briar", kind="tripwire", price=150, max=2, start=0, length=5.0, duration=120.0, status="slow", status_time=3.0),
        Q=dict(name="Bramble", kind="wall", price=250, max=1, start=0, range=18.0, length=8.0, duration=10.0,
               cross_status="vulnerable", cross_time=3.0),
        E=dict(name="Shroud", kind="smoke", price=0, max=2, start=2, range=25.0, radius=2.6, duration=15.0, recharge=35.0),
        X=dict(name="Thornfield", kind="zone", cost=7, range=30.0, radius=7.0, duration=8.0, dps=15, status="slow", status_time=0.5),
    )),
    "moraine": dict(name="Moraine", role="Controller", abilities=dict(
        C=dict(name="Scree", kind="zone", price=150, max=1, start=0, range=16.0, radius=3.0, duration=6.0, status="slow", status_time=0.5),
        Q=dict(name="Cairn", kind="smoke", price=150, max=1, start=0, range=20.0, radius=3.0, duration=12.0),
        E=dict(name="Drift", kind="smoke", price=0, max=2, start=2, range=40.0, radius=2.8, duration=14.0, remote=True, recharge=40.0),
        X=dict(name="Glacier", kind="wall", cost=7, range=30.0, length=30.0, duration=15.0),
    )),
    "sloane": dict(name="Sloane", role="Controller", abilities=dict(
        C=dict(name="Ash", kind="smoke", price=100, max=2, start=0, range=10.0, radius=1.8, duration=8.0),
        Q=dict(name="Back Alley", kind="teleport", price=250, max=1, start=0, range=10.0),
        E=dict(name="Fog Bank", kind="smoke", price=0, max=2, start=2, range=35.0, radius=3.0, duration=14.0, remote=True, recharge=40.0),
        X=dict(name="Long Night", kind="zone", cost=8, range=30.0, radius=10.0, duration=7.0, delay=1.0, status="nearsight", status_time=1.0),
    )),
    "tove": dict(name="Tove", role="Controller", abilities=dict(
        C=dict(name="Flurry", kind="flash", price=200, max=1, start=0, range=12.0, fuse=0.5, blind=1.3, cone=120.0),
        Q=dict(name="Snowbank", kind="wall", price=250, max=1, start=0, range=18.0, length=9.0, duration=12.0),
        E=dict(name="Whiteout", kind="smoke", price=0, max=2, start=2, range=30.0, radius=2.8, duration=15.0, recharge=35.0),
        X=dict(name="Hoarfrost", kind="zone", cost=7, range=30.0, radius=6.0, duration=6.0, delay=0.8, status="suppress", status_time=1.0),
    )),
    "garrick": dict(name="Garrick", role="Sentinel", abilities=dict(
        C=dict(name="Plate", kind="shield", price=200, max=1, start=0, points=40, range=10.0),
        Q=dict(name="Bell Line", kind="tripwire", price=200, max=2, start=0, length=6.0, duration=120.0, status="detain", status_time=1.5),
        E=dict(name="Watch", kind="sensor", price=0, max=1, start=1, range=10.0, radius=8.0, duration=25.0, pulse=2.0, recharge=45.0),
        X=dict(name="Bastion", kind="stim", cost=7, radius=10.0, duration=10.0),
    )),
    "ilse": dict(name="Ilse", role="Sentinel", abilities=dict(
        C=dict(name="Chill", kind="alarm", price=150, max=1, start=0, range=10.0, radius=5.0, duration=120.0, status="slow", status_time=2.5),
        Q=dict(name="Frost Line", kind="tripwire", price=200, max=1, start=0, length=6.0, duration=120.0, status="slow", status_time=3.0),
        E=dict(name="Hearth", kind="heal", price=0, max=1, start=1, amount=50, duration=4.0, range=12.0, recharge=45.0),
        X=dict(name="Winterhold", kind="zone", cost=8, range=25.0, radius=8.0, duration=6.0, delay=1.0, status="suppress", status_time=1.0),
    )),
    "basil": dict(name="Basil", role="Sentinel", abilities=dict(
        C=dict(name="Salve", kind="heal", price=150, max=1, start=0, amount=40, duration=3.0, range=12.0),
        Q=dict(name="Snare Root", kind="tripwire", price=200, max=1, start=0, length=5.0, duration=120.0, status="detain", status_time=2.0),
        E=dict(name="Tonic", kind="stim", price=0, max=1, start=1, radius=5.0, duration=6.0, recharge=45.0),
        X=dict(name="Garden", kind="zone", cost=7, range=15.0, radius=6.0, duration=8.0, heal_allies=12.0, status="slow", status_time=0.5),
    )),
    "cato": dict(name="Cato", role="Sentinel", abilities=dict(
        C=dict(name="Rampart", kind="shield", price=200, max=1, start=0, points=35, range=10.0),
        Q=dict(name="Watchpost", kind="sensor", price=200, max=1, start=0, range=12.0, radius=9.0, duration=40.0, pulse=2.5),
        E=dict(name="Recall", kind="anchor", price=0, max=1, start=1, duration=60.0, recharge=45.0),
        X=dict(name="Overwatch", kind="reveal_all", cost=7, duration=5.0),
    )),
    "ulric": dict(name="Ulric", role="Sentinel", abilities=dict(
        C=dict(name="Howl", kind="zone", price=150, max=1, start=0, range=14.0, radius=4.0, duration=4.0, status="deaf", status_time=1.0, reveal=True),
        Q=dict(name="Jaw Trap", kind="tripwire", price=200, max=2, start=0, length=4.0, duration=120.0, status="concuss", status_time=2.0),
        E=dict(name="Den", kind="alarm", price=0, max=1, start=1, range=10.0, radius=6.0, duration=120.0,
               status="vulnerable", status_time=3.0, recharge=45.0),
        X=dict(name="Pack", kind="immunity", cost=7, duration=9.0, regen=8.0),
    )),
}
