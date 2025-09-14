from pygame.font import Font
from typing import Union

from engine.level import Level
from game.side_scroller_game_context import SideScrollerGameContext


class SideScrollerExampleGameContext(SideScrollerGameContext):
    def __init__(self, levels: dict[Union[str, int], Level]) -> None:
        super().__init__(levels)
