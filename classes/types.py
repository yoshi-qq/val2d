from typing import Any
class GameState:
    def __init__(self):
        pass
    def __str__(self) -> str:
        return f"GameState[]"

class Input:
    def __init__(self, type: str):
        self.type = type
    def __str__(self) -> str:
        return f"Input[type={self.type}]"

class Action:
    def __init__(self, type: str, content: Any):
        self.type = type
        self.content = content
    def __str__(self) -> str:
        return f"Action[type={self.type}, content={self.content}]"

class Message:
    def __init__(self, head: str, body: Any):
        self.head = head
        self.body = body
    def __str__(self) -> str:
        return f"Message[head={self.head}, body={self.body}]"