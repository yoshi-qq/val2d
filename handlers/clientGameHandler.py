from time import time as now
from math import atan2, degrees
from dependencies.communications import Request
from config.constants import AGENT_SELECT_TIME, PING_INTERVAL, debug, D, DEFAULT_ACCELERATION, DEFAULT_SENSITIVITY
from typing import Union, Any
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
            debug(D.ERROR, "Local GameState is None")
            return
        if not self.__inGame:
            debug(D.WARNING, f"Local Player {playerName} tried to move while not in game")
            return
        if not (player := self.__gameState.getPlayer(playerName)):
            debug(D.WARNING, f"Local Couldnt move Player {playerName}", f"Player {playerName} not found in game")
            return
        if not player.getStatus().isAlive():
            debug(D.LOG, f"Local Player {playerName} tried to move while dead")
            return
        if accelerationDirection is None:
            player.setAcceleration(getZeroPosition())
            return
        newAcceleration = getForwardPosition().rotate(accelerationDirection)*DEFAULT_ACCELERATION
        player.setAcceleration(newAcceleration)
    
    def __tickMovement(self, passedTime: float) -> None:
        if self.__gameState is None:
            debug(D.WARNING, "Local GameState is None")
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
            debug(D.ERROR, "Local GameState is None")
            return
        if (player := self.getOwnPlayer()) is None:
            debug(D.ERROR, f"Couldn't turn Player {self.__name}", f"Player {self.__name} not found in local game")
            return
        turnAmount = mouseMovement[0] * DEFAULT_SENSITIVITY
        turnAngle = Angle(turnAmount)
        self.__ownAngle = player.getPose().turn(turnAngle)
        self.__sendMessage("sendTurnToRequest", self.__ownAngle)
    
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
                        debug(D.TRACE, f"Unhandled held Input 🎮: {input}", "couldnt case match input.type")
                    else:
                        debug(D.WARNING, f"Unhandled Input 🎮: {input}", "couldnt case match input.type")
        self.__walking = walk
        self.__crouching = crouch
        # Walking
        if (player := self.getOwnPlayer()) is None:
                debug(D.WARNING, "Couldn't walk, Local Player is None")
        elif self.__walking != player.getStatus().isWalking():    
            if self.__walking:
                player.getStatus().setWalk(True)
                serverRequests.append(Request("SetWalkStatusRequest", True))
            else:
                player.getStatus().setWalk(False)
                serverRequests.append(Request("SetWalkStatusRequest", False))
        
        # Crouching
        if (player := self.getOwnPlayer()) is None:
                debug(D.WARNING, "Couldn't crouch, Local Player is None")
        elif self.__crouching != player.getStatus().isCrouched():    
            if self.__crouching:
                player.getStatus().setCrouch(True)
                serverRequests.append(Request("SetCrouchStatusRequest", True))
            else:
                player.getStatus().setCrouch(False)
                serverRequests.append(Request("SetCrouchStatusRequest", False))
        
        self.__accelerationDirection: Angle | None = Angle(degrees(atan2(accelerationVector[0], accelerationVector[1]))) if accelerationVector != (0, 0) else None
        serverRequests.append(Request("MovementRequest", self.__accelerationDirection))
        self.__sendMessage("sendInputRequests", serverRequests) 
        
    # Local
    def __sendMessage(self, head: str, body: Any) -> None:
        self.__messageQueue.append(Message(head, body))
    
    def __pingTick(self) -> None: # type: ignore TODO
        if now() - self.__lastPingTime > PING_INTERVAL:
            newPing = Ping(now())
            self.__pingQueue.append(newPing)
            self.__lastPingTime = newPing.time
            self.__sendMessage("Ping", newPing)
        
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
        if not self.__name:
            debug(D.WARNING, "Local name is None")
            return
        if (player := self.getOwnPlayer()) is None:
            debug(D.WARNING, f"Couldn't realign Player turn {self.__name}", f"Player {self.__name} not found in local game")
            return
        if self.__ownAngle is None:
            debug(D.WARNING, "Local ownAngle is None, setting to server side angle")
            self.__ownAngle = player.getPose().getOrientation()
            return
        player.getPose().turnTo(self.__ownAngle)
        player.getStatus().setWalk(self.__walking)
        player.getStatus().setCrouch(self.__crouching)

    def setRemainingSelectTime(self, time: float) -> None:
        self.__remainingSelectTime = time