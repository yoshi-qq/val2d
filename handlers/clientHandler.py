from config.constants import AGENT_SELECT_TIME
from typing import Union
from classes.types import Action, GameState, Input
class ClientHandler:
    def __init__(self) -> None:
        self.__remainingSelectTime = AGENT_SELECT_TIME
        self.__actionQueue: list[Action] = []
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
    def getActions(self) -> list[Action]:
        actions = self.__actionQueue
        self.__actionQueue = self.__actionQueue[len(actions):]
        return actions