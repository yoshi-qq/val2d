"""Template for a new agent. Copy this file to config/agents/<key>.py (the file name is the agent's key,
lower case, no leading underscore), change names and values, start the game. Nothing else to touch.

Sprites: assets/agents/<key>/ (docs/SPRITES.md); until they exist the game draws placeholders.
All mechanics, triggers and statuses: docs/MODDING.md.
"""
from gameplay.kit.dsl import (ability, agent, damage, dps, event, heal, on, preset, reveal, spawn, status, thing)

AGENT = agent(
    "Ember", role="Duelist", order=100,
    # a composed ability: a firebomb that bursts and leaves a burning patch
    C=ability(
        "Firebomb", price=200, max=1, target="aim", range=14.0, preview="zone", bot="offense",
        place=thing("blast", lasts=0.8, radius=3.0, thrown=True, triggers=[
            on("expire", who="enemies", sight="walls", do=[
                damage(40, falloff=0.5),
                event("blast"),
                spawn(thing("zone", lasts=4.0, radius=3.0, triggers=[
                    on("tick", who="enemies", do=[dps(20), status("burn", 0.5)]),
                ])),
            ]),
        ]),
    ),
    # presets: the classic building blocks with their values
    Q=preset("hop", "Updraft", price=150, max=2, velocity=6.5),
    E=preset("dash", "Flare Step", max=1, start=1, distance=6.0, duration=0.2, recharge=30.0),
    # an ultimate (cost = ultimate points) that marks every enemy and speeds up the team
    X=ability(
        "Wildfire", cost=7, target="self", bot="buff",
        do=[reveal(3.0, who="enemies", area="everywhere"), status("haste", 6.0, who="team")],
    ),
    # passive: every kill heals 25 over two seconds
    passives=[on("kill", do=[heal(25, over=2.0)])],
)
