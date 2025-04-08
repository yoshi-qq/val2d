from typing import Union
from classes.types import GameState, Input, Action, Player 
from classes.types import abilities, agents, effects, melees, sidearms, guns, maps, spriteSets
from classes.types import MapKey, GameModeKey
from prebuilts.abilities import init as initAbilities
from prebuilts.agents import init as initAgents
from prebuilts.effects import init as initEffects
from prebuilts.maps import init as initMaps
from prebuilts.spriteSets import init as initSpriteSets
from prebuilts.weapons import init as initWeapons

class ServerHandler:
    def __init__(self) -> None:
        self.__actionQueue: list[Action] = []
        self.__gameState: GameState = GameState([], -1, 0, (0, 0), MapKey.ASCENT, GameModeKey.UNRATED, -1, [])
    def close(self) -> None:
        pass
    def start(self) -> None:
        self.__actionQueue.append(Action("StartAgentSelectionEvent", None))
    
    # Setters
    def setGamemode(self, mode: GameModeKey) -> None:
        self.__gameState.mode = mode
    def setMap(self, map: MapKey) -> None:
        self.__gameState.map = map
    def addPlayer(self, player: Player) -> None:
        self.__gameState.players.append(player)
    def removePlayer(self, player: Player) -> None:
        self.__gameState.players.remove(player)
    # Getters
    def getActions(self) -> list[Action]:
        actions = self.__actionQueue
        self.__actionQueue = self.__actionQueue[len(actions):]
        return actions