from time import time as now
from threading import Thread
from config.constants import AGENT_SELECT_TIME, debug, D, DEFAULT_ACCELERATION
from classes.heads import MessageHead
from classes.types import Message, AgentKey, Connection, Angle, Pose, Position
from classes.gameTypes import GameState
from classes.playerTypes import Player
from classes.gameTypes import GameModeKey
from classes.keys import MenuKey, MapKey
from prebuilts.base import getForwardPosition, getZeroPosition

class ServerGameHandler:
    def __init__(self) -> None:
        self.__messageQueue: list[Message] = []
        self.__inLoading = False
        self.__inGame = False
        self.__gameState: GameState = GameState([], -1, 0, (0, 0), MapKey.ASCENT, GameModeKey.UNRATED, -1, [])
        self.__roundStartTime: int = -1 # type: ignore TODO LATER
    def close(self) -> None:
        pass
    def tick(self, passedTime: float, menu: MenuKey) -> None:
        if menu == MenuKey.HOST_AGENT_SELECT:
            self.__messageQueue.append(Message(MessageHead.UPDATE_REMAINING_SELECT_TIME, self.getRemainingSelectTime()))
        if menu == MenuKey.IN_GAME_HOST:
            self.__messageQueue.append(Message(MessageHead.CAST_UPDATE_GAMESTATE_EVENT, self.__gameState))
        self.tickMovement(passedTime)
            
    def start(self, connections: list[Connection]) -> None:
        self.__inLoading = True
        self.__messageQueue.append(Message(MessageHead.START_AGENT_SELECT, None))
        self.__gameState.players = []
        for i, connection in enumerate(connections):
            self.addPlayer(Player(name = connection.getName(), pose=Pose(Position((i%3-1)*10, 0, (i//3-1)*10), Angle(0))))
        
        self.__selectStartTime = now()
        def endAgentSelectAtTime() -> None:
            while self.getRemainingSelectTime() > 0:
                pass
            self.__messageQueue.append(Message(MessageHead.END_AGENT_SELECT, None))
        thread = Thread(target=endAgentSelectAtTime)
        thread.start()
    def endAgentSelect(self) -> None:
        self.__selectStartTime = -1
    def startGame(self) -> None:
        for player in self.__gameState.players:
            if player.getAgentKey() is None:
                player.setAgent(AgentKey.OMEN)
        self.__inGame = True
        self.__gameState.time = 0
        self.__messageQueue.append(Message(MessageHead.SERVER_GAME_START, self.__gameState))
        self.startRound()

    def startRound(self) -> None:
        self.__roundStartTime: float = now()
        # TODO NEXT
    
    def tickMovement(self, passedTime: float) -> None:
        for player in self.__gameState.players:
            if player.getStatus().isAlive():
                player.tickMovement(passedTime)
    
    def trySetWalkStatus(self, playerName: str, walk: bool) -> None:
        if not self.__inGame:
            debug(D.WARNING, f"Player {playerName} tried to walk while not in game")
            return
        if not (player := self.__gameState.getPlayer(playerName)):
            debug(D.WARNING, f"Couldnt set walk status Player {playerName}", f"Player {playerName} not found in game")
            return
        if not player.getStatus().isAlive():
            debug(D.LOG, f"Player {playerName} tried to set walk status while dead")
            return
        player.getStatus().setWalk(walk)
    
    def trySetCrouchStatus(self, playerName: str, crouch: bool) -> None:
        if not self.__inGame:
            debug(D.WARNING, f"Player {playerName} tried to crouch while not in game")
            return
        if not (player := self.__gameState.getPlayer(playerName)):
            debug(D.WARNING, f"Couldnt set crouch status Player {playerName}", f"Player {playerName} not found in game")
            return
        if not player.getStatus().isAlive():
            debug(D.LOG, f"Player {playerName} tried to set crouch status while dead")
            return
        player.getStatus().setCrouch(crouch)
        
    def tryTurnTo(self, playerName: str, newAngle: Angle) -> None:
        if not self.__inGame:
            debug(D.WARNING, f"Player {playerName} tried to turn while not in game")
            return
        if not (player := self.__gameState.getPlayer(playerName)):
            debug(D.WARNING, f"Couldnt turn Player {playerName}", f"Player {playerName} not found in game")
            return
        if not player.getStatus().isAlive():
            debug(D.LOG, f"Player {playerName} tried to turn while dead")
            return
        player.getPose().turnTo(newAngle)
    
    def tryMovement(self, playerName: str, accelerationDirection: Angle | None) -> None:
        if not self.__inGame:
            debug(D.WARNING, f"Player {playerName} tried to move while not in game")
            return
        if not (player := self.__gameState.getPlayer(playerName)):
            debug(D.WARNING, f"Couldnt move Player {playerName}", f"Player {playerName} not found in game")
            return
        if not player.getStatus().isAlive():
            debug(D.LOG, f"Player {playerName} tried to move while dead")
            return
        if accelerationDirection is None:
            player.setAcceleration(getZeroPosition())
            return
        newAcceleration = getForwardPosition().rotate(accelerationDirection).rotate(player.getPose().getOrientation())*DEFAULT_ACCELERATION
        player.setAcceleration(newAcceleration)

    # Setters
    def setGamemode(self, mode: GameModeKey) -> None:
        self.__gameState.gameMode = mode
    def setMap(self, mapKey: MapKey) -> None:
        self.__gameState.mapKey = mapKey
    def setAgent(self, playerName: str, agent: AgentKey) -> None:
        for player in self.__gameState.players:
            if player.getName() == playerName:
                player.setAgent(agent)

    def addPlayer(self, player: Player) -> None:
        self.__gameState.players.append(player)
    def removePlayer(self, player: Player) -> None:
        self.__gameState.players.remove(player)
    # Getters
    def isIngame(self) -> bool:
        return self.__inGame
    def isInLoading(self) -> bool:
        return self.__inLoading
    def getMessages(self) -> list[Message]:
        messages = self.__messageQueue
        self.__messageQueue = self.__messageQueue[len(messages):]
        return messages
    def getGameState(self) -> GameState:
        return self.__gameState
    def getRemainingSelectTime(self) -> float:
        return AGENT_SELECT_TIME - now() + self.__selectStartTime