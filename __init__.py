import os
from config.constants import debug, D
from dependencies.communications import Event, Request
from typing import Union, Callable
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
    "ForceDisconnect": lambda: localMessages.append(Message("ForceDisconnect", None))
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
    if message.head not in ("CastUpdateGameStateEvent", "sendInputRequests", "UpdateRemainingSelectTime"):
        debug(D.LOG, f"Handling Message 🛠️: {message.head}", message.body)
    else:
        debug(D.TRACE, f"Handling Message 🔄🛠️: {message.head}", message.body)
    match message.head:
        case "Initiated":
            debug(D.LOG ,"+++Initiated+++")
        case "Connected":
            menu.setMenu(MenuKey.PLAYER_LOBBY)
        case "Hosted":
            menu.setMenu(MenuKey.HOST_LOBBY)
        case "Disconnected":
            menu.setMenu(MenuKey.PLAY)
        case "OpenServerAgentSelect":
            menu.setMenu(MenuKey.HOST_AGENT_SELECT)
        # MENU
        case "Leave":
            communication.disconnect()
            if server is not None:
                server.close()
        case "Join":
            communication.connectToGame(*message.body)
            client = ClientGameHandler()
        case "Host":
            if communication.getType() is None:
                communication.hostGame(CONFIG["port"])
                server = ServerGameHandler()
        case "Start":
            if server:
                server.start(communication.getConnections())
        case "SelectAgent":
            communication.sendRequest("SelectAgentRequest", message.body) # agent
        case "ForceStart":
            if server and not server.isIngame():
                server.startGame()
                menu.setMenu(MenuKey.IN_GAME_HOST)
        case "StartAgentSelectionEvent":
            localMessages.append(Message("OpenServerAgentSelect", None))
            communication.castEvent("StartAgentSelectionEvent", None)
        case "EndAgentSelectMessage":
            if server and not server.isIngame():
                server.startGame()
        case "UpdateRemainingSelectTime":
            communication.castEvent("UpdateRemainingSelectTimeEvent", message.body) # time
        case "ServerGameStart":
            communication.castEvent("GameStartEvent", message.body) # gameState
        case "CastUpdateGameStateEvent":
            communication.castEvent("UpdateGameStateEvent", message.body) # gameState
        case "sendInputRequests":
            for request in message.body:
                communication.sendRequest(request.head, request.body) # request details
        case "sendTurnToRequest":
            communication.sendRequest("TurnToRequest", message.body) # new angle
        case _:
            debug(D.WARNING, f"Unhandled message 🛠️: {message.head}", message.body)

def handleEvent(event: Event) -> None:
    global server, client
    if event.head not in ("UpdateGameStateEvent", "Ping", "UpdateRemainingSelectTimeEvent"):
        debug(D.LOG, f"Handling Event 📅: {event.head}", event.body)
    else:
        debug(D.TRACE, f"Handling Event 🔄📅: {event.head}", event.body)
    match event.head:
        case "EndSession":
            if comm := communication.getComm(): 
                comm.quit()
            communication.setType(None)
            menu.setMenu(MenuKey.PLAY)
            debug(D.ERROR, "Connection lost")
        case "StartAgentSelectionEvent":
            menu.setMenu(MenuKey.AGENT_SELECT)
        case "UpdateRemainingSelectTimeEvent":
            if client:
                client.setRemainingSelectTime(event.body)
        case "GameStartEvent":
            menu.setMenu(MenuKey.IN_GAME_PLAYER)
            menu.disable()
            if client:
                client.setup(event.body)
        case "UpdateGameStateEvent":
            if client:
                client.updateGameState(event.body)
        case _:
            debug(D.WARNING, f"Unhandled event 📅: {event.head}", event.body)

def handleRequest(request: Request) -> None:
    global server, client
    if request.head not in ("Ping", "MovementRequest"):
        debug(D.LOG, f"Handling Request 📡: {request.head}", request.body)
    else:
        debug(D.TRACE, f"Handling Request 🔄📡: {request.head}", request.body)
    match request.head:
        case "SelectAgentRequest":
            if server and not server.isIngame():
                server.setAgent(request.signature, request.body)
        case "MovementRequest":
            if server:
                server.tryMovement(request.signature, request.body)
        case "TurnToRequest":
            if server:
                server.tryTurnTo(request.signature, request.body)
        case _:
            debug(D.WARNING, f"Unhandled request 📡: {request.head}", request)