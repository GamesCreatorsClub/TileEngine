import time

import pygame.draw
from pygame import Surface, Rect
from pygame.time import Clock

from engine import level
from engine.engine import Engine


class Debug:
    def __init__(self, engine: Engine, frameclock: Clock, framerate: int, back_buffer_secs: float = 3.0) -> None:
        self.engine = engine
        self.frameclock = frameclock
        self.framerate = framerate
        self._frame_start = 0.0
        self._max_frame_time = framerate / 1000.0
        self._back_buffer_len = int(framerate * back_buffer_secs)
        self._back_buffer: list[float] = [0.0] * self._back_buffer_len
        self.debug_colour_main = pygame.color.THECOLORS["darkgreen"]
        self.debug_colour_decoration = pygame.color.THECOLORS["black"]
        self.utilisation_rect = Rect(0, 0, 0, 0)
        self.show_utilisation = True
        self.show_fps = False
        self.debug_key_expected = False
        self.debug_font_small = pygame.font.SysFont("Comic Sans MS", 30)
        self.debug_font_big = pygame.font.SysFont("Comic Sans MS", 60)
        self.show_player = False

        self._show_jumps = False

        self.input_expected_text = self.debug_font_big.render("Input:", True, self.debug_colour_main)

    def frame_start(self) -> None:
        self._frame_start = time.time()

    def process_key(self, key: int, _mod: int) -> bool:
        if key == pygame.K_u: self.show_utilisation = not self.show_utilisation
        elif key == pygame.K_f: self.show_fps = not self.show_fps
        elif key == pygame.K_o: level.offscreen_rendering = not level.offscreen_rendering
        elif key == pygame.K_p: self.show_player = not self.show_player
        elif key == pygame.K_j:
            self.show_jumps = not self.show_jumps
        else:
            return False
        return True

    @property
    def show_jumps(self) -> bool: return self._show_jumps

    @show_jumps.setter
    def show_jumps(self, v: bool) -> None:
        self._show_jumps = v
        self.engine.game_context.player.save_previous_positions = v
        if not v:
            del self.engine.game_context.player.previous_positions[:]

    def draw(self, screen: Surface) -> None:
        screen_rect = screen.get_rect()
        if self.utilisation_rect.right != screen_rect.right or self.utilisation_rect.bottom != screen_rect.bottom:
            self.utilisation_rect = Rect(screen_rect.w - self._back_buffer_len - 2,
                                         screen_rect.h - 122,
                                         self._back_buffer_len + 2,
                                         122)

        elapsed = time.time() - self._frame_start
        utilisation_percentage = elapsed * 100 / self._max_frame_time
        utilisation_percentage = utilisation_percentage if utilisation_percentage < 120.0 else 120.
        self._back_buffer.append(utilisation_percentage)
        del self._back_buffer[0]

        if self.debug_key_expected:
            screen.blit(self.input_expected_text, (0, 0))

        if self.show_fps:
            fps = self.frameclock.get_fps()
            screen.blit(self.debug_font_small.render(f"{fps:3.1f} fps", True, self.debug_colour_main), (screen_rect.right - 90, 0))

        if self.show_player:
            fps = self.frameclock.get_fps()
            player = self.engine.game_context.player
            screen.blit(
                self.debug_font_small.render(f"P: {player.vx:3.1f},{player.vy:3.1f} {player.hit_velocity:3.1f} {'_' if player.on_the_ground else ' '}", True, self.debug_colour_main),
                (200, 0))

        if self.show_utilisation:
            pygame.draw.rect(screen,
                             self.debug_colour_main,
                             self.utilisation_rect,
                             width=1)
            points = [
                (self.utilisation_rect.x + 1 + i, self.utilisation_rect.bottom - v + 1) for i, v in enumerate(self._back_buffer)
            ]
            points.append((self.utilisation_rect.right, self.utilisation_rect.bottom))
            points.append((self.utilisation_rect.left, self.utilisation_rect.bottom + 1))
            pygame.draw.polygon(screen, self.debug_colour_main, points)
        # for i in range(1, self._back_buffer_len):
        #     pygame.draw.line(screen,
        #                      self.debug_colour,
        #                      (self.utilisation_rect.x + 1 + i,
        #                       self.utilisation_rect.bottom - self._back_buffer[i - i] + 1),
        #                      (self.utilisation_rect.x + 2 + i,
        #                       self.utilisation_rect.bottom - self._back_buffer[i] + 1))

        if self._show_jumps:
            if len(self.engine.game_context.player.previous_positions) > 1:
                xo = self.engine.xo
                yo = self.engine.yo
                positions = [
                    (x - xo, y - yo) for x, y in self.engine.game_context.player.previous_positions
                ]
                pygame.draw.lines(screen, (255, 255, 255), False, positions, width=2)