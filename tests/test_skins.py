"""Skin coverage and the lifecycle of a skinned weapon."""
from gameplay.data import load_weapons
from gameplay.match import Command, Match
from gameplay.net import apply_snapshot
from gameplay.skins import SKIN_LINES, skin_options
from map_fixtures import load_archived_map


def test_all_weapons_have_a_skin() -> None:
    weapons = load_weapons()
    assert len(SKIN_LINES) == 5
    assert set(weapons) <= set().union(*(line.weapons for line in SKIN_LINES.values()))
    assert set(skin_options("vandal")) == set(SKIN_LINES)


def test_skin_stays_with_a_bought_weapon_after_pickup() -> None:
    world = load_archived_map("workyard")
    match = Match(world)
    owner = match.add_player("Owner", 0, "omen", weapon_skins={"classic": "prime", "vandal": "oni"})
    receiver = match.add_player("Receiver", 0, "jett", weapon_skins={"vandal": "reaver"})
    match.add_player("Opponent", 1, "sage")
    match.start()
    assert owner.weapon and owner.weapon.skin == "prime"
    owner.credits = 5000
    assert match.buy(owner, "vandal")
    assert owner.weapon and owner.weapon.skin == "oni"
    match.spike_carrier = None
    match._drop(owner)
    drop = match.drops[0]
    shadow = Match(world)
    apply_snapshot(shadow, match.snapshot(), receiver.pid)
    assert shadow.drops[0].skin == "oni"
    receiver.pos = drop.pos
    match._pickup(receiver, Command(interact=True))
    assert receiver.weapon and receiver.weapon.skin == "oni"
    apply_snapshot(shadow, match.snapshot(), receiver.pid)
    assert not shadow.drops
    assert shadow.players[receiver.pid].weapons["primary"].skin == "oni"
