from classes.types import Position
from classes.mapTypes import Wall, Box, Cylinder, Stair, Decoration, BreakableDoor, Switch, Bike, UltOrb, Zipline, Teleporter, TPDoor, RotatingDoor, Abyss, SpawnPoint, PlantSite, PenetrationLevel
from typing import Type, Dict, Union

SpecificObject = Union[Wall, Box, Cylinder, Stair, Decoration, BreakableDoor, Switch, Bike, UltOrb, Zipline, Teleporter, TPDoor, RotatingDoor, Abyss, SpawnPoint, PlantSite]

walls: list[SpecificObject] = [
]
boxes: list[SpecificObject] = [
    Box(sprite="box1", size=Position(2, 2, 2), penetrationLevel=PenetrationLevel.LOW),
    Box(sprite="box2", size=Position(2, 2, 2), penetrationLevel=PenetrationLevel.LOW),
    Box(sprite="box3", size=Position(2, 2, 2), penetrationLevel=PenetrationLevel.LOW),
    Box(sprite="wood_box", size=Position(2, 2, 2), penetrationLevel=PenetrationLevel.MEDIUM),
    Box(sprite="floor_tile", size=Position(2, 2, 2), penetrationLevel=PenetrationLevel.HIGH),
    Box(sprite="floor_tile_padded", size=Position(2, 2, 2), penetrationLevel=PenetrationLevel.INPENETRABLE),
    Box(sprite="floor_tile_padded", size=Position(2, 2, 2), penetrationLevel=PenetrationLevel.INPENETRABLE),
    Box(sprite="grass_tile", size=Position(2, 2, 2), penetrationLevel=PenetrationLevel.MEDIUM),
    Box(sprite="light_gray_tile", size=Position(2, 2, 2), penetrationLevel=PenetrationLevel.MEDIUM),
    Box(sprite="white_tile", size=Position(2, 2, 2), penetrationLevel=PenetrationLevel.MEDIUM),
    Box(sprite="wood_floor", size=Position(2, 2, 2), penetrationLevel=PenetrationLevel.MEDIUM),
    Box(sprite="wood_floor_2", size=Position(2, 2, 2), penetrationLevel=PenetrationLevel.MEDIUM),
]
cylinders: list[SpecificObject] = []
stairs: list[SpecificObject] = []
decorations: list[SpecificObject] = []
breakableDoors: list[SpecificObject] = []
switches: list[SpecificObject] = []
bikes: list[SpecificObject] = []
ultOrbs: list[SpecificObject] = []
ziplines: list[SpecificObject] = []
teleporters: list[SpecificObject] = []
tpDoors: list[SpecificObject] = []
rotatingDoors: list[SpecificObject] = []
abysses: list[SpecificObject] = []
spawnPoints: list[SpecificObject] = []
plantSites: list[SpecificObject] = []

objects: Dict[Type[SpecificObject], list[SpecificObject]] = {
    Wall: walls,
    Box: boxes,
    Cylinder: cylinders,
    Stair: stairs,
    Decoration: decorations,
    BreakableDoor: breakableDoors,
    Switch: switches,
    Bike: bikes,
    UltOrb: ultOrbs,
    Zipline: ziplines,
    Teleporter: teleporters,
    TPDoor: tpDoors,
    RotatingDoor: rotatingDoors,
    Abyss: abysses,
    SpawnPoint: spawnPoints,
    PlantSite: plantSites,
}