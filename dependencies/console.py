import os
from time import time as now

class Console:
    def __init__(self) -> None:
        self.messages: dict[str, tuple[str, int, float]] = {}
        self.__lastDisplayed: float = -1
    def log(self, msg: str, subMessage: str = "") -> None:
        self.messages[msg] = (subMessage, self.messages.get(msg, ("", 0, 0))[1]+1, now())
        self.display()

    def display(self) -> None:
        if now() - self.__lastDisplayed < 0.5:
            return
        self.__lastDisplayed = now()
        os.system('cls' if os.name == 'nt' else 'clear')
        for msg, data in sorted(self.messages.items(), key=lambda x: x[1][2]):
            if data[1] > 1:
                print(f"{msg}{data[0]} (x{data[1]})")
            else:
                print(msg)
