from typing import Union
from classes.types import GameState, Input, Action, Player, AgentKey
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
        self.__inGame = False
        self.__gameState: GameState = GameState([], -1, 0, (0, 0), MapKey.ASCENT, GameModeKey.UNRATED, -1, [])
    def close(self) -> None:
        pass
    def start(self) -> None:
        self.__actionQueue.append(Action("StartAgentSelectionEvent", None))
    
    def isIngame(self) -> bool:
        return self.__inGame
    # Setters
    def setGamemode(self, mode: GameModeKey) -> None:
        self.__gameState.mode = mode
    def setMap(self, map: MapKey) -> None:
        self.__gameState.map = map
    def setAgent(self, playerName: str, agent: AgentKey) -> None:
        for player in self.__gameState.players:
            if player.name == playerName:
                player.setAgent(agent)

    def addPlayer(self, player: Player) -> None:
        self.__gameState.players.append(player)
    def removePlayer(self, player: Player) -> None:
        self.__gameState.players.remove(player)
    # Getters
    def getActions(self) -> list[Action]:
        actions = self.__actionQueue
        self.__actionQueue = self.__actionQueue[len(actions):]
        return actions