"""Ascent's floor levels: stairs climb, Heaven is too high to jump onto, cover counts from its own floor, bots path over levels."""
from __future__ import annotations

from gameplay.geometry import Vec
from gameplay.match import Command, Match
from gameplay.nav import grid_for
from gameplay.world import load_map


def setup() -> tuple[Match, int]:
    m = Match(load_map("ascent"), seed=1)
    pid = m.add_player("A", 0, "kestrel").pid
    m.start()
    for _ in range(31 * 64):
        m.tick(1 / 64, {})
    return m, pid


def place(m: Match, pid: int, x: float, top: float) -> None:
    p = m.players[pid]
    p.pos, p.z, p.vz = Vec(x, m.world.height - top), 0.0, 0.0
    p.ground = m.world.ground_height(p.pos)


def walk(m: Match, pid: int, facing: float, seconds: float, jump: bool = False) -> None:
    for i in range(int(seconds * 64)):
        m.tick(1 / 64, {pid: Command(move_y=1.0, facing=facing, jump=jump and i % 20 == 0)})


def test_levels_of_the_main_areas() -> None:
    w = load_map("ascent")
    at = lambda x, top: w.ground_height(Vec(x, w.height - top))  # noqa: E731
    assert at(110, 52) == 0.0 and at(110, 40) == 1.0 and at(110, 31) == 3.0  # A front, site, Heaven
    assert at(64, 65) == 0.0 and at(64, 55) == 1.0 and at(76, 75) == 1.0     # courtyard, Mid Bottom, Catwalk
    assert at(25, 30) == 0.0 and at(55, 38) == 1.0                           # B site, Market


def test_stairs_climb_and_heaven_needs_its_stairs() -> None:
    m, pid = setup()
    p = m.players[pid]
    place(m, pid, 110, 52)
    walk(m, pid, 0.0, 1.5)  # north up the A site stairs
    assert p.ground == 1.0 and m.world.callout_at(p.pos) == "A Site"
    place(m, pid, 115, 36)
    walk(m, pid, 0.0, 1.5, jump=True)  # jumping at the Heaven edge from the site
    assert p.ground == 1.0 and m.world.height - p.pos.y > 34.0
    place(m, pid, 101.5, 19)
    walk(m, pid, 180.0, 2.0)  # south up the Heaven stairs
    assert p.ground == 3.0


def test_crate_on_a_raised_floor_is_still_cover() -> None:
    w = load_map("ascent")
    site = w.site_at
    dice = [wl for wl in w.walls if wl.material == "obj:ascent_radianite_crate" and site(wl.rect.center)
            and site(wl.rect.center).name == "A"]
    assert dice and all(wl.top == 2.0 for wl in dice)  # one level above the A site plateau
    assert w.ground_height(dice[0].rect.center) == 2.0


def test_bots_reach_every_area() -> None:
    w = load_map("ascent")
    grid = grid_for(w)
    for x, top in ((115, 40), (112, 31), (25, 30), (64, 55), (76, 75), (125, 63)):
        assert grid.path(w.spawns[0][2], Vec(x, w.height - top)), (x, top)
