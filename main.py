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
            for action in core.server.getActions():
                core.handleServerAction(action)
        # Menu
        core.menu.update(core.client, core.server)
        for action in core.menu.getActions():
            core.handleMenuAction(action)
        # Client
        if core.client is not None:
            core.client.tick()
            for input_ in core.inputs.getInputs():
                if core.menu.isEnabled():
                    core.menu.handleInput(input_)
                elif core.client.inGame():
                    core.client.handleInput(input_)
            if core.client is not None:
                for action in core.client.getActions():
                    core.handleGameAction(action)
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
        # Graphics
        core.graphics.draw()
    # TODO 10: Close everything

if __name__ == "__main__":
    main()