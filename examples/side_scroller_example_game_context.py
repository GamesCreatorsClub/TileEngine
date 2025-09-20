from pygame import Surface
from pygame.font import Font
from typing import Union

from pygame.key import ScancodeWrapper

from engine.level import Level
from game.side_scroller_game_context import SideScrollerGameContext


class SideScrollerExampleGameContext(SideScrollerGameContext):
    def __init__(self, levels: dict[Union[str, int], Level]) -> None:
        super().__init__(levels)

    def process_keys(self, previous_keys: ScancodeWrapper, current_keys: ScancodeWrapper) -> None:
        super().process_keys(previous_keys, current_keys)

    def before_map(self, screen: Surface) -> None:
        pass

    def after_map(self, screen: Surface) -> None:
        pass

    # @property
    # def screen_size(self) -> Optional[Size]:

    # Properties available 'in context':
    # tiles_by_name: Mapping[str, int]
    # object_by_name(self): Mapping[str, TiledObject]

    # Methods available 'in context'
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

