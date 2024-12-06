import pygame

from engine.game import Game
from engine.level import Level
from examples.top_down_example_game_context import TopDownExampleGameContext
from game.rpg_game_context import RPGGameContext

screen_size = (1024, 640)

pygame.init()
pygame.font.init()

small_font = pygame.font.SysFont("apple casual", 16)
font = pygame.font.SysFont("apple casual", 24)

screen = pygame.display.set_mode(screen_size)

levels = Level.load_levels(
    screen.get_rect(),
    "assets/top_down/test-level.tmx")

game_context = TopDownExampleGameContext(levels, font, small_font)
game_context.set_level(levels["test-level"])
game_context.screen_size = screen_size

game = Game(
    screen,
    game_context,
    framerate=60, debug=True)

game.before_map = None
game.after_map = game_context.after_map

game.main_loop()

pygame.display.quit()
pygame.quit()
