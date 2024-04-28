from engine.level import Level
from engine.player import Player


class GameContext:
    def __init__(self, initial_level: Level) -> None:
        self.level = initial_level
        self.player = Player()
