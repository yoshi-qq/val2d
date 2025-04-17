from typing import Union, Callable
from time import sleep, time as now
from config.constants import TICK_RATE, debug, D, SERVER_NAME
from dependencies.communications import Request, Event
from classes.keys import MenuKey
from classes.types import Null, Message, Input, AutoMessageTrigger
from handlers.inputHandler import InputHandler
from handlers.serverGameHandler import ServerGameHandler
from handlers.clientGameHandler import ClientGameHandler
from handlers.menuHandler import MenuHandler
from handlers.communicationHandler import CommunicationHandler
from handlers.graphicsHandler import GraphicsHandler
import __init__ as core

core.localMessages.append(Message("Initiated", None))

def inputTick(inputHandler: InputHandler) -> tuple[list[Input], tuple[int, int]]:
    return inputHandler.getInputs()

def serverTick(passedTime: float, server: Union[None, ServerGameHandler], currentMenu: MenuKey, messageHandleFunction: Callable[[Message], None]) -> None:
    if server is not None:
        server.tick(passedTime, currentMenu)
        for message in server.getMessages():
            messageHandleFunction(message)

def clientTick(name: str | None, tickTime: float, client: Union[None, ClientGameHandler], messageHandleFunction: Callable[[Message], None], inputs: list[Input], mouseMovement: tuple[int, int]) -> None:
    if client is not None and name is not None:
        client.tick()
        if core.menu.isEnabled():
            for input_ in inputs:
                core.menu.handleInput(input_)
        elif client.inGame():
            client.handleInputs(inputs)

        if mouseMovement[0] != 0 or mouseMovement[1] != 0:
            client.handleMouseMovement(mouseMovement)
        for message in client.getMessages():
            messageHandleFunction(message)

def menuTick(tickTime: float, menuHandler: MenuHandler, messageHandleFunction: Callable[[Message], None], server: Union[None, ServerGameHandler], client: Union[None, ClientGameHandler]) -> None:
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

def communicationTick(tickID: int, tickTime: float, inGame: bool, communicationHandler: CommunicationHandler, localMessages: list[Message], addMessageFunction: Callable[[Message], None], autoMessageTriggers: Union[None, list[AutoMessageTrigger]], messageHandleFunction: Callable[[Message], None], eventHandleFunction: Callable[[Event], None], requestHandleFunction: Callable[[Request], None]) -> bool:
    updated = communicationHandler.runCycle(inGame)
    extraMessages = localMessages
    allMessages = communicationHandler.getMessages() + extraMessages
    
    # Automation BEGIN
    if autoMessageTriggers is not None:
        for aMessage in autoMessageTriggers:
            match aMessage.trigger:
                case Message():
                    if aMessage.trigger.body is not Null:
                        if aMessage.trigger in allMessages and aMessage.incrCheck(tickID, tickTime):
                            addMessageFunction(aMessage.responseMessage)
                    elif any(message.head == aMessage.trigger.head for message in allMessages):
                        addMessageFunction(aMessage.responseMessage)
                case Request():
                    if aMessage.trigger.body is not Null:
                        if aMessage.trigger in communicationHandler.spyRequests() and aMessage.incrCheck(tickID, tickTime):
                            addMessageFunction(aMessage.responseMessage)
                    elif any(request.head == aMessage.trigger.head for request in communicationHandler.spyRequests()):
                        addMessageFunction(aMessage.responseMessage)
                case Event():
                    if aMessage.trigger.body is not Null:
                        if aMessage.trigger in communicationHandler.spyEvents() and aMessage.incrCheck(tickID, tickTime):
                            addMessageFunction(aMessage.responseMessage)
                    elif any(event.head == aMessage.trigger.head for event in communicationHandler.spyEvents()):
                        addMessageFunction(aMessage.responseMessage)
    # Automation END
    
    for message in allMessages:
        messageHandleFunction(message)
    for event in communicationHandler.getEvents():
        eventHandleFunction(event)
    for request in communicationHandler.getRequests():
       requestHandleFunction(request)
    return updated
    
def graphicsTick(graphicsHandler: GraphicsHandler, server: Union[None, ServerGameHandler],client: Union[None, ClientGameHandler], clientName: Union[None, str]) -> None:
    if client and client.inGame() and clientName:
        if gameState := client.getGameState():
            graphicsHandler.drawGameState(clientName, gameState)
    elif server and server.isIngame():
        if gameState := server.getGameState():
            graphicsHandler.drawGameState(SERVER_NAME, gameState)
    core.graphics.draw()

#* +++MAIN+++
def main(autoMessageTriggers: Union[None, list[AutoMessageTrigger]] = None) -> None:
    global core
    tickID = 0
    lastTickStart: float = now()
    while core.loop:
        tickID += 1
        tickStart: float = now()
        tickDifference: float = tickStart - lastTickStart
        if tickDifference == 0:
            tickDifference = 1 / TICK_RATE
        if core.server:
            if tickDifference < TICK_RATE:
                debug(D.TRACE, f"Tick fast enough", f"Speed: {1/tickDifference:.2f}t/s > {1/TICK_RATE:.2f}t/s")
                sleep(TICK_RATE - tickDifference)
                tickStart: float = now()
                tickDifference: float = tickStart - lastTickStart
            else:
                debug(D.WARNING, f"Tick too slow", f"Speed: {1/tickDifference:.2f}t/s < {1/TICK_RATE:.2f}t/s")
        #* Input
        inputs, mouseMovement = inputTick(core.inputs)
        
        #* Server
        serverTick(passedTime=tickDifference, server=core.server, currentMenu=core.menu.getMenu(), messageHandleFunction=core.handleMessage)
        
        #* Client
        clientTick(name = core.communication.getName(), tickTime=tickStart, client=core.client, messageHandleFunction=core.handleMessage, inputs=inputs, mouseMovement=mouseMovement)
        
        #* Menu
        menuTick(tickTime=tickStart, menuHandler=core.menu, messageHandleFunction=core.handleMessage, server=core.server, client=core.client)
        
        #* Communication
        updated = communicationTick(tickID=tickID, tickTime=tickStart, inGame=core.client.inGame() if core.client else False, communicationHandler=core.communication, localMessages=core.getLocalMessages(), addMessageFunction=core.addLocalMessage, autoMessageTriggers=autoMessageTriggers, messageHandleFunction=core.handleMessage, eventHandleFunction=core.handleEvent, requestHandleFunction=core.handleRequest)
        
        #* Local Computation
        if (not updated) and core.client and (name := core.communication.getName()):
            debug(D.LOG, f"Server didn't respond in time, {name} is self updating")
            core.client.selfUpdate(tickDifference, name)
        #* Graphics
        graphicsTick(graphicsHandler=core.graphics, server=core.server, client=core.client, clientName=core.communication.getName())

        lastTickStart = tickStart
    # TODO 10: Close everything

if __name__ == "__main__":
    main()