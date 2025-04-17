from typing import Any, Callable
from handlers.graphicsHandler import g
from classes.types import Input, Message, agents
from classes.keys import MenuKey, AgentKey
from handlers.config import CONFIG
from dependencies.helpers import distributeObjects

K = MenuKey

class MenuHandler:
    def __init__(self) -> None:
        self.__enabled: bool = True
        self.__menu: MenuKey = K.EMPTY
        self.__messageQueue: list[Message] = []
        self.__menus: dict[MenuKey, list[g.RenderObject]] = {}
        self.__menuUpdaters: dict[MenuKey, Callable[[float], None]] = {}
        self.__setupMenus()
    # Global
    def handleInput(self, input: Input) -> None:
        pass
    def update(self, menu: MenuKey, time: float) -> None:
        if menu in self.__menuUpdaters.keys():
            self.__menuUpdaters[self.__menu](time)
    # Local
    def __addMessage(self, head: str, body: Any) -> None:
        self.__messageQueue.append(Message(head, body))
    
    def __setupMenus(self) -> None:
        # Empty
        self.__menus[K.EMPTY] = []
        
        # Play
        playMenu: list[g.RenderObject] = []
        self.__menus[K.PLAY] = playMenu
        playMenu.append(g.RenderButton(imageName="practice", arguments=(), clickAction=self.__practiceButton, x=g.middle[0]-300, y=g.middle[1]*1.75, width=256, height=32, enabled=False, middle=True))
        playMenu.append(g.RenderButton(imageName="join", clickAction=self.__joinButton, x=g.middle[0]+150, y=g.middle[1]*0.5, width=256, height=32, enabled=False, middle=True))
        playMenu.append(g.RenderButton(imageName="host", clickAction=self.__hostButton, x=g.middle[0]-150, y=g.middle[1]*0.5, width=256, height=32, enabled=False, middle=True))
        
        # HostLobby
        hostLobbyMenu: list[g.RenderObject] = []
        self.__menus[K.HOST_LOBBY] = hostLobbyMenu
        hostLobbyMenu.append(g.RenderButton(imageName="start", clickAction=self.__startButton, x=g.middle[0], y=g.middle[1]*1.75, width=256, height=64, enabled=False, middle=True))
        hostLobbyMenu.append(g.RenderButton(imageName="practice", clickAction=self.__practiceButton, x=g.middle[0]-300, y=g.middle[1]*1.75, width=256, height=32, enabled=False, middle=True))
        hostLobbyMenu.append(g.RenderButton(imageName="leave", clickAction=self.__leaveButton, x=g.middle[0]+300, y=g.middle[1]*1.75, width=256, height=32, enabled=False, middle=True))
        
        # PlayerLobby
        playerLobbyMenu: list[g.RenderObject] = []
        self.__menus[K.PLAYER_LOBBY] = playerLobbyMenu
        playerLobbyMenu.append(g.RenderButton(imageName="practice", clickAction=self.__practiceButton, x=g.middle[0]-300, y=g.middle[1]*1.75, width=256, height=32, enabled=False, middle=True))
        playerLobbyMenu.append(g.RenderButton(imageName="leave", clickAction=self.__leaveButton, x=g.middle[0]+300, y=g.middle[1]*1.75, width=256, height=32, enabled=False, middle=True))

        # PlayerAgentSelect
        agentSelectMenu: list[g.RenderObject] = []
        self.__menus[K.AGENT_SELECT] = agentSelectMenu
        agentLogos: list[tuple[AgentKey, str]] = []
        for key, agent in agents.items():
            agentLogos.append((key, agent.getSpriteSet().logo))
        agentMatrix = distributeObjects(agentLogos, 4)
        xSpacing = g.displayResolution[0] / (len(agentMatrix[0]) + 3)
        ySpacing = g.middle[1]*0.75 / (len(agentMatrix) + 1)
        for y, row in enumerate(agentMatrix):
            yPos = y - 0.5*len(agentMatrix)
            for x, agent in enumerate(row):
                xPos = x - 0.5*len(row)
                agentSelectMenu.append(g.RenderButton(imageName=agent[1], clickAction=self.__agentSelectButton, arguments=(agent[0],), x=g.middle[0]+xPos*xSpacing, y=g.middle[1]+yPos*ySpacing, width=64, height=64, enabled=False, middle=True))
        self.__agentSelectTimer = g.RenderText(text="Loading", x=g.middle[0], y=g.middle[1]*0.5, size = 45, color=(255, 255, 255), middle=True, enabled=False) ###
        agentSelectMenu.append(self.__agentSelectTimer)
        self.__menuUpdaters[K.AGENT_SELECT] = lambda time: self.__agentSelectTimer.updateText(f"{time:.0f}s") if f"{time:.0f}s" != self.__agentSelectTimer.text else None
        
        # HostAgentSelect
        hostAgentSelect: list[g.RenderObject] = []
        self.__menus[K.HOST_AGENT_SELECT] = hostAgentSelect
        agentLogos: list[tuple[AgentKey, str]] = []
        for key, agent in agents.items():
            agentLogos.append((key, agent.getSpriteSet().logo))
        agentMatrix = distributeObjects(agentLogos, 4)
        xSpacing = g.displayResolution[0] / (len(agentMatrix[0]) + 3)
        ySpacing = g.middle[1]*0.75 / (len(agentMatrix) + 1)
        for y, row in enumerate(agentMatrix):
            yPos = y - 0.5*len(agentMatrix)
            for x, agent in enumerate(row):
                xPos = x - 0.5*len(row)
                hostAgentSelect.append(g.RenderImage(imageName=agent[1], x=g.middle[0]+xPos*xSpacing, y=g.middle[1]+yPos*ySpacing, width=64, height=64, enabled=False, middle=True))
        hostAgentSelect.append(g.RenderButton(imageName="start", clickAction=self.__forceStartButton, x=g.middle[0], y=g.middle[1]*1.75, width=256, height=64, enabled=False, middle=True))
        hostAgentSelect.append(self.__agentSelectTimer)
        self.__menuUpdaters[K.HOST_AGENT_SELECT] = lambda time: self.__agentSelectTimer.updateText(f"{time:.0f}s") if f"{time:.0f}s" != self.__agentSelectTimer.text else None
        
        #inGamePlayer
        inGamePlayer: list[g.RenderObject] = []
        self.__menus[K.IN_GAME_PLAYER] = inGamePlayer
        
        #inGameHost
        inGameHost: list[g.RenderObject] = []
        self.__menus[K.IN_GAME_HOST] = inGameHost
        
    def __startButton(self) -> None:
        self.__addMessage(MessageHead.START, None)
    def __practiceButton(self) -> None:
        self.__addMessage("Practice", None)
    def __leaveButton(self) -> None:
        self.__addMessage(MessageHead.LEAVE, None)
    def __joinButton(self) -> None:
        self.__addMessage(MessageHead.JOIN, (CONFIG["ip"], CONFIG["port"]))
    def __hostButton(self) -> None:
        self.__addMessage(MessageHead.HOST, None)
    def __agentSelectButton(self, agentKey: AgentKey) -> None:
        self.__addMessage(MessageHead.SELECT_AGENT, agentKey)
    def __forceStartButton(self) -> None:
        self.__addMessage(MessageHead.FORCE_START, None)
        
    # Setters
    def setMenu(self, menu: MenuKey) -> None:
        if menu == self.__menu:
            return
        if menu not in self.__menus.keys():
            raise KeyError(f"{menu} is not a valid menu name")
        for obj in self.__menus[self.__menu]:
            obj.enabled = False
        for obj in self.__menus[menu]:
            obj.enabled = True
        self.__menu = menu
        
    def disable(self) -> None:
        self.__enabled = False
    def enable(self) -> None:
        self.__enabled = True
    
    # Getters
    def getMenu(self) -> MenuKey:
        return self.__menu
    def getMessages(self) -> list[Message]:
        messages = self.__messageQueue
        self.__messageQueue = self.__messageQueue[len(messages):]
        return messages
    
    def isEnabled(self) -> bool:
        return self.__enabled