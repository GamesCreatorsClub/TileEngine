import enum
from typing import Union, cast

import pygame

from engine.collision_result import CollisionResult
from engine.utils import int_tuple, NestedDict
from engine.tmx import TiledObject


class Orientation(enum.Enum):
    LEFT = enum.auto()
    RIGHT = enum.auto()
    UP = enum.auto()
    DOWN = enum.auto()


class Player(TiledObject):
    def __init__(self) -> None:
        super().__init__(None)
        self.properties = NestedDict()
        self.name = "player"

        self.coins = 0

        self.collision_result = CollisionResult()
        self.orientation = Orientation.LEFT
        self.left_animation: list[int] = []
        self.right_animation: list[int] = []
        self.up_animation: list[int] = []
        self.down_animation: list[int] = []
        self.animations = {Orientation.LEFT: self.left_animation, Orientation.RIGHT: self.right_animation, Orientation.UP: self.up_animation, Orientation.DOWN: self.down_animation}

        self.animation_speed = 3
        self.animation_tick = 0

        self.vx = 0
        self.vy = 0
        self.hit_velocity = 0
        self.jump_treshold = 10
        self.jump = 0
        self.player_speed = 2
        self.on_the_ground = True

        self.restricted_rect = pygame.Rect(0, 0, 0, 0)

        self.save_previous_positions = False
        self.previous_positions_length = 400
        self.previous_positions = []
        self.collisions = set()

    @property
    def tiled_object(self) -> TiledObject:
        return self

    @tiled_object.setter
    def tiled_object(self, obj: TiledObject) -> None:
        self.rect = obj.rect
        cast(NestedDict, self.properties).over = obj.properties
        self.next_rect.update(obj.next_rect)
        self.collisions.clear()
        self.collisions.update(obj.collisions)
        self.collision_result.clear()
        self.map = obj.map
        for key in self.properties:
            if hasattr(self, key):
                setattr(self, key, self.properties[key])

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
        animation_list = self.animations[self.orientation]

        if stage >= len(animation_list):
            self.animation_tick = 0
            stage = 0

        self.tile = animation_list[stage]

    def stop_walk(self) -> None:
        self.animation_tick = 0
        animation_list = self.animations[self.orientation]
        self.tile = animation_list[0]

    def turn_left(self) -> None:
        if self.orientation != Orientation.LEFT:
            self.orientation = Orientation.LEFT
            self.tile = self.left_animation[0]
            self.animation_tick = 0

    def turn_right(self) -> None:
        if self.orientation != Orientation.RIGHT:
            self.orientation = Orientation.RIGHT
            self.tile = self.right_animation[0]
            self.animation_tick = 0

    def turn_up(self) -> None:
        if self.orientation != Orientation.UP:
            self.orientation = Orientation.UP
            self.tile = self.up_animation[0]
            self.animation_tick = 0

    def turn_down(self) -> None:
        if self.orientation != Orientation.DOWN:
            self.orientation = Orientation.DOWN
            self.tile = self.down_animation[0]
            self.animation_tick = 0
