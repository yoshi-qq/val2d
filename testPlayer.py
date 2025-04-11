import os
from config.constants import TESTING_WINDOW_POSITIONS

# Positioning
ID = int(os.getenv("ID", "1"))
x, y = TESTING_WINDOW_POSITIONS[ID]
os.environ['SDL_VIDEO_WINDOW_POS'] = f"{x},{y}"

from main import main
from classes.types import AutoMessage

# Automation
playerAutoMessagesLists: list[list[AutoMessage]] = [[]]

# Main Function
def run() -> None:
    main(playerAutoMessagesLists[ID - 1])

if __name__ == "__main__":
    run()