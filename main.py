import pygame
from pygame import Rect

from game.game_context import GameContext

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


debug = Debug(frameclock, framerate)


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

    last_keys = current_keys
    current_keys = pygame.key.get_pressed()

    if current_keys[pygame.K_LEFT]: xo = (xo - 1) if xo > 0 else xo
    if current_keys[pygame.K_RIGHT]: xo = (xo + 1) if xo < 1024 else xo
    if current_keys[pygame.K_UP]: yo = (yo - 1) if yo > 0 else yo
    if current_keys[pygame.K_DOWN]: yo = (yo + 1) if yo < 1024 else yo

    elapsed_ms = frameclock.tick(60)

    screen.fill((0, 0, 0))

    old_clip = screen.get_clip()
    screen.set_clip(level_rect)
    level.draw(screen, xo, yo)
    screen.set_clip(old_clip)
    debug.draw(screen)

    pygame.display.flip()
    frameclock.tick(framerate)

pygame.display.quit()
pygame.quit()
