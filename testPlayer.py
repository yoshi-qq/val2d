import os
from typing import Callable
from dependencies.communications import Event, Request
from config.constants import TESTING_WINDOW_POSITIONS, DEFAULT_IP, DEFAULT_PORT

# Positioning
ID = int(os.getenv("ID", "1"))
x, y = TESTING_WINDOW_POSITIONS[ID]
os.environ['SDL_VIDEO_WINDOW_POS'] = f"{x},{y}"

from main import main
from classes.types import Message, AutoMessageTrigger, AgentKey
M = Message
E = Event
R = Request
AMA = AutoMessageTrigger
qAMA: Callable[[str, str], AutoMessageTrigger] = lambda m, a: AutoMessageTrigger(M(m, None), M(a, None))

# Automation
playerAutoMessageTriggersLists: list[list[AutoMessageTrigger]] = [
    [
        AMA(M("Initiated", None), M("Join", (DEFAULT_IP, DEFAULT_PORT))),
        AMA(E("StartAgentSelectionEvent", None), M("SelectAgent", AgentKey.OMEN))
    ]
]

# Main Function
def run() -> None:
    main(playerAutoMessageTriggersLists[ID - 1])

if __name__ == "__main__":
    run()