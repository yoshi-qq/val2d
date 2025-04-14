import os
from typing import Callable
from dependencies.communications import Event, Request
from config.constants import TESTING_WINDOW_POSITIONS

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
serverAutoMessageTriggers: list[AutoMessageTrigger] = [
    qAMA("Initiated", "Host"),
    qAMA("ClientConnected", "Start"),
    AMA(R("SelectAgentRequest", AgentKey.OMEN), M("ForceStart", None))
]

# Main Function
def run() -> None:
    main(serverAutoMessageTriggers)

if __name__ == "__main__":
    run()