from classes.types import GameState, Input, Action
class GameHandler:
    def __init__(self) -> None:
        self.__inGame: bool = False
        self.__actionQueue: list[Action] = []
        self.__gameState: GameState = GameState()
    
    # Global
    def tick(self) -> None:
        pass
    def handleInput(self, input: Input) -> None:
        pass
    def start(self) -> None:
        pass
    # Local
    # Setters
    # Getters
    def inGame(self) -> bool:
        return self.__inGame
    def getActions(self) -> list[Action]:
        actions = self.__actionQueue
        self.__actionQueue = self.__actionQueue[len(actions):]
        return actions