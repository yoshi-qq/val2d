import os
from typing import Literal, Optional
from time import time as now

class Console:
    def __init__(self) -> None:
        self.messages: dict[str, tuple[str, int, float]] = {}
        self.__lastDisplayed: float = 0
    # def log(self, msg: str, subMessage: str = "", obj: object = "") -> None:
    #     self.messages[msg+subMessage] = (obj, self.messages.get(msg, ("", 0, 0))[1]+1, now())
    #     self.display()
    
    def log(self, _case: Literal[0, 1, 2], symbol: str, problem: str, reason: str = "", detailsSymbol: str = "", details: str = "", obj: Optional[object] = None) -> None:
        key = f"{problem}{reason}"
        match _case:
            case 0:
                self.messages[key] = (f"{symbol} |{problem} <- {reason} -  | {detailsSymbol}|{details}", self.messages.get(key, ("", 0, 0))[1]+1, now())
            case 1:
                self.messages[key] = (f"{symbol} |{problem} <- {reason}", self.messages.get(key, ("", 0, 0))[1]+1, now())
            case 2:
                self.messages[key] = (f"{symbol} |{problem}", self.messages.get(key, ("", 0, 0))[1]+1, now())
        self.display()

    def display(self) -> None:
        if now() - self.__lastDisplayed < 0.5:
            return
        self.__lastDisplayed = now()
        os.system('cls' if os.name == 'nt' else 'clear')
        for msg, data in sorted(self.messages.items(), key=lambda x: x[1][2]):
            if data[1] > 1:
                print(f"{data[0]} (x{data[1]})")
            else:
                print(msg)