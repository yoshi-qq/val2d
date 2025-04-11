from typing import Union
from classes.types import AutoMessage
import __init__ as core

def main(autoMessages: Union[None, list[AutoMessage]] = None) -> None:
    global core
    nextMessages = []
    while core.loop:
        # Menu
        for action in core.menu.getActions():
            core.handleMenuAction(action)
        # Input
        for input_ in core.inputs.getInputs():
            if core.menu.isEnabled():
                core.menu.handleInput(input_)
            elif core.game.inGame():
                core.game.handleInput(input_)
        # Communication
        core.communication.runCycle()
        extraMessages = core.localMessages.copy()
        allMessages = core.communication.getMessages() + extraMessages
        # Automation BEGIN
        if autoMessages is not None:
            for aMessage in autoMessages:
                if aMessage.triggerMessage in allMessages:
                    core.localMessages.append(aMessage.responseMessage)
        # Automation END
        for message in allMessages:
            core.handleMessage(message)
        # core.localMessages = core.localMessages[len(extraMessages):]
        # Game
        core.game.tick()
        if core.communication.getType() == "player":
            for action in core.game.getActions():
                core.handleGameAction(action)
        if core.server is not None:
            for action in core.server.getActions():
                core.handleServerAction(action)
        # Graphics
        core.graphics.draw()
    # TODO 10: Close everything

if __name__ == "__main__":
    main()