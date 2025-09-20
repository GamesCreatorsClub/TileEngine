from typing import Union

from pygame.font import Font

import pygame
from engine.level import Level
from engine.tmx import TiledObject
from game.rpg_game_context import RPGGameContext
from pygame import Surface, Rect

from engine.game_context import in_context

COLOUR_WHITE = pygame.Color("white")
COLOUR_BLACK = pygame.Color("black")
COLOUR_BROWN = pygame.Color("burlywood4")
COLOUR_BROWN_TRANSPARENT = pygame.Color(COLOUR_BROWN.r, COLOUR_BROWN.g, COLOUR_BROWN.b, 128)


def sgn(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    d = a - b
    return -1 if d < 0 else (1 if d > 0 else 0)


class TopDownExampleGameContext(RPGGameContext):
    def __init__(self, levels: dict[Union[str, int], Level], font: Font, small_font: Font) -> None:
        super().__init__(levels, font, small_font)

    def before_map(self, screen: Surface) -> None:
        pass

    def after_map(self, screen: Surface) -> None:
        self.text_area.draw(screen)
        box_size = self._inventory.image_size
        rect = Rect(screen.get_rect().right - box_size[0] - 2, 50, box_size[0], box_size[1] * 10)
        self._inventory.draw(screen, rect)

    # @property
    # def screen_size(self) -> Optional[Size]:

    # Properties available 'in context':
    # tiles_by_name: Mapping[str, int]
    # object_by_name(self): Mapping[str, TiledObject]
    # inventory: Inventory

    # Methods available 'in context'
    # def add_coins(self, coins: int) -> None:
    # def add_object_to_inventory(self, obj: TiledObject) -> None:
    # def give_object(self, obj_name: str) -> None:
    # def set_inventory_visibility(self, visible: bool) -> None:
    # def say(self, text: str, colour: Optional[Color] = None, expires_in: float = 0.0) -> None:
    # def say_once(self, text: str, colour: Optional[Color] = None, expires_in: float = 0.0) -> None:

    # def distance_from_player(self, obj: TiledObject) -> float:
    # def set_player_input_allowed(self, allowed) -> None:
    # def move_object(self, obj: PlayerOrObject, x: float, y: float, test_collisions: bool = False, absolute: bool = False) -> bool:
    # def prevent_moving(self) -> None:
    # def prevent_colliding(self) -> None:
    # def is_player(self, obj: PlayerOrObject) -> bool:
    # def remove_object(self, obj: TiledObject) -> None:
    # def remove_collided_object(self) -> None:
    # def show_next_level(self) -> None:
    # def show_previous_level(self) -> None:
    # def select_level(self, name: str, keep_others: bool = False) -> None:
    # def next_level(self, keep_others: bool = False) -> None:
    # def previous_level(self, keep_others: bool = False) -> None:
    # def teleport_to_object(self, who: PlayerOrObject, obj_name: str) -> None:
    # def push_object(self, this: TiledObject, obj: TiledObject, test_collisions: bool = True) -> None:
    # def record_position(self, obj: TiledObject) -> None:
    # def move_object_away(self, this: TiledObject, obj: TiledObject, at_distance: float, test_collisions: bool = False, above_everything: bool = True) -> None:
    # def move_object_towards(self, this: TiledObject, obj: TiledObject, speed: float, test_collisions: bool = False, above_everything: bool = True) -> None:

