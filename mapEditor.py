import os, pygame as p
from typing import Optional
from dependencies import graphy as g
from config.constants import RESOLUTION, ABYSS_HEIGHT
from classes.categories import PenetrationLevel as P
from classes.types import Rect, Position as Pos, Angle, Pose, Position
from classes.mapTypes import Map, Object, Box, Callout as C
from handlers.mapHandler import createObjectRenders

HOLD_TICK_DELAY = 10

CAMERA_MOVEMENT_AMOUNT = 1
CAMERA_ROTATION_AMOUNT = 15
OBJ_MOVEMENT_AMOUNT = 1
OBJ_ROTATION_AMOUNT = 15
SHIFT_MODIFIER = 0.1

objects: list[Object] = [
    Box(id=0, sprite="box1", callout=C.MID, position=Pos(0, 0, 0), orientation=Angle(0), size=Pos(2, 2, 2), penetrationLevel=P.LOW),
    Box(id=1, sprite="box2", callout=C.MID, position=Pos(0, 0, 2), orientation=Angle(0), size=Pos(2, 2, 2), penetrationLevel=P.LOW),
    Box(id=1, sprite="box1", callout=C.MID, position=Pos(-2, 0, 0), orientation=Angle(0), size=Pos(2, 2, 2), penetrationLevel=P.LOW),
    Box(id=1, sprite="box3", callout=C.MID, position=Pos(0, 2, 0), orientation=Angle(0), size=Pos(2, 2, 2), penetrationLevel=P.LOW)
]
testMap = Map("Test Map", objects, Rect(-100, -100, 100, 100), "map_background")
currentPose: Pose = Pose(Pos(0, 0, 0), Angle(0))
currentMap: Map = testMap
selectedObject: Optional[Object] = None
tick: int = 0
lastKeys: list[int] = []
keysFirstSeen: dict[int, int] = {}

def setSelectedObject(obj: Optional[Object]) -> None:
    """
    Sets the selected object in the map editor.
    
    Args:
        obj (Object): The object to select.
    """
    global selectedObject
    selectedObject = obj

def openContextMenu(obj: Object) -> None:
    """
    Opens the context menu for the selected object.
    
    Args:
        obj (Object): The object to open the context menu for.
    """
    pass

def held(key: int) -> bool:
    return key not in lastKeys or tick - keysFirstSeen[key] >= HOLD_TICK_DELAY

def handleInputs(keys: list[int]) -> None:
    global tick, lastKeys, keysFirstSeen
    if p.K_LSHIFT in keys:
        mod = SHIFT_MODIFIER
    else: mod = 1
    for key in keys:
        if held(key):
            match key:
                case p.K_ESCAPE:
                    setSelectedObject(None)
                case p.K_d:
                    currentPose.move(Position(CAMERA_MOVEMENT_AMOUNT*mod, 0, 0))
                case p.K_a:
                    currentPose.move(Position(-CAMERA_MOVEMENT_AMOUNT*mod, 0, 0))
                case p.K_w:
                    currentPose.move(Position(0, 0, CAMERA_MOVEMENT_AMOUNT*mod))
                case p.K_s:
                    currentPose.move(Position(0, 0, -CAMERA_MOVEMENT_AMOUNT*mod))
                case p.K_q:
                    currentPose.move(Position(0, CAMERA_MOVEMENT_AMOUNT*mod, 0))
                case p.K_e:
                    currentPose.move(Position(0, -CAMERA_MOVEMENT_AMOUNT*mod, 0))
                case p.K_x:
                    currentPose.turn(Angle(CAMERA_ROTATION_AMOUNT*mod))
                case p.K_y:
                    currentPose.turn(Angle(-CAMERA_ROTATION_AMOUNT*mod))
                case p.K_RIGHT:
                    if selectedObject:
                        selectedObject.move(Position(OBJ_MOVEMENT_AMOUNT*mod, 0, 0))
                case p.K_LEFT:
                    if selectedObject:
                        selectedObject.move(Position(-OBJ_MOVEMENT_AMOUNT*mod, 0, 0))
                case p.K_UP:
                    if selectedObject:
                        selectedObject.move(Position(0, 0, OBJ_MOVEMENT_AMOUNT*mod))
                case p.K_DOWN:
                    if selectedObject:
                        selectedObject.move(Position(0, 0, -OBJ_MOVEMENT_AMOUNT*mod))
                case p.K_COMMA:
                    if selectedObject:
                        selectedObject.move(Position(0, OBJ_MOVEMENT_AMOUNT*mod, 0))
                case p.K_PERIOD:
                    if selectedObject:
                        selectedObject.move(Position(0, -OBJ_MOVEMENT_AMOUNT*mod, 0))
                case p.K_m:
                    if selectedObject:
                        selectedObject.turn(Angle(OBJ_ROTATION_AMOUNT*mod))
                case p.K_n:
                    if selectedObject:
                        selectedObject.turn(Angle(-OBJ_ROTATION_AMOUNT*mod))
                case _:
                    pass
        if key not in lastKeys:
            keysFirstSeen[key] = tick
    lastKeys = keys

# *MAIN FUNCTIONS*
def setup() -> None:
    """
    Initializes the map editor.
    
    This function sets up the initial state of the map editor, including loading the map and setting up the camera.
    """
    ASSETS_FOLDER = os.path.join(os.path.dirname(__file__), "assets")
    g.init(file=__file__, fps=60, fontPath="font/fixed_sys.ttf", captureCursor=False, naturalY=True, fullscreen=False, windowName="Map Editor", spriteFolder=ASSETS_FOLDER, spriteExtension="png", windowIcon="editor", windowRes=(1840, 1080), nativeRes = RESOLUTION)
    _background = g.RenderImage(imageName=currentMap.getBackgroundSprite(), x=g.middle[0], y=g.middle[1], width=RESOLUTION[0], height=RESOLUTION[1], middle=True, priority=ABYSS_HEIGHT)

def mainLoop() -> Optional[bool]:
    """
    The main loop for the map editor.
    
    This function handles user input, updates the map, and renders the map and objects.
    """
    global tick
    tick += 1
    handleInputs(list(g.getHeldKeys()))
    createObjectRenders(objects=currentMap.getObjects(), perspective=currentPose, editable=True, selectObject=setSelectedObject, openContextMenu=openContextMenu)
    if g.draw() == "quit":
        return True

if __name__ == "__main__":
    setup()
    running = True
    while running:
        if mainLoop(): running = False