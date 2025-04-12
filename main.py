from typing import Union
from classes.types import Message, AutoMessageAction
import __init__ as core

core.localMessages.append(Message("Initiated", None))

def main(autoMessageActions: Union[None, list[AutoMessageAction]] = None) -> None:
    global core
    while core.loop:
        # Server
        if core.server is not None:
            core.server.tick(core.menu.getMenu())
        # Menu
        core.menu.update(core.client, core.server)
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
        extraMessages = core.getLocalMessages()
        allMessages = core.communication.getMessages() + extraMessages
        # Automation BEGIN
        if autoMessageActions is not None:
            for aMessage in autoMessageActions:
                if aMessage.triggerMessage in allMessages:
                    core.menu.addAction(aMessage.responseAction)
        # Automation END
        for message in allMessages:
            core.handleMessage(message)
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