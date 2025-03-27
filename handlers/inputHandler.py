from classes.types import Input
class InputHandler:
    def __init__(self):
        self.__inputQueue: list[Input] = []
    
    # Global
    # Local
    # Setters
    # Getters
    def getInputs(self) -> list[Input]:
        inputs = self.__inputQueue
        self.__inputQueue = self.__inputQueue[len(inputs):]
        return inputs