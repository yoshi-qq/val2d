from config.constants import AGENT_SELECT_TIME
from typing import Union
from classes.types import Message, GameState, Input
class ClientGameHandler:
    def __init__(self) -> None:
        self.__remainingSelectTime = AGENT_SELECT_TIME
        self.__messageQueue: list[Message] = []
        self.__inGame = False
        self.__gameState: Union[None, GameState] = None

    # Global
    def setup(self, gameState: GameState) -> None:
        pass
    def tick(self) -> None:
        pass # TODO
    def handleInput(self, input: Input) -> None:
        pass # TODO
    
    # Local
    
    # Getters
    def inGame(self) -> bool:
        return self.__inGame
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