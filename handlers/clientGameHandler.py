from time import time as now
from config.constants import AGENT_SELECT_TIME, PING_INTERVAL
from typing import Union, Any
from classes.types import Message, GameState, Input, Ping
class ClientGameHandler:
    def __init__(self) -> None:
        self.__remainingSelectTime = AGENT_SELECT_TIME
        self.__messageQueue: list[Message] = []
        self.__inGame = False
        self.__gameState: Union[None, GameState] = None
        self.__pingQueue: list[Ping] = []
        self.__lastPingTime: float = now()
    # Global
    def setGameState(self, gameState: GameState) -> None:
        self.__gameState = gameState
        
    def setup(self, gameState: GameState) -> None:
        self.setGameState(gameState)
        self.__inGame = True
        
    def tick(self) -> None:
        pass
        # self.__pingTick()
            
    def handleInput(self, input: Input) -> None:
        pass # TODO
    
    # Local
    def __sendMessage(self, head: str, body: Any) -> None:
        self.__messageQueue.append(Message(head, body))
    
    def __pingTick(self) -> None: # type: ignore TODO
        if now() - self.__lastPingTime > PING_INTERVAL:
            newPing = Ping(now())
            self.__pingQueue.append(newPing)
            self.__lastPingTime = newPing.time
            self.__sendMessage("Ping", newPing)
        
    # Getters
    def inGame(self) -> bool:
        return self.__inGame
    def getGameState(self) -> Union[None, GameState]:
        return self.__gameState
    def getRemainingSelectTime(self) -> float:
        return self.__remainingSelectTime
    def getMessages(self) -> list[Message]:
        messages = self.__messageQueue
        self.__messageQueue = self.__messageQueue[len(messages):]
        return messages
    
    # Setters
    def updateGameState(self, newGameState: GameState) -> None:
        self.__gameState = newGameState
    def setRemainingSelectTime(self, time: float) -> None:
        self.__remainingSelectTime = time