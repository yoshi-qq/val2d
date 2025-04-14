import os
from classes.types import GameState
from dependencies import graphy as g
class GraphicsHandler:
    def __init__(self, root: str) -> None:
        ASSETS_FOLDER = os.path.join(root, "assets")
        self.__gameObjects: list[g.RenderObject] = []
        self.__menuObjects: list[g.RenderObject] = []
        g.init(file=__file__, fps=60, fontPath="font/fixed_sys.ttf", fullscreen=False, windowName="Val2D", spriteFolder=ASSETS_FOLDER, spriteExtension="png", windowIcon="logo", windowRes=(960, 540))
        self.__gameObjectRenders: list[g.RenderObject] = []
    # Global
    def draw(self) -> None:
        g.draw()
        
    def getRendersFromPerspective(self) -> list[g.RenderObject]: # type: ignore
        pass
    
    def drawGameState(self, clientName: str, gameState: GameState) -> None:
        renders = self.getRendersFromPerspective() # type: ignore

    # Local
    # Setters
    
            
    
    def setGameVisibility(self, visible: bool) -> None:
        for obj in self.__gameObjects:
            obj.enabled = visible
    def setMenuVisibility(self, visible: bool) -> None:
        for obj in self.__menuObjects:
            obj.enabled = visible
    
    # Getters