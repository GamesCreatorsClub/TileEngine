import enum
from typing import Optional, Union

from pygame import Rect

from engine.collision_result import CollisionResult
from engine.utils import int_tuple
from engine.pytmx import TiledObject


class Orientation(enum.Enum):
    LEFT = enum.auto()
    RIGHT = enum.auto()


class Player:
    def __init__(self) -> None:
        self.coins = 0

        self.next_rect = Rect(0, 0, 0, 0)
        self.collision_result = CollisionResult()
        self.orientation = Orientation.LEFT
        self._object: Optional[TiledObject] = None
        self.left_animation: list[int] = []
        self.right_animation: list[int] = []
        self.animation_speed = 3
        self.animation_tick = 0

        self.vx = 0
        self.vy = 0
        self.hit_velocity = 0
        self.jump_treshold = 10
        self.jump = 0
        self.player_speed = 2
        self.on_the_ground = True

        self.save_previous_positions = False
        self.previous_positions_length = 400
        self.previous_positions = []
        self.collisions = set()
        self.properties = {}

    @property
    def tiled_object(self) -> TiledObject:
        return self._object

    @tiled_object.setter
    def tiled_object(self, obj: TiledObject) -> None:
        self._object = obj
        self.next_rect.update(obj.rect)

    @property
    def rect(self) -> Rect: return self._object.rect

    def move_to(self, pos: tuple[Union[int, float], Union[int, float]]) -> bool:
        rect = self.rect
        old_pos = int_tuple(rect.topleft)
        new_pos = int_tuple(pos)
        rect.topleft = pos

        if self.save_previous_positions:
            if len(self.previous_positions) > self.previous_positions_length:
                del self.previous_positions[:-self.previous_positions_length]
            if old_pos != new_pos:
                self.previous_positions.append(new_pos)
                return True
        elif old_pos != new_pos:
            return True
        return False

    def animate_walk(self) -> None:
        self.animation_tick += 1
        stage = self.animation_tick // self.animation_speed
        if stage > 1:
            self.animation_tick = 0
            stage = 0
        animation_list = self.left_animation if self.orientation == Orientation.LEFT else self.right_animation
        self._object.gid = animation_list[stage]

    def stop_walk(self) -> None:
        self.animation_tick = 0
        animation_list = self.left_animation if self.orientation == Orientation.LEFT else self.right_animation
        self._object.gid = animation_list[0]

    def turn_left(self) -> None:
        if self.orientation != Orientation.LEFT:
            self.orientation = Orientation.LEFT
            self._object.gid = self.left_animation[0]
            self.animation_tick = 0

    def turn_right(self) -> None:
        if self.orientation != Orientation.RIGHT:
            self.orientation = Orientation.RIGHT
            self._object.gid = self.right_animation[0]
            self.animation_tick = 0
