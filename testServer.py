import os
from config.constants import TESTING_WINDOW_POSITIONS

# Positioning
ID = int(os.getenv("ID", "1"))
x, y = TESTING_WINDOW_POSITIONS[ID]
os.environ['SDL_VIDEO_WINDOW_POS'] = f"{x},{y}"

from main import main
from classes.types import Message, Action, AutoMessageAction
M = Message
A = Action
AMA = AutoMessageAction
qAMA = lambda m, a: AutoMessageAction(M(m, None), A(a, None))

# Automation
serverAutoMessageActions: list[AutoMessageAction] = [
    qAMA("Initiated", "Host"),
    qAMA("ClientConnected", "Start")
]

# Main Function
def run() -> None:
    main(serverAutoMessageActions)

if __name__ == "__main__":
    run()