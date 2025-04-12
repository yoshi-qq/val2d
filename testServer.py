import os
from config.constants import TESTING_WINDOW_POSITIONS

# Positioning
ID = int(os.getenv("ID", "1"))
x, y = TESTING_WINDOW_POSITIONS[ID]
os.environ['SDL_VIDEO_WINDOW_POS'] = f"{x},{y}"

from main import main
from classes.types import Message, Message, AutoMessageTrigger
M = Message
A = Message
AMA = AutoMessageTrigger
qAMA = lambda m, a: AutoMessageTrigger(M(m, None), A(a, None))

# Automation
serverAutoMessageTriggers: list[AutoMessageTrigger] = [
    qAMA("Initiated", "Host"),
    qAMA("ClientConnected", "Start")
]

# Main Function
def run() -> None:
    main(serverAutoMessageTriggers)

if __name__ == "__main__":
    run()