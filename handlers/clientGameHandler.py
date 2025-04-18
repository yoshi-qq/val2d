from typing import Union, Any
from time import time as now
from math import atan2, degrees
from dependencies.communications import Request
from config.constants import AGENT_SELECT_TIME, PING_INTERVAL, debug, D, DEFAULT_ACCELERATION, DEFAULT_SENSITIVITY, DebugProblem as P, DebugReason as R, DebugDetails as DD
from classes.heads import MessageHead, RequestHead
from classes.types import Message, Input, Ping, Angle
from classes.keys import InputKey
from classes.gameTypes import GameState
from classes.playerTypes import Player
from prebuilts.base import getForwardPosition, getZeroPosition
class ClientGameHandler:
    def __init__(self) -> None:
        self.__accelerationDirection: Angle | None = None
        self.__ownAngle: Angle | None = None
        self.__walking: bool = False
        self.__crouching: bool = False
        self.__remainingSelectTime = AGENT_SELECT_TIME
        self.__messageQueue: list[Message] = []
        self.__inGame = False
        self.__gameState: Union[None, GameState] = None
        self.__pingQueue: list[Ping] = []
        self.__lastPingTime: float = now()
        self.__name: str | None = None
    # Global
    def setGameState(self, gameState: GameState, tickTime: float) -> None:
        self.__gameState = gameState
    
    def getOwnPlayer(self) -> Player | None:
        if self.__name and self.__gameState:
            return self.__gameState.getPlayer(self.__name)
    
    def setup(self, gameState: GameState, ownName: str) -> None:
        self.setGameState(gameState, now())
        self.__name = ownName
        self.__inGame = True
        
    def tick(self) -> None:
        pass
        # self.__pingTick()
    
    def __doMovement(self, playerName: str, accelerationDirection: Angle | None) -> None:
        if self.__gameState is None:
            debug(D.ERROR, P.COULDNT_MOVE_PLAYER_LOCALLY, R.LOCAL_GAMESTATE_IS_NONE)
            return
        if not self.__inGame:
            debug(D.WARNING, P.COULDNT_MOVE_PLAYER_LOCALLY, R.NOT_INGAME, DD.PLAYER_NAME, playerName)
            return
        if not (player := self.__gameState.getPlayer(playerName)):
            debug(D.WARNING, P.COULDNT_MOVE_PLAYER_LOCALLY, R.PLAYER_NOT_FOUND_LOCALLY, DD.PLAYER_NAME, playerName)
            return
        if not player.getStatus().isAlive():
            debug(D.LOG, P.COULDNT_MOVE_PLAYER_LOCALLY, R.PLAYER_IS_DEAD, DD.PLAYER_OBJECT, player)
            return
        if accelerationDirection is None:
            player.setAcceleration(getZeroPosition())
            return
        newAcceleration = getForwardPosition().rotate(accelerationDirection)*DEFAULT_ACCELERATION
        player.setAcceleration(newAcceleration)
    
    def __tickMovement(self, passedTime: float) -> None:
        if self.__gameState is None:
            debug(D.WARNING, P.NO_MOVEMENT_TICK, R.LOCAL_GAMESTATE_IS_NONE)
            return
        for player in self.__gameState.players:
            if player.getStatus().isAlive():
                player.tickMovement(passedTime)
    
    def selfUpdate(self, tickTime: float, name: str) -> None:
        self.__name = name
        self.__doMovement(self.__name, self.__accelerationDirection)
        self.__tickMovement(tickTime)
    
    def handleMouseMovement(self, mouseMovement: tuple[int, int]) -> None:
        if self.__gameState is None:
            debug(D.ERROR, P.NO_MOUSE_HANDLING, R.LOCAL_GAMESTATE_IS_NONE)
            return
        if (player := self.getOwnPlayer()) is None: # TODO: Proper Error Handling (Case Differentation)
            debug(D.ERROR, P.NO_MOUSE_HANDLING, R.PLAYER_NOT_FOUND_LOCALLY, DD.PLAYER_NAME, self.__name)
            return
        turnAmount = mouseMovement[0] * DEFAULT_SENSITIVITY
        turnAngle = Angle(turnAmount)
        self.__ownAngle = player.getPose().turn(turnAngle)
        self.__sendMessage(MessageHead.SEND_TURN_REQUEST, self.__ownAngle)
    
    def handleInputs(self, inputs: list[Input]) -> None:
        accelerationVector: tuple[int, int] = (0, 0)
        serverRequests: list[Request] = []
        walk = False
        crouch = False
        for input in inputs:
            match input.type:
                case InputKey.UP:
                    accelerationVector = (accelerationVector[0], accelerationVector[1]+1)
                case InputKey.DOWN:
                    accelerationVector = (accelerationVector[0], accelerationVector[1]-1)
                case InputKey.RIGHT:
                    accelerationVector = (accelerationVector[0]+1, accelerationVector[1])
                case InputKey.LEFT:
                    accelerationVector = (accelerationVector[0]-1, accelerationVector[1])
                case InputKey.WALK: # TODO: toggle sneak implementation
                    walk = True
                case InputKey.CROUCH:
                    crouch = True
                    
                case _:
                    if input.held:
                        debug(D.TRACE, P.UNHANDLED_HELD_INPUT, R.NO_INPUTTYPE_MATCH, DD.INPUTTYPE, input.type)
                    else:
                        debug(D.TRACE, P.UNHANDLED_INPUT, R.NO_INPUTTYPE_MATCH, DD.INPUTTYPE, input.type)
        self.__walking = walk
        self.__crouching = crouch
        # Walking
        if (player := self.getOwnPlayer()) is None:
            debug(D.WARNING, P.WALK_STATUS_UNCHANGED, R.LOCAL_PLAYER_IS_NONE)
        elif self.__walking != player.getStatus().isWalking():    
            if self.__walking:
                player.getStatus().setWalk(True)
                serverRequests.append(Request(RequestHead.SET_WALK_REQUEST, True))
            else:
                player.getStatus().setWalk(False)
                serverRequests.append(Request(RequestHead.SET_WALK_REQUEST, False))
        
        # Crouching
        if (player := self.getOwnPlayer()) is None:
            debug(D.WARNING, P.CROUCH_STATUS_UNCHANGED, R.LOCAL_PLAYER_IS_NONE)
        elif self.__crouching != player.getStatus().isCrouched():    
            if self.__crouching:
                player.getStatus().setCrouch(True)
                serverRequests.append(Request(RequestHead.SET_CROUCH_REQUEST, True))
            else:
                player.getStatus().setCrouch(False)
                serverRequests.append(Request(RequestHead.SET_CROUCH_REQUEST, False))
        
        self.__accelerationDirection: Angle | None = Angle(degrees(atan2(accelerationVector[0], accelerationVector[1]))) if accelerationVector != (0, 0) else None
        serverRequests.append(Request(RequestHead.MOVEMENT_REQUEST, self.__accelerationDirection))
        self.__sendMessage(MessageHead.SEND_INPUT_REQUESTS, serverRequests) 
        
    # Local
    def __sendMessage(self, head: MessageHead, body: Any) -> None:
        self.__messageQueue.append(Message(head, body))
    
    def __pingTick(self) -> None: # type: ignore TODO
        if now() - self.__lastPingTime > PING_INTERVAL:
            newPing = Ping(now())
            self.__pingQueue.append(newPing)
            self.__lastPingTime = newPing.time
            self.__sendMessage(MessageHead.PING, newPing)
        
    # Getters
    def inGame(self) -> bool:
        return self.__inGame
    def getGameState(self) -> Union[None, GameState]:
        return self.__gameState
    def getRemainingSelectTime(self) -> float:
        return self.__remainingSelectTime
    def getMessages(self) -> list[Message]:
        messages = self.__messageQueue
        self.__messageQueue = self.__messageQueue[len(messages):]
        return messages
    
    # Setters
    def updateGameState(self, newGameState: GameState) -> None:
        self.__gameState = newGameState
        if (player := self.getOwnPlayer()) is None:
            debug(D.WARNING, P.NO_PLAYER_RESET_TO_LOCAL_VALUES, R.PLAYER_NOT_FOUND_LOCALLY) # TODO: Detaills for getOwnPlayer Failure
            return
        player.getStatus().setWalk(self.__walking)
        player.getStatus().setCrouch(self.__crouching)
        if self.__ownAngle is None:
            debug(D.WARNING, P.NO_PLAYER_RESET_TO_LOCAL_ORIENTATION, R.LOCAL_ANGLE_IS_NONE)
            self.__ownAngle = player.getPose().getOrientation()
            return
        player.getPose().turnTo(self.__ownAngle)

    def setRemainingSelectTime(self, time: float) -> None:
        self.__remainingSelectTime = time