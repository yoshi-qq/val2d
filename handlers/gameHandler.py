from classes.types import GameState, Input, Action
from prebuilts.abilities import init as initAbilities
from prebuilts.agents import init as initAgents
from prebuilts.effects import init as initEffects
from prebuilts.maps import init as initMaps
from prebuilts.spriteSets import init as initSpriteSets
from prebuilts.weapons import init as initWeapons

from handlers.config import SERVER_SETTINGS
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
    
    # Setup
    def setup(self) -> None:
        initAbilities()
        initAgents()
        initEffects()
        initMaps()
        initSpriteSets()
        initWeapons()
        
    # Local
    # Setters
    # Getters
    def inGame(self) -> bool:
        return self.__inGame
    def getActions(self) -> list[Action]:
        actions = self.__actionQueue
        self.__actionQueue = self.__actionQueue[len(actions):]
        return actions