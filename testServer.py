import os
from typing import Callable
from dependencies.communications import Event, Request
from config.constants import TESTING_WINDOW_POSITIONS

# Positioning
ID = int(os.getenv("ID", "1"))
x, y = TESTING_WINDOW_POSITIONS[ID]
os.environ['SDL_VIDEO_WINDOW_POS'] = f"{x},{y}"

from main import main
from classes.types import Null, Message, AutoMessageTrigger, AgentKey
M = Message
E = Event
R = Request
AMA = AutoMessageTrigger
qAMA: Callable[[str, str], AutoMessageTrigger] = lambda m, a: AutoMessageTrigger(M(m, Null), M(a, None))

# Automation
serverAutoMessageTriggers: list[AutoMessageTrigger] = [
    qAMA("Initiated", "Host"),
    AMA(M("ClientConnected", Null), M("Start", None), 2, 0),
    AMA(R("SelectAgentRequest", AgentKey.OMEN), M("ForceStart", None), 2, 0)
]

# Main Function
def run() -> None:
    main(serverAutoMessageTriggers)

if __name__ == "__main__":
    run()