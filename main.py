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

levels = Level.load_levels("assets/level1.tmx")
first_level = levels[0]

engine = Engine()

game_context = GameContext(engine)
game_context.all_levels = {
    i + 1: l for i, l in enumerate(levels)
}
game_context.set_level(first_level)

first_level.start(game_context.player)

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
