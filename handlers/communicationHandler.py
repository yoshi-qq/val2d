from typing import Union, Callable, Any, Literal
from config.constants import DATA_SIZE
from classes.types import Message, Connection
from dependencies.communications import Request, Event, CommunicationsHandler as Comm, setOnClientJoin, setOnDisconnect
from handlers.config import CONFIG

# TODO 7: host being a player as well

class CommunicationHandler:
    def __init__(self, playerCommandList: dict[str, Callable[[], None]], hostCommandList: dict[str, Callable[[], None]], debugLevel: int = 0) -> None:
        self.__messageQueue: list[Message] = []
        self.__eventQueue: list[Event] = []
        self.__requestQueue: list[Request] = []
        self.__ip, self.__port = CONFIG["ip"], CONFIG["port"]
        self.__comm: Union[Comm, None] = None
        self.__type: Union[Literal["player", "host"], None] = None
        self.__playerCommandList = playerCommandList
        self.__hostCommandList = hostCommandList
        self.__debug = debugLevel
    # Global
    def runCycle(self) -> None:
        if self.__comm is None:
            return
        if self.__type == "player":
            for event in self.__comm.getEvents():
                if self.__debug > 3: print(event)
                self.__addEvent(event)
                self.__comm.resolveEvent(event.id)
        if self.__type == "host":
            for request in self.__comm.getRequests():
                if self.__debug > 3: print(request)
                self.__addRequest(request)
                self.__comm.resolveRequest(request.id)
                
    def connectToGame(self, ip: str, port: int) -> None:
        if self.__type is not None:
            print("Already in a lobby")
            return
        self.__comm = Comm(host=False, ip = ip, port=port, maxClients=4, dataSize=DATA_SIZE, commands = self.__playerCommandList)
        setOnDisconnect(lambda: self.__addMessage("ForceDisconnect", None))
        self.__type = "player"
        self.__addMessage("Connected", None)
    
    def hostGame(self, port: int) -> None:
        if self.__type is not None:
            print("Already in a lobby")
            return
        setOnClientJoin(lambda: self.__addMessage("ClientConnected", None))
        self.__comm = Comm(host=True, ip = "0.0.0.0", port=port, maxClients=4, dataSize=DATA_SIZE, commands = self.__hostCommandList)
        self.__type = "host"
        self.__addMessage("Hosted", None)
    def disconnect(self) -> None:
        if self.__comm is None: 
            print("No Connection to disconnect")
            return
        match self.__type:
            case "player":
                self.__comm.quit()
                self.__type = None
                self.__addMessage("Disconnected", None)
            case "host":
                self.__comm.castEvent(Event("EndSession", None))
                self.__comm.quit()
                self.__type = None
                self.__addMessage("Disconnected", None)
            case None:
                pass
    
    def castEvent(self, head: str, body: Any) -> None:
        if self.__comm and self.__type == "host":
            self.__comm.castEvent(Event(head, body))
    def sendRequest(self, head: str, body: Any) -> None:
        if self.__comm:
            self.__comm.sendRequest(Request(head, body))
    
    # Local
    def __addMessage(self, head: str, body: Any):
        self.__messageQueue.append(Message(head, body))
    
    def __addEvent(self, event: Event):
        self.__eventQueue.append(event)
    
    def __addRequest(self, request: Request):
        self.__requestQueue.append(request)
    
    # Setters
    def setType(self, newType: Union[Literal["player", "host"], None]) -> None:
        self.__type = newType
    # Getters
    def getName(self) -> Union[str, None]:
        if self.__comm:
            return self.__comm.getName()
    def getComm(self) -> Union[Comm, None]:
        return self.__comm
    def getType(self) -> Union[Literal["player", "host"], None]:
        return self.__type
    def getIPPort(self) -> tuple[str, int]: # type: ignore TODO
        pass
    def getMessages(self) -> list[Message]:
        messages = self.__messageQueue
        self.__messageQueue = self.__messageQueue[len(messages):]
        return messages
    
    def getConnections(self) -> list[Connection]:
        return [Connection(client.name) for client in self.__comm.getMainObject().clients] # type: ignore

    def getEvents(self) -> list[Event]:
        events = self.__eventQueue
        self.__eventQueue = self.__eventQueue[len(events):]
        return events

    def getRequests(self) -> list[Request]:
        requests = self.__requestQueue
        self.__requestQueue = self.__requestQueue[len(requests):]
        return requests

    def spyEvents(self) -> list[Event]:
        return self.__eventQueue
    
    def spyRequests(self) -> list[Request]:
        return self.__requestQueue