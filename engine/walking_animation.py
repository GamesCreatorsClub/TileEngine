from typing import Optional

import enum

from engine.tmx import TiledObject


class Orientation(enum.Enum):
    LEFT = enum.auto()
    RIGHT = enum.auto()
    UP = enum.auto()
    DOWN = enum.auto()


class WalkingAnimation:
    def __init__(self, obj: Optional[TiledObject] = None) -> None:
        self.obj = obj
        self.orientation = Orientation.LEFT
        self.left_animation: list[int] = []
        self.right_animation: list[int] = []
        self.up_animation: list[int] = []
        self.down_animation: list[int] = []
        self.animations = {Orientation.LEFT: self.left_animation, Orientation.RIGHT: self.right_animation, Orientation.UP: self.up_animation, Orientation.DOWN: self.down_animation}

        self.animation_speed = 3
        self.animation_tick = 0

    def animate_walk(self) -> None:
        self.animation_tick += 1
        stage = self.animation_tick // self.animation_speed
        animation_list = self.animations[self.orientation]

        if stage >= len(animation_list):
            self.animation_tick = 0
            stage = 0

        self.obj.tile = animation_list[stage]

    def stop_walk(self) -> None:
        self.animation_tick = 0
        animation_list = self.animations[self.orientation]
        self.obj.tile = animation_list[0]

    def turn_left(self) -> None:
        if self.orientation != Orientation.LEFT:
            self.orientation = Orientation.LEFT
            self.obj.tile = self.left_animation[0]
            self.animation_tick = 0

    def turn_right(self) -> None:
        if self.orientation != Orientation.RIGHT:
            self.orientation = Orientation.RIGHT
            self.obj.tile = self.right_animation[0]
            self.animation_tick = 0

    def turn_up(self) -> None:
        if self.orientation != Orientation.UP:
            self.orientation = Orientation.UP
            self.obj.tile = self.up_animation[0]
            self.animation_tick = 0

    def turn_down(self) -> None:
        if self.orientation != Orientation.DOWN:
            self.orientation = Orientation.DOWN
            self.obj.tile = self.down_animation[0]
            self.animation_tick = 0
