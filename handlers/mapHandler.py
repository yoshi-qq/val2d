from typing import Optional
from config.constants import ZOOM_IN
from dependencies import graphy as g
from classes.types import Pose
from classes.mapTypes import Object, Wall, Box, Cylinder, Stair, Decoration, BreakableDoor, Switch, Bike, UltOrb, Zipline, Teleporter, TPDoor, RotatingDoor, CrouchDoor, Abyss, SpawnPoint, PlantSite
from helpers.graphicsHelper import getPoseAndSizeFromPerspective

# region Specific Object Rendering
def createWallRender(object: Wall, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    return
def createBoxRender(object: Box, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    if (sprite := object.getSprite()) is None:
        return None
    width, height, length = object.getSize().getPosition()
    pose, size = getPoseAndSizeFromPerspective(perspective, object.getPose(), True)
    x, y, z = pose.getPosition().getPosition()
    x = x*ZOOM_IN + g.middle[0]
    z = z*ZOOM_IN + g.middle[1]
    angle = pose.getOrientation().getAngle()
    
    width *= size
    height *= size
    length *= size
    return g.RenderImage(temporary=True, imageName=sprite, x=x, priority= y, y=z, width=width, height=length, middle=True, angle=angle)
    
def createCylinderRender(object: Cylinder, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    return
def createStairRender(object: Stair, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    return
def createDecorationRender(object: Decoration, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    return
def createBreakableDoorRender(object: BreakableDoor, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    return
def createSwitchRender(object: Switch, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    return
def createBikeRender(object: Bike, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    return
def createUltOrbRender(object: UltOrb, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    return
def createZiplineRender(object: Zipline, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    return
def createTeleporterRender(object: Teleporter, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    return
def createTPDoorRender(object: TPDoor, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    return
def createRotatingDoorRender(object: RotatingDoor, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    return
def createCrouchDoorRender(object: CrouchDoor, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    return
def createAbyssRender(object: Abyss, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    return
def createSpawnPointRender(object: SpawnPoint, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    return
def createPlantSiteRender(object: PlantSite, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    return
# endregion Specific Object Rendering


def createObjectRender(object: Object, perspective: Pose, editable: bool = False) -> Optional["g.RenderObject"]:
    """
    Creates a RenderObject for an object from the given perspective.
    
    Args:
        object (Object): The object to create a render for.
        perspective (Pose): The perspective from which to render the object.
        editable (bool): Whether to render for MapEdit mode. Defaults to False.
        
    Returns:
        Optional[g.RenderObject]: The created RenderObject, or None if the object is not renderable.
    """
    if isinstance(object, Wall):
        return createWallRender(object, perspective, editable)
    elif isinstance(object, Box):
        return createBoxRender(object, perspective, editable)
    elif isinstance(object, Cylinder):
        return createCylinderRender(object, perspective, editable)
    elif isinstance(object, Stair):
        return createStairRender(object, perspective, editable)
    elif isinstance(object, Decoration):
        return createDecorationRender(object, perspective, editable)
    elif isinstance(object, BreakableDoor):
        return createBreakableDoorRender(object, perspective, editable)
    elif isinstance(object, Switch):
        return createSwitchRender(object, perspective, editable)
    elif isinstance(object, Bike):
        return createBikeRender(object, perspective, editable)
    elif isinstance(object, UltOrb):
        return createUltOrbRender(object, perspective, editable)
    elif isinstance(object, Zipline):
        return createZiplineRender(object, perspective, editable)
    elif isinstance(object, Teleporter):
        return createTeleporterRender(object, perspective, editable)
    elif isinstance(object, TPDoor):
        return createTPDoorRender(object, perspective, editable)
    elif isinstance(object, RotatingDoor):
        return createRotatingDoorRender(object, perspective, editable)
    elif isinstance(object, CrouchDoor):
        return createCrouchDoorRender(object, perspective, editable)
    elif isinstance(object, Abyss):
        return createAbyssRender(object, perspective, editable)
    elif isinstance(object, SpawnPoint):
        return createSpawnPointRender(object, perspective, editable)
    elif isinstance(object, PlantSite):
        return createPlantSiteRender(object, perspective, editable)
    else:
        return None

def createObjectRenders(objects: list[Object], perspective: Pose, editable: bool = False) -> list["g.RenderObject"]:
    """
    Creates a list of RenderObjects from the given objects and perspective.
    
    Args:
        objects (list[Object]): The list of objects to create renders for.
        perspective (Pose): The perspective from which to render the objects.
        editable (bool): Whether to render for MapEdit mode. Defaults to False.
        
    Returns:
        list["g.RenderObject"]: A list of RenderObjects created from the given objects and perspective.
    """
    renders: list[g.RenderObject] = []
    for obj in objects:
        render = createObjectRender(obj, perspective, editable)
        if render is not None:
            renders.append(render)
    return renders