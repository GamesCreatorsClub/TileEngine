from engine.level import Level


class GameContext:
    def __init__(self, initial_level: Level) -> None:
        self.level = initial_level

