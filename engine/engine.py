from typing import Union, Optional, Callable

import pygame
from pygame import Surface
from pygame.key import ScancodeWrapper

from engine.level import Level
from engine.player import Player


class Engine:
    def __init__(self) -> None:
        self.visible_levels = []
        self.player: Optional[Player] = None
        self.level: Optional[Level] = None
        self.xo = 0
        self.yo = 0
        self.move_player: Optional[Callable[[Union[int, float], Union[int, float]], bool]] = None

    @property
    def current_level(self) -> Level: return self.level

    @current_level.setter
    def current_level(self, level: Level) -> None:
        self.level = level
        if self.level not in self.visible_levels:
            self.visible_levels.append(self.level)

    def show_level(self, level: Level) -> None:
        if level not in self.visible_levels:
            self.visible_levels.append(level)

    def draw(self, surface: Surface) -> None:
        for level in self.visible_levels:
            if level == self.current_level:
                level.draw(surface)
            else:
                level.draw(surface)  # TOOD add calculation of level's xo/yo offset. Do the same above

    def process_keys(self, _previous_keys: ScancodeWrapper, current_keys: ScancodeWrapper) -> None:
        player = self.player
        player_moved = False
        if current_keys[pygame.K_LEFT] and current_keys[pygame.K_RIGHT]:
            player.vx = 0
        elif current_keys[pygame.K_LEFT]:
            self.player.turn_left()
            player.vx = -player.player_speed
            # player_moved = self.move_player(-player.player_speed, 0)
        elif current_keys[pygame.K_RIGHT]:
            self.player.turn_right()
            player.vx = player.player_speed
        else:
            player.vx = 0

        if player.vx != 0:
            player_moved = self.move_player(player.vx, 0)

        if current_keys[pygame.K_UP] and current_keys[pygame.K_DOWN]:
            player.jump = 0
        elif current_keys[pygame.K_UP]:
            if (player.jump == 0 and player.on_the_ground) or 0 < player.jump <= player.jump_treshold:
                player.jump += 1
                player.vy += -5 + 4 * player.jump / player.jump_treshold
        elif current_keys[pygame.K_DOWN]:
            player.jump = 0
        else:
            player.jump = 0

        player.vy = player.vy + 2  # 2 is gravity

        can_move_vertically = self.move_player(0, player.vy)
        if can_move_vertically and player.vy < 0:
            player.on_the_ground = False
        elif player.vy > 0:
            player.on_the_ground = not can_move_vertically
            if not can_move_vertically:
                player.hit_velocity = player.vy
                player.vy = 0
        player_moved = player_moved or (player.vy > 0.1) or (player.vy < -0.1)

        if player_moved:
            self.player.animate_walk()
            self.level.update_map_position(self.player.rect)
        else:
            self.player.stop_walk()
