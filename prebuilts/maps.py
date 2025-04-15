from classes.types import maps as maps_
from classes.keys import MapKey
from classes.mapTypes import Map

k = MapKey
maps: dict[MapKey, Map] = {} # TODO 9: Map Editor

def init() -> None:
    maps_.update(maps)