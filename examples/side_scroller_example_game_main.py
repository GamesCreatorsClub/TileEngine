import os
import pygame
import sys

from examples.side_scroller_example_game_context import SideScrollerExampleGameContext

# This is needed to ensure examples can be run from the subfolder
if not os.path.exists("engine"):
    os.chdir(os.path.dirname(os.path.abspath(".")))

sys.path.append(os.getcwd())

from engine.game import Game
from engine.level import Level

screen_size = (1024, 640)

pygame.init()
pygame.font.init()


screen = pygame.display.set_mode(screen_size)

# Load all levels here
levels = Level.load_levels(
    screen.get_rect(),
    "assets/side_scroller/level1.tmx",
    "assets/side_scroller/level2.tmx")

game_context = SideScrollerExampleGameContext(levels)
# Starting/first level
game_context.set_level(levels["level1"])
game_context.screen_size = screen_size

game = Game(screen, game_context, framerate=60, debug=True)

# Method to be called before the map is drawn on screen with signature def xxx(surface: Surface)
game.before_map = game_context.before_map

# Method to be called after the map is drawn on screen with signature def xxx(surface: Surface)
game.after_map = game_context.after_map

# Main game loop - see context for key processing
game.main_loop()

pygame.display.quit()
pygame.quit()
