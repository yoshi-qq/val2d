import os
from typing import Optional, Literal
from copy import copy
from config.constants import debug, D, AGENT_SPRITE_DIMENSIONS, ZOOM_IN, SERVER_NAME, RESOLUTION, DebugProblem as P, DebugReason as R, DebugDetails as DD
from classes.keys import MapKey, HandItemKey
from classes.types import Position, Angle, Pose
from classes.playerTypes import Player, Status
from classes.mapTypes import Object
from classes.gameTypes import GameState
from classes.agentTypes import Agent
from classes.finalTypes import Holdable
from helpers.graphicsHelper import getPoseAndSizeFromPerspective
from handlers.mapHandler import createObjectRenders
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
        g.init(file=__file__, fps=60, fontPath="font/fixed_sys.ttf", captureCursor=True, naturalY=True, fullscreen=False, windowName="Val2D", spriteFolder=ASSETS_FOLDER, spriteExtension="png", windowIcon="logo", windowRes=(960, 540), nativeRes = RESOLUTION)
        self.__gameObjectRenders: list[g.RenderObject] = []
    # Global
    def draw(self) -> bool | Literal["quit"]:
        return g.draw()
    
    
    
    # * Map Rendering
    def __createMapRenders(self, perspective: Pose, mapKey: MapKey) -> list["g.RenderObject"]: # type: ignore TODO
        pass
    
    # * Player Rendering
    def __isFlipped(self, perspective: Pose, pose: Pose) -> bool:
        ownAngle = perspective.getOrientation()
        objAngle = pose.getOrientation()
        displayAngle = objAngle - ownAngle
        return displayAngle.getAngle() < 180
        
    def __createAgentRender(self, perspective: Pose, playerPose: Pose, agent: Agent, status: Status) -> "g.RenderObject":
        if not status.isAlive():
            assetName = agent.getSpriteSet().dead
        elif not status.isGrounded():
            if status.getVelocity().getY() > 0:
                assetName = agent.getSpriteSet().jump
            else:
                assetName = agent.getSpriteSet().fall
        elif status.getVelocity().getY() < 0: # grounded + downward velocity -> just landed
            assetName = agent.getSpriteSet().land
        elif status.isCrouched():
            assetName = agent.getSpriteSet().crouch
        elif status.isHorizontallyMoving():
            assetName = agent.getSpriteSet().walk
        else:
            assetName = agent.getSpriteSet().idle
        
        flipped = self.__isFlipped(perspective, playerPose)
        pose, size = getPoseAndSizeFromPerspective(perspective, playerPose, False)
        x, _, z = pose.getPosition().getX(), pose.getPosition().getY(), pose.getPosition().getZ()
        angle = pose.getOrientation().getAngle()
        
        x = x*ZOOM_IN + g.middle[0]
        z = z*ZOOM_IN + g.middle[1]
        
        # TODO: fix rotation being around middle, not bottom middle
        return g.RenderImage(temporary=True, imageName=assetName, x=x, y=z, width=AGENT_SPRITE_DIMENSIONS[0]*size, height=AGENT_SPRITE_DIMENSIONS[1]*size, middle=False, priority=100-playerPose.getPosition().getZ(), angle=angle, flipped=flipped)
        
    
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
        else: debug(D.ERROR, P.AGENT_NOT_DRAWN, R.AGENT_KEY_IS_NONE, DD.PLAYER_NAME, player.getName())
        
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
                else: debug(D.ERROR, P.HANDITEM_NOT_DRAWN, R.SIDEARM_IS_NONE, DD.PLAYER_NAME, player.getName())
            case HandItemKey.PRIMARY:
                if (primary := inventory.getPrimaryKey()) is not None:
                    handItem = guns[primary]
                else: debug(D.ERROR, P.HANDITEM_NOT_DRAWN, R.PRIMARY_IS_NONE, DD.PLAYER_NAME, player.getName())
            case HandItemKey.BASIC:
                if agent is not None:
                    handItem = abilities[agent.getAbilityKey(HandItemKey.BASIC)]
                else: debug(D.ERROR, P.HANDITEM_NOT_DRAWN, R.AGENT_IS_NONE, DD.PLAYER_NAME, player.getName())
            case HandItemKey.TACTICAL:
                if agent is not None:
                    handItem = abilities[agent.getAbilityKey(HandItemKey.TACTICAL)]
                else: debug(D.ERROR, P.HANDITEM_NOT_DRAWN, R.AGENT_IS_NONE, DD.PLAYER_NAME, player.getName())
            case HandItemKey.SIGNATURE:
                if agent is not None:
                    handItem = abilities[agent.getAbilityKey(HandItemKey.SIGNATURE)]
                else: debug(D.ERROR, P.HANDITEM_NOT_DRAWN, R.AGENT_IS_NONE, DD.PLAYER_NAME, player.getName())
            case HandItemKey.ULTIMATE:
                if agent is not None:
                    handItem = abilities[agent.getAbilityKey(HandItemKey.ULTIMATE)]
                else: debug(D.ERROR, P.HANDITEM_NOT_DRAWN, R.AGENT_IS_NONE, DD.PLAYER_NAME, player.getName())
        if handItem is not None: renders.append(self.__createHoldableRender(perspective, player.getPose(), handItem))
        
        return renders

    def __createPlayerRenders(self, name: str, perspective: Pose, players: list[Player]) -> list["g.RenderObject"]:
        renders: list["g.RenderObject"] = []
        ownPlayerRender = None
        for player in players:
            if player.getName() != name:
                ownPlayerRender = self.__createPlayerRender(perspective, player)
            else: renders += self.__createPlayerRender(perspective, player)
        if ownPlayerRender is None:
            debug(D.ERROR, P.PLAYER_NOT_DRAWN, R.LOCAL_PLAYER_IS_NONE, DD.CLIENT_NAME, name)
        else: renders += ownPlayerRender
        return renders
    # * Object Rendering
    def __createObjectRenders(self, perspective: Pose, objects: list[Object]) -> list["g.RenderObject"]: # type: ignore TODO
        return createObjectRenders(objects, perspective, False)
    
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
                debug(D.ERROR, P.GAME_STATE_NOT_DRAWN, R.PERSPECTIVE_IS_NONE, DD.CLIENT_NAME, name)
                return
        renders: list["g.RenderObject"] = []
        # renders += self.__createMapRenders(self.__perspective, localGameState.mapKey)
        # renders += self.__createObjectRenders(self.__perspective, localGameState.objects)
        renders += self.__createPlayerRenders(name, self.__perspective, localGameState.players)
        return renders
    
    def drawGameState(self, clientName: str, gameState: GameState) -> None:
        renders: list["g.RenderObject"] | None = self.__createRendersFromPerspective(clientName, gameState)
        debug(D.LOG, P.RENDERING_GAMESTATE, R.CYCLE, DD.RENDERS, renders)
    # Local
    # Setters
    
            
    
    def setGameVisibility(self, visible: bool) -> None:
        for obj in self.__gameObjects:
            obj.enabled = visible
    def setMenuVisibility(self, visible: bool) -> None:
        for obj in self.__menuObjects:
            obj.enabled = visible
    
    # Getters