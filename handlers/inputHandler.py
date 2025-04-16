from typing import Optional
from config.constants import debug, D
from classes.types import Input
from classes.keys import KeyInputKey
from prebuilts.keybinds import keybinds
from dependencies import graphy as g
class InputHandler:
    def __init__(self):
        self.__lastKeys: list[int] = []
        self.__inputQueue: list[Input] = []
    
    # Global
    # Local
    def toInput(self, keyNumber: int) -> Optional[Input]:
        try:
            inputKey = keybinds.get(KeyInputKey(keyNumber))
        except ValueError:
            debug(D.WARNING, "Unhandled Input", f"key: {keyNumber}")
            return None
        if inputKey is None:
            debug(D.WARNING, "Unhandled Input", f"key: {keyNumber}")
            return None
        held = keyNumber in self.__lastKeys
        return Input(type=inputKey, held=held)
    
    # Setters
    # Getters
    def getInputs(self) -> tuple[list[Input], tuple[int, int]]:
        mouseMovement = g.getMouseMovement()
        inputs: list[Input] = []
        heldKeys: list[int] = list(g.getHeldKeys())
        for key in heldKeys:
            if input := self.toInput(key):
                inputs.append(input)
        self.__lastKeys = heldKeys
        if inputs:
            debug(D.TRACE, [input for input in inputs if input.held])
            for input in inputs:
                if not input.held:
                    debug(D.DEBUG, [input for input in inputs if not input.held])
                    break
        return inputs, mouseMovement

    # Setters
    def addInput(self, input: Input) -> None:
        self.__inputQueue.append(input)