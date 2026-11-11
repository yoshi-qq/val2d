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
}
