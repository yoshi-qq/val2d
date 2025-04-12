from time import time as now
from typing import Union
from threading import Thread
from config.constants import AGENT_SELECT_TIME
from classes.types import GameState, Input, Action, Player, AgentKey, MenuKey, Connection
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
        self.__roundStartTime: int = -1
    def close(self) -> None:
        pass
    def tick(self, menu: MenuKey) -> None:
        if menu == MenuKey.HOST_AGENT_SELECT:
            self.__actionQueue.append(Action("updateRemainingSelectTime", self.getRemainingSelectTime()))
    
    def start(self, connections: list[Connection]) -> None:
        self.__actionQueue.append(Action("StartAgentSelectionEvent", None))
        for connection in connections:
            self.addPlayer(Player(name = connection.getName()))
            
        self.__selectStartTime = now()
        def endAgentSelectAtTime() -> None:
            while self.getRemainingSelectTime() > 0:
                pass
            self.__actionQueue.append(Action("EndAgentSelectAction", None))
        thread = Thread(target=endAgentSelectAtTime)
        thread.start()
    
    def startGame(self) -> None:
        for player in self.__gameState.players:
            if player.getAgent() is None:
                player.setAgent(AgentKey.OMEN)
        self.__inGame = True
        self.__gameState.time = 0
        self.__actionQueue.append(Action("serverGameStart", self.__gameState))
        self.startRound()

    def start_Round(self) -> None:
        self.__roundStartTime = now()
    
    def isIngame(self) -> bool:
        return self.__inGame
    # Setters
    def setGamemode(self, mode: GameModeKey) -> None:
        self.__gameState.mode = mode
    def setMap(self, map: MapKey) -> None:
        self.__gameState.map = map
    def setAgent(self, playerName: str, agent: AgentKey) -> None:
        for player in self.__gameState.players:
            if player.getName() == playerName:
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
    
    def getRemainingSelectTime(self) -> float:
        return AGENT_SELECT_TIME - now() + self.__selectStartTime