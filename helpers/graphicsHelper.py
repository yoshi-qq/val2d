from math import sqrt, sin, cos, tan, atan2, radians
from config.constants import VIEW_WIDTH, VIEW_HEIGHT, VIEW_ANGLE, ZOOM_IN, HEIGHT_TO_Z_OFFSET, THREE_D_LEVEL
from classes.types import Pose, Position, Angle

HORIZONTAL_MIDDLE = VIEW_WIDTH / 2
VERTICAL_MIDDLE = VIEW_HEIGHT / 2

def getSizeFromY(y: float) -> float:
    return (1+y/(VIEW_WIDTH/(2*tan(radians(VIEW_ANGLE)/2))-y)) * ZOOM_IN

def getPoseAndSizeFromPerspective(perspective: Pose, objectPose: Pose, turnable: bool, threeDLevel: int = THREE_D_LEVEL) -> tuple[Pose, float]:
    ownX, ownY, ownZ = perspective.getPosition().getX(), perspective.getPosition().getY(), perspective.getPosition().getZ()
    objX, objY, objZ = objectPose.getPosition().getX(), objectPose.getPosition().getY(), objectPose.getPosition().getZ()
    X, Y, Z = objX - ownX, objY - ownY, objZ - ownZ
    angle = perspective.getOrientation().getAngle()
    objAngle = objectPose.getOrientation().getAngle()
    newX = sqrt(X**2 + Z**2) * cos(radians(angle) + atan2(Z, X))
    newY = Y
    newZ = sqrt(X**2 + Z**2) * sin(radians(angle) + atan2(Z, X))
    if threeDLevel >= 3:
        newZ +=  + Y*HEIGHT_TO_Z_OFFSET
    if turnable:
        newAngle = objAngle - angle
    else: newAngle = 0
    size = getSizeFromY(newY if threeDLevel >= 2 else 0)
    newX *= size / ZOOM_IN
    newZ *= size / ZOOM_IN
    pose = Pose(Position(newX, newY, newZ), Angle(newAngle))
    
    return pose, size