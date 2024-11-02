import time
from typing import Optional

import pygame
from pygame import Color, Surface, Rect
from pygame.font import Font

from engine.utils import Size, Position


class SayThing:
    def __init__(self, text: str, colour: Color = pygame.Color("white"), expires_in: float = 0) -> None:
        self.text = text
        self.colour = colour
        self.expires_at = time.time() + expires_in
        self.surface: Optional[Surface] = None

    def invalidate(self) -> None:
        self.surface = None

    def is_expired(self) -> bool:
        return False if self.expires_at == 0 else time.time() >= self.expires_at


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
                say_thing.surface = Surface((place.width, self.line_height), pygame.SRCALPHA, 32).convert_alpha()
                say_thing.surface.fill((0, 0, 0, 0))
                black_text = self.font.render(say_thing.text, True, self.outline_color).convert_alpha()
                colour_text = self.font.render(say_thing.text, True, say_thing.colour).convert_alpha()
                say_thing.surface.blit(black_text, (0, 0))
                say_thing.surface.blit(black_text, (2, 0))
                say_thing.surface.blit(black_text, (2, 2))
                say_thing.surface.blit(black_text, (0, 2))
                say_thing.surface.blit(black_text, (3, 3))
                say_thing.surface.blit(black_text, (2, 3))
                say_thing.surface.blit(colour_text, (1, 1))
            screen.blit(say_thing.surface, (10, y))
            y += self.line_height

    def _trim(self) -> None:
        while len(self.say_things) > self.number_of_lines:
            del self.say_things[0]

    def say(self, text: str, colour: Optional[Color] = None, expires_in: float = 0.0) -> None:
        self.say_things.append(SayThing(text, colour=self.font_colour if colour is None else colour, expires_in=expires_in))
        self._trim()

    def say_once(self, text: str, colour: Optional[Color] = None, expires_in: float = 0.0) -> None:
        colour = self.font_colour if colour is None else colour
        if len(self.say_things) == 0 or self.say_things[-1].text != text:
            self.say_things.append(SayThing(text, colour=colour, expires_in=expires_in))
        elif self.say_things[-1].colour != colour:
            self.say_things[-1].colour = colour
            self.say_things[-1].invalidate()
        self._trim()
