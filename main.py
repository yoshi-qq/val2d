from typing import Union, Callable
from dependencies.communications import Request, Event
from classes.keys import MenuKey
from classes.types import Message, Input, AutoMessageTrigger
from handlers.inputHandler import InputHandler
from handlers.serverGameHandler import ServerGameHandler
from handlers.clientGameHandler import ClientGameHandler
from handlers.menuHandler import MenuHandler
from handlers.communicationHandler import CommunicationHandler
from handlers.graphicsHandler import GraphicsHandler
import __init__ as core

core.localMessages.append(Message("Initiated", None))

def inputTick(inputHandler: InputHandler) -> list[Input]:
    return inputHandler.getInputs()

def serverTick(server: Union[None, ServerGameHandler], currentMenu: MenuKey, messageHandleFunction: Callable[[Message], None]) -> None:
    if server is not None:
        server.tick(currentMenu)
        for message in server.getMessages():
            messageHandleFunction(message)

def clientTick(client: Union[None, ClientGameHandler], messageHandleFunction: Callable[[Message], None], inputs: list[Input]) -> None:
    if client is not None:
        client.tick()
        for input_ in inputs:
            if core.menu.isEnabled():
                core.menu.handleInput(input_)
            elif client.inGame():
                client.handleInput(input_)
        for message in client.getMessages():
            core.handleMessage(message)

def menuTick(menuHandler: MenuHandler, messageHandleFunction: Callable[[Message], None], server: Union[None, ServerGameHandler], client: Union[None, ClientGameHandler]) -> None:
    menu = menuHandler.getMenu()
    if menu == MenuKey.HOST_AGENT_SELECT and server is not None:
        remainingTime = server.getRemainingSelectTime()
    elif menu == MenuKey.AGENT_SELECT and client is not None:
        remainingTime = client.getRemainingSelectTime()
    else:
        remainingTime = -1
            
    menuHandler.update(menu, remainingTime)
    for message in menuHandler.getMessages():
        messageHandleFunction(message)

def communicationTick(communicationHandler: CommunicationHandler, localMessages: list[Message], addMessageFunction: Callable[[Message], None], autoMessageTriggers: Union[None, list[AutoMessageTrigger]], messageHandleFunction: Callable[[Message], None], eventHandleFunction: Callable[[Event], None], requestHandleFunction: Callable[[Request], None]) -> None:
    communicationHandler.runCycle()
    extraMessages = localMessages
    allMessages = communicationHandler.getMessages() + extraMessages
    
    # Automation BEGIN
    if autoMessageTriggers is not None:
        for aMessage in autoMessageTriggers:
            match aMessage.trigger:
                case Message():
                    if aMessage.trigger in allMessages:
                        addMessageFunction(aMessage.responseMessage)
                case Request():
                    if aMessage.trigger in communicationHandler.spyRequests():
                        addMessageFunction(aMessage.responseMessage)
                case Event():
                    if aMessage.trigger in communicationHandler.spyEvents():
                        addMessageFunction(aMessage.responseMessage)
    # Automation END
    
    for message in allMessages:
        messageHandleFunction(message)
    for event in communicationHandler.getEvents():
        eventHandleFunction(event)
    for request in communicationHandler.getRequests():
       requestHandleFunction(request)

def graphicsTick(graphicsHandler: GraphicsHandler, client: Union[None, ClientGameHandler], clientName: Union[None, str]) -> None:
    if client is not None and client.inGame() and clientName:
        if gameState := client.getGameState():
            graphicsHandler.drawGameState(clientName, gameState)
    core.graphics.draw()

#* +++MAIN+++
def main(autoMessageTriggers: Union[None, list[AutoMessageTrigger]] = None) -> None:
    global core
    while core.loop:
        #* Input
        inputs = inputTick(core.inputs)
        
        #* Server
        serverTick(server=core.server, currentMenu=core.menu.getMenu(), messageHandleFunction=core.handleMessage)
        
        #* Client
        clientTick(client=core.client, messageHandleFunction=core.handleMessage, inputs=inputs)
        
        #* Menu
        menuTick(menuHandler=core.menu, messageHandleFunction=core.handleMessage, server=core.server, client=core.client)
        
        #* Communication
        communicationTick(communicationHandler=core.communication, localMessages=core.getLocalMessages(), addMessageFunction=core.addLocalMessage, autoMessageTriggers=autoMessageTriggers, messageHandleFunction=core.handleMessage, eventHandleFunction=core.handleEvent, requestHandleFunction=core.handleRequest)
        
        #* Graphics
        graphicsTick(graphicsHandler=core.graphics, client=core.client, clientName=core.communication.getName())
        
    # TODO 10: Close everything

if __name__ == "__main__":
    main()