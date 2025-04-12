import os
from config.constants import TESTING_WINDOW_POSITIONS, DEFAULT_IP, DEFAULT_PORT

# Positioning
ID = int(os.getenv("ID", "1"))
x, y = TESTING_WINDOW_POSITIONS[ID]
os.environ['SDL_VIDEO_WINDOW_POS'] = f"{x},{y}"

from main import main
from classes.types import Message, Message, AutoMessageTrigger, AgentKey
M = Message
A = Message
AMA = AutoMessageTrigger
qAMA = lambda m, a: AutoMessageTrigger(M(m, None), A(a, None))

# Automation
playerAutoMessageTriggersLists: list[list[AutoMessageTrigger]] = [
    [
        AMA(M("Initiated", None), A("Join", (DEFAULT_IP, DEFAULT_PORT))),
        AMA(M("OpenAgentSelectMenu", None), A("SelectAgent", AgentKey.OMEN))
    ]
]

# Main Function
def run() -> None:
    main(playerAutoMessageTriggersLists[ID - 1])

if __name__ == "__main__":
    run()