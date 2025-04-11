from typing import Union
import __init__ as core

def main(autoEvents: Union[None, list[core.AutoEvent]] = None, autoRequests: Union[None, list[core.AutoRequest]] = None) -> None:
    global core
    while core.loop:
        # Automation TODO
        if autoEvents is not None:
            for aEvent in autoEvents:
                pass
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
        for message in core.communication.getMessages() + extraMessages:
            core.handleMessage(message)
        core.localMessages = core.localMessages[len(extraMessages):]
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