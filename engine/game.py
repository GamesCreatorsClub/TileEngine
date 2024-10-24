from typing import Callable, Optional

import pygame
from pygame import Surface

from engine.debug import Debug
from engine.game_context import GameContext


class Game:
    def __init__(self, screen: Surface, game_context: GameContext, framerate: int, debug: bool = False) -> None:
        self.screen = screen
        self.game_context = game_context
        self.frameclock = pygame.time.Clock()
        self.framerate = 60
        self.debug = Debug(game_context, self.frameclock, framerate) if debug else None

        self.previous_keys = pygame.key.get_pressed()
        self.current_keys = pygame.key.get_pressed()
        self.before_map: Optional[Callable[[Surface], None]] = None
        self.after_map: Optional[Callable[[Surface], None]] = None

    def main_loop(self) -> None:
        leave = False
        while not leave:
            if self.debug:
                self.debug.frame_start()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    leave = True
                elif event.type == pygame.KEYDOWN:
                    if self.debug:
                        if self.debug.debug_key_expected:
                            processed = self.debug.process_key(event.key, event.mod)
                            self.debug.debug_key_expected = False
                        else:
                            if event.key == pygame.K_k and event.mod & pygame.KMOD_LCTRL:
                                self.debug.debug_key_expected = True
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.game_context.process_mouse_down(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.game_context.process_mouse_up(event.pos)

            self.previous_keys = self.current_keys
            self.current_keys = pygame.key.get_pressed()

            self.game_context.process_keys(self.previous_keys, self.current_keys)

            elapsed_ms = self.frameclock.tick(60)
            self.game_context.animate(elapsed_ms)

            self.screen.fill((0, 0, 0))

            if self.before_map: self.before_map(self.screen)
            self.game_context.draw(self.screen)
            if self.before_map: self.after_map(self.screen)
            if self.debug: self.debug.draw(self.screen)

            pygame.display.flip()
            self.frameclock.tick(self.framerate)
