# Version: 1.2
from dependencies.networking import * 
from typing import Union, Any, Callable
from threading import Lock
from types import MethodType

HOSTNAME = "Host"

class Request:
    def __init__(self: "Request", head: str, body: Any):
        self.signature: str = "unsigned"
        self.head = head
        self.body = body
        self.id: Union[int, None] = None
class Event:
    def __init__(self: "Event", head: str, body: Any):
        self.head = head
        self.body = body
        self.id: Union[int, None] = None

class CommunicationsHandler:
    def __init__(self: "CommunicationsHandler", host: bool = False, ip: str = "localhost", port: int = 54321, maxClients = 4, commands: dict[str, Callable] = None) -> None:
        if commands is None:
            self.__commands = {}
        else:
            self.__commands = commands
        self._host: bool = host
        self._ip: str = ip
        self._port: int = port
        self.__idCount: int = 1
        self.__queueLock: Lock = Lock()
        if self._host:
            self._maxClients: int = maxClients
            self.__requestQueue: list[Request] = []
            self.__initHost()
        else:
            self.__eventQueue: list[Event] = []
            self.__initClient()
 
    def __getId(self: "CommunicationsHandler"):
        self.__idCount += 1
        return self.__idCount
    def __addRequest(self, sender: str, request: Request):
            localRequest = request
            localRequest.id = self.__getId()
            localRequest.signature = sender
            with self.__queueLock:
                self.__requestQueue.append(localRequest)
    def __initHost(self: "CommunicationsHandler") -> None:
        self.__mainObject = Server(self._ip, self._port, 1024, "pickle", self._maxClients)
        self.__mainObject.messageFunctions = self.__mainObject.messageFunctions | self.__commands
        
        
        # Receiving
        self.__mainObject.messageFunctions["Request"] = self.__addRequest
        
        # Methods
        def getRequests(self: "CommunicationsHandler") -> list[Request]:
            return self.__requestQueue
        def resolveRequest(self: "CommunicationsHandler", requestId: int):
            with self.__queueLock:
                self.__requestQueue[:] = [request for request in self.__requestQueue if request.id != requestId]
        def castEvent(self: "CommunicationsHandler", event: Event) -> None:
            self.__mainObject.sendAll(Message(sender="Host", type="Event", content=event))
        
        self.getRequests = MethodType(getRequests, self)
        self.resolveRequest = MethodType(resolveRequest, self)
        self.castEvent = MethodType(castEvent, self)
        
    def __addEvent(self, sender: str, event: Event):
            if sender != HOSTNAME: return
            localEvent = event
            localEvent.id = self.__getId()
            with self.__queueLock:
                self.__eventQueue.append(localEvent)
                
    def __initClient(self: "CommunicationsHandler") -> None:
        self.__mainObject = Client(self._ip, self._port, 1024, "pickle", False, debug = True)
        self.__mainObject.messageFunctions = self.__mainObject.messageFunctions | self.__commands
        
        
        # Receiving
        self.__mainObject.messageFunctions["Event"] = self.__addEvent
        
        # Methods
        def getEvents(self: "CommunicationsHandler") -> list[Event]:
            return self.__eventQueue
        def resolveEvent(self: "CommunicationsHandler", eventId: int):
            with self.__queueLock:
                self.__eventQueue[:] = [event for event in self.__eventQueue if event.id != eventId]
        def sendRequest(self: "CommunicationsHandler", request: Request) -> None:
            self.__mainObject.send(Message(sender=self.__mainObject.name, type="Request", content=request))
        
        self.getEvents = MethodType(getEvents, self)
        self.resolveEvent = MethodType(resolveEvent, self)
        self.sendRequest = MethodType(sendRequest, self)
        
    def quit(self: "CommunicationsHandler") -> None:
        self.__mainObject.close()

def setOnConnect(func: Callable):
    onConnect = func

def setOnDisconnect(func: Callable):
    onDisconnect = func