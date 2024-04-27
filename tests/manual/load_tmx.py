import os.path
import sys

import pygame
from pytmx import load_pygame

from engine.level import Level

print(f"file exists {os.path.exists('assets/level1.tmx')}")

screen_size = (640, 640)

pygame.init()
frameclock = pygame.time.Clock()
screen = pygame.display.set_mode(screen_size)

# tilemap = pytmx.TiledMap("assets/level1.tmx")
tmx_data = load_pygame("assets/level1.tmx")

level = Level(tmx_data)
level.level_part = 1


xo = 0
yo = 0

current_keys = pygame.key.get_pressed()

leave = False
while not leave:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    last_keys = current_keys
    current_keys = pygame.key.get_pressed()
    if current_keys[pygame.K_LEFT]: xo = (xo - 1) if xo > 0 else xo
    if current_keys[pygame.K_RIGHT]: xo = (xo + 1) if xo < 1024 else xo
    if current_keys[pygame.K_UP]: yo = (yo - 1) if yo > 0 else yo
    if current_keys[pygame.K_DOWN]: yo = (yo + 1) if yo < 1024 else yo

    elapsed_ms = frameclock.tick(60)
    fps = frameclock.get_fps()

    screen.fill((0, 224, 0))

    level.draw(screen, xo, yo)

    pygame.display.flip()


print("Loaded")