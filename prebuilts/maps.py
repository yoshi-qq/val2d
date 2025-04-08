from classes.types import MapKey, Map, maps as maps_

maps: dict[MapKey, Map] = {} # TODO 9: Map Editor

def init() -> None:
    maps_.update(maps)