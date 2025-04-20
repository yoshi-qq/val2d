from math import sqrt, sin, cos, tan, atan2, radians
from config.constants import PLAYER_HEIGHT, VIEW_WIDTH, VIEW_ANGLE, ZOOM_IN, HEIGHT_TO_Z_OFFSET
from classes.types import Pose, Position, Angle

def getSizeFromY(y: float) -> float:
    y = y - PLAYER_HEIGHT
    return (1+y/(VIEW_WIDTH/(2*tan(radians(VIEW_ANGLE)/2))-y)) * ZOOM_IN
    
def getPoseAndSizeFromPerspective(perspective: Pose, objectPose: Pose, turnable: bool) -> tuple[Pose, float]:
    ownX, ownY, ownZ = perspective.getPosition().getX(), perspective.getPosition().getY(), perspective.getPosition().getZ()
    objX, objY, objZ = objectPose.getPosition().getX(), objectPose.getPosition().getY(), objectPose.getPosition().getZ()
    X, Y, Z = objX - ownX, objY - ownY, objZ - ownZ
    angle = perspective.getOrientation().getAngle()
    objAngle = objectPose.getOrientation().getAngle()
    newX = sqrt(X**2 + Z**2) * cos(radians(angle) + atan2(Z, X))
    newY = Y
    newZ = sqrt(X**2 + Z**2) * sin(radians(angle) + atan2(Z, X)) + Y*HEIGHT_TO_Z_OFFSET
    if turnable:
        newAngle = objAngle - angle
    else: newAngle = 0
    pose = Pose(Position(newX, newY, newZ), Angle(newAngle))
    size = getSizeFromY(newY)
    return pose, size