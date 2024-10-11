from abc import ABC, abstractmethod
from typing import Optional

from pygame import Surface

from engine.level import Level


class LevelTransition(ABC):
    def __init__(self, level: Level) -> None:
        self.level = level
        self.remove = False

    @abstractmethod
    def draw(self, surface: Surface) -> Optional['LevelTransition']:
        pass
