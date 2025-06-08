import os, pygame as p, pickle, copy
from math import ceil, floor
from typing import Optional, Callable, Type
from typing import Sequence # type: ignore
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from dependencies import graphy as g
from config.constants import RESOLUTION, MAP_SKY, ABYSS_HEIGHT
from classes.categories import PenetrationLevel as P
from classes.types import Rect, Position as Pos, Angle, Pose, Position
from classes.mapTypes import Map, Object, Callout as C, Box, Stair 
from handlers.mapHandler import createObjectRenders, createObjectRender
from prebuilts.objects import objects, SpecificObject
from helpers.graphicsHelper import removeListObjects

ASSETS_FOLDER = os.path.join(os.path.dirname(__file__), "assets")
g.init(file=__file__, fps=60, fontPath="font/fixed_sys.ttf", captureCursor=False, naturalY=True, fullscreen=False, windowName="Map Editor", spriteFolder=ASSETS_FOLDER, spriteExtension="png", windowIcon="editor", windowRes=(1656, 972), nativeRes = RESOLUTION)

TOPBAR_HEIGHT = 192
SIDEBAR_WIDTH = 300
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

INFO_DEPTH = 12*TILESIZE
INFO_TEXT_SIZE = 26

testObjects: list[Object] = [
    Box(id=0, sprite="box1", callout=C.MID, position=Pos(1, 0, 3), orientation=Angle(0), size=Pos(2, 2, 2), penetrationLevel=P.LOW),
    Box(id=1, sprite="box2", callout=C.MID, position=Pos(-1, 0, 3), orientation=Angle(0), size=Pos(2, 2, 2), penetrationLevel=P.LOW),
    Box(id=2, sprite="box1", callout=C.MID, position=Pos(1, -2, -3), orientation=Angle(0), size=Pos(2, 2, 2), penetrationLevel=P.LOW),
    Box(id=3, sprite="box3", callout=C.MID, position=Pos(-1, -2, -3), orientation=Angle(0), size=Pos(2, 2, 2), penetrationLevel=P.LOW),
    Stair(id=4, sprite="wood_stairs", callout=C.MID, position=Pos(0, 0, 0), orientation=Angle(0), size=Pos(4, 2, 4))
]
testMap = Map("Test Map", testObjects, Rect(-100, -100, 100, 100), "map_background")
currentPose: Pose = Pose(Pos(0, 0, 0), Angle(0))
currentMap: Map = testMap
selectedObject: Optional[Object] = None
tick: int = 0
lastKeys: list[int] = []
keysFirstSeen: dict[int, int] = {}
selectedObject: Optional[Object] = None
# *UI
objectButtons: list[g.RenderButton] = []
objectButtonsBackground: list[g.RenderImage] = []
editButtons: list[g.RenderButton] = []
dataTexts: dict[str, g.RenderText] = {}

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

def setSelectedType(objType: Type[SpecificObject]) -> None:
    global objectButtons, objectButtonsBackground
    _spacing2 = TILESIZE/2
    
    _objectButtonData: list[tuple[Optional[str], Object, float]] = [] # TODO: add more Buttons
    for obj in objects[objType]:
        _objectButtonData.append((obj.getSprite(), obj, 1)) # TODO: add size dynamically
    
    removeListObjects(objectButtons)
    removeListObjects(objectButtonsBackground)
    objectButtons = []
    objectButtonsBackground = []
    
    _objectLength: int = len(_objectButtonData)
    if _objectLength == 0:
        return
    width2 = min(2*TILESIZE, RESOLUTION[0]/_objectLength - _spacing2)
    maxSpace2 = 3*TILESIZE
    y = RESOLUTION[1]-5.5*TILESIZE
    for i, (sprite, obj, size) in enumerate(_objectButtonData):
            height = width2 / size
            x = min(i*(maxSpace2+width2), i/_objectLength * RESOLUTION[0]) + (width2+TILESIZE)/2
            objectButtons.append(g.RenderButton(imageName=sprite, clickAction=placeObject, arguments=(obj,), x=x, y=y, width=width2, height=height, middle=True, priority=UI_LEVEL+3))
            objectButtonsBackground.append(g.RenderImage(imageName="select", x=x, y=y, width=width2*SELECT_FACTOR, height=height*SELECT_FACTOR, middle=True, priority=UI_LEVEL+2.5))
    
# *MAIN FUNCTIONS*
def setup() -> None:
    """
    Initializes the map editor.
    
    This function sets up the initial state of the map editor, including loading the map and setting up the camera.
    """
    global editButtons, dataTexts
    root = Tk()
    root.withdraw()
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
    
    _actionButtons: list[g.RenderButton] = []
    _actionLength: int = len(actionButtonData)
    spacing1 = TILESIZE/2
    width1 = min(3*TILESIZE, RESOLUTION[0]/_actionLength - spacing1)
    maxSpace1 = 3*TILESIZE
    for i, (sprite, hoverSprite, func, size) in enumerate(actionButtonData):
        height = width1 / size
        x = min(i*(maxSpace1+width1), i/_actionLength * RESOLUTION[0]) + (width1+TILESIZE)/2
        y = RESOLUTION[1]-0.5*TILESIZE
        _actionButtons.append(g.RenderButton(imageName=sprite, hoverImageName=hoverSprite, clickAction=func, x=x, y=y, width=width1, height=height, middle=True, priority=UI_LEVEL+3))
    
    _spacing2 = TILESIZE/2
    
    _typeButtonData: list[tuple[Optional[str], Type[SpecificObject], Object, float]] = [] # TODO: add more Buttons
    for _type, subObjects in objects.items():
        try:
            obj = subObjects[0]
        except IndexError:
            obj = Box() # Fallback
        _typeButtonData.append((obj.getSprite(), _type, obj, 1)) # TODO: add size dynamically
    
    typeButtons: list[g.RenderButton] = []
    typeButtonsBackground: list[g.RenderImage] = []
    
    _typeLength: int = len(_typeButtonData)
    width2 = min(2*TILESIZE, RESOLUTION[0]/_typeLength - _spacing2)
    maxSpace2 = 3*TILESIZE
    y = RESOLUTION[1]-2.5*TILESIZE
    for i, (sprite, _type, obj, size) in enumerate(_typeButtonData):
        height = width2 / size
        x = min(i*(maxSpace2+width2), i/_typeLength * RESOLUTION[0]) + (width2+TILESIZE)/2
        typeButtons.append(g.RenderButton(imageName=sprite, clickAction=setSelectedType, arguments=(_type,), x=x, y=y, width=width2, height=height, middle=True, priority=UI_LEVEL+3))
        typeButtonsBackground.append(g.RenderImage(imageName="select", x=x, y=y, width=width2*SELECT_FACTOR, height=height*SELECT_FACTOR, middle=True, priority=UI_LEVEL+2.5))
    
    # SIDE BAR
    dataTexts = {
        "ID_name": g.RenderText(text="ID", x=SIDEBAR_WIDTH/2+TILESIZE, middle=True, priority=UI_LEVEL+3, size=INFO_TEXT_SIZE),
        "ID": g.RenderText(text="iii", x=SIDEBAR_WIDTH/2+TILESIZE, middle=True, priority=UI_LEVEL+3, size=INFO_TEXT_SIZE),
        "Position_name": g.RenderText(text="Position", x=SIDEBAR_WIDTH/2+TILESIZE, middle=True, priority=UI_LEVEL+3, size=INFO_TEXT_SIZE),
        "Position": g.RenderText(text="xxxxx | yyyyy | zzzzz", x=SIDEBAR_WIDTH/2+TILESIZE, middle=True, priority=UI_LEVEL+3, size=INFO_TEXT_SIZE),
        "Size_name": g.RenderText(text="Size", x=SIDEBAR_WIDTH/2+TILESIZE, middle=True, priority=UI_LEVEL+3, size=INFO_TEXT_SIZE),
        "Size": g.RenderText(text="xxxxx | yyyyy | zzzzz", x=SIDEBAR_WIDTH/2+TILESIZE, middle=True, priority=UI_LEVEL+3, size=INFO_TEXT_SIZE),
        "Orientation_name": g.RenderText(text="Orientation", x=SIDEBAR_WIDTH/2+TILESIZE, middle=True, priority=UI_LEVEL+3, size=INFO_TEXT_SIZE),
        "Orientation": g.RenderText(text="rrrrr", x=SIDEBAR_WIDTH/2+TILESIZE, middle=True, priority=UI_LEVEL+3, size=INFO_TEXT_SIZE)
    }
    for i, text in enumerate(dataTexts.values()):
        text.y = INFO_DEPTH+(i+floor(i/2))*INFO_TEXT_SIZE
    
    editButtons = [
        # TODO: add penetration level
        # TODO: position buttons
        # TODO: orientation buttons
        # TODO: size buttons
    ]
    # TODO: callout dropdown
    # TODO: add texture buttons automatically
    # LATER: IDs for doors
    setSelectedType(Box)  # Default selected type
    
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
        position = selectedObject.getPosition().getPosition()
        size = selectedObject.getSize().getPosition()
        dataTexts["ID"].updateText(f"{selectedObject.getID():0>3}")
        dataTexts["Position"].updateText(f"{position[0]:>5.2f} | {position[1]:>5.2f} | {position[2]:>5.2f}")
        dataTexts["Size"].updateText(f"{size[0]:>5.2f} | {size[1]:>5.2f} | {size[2]:>5.2f}")
        dataTexts["Orientation"].updateText(f"{selectedObject.getOrientation().getAngle():>5.2f}")
        if _selectedRender:
            _selectedRender.x, _selectedRender.y = SIDEBAR_WIDTH/2+TILESIZE, 8*TILESIZE
            _selectedRender.width = _selectedRender.height = 5*TILESIZE
            _selectedRender.priority = UI_LEVEL + 3
        for obj in dataTexts.values():
               obj.show()
    else:
           for obj in dataTexts.values():
               obj.hide()
    if g.draw() == "quit":
        return True

if __name__ == "__main__":
    setup()
    running = True
    while running:
        if mainLoop(): running = False