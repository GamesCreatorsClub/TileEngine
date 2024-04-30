import enum
from typing import Optional, Union

from pygame import Rect

from pytmx import TiledObject


class Orientation(enum.Enum):
    LEFT = enum.auto()
    RIGHT = enum.auto()


class Player:
    def __init__(self) -> None:
        self._next_pos = Rect(0, 0, 0, 0)
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

    @property
    def tiled_object(self) -> TiledObject:
        return self._object

    @tiled_object.setter
    def tiled_object(self, obj: TiledObject) -> None:
        self._object = obj
        self._next_pos.topleft = obj.rect.topleft
        self._next_pos.size = obj.rect.size

    @property
    def rect(self) -> Rect: return self._object.rect

    def move_to(self, pos: tuple[Union[int, float], Union[int, float]]) -> Rect:
        rect = self.rect
        rect.topleft = pos

        if self.save_previous_positions:
            if len(self.previous_positions) > self.previous_positions_length:
                del self.previous_positions[:-self.previous_positions_length]
            self.previous_positions.append(pos)
        return rect

    @property
    def next_rect(self) -> Rect:
        self._next_pos.topleft = self._object.rect.topleft
        return self._next_pos

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
