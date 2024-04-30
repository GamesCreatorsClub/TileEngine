import pygame
from pygame import Rect

from engine.engine import Engine
from engine.game_context import GameContext

from engine.level import Level
from game.debug import Debug

screen_size = (1024, 640)

pygame.init()
pygame.font.init()


screen = pygame.display.set_mode(screen_size)

frameclock = pygame.time.Clock()
framerate = 60

level = Level.load_level("assets/level1.tmx")

game_context = GameContext(level)
engine = Engine(game_context)
engine.init_level()
engine.set_level_part(1)


debug = Debug(engine, frameclock, framerate)


xo = 0
yo = 0

current_keys = pygame.key.get_pressed()
level_rect = Rect(20, 20, screen_size[0] - 40, 260)

leave = False
while not leave:
    debug.frame_start()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            leave = True
        elif event.type == pygame.KEYDOWN:
            if debug.debug_key_expected:
                processed = debug.process_key(event.key, event.mod)
                debug.debug_key_expected = False
            else:
                if event.key == pygame.K_k and event.mod & pygame.KMOD_LCTRL:
                    debug.debug_key_expected = True

    previous_keys = current_keys
    current_keys = pygame.key.get_pressed()

    engine.process_keys(previous_keys, current_keys)

    elapsed_ms = frameclock.tick(60)

    screen.fill((0, 0, 0))

    engine.draw(screen)
    debug.draw(screen)

    pygame.display.flip()
    frameclock.tick(framerate)

pygame.display.quit()
pygame.quit()
