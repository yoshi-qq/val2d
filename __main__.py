import os
from typing import Union
from classes.types import Message, Action
from handlers.graphicsHandler import GraphicsHandler
from handlers.menuHandler import MenuHandler
from handlers.inputHandler import InputHandler
from handlers.communicationHandler import CommunicationHandler
from handlers.gameHandler import GameHandler
from handlers.serverHandler import ServerHandler
from handlers.config import CONFIG

from prebuilts.abilities import init as initAbilities
from prebuilts.agents import init as initAgents
from prebuilts.effects import init as initEffects
from prebuilts.maps import init as initMaps
from prebuilts.spriteSets import init as initSpriteSets
from prebuilts.weapons import init as initWeapons

debug = 3
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
graphics = GraphicsHandler(ROOT)
menu = MenuHandler()
inputs = InputHandler()
playerCommands = {
    "ForceDisconnect": lambda: localMessages.append(Message("ForceDisconnect", None))
}
hostCommands = {}
communication = CommunicationHandler(playerCommands, hostCommands, debug)
game = GameHandler()
server: Union[None, ServerHandler] = None
menu.setMenu("play")
loop = True

def handleMessage(message: Message) -> None:
    if debug > 1: print(message)
    match message.head:
        case "Connected":
            menu.setMenu("playerLobby")
        case "Hosted":
            menu.setMenu("hostLobby")
        case "Disconnected":
            menu.setMenu("play")
        case "ForceDisconnect":
            menu.setMenu("play")
            print("Connection lost")
        case "OpenAgentSelectMenu":
            menu.setMenu("agentSelect")
        case "SelectAgentRequest":
            if not server.isIngame():
                server.setAgent(message.body[0], message.body[1])
            
def handleMenuAction(action: Action) -> None:
    global server
    if debug > 1: print(action)
    match action.type:
        case "Leave":
            communication.disconnect()
            if server is not None:
                server.close()
        case "Join":
            communication.connectToGame(*action.content)
        case "Host":
            communication.hostGame(CONFIG["port"])
            server = ServerHandler()
        case "Start":
            server.start()
        case "SelectAgent":
            communication.selectAgent(action.content)
        
def handleGameAction(action: Action) -> None:
    if debug > 1: print(action)
    pass
def handleServerAction(action: Action) -> None:
    if debug > 1: print(action)
    match action.type:
        case "StartAgentSelectionEvent":
            communication.selectAgents()

while loop:
    # Menu
    for action in menu.getActions():
        handleMenuAction(action)
    # Input
    for input_ in inputs.getInputs():
        if menu.isEnabled():
            menu.handleInput(input_)
        elif game.inGame():
            game.handleInput(input_)
    # Communication
    communication.runCycle()
    extraMessages = localMessages.copy()
    for message in communication.getMessages() + extraMessages:
        handleMessage(message)
    localMessages = localMessages[len(extraMessages):]
    # Game
    game.tick()
    if communication.getType() == "player":
        for action in game.getActions():
            handleGameAction(action)
    if server is not None:
        for action in server.getActions():
            handleServerAction(action)
    # Graphics
    graphics.draw()