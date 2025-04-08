import os
from handlers.graphicsHandler import GraphicsHandler
from handlers.menuHandler import MenuHandler
from handlers.inputHandler import InputHandler
from handlers.communicationHandler import CommunicationHandler
from handlers.gameHandler import GameHandler
from classes.types import Message, Action
from handlers.config import CONFIG

debug = 3
ROOT = os.path.dirname(__file__)

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
def handleMenuAction(action: Action) -> None:
    if debug > 1: print(action)
    match action.type:
        case "Leave":
            communication.disconnect()
        case "Join":
            communication.connectToGame(*action.content)
        case "Host":
            communication.hostGame(CONFIG["port"])
        case "Start":
            game.start()
def handleGameAction(action: Action) -> None:
    if debug > 1: print(action)
    pass

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
    for action in game.getActions():
        handleGameAction(action)
    # Graphics
    graphics.draw()