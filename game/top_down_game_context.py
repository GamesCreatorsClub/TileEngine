from typing import Union

import pygame
from pygame.key import ScancodeWrapper

from engine.game_context import GameContext
from engine.level import Level


class TopDownGameContext(GameContext):
    def __init__(self, levels: dict[Union[str, int], Level]) -> None:
        super().__init__(levels)

    def process_keys(self, _previous_keys: ScancodeWrapper, current_keys: ScancodeWrapper) -> None:
        if self.player_input_allowed:
            player = self.player
            walking_animation = player["__walking_animation"]
            player_moved_horizontally = False
            left = current_keys[pygame.K_LEFT] or current_keys[pygame.K_a]
            right = current_keys[pygame.K_RIGHT] or current_keys[pygame.K_d]
            if left and right:
                player.vx = 0
            elif left:
                walking_animation.turn_left()
                player.vx = -player.speed
            elif right:
                walking_animation.turn_right()
                player.vx = player.speed
            else:
                player.vx = 0

            if player.vx != 0:
                player_moved_horizontally = self.move_object(player, player.vx, 0, test_collisions=True)

            player_moved_vertically = False
            up = current_keys[pygame.K_UP] or current_keys[pygame.K_w]
            down = current_keys[pygame.K_DOWN] or current_keys[pygame.K_s]
            if up and down:
                player.vy = 0
            elif up:
                walking_animation.turn_up()
                player.vy = -player.speed
            elif down:
                walking_animation.turn_down()
                player.vy = player.speed
            else:
                player.vy = 0

            if player.vy != 0:
                player_moved_vertically = self.move_object(player, 0, player.vy, test_collisions=True)

            player_moved = player_moved_horizontally or player_moved_vertically

            if player_moved:
                walking_animation.animate_walk()
                self.level.update_map_position(self.player.rect.center)
                self.level.invalidated = True
            else:
                walking_animation.stop_walk()
