import os, pygame as p, pickle, copy
from math import ceil
from typing import Optional, Callable
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from dependencies import graphy as g
from config.constants import RESOLUTION, MAP_SKY, ABYSS_HEIGHT
from classes.categories import PenetrationLevel as P
from classes.types import Rect, Position as Pos, Angle, Pose, Position
from classes.mapTypes import Map, Object, Callout as C, Box, Stair 
from handlers.mapHandler import createObjectRenders, createObjectRender

TOPBAR_HEIGHT = 96
SIDEBAR_WIDTH = 200
HOLD_TICK_DELAY = 10

UI_LEVEL = MAP_SKY + 1
TILESIZE = 32

CAMERA_MOVEMENT_AMOUNT = 1
CAMERA_ROTATION_AMOUNT = 15
OBJ_MOVEMENT_AMOUNT = 1
OBJ_ROTATION_AMOUNT = 15
OBJ_STRETCH_AMOUNT = 1
SHIFT_MODIFIER = 0.1
SELECT_FACTOR = 1.25

objects: list[Object] = [
    Box(id=0, sprite="box1", callout=C.MID, position=Pos(1, 0, 3), orientation=Angle(0), size=Pos(2, 2, 2), penetrationLevel=P.LOW),
    Box(id=1, sprite="box2", callout=C.MID, position=Pos(-1, 0, 3), orientation=Angle(0), size=Pos(2, 2, 2), penetrationLevel=P.LOW),
    Box(id=2, sprite="box1", callout=C.MID, position=Pos(1, -2, -3), orientation=Angle(0), size=Pos(2, 2, 2), penetrationLevel=P.LOW),
    Box(id=3, sprite="box3", callout=C.MID, position=Pos(-1, -2, -3), orientation=Angle(0), size=Pos(2, 2, 2), penetrationLevel=P.LOW),
    Stair(id=4, sprite="wood_stairs", callout=C.MID, position=Pos(0, 0, 0), orientation=Angle(0), size=Pos(4, 2, 4))
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
    global tick, lastKeys, keysFirstSeen, selectedObject
    
    if p.K_LSHIFT in keys:
        mod = SHIFT_MODIFIER
    else: mod = 1
    if p.K_LCTRL in keys:
        primary = False
    else: primary = True
    
    for key in keys:
        if held(key):
            match key:
                case p.K_ESCAPE:
                    setSelectedObject(None)
                case p.K_d:
                    currentPose.move(Position(CAMERA_MOVEMENT_AMOUNT*mod, 0, 0).rotate(currentPose.getOrientation()))
                case p.K_a:
                    currentPose.move(Position(-CAMERA_MOVEMENT_AMOUNT*mod, 0, 0).rotate(currentPose.getOrientation()))
                case p.K_w:
                    currentPose.move(Position(0, 0, CAMERA_MOVEMENT_AMOUNT*mod).rotate(currentPose.getOrientation()))
                case p.K_s:
                    currentPose.move(Position(0, 0, -CAMERA_MOVEMENT_AMOUNT*mod).rotate(currentPose.getOrientation()))
                case p.K_q:
                    currentPose.move(Position(0, CAMERA_MOVEMENT_AMOUNT*mod, 0))
                case p.K_e:
                    currentPose.move(Position(0, -CAMERA_MOVEMENT_AMOUNT*mod, 0))
                    currentPose.getPosition().minY(-10)
                case p.K_x:
                    currentPose.turn(Angle(CAMERA_ROTATION_AMOUNT*mod))
                case p.K_y:
                    currentPose.turn(Angle(-CAMERA_ROTATION_AMOUNT*mod))
                case p.K_RIGHT:
                    if selectedObject:
                        if primary:
                            selectedObject.move(Position(OBJ_MOVEMENT_AMOUNT*mod, 0, 0).rotate(currentPose.getOrientation()))
                        else:
                            selectedObject.stretch(Position(OBJ_MOVEMENT_AMOUNT*mod, 0, 0))
                case p.K_LEFT:
                    if selectedObject:
                        if primary:
                            selectedObject.move(Position(-OBJ_MOVEMENT_AMOUNT*mod, 0, 0).rotate(currentPose.getOrientation()))
                        else:
                            selectedObject.stretch(Position(-OBJ_MOVEMENT_AMOUNT*mod, 0, 0))
                case p.K_UP:
                    if selectedObject:
                        if primary:
                            selectedObject.move(Position(0, 0, OBJ_MOVEMENT_AMOUNT*mod).rotate(currentPose.getOrientation()))
                        else:
                            selectedObject.stretch(Position(0, 0, OBJ_STRETCH_AMOUNT*mod))
                case p.K_DOWN:
                    if selectedObject:
                        if primary:
                            selectedObject.move(Position(0, 0, -OBJ_MOVEMENT_AMOUNT*mod).rotate(currentPose.getOrientation()))
                        else:
                            selectedObject.stretch(Position(0, 0, -OBJ_STRETCH_AMOUNT*mod))
                case p.K_COMMA:
                    if selectedObject:
                        if primary:
                            selectedObject.move(Position(0, OBJ_MOVEMENT_AMOUNT*mod, 0))
                        else:
                            selectedObject.stretch(Position(0, OBJ_MOVEMENT_AMOUNT*mod, 0))
                case p.K_PERIOD:
                    if selectedObject:
                        if primary:
                            selectedObject.move(Position(0, -OBJ_MOVEMENT_AMOUNT*mod, 0))
                        else:
                            selectedObject.stretch(Position(0, -OBJ_MOVEMENT_AMOUNT*mod, 0))
                case p.K_m:
                    if selectedObject:
                        selectedObject.turn(Angle(OBJ_ROTATION_AMOUNT*mod))
                case p.K_n:
                    if selectedObject:
                        selectedObject.turn(Angle(-OBJ_ROTATION_AMOUNT*mod))
                case p.K_DELETE:
                    if selectedObject:
                        currentMap.removeObject(selectedObject)
                case _:
                    pass
        if key not in lastKeys:
            keysFirstSeen[key] = tick
    lastKeys = keys

def saveMap() -> None:
    path = asksaveasfilename(
    title="Save pickle file",
    defaultextension=".pkl",
    filetypes=[("Pickle files", "*.pkl"), ("All files", "*.*")]
    )
    with open(path, 'wb') as _file:
        pickle.dump(currentMap, _file)

def editMap() -> None:
    global currentMap
    path = askopenfilename(
    title="Select a pickle file",
    filetypes=[("Pickle files", "*.pkl"), ("All files", "*.*")]
    )
    with open(path, 'rb') as _file:
        currentMap = pickle.load(_file)

def placeObject(obj: Object) -> None:
    global currentMap, currentPose
    def generateID(IDs: list[int]) -> int:
        found: bool = False
        tryID: int = 0
        while not found:
            if tryID in IDs:
                tryID += 1
            else:
                break
        return tryID
    newObj = copy.deepcopy(obj)
    newObj.setPosition(currentPose.getPosition())
    newObj.setID(generateID([obj.getID() for obj in currentMap.getObjects()]))
    currentMap.addObject(newObj)

# *MAIN FUNCTIONS*
def setup() -> None:
    """
    Initializes the map editor.
    
    This function sets up the initial state of the map editor, including loading the map and setting up the camera.
    """
    root = Tk()
    root.withdraw()
    ASSETS_FOLDER = os.path.join(os.path.dirname(__file__), "assets")
    g.init(file=__file__, fps=60, fontPath="font/fixed_sys.ttf", captureCursor=False, naturalY=True, fullscreen=False, windowName="Map Editor", spriteFolder=ASSETS_FOLDER, spriteExtension="png", windowIcon="editor", windowRes=(1656, 972), nativeRes = RESOLUTION)
    _background = g.RenderImage(imageName=currentMap.getBackgroundSprite(), x=g.middle[0], y=g.middle[1], width=RESOLUTION[0], height=RESOLUTION[1], middle=True, priority=ABYSS_HEIGHT)
    # *UI)
    _ui: list[g.RenderObject] = []
    _topBarBackground: list[g.RenderImage] = [g.RenderImage(imageName="gray", y=RESOLUTION[1]-(j*TILESIZE), x=i*TILESIZE, middle=False, width=TILESIZE, height=TILESIZE, priority=UI_LEVEL+2) 
                                              for i in range(0, ceil(RESOLUTION[0]/TILESIZE)) for j in range(0, ceil(TOPBAR_HEIGHT/TILESIZE))] + [g.RenderImage(imageName="sidebar", y=RESOLUTION[1]-(ceil(TOPBAR_HEIGHT/TILESIZE)*TILESIZE), x=i*TILESIZE, middle=False, width=TILESIZE, height=TILESIZE, priority=UI_LEVEL+2, angle=90) 
                                                                                                                                                  for i in range(0, ceil(RESOLUTION[0]/TILESIZE))]
    _sideBarBackground: list[g.RenderImage] = [g.RenderImage(imageName="gray", x=j*TILESIZE, y=i*TILESIZE, middle=False, width=TILESIZE, height=TILESIZE, priority=UI_LEVEL+1) 
                                               for i in range(ceil(RESOLUTION[1]/TILESIZE)) for j in range(ceil(SIDEBAR_WIDTH/TILESIZE))] + [g.RenderImage(imageName="sidebar", x=ceil(SIDEBAR_WIDTH/TILESIZE)*TILESIZE, y=i*TILESIZE, middle=False, width=TILESIZE, height=TILESIZE, priority=UI_LEVEL+1) 
                                                                                                                                             for i in range(0, ceil(RESOLUTION[1]/TILESIZE))]
    # TOP BAR
    # actionButtons of the format list[(sprite, hoverSprite, function, size)]
    actionButtonData: list[tuple[str, str, Callable[[], None], float]] = [
        ("save", "save_hover", saveMap, 23/9),
        ("edit", "edit_hover", editMap, 23/9)
    ]
    # objectButtons of the format list[(sprite, Object, size)]
    objectButtonData: list[tuple[str, Object, float]] = [
        ("box1", Box(id=-1, sprite="box1", callout=C.MID, position=Position(), orientation=Angle(), size=Position(2, 2, 2)), 1),
        ("box2", Box(id=-1, sprite="box2", callout=C.MID, position=Position(), orientation=Angle(), size=Position(2, 2, 2)), 1),
        ("box3", Box(id=-1, sprite="box3", callout=C.MID, position=Position(), orientation=Angle(), size=Position(2, 2, 2)), 1),
        ("grass_tile", Box(id=-1, sprite="grass_tile", callout=C.MID, position=Position(), orientation=Angle(), size=Position(2, 2, 2)), 1),
        ("floor_tile", Box(id=-1, sprite="floor_tile", callout=C.MID, position=Position(), orientation=Angle(), size=Position(2, 2, 2)), 1),
        ("floor_tile_padded", Box(id=-1, sprite="floor_tile_padded", callout=C.MID, position=Position(), orientation=Angle(), size=Position(2, 2, 2)), 1),
        ("light_gray_tile", Box(id=-1, sprite="light_gray_tile", callout=C.MID, position=Position(), orientation=Angle(), size=Position(2, 2, 2)), 1),
        ("white_tile", Box(id=-1, sprite="white_tile", callout=C.MID, position=Position(), orientation=Angle(), size=Position(2, 2, 2)), 1),
        ("wood_box", Box(id=-1, sprite="wood_box", callout=C.MID, position=Position(), orientation=Angle(), size=Position(2, 2, 2)), 1),
        ("wood_floor", Box(id=-1, sprite="wood_floor", callout=C.MID, position=Position(), orientation=Angle(), size=Position(2, 2, 2)), 1),
        ("wood_floor_2", Box(id=-1, sprite="wood_floor_2", callout=C.MID, position=Position(), orientation=Angle(), size=Position(2, 2, 2)), 1),
        ("wood_stairs", Stair(id=-1, sprite="wood_stairs", callout=C.MID, position=Position(), orientation=Angle(), size=Position(2, 4, 4)), 1),
    ] # TODO: add more Buttons
    _actionButtons: list[g.RenderButton] = []
    _objectButtons: list[g.RenderButton] = []
    _actionButtonsBackground: list[g.RenderImage] = []
    _actionLength: int = len(actionButtonData)
    _objectLength: int = len(objectButtonData)
    spacing1 = TILESIZE/2
    spacing2 = TILESIZE/2
    width1 = min(3*TILESIZE, RESOLUTION[0]/_actionLength - spacing1)
    width2 = min(2*TILESIZE, RESOLUTION[0]/_objectLength - spacing2)
    maxSpace1 = 3*TILESIZE
    maxSpace2 = 3*TILESIZE
    for i, (sprite, hoverSprite, func, size) in enumerate(actionButtonData):
        height = width1 / size
        x = min(i*(maxSpace1+width1), i/_actionLength * RESOLUTION[0]) + (width1+TILESIZE)/2
        y = RESOLUTION[1]-0.5*TILESIZE
        _actionButtons.append(g.RenderButton(imageName=sprite, hoverImageName=hoverSprite, clickAction=func, x=x, y=y, width=width1, height=height, middle=True, priority=UI_LEVEL+3))
    for i, (sprite, obj, size) in enumerate(objectButtonData):
        height = width2 / size
        x = min(i*(maxSpace2+width2), i/_objectLength * RESOLUTION[0]) + (width2+TILESIZE)/2
        y = RESOLUTION[1]-2.5*TILESIZE
        _objectButtons.append(g.RenderButton(imageName=sprite, clickAction=placeObject, arguments=(obj,), x=x, y=y, width=width2, height=height, middle=True, priority=UI_LEVEL+3))
        _actionButtonsBackground.append(g.RenderImage(imageName="select", x=x, y=y, width=width2*SELECT_FACTOR, height=height*SELECT_FACTOR, middle=True, priority=UI_LEVEL+2.5))
    # TODO: SIDE BAR

def mainLoop() -> Optional[bool]:
    """
    The main loop for the map editor.
    
    This function handles user input, updates the map, and renders the map and objects.
    """
    global tick, selectedObject
    tick += 1
    handleInputs(list(g.getHeldKeys()))
    createObjectRenders(objects=currentMap.getObjects(), perspective=currentPose, editable=True, selectObject=setSelectedObject, openContextMenu=openContextMenu)
    if selectedObject:
        _selectedRender = createObjectRender(selectedObject, selectedObject.getPose())
        if _selectedRender:
            _selectedRender.x, _selectedRender.y = 4*TILESIZE, 8*TILESIZE
            _selectedRender.width = _selectedRender.height = 5*TILESIZE
            _selectedRender.priority = UI_LEVEL + 3
    if g.draw() == "quit":
        return True

if __name__ == "__main__":
    setup()
    running = True
    while running:
        if mainLoop(): running = False