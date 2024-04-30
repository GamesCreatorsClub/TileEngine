from typing import Union

import pygame
from pygame import Surface, Rect
from pygame.key import ScancodeWrapper

from engine.game_context import GameContext
from game.utils import is_close


class Engine:
    def __init__(self, game_context: GameContext) -> None:
        self.game_context = game_context
        self.map_rect = Rect(0, 0, 0, 0)
        self.xo = 0
        self.yo = 0

    def draw(self, surface: Surface) -> None:
        self.game_context.level.draw(surface, self.xo, self.yo)

    def gids_for_rect(self, rect: Rect) -> list[int]:
        main_layer = self.game_context.level.main_layer
        level_map = self.game_context.level.map
        t_w = level_map.tilewidth
        t_h = level_map.tileheight

        t_col = rect.x // t_w
        t_row = rect.y // t_h
        start_col = t_col

        t_x = t_col * t_w
        t_y = t_row * t_h

        res = []
        try:
            while t_y + t_h >= rect.y and t_y < rect.bottom:
                while t_x + t_w > rect.x and t_x < rect.right:
                    res.append(main_layer.data[t_row][t_col])
                    t_col += 1
                    t_x = t_col * t_w
                t_col = start_col
                t_row += 1
                t_x = t_col * t_w
                t_y = t_row * t_h
        except IndexError as e:
            raise IndexError(f"[{t_row}][{t_col}]", e)

        return res

    def move_player(self, dx: float, dy: float) -> bool:
        player = self.game_context.player
        next_rect = player.next_rect
        next_rect.x += dx
        next_rect.y += dy

        level = self.game_context.level
        if next_rect.x >= 0 and next_rect.y >= 0 and \
                next_rect.right < level.width and \
                next_rect.top < level.height:

            gids = self.gids_for_rect(next_rect)
            if next((g for g in gids if g > 0), 0) == 0:
                self.game_context.player.move_to(next_rect.topleft)
                return True

        lx = player.rect.x
        ly = player.rect.y
        rx = next_rect.x
        ry = next_rect.y
        r = Rect((0, 0), next_rect.size)
        changed = False
        while not is_close(lx, rx, ly, ry):
            changed = True
            mx = rx + (lx - rx) / 2
            my = ry + (ly - ry) / 2
            r.x = mx
            r.y = my

            middle_collides = not (next_rect.x >= 0 and next_rect.y >= 0 and
                next_rect.right < level.width and
                next_rect.top < level.height)

            if not middle_collides:
                try:
                    gids = self.gids_for_rect(r)
                except IndexError:
                    raise
                middle_collides = next((g for g in gids if g > 0), 0) != 0

            if middle_collides:
                rx = mx
                ry = my
            else:
                lx = mx
                ly = my

        if changed and (int(next_rect.x) != int(lx) or int(next_rect.y) != int(ly)):
            next_rect.x = lx
            next_rect.y = ly
            self.game_context.player.move_to(next_rect.topleft)
        return False

    def process_keys(self, _previous_keys: ScancodeWrapper, current_keys: ScancodeWrapper) -> None:
        player = self.game_context.player
        player_moved = False
        if current_keys[pygame.K_LEFT] and current_keys[pygame.K_RIGHT]:
            player.vx = 0
        elif current_keys[pygame.K_LEFT]:
            self.game_context.player.turn_left()
            player.vx = -player.player_speed
            # player_moved = self.move_player(-player.player_speed, 0)
        elif current_keys[pygame.K_RIGHT]:
            self.game_context.player.turn_right()
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
            self.game_context.player.animate_walk()
            self.update_map_position()
        else:
            self.game_context.player.stop_walk()

    def init_level(self) -> None:
        tiled_map = self.game_context.level.map
        self.map_rect.width = tiled_map.width * tiled_map.tilewidth
        self.map_rect.height = tiled_map.height * tiled_map.tileheight

    def set_level_part(self, level_part: int) -> None:
        self.game_context.level.set_level_part(level_part, self.game_context.player)

    def update_map_position(self) -> None:
        def place(screen_half: int, player_pos: float, map_width: int) -> int:
            player_pos = int(player_pos)
            offset = player_pos - screen_half
            if offset < 0: offset = 0
            if offset + 2 * screen_half > map_width: offset = map_width - 2 * screen_half
            return offset

        player_pos = self.game_context.player.rect
        self.xo = place(self.game_context.level.viewport.width // 2, player_pos.x, self.map_rect.width)
        self.yo = place(self.game_context.level.viewport.height // 2, player_pos.y, self.map_rect.height)

