import os
from dependencies.communications import Event, Request
from typing import Union
from classes.types import Message, Message, MenuKey, AutoMessageTrigger
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

debug = 4
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
localMessages = []
server: Union[None, ServerGameHandler] = None
client: Union[None, ClientGameHandler] = None
graphics = GraphicsHandler(ROOT)
menu = MenuHandler()
inputs = InputHandler()
playerCommands = {
    "ForceDisconnect": lambda: localMessages.append(Message("ForceDisconnect", None))
}
hostCommands = {}
communication = CommunicationHandler(playerCommands, hostCommands, debug)
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
    if debug > 1: print(message)
    match message.head:
        case "Initiated":
            print("+++Initiated+++")
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
            server.start(communication.getConnections())
        case "SelectAgent":
            communication.sendRequest("SelectAgentRequest", message.body) # agent
        case "ForceStart":
            if not server.isIngame():
                server.startGame()
                menu.setMenu(MenuKey.IN_GAME_HOST)
        case "StartAgentSelectionEvent":
            localMessages.append(Message("OpenServerAgentSelect", None))
            communication.castEvent("StartAgentSelectionEvent", None)
        case "EndAgentSelectMessage":
            if not server.isIngame():
                server.startGame()
        case "UpdateRemainingSelectTime":
            communication.castEvent("UpdateRemainingSelectTimeEvent", message.body) # time
        case "ServerGameStart":
            communication.castEvent("GameStartEvent", message.body) # gameState

def handleEvent(event: Event) -> None:
    global server, client
    if debug > 2: print(event)
    match event.head:
        case "EndSession":
            communication.getComm().quit()
            communication.setType(None)
            menu.setMenu(MenuKey.PLAY)
            if debug >= 0:
                print("Connection lost")
        case "StartAgentSelectionEvent":
            menu.setMenu(MenuKey.AGENT_SELECT)
        case "UpdateRemainingSelectTimeEvent":
            client.setRemainingSelectTime(event.body)
        case "GameStartEvent":
            pass
            # TODO: event.body
    
def handleRequest(request: Request) -> None:
    global server, client
    if debug > 2: print(request)
    match request.head:
        case "SelectAgentRequest":
            if not server.isIngame():
                server.setAgent(request.signature, request.body)