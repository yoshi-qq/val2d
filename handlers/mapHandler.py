from dependencies import graphy as g
from classes.types import Pose
from classes.mapTypes import Object
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
    return renders