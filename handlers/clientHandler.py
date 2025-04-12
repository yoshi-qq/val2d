from config.constants import AGENT_SELECT_TIME
from typing import Union
from classes.types import Action, GameState
class ClientHandler:
    def __init__(self) -> None:
        self.__remainingSelectTime = AGENT_SELECT_TIME
        self.__actionQueue: list[Action] = []
        self.__inGame = False
        self.__gameState: Union[None, GameState] = None
        
    def setRemainingSelectTime(self, time: float) -> None:
        self.__remainingSelectTime = time
    def getRemainingSelectTime(self) -> float:
        return self.__remainingSelectTime