import os
from math import sqrt, sin, cos, atan2, radians
from typing import Optional
from copy import copy
from config.constants import debug, D, PLAYER_HEIGHT, AGENT_SPRITE_DIMENSIONS, ZOOM_IN, SERVER_NAME, RESOLUTION
from classes.keys import MapKey, HandItemKey
from classes.types import Position, Angle, Pose
from classes.playerTypes import Player, Status
from classes.mapTypes import Object
from classes.gameTypes import GameState
from classes.agentTypes import Agent
from classes.finalTypes import Holdable
from prebuilts.agents import agents
from prebuilts.weapons import melees, sidearms, guns
from prebuilts.abilities import abilities
from dependencies import graphy as g
class GraphicsHandler:
    def __init__(self, root: str) -> None:
        ASSETS_FOLDER = os.path.join(root, "assets")
        self.__perspective: Optional[Pose] = None
        self.__gameObjects: list[g.RenderObject] = []
        self.__menuObjects: list[g.RenderObject] = []
        g.init(file=__file__, fps=60, fontPath="font/fixed_sys.ttf", naturalY=True, fullscreen=False, windowName="Val2D", spriteFolder=ASSETS_FOLDER, spriteExtension="png", windowIcon="logo", windowRes=(960, 540), nativeRes = RESOLUTION)
        self.__gameObjectRenders: list[g.RenderObject] = []
    # Global
    def draw(self) -> None:
        g.draw()
    
    def __getPoseAndSizeFromPerspective(self, perspective: Pose, objectPose: Pose) -> tuple[Pose, float]:
        ownX, ownY, ownZ = perspective.getPosition().getX(), perspective.getPosition().getY(), perspective.getPosition().getZ()
        objX, objY, objZ = objectPose.getPosition().getX(), objectPose.getPosition().getY(), objectPose.getPosition().getZ()
        X, Y, Z = objX - ownX, objY - ownY, objZ - ownZ
        angle = perspective.getOrientation().getAngle()
        objAngle = objectPose.getOrientation().getAngle()
        newAngle = objAngle - angle
        newX = sqrt(X**2 + Z**2) * cos(radians(angle) + atan2(Z, X))
        newY = objY
        newZ = sqrt(X**2 + Z**2) * sin(radians(angle) + atan2(Z, X))
        
        pose = Pose(Position(newX, newY, newZ), Angle(newAngle))
        size = (ownY - Y + PLAYER_HEIGHT) / PLAYER_HEIGHT * ZOOM_IN 
        return pose, size
    
    # * Map Rendering
    def __createMapRenders(self, perspective: Pose, mapKey: MapKey) -> list["g.RenderObject"]: # type: ignore TODO
        pass
    
    # * Player Rendering
    def __createAgentRender(self, perspective: Pose, playerPose: Pose, agent: Agent, status: Status) -> "g.RenderObject":
        if not status.isAlive():
            assetName = agent.getSpriteSet().dead
        elif status.isGrounded():
            if status.getVelocity().getY() < 0: # grounded + downward velocity -> just landed
                assetName = agent.getSpriteSet().land
            elif status.isCrouched():
                assetName = agent.getSpriteSet().crouch
            elif status.isHorizontallyMoving():
                assetName = agent.getSpriteSet().walk
            else:
                assetName = agent.getSpriteSet().idle
        elif status.getVelocity().getY() > 0:
            assetName = agent.getSpriteSet().jump
        else:
            assetName = agent.getSpriteSet().fall
        
        pose, size = self.__getPoseAndSizeFromPerspective(perspective, playerPose)
        x, y, z = pose.getPosition().getX(), pose.getPosition().getY(), pose.getPosition().getZ()
        angle = pose.getOrientation().getAngle()
        
        x = x*ZOOM_IN + g.middle[0]
        z = z*ZOOM_IN + g.middle[1]
        
        # TODO: fix rotation being around middle, not bottom middle
        return g.RenderImage(temporary=True, imageName=assetName, x=x, y=z, width=AGENT_SPRITE_DIMENSIONS[0]*size, height=AGENT_SPRITE_DIMENSIONS[1]*size, middle=False, priority=y, angle=angle)
        
    
    # TODO: create this method
    def __createHoldableRender(self, perspective: Pose, playerPose: Pose, holdable: Holdable) -> "g.RenderObject": # type: ignore
        pass
    
    def __createPlayerRender(self, perspective: Pose, player: Player) -> list["g.RenderObject"]:
        renders: list["g.RenderObject"] = []
        agent: Optional[Agent] = None
        if (agentKey := player.getAgentKey()) is not None:
            # * Agent Rendering
            agent = agents[agentKey]
            renders.append(self.__createAgentRender(perspective, player.getPose(), agent, player.getStatus()))
        else: debug(D.ERROR, "Couldn't draw Agent", f"AgentKey is None (Name: {player.getName()})")
        
        # * Holdable Rendering
        inventory = player.getInventory()
        handItemSlotKey = player.getStatus().getHandItemKey()
        handItem: Optional[Holdable] = None
        match handItemSlotKey:
            case HandItemKey.MELEE:
                handItem = melees[inventory.getMeleeKey()]
            case HandItemKey.SIDEARM:
                if (sidearm := inventory.getSidearmKey()) is not None:
                    handItem = sidearms[sidearm]
                else: debug(D.ERROR, "Couldn't draw HandItem", f"Sidearm is None (Name: {player.getName()})")
            case HandItemKey.PRIMARY:
                if (primary := inventory.getPrimaryKey()) is not None:
                    handItem = guns[primary]
                else: debug(D.ERROR, "Couldn't draw HandItem", f"Primary is None (Name: {player.getName()})")
            case HandItemKey.BASIC:
                if agent is not None:
                    handItem = abilities[agent.getAbilityKey(HandItemKey.BASIC)]
                else: debug(D.ERROR, "Couldn't draw HandItem", f"Agent is None (Name: {player.getName()})")
            case HandItemKey.TACTICAL:
                if agent is not None:
                    handItem = abilities[agent.getAbilityKey(HandItemKey.TACTICAL)]
                else: debug(D.ERROR, "Couldn't draw HandItem", f"Agent is None (Name: {player.getName()})")
            case HandItemKey.SIGNATURE:
                if agent is not None:
                    handItem = abilities[agent.getAbilityKey(HandItemKey.SIGNATURE)]
                else: debug(D.ERROR, "Couldn't draw HandItem", f"Agent is None (Name: {player.getName()})")
            case HandItemKey.ULTIMATE:
                if agent is not None:
                    handItem = abilities[agent.getAbilityKey(HandItemKey.ULTIMATE)]
                else: debug(D.ERROR, "Couldn't draw HandItem", f"Agent is None (Name: {player.getName()})")
        if handItem is not None: renders.append(self.__createHoldableRender(perspective, player.getPose(), handItem))
        
        return renders

    def __createPlayerRenders(self, perspective: Pose, players: list[Player]) -> list["g.RenderObject"]:
        renders: list["g.RenderObject"] = []
        for player in players:
            renders += self.__createPlayerRender(perspective, player)
        return renders
    # * Object Rendering
    def __createObjectRenders(self, perspective: Pose, objects: list[Object]) -> list["g.RenderObject"]: # type: ignore TODO
        pass
    
    # * GameState Rendering
    def __createRendersFromPerspective(self, name: str, gameState: GameState) -> list["g.RenderObject"] | None:
        localGameState = copy(gameState)
        if name == SERVER_NAME:
            self.__perspective = Pose(Position(0, 0, 0), Angle(0))
        else:
            for player in localGameState.players:
                if player.getName() == name:
                    self.__perspective = player.getPose()
            if self.__perspective is None:
                debug(D.ERROR, "Coudn't draw gameState", "Perspective is None")
                return
        renders: list["g.RenderObject"] = []
        # renders += self.__createMapRenders(self.__perspective, localGameState.mapKey)
        # renders += self.__createObjectRenders(self.__perspective, localGameState.objects)
        renders += self.__createPlayerRenders(self.__perspective, localGameState.players)
        return renders
    
    def drawGameState(self, clientName: str, gameState: GameState) -> None:
        renders: list["g.RenderObject"] | None = self.__createRendersFromPerspective(clientName, gameState)
        debug(D.TRACE, "Rendering GameState", f"Renders: {renders}")
    # Local
    # Setters
    
            
    
    def setGameVisibility(self, visible: bool) -> None:
        for obj in self.__gameObjects:
            obj.enabled = visible
    def setMenuVisibility(self, visible: bool) -> None:
        for obj in self.__menuObjects:
            obj.enabled = visible
    
    # Getters