from typing import Union, Callable, Any
from classes.types import Message, AgentKey
from dependencies.communications import Request, Event, CommunicationsHandler as Comm, setOnClientJoin, setOnDisconnect
from handlers.config import CONFIG

# TODO 3: host being a player as well

class CommunicationHandler:
    def __init__(self, playerCommandList: dict[str, Callable], hostCommandList: dict[str, Callable], debugLevel: int = 0) -> None:
        self.__messageQueue: list[Message] = []
        self.__ip, self.__port = CONFIG["ip"], CONFIG["port"]
        self.__comm: Union[Comm, None] = None
        self.__type: Union[str, None] = None
        self.__playerCommandList = playerCommandList
        self.__hostCommandList = hostCommandList
        self.__debug = debugLevel
    # Global
    def connectToGame(self, ip: str, port: int) -> None:
        if self.__type is not None:
            print("Already in a lobby")
            return
        self.__comm = Comm(host=False, ip = ip, port=port, maxClients=4, commands = self.__playerCommandList)
        setOnDisconnect(lambda: self.__addMessage("ForceDisconnect", None))
        self.__type = "player"
        self.__addMessage("Connected", None)
    def hostGame(self, port: int) -> None:
        if self.__type is not None:
            print("Already in a lobby")
            return
        setOnClientJoin(lambda: self.__addMessage("ClientConnected", None))
        self.__comm = Comm(host=True, ip = "localhost", port=port, maxClients=4, commands = self.__hostCommandList)
        self.__type = "host"
        self.__addMessage("Hosted", None)
    def disconnect(self) -> None:
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
    
    def selectAgents(self) -> None:
        self.castEvent("StartAgentSelectionEvent", None)
    def selectAgent(self, agent: AgentKey) -> None:
        self.sendRequest("SelectAgent", agent)
    
    # Local
    # Setters
    # Getters
    def getType(self) -> str:
        return self.__type
    def getIPPort(self) -> tuple[str, int]:
        pass
    def getMessages(self) -> list[Message]:
        messages = self.__messageQueue
        self.__messageQueue = self.__messageQueue[len(messages):]
        return messages
       
    def runCycle(self) -> None:
        if self.__type == "player":
            for event in self.__comm.getEvents():
                if self.__debug > 2: print(event)
                self.__handleEvent(event)
                self.__comm.resolveEvent(event.id)
        if self.__type == "host":
            for request in self.__comm.getRequests():
                if self.__debug > 2: print(request)
                self.__handleRequest(request)
                self.__comm.resolveRequest(request.id)
    
    def castEvent(self, head: str, body: Any) -> None:
        if self.__type == "host":
            self.__comm.castEvent(Event(head, body))
    def sendRequest(self, head: str, body: Any) -> None:
        self.__comm.sendRequest(Request(head, body))

    def __addMessage(self, head: str, body: Any):
        self.__messageQueue.append(Message(head, body))
    
    def __handleEvent(self, event: Event):
        match event.head:
            case "EndSession":
                self.__comm.quit()
                self.__type = None
                self.__addMessage("ForceDisconnect", None)
            case "StartAgentSelectionEvent":
                self.__addMessage("OpenAgentSelectMenu", None)
    
    def __handleRequest(self, request: Request):
        match request.head:
            case "SelectAgent":
                self.__addMessage("SelectAgentRequest", (request.signature, request.body))