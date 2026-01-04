from enum import Enum

import time
from typing import Optional, Union

import pygame
from pygame import Color, Surface, Rect
from pygame.font import Font

from engine.utils import Size, Position


class Placement(Enum):
    NONE = -1
    CENTRE = 0
    LEFT = -1
    TOP = -1
    RIGHT = 1
    BOTTOM = 1


class LayoutPosition(Enum):

    CENTRE = (0, False)
    N = (1, True)
    S = (2, True)
    W = (3, True)
    E = (4, True)
    NE = (5, False)
    SE = (6, False)
    NW = (7, False)
    SW = (8, False)
    NNW = (9, True)
    NNE = (10, True)
    SSW = (11, True)
    SSE = (12, True)
    WNW = (13, True)
    WSW = (14, True)
    ENE = (15, True)
    ESE = (16, True)

    def __init__(self, value: int, multi_values: bool) -> None:
        self._value_ = value
        self.multi_values = multi_values

    @classmethod
    def from_str(cls, s: str) -> 'LayoutPosition':
        return LayoutPosition[s]


class Text:
    def __init__(self,
                 text: Union[str, Surface],
                 colour: Optional[Color] = None,
                 expires_in: float = 0,
                 order: int = 0) -> None:

        self.text = text if isinstance(text, str) else ""
        self.colour = colour
        self.expires_at = (time.time() + expires_in) if expires_in > 0 else 0
        self.surface: Optional[Surface] = text if isinstance(text, Surface) else None
        self.order = order
        w, h = 0, 0
        if self.surface is not None:
            w, h = self.surface.get_size()
        self.rect = Rect(0, 0, w, h)

    def invalidate(self) -> None:
        self.surface = None

    def is_expired(self) -> bool:
        return False if self.expires_at == 0 else time.time() >= self.expires_at

    def draw(self,
             font: Font,
             width: int = 0,
             height: int = 0,
             colour: Color = pygame.Color("white"),
             horizontal_placement: Placement = Placement.NONE,
             vertical_placement: Placement = Placement.NONE) -> None:
        x = 0
        y = 0
        line_height = 0
        lines = self.text.split("\n")
        if lines[-1] == "": del lines[-1]

        if width == 0 or height == 0:
            t_width, line_height = font.size(self.text)
            t_height = line_height * len(lines)
            if width == 0:
                width = t_width
            else:
                if horizontal_placement == Placement.CENTRE:
                    x = (width - t_width) // 2
                elif horizontal_placement == Placement.RIGHT:
                    x = width - t_width

            if height == 0:
                height = t_height
            else:
                if vertical_placement == Placement.CENTRE:
                    y = (height - t_height) // 2
                elif vertical_placement == Placement.BOTTOM:
                    y = height - t_height
        elif len(lines) > 1:
            line_height = font.get_linesize()

        self.surface = Surface((width, height), pygame.SRCALPHA, 32).convert_alpha()
        self.surface.fill((0, 0, 0, 0))
        for line in lines:
            self.surface.blit(font.render(line, True, colour).convert_alpha(), (x, y))
            y += line_height
        self.rect.width, self.rect.height = self.surface.get_size()

    def draw_outline(self,
                          font: Font,
                          width: int = 0,
                          height: int = 0,
                          outline_size: int = 2,
                          colour: Color = pygame.Color("white"),
                          outline_colour: Color = Color("black"),
                          horizontal_placement: Placement = Placement.NONE,
                          vertical_placement: Placement = Placement.NONE) -> None:
        x = outline_size
        y = outline_size
        line_height = 0
        lines = self.text.split("\n")
        if lines[-1] == "": del lines[-1]

        if width == 0 or height == 0:
            t_width, line_height = font.size(self.text)
            t_height = line_height * len(lines)
            if width == 0:
                width = t_width + outline_size * 2
            else:
                if horizontal_placement == Placement.CENTRE:
                    x = (width - t_width) // 2 - outline_size
                elif horizontal_placement == Placement.RIGHT:
                    x = width - t_width

            if height == 0:
                height = t_height + outline_size * 2
            else:
                if vertical_placement == Placement.CENTRE:
                    y = (height - t_height) // 2 - outline_size
                elif vertical_placement == Placement.BOTTOM:
                    y = height - t_height

        self.surface = Surface((width, height), pygame.SRCALPHA, 32).convert_alpha()
        self.surface.fill((0, 0, 0, 0))
        self.rect.width, self.rect.height = self.surface.get_size()

        kx, ky = x, y

        for line in lines:
            black_text = font.render(line, True, outline_colour).convert_alpha()
            for i in range(1, outline_size + 1):
                self.surface.blit(black_text, (x - i, y - i))
                self.surface.blit(black_text, (x, y - i))
                self.surface.blit(black_text, (x + i, y - i))

                self.surface.blit(black_text, (x - i, y))
                self.surface.blit(black_text, (x + i, y))

                self.surface.blit(black_text, (x - i, y + i))
                self.surface.blit(black_text, (x, y + i))
                self.surface.blit(black_text, (x + i, y + i))
            y += line_height

        x, y = kx, ky
        for line in lines:
            self.surface.blit(font.render(line, True, colour).convert_alpha(), (x, y))
            y += line_height

    @classmethod
    def normal(cls, text: str, font: Font,
                width: int = 0, height: int = 0,
                colour: Color = Color("white"),
                horizontal_placement: Placement = Placement.NONE,
                vertical_placement: Placement = Placement.NONE,
                expires_in: int = 0, order: int = 0) -> 'Text':
        t = Text(text, expires_in=expires_in, order=order)
        t.draw(font, width=width, height=height, colour=colour, horizontal_placement=horizontal_placement, vertical_placement=vertical_placement)
        return t

    @classmethod
    def outline(cls, text: str, font: Font,
                width: int = 0, height: int = 0,
                outline_size: int = 2,
                colour: Color = Color("white"), outline_colour: Color = Color("black"),
                horizontal_placement: Placement = Placement.NONE,
                vertical_placement: Placement = Placement.NONE,
                expires_in: int = 0, order: int = 0) -> 'Text':
        t = Text(text, expires_in=expires_in, order=order)
        t.draw_outline(font, width=width, height=height, outline_size=outline_size, colour=colour, outline_colour=outline_colour, horizontal_placement=horizontal_placement, vertical_placement=vertical_placement)
        return t


class TextOverlay:
    def __init__(self,
                 font: Font) -> None:
        self.font = font
        self.size = Size(100, 100)
        self.texts: dict[LayoutPosition, list[Text]] = {}

    def set_size(self, size: Size) -> None:
        do_layout = self.size != size
        self.size = size
        if do_layout:
            self.layout()

    def add_text(self, layout_position: LayoutPosition, text: Text) -> None:
        if layout_position not in self.texts or not layout_position.multi_values:
            self.texts[layout_position] = [text]
        else:
            texts = self.texts[layout_position]
            texts.append(text)
            texts.sort(key=lambda t: t.order)

        self._layout_position(layout_position, self.texts[layout_position])

    def layout(self) -> None:
        for layout_position in list(self.texts):
            texts = self.texts[layout_position]
            for i in range(len(texts) - 1, -1, -1):
                if texts[i].is_expired():
                    del texts[i]

            if len(texts) == 0:
                del self.texts[layout_position]
            else:
                self._layout_position(layout_position, texts)

    def _layout_position(self, layout_position: LayoutPosition, texts: list[Text]) -> None:
        x = 0
        y = 0
        if layout_position.multi_values:
            max_width = 0
            max_height = 0
            total_width = 0
            total_height = 0
            for t in texts:
                if t.rect.width > max_width: max_width = t.rect.width
                if t.rect.height > max_height: max_height = t.rect.height
                total_width += t.rect.width
                total_height += t.rect.height

            if layout_position == LayoutPosition.N:
                x = (self.size.width - total_width) // 2
                for t in texts:
                    t.rect.x = x
                    t.rect.y = 0
                    x += t.rect.width
            elif layout_position == LayoutPosition.S:
                x = (self.size.width - total_width) // 2
                for t in texts:
                    t.rect.x = x
                    t.rect.y = self.size.height - t.rect.height
                    x += t.rect.width
            elif layout_position == LayoutPosition.W:
                y = (self.size.height - total_height) // 2
                for t in texts:
                    t.rect.x = 0
                    t.rect.y = y
                    y += t.rect.height
            elif layout_position == LayoutPosition.E:
                y = (self.size.height - total_height) // 2
                for t in texts:
                    t.rect.x = self.size.width - t.rect.width
                    t.rect.y = y
                    y += t.rect.height
            elif layout_position == LayoutPosition.NNW:
                x = self.texts[LayoutPosition.NW][0].rect.width if LayoutPosition.NW in self.texts else 0
                for t in texts:
                    t.rect.x = x
                    t.rect.y = 0
                    x += t.rect.width
            elif layout_position == LayoutPosition.NNE:
                x = self.size.width - (self.texts[LayoutPosition.NE][0].rect.width if LayoutPosition.NE in self.texts else 0) - max_width
                for t in texts:
                    t.rect.x = x
                    t.rect.y = 0
                    x += t.rect.width
            elif layout_position == LayoutPosition.SSW:
                x = self.texts[LayoutPosition.SW][0].rect.width if LayoutPosition.NW in self.texts else 0
                for t in texts:
                    t.rect.x = x
                    t.rect.y = self.size.height - t.rect.height
                    x += t.rect.width
            elif layout_position == LayoutPosition.SSE:
                x = self.size.width - (self.texts[LayoutPosition.SE][0].rect.width if LayoutPosition.SE in self.texts else 0) - max_width
                for t in texts:
                    t.rect.x = x
                    t.rect.y = self.size.height - t.rect.height
                    x += t.rect.width
            elif layout_position == LayoutPosition.WNW:
                y = self.texts[LayoutPosition.NW][0].rect.height if LayoutPosition.NW in self.texts else 0
                for t in texts:
                    t.rect.x = 0
                    t.rect.y = y
                    y += t.rect.height
            elif layout_position == LayoutPosition.WSW:
                y = self.size.height - (self.texts[LayoutPosition.SW][0].rect.height if LayoutPosition.SW in self.texts else 0) - max_height
                for t in texts:
                    t.rect.x = 0
                    t.rect.y = y
                    y += t.rect.height
            elif layout_position == LayoutPosition.ENE:
                y = self.texts[LayoutPosition.NE][0].rect.height if LayoutPosition.NE in self.texts else 0
                for t in texts:
                    t.rect.x = self.size.width - t.rect.width
                    t.rect.y = y
                    y += t.rect.height
            elif layout_position == LayoutPosition.ESE:
                y = self.size.height - (self.texts[LayoutPosition.SE][0].rect.height if LayoutPosition.SE in self.texts else 0) - max_height
                for t in texts:
                    t.rect.x = self.size.width - t.rect.width
                    t.rect.y = y
                    y += t.rect.height

        else:
            t = texts[0]
            x = 0
            y = 0
            if layout_position == LayoutPosition.CENTRE:
                x = (self.size.width - t.rect.width) // 2
                y = (self.size.height - t.rect.height) // 2
            elif layout_position == LayoutPosition.NW:
                pass
            elif layout_position == LayoutPosition.NE:
                x = self.size.width - t.rect.width
                y = 0
            elif layout_position == LayoutPosition.SW:
                x = 0
                y = self.size.height - t.rect.height
            elif layout_position == LayoutPosition.SE:
                x = self.size.width - t.rect.width
                y = self.size.height - t.rect.height

            t.rect.x, t.rect.y = x, y

    def draw(self, screen: Surface) -> None:
        for layout_position in list(self.texts):
            texts = self.texts[layout_position]
            for i in range(len(texts) - 1, -1, -1):
                if texts[i].is_expired():
                    del texts[i]

            if len(texts) == 0:
                del self.texts[layout_position]
            else:
                for t in texts:
                    screen.blit(t.surface, t.rect)


class TextArea:
    def __init__(self,
                 font: Font,
                 number_of_lines: int = 3,
                 line_spacing: int = 2,
                 font_colour: Color = pygame.Color("white"),
                 outline_color: Color = pygame.Color("black")) -> None:
        self.say_things = []
        self.line_spacing = line_spacing
        self.number_of_lines = number_of_lines
        self.font = font
        self.font_height = font.get_linesize()
        self.font_colour = font_colour
        self.outline_color = outline_color
        self._position = Position(-1, -1)
        self._size = Size(-1, self.number_of_lines * self.line_height)
        self._rect = Rect(-1, -1, -1, -1)

    @property
    def position(self) -> Position:
        return self._position

    @position.setter
    def position(self, position: Position) -> None:
        self._position = position
        self._rect.move_ip(position)

    @property
    def size(self) -> Size:
        return self._size

    @size.setter
    def size(self, size: Size) -> None:
        self._size = size
        self._rect.width = size.width
        self._rect.height = size.height

    @property
    def line_height(self) -> int:
        return self.font_height + self.line_spacing

    def draw(self, screen: Surface, place: Optional[Rect] = None) -> None:
        place = place if place is not None else self._rect
        y = place.y
        for say_thing in self.say_things:
            if say_thing.surface is None:
                say_thing.draw_outline(self.font, colour=self.font_colour if say_thing.colour is None else say_thing.colour, width=place.width, outline_size=2, outline_colour=self.outline_color)
            screen.blit(say_thing.surface, (10, y))
            y += self.line_height
        for i in range(len(self.say_things) - 1, -1, -1):
            if self.say_things[i].is_expired():
                del self.say_things[i]

    def _trim(self) -> None:
        while len(self.say_things) > self.number_of_lines:
            del self.say_things[0]

    def say(self, text: str, colour: Optional[Color] = None, expires_in: float = 0.0) -> None:
        colour = self.font_colour if colour is None else colour
        self.say_things.append(Text(text, expires_in=expires_in, colour=colour))
        self._trim()

    def say_once(self, text: str, colour: Optional[Color] = None, expires_in: float = 0.0) -> None:
        colour = self.font_colour if colour is None else colour
        if len(self.say_things) == 0 or self.say_things[-1].text != text:
            self.say_things.append(Text(text, expires_in=expires_in, colour=colour))
        elif self.say_things[-1].colour != colour:
            self.say_things[-1].colour = colour
            self.say_things[-1].invalidate()
        self._trim()
