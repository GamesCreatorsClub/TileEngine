from typing import Union, cast, Optional

import pygame

from engine.collision_result import CollisionResult
from engine.utils import int_tuple, NestedDict
from engine.tmx import TiledObject


class Player(TiledObject):
    def __init__(self) -> None:
        super().__init__(None)
        self.name = "player"

        self.coins = 0

        self.hit_velocity = 0
        self.jump = 0
        self.jump_threshold = 10
        self.speed = 2
        self.jump_strength = 5
        self.on_the_ground = True

        self.restricted_rect = pygame.Rect(0, 0, 0, 0)

        self.save_previous_positions = False
        self.previous_positions_length = 400
        self.previous_positions = []

        self.collision_result = CollisionResult()
        self._tiled_object: Optional[TiledObject] = None

    @property
    def tile(self) -> int:
        return self._tiled_object.tile

    @tile.setter
    def tile(self, gid: int) -> None:
        self._tiled_object.tile = gid

    @property
    def tiled_object(self) -> TiledObject:
        return self

    @tiled_object.setter
    def tiled_object(self, obj: TiledObject) -> None:
        self._tiled_object = obj
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

        if "jump_threshold" in obj: self.jump_threshold = float(obj["jump_threshold"])
        if "jump_strength" in obj: self.jump_strength = float(obj["jump_strength"])
        if "speed" in obj: self.speed = float(obj["speed"])

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
