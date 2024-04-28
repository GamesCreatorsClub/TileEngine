
import pygame
from pygame import Surface, Rect
from pygame.key import ScancodeWrapper

from engine.game_context import GameContext


class Engine:
    def __init__(self, game_context: GameContext) -> None:
        self.game_context = game_context
        self.map_rect = Rect(0, 0, 0, 0)
        self.xo = 0
        self.yo = 0

    def draw(self, surface: Surface) -> None:
        self.game_context.level.draw(surface, self.xo, self.yo)

    def move_player(self, dx: float, dy: float) -> bool:
        next_rect = self.game_context.player.next_rect
        next_rect.x += (dx * 2)
        next_rect.y += (dy * 2)

        self.game_context.player.rect.topleft = next_rect.topleft
        return True

    def process_keys(self, _previous_keys: ScancodeWrapper, current_keys: ScancodeWrapper) -> None:
        player_moved = False
        if current_keys[pygame.K_LEFT]:
            self.move_player(-1, 0)
            self.game_context.player.turn_left()
            player_moved = True
        if current_keys[pygame.K_RIGHT]:
            self.move_player(1, 0)
            self.game_context.player.turn_right()
            player_moved = True
        if current_keys[pygame.K_UP]:
            self.move_player(0, -1)
        if current_keys[pygame.K_DOWN]:
            self.move_player(0, 1)

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

