from config.constants import AGENT_SELECT_TIME
from typing import Union
from classes.types import Message, GameState, Input
class ClientHandler:
    def __init__(self) -> None:
        self.__remainingSelectTime = AGENT_SELECT_TIME
        self.__messageQueue: list[Message] = []
        self.__inGame = False
        self.__gameState: Union[None, GameState] = None
    
    def inGame(self) -> bool:
        return self.__inGame
    def tick(self) -> None:
        pass # TODO
    
    def handleInput(self, input: Input) -> None:
        pass # TODO
    
    def setRemainingSelectTime(self, time: float) -> None:
        self.__remainingSelectTime = time
    def getRemainingSelectTime(self) -> float:
        return self.__remainingSelectTime
    def getMessages(self) -> list[Message]:
        messages = self.__messageQueue
        self.__messageQueue = self.__messageQueue[len(messages):]
        return messages