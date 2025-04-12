from typing import Union
from classes.types import Message, AutoMessageTrigger
import __init__ as core

core.localMessages.append(Message("Initiated", None))

def main(autoMessageTriggers: Union[None, list[AutoMessageTrigger]] = None) -> None:
    global core
    while core.loop:
        # Server
        if core.server is not None:
            core.server.tick(core.menu.getMenu())
            for message in core.server.getMessages():
                core.handleServerMessage(message)
        
        # Menu
        core.menu.update(core.client, core.server)
        for message in core.menu.getMessages():
            core.handleMessage(message)
        
        # Client
        if core.client is not None:
            core.client.tick()
            for input_ in core.inputs.getInputs():
                if core.menu.isEnabled():
                    core.menu.handleInput(input_)
                elif core.client.inGame():
                    core.client.handleInput(input_)
            if core.client is not None:
                for message in core.client.getMessages():
                    core.handleGameMessage(message)
        
        # Communication
        core.communication.runCycle()
        extraMessages = core.getLocalMessages()
        allMessages = core.communication.getMessages() + extraMessages
        
        # Automation BEGIN
        if autoMessageTriggers is not None:
            for aMessage in autoMessageTriggers:
                if aMessage.triggerMessage in allMessages:
                    core.addLocalMessage(aMessage.responseMessage)
        # Automation END
        
        for message in allMessages:
            core.handleMessage(message)
        for event in core.communication.getEvents():
            core.handleEvent(event)
        for request in core.communication.getRequests():
            core.handleRequest(request)
        
        # Graphics
        core.graphics.draw()
    # TODO 10: Close everything

if __name__ == "__main__":
    main()