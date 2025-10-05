from typing import Union

import pygame
from pygame.key import ScancodeWrapper

from engine.game_context import GameContext
from engine.level import Level


class SideScrollerGameContext(GameContext):
    def __init__(self, levels: dict[Union[str, int], Level]) -> None:
        super().__init__(levels)

    def process_keys(self, _previous_keys: ScancodeWrapper, current_keys: ScancodeWrapper) -> None:
        player = self.player
        player_moved_horizotanlly = False
        if current_keys[pygame.K_LEFT] and current_keys[pygame.K_RIGHT]:
            player.vx = 0
        elif current_keys[pygame.K_LEFT]:
            self.player.turn_left()
            player.vx = -player.speed
            # player_moved = self.move_player(-player.speed, 0)
        elif current_keys[pygame.K_RIGHT]:
            self.player.turn_right()
            player.vx = player.speed
        else:
            player.vx = 0

        if player.vx != 0:
            player_moved_horizotanlly = self.move_object(player, player.vx, 0, test_collisions=True)

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

        player_moved_vertically = self.move_object(player, 0, player.vy, test_collisions=True)
        if player_moved_vertically:
            if player.vy < 0:
                player.on_the_ground = False
        elif player.vy > 0:
            player.on_the_ground = not player_moved_vertically
            if not player_moved_vertically:
                player.hit_velocity = player.vy
                player.vy = 0
        player_moved = player_moved_horizotanlly or player_moved_vertically

        if player_moved:
            self.player.animate_walk()
            self.level.update_map_position(self.player.rect.center)
            self.level.invalidated = True
        else:
            self.player.stop_walk()
