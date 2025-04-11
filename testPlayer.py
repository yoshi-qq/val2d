import os
from config.constants import TESTING_WINDOW_POSITIONS, DEFAULT_IP, DEFAULT_PORT

# Positioning
ID = int(os.getenv("ID", "1"))
x, y = TESTING_WINDOW_POSITIONS[ID]
os.environ['SDL_VIDEO_WINDOW_POS'] = f"{x},{y}"

from main import main
from classes.types import Message, Action, AutoMessageAction, AgentKey
M = Message
A = Action
AMA = AutoMessageAction
qAMA = lambda m, a: AutoMessageAction(M(m, None), A(a, None))

# Automation
playerAutoMessageActionsLists: list[list[AutoMessageAction]] = [
    [
        AMA(M("Initiated", None), A("Join", (DEFAULT_IP, DEFAULT_PORT))),
        AMA(M("OpenAgentSelectMenu", None), A("SelectAgent", AgentKey.OMEN))
    ]
]

# Main Function
def run() -> None:
    main(playerAutoMessageActionsLists[ID - 1])

if __name__ == "__main__":
    run()