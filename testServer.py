import os
from typing import Callable
from dependencies.communications import Event, Request
from config.constants import TESTING_WINDOW_POSITIONS
from classes.heads import MessageHead, RequestHead

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
qAMA: Callable[[MessageHead, MessageHead], AutoMessageTrigger] = lambda m, a: AutoMessageTrigger(M(m, Null), M(a, None))

# Automation
serverAutoMessageTriggers: list[AutoMessageTrigger] = [
    qAMA(MessageHead.INITIATED, MessageHead.HOST),
    AMA(M(MessageHead.CLIENT_CONNECTED, Null), M(MessageHead.START, None), 2, 0),
    AMA(R(RequestHead.SELECT_AGENT, AgentKey.OMEN), M(MessageHead.FORCE_START, None), 2, 0)
]

# Main Function
def run() -> None:
    main(serverAutoMessageTriggers)

if __name__ == "__main__":
    run()