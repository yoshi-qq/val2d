import os
from config.constants import debug, D
from dependencies.communications import Event, Request
from typing import Union, Callable
from classes.heads import EventHead, RequestHead, MessageHead, DebugProblem as P, DebugReason as R, DebugDetails as DD
from classes.types import Message
from classes.keys import MenuKey
from handlers.graphicsHandler import GraphicsHandler
from handlers.menuHandler import MenuHandler
from handlers.inputHandler import InputHandler
from handlers.communicationHandler import CommunicationHandler
from handlers.serverGameHandler import ServerGameHandler
from handlers.clientGameHandler import ClientGameHandler
from handlers.config import CONFIG

from prebuilts.abilities import init as initAbilities
from prebuilts.agents import init as initAgents
from prebuilts.effects import init as initEffects
from prebuilts.maps import init as initMaps
from prebuilts.spriteSets import init as initSpriteSets
from prebuilts.weapons import init as initWeapons

ROOT = os.path.dirname(__file__)
# Setup
def setup() -> None:
    initAbilities()
    initAgents()
    initEffects()
    initMaps()
    initSpriteSets()
    initWeapons()


setup()
localMessages: list[Message] = []
server: Union[None, ServerGameHandler] = None
client: Union[None, ClientGameHandler] = None
graphics = GraphicsHandler(ROOT)
menu = MenuHandler()
inputs = InputHandler()
playerCommands: dict[str, Callable[[], None]] = {
    "ForceDisconnect": lambda: localMessages.append(Message(MessageHead.FORCE_DISCONNECT, None))
}
hostCommands: dict[str, Callable[[], None]] = {}
communication = CommunicationHandler(playerCommands, hostCommands)
menu.setMenu(MenuKey.PLAY)
loop = True

def addLocalMessage(message: Message) -> None:
    global localMessages
    localMessages.append(message)

def getLocalMessages() -> list[Message]:
    global localMessages
    messages = localMessages.copy()
    localMessages = localMessages[len(messages):]
    return messages

# HANDLING
def handleMessage(message: Message) -> None:
    global server, client
    try: head = MessageHead(message.head)
    except ValueError:
        debug(D.ERROR, P.UNHANDLED_MESSAGE, R.INVALID_MESSAGE_HEAD, DD.MESSAGE_HEAD, {message.head})
        return
    if head not in (MessageHead.CAST_UPDATE_GAMESTATE_EVENT, MessageHead.SEND_INPUT_REQUESTS, MessageHead.UPDATE_REMAINING_SELECT_TIME):
        debug(D.LOG, P.HANDLING_MESSAGE, R.EXPECTED, DD.FULL_MESSAGE, message)
    else:
        debug(D.LOG, P.HANDLING_MESSAGE, R.CYCLE, DD.FULL_MESSAGE, message)
    match head:
        case MessageHead.INITIATED:
            debug(D.LOG , P.INITIATED)
        case MessageHead.CONNECTED:
            menu.setMenu(MenuKey.PLAYER_LOBBY)
        case MessageHead.HOSTED:
            menu.setMenu(MenuKey.HOST_LOBBY)
        case MessageHead.CLIENT_CONNECTED:
            debug(D.LOG, P.CLIENT_CONNECTED, R.EXPECTED, DD.CLIENT_NAME, message.body.name) # Server.Client Object from networking
        case MessageHead.DISCONNECTED:
            menu.setMenu(MenuKey.PLAY)
        case MessageHead.OPEN_SERVER_AGENT_SELECT:
            menu.setMenu(MenuKey.HOST_AGENT_SELECT)
        # MENU
        case MessageHead.LEAVE:
            communication.disconnect()
            if server is not None:
                server.close()
        case MessageHead.JOIN:
            communication.connectToGame(*message.body)
            client = ClientGameHandler()
        case MessageHead.HOST:
            if communication.getType() is None:
                communication.hostGame(CONFIG["port"])
                server = ServerGameHandler()
        case MessageHead.START:
            if server and not server.isInLoading():
                server.start(communication.getConnections())
        case MessageHead.SELECT_AGENT:
            communication.sendRequest(RequestHead.SELECT_AGENT, message.body) # agent
        case MessageHead.FORCE_START:
            if server and not server.isIngame():
                server.endAgentSelect()
        case MessageHead.START_AGENT_SELECT:
            localMessages.append(Message(MessageHead.OPEN_SERVER_AGENT_SELECT, None))
            communication.castEvent(EventHead.START_AGENT_SELECT_EVENT, None)
        case MessageHead.END_AGENT_SELECT:
            if server and not server.isIngame():
                menu.setMenu(MenuKey.IN_GAME_HOST)
                server.startGame()
        case MessageHead.UPDATE_REMAINING_SELECT_TIME:
            communication.castEvent(EventHead.UPDATE_REMAINING_SELECT_TIME_EVENT, message.body) # time
        case MessageHead.SERVER_GAME_START:
            communication.castEvent(EventHead.GAME_START_EVENT, message.body) # gameState
        case MessageHead.CAST_UPDATE_GAMESTATE_EVENT:
            communication.castEvent(EventHead.UPDATE_GAMESTATE_EVENT, message.body) # gameState
        case MessageHead.SEND_INPUT_REQUESTS:
            for request in message.body:
                communication.sendRequest(request.head, request.body) # request details
        case MessageHead.SEND_TURN_REQUEST:
            communication.sendRequest(RequestHead.TURN_TO_REQUEST, message.body) # new angle
        case _:
            debug(D.WARNING, P.UNHANDLED_MESSAGE, R.NO_MATCHING_MESSAGE_HEAD, DD.FULL_MESSAGE, message)

def handleEvent(event: Event) -> None:
    if (name := communication.getName()) is None:
        debug(D.ERROR, P.UNHANDLED_EVENT, R.COMM_NOT_INITIALIZED, DD.CLIENT_NAME_IS_NONE)
        return
    global server, client
    if event.head not in (EventHead.UPDATE_GAMESTATE_EVENT, "Ping", EventHead.UPDATE_REMAINING_SELECT_TIME_EVENT):
        debug(D.LOG, P.HANDLING_EVENT, R.EXPECTED, DD.FULL_EVENT, event)
    else:
        debug(D.TRACE, P.HANDLING_EVENT, R.CYCLE, DD.FULL_EVENT, event)
    match event.head:
        case EventHead.END_SESSION:
            if comm := communication.getComm(): 
                comm.quit()
            communication.setType(None)
            menu.setMenu(MenuKey.PLAY)
            debug(D.ERROR, P.CONNECTION_LOST, R.SESSION_ENDED)
        case MessageHead.START_AGENT_SELECT:
            menu.setMenu(MenuKey.AGENT_SELECT)
        case EventHead.UPDATE_REMAINING_SELECT_TIME_EVENT:
            if client:
                client.setRemainingSelectTime(event.body)
        case EventHead.GAME_START_EVENT:
            menu.setMenu(MenuKey.IN_GAME_PLAYER)
            menu.disable()
            if client:
                client.setup(event.body, name)
        case EventHead.UPDATE_GAMESTATE_EVENT:
            if client:
                client.updateGameState(event.body)
        case _:
            debug(D.WARNING, P.UNHANDLED_EVENT, R.NO_MATCHING_EVENT_HEAD, DD.FULL_EVENT, event)

def handleRequest(request: Request) -> None:
    global server, client
    if request.head not in ("Ping", RequestHead.MOVEMENT_REQUEST):
        debug(D.LOG, P.HANDLING_REQUEST, R.EXPECTED, DD.FULL_REQUEST, request)
    else:
        debug(D.LOG, P.HANDLING_REQUEST, R.CYCLE, DD.FULL_REQUEST, request)
    match request.head:
        case RequestHead.SELECT_AGENT:
            if server and not server.isIngame():
                server.setAgent(request.signature, request.body)
        case RequestHead.MOVEMENT_REQUEST:
            if server:
                server.tryMovement(request.signature, request.body)
        case RequestHead.TURN_TO_REQUEST:
            if server:
                server.tryTurnTo(request.signature, request.body)
        case RequestHead.SET_WALK_REQUEST:
            if server:
                server.trySetWalkStatus(request.signature, request.body)
        case RequestHead.SET_CROUCH_REQUEST:
            if server:
                server.trySetCrouchStatus(request.signature, request.body)
        case _:
            debug(D.WARNING, P.UNHANDLED_REQUEST, R.NO_MATCHING_REQUEST_HEAD, DD.FULL_REQUEST, request)