from time import time as now
from typing import Union
from threading import Thread
from config.constants import AGENT_SELECT_TIME
from classes.types import GameState, Input, Message, Player, AgentKey, MenuKey, Connection
from classes.types import abilities, agents, effects, melees, sidearms, guns, maps, spriteSets
from classes.types import MapKey, GameModeKey
from prebuilts.abilities import init as initAbilities
from prebuilts.agents import init as initAgents
from prebuilts.effects import init as initEffects
from prebuilts.maps import init as initMaps
from prebuilts.spriteSets import init as initSpriteSets
from prebuilts.weapons import init as initWeapons

class ServerGameHandler:
    def __init__(self) -> None:
        self.__messageQueue: list[Message] = []
        self.__inGame = False
        self.__gameState: GameState = GameState([], -1, 0, (0, 0), MapKey.ASCENT, GameModeKey.UNRATED, -1, [])
        self.__roundStartTime: int = -1
    def close(self) -> None:
        pass
    def tick(self, menu: MenuKey) -> None:
        if menu == MenuKey.HOST_AGENT_SELECT:
            self.__messageQueue.append(Message("UpdateRemainingSelectTime", self.getRemainingSelectTime()))
    
    def start(self, connections: list[Connection]) -> None:
        self.__messageQueue.append(Message("StartAgentSelectionEvent", None))
        for connection in connections:
            self.addPlayer(Player(name = connection.getName()))
            
        self.__selectStartTime = now()
        def endAgentSelectAtTime() -> None:
            while self.getRemainingSelectTime() > 0:
                pass
            self.__messageQueue.append(Message("EndAgentSelectMessage", None))
        thread = Thread(target=endAgentSelectAtTime)
        thread.start()
    
    def startGame(self) -> None:
        for player in self.__gameState.players:
            if player.getAgent() is None:
                player.setAgent(AgentKey.OMEN)
        self.__inGame = True
        self.__gameState.time = 0
        self.__messageQueue.append(Message("ServerGameStart", self.__gameState))
        self.startRound()

    def startRound(self) -> None:
        self.__roundStartTime = now()
        # TODO NEXT
    
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
    def getMessages(self) -> list[Message]:
        messages = self.__messageQueue
        self.__messageQueue = self.__messageQueue[len(messages):]
        return messages
    
    def getRemainingSelectTime(self) -> float:
        return AGENT_SELECT_TIME - now() + self.__selectStartTime