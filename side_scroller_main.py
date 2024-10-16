import pygame

from engine.game import Game
from engine.level import Level

from game.side_scroller_game_context import SideScrollerGameContext

screen_size = (1024, 640)

pygame.init()
pygame.font.init()


screen = pygame.display.set_mode(screen_size)


levels = Level.load_levels(
    screen.get_rect(),
    "assets/side_scroller/level1.tmx",
    "assets/side_scroller/level2.tmx")

game_context = SideScrollerGameContext(levels)
game_context.set_level(levels["level1"])

game = Game(screen, game_context, 60, True)

game.main_loop()

pygame.display.quit()
pygame.quit()
