import os
from dependencies import graphy as g
from config.constants import RESOLUTION
from classes.categories import PenetrationLevel as P
from classes.types import Rect, Position as Pos, Angle, Pose
from classes.mapTypes import Map, Object, Box, Callout as C
from handlers.mapHandler import createObjectRenders


objects: list[Object] = [
    Box(id=0, sprite="box1", callout=C.MID, position=Pos(0, 0, 0), orientation=Angle(0), size=Pos(2, 2, 2), penetrationLevel=P.LOW),
    Box(id=1, sprite="box2", callout=C.MID, position=Pos(2, 0, 0), orientation=Angle(0), size=Pos(2, 2, 2), penetrationLevel=P.LOW)
]
testMap = Map("Test Map", objects, Rect(-100, -100, 100, 100), "mapBackground")
currentPose: Pose = Pose(Pos(0, 0, 0), Angle(0))
currentMap: Map = testMap

def setup() -> None:
    """
    Initializes the map editor.
    
    This function sets up the initial state of the map editor, including loading the map and setting up the camera.
    """
    ASSETS_FOLDER = os.path.join(os.path.dirname(__file__), "assets")
    g.init(file=__file__, fps=60, fontPath="font/fixed_sys.ttf", captureCursor=False, naturalY=True, fullscreen=False, windowName="Map Editor", spriteFolder=ASSETS_FOLDER, spriteExtension="png", windowIcon="editor", windowRes=(960, 540), nativeRes = RESOLUTION)
    

def mainLoop() -> None:
    """
    The main loop for the map editor.
    
    This function handles user input, updates the map, and renders the map and objects.
    """

    # TODO: Handle user input
    createObjectRenders(currentMap.getObjects(), currentPose, editable=True)
    g.draw()
    

if __name__ == "__main__":
    setup()
    running = True
    while running:
        mainLoop()