from classes.types import Input
from classes.keys import KeyInputKey, InputKey
from dependencies import graphy as g
class InputHandler:
    def __init__(self):
        self.__lastKeys: list[int] = []
    
    # Global
    # Local
    def toInput(self, keyNumber: int) -> Input:
        inputKey = InputKey(keyNumber)
        held = keyNumber in self.__lastKeys
        return Input(type=inputKey, held=held)
    
    # Setters
    # Getters
    def getInputs(self) -> list[Input]:
        inputs: list[Input] = []
        heldKeys: list[int] = g.getHeldKeys()
        for key in heldKeys:
            inputs.append(self.toInput(key))
        self.__lastKeys = heldKeys
        return inputs

    # Setters
    def addInput(self, input: Input) -> None:
        self.__inputQueue.append(input)