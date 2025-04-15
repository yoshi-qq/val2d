from classes.types import Printable, JSONType
from classes.keys import ObjectiveKey, MapKey, GameModeKey
from classes.playerTypes import Player
from classes.mapTypes import Object

class GameMode(Printable):
    def __init__(self, name: str, objective: ObjectiveKey = ObjectiveKey.SPIKE, winThreshold: int = 13, roundTime: int = 100, overTime: bool = False) -> None:
        self.__name = name
        self.__objective = objective
        self.__winThreshold = winThreshold
        self.__roundTime = roundTime
        self.__overTime = overTime
    def getName(self) -> str:
        return self.__name
    def getObjectiveKey(self) -> ObjectiveKey:
        return self.__objective
    def getWinThreshold(self) -> int:
        return self.__winThreshold
    def getRoundTime(self) -> int:
        return self.__roundTime
    def getOverTime(self) -> bool:
        return self.__overTime


class GameState:
    def __init__(self, players: list[Player], time: float, roundNo: int, score: tuple[int, int], mapKey: MapKey, gameMode: GameModeKey, roundTime: float, objects: list[Object]) -> None:
        self.players = players
        self.time = time
        self.round = roundNo
        self.score = score
        self.mapKey = mapKey
        self.gameMode = gameMode
        self.roundTime = roundTime
        self.objects = objects
    def cutForPlayer(self, playerName: str) -> "GameState": # type: ignore
        pass # TODO L8
    
    def getPlayer(self, playerName: str) -> Player | None:
        for player in self.players:
            if player.getName() == playerName:
                return player
        return None
    
    def collapseToDict(self) -> JSONType:
        return {
            "players": [player.collapseToDict() for player in self.players],
            "time": self.time,
            "round": self.round,
            "score": self.score,
            "mapKey": self.mapKey,
            "gameMode": self.gameMode,
            "roundTime": self.roundTime,
            "objects": [obj.collapseToDict() for obj in self.objects]
        }

    def __str__(self) -> str:
        return str(self.collapseToDict())
    def __repr__(self) -> str:
        return self.__str__()
    