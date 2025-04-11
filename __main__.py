from __init__ import *

if __name__ == "__main__":
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
    # TODO 10: Close everything