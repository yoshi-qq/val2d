from handlers.graphicsHandler import g
from classes.types import Input, Action, AgentKey, agents
from handlers.config import CONFIG
from dependencies.helpers import distributeObjects

class MenuHandler:
    def __init__(self) -> None:
        self.__enabled: bool = True
        self.__menu: str = "empty"
        self.__actionQueue: list[Action] = []
        self.__menus: dict[str, list[g.RenderObject]] = {}
        self.__setupMenus()
    # Global
    def handleInput(self, input: Input) -> None:
        pass
    
    # Local
    def __setupMenus(self) -> None:
        # Empty
        self.__menus["empty"] = []
        
        # Play
        playMenu: list[g.RenderObject] = []
        self.__menus["play"] = playMenu
        playMenu.append(g.RenderButton(imageName="practice", clickAction=self.__practiceButton, x=g.middle[0]-300, y=g.middle[1]*1.75, width=256, height=32, enabled=False, middle=True))
        playMenu.append(g.RenderButton(imageName="join", clickAction=self.__joinButton, x=g.middle[0]+150, y=g.middle[1]*0.5, width=256, height=32, enabled=False, middle=True))
        playMenu.append(g.RenderButton(imageName="host", clickAction=self.__hostButton, x=g.middle[0]-150, y=g.middle[1]*0.5, width=256, height=32, enabled=False, middle=True))
        
        # HostLobby
        hostLobbyMenu: list[g.RenderObject] = []
        self.__menus["hostLobby"] = hostLobbyMenu
        hostLobbyMenu.append(g.RenderButton(imageName="start", clickAction=self.__startButton, x=g.middle[0], y=g.middle[1]*1.75, width=256, height=64, enabled=False, middle=True))
        hostLobbyMenu.append(g.RenderButton(imageName="practice", clickAction=self.__practiceButton, x=g.middle[0]-300, y=g.middle[1]*1.75, width=256, height=32, enabled=False, middle=True))
        hostLobbyMenu.append(g.RenderButton(imageName="leave", clickAction=self.__leaveButton, x=g.middle[0]+300, y=g.middle[1]*1.75, width=256, height=32, enabled=False, middle=True))
        
        # PlayerLobby
        playerLobbyMenu: list[g.RenderObject] = []
        self.__menus["playerLobby"] = playerLobbyMenu
        playerLobbyMenu.append(g.RenderButton(imageName="practice", clickAction=self.__practiceButton, x=g.middle[0]-300, y=g.middle[1]*1.75, width=256, height=32, enabled=False, middle=True))
        playerLobbyMenu.append(g.RenderButton(imageName="leave", clickAction=self.__leaveButton, x=g.middle[0]+300, y=g.middle[1]*1.75, width=256, height=32, enabled=False, middle=True))

        # AgentSelect
        agentSelectMenu: list[g.RenderObject] = []
        self.__menus["agentSelect"] = agentSelectMenu
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
            
        
    def __startButton(self) -> None:
        self.__actionQueue.append(Action("Start", None))
    def __practiceButton(self) -> None:
        self.__actionQueue.append(Action("Practice", None))
    def __leaveButton(self) -> None:
        self.__actionQueue.append(Action("Leave", None))
    def __joinButton(self) -> None:
        self.__actionQueue.append(Action("Join", (CONFIG["ip"], CONFIG["port"])))
    def __hostButton(self) -> None:
        self.__actionQueue.append(Action("Host", None))
    def __agentSelectButton(self, agentKey: AgentKey) -> None:
        self.__actionQueue.append(Action("SelectAgent", agentKey))
    # Setters
    def setMenu(self, menu: str) -> None:
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
    def getMenu(self) -> str:
        return self.__menu
    def getActions(self) -> list:
        actions = self.__actionQueue
        self.__actionQueue = self.__actionQueue[len(actions):]
        return actions
    def isEnabled(self) -> bool:
        return self.__enabled
    
    # Setters
    def addAction(self, action: Action) -> None:
        self.__actionQueue.append(action)