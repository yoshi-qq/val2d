import os
from typing import Union
from classes.types import Message, Action, MenuKey, AutoMessageAction
from handlers.graphicsHandler import GraphicsHandler
from handlers.menuHandler import MenuHandler
from handlers.inputHandler import InputHandler
from handlers.communicationHandler import CommunicationHandler
from handlers.serverHandler import ServerHandler
from handlers.clientHandler import ClientHandler
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
server: Union[None, ServerHandler] = None
client: Union[None, ClientHandler] = None
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

def getLocalMessages() -> list[Message]:
    global localMessages
    messages = localMessages.copy()
    localMessages = localMessages[len(messages):]
    return messages

def handleMessage(message: Message) -> None:
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
        case "ForceDisconnect":
            menu.setMenu(MenuKey.PLAY)
            print("Connection lost")
        case "OpenAgentSelectMenu":
            menu.setMenu(MenuKey.AGENT_SELECT)
        case "SelectAgentRequest":
            if not server.isIngame():
                server.setAgent(message.body[0], message.body[1])
        case "OpenServerAgentSelect":
            menu.setMenu(MenuKey.HOST_AGENT_SELECT)
        case "EndAgentSelect":
            if not server.isIngame():
                server.startGame()
        case "updateClientRemainingSelectTime":
            client.setRemainingSelectTime(message.body)
            
def handleMenuAction(action: Action) -> None:
    global client, server
    if debug > 2: print(action)
    match action.type:
        case "Leave":
            communication.disconnect()
            if server is not None:
                server.close()
        case "Join":
            communication.connectToGame(*action.content)
            client = ClientHandler()
        case "Host":
            if communication.getType() is None:
                communication.hostGame(CONFIG["port"])
                server = ServerHandler()
        case "Start":
            server.start(communication.getConnections())
        case "SelectAgent":
            communication.selectAgent(action.content)
        case "ForceStart":
            localMessages.append(Message("EndAgentSelect", None))
        
def handleGameAction(action: Action) -> None:
    if debug > 3: print(action)
    pass
def handleServerAction(action: Action) -> None:
    if debug > 3: print(action)
    match action.type:
        case "StartAgentSelectionEvent":
            localMessages.append(Message("OpenServerAgentSelect", None))
            communication.selectAgents()
        case "EndAgentSelectAction":
            if not server.isIngame():
                server.startGame()
        case "updateRemainingSelectTime":
            communication.updateRemainingSelectTime(action.content)
        case "serverGameStart":
            communication.gameStartEvent(action.content)