from pygame.font import Font
from typing import Optional, Union, Callable

from pygame import Rect, Surface, Color

from engine.game_context import GameContext
from engine.level import Level
from engine.player import Player
from engine.utils import Size, Position
from engine.tmx import TiledObject
from game.overlays.text_overlay import TextArea, Text, TextOverlay, LayoutPosition, Placement

PlayerOrObject = Union[Player, TiledObject]


def in_context(target: Union[Callable, property]) -> Callable:
    if isinstance(target, property):
        target.fget.context_object = True
    else:
        target.context_object = True
    return target


class TextGameContext(GameContext):
    def __init__(self,
                 levels: dict[Union[str, int], Level],
                 font: Optional[Font] = None,
                 small_font: Optional[Font] = None,
                 **kwargs) -> None:
        super().__init__(levels, **kwargs)
        self.font = font
        self.small_font = small_font
        self.font_height = font.get_linesize()
        self.texts: list[Text] = []

        self.text_area = TextArea(font) if font is not None else None
        self.text_overlay = TextOverlay(font) if font is not None else None

    def _set_screen_size(self, size: Size) -> None:
        super()._set_screen_size(size)
        if self.text_area is not None:
            self.text_area.position = Position(20, size.height - self.text_area.size.height - 10)
            self.text_area.size = Size(size.width - 40, self.text_area.size.height)
        if self.text_overlay is not None:
            self.text_overlay.set_size(size)

    def draw_before_map(self, screen: Surface) -> None:
        pass

    def draw_after_map(self, screen: Surface) -> None:
        if self.text_area is not None:
            self.text_area.draw(screen)
        if self.text_overlay is not None:
            self.text_overlay.draw(screen)

    @in_context
    def say(self, text: str, colour: Optional[Color] = None, expires_in: float = 0.0) -> None:
        self.text_area.say(text, colour, expires_in)

    @in_context
    def say_once(self, text: str, colour: Optional[Color] = None, expires_in: float = 0.0) -> None:
        self.text_area.say_once(text, colour, expires_in)

    @in_context
    def overlay_image(self, surface: Surface, placement: Union[str, LayoutPosition], expires_in: int = 0, order: int = 0) -> Optional[Text]:
        if isinstance(placement, str):
            placement = LayoutPosition.from_str(placement)
        if self.text_overlay is not None:
            t = Text(surface, expires_in=expires_in, order=order)
            self.text_overlay.add_text(placement, t)
            return t
        return None

    @in_context
    def text(self, text: str, placement: Union[str, LayoutPosition], expires_in: int = 0, order: int = 0) -> Optional[Text]:
        if isinstance(placement, str):
            placement = LayoutPosition.from_str(placement)
        if self.text_overlay is not None:
            t = Text.normal(text, self.font, expires_in=expires_in, order=order)
            self.text_overlay.add_text(placement, t)
            return t
        return None

    @in_context
    def text_outline(self, text: str, placement: Union[str, LayoutPosition],
                     expires_in: int = 0, order: int = 0,
                     outline_size: int = 2,
                     colour: Color = Color("white"), outline_colour: Color = Color("black"),
                     horizontal_placement: Placement = Placement.NONE,
                     vertical_placement: Placement = Placement.NONE,
                     ) -> Optional[Text]:
        if isinstance(placement, str):
            placement = LayoutPosition.from_str(placement)
        if self.text_overlay is not None:
            t = Text.outline(text, self.font, expires_in=expires_in, order=order, colour=colour, outline_colour=outline_colour, outline_size=outline_size, horizontal_placement=horizontal_placement, vertical_placement=vertical_placement)
            self.text_overlay.add_text(placement, t)
            return t
        return None
